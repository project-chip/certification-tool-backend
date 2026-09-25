#
# Copyright (c) 2023-2026 Project CHIP Authors
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

import hashlib
import json
import os
from pathlib import Path
from typing import Generator, cast

import loguru

from app.constants.shared_constants import DutPairingModeEnum
from app.schemas.test_environment_config import ThreadAutoConfig
from app.test_engine.logger import PYTHON_TEST_LEVEL
from app.user_prompt_support import UserPromptSupport
from test_collections.matter.sdk_tests.support.otbr_manager.otbr_manager import (
    ThreadBorderRouter,
)
from test_collections.matter.test_environment_config import (
    TestEnvironmentConfigMatter,
    ThreadExternalConfig,
)

from ...sdk_container import SDKContainer
from ...utils import (
    ADMIN_STORAGE_FILE_CONTAINER_DEFAULT_PATH,
    ADMIN_STORAGE_FILE_DEFAULT_NAME,
    ADMIN_STORAGE_FILE_HOST,
    ADMIN_STORAGE_FILE_HOST_PATH,
    THREAD_ACTIVE_DATASET_FILE_HOST,
    PromptOption,
    prompt_reuse_commissioning,
)

# Command line params
RUNNER_CLASS_PATH = "/root/python_testing/scripts/sdk/matter_testing_infrastructure/chip/testing/test_harness_client.py"  # noqa
EXECUTABLE = "python3"

# Test output file path relative to sdk_tests directory
TEST_OUTPUT_FILE_PATH = "sdk_checkout/python_testing/test_output.txt"

TEST_PARAMETER_STORAGE_PATH_KEY = "storage-path"

NFC_PAIRING_MODES = {
    DutPairingModeEnum.NFC_WIFI.value,
    DutPairingModeEnum.NFC_THREAD.value,
}

THREAD_PAIRING_MODES = {
    DutPairingModeEnum.BLE_THREAD,
    DutPairingModeEnum.NFC_THREAD,
    DutPairingModeEnum.THREAD_MESHCOP,
}

# Typed SDK argument flags that accept NAME:VALUE pairs and require special
# handling to survive the container shell without mangling.
_SPLIT_ARGS = {"json-arg", "string-arg", "int-arg", "float-arg", "bool-arg", "hex-arg"}

# Characters that trigger shell brace expansion or word splitting.
_SHELL_SPECIAL = set("{[}\"'")


async def generate_command_arguments(
    config: TestEnvironmentConfigMatter, omit_commissioning_method: bool = False
) -> list:
    dut_config = config.dut_config
    test_parameters = config.test_parameters

    # Map TH pairing modes to SDK commissioning method names
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

    if pairing_mode in (DutPairingModeEnum.BLE_WIFI, DutPairingModeEnum.NFC_WIFI):
        arguments.append(f"--wifi-ssid {config.network.wifi.ssid}")
        arguments.append(f"--wifi-passphrase {config.network.wifi.password}")
    elif pairing_mode in (
        DutPairingModeEnum.BLE_THREAD,
        DutPairingModeEnum.NFC_THREAD,
        DutPairingModeEnum.THREAD_MESHCOP,
    ):
        dataset_hex = await __thread_dataset_hex(config.network.thread)
        arguments.append(f"--thread-dataset-hex {dataset_hex}")

        # Add Border Agent parameters for THREAD_MESHCOP
        if pairing_mode == DutPairingModeEnum.THREAD_MESHCOP:
            thread_config = config.network.thread
            if thread_config.ba_host:
                arguments.append(f"--thread-ba-host {thread_config.ba_host}")
            if thread_config.ba_port:
                arguments.append(f"--thread-ba-port {thread_config.ba_port}")

    # NFC pairing modes don't need discriminator and passcode in the arguments,
    # since it is provided directly by the NFC tag.
    # Also, if manual-code or qr-code and also discriminator and passcode are provided,
    # the test will think that we're trying to commission 2 DUTs and it will fail
    if (
        pairing_mode not in NFC_PAIRING_MODES
        and ("manual-code" not in test_parameters.keys() if test_parameters else True)
        and ("qr-code" not in test_parameters.keys() if test_parameters else True)
    ):
        # Retrieve arguments from dut_config
        arguments.append(f"--discriminator {dut_config.discriminator}")
        arguments.append(f"--passcode {dut_config.setup_code}")

    # Retrieve arguments from test_parameters.
    # Typed SDK args (--json-arg, --string-arg, etc.) may contain special
    # characters such as braces and quotes that the container shell would
    # mangle if embedded in a single string token.
    # Emit the flag and each NAME:VALUE pair as separate list entries.
    # Single-quote pairs that contain shell-special characters so the
    # container shell does not perform brace expansion or word splitting.
    # json-arg is always a single NAME:JSON token — never split on spaces,
    # as the JSON value itself may contain spaces.
    # Other typed args (int-arg, string-arg, etc.) use plain NAME:VALUE pairs
    # with no spaces, so splitting on spaces is safe for them.
    if test_parameters:
        for name, value in test_parameters.items():
            if isinstance(value, (dict, list)):
                arg_value = json.dumps(value, separators=(",", ":"))
            elif value is not None:
                arg_value = str(value)
            else:
                arg_value = ""
            if name in _SPLIT_ARGS:
                arguments.append(f"--{name}")
                pairs = [arg_value] if name == "json-arg" else arg_value.split(" ")
                for pair in pairs:
                    if pair:
                        if any(c in pair for c in _SHELL_SPECIAL):
                            arguments.append(f"'{pair}'")
                        else:
                            arguments.append(pair)
            else:
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
    if ADMIN_STORAGE_FILE_HOST.exists():
        ADMIN_STORAGE_FILE_HOST.chmod(0o600)


def _normalize_thread_active_dataset(dataset: bytes | str) -> bytes:
    if isinstance(dataset, bytes):
        normalized = dataset
    else:
        try:
            normalized = bytes.fromhex(dataset.strip())
        except ValueError as error:
            raise DUTCommissioningError("Invalid Thread Active Dataset") from error

    if not normalized:
        raise DUTCommissioningError("Thread Active Dataset is empty")
    return normalized


def _thread_dataset_fingerprint(dataset: bytes) -> str:
    return hashlib.sha256(dataset).hexdigest()


def load_persisted_thread_active_dataset(logger: loguru.Logger) -> bytes:
    try:
        dataset = _normalize_thread_active_dataset(
            THREAD_ACTIVE_DATASET_FILE_HOST.read_text(encoding="ascii")
        )
    except OSError as error:
        raise DUTCommissioningError(
            "Could not read persisted Thread Active Dataset"
        ) from error

    logger.info(
        "Loaded Thread Active Dataset fingerprint: "
        + _thread_dataset_fingerprint(dataset)
    )
    return dataset


def persist_thread_active_dataset(dataset: bytes, logger: loguru.Logger) -> None:
    normalized = _normalize_thread_active_dataset(dataset)
    temporary_path = THREAD_ACTIVE_DATASET_FILE_HOST.with_suffix(".hex.tmp")

    try:
        descriptor = os.open(
            temporary_path,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o600,
        )
        with os.fdopen(descriptor, "w", encoding="ascii") as dataset_file:
            dataset_file.write(normalized.hex())
            dataset_file.write("\n")
        os.replace(temporary_path, THREAD_ACTIVE_DATASET_FILE_HOST)
        THREAD_ACTIVE_DATASET_FILE_HOST.chmod(0o600)
    finally:
        temporary_path.unlink(missing_ok=True)

    logger.info(
        "Persisted Thread Active Dataset fingerprint: "
        + _thread_dataset_fingerprint(normalized)
    )


def uses_managed_thread_network(config: TestEnvironmentConfigMatter) -> bool:
    return config.dut_config.pairing_mode in THREAD_PAIRING_MODES and isinstance(
        config.network.thread, ThreadAutoConfig
    )


def invalidate_reusable_commissioning_state(
    config: TestEnvironmentConfigMatter, logger: loguru.Logger
) -> None:
    paths = [ADMIN_STORAGE_FILE_HOST]
    if uses_managed_thread_network(config):
        paths.append(THREAD_ACTIVE_DATASET_FILE_HOST)

    for path in paths:
        if path.exists():
            path.unlink()
            logger.info(f"Removed stale reusable commissioning state: {path.name}")


def _managed_thread_reuse_bundle_is_valid(
    config: TestEnvironmentConfigMatter, logger: loguru.Logger
) -> bool:
    has_admin_storage = ADMIN_STORAGE_FILE_HOST.exists()
    has_thread_dataset = THREAD_ACTIVE_DATASET_FILE_HOST.exists()
    if has_admin_storage != has_thread_dataset:
        logger.warning(
            "Reusable Thread commissioning state is incomplete; "
            "new commissioning is required"
        )
        invalidate_reusable_commissioning_state(config, logger)
        return False

    if not has_admin_storage:
        return False

    try:
        persisted_dataset = load_persisted_thread_active_dataset(logger)
        thread_config = config.network.thread
        assert isinstance(thread_config, ThreadAutoConfig)
        if thread_config.operational_dataset_hex is not None:
            configured_dataset = _normalize_thread_active_dataset(
                thread_config.operational_dataset_hex
            )
            if persisted_dataset != configured_dataset:
                raise DUTCommissioningError(
                    "Configured and persisted Thread Active Datasets differ"
                )
    except DUTCommissioningError as error:
        logger.warning(f"Reusable Thread commissioning state is invalid: {error}")
        invalidate_reusable_commissioning_state(config, logger)
        return False

    return True


def capture_admin_storage_file(
    config: TestEnvironmentConfigMatter,
    logger: loguru.Logger,
) -> None:
    """Re-capture admin_storage.json from the still-running container to the host
    snapshot, so the snapshot reflects the message counters as they stood at the end
    of this run rather than only as they stood right after the last commissioning.
    """
    __copy_admin_storage_file(config, logger)


def log_test_output_file(logger: loguru.Logger) -> None:
    """Log the entire content of test_output.txt file.

    Args:
        logger: Logger instance to write logs to
    """
    try:
        # Navigate up 3 levels from utils.py to sdk_tests directory
        sdk_tests_path = next(
            (p for p in Path(__file__).resolve().parents if p.name == "sdk_tests"),
            Path(__file__).parents[3],
        )
        file_output_path = sdk_tests_path / TEST_OUTPUT_FILE_PATH

        if file_output_path.exists():
            with open(file_output_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                if content.strip():  # Only log if there's actual content
                    logger.log(PYTHON_TEST_LEVEL, content)
        else:
            logger.debug(f"test_output.txt not found at {file_output_path}")
    except (OSError, IndexError) as e:
        logger.warning(f"Could not read test_output.txt: {e}")


async def commission_device(
    config: TestEnvironmentConfigMatter,
    logger: loguru.Logger,
) -> None:
    sdk_container = SDKContainer(logger)

    command = [f"{RUNNER_CLASS_PATH} --commission"]
    command_arguments = await generate_command_arguments(config)
    command.extend(command_arguments)

    exec_result = sdk_container.send_command(
        command,
        prefix=EXECUTABLE,
        is_stream=True,
        is_socket=False,
        sensitive=True,
    )

    handle_logs(cast(Generator, exec_result.output), logger)

    exit_code = sdk_container.exec_exit_code(exec_result.exec_id)

    if exit_code:
        raise DUTCommissioningError("Failed to commission DUT")

    # Print all content from test_output.txt file after commissioning
    logger.info("---- Start of commissioning test output ----")
    log_test_output_file(logger)
    logger.info("---- End of commissioning test output ----")

    # Copy admin_storage.json file from container, in case the user wants to
    # reuse this information in the next execution. This duplicates the capture
    # PythonTestSuite.cleanup() does unconditionally at the end of the suite run,
    # but is kept intentionally: if the container is torn down abnormally before
    # cleanup() runs, this is the only snapshot that survives.
    __copy_admin_storage_file(config, logger)


async def __thread_dataset_hex(
    thread_config: ThreadAutoConfig | ThreadExternalConfig,
) -> str:
    hex_dataset = ""

    if isinstance(thread_config, ThreadExternalConfig):
        hex_dataset = thread_config.operational_dataset_hex
    elif isinstance(thread_config, ThreadAutoConfig):
        border_router: ThreadBorderRouter = ThreadBorderRouter()

        # Expecting false as the OTBR is started in the suite's setup. If the
        # container is unexpectedly absent, restore the configured dataset or form
        # one and use only the verified live value.
        if await border_router.start_device(thread_config):
            configured_dataset = (
                _normalize_thread_active_dataset(thread_config.operational_dataset_hex)
                if thread_config.operational_dataset_hex
                else None
            )
            await border_router.form_thread_topology(configured_dataset)

        hex_dataset = border_router.active_dataset

    return hex_dataset


async def should_perform_new_commissioning(
    prompt_support: UserPromptSupport,
    config: TestEnvironmentConfigMatter,
    logger: loguru.Logger,
) -> bool:
    sdk_container = SDKContainer(logger)

    if uses_managed_thread_network(config):
        if not _managed_thread_reuse_bundle_is_valid(config, logger):
            return True

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
        else:
            invalidate_reusable_commissioning_state(config, logger)
    return True
