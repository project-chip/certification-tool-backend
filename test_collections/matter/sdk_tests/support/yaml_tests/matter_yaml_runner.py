#
# Copyright (c) 2023 Project CHIP Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Optional, Union

import loguru
from matter.yamltests.definitions import SpecDefinitionsFromPaths
from matter.yamltests.hooks import TestParserHooks, TestRunnerHooks

# Matter YAML tests Imports
from matter.yamltests.parser import TestParserConfig
from matter.yamltests.parser_builder import TestParserBuilderConfig
from matter.yamltests.pseudo_clusters.pseudo_clusters import get_default_pseudo_clusters
from matter.yamltests.runner import TestRunnerConfig, TestRunnerOptions
from matter.yamltests.websocket_runner import WebSocketRunner, WebSocketRunnerConfig
from matter_chip_tool_adapter import adapter as ChipToolAdapter
from matter_chip_tool_adapter.decoder import MatterLog
from matter_placeholder_adapter import adapter as ChipAppAdapter

from app.container_manager.backend_container import backend_container
from app.schemas.pics import PICS, PICSError
from app.singleton import Singleton
from app.test_engine.logger import CHIP_LOG_FORMAT, CHIPTOOL_LEVEL
from app.test_engine.logger import test_engine_logger as logger
from test_collections.matter.config import matter_settings

from ..chip.chip_server import ChipServer, ChipServerType
from ..paths import SDK_CHECKOUT_PATH
from ..pics import PICS_FILE_PATH, set_pics_command

# Test Parameters
TEST_ARG_NODEID = "nodeId"
TEST_ARG_TIMEOUT = "timeout"
TEST_DEFAULT_TIMEOUT_IN_SEC = "900"  # 15 minutes (60*15 seconds)

TEST_RUNNER_OPTIONS = TestRunnerOptions(
    stop_on_error=False, stop_on_warning=False, stop_at_number=-1, delay_in_ms=250
)

PAIRING_CMD = "pairing"
PAIRING_MODE_ONNETWORK = "onnetwork-long"
PAIRING_MODE_BLE_WIFI = "ble-wifi"
PAIRING_MODE_BLE_THREAD = "ble-thread"
PAIRING_MODE_WIFIPAF_WIFI = "wifipaf-wifi"
PAIRING_MODE_NFC_THREAD = "nfc-thread"
PAIRING_MODE_UNPAIR = "unpair"

# Websocket runner
YAML_TESTS_PATH_BASE = SDK_CHECKOUT_PATH / Path("yaml_tests/")
YAML_TESTS_PATH = YAML_TESTS_PATH_BASE / Path("yaml/sdk")
XML_SPEC_DEFINITION_PATH = SDK_CHECKOUT_PATH / Path("sdk_runner/specifications/chip/")


# Docker Network
DOCKER_NETWORK_SETTINGS_KEY = "NetworkSettings"
DOCKER_NETWORKS_KEY = "Networks"
DOCKER_CHIP_DEFAULT_KEY = "chip-default"
DOCKER_GATEWAY_KEY = "Gateway"


class ContainerNotRunning(Exception):
    """Raised when we attempt to use a docker container but it's not running"""


class UnsupportedChipServerType(Exception):
    """Raised when we attempt to use a chip binary, but the server type is not
    supported"""


class MatterYAMLRunner(metaclass=Singleton):
    __pics_file_created: bool  # Flag that is set if PICS needs to be passed to server

    def __init__(
        self,
        logger: loguru.Logger = logger,
    ) -> None:
        """
        Args:
            logger (Logger, optional): Optional logger injection. Defaults to standard
            self.logger.
        """
        self.logger = logger
        self.chip_server: ChipServer = ChipServer(logger)
        self.__pics_file_created = False
        # TODO: Need to dynamically select the specs based on clusters in test.
        specifications_paths = [f"{XML_SPEC_DEFINITION_PATH}/*.xml"]
        self.pseudo_clusters = get_default_pseudo_clusters()
        self.specifications = SpecDefinitionsFromPaths(
            specifications_paths, self.pseudo_clusters
        )

    async def setup(
        self, server_type: ChipServerType, use_paa_certs: bool = False
    ) -> None:
        self.__pics_file_created = False

        web_socket_config = WebSocketRunnerConfig()
        web_socket_config.server_address = self.__get_gateway_ip()
        self.__test_harness_runner = WebSocketRunner(config=web_socket_config)

        self.__chip_tool_log = await self.chip_server.start(server_type, use_paa_certs)

    async def stop(self) -> None:
        await self.stop_runner()
        await self.chip_server.stop()

    def __get_gateway_ip(self) -> str:
        """
        Obtains the IP address from the backend gateway.

        Returns:
            str: IP address of the gateway within the SDK container
        """
        backend_container_obj = backend_container()
        if backend_container_obj is None:
            raise ContainerNotRunning("Backend container not running")

        return (
            backend_container_obj.attrs.get(DOCKER_NETWORK_SETTINGS_KEY, {})
            .get(DOCKER_NETWORKS_KEY, {})
            .get(DOCKER_CHIP_DEFAULT_KEY, {})
            .get(DOCKER_GATEWAY_KEY, "")
        )

    async def start_runner(self) -> None:
        if not self.__test_harness_runner.is_connected:
            await self.__test_harness_runner.start()

    async def stop_runner(self) -> None:
        if self.__test_harness_runner.is_connected:
            await self.__test_harness_runner.stop()

    async def send_websocket_command(self, cmd: str) -> Union[str, bytes, bytearray]:
        await self.start_runner()
        response = await self.__test_harness_runner.execute(cmd)

        # Log response
        if response:
            json_payload = json.loads(response)
            logs = MatterLog.decode_logs(json_payload.get("logs"))

            for log_entry in logs:
                self.logger.log(
                    CHIPTOOL_LEVEL,
                    CHIP_LOG_FORMAT.format(log_entry.module, log_entry.message),
                )

        return response

    async def pairing(self, mode: str, *params: str) -> bool:
        command = [PAIRING_CMD, mode] + list(params)

        if matter_settings.CHIP_TOOL_TRACE:
            topic = f"PAIRING_{mode}"
            command.append(self.chip_server.trace_file_params(topic))

        response = await self.send_websocket_command(" ".join(command))
        if not response:
            return False

        json_payload = json.loads(response)
        # TODO: Need to save logs maybe?
        # logs = MatterLog.decode_logs(json_payload.get('logs'))
        return not bool(
            len([lambda x: x.get("error") for x in json_payload.get("results")])
        )

    async def run_test(
        self,
        test_step_interface: TestRunnerHooks,
        test_parser_hooks: TestParserHooks,
        test_path: str,
        server_type: ChipServerType,
        timeout: Optional[str] = None,
        test_parameters: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Run the test with the associated id using the right executable/container

        Args:
            test_path (str): The path of the test to be run
            server_type (ChipServerType): Type of the binary that needs to be run

        Raises:
            UnsupportedChipServerType: Unsupported type of test binary

        Returns:
            A boolean indicating if the run has succeeded
        """

        if timeout is None:
            timeout = TEST_DEFAULT_TIMEOUT_IN_SEC

        test_options = {
            f"{TEST_ARG_NODEID}": f"{hex(self.chip_server.node_id)}",
            f"{TEST_ARG_TIMEOUT}": f"{timeout}",
        }

        if test_parameters is not None:
            test_options.update(
                {
                    key: value
                    for key, value in test_parameters.items()
                    # We are not considering nodeId and cluster for test parameters
                    # skipping nodeID, as it is passed separately
                    # skipping cluster, as we don't allow to override this
                    if key != "nodeId" and key != "cluster"
                }
            )

        pics_path = None
        if self.__pics_file_created:
            pics_path = f"{PICS_FILE_PATH}"
            self.logger.info(f"Using PICS file: {pics_path}")

        parser_config = TestParserConfig(pics_path, self.specifications, test_options)
        parser_builder_config = TestParserBuilderConfig(
            [test_path], parser_config, test_parser_hooks
        )

        # Reuse chip-tool adapter for camera-controller
        if (
            server_type == ChipServerType.CHIP_TOOL
            or server_type == ChipServerType.CHIP_CAMERA_CONTROLLER
        ):
            adapter = ChipToolAdapter.Adapter(parser_config.definitions)
        elif server_type == ChipServerType.CHIP_APP:
            adapter = ChipAppAdapter.Adapter(parser_config.definitions)
        else:
            raise UnsupportedChipServerType(f"Unsupported Server Type: {server_type}")

        runner_config = TestRunnerConfig(
            adapter,
            self.pseudo_clusters,
            TEST_RUNNER_OPTIONS,
            test_step_interface,
            auto_start_stop=False,
        )

        await self.start_runner()

        return await self.__test_harness_runner.run(
            parser_builder_config, runner_config
        )

    async def unpair(self) -> bool:
        return await self.pairing(
            PAIRING_MODE_UNPAIR,
            hex(self.chip_server.node_id),
        )

    async def pairing_on_network(
        self,
        setup_code: str,
        discriminator: str,
    ) -> bool:
        return await self.pairing(
            PAIRING_MODE_ONNETWORK,
            hex(self.chip_server.node_id),
            setup_code,
            discriminator,
        )

    async def pairing_ble_wifi(
        self,
        ssid: str,
        password: str,
        setup_code: str,
        discriminator: str,
    ) -> bool:
        return await self.pairing(
            PAIRING_MODE_BLE_WIFI,
            hex(self.chip_server.node_id),
            ssid,
            password,
            setup_code,
            discriminator,
        )

    async def pairing_wifipaf_wifi(
        self,
        ssid: str,
        password: str,
        setup_code: str,
        discriminator: str,
    ) -> bool:
        return await self.pairing(
            PAIRING_MODE_WIFIPAF_WIFI,
            hex(self.chip_server.node_id),
            ssid,
            password,
            setup_code,
            discriminator,
        )

    async def pairing_ble_thread(
        self,
        hex_dataset: str,
        setup_code: str,
        discriminator: str,
    ) -> bool:
        return await self.pairing(
            PAIRING_MODE_BLE_THREAD,
            hex(self.chip_server.node_id),
            f"hex:{hex_dataset}",
            setup_code,
            discriminator,
        )

    async def pairing_nfc_thread(
        self,
        hex_dataset: str,
        setup_code: str,
        discriminator: str,
    ) -> bool:
        return await self.pairing(
            PAIRING_MODE_NFC_THREAD,
            hex(self.chip_server.node_id),
            f"hex:{hex_dataset}",
            setup_code,
            discriminator,
        )

    def set_pics(self, pics: PICS) -> None:
        """Sends command to create pics file.

        Args:
            pics (PICS): PICS that contains all the pics codes

        Raises:
            PICSError: If creating PICS file inside the container fails.
        """
        # List of default PICS which needs to set specifically in TH are added here.
        # These PICS are applicable for CI / Chip tool testing purposes only.
        # These PICS are unknown / not visible to external users.

        prefix, cmd = set_pics_command(pics)

        full_cmd = f"{prefix} {cmd}"
        self.logger.info(f"Sending command: {full_cmd}")
        result = subprocess.run(full_cmd, shell=True)

        if result.returncode != 0:
            raise PICSError("Creating PICS file failed")

        self.__pics_file_created = True

    def reset_pics_state(self) -> None:
        self.__pics_file_created = False
