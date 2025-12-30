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

import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from random import randrange
from time import sleep, time
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

# Chip App Parameters
CHIP_APP_EXE = "./chip-app1"

CHIP_SERVER_EXIT_TIMEOUT = 30  # seconds


class ChipServerStartingError(Exception):
    """Raised when we fail to start the chip server"""


class UnsupportedChipServerType(Exception):
    """Raised when we attempt to use a chip server, but the type is not supported"""


class ChipServerExitError(Exception):
    """Raised when a timout happens while trying to exit the chip server"""


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

    def generate_manual_pairing_code_with_chip_tool(
        self,
        discriminator: str,
        setup_pin_code: str,
        version: int = 0,
        vendor_id: int = 0,
        product_id: int = 0,
    ) -> str:
        """Generate manual pairing code using chip-tool payload command.

        Note: This method requires the SDK container to be running.

        Args:
            discriminator: 12-bit discriminator value
            setup_pin_code: Setup PIN code
            version: Version number (default: 0)
            vendor_id: Vendor ID (default: 0)
            product_id: Product ID (default: 0)

        Returns:
            str: Manual pairing code or empty string if generation fails
        """
        # Check if SDK container is up
        if not self.sdk_container.is_running():
            self.logger.warning(
                "SDK container is not running. Cannot generate manual pairing code."
            )
            return ""

        try:
            command = [
                "payload",
                "generate-manualcode",
                "--discriminator",
                discriminator,
                "--setup-pin-code",
                setup_pin_code,
                "--version",
                str(version),
                "--vendor-id",
                str(vendor_id),
                "--product-id",
                str(product_id),
            ]

            result = self.sdk_container.send_command(
                command,
                prefix=CHIP_TOOL_EXE,
            )

            # Parse the output result to extract the manual pairing code
            if result.exit_code == 0 and result.output:
                return self.__extract_manual_code(result.output)

            self.logger.warning(
                "Failed to generate manual pairing code from chip-tool output"
            )
            return ""
        except Exception as e:
            self.logger.error(f"Error generating manual pairing code: {e}")
            return ""

    def __extract_manual_code(self, log_chunk: Generator | bytes | tuple) -> str:
        # Extracts the manual pairing code from the chip-tool output logs.
        # Log format: "[timestamp] [pid:tid] [TOO] Manual Code: XXXXXXXXXX"
        code = ""
        output_str: str

        # Convert output to string
        if isinstance(log_chunk, bytes):
            output_str = log_chunk.decode()
        else:
            # Handle Generator or tuple - convert to string
            output_str = str(log_chunk)

        # Remove ANSI escape sequences
        output_str = re.sub(r"\x1b\[[0-9;]*m", "", output_str)

        for line in output_str.splitlines():
            # Look for the line containing "[TOO] Manual Code:"
            if "[TOO] Manual Code:" in line:
                # Extract the Manual Code:"
                code = line.split("Manual Code:")[-1].strip()
                self.logger.info(f"Generated manual pairing code: {code}")
                break
        return code

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

        # A given timeout in seconds is provided to wait for the chip server exit code
        # To avoid excessive attempts, we verify 5 times over the timeout value provided
        # In case the timeout is triggered, the process continues after logging
        sleeping_seconds = CHIP_SERVER_EXIT_TIMEOUT / 5
        timeout = time() + CHIP_SERVER_EXIT_TIMEOUT
        exit_code = self.sdk_container.exec_exit_code(self.__chip_server_id)

        while exit_code is None and time() <= timeout:
            self.logger.info(
                f"Sleeping for {sleeping_seconds} seconds before verifying chip server "
                "exit code again."
            )
            sleep(sleeping_seconds)
            exit_code = self.sdk_container.exec_exit_code(self.__chip_server_id)

        if exit_code is None:
            raise ChipServerExitError("Timeout while waiting to exit chip server")

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
