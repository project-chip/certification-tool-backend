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

from unittest import mock

import pytest

from app.default_environment_config import default_environment_config
from app.schemas.test_environment_config import DutConfig, DutPairingModeEnum
from app.test_engine.logger import test_engine_logger

from ...exec_run_in_container import ExecResultExtended
from ...python_testing.models.utils import (
    EXECUTABLE,
    RUNNER_CLASS_PATH,
    DUTCommissioningError,
    commission_device,
    generate_command_arguments,
)
from ...sdk_container import SDKContainer


@pytest.mark.asyncio
async def test_generate_command_arguments_with_null_value_attribute() -> None:
    # Mock config
    mock_config = default_environment_config.copy(deep=True)

    mock_config.test_parameters = {"test-argument": None}

    mock_dut_config = DutConfig(
        discriminator="123",
        setup_code="1234",
        pairing_mode=DutPairingModeEnum.ON_NETWORK,
    )

    mock_config.dut_config = mock_dut_config

    arguments = generate_command_arguments(
        config=mock_config, omit_commissioning_method=False
    )

    assert [
        "--trace-to json:log",
        "--discriminator 123",
        "--passcode 1234",
        "--commissioning-method on-network",
        "--test-argument ",
    ] == arguments


@pytest.mark.asyncio
async def test_generate_command_arguments_on_network() -> None:
    # Mock config
    mock_config = default_environment_config.copy(deep=True)

    # Using attributes with both - and _ word separators in test_parameters
    # Both must be considered as python test arguments the way it was configured
    mock_config.test_parameters = {
        "paa-trust-store-path": "/paa-root-certs",
        "storage_path": "/root/admin_storage.json",
    }

    mock_dut_config = DutConfig(
        discriminator="123",
        setup_code="1234",
        pairing_mode=DutPairingModeEnum.ON_NETWORK,
    )

    mock_config.dut_config = mock_dut_config

    arguments = generate_command_arguments(
        config=mock_config, omit_commissioning_method=False
    )

    assert [
        "--trace-to json:log",
        "--discriminator 123",
        "--passcode 1234",
        "--commissioning-method on-network",
        "--paa-trust-store-path /paa-root-certs",
        "--storage_path /root/admin_storage.json",
    ] == arguments


@pytest.mark.asyncio
async def test_generate_command_arguments_ble_wifi() -> None:
    # Mock config
    mock_config = default_environment_config.copy(deep=True)

    mock_config.test_parameters = {
        "paa-trust-store-path": "/paa-root-certs",
        "storage_path": "/root/admin_storage.json",
    }

    mock_dut_config = DutConfig(
        discriminator="147",
        setup_code="357",
        pairing_mode=DutPairingModeEnum.BLE_WIFI,
    )

    mock_config.dut_config = mock_dut_config

    arguments = generate_command_arguments(
        config=mock_config, omit_commissioning_method=False
    )

    assert [
        "--trace-to json:log",
        "--discriminator 147",
        "--passcode 357",
        "--commissioning-method ble-wifi",
        "--paa-trust-store-path /paa-root-certs",
        "--storage_path /root/admin_storage.json",
    ] == arguments


@pytest.mark.asyncio
async def test_generate_command_arguments_ble_thread() -> None:
    # Mock config
    mock_config = default_environment_config.copy(deep=True)

    mock_config.test_parameters = {
        "paa-trust-store-path": "/paa-root-certs",
        "storage_path": "/root/admin_storage.json",
    }

    mock_dut_config = DutConfig(
        discriminator="456",
        setup_code="8765",
        pairing_mode=DutPairingModeEnum.BLE_THREAD,
    )

    mock_config.dut_config = mock_dut_config

    arguments = generate_command_arguments(
        config=mock_config, omit_commissioning_method=False
    )
    assert [
        "--trace-to json:log",
        "--discriminator 456",
        "--passcode 8765",
        "--commissioning-method ble-thread",
        "--paa-trust-store-path /paa-root-certs",
        "--storage_path /root/admin_storage.json",
    ] == arguments


@pytest.mark.asyncio
async def test_generate_command_arguments_no_test_parameter_informed() -> None:
    # Mock config
    mock_config = default_environment_config.copy(deep=True)

    mock_config.test_parameters = None

    mock_dut_config = DutConfig(
        discriminator="456",
        setup_code="8765",
        pairing_mode=DutPairingModeEnum.BLE_THREAD,
    )

    mock_config.dut_config = mock_dut_config

    arguments = generate_command_arguments(
        config=mock_config, omit_commissioning_method=False
    )

    assert [
        "--trace-to json:log",
        "--discriminator 456",
        "--passcode 8765",
        "--commissioning-method ble-thread",
    ] == arguments


@pytest.mark.asyncio
async def test_generate_command_arguments_omit_comissioning_method() -> None:
    # Mock config
    mock_config = default_environment_config.copy(deep=True)

    mock_dut_config = DutConfig(
        discriminator="456",
        setup_code="8765",
        pairing_mode=DutPairingModeEnum.ON_NETWORK,
    )

    mock_config.dut_config = mock_dut_config

    arguments = generate_command_arguments(
        config=mock_config, omit_commissioning_method=True
    )

    assert [
        "--trace-to json:log",
        "--discriminator 456",
        "--passcode 8765",
    ] == arguments


@pytest.mark.asyncio
async def test_commission_device() -> None:
    sdk_container: SDKContainer = SDKContainer()

    command_args = ["arg1", "arg2", "arg3"]
    expected_command = [f"{RUNNER_CLASS_PATH} commission"]
    expected_command.extend(command_args)
    mock_result = ExecResultExtended(0, "log output".encode(), "ID", mock.MagicMock())

    with mock.patch.object(
        target=sdk_container, attribute="send_command", return_value=mock_result
    ) as mock_send_command, mock.patch(
        target="test_collections.matter.sdk_tests.support.python_testing.models.utils"
        ".generate_command_arguments",
        return_value=command_args,
    ), mock.patch(
        target="test_collections.matter.sdk_tests.support.python_testing.models.utils"
        ".handle_logs"
    ) as mock_handle_logs, mock.patch.object(
        target=sdk_container, attribute="exec_exit_code", return_value=0
    ):
        commission_device(default_environment_config, test_engine_logger)

    mock_send_command.assert_called_once_with(
        expected_command, prefix=EXECUTABLE, is_stream=True, is_socket=False
    )
    mock_handle_logs.assert_called_once()


@pytest.mark.asyncio
async def test_commission_device_failure() -> None:
    sdk_container: SDKContainer = SDKContainer()

    command_args = ["arg1", "arg2", "arg3"]
    expected_command = [f"{RUNNER_CLASS_PATH} commission"]
    expected_command.extend(command_args)
    mock_result = ExecResultExtended(0, "log output".encode(), "ID", mock.MagicMock())

    with mock.patch.object(
        target=sdk_container, attribute="send_command", return_value=mock_result
    ) as mock_send_command, mock.patch(
        target="test_collections.matter.sdk_tests.support.python_testing.models.utils"
        ".generate_command_arguments",
        return_value=command_args,
    ), mock.patch(
        target="test_collections.matter.sdk_tests.support.python_testing.models.utils"
        ".handle_logs"
    ) as mock_handle_logs, mock.patch.object(
        target=sdk_container, attribute="exec_exit_code", return_value=1
    ), pytest.raises(
        DUTCommissioningError
    ):
        commission_device(default_environment_config, test_engine_logger)

    mock_send_command.assert_called_once_with(
        expected_command, prefix=EXECUTABLE, is_stream=True, is_socket=False
    )
    mock_handle_logs.assert_called_once()
