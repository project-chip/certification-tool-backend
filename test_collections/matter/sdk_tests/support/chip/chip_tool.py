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
from datetime import datetime
from enum import Enum
from pathlib import Path
from random import randrange
from typing import Any, Generator, Optional, Union, cast

import loguru
from matter_chip_tool_adapter import adapter as ChipToolAdapter
from matter_chip_tool_adapter.decoder import MatterLog
from matter_placeholder_adapter import adapter as ChipAppAdapter
from matter_yamltests.definitions import SpecDefinitionsFromPaths
from matter_yamltests.hooks import TestParserHooks, TestRunnerHooks

# Matter YAML tests Imports
from matter_yamltests.parser import TestParserConfig
from matter_yamltests.parser_builder import TestParserBuilderConfig
from matter_yamltests.pseudo_clusters.pseudo_clusters import get_default_pseudo_clusters
from matter_yamltests.runner import TestRunnerConfig, TestRunnerOptions
from matter_yamltests.websocket_runner import WebSocketRunner, WebSocketRunnerConfig

from app.container_manager.backend_container import backend_container
from app.core.config import settings
from app.schemas.pics import PICS, PICSError
from app.singleton import Singleton
from app.test_engine.logger import CHIP_LOG_FORMAT, CHIPTOOL_LEVEL
from app.test_engine.logger import test_engine_logger as logger

from ..paths import SDK_CHECKOUT_PATH
from ..pics import PICS_FILE_PATH, set_pics_command
from ..sdk_container import DOCKER_LOGS_PATH, DOCKER_PAA_CERTS_PATH, SDKContainer

# Chip Tool Parameters
CHIP_TOOL_EXE = "./chip-tool"
CHIP_TOOL_ARG_NODEID = "nodeId"
CHIP_TOOL_ARG_DELAY = "delayInMs"
CHIP_TOOL_ARG_PICS = "--PICS"
CHIP_TOOL_ARG_ENDPOINT_ID = "--endpoint"
CHIP_TOOL_ARG_TIMEOUT = "timeout"
CHIP_TOOL_TEST_DEFAULT_TIMEOUT_IN_SEC = "900"  # 15 minutes (60*15 seconds)
CHIP_TOOL_ARG_PAA_CERTS_PATH = "--paa-trust-store-path"
CHIP_TOOL_CONTINUE_ON_FAILURE_VALUE = True

TESTS_CMD = "tests"
PAIRING_CMD = "pairing"
PAIRING_MODE_CODE = "code"
PAIRING_MODE_ONNETWORK = "onnetwork-long"
PAIRING_MODE_BLE_WIFI = "ble-wifi"
PAIRING_MODE_BLE_THREAD = "ble-thread"
PAIRING_MODE_UNPAIR = "unpair"
TEST_STEP_DELAY_VALUE = 250


# Chip App Parameters
CHIP_APP_EXE = "./chip-app1"
CHIP_APP_PORT_ARG = "--secured-device-port"
CHIP_APP_DEFAULT_PORT = 5540
CHIP_APP_TEST_CMD_ARG = "--command"

# Websocket runner
YAML_TESTS_PATH_BASE = SDK_CHECKOUT_PATH / Path("yaml_tests/")
YAML_TESTS_PATH = YAML_TESTS_PATH_BASE / Path("yaml/sdk")
XML_SPEC_DEFINITION_PATH = SDK_CHECKOUT_PATH / Path("sdk_runner/specifications/chip/")


# Docker Network
DOCKER_NETWORK_SETTINGS_KEY = "NetworkSettings"
DOCKER_NETWORKS_KEY = "Networks"
DOCKER_CHIP_DEFAULT_KEY = "chip-default"
DOCKER_GATEWAY_KEY = "Gateway"


class ChipToolStartingError(Exception):
    """Raised when we fail to start the chip-tool docker container"""


class ChipToolNotRunning(Exception):
    """Raised when we attempt to use chip-tool, but docker container is not running"""


class ChipToolUnknownTestType(Exception):
    """Raised when we attempt to use chip-tool, but test(executable) type is not
    supported"""


class ChipTestType(str, Enum):
    CHIP_TOOL = "chip-tool"
    CHIP_APP = "chip-app"


class ChipTool(metaclass=Singleton):
    """
    Base class for Chip Tool to be used during test case execution.

    Usage:
    Create an instance by calling initializer. When ready to use, start the device by
    calling start_device and when done cleanup by calling destroy_device
    """

    __node_id: Optional[int] = None
    __pics_file_created: bool  # Flag that is set if PICS needs to be passed to chiptool

    def __init__(
        self,
        logger: loguru.Logger = logger,
    ) -> None:
        """Chip-Tool run chip-tool commands in Docker container.

        Args:
            logger (Logger, optional): Optional logger injection. Defaults to standard
            self.logger.
        """

        self.logger = logger
        self.sdk_container: SDKContainer = SDKContainer(logger)
        self.__pics_file_created = False
        self.__chip_server_id: Optional[str] = None
        self.__server_started = False
        self.__server_logs: Union[Generator, bytes, tuple]
        self.__use_paa_certs = False
        self.__test_type: ChipTestType = ChipTestType.CHIP_TOOL
        # TODO: Need to dynamically select the specs based on clusters in test.
        specifications_paths = [f"{XML_SPEC_DEFINITION_PATH}/*.xml"]
        self.pseudo_clusters = get_default_pseudo_clusters()
        self.specifications = SpecDefinitionsFromPaths(
            specifications_paths, self.pseudo_clusters
        )

    @property
    def pics_file_created(self) -> bool:
        return self.__pics_file_created

    @property
    def node_id(self) -> int:
        """Node id is used to reference DUT during testing.

        Returns:
            int: unit64 node id
        """

        if self.__node_id is None:
            return self.__reset_node_id()

        return self.__node_id

    def __reset_node_id(self) -> int:
        """Resets node_id to a random uint64."""
        max_uint_64 = (1 << 64) - 1
        self.__node_id = randrange(max_uint_64)
        self.logger.info(f"New Node Id generated: {hex(self.__node_id)}")
        return self.__node_id

    async def __wait_for_server_start(self, log_generator: Generator) -> bool:
        for chunk in log_generator:
            decoded_log = chunk.decode().strip()
            log_lines = decoded_log.splitlines()
            for line in log_lines:
                if "LWS_CALLBACK_PROTOCOL_INIT" in line:
                    self.logger.log(CHIPTOOL_LEVEL, line)
                    return True
                self.logger.log(CHIPTOOL_LEVEL, line)
        else:
            return False

    async def start_chip_server(
        self, test_type: ChipTestType, use_paa_certs: bool = False
    ) -> Generator:
        # Start chip interactive server
        self.__use_paa_certs = use_paa_certs
        self.__test_type = test_type

        self.logger.info("Starting chip server")
        if self.__server_started:
            return cast(Generator, self.__server_logs)

        if test_type == ChipTestType.CHIP_TOOL:
            prefix = CHIP_TOOL_EXE
            command = ["interactive", "server"]
        elif test_type == ChipTestType.CHIP_APP:
            prefix = CHIP_APP_EXE
            command = ["--interactive", "--port 9002"]
        else:
            raise ChipToolUnknownTestType(f"Unsupported Test Type: {test_type}")

        if settings.CHIP_TOOL_TRACE:
            topic = "CHIP_TOOL_WEBSOCKET_SERVER"
            command.append(self.__trace_file_params(topic))

        if use_paa_certs:
            paa_cert_params = f"{CHIP_TOOL_ARG_PAA_CERTS_PATH} {DOCKER_PAA_CERTS_PATH}"
            command.append(paa_cert_params)

        exec_result = self.sdk_container.send_command(
            command,
            prefix=prefix,
            is_stream=True,
            is_socket=False,
        )
        self.__server_logs = exec_result.output
        self.__chip_server_id = exec_result.exec_id

        wait_result = await self.__wait_for_server_start(
            cast(Generator, self.__server_logs)
        )
        if not wait_result:
            raise ChipToolStartingError("Unable to start chip-tool server")
        self.__server_started = True
        return cast(Generator, self.__server_logs)

    def __wait_for_server_exit(self) -> Optional[int]:
        if self.__chip_server_id is None:
            self.logger.info(
                "Server execution id not found, cannot wait for server exit."
            )
            return None

        exit_code = self.sdk_container.exec_exit_code(self.__chip_server_id)
        while not exit_code:
            exit_code = self.sdk_container.exec_exit_code(self.__chip_server_id)

        return exit_code

    async def stop_chip_server(self) -> None:
        if not self.__server_started:
            return

        await self.start_runner()
        await self.__test_harness_runner._client.send("quit()")
        self.__wait_for_server_exit()
        await self.stop_runner()
        self.__server_started = False

    def __get_gateway_ip(self) -> str:
        """
        Obtains the IP address from the backend gateway.

        Returns:
            str: IP address of the gateway within the th-chip-tool container
        """
        backend_container_obj = backend_container()
        if backend_container_obj is None:
            raise ChipToolNotRunning("Backend container not running")

        return (
            backend_container_obj.attrs.get(DOCKER_NETWORK_SETTINGS_KEY, {})
            .get(DOCKER_NETWORKS_KEY, {})
            .get(DOCKER_CHIP_DEFAULT_KEY, {})
            .get(DOCKER_GATEWAY_KEY, "")
        )

    async def start_server(
        self, test_type: ChipTestType, use_paa_certs: bool = False
    ) -> None:
        # Reset any previous states
        self.__pics_file_created = False
        # Generate new random node id for the DUT
        self.__reset_node_id()
        # Server started is false after spinning up a new container.
        self.__server_started = False

        web_socket_config = WebSocketRunnerConfig()
        web_socket_config.server_address = self.__get_gateway_ip()
        self.__test_harness_runner = WebSocketRunner(config=web_socket_config)

        self.__chip_tool_log = await self.start_chip_server(test_type, use_paa_certs)

    async def start_runner(self) -> None:
        if not self.__test_harness_runner.is_connected:
            await self.__test_harness_runner.start()

    async def stop_runner(self) -> None:
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

    # Chip Tool Command wrappers ###
    async def pairing(self, mode: str, *params: str, stream: bool = True) -> bool:
        command = [PAIRING_CMD, mode] + list(params)

        if settings.CHIP_TOOL_TRACE:
            topic = f"PAIRING_{mode}"
            command.append(self.__trace_file_params(topic))

        response = await self.send_websocket_command(" ".join(command))
        if not response:
            return False

        json_payload = json.loads(response)
        # TODO: Need to save logs maybe?
        # logs = MatterLog.decode_logs(json_payload.get('logs'))
        return not bool(
            len([lambda x: x.get("error") for x in json_payload.get("results")])
        )

    async def run_websocket_test(
        self,
        test_step_interface: TestRunnerHooks,
        adapter: Optional[Any],
        parser_builder_config: TestParserBuilderConfig,
    ) -> bool:
        stop_on_warning = False
        stop_at_number = -1
        stop_on_error = not CHIP_TOOL_CONTINUE_ON_FAILURE_VALUE
        runner_options = TestRunnerOptions(
            stop_on_error, stop_on_warning, stop_at_number, TEST_STEP_DELAY_VALUE
        )
        self.__runner_hooks = test_step_interface
        runner_config = TestRunnerConfig(
            adapter,
            self.pseudo_clusters,
            runner_options,
            test_step_interface,
            auto_start_stop=False,
        )

        await self.start_runner()

        return await self.__test_harness_runner.run(
            parser_builder_config, runner_config
        )

    # TODO: Clean up duplicate function definition written to avoid unit test failures
    async def run_test(
        self,
        test_step_interface: TestRunnerHooks,
        test_parser_hooks: TestParserHooks,
        test_id: str,
        test_type: ChipTestType,
        timeout: Optional[str] = None,
        test_parameters: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Run the test with the associated id using the right executable/container

        Args:
            test_id (str): Test Id to be run, must be available on the particular binary
            test_type (ChipTestType): Type of the binary that needs to be run

        Raises:
            ChipToolUnknownTestType: Unsupported type of test binary

        Yields:
            ExecResultExtended named tuple with the following information
            - exit_code
            - Union of Generator / bytes / tuple
            - exec_id
            - socket, when "is_socket" is set to True
        """
        if timeout is None:
            timeout = CHIP_TOOL_TEST_DEFAULT_TIMEOUT_IN_SEC

        test_options = {
            f"{CHIP_TOOL_ARG_NODEID}": f"{hex(self.node_id)}",
            f"{CHIP_TOOL_ARG_TIMEOUT}": f"{timeout}",
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

        if test_type == ChipTestType.CHIP_TOOL:
            test_path = f"{YAML_TESTS_PATH}/{test_id}.yaml"
        else:
            test_path = f"{YAML_TESTS_PATH}/{test_id}_Simulated.yaml"

        parser_config = TestParserConfig(pics_path, self.specifications, test_options)
        parser_builder_config = TestParserBuilderConfig(
            [test_path], parser_config, test_parser_hooks
        )

        if test_type == ChipTestType.CHIP_TOOL:
            adapter = ChipToolAdapter.Adapter(parser_config.definitions)
        elif test_type == ChipTestType.CHIP_APP:
            adapter = ChipAppAdapter.Adapter(parser_config.definitions)
        else:
            raise ChipToolUnknownTestType(f"Unsupported Test Type: {test_type}")

        return await self.run_websocket_test(
            test_step_interface, adapter, parser_builder_config
        )

    async def unpair(self) -> bool:
        return await self.pairing(
            PAIRING_MODE_UNPAIR,
            hex(self.node_id),
        )

    async def pairing_on_network(
        self,
        setup_code: str,
        discriminator: str,
    ) -> bool:
        return await self.pairing(
            PAIRING_MODE_ONNETWORK,
            hex(self.node_id),
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
            hex(self.node_id),
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
            hex(self.node_id),
            f"hex:{hex_dataset}",
            setup_code,
            discriminator,
        )

    def __trace_file_params(self, topic: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
        filename = f"trace_log_{timestamp}_{hex(self.node_id)}_{topic}.log"
        path = Path(DOCKER_LOGS_PATH) / filename
        return f'--trace_file "{path}" --trace_decode 1'

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

    async def restart_server(self) -> None:
        await self.stop_chip_server()
        self.__chip_tool_log = await self.start_chip_server(
            self.__test_type, self.__use_paa_certs
        )
