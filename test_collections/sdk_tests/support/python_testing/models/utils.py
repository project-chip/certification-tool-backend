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

from typing import Generator

import loguru

from app.schemas.test_environment_config import TestEnvironmentConfig
from app.test_engine.logger import PYTHON_TEST_LEVEL
from app.test_engine.logger import test_engine_logger as logger

# Command line params
RUNNER_CLASS_PATH = "/root/python_testing/test_harness_client.py"
EXECUTABLE = "python3"


def generate_command_arguments(
    config: TestEnvironmentConfig, omit_commissioning_method: bool = False
) -> list:
    # All valid arguments for python test
    valid_args = [
        "ble_interface_id",
        "commissioning_method",
        "controller_node_id",
        "discriminator",
        "endpoint",
        "logs_path",
        "PICS",
        "paa_trust_store_path",
        "timeout",
        "trace_to",
        "int_arg",
        "float_arg",
        "string_arg",
        "json_arg",
        "hex_arg",
        "bool_arg",
        "storage_path",
        "passcode",
        "dut_node_id",
        "qr_code",
        "manual_code",
    ]

    dut_config = config.dut_config
    test_parameters = config.test_parameters

    pairing_mode = (
        "on-network"
        if dut_config.pairing_mode == "onnetwork"
        else dut_config.pairing_mode
    )

    arguments = []
    # Retrieve arguments from dut_config
    arguments.append(f"--discriminator {dut_config.discriminator}")
    arguments.append(f"--passcode {dut_config.setup_code}")
    if not omit_commissioning_method:
        arguments.append(f"--commissioning-method {pairing_mode}")

    # Retrieve arguments from test_parameters
    if test_parameters:
        for name, value in test_parameters.items():
            if name in valid_args:
                if str(value) != "":
                    arguments.append(f"--{name.replace('_','-')} {str(value)}")
                else:
                    arguments.append(f"--{name.replace('_','-')} " "")
            else:
                logger.warning(f"Argument {name} is not valid")

    return arguments


def handle_logs(log_generator: Generator, logger: loguru.Logger) -> None:
    for chunk in log_generator:
        decoded_log = chunk.decode().strip()
        log_lines = decoded_log.splitlines()
        for line in log_lines:
            logger.log(PYTHON_TEST_LEVEL, line)
