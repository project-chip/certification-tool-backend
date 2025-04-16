#
# Copyright (c) 2024 Project CHIP Authors
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

from datetime import datetime
from enum import Enum
from pathlib import Path
from random import randrange
from typing import Generator, Optional, Union, cast

import loguru

from app.singleton import Singleton
from app.test_engine.logger import CHIPTOOL_LEVEL
from app.test_engine.logger import test_engine_logger as logger
from test_collections.matter.config import matter_settings

from ..sdk_container import DOCKER_LOGS_PATH, DOCKER_PAA_CERTS_PATH, SDKContainer

# Chip Tool Parameters
CHIP_TOOL_EXE = "./chip-tool"
CHIP_TOOL_ARG_PAA_CERTS_PATH = "--paa-trust-store-path"

# TODO: Use chip-camera-controller for camera tests.

# Chip App Parameters
CHIP_APP_EXE = "./chip-app1"


class ChipServerStartingError(Exception):
    """Raised when we fail to start the chip server"""


class UnsupportedChipServerType(Exception):
    """Raised when we attempt to use a chip server, but the type is not supported"""


class ChipServerType(str, Enum):
    CHIP_TOOL = "chip-tool"
    CHIP_APP = "chip-app"


class ChipServer(metaclass=Singleton):
    __node_id: Optional[int] = None

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
        self.sdk_container: SDKContainer = SDKContainer(logger)
        self.__chip_server_id: Optional[str] = None
        self.__server_started = False
        self.__server_logs: Union[Generator, bytes, tuple]
        self.__use_paa_certs = False
        self.__server_type: ChipServerType = ChipServerType.CHIP_TOOL

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

    async def start(
        self, server_type: ChipServerType, use_paa_certs: bool = False
    ) -> Generator:
        if self.__server_started:
            self.logger.info("Chip server is already started")
            return cast(Generator, self.__server_logs)

        self.logger.info("Starting chip server")

        # Generate new random node id for the DUT
        self.__reset_node_id()

        # Start chip interactive server
        self.__use_paa_certs = use_paa_certs
        self.__server_type = server_type

        if server_type == ChipServerType.CHIP_TOOL:
            prefix = CHIP_TOOL_EXE
            command = ["interactive", "server"]
        elif server_type == ChipServerType.CHIP_APP:
            prefix = CHIP_APP_EXE
            command = ["--interactive", "--port 9002"]
        else:
            raise UnsupportedChipServerType(f"Unsupported server type: {server_type}")

        if matter_settings.CHIP_TOOL_TRACE:
            topic = "CHIP_WEBSOCKET_SERVER"
            command.append(self.trace_file_params(topic))

        if use_paa_certs:
            paa_cert_params = f"{CHIP_TOOL_ARG_PAA_CERTS_PATH} {DOCKER_PAA_CERTS_PATH}"
            command.append(paa_cert_params)

        # Need to store the command to use it later to stop the proccess
        self.__server_full_command = " ".join([prefix] + command)

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
            raise ChipServerStartingError("Unable to start chip server")

        self.__server_started = True

        return cast(Generator, self.__server_logs)

    def __wait_for_server_exit(self) -> Optional[int]:
        if self.__chip_server_id is None:
            self.logger.info(
                "Server execution id not found, cannot wait for server exit."
            )
            return None

        exit_code = self.sdk_container.exec_exit_code(self.__chip_server_id)
        while exit_code is None:
            exit_code = self.sdk_container.exec_exit_code(self.__chip_server_id)

        return exit_code

    async def stop(self) -> None:
        if not self.__server_started:
            return

        try:
            self.sdk_container.send_command(
                f'-SIGTERM -f "{self.__server_full_command}"', prefix="pkill"
            )
            self.__wait_for_server_exit()
        except Exception as e:
            # Issue: https://github.com/project-chip/certification-tool/issues/414
            self.logger.info(
                "Could not get exit code after pkill command "
                f"{self.__server_full_command}."
            )
            self.logger.debug(str(e))

        self.__server_started = False

    def trace_file_params(self, topic: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
        filename = f"trace_log_{timestamp}_{hex(self.node_id)}_{topic}.log"
        path = Path(DOCKER_LOGS_PATH) / filename
        return f'--trace_file "{path}" --trace_decode 1'

    async def restart(self) -> None:
        await self.stop()
        await self.start(self.__server_type, self.__use_paa_certs)
