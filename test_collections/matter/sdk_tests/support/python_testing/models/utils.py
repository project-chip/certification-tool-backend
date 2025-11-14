#
# Copyright (c) 2023-2024 Project CHIP Authors
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

from pathlib import Path
from typing import Generator, cast

import loguru

from app.schemas.test_environment_config import ThreadAutoConfig
from app.test_engine.logger import PYTHON_TEST_LEVEL
from app.user_prompt_support import UserPromptSupport
from test_collections.matter.sdk_tests.support.otbr_manager.otbr_manager import (
    ThreadBorderRouter,
)
from test_collections.matter.test_environment_config import (
    DutPairingModeEnum,
    TestEnvironmentConfigMatter,
    ThreadExternalConfig,
)

from ...sdk_container import SDKContainer
from ...utils import (
    ADMIN_STORAGE_FILE_CONTAINER_DEFAULT_PATH,
    ADMIN_STORAGE_FILE_DEFAULT_NAME,
    ADMIN_STORAGE_FILE_HOST,
    ADMIN_STORAGE_FILE_HOST_PATH,
    PromptOption,
    prompt_reuse_commissioning,
)

# Command line params
RUNNER_CLASS_PATH = "/root/python_testing/scripts/sdk/matter_testing_infrastructure/chip/testing/test_harness_client.py"  # noqa
EXECUTABLE = "python3"

TEST_PARAMETER_STORAGE_PATH_KEY = "storage-path"


async def generate_command_arguments(
    config: TestEnvironmentConfigMatter, omit_commissioning_method: bool = False
) -> list:
    dut_config = config.dut_config
    test_parameters = config.test_parameters

    pairing_mode = (
        "on-network"
        if dut_config.pairing_mode == DutPairingModeEnum.ON_NETWORK
        else dut_config.pairing_mode
    )

    arguments = []
    # Increase log level by adding trace log
    if dut_config.trace_log:
        arguments.append("--trace-to json:log")

    if dut_config.enhanced_setup_flow:
        arguments.append("--require-tc-acknowledgements 1")
        arguments.append(
            f"--tc-acknowledgements {dut_config.enhanced_setup_flow.tc_user_response}"
        )
        arguments.append(
            f"--tc-acknowledgements-version {dut_config.enhanced_setup_flow.tc_version}"
        )

    if omit_commissioning_method:
        arguments.append(f"--in-test-commissioning-method {pairing_mode}")

    else:
        arguments.append(f"--commissioning-method {pairing_mode}")

    if pairing_mode == DutPairingModeEnum.BLE_WIFI:
        arguments.append(f"--wifi-ssid {config.network.wifi.ssid}")
        arguments.append(f"--wifi-passphrase {config.network.wifi.password}")
    elif (
        pairing_mode == DutPairingModeEnum.BLE_THREAD
        or pairing_mode == DutPairingModeEnum.NFC_THREAD
    ):
        dataset_hex = await __thread_dataset_hex(config.network.thread)
        arguments.append(f"--thread-dataset-hex {dataset_hex}")

    # Retrieve arguments from test_parameters
    if test_parameters:
        # If manual-code or qr-code and also discriminator and passcode are provided,
        # the test will think that we're trying to commission 2 DUTs and it will fail
        if (
            "manual-code" not in test_parameters.keys()
            and "qr-code" not in test_parameters.keys()
        ):
            # Retrieve arguments from dut_config
            arguments.append(f"--discriminator {dut_config.discriminator}")
            arguments.append(f"--passcode {dut_config.setup_code}")

        for name, value in test_parameters.items():
            arg_value = str(value) if value is not None else ""
            arguments.append(f"--{name} {arg_value}")
    else:
        # Retrieve arguments from dut_config
        arguments.append(f"--discriminator {dut_config.discriminator}")
        arguments.append(f"--passcode {dut_config.setup_code}")

    return arguments


def handle_logs(log_generator: Generator, logger: loguru.Logger) -> None:
    for chunk in log_generator:
        decoded_log = chunk.decode().strip()
        log_lines = decoded_log.splitlines()
        for line in log_lines:
            logger.log(PYTHON_TEST_LEVEL, line)


class DUTCommissioningError(Exception):
    pass


def __retrieve_storage_path(config: TestEnvironmentConfigMatter) -> Path:
    storage_path = ADMIN_STORAGE_FILE_CONTAINER_DEFAULT_PATH.joinpath(
        ADMIN_STORAGE_FILE_DEFAULT_NAME
    )

    if (
        config.test_parameters
        and TEST_PARAMETER_STORAGE_PATH_KEY in config.test_parameters
        and config.test_parameters[TEST_PARAMETER_STORAGE_PATH_KEY]
    ):
        storage_path = Path(config.test_parameters[TEST_PARAMETER_STORAGE_PATH_KEY])
    return storage_path


def __copy_admin_storage_file(
    config: TestEnvironmentConfigMatter,
    logger: loguru.Logger,
) -> None:
    sdk_container = SDKContainer(logger)

    storage_path = __retrieve_storage_path(config)

    logger.info(f"Copy file '{storage_path}' from container")
    sdk_container.copy_file_from_container(
        container_file_path=Path(storage_path),
        destination_path=ADMIN_STORAGE_FILE_HOST_PATH,
        destination_file_name=ADMIN_STORAGE_FILE_DEFAULT_NAME,
    )


async def commission_device(
    config: TestEnvironmentConfigMatter,
    logger: loguru.Logger,
) -> None:
    sdk_container = SDKContainer(logger)

    command = [f"{RUNNER_CLASS_PATH} commission"]
    command_arguments = await generate_command_arguments(config)
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

    # Copy admin_storage.json file from container, in case the user wants to
    # reuse this information in the next execution
    __copy_admin_storage_file(config, logger)


async def __thread_dataset_hex(
    thread_config: ThreadAutoConfig | ThreadExternalConfig,
) -> str:
    hex_dataset = ""

    if isinstance(thread_config, ThreadExternalConfig):
        hex_dataset = thread_config.operational_dataset_hex
    elif isinstance(thread_config, ThreadAutoConfig):
        border_router: ThreadBorderRouter = ThreadBorderRouter()

        # Expecting false as the OTBR is started in the suite's setup.
        # Either way, if true, we try to start and configure the container in case
        # there's no OTBR application running.
        if await border_router.start_device(thread_config):
            await border_router.form_thread_topology()

        hex_dataset = border_router.active_dataset

    return hex_dataset


async def should_perform_new_commissioning(
    prompt_support: UserPromptSupport,
    config: TestEnvironmentConfigMatter,
    logger: loguru.Logger,
) -> bool:
    sdk_container = SDKContainer(logger)

    # If the admin storage file exists, prompt user if the execution should retrieve
    # the previous commissioning information or if it should perform a
    # new commissioning
    if ADMIN_STORAGE_FILE_HOST.exists():
        user_response = await prompt_reuse_commissioning(prompt_support, logger)
        if user_response == PromptOption.PASS:
            logger.info(f"Copying file {str(ADMIN_STORAGE_FILE_HOST)} to container")

            storage_path = __retrieve_storage_path(config)

            sdk_container.copy_file_to_container(
                host_file_path=ADMIN_STORAGE_FILE_HOST,
                destination_container_path=storage_path,
            )
            return False

    return True
