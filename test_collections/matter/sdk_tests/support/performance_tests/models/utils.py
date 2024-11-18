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

from typing import Generator, cast

import loguru

from app.schemas.test_environment_config import TestEnvironmentConfig
from app.test_engine.logger import PYTHON_TEST_LEVEL

from ...sdk_container import SDKContainer

# Command line params
RUNNER_CLASS_PATH = "/root/python_testing/scripts/sdk/test_harness_client.py"
EXECUTABLE = "python3"


def generate_command_arguments(
    config: TestEnvironmentConfig, omit_commissioning_method: bool = False
) -> list:
    dut_config = config.dut_config  # type: ignore[attr-defined]
    test_parameters = config.test_parameters

    pairing_mode = (
        "on-network"
        if dut_config.pairing_mode == "onnetwork"
        else dut_config.pairing_mode
    )

    arguments = []
    # Increase log level by adding trace log
    if dut_config.trace_log:
        arguments.append("--trace-to json:log")
    # Retrieve arguments from dut_config
    arguments.append(f"--discriminator {dut_config.discriminator}")
    arguments.append(f"--passcode {dut_config.setup_code}")
    if not omit_commissioning_method:
        arguments.append(f"--commissioning-method {pairing_mode}")

    # Retrieve arguments from test_parameters
    if test_parameters:
        for name, value in test_parameters.items():
            arg_value = str(value) if value is not None else ""
            arguments.append(f"--{name} {arg_value}")

    return arguments


def handle_logs(log_generator: Generator, logger: loguru.Logger) -> None:
    for chunk in log_generator:
        decoded_log = chunk.decode().strip()
        log_lines = decoded_log.splitlines()
        for line in log_lines:
            logger.log(PYTHON_TEST_LEVEL, line)


class DUTCommissioningError(Exception):
    pass


def commission_device(
    config: TestEnvironmentConfig,
    logger: loguru.Logger,
) -> None:
    sdk_container: SDKContainer = SDKContainer()

    command = [f"{RUNNER_CLASS_PATH} commission"]
    command_arguments = generate_command_arguments(config)
    command.extend(command_arguments)

    exec_result = sdk_container.send_command(
        command,
        prefix=EXECUTABLE,
        is_stream=True,
        is_socket=False,
    )

    handle_logs(cast(Generator, exec_result.output), logger)

    exit_code = sdk_container.exec_exit_code(exec_result.exec_id)

    if exit_code:
        raise DUTCommissioningError("Failed to commission DUT")
