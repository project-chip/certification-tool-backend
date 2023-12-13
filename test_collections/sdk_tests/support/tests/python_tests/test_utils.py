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

import pytest

from app.default_environment_config import default_environment_config
from app.schemas.test_environment_config import DutConfig, DutPairingModeEnum
from test_collections.sdk_tests.support.python_testing.models.utils import (
    generate_command_arguments,
)


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
        "--discriminator 456",
        "--passcode 8765",
    ] == arguments
