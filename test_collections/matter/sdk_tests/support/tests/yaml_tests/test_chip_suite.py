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
# type: ignore
# Ignore mypy type check for this file
# flake8: noqa

from unittest import mock

import pytest

from app.models.test_suite_execution import TestSuiteExecution
from app.user_prompt_support.constants import UserResponseStatusEnum
from app.user_prompt_support.prompt_response import PromptResponse
from test_collections.matter.sdk_tests.support.otbr_manager.otbr_manager import (
    ThreadBorderRouter,
)
from test_collections.matter.test_environment_config import (
    TestEnvironmentConfigMatter,
    ThreadExternalConfig,
)

from ...yaml_tests.models.chip_suite import (
    ChipSuite,
    DUTCommissioningError,
    SuiteSetupError,
)
from ...yaml_tests.models.chip_test import PromptOption

RETRY_PROMPT_RESPONSE = PromptResponse(
    response=PromptOption.RETRY, status_code=UserResponseStatusEnum.OKAY
)
CANCEL_PROMPT_RESPONSE = PromptResponse(
    response=PromptOption.CANCEL, status_code=UserResponseStatusEnum.OKAY
)
UNEXPECTED_PROMPT_RESPONSE = PromptResponse(
    response="unexpected", status_code=UserResponseStatusEnum.INVALID
)


@pytest.mark.asyncio
async def test_test_suite_commission_dut_allowing_retries_success() -> None:
    test_suite = ChipSuite(TestSuiteExecution())

    with mock.patch.object(
        target=test_suite,
        attribute="_ChipSuite__pair_with_dut",
        side_effect=None,
    ) as mock_pair_with_dut, mock.patch.object(
        target=test_suite,
        attribute="send_prompt_request",
        return_value=None,
    ) as mock_send_prompt_request:
        await test_suite._ChipSuite__commission_dut_allowing_retries()

        mock_pair_with_dut.assert_called_once()
        mock_send_prompt_request.assert_not_called()
        assert test_suite._ChipSuite__dut_commissioned_successfully is True


@pytest.mark.asyncio
async def test_test_suite_commission_dut_allowing_retries_retry_success() -> None:
    test_suite = ChipSuite(TestSuiteExecution())

    with mock.patch.object(
        target=test_suite,
        attribute="_ChipSuite__pair_with_dut",
        side_effect=[
            DUTCommissioningError(),
            DUTCommissioningError(),
            DUTCommissioningError(),
            None,
        ],
    ) as mock_pair_with_dut, mock.patch.object(
        target=test_suite,
        attribute="send_prompt_request",
        side_effect=[
            RETRY_PROMPT_RESPONSE,
            RETRY_PROMPT_RESPONSE,
            RETRY_PROMPT_RESPONSE,
        ],
    ) as mock_send_prompt_request:
        await test_suite._ChipSuite__commission_dut_allowing_retries()

        # __pair_with_dut should be called 3 times with an error and once with success
        assert mock_pair_with_dut.call_count == 4
        # mock_send_prompt_request should be called once for each error
        assert mock_send_prompt_request.call_count == 3
        assert test_suite._ChipSuite__dut_commissioned_successfully is True


@pytest.mark.asyncio
async def test_test_suite_commission_dut_allowing_retries_retry_cancel() -> None:
    test_suite = ChipSuite(TestSuiteExecution())

    with mock.patch.object(
        target=test_suite,
        attribute="_ChipSuite__pair_with_dut",
        side_effect=[
            DUTCommissioningError(),
            DUTCommissioningError(),
            DUTCommissioningError(),
        ],
    ) as mock_pair_with_dut, mock.patch.object(
        target=test_suite,
        attribute="send_prompt_request",
        side_effect=[
            RETRY_PROMPT_RESPONSE,
            RETRY_PROMPT_RESPONSE,
            CANCEL_PROMPT_RESPONSE,
        ],
    ) as mock_send_prompt_request:
        with pytest.raises(SuiteSetupError):
            await test_suite._ChipSuite__commission_dut_allowing_retries()

        # __pair_with_dut should be called 3 times with an error
        assert mock_pair_with_dut.call_count == 3
        # mock_send_prompt_request should be called once for each error
        assert mock_send_prompt_request.call_count == 3
        assert test_suite._ChipSuite__dut_commissioned_successfully is False


@pytest.mark.asyncio
async def test_test_suite_commission_dut_allowing_retries_retry_unexpected() -> None:
    test_suite = ChipSuite(TestSuiteExecution())

    with mock.patch.object(
        target=test_suite,
        attribute="_ChipSuite__pair_with_dut",
        side_effect=[
            DUTCommissioningError(),
            DUTCommissioningError(),
            DUTCommissioningError(),
        ],
    ) as mock_pair_with_dut, mock.patch.object(
        target=test_suite,
        attribute="send_prompt_request",
        side_effect=[
            RETRY_PROMPT_RESPONSE,
            RETRY_PROMPT_RESPONSE,
            UNEXPECTED_PROMPT_RESPONSE,
        ],
    ) as mock_send_prompt_request:
        with pytest.raises(ValueError):
            await test_suite._ChipSuite__commission_dut_allowing_retries()

        # __pair_with_dut should be called 3 times with an error
        assert mock_pair_with_dut.call_count == 3
        # mock_send_prompt_request should be called once for each error
        assert mock_send_prompt_request.call_count == 3
        assert test_suite._ChipSuite__dut_commissioned_successfully is False


@pytest.mark.asyncio
async def test_pair_with_dut_thread_with_external_config_success() -> None:
    """Test pairing with THREAD mode using ThreadExternalConfig."""

    test_suite = ChipSuite(TestSuiteExecution())

    # Create a mock config with ThreadExternalConfig
    config_dict = {
        "network": {
            "fabric_id": "0",
            "thread": {
                "operational_dataset_hex": "0e080000000000010000000300001335060004001ff"
                "fe00208fedcba9876543210070800000000000000050800000000000000030d4f70656"
                "e54687265616444656d6f01021234041011223344556677889900aabbccddeeff000c0"
                "402a0f7f8",
                "ba_host": "127.0.0.1",
                "ba_port": 5684,
            },
            "wifi": {"ssid": "testharness", "password": "wifi-password"},
        },
        "dut_config": {
            "pairing_mode": "thread-meshcop",
            "setup_code": "20202021",
            "discriminator": "3840",
            "chip_use_paa_certs": False,
            "trace_log": True,
        },
        "test_parameters": None,
    }

    # Set the private config_matter attribute directly
    test_suite._ChipSuite__config_matter = TestEnvironmentConfigMatter(**config_dict)

    with mock.patch.object(
        target=test_suite.runner.chip_server,
        attribute="generate_manual_pairing_code_with_chip_tool",
        return_value="MT:ABC123",
    ) as mock_gen_code, mock.patch.object(
        target=test_suite.runner,
        attribute="pairing_thread",
        return_value=True,
    ) as mock_pairing_thread, mock.patch(
        "test_collections.matter.sdk_tests.support.yaml_tests.models.chip_suite"
        ".settings.ENABLE_CONTAINER_LOGS",
        False,
    ):
        result = await test_suite._ChipSuite__pair_with_dut_thread()

    assert result is True
    mock_gen_code.assert_called_once_with(
        discriminator="3840",
        setup_pin_code="20202021",
        enable_container_logs=False,
    )
    mock_pairing_thread.assert_called_once_with(
        hex_dataset="0e080000000000010000000300001335060004001fffe002"
        "08fedcba9876543210070800000000000000050800000000000000030d4f70656e546872656164"
        "44656d6f01021234041011223344556677889900aabbccddeeff000c0402a0f7f8",
        payload="MT:ABC123",
        ba_host="127.0.0.1",
        ba_port=5684,
    )


@pytest.mark.asyncio
async def test_pair_with_dut_thread_with_auto_config_success() -> None:
    """Test pairing with THREAD mode using ThreadAutoConfig."""

    test_suite = ChipSuite(TestSuiteExecution())

    # Create a mock config with ThreadAutoConfig
    config_dict = {
        "network": {
            "fabric_id": "0",
            "thread": {
                "dataset": {
                    "channel": "15",
                    "panid": "0x1234",
                    "extpanid": "1111111122222222",
                    "networkkey": "00112233445566778899aabbccddeeff",
                    "networkname": "DEMO",
                },
                "rcp_serial_path": "/dev/ttyACM0",
                "rcp_baudrate": 115200,
                "on_mesh_prefix": "fd11:22::/64",
                "network_interface": "eth0",
                "ba_host": "127.0.0.1",
                "ba_port": 5684,
            },
            "wifi": {"ssid": "testharness", "password": "wifi-password"},
        },
        "dut_config": {
            "pairing_mode": "thread-meshcop",
            "setup_code": "20202021",
            "discriminator": "3840",
            "chip_use_paa_certs": False,
            "trace_log": True,
        },
        "test_parameters": None,
    }

    test_suite._ChipSuite__config_matter = TestEnvironmentConfigMatter(**config_dict)

    # Mock border router
    mock_border_router = mock.MagicMock(spec=ThreadBorderRouter)
    mock_border_router.active_dataset = "c0ffee123456"
    mock_border_router.start_device = mock.AsyncMock(return_value=True)
    mock_border_router.form_thread_topology = mock.AsyncMock()

    with mock.patch(
        "test_collections.matter.sdk_tests.support.yaml_tests.models.chip_suite."
        "ThreadBorderRouter",
        return_value=mock_border_router,
    ), mock.patch.object(
        target=test_suite.runner.chip_server,
        attribute="generate_manual_pairing_code_with_chip_tool",
        return_value="MT:ABC123",
    ) as mock_gen_code, mock.patch.object(
        target=test_suite.runner,
        attribute="pairing_thread",
        return_value=True,
    ) as mock_pairing_thread, mock.patch(
        "test_collections.matter.sdk_tests.support.yaml_tests.models.chip_suite"
        ".settings.ENABLE_CONTAINER_LOGS",
        False,
    ):
        result = await test_suite._ChipSuite__pair_with_dut_thread()

    assert result is True
    mock_border_router.start_device.assert_awaited_once()
    mock_border_router.form_thread_topology.assert_awaited_once()
    mock_gen_code.assert_called_once_with(
        discriminator="3840",
        setup_pin_code="20202021",
        enable_container_logs=False,
    )
    mock_pairing_thread.assert_called_once_with(
        hex_dataset="c0ffee123456",
        payload="MT:ABC123",
        ba_host="127.0.0.1",
        ba_port=5684,
    )


@pytest.mark.asyncio
async def test_pair_with_dut_thread_missing_thread_config_fails() -> None:
    """Test that pairing fails when thread config is missing."""

    test_suite = ChipSuite(TestSuiteExecution())

    # Create a valid config first (with thread config), then set to None
    config_dict = {
        "network": {
            "fabric_id": "0",
            "thread": {
                "operational_dataset_hex": "0e080000000000010000000300001335060004001ff"
                "fe00208fedcba9876543210070800000000000000050800000000000000030d4f70656"
                "e54687265616444656d6f01021234041011223344556677889900aabbccddeeff000c0"
                "402a0f7f8",
                "ba_host": "127.0.0.1",
                "ba_port": 5684,
            },
            "wifi": {"ssid": "testharness", "password": "wifi-password"},
        },
        "dut_config": {
            "pairing_mode": "thread-meshcop",
            "setup_code": "20202021",
            "discriminator": "3840",
            "chip_use_paa_certs": False,
            "trace_log": True,
        },
        "test_parameters": None,
    }

    test_suite._ChipSuite__config_matter = TestEnvironmentConfigMatter(**config_dict)
    # Set thread to None directly on the private attribute
    test_suite._ChipSuite__config_matter.network.thread = None

    with pytest.raises(DUTCommissioningError) as exc_info:
        await test_suite._ChipSuite__pair_with_dut_thread()

    assert "Tool config is missing thread config" in str(exc_info.value)


@pytest.mark.asyncio
async def test_pair_with_dut_thread_invalid_thread_config_type_fails() -> None:
    """Test that pairing fails when thread config is invalid type."""

    test_suite = ChipSuite(TestSuiteExecution())

    # Create a mock config
    config_dict = {
        "network": {
            "fabric_id": "0",
            "thread": {
                "operational_dataset_hex": "0e080000000000010000000300001335060004001ff"
                "fe00208fedcba9876543210070800000000000000050800000000000000030d4f70656"
                "e54687265616444656d6f01021234041011223344556677889900aabbccddeeff000c0"
                "402a0f7f8",
                "ba_host": "127.0.0.1",
                "ba_port": 5684,
            },
            "wifi": {"ssid": "testharness", "password": "wifi-password"},
        },
        "dut_config": {
            "pairing_mode": "thread-meshcop",
            "setup_code": "20202021",
            "discriminator": "3840",
            "chip_use_paa_certs": False,
            "trace_log": True,
        },
        "test_parameters": None,
    }

    test_suite._ChipSuite__config_matter = TestEnvironmentConfigMatter(**config_dict)
    # Replace with invalid type directly on the private attribute
    test_suite._ChipSuite__config_matter.network.thread = "invalid_type"

    with pytest.raises(DUTCommissioningError) as exc_info:
        await test_suite._ChipSuite__pair_with_dut_thread()

    assert "Invalid thread configuration" in str(exc_info.value)


@pytest.mark.asyncio
async def test_pair_with_dut_thread_pairing_fails() -> None:
    """Test that pairing with THREAD mode returns False when pairing fails."""

    test_suite = ChipSuite(TestSuiteExecution())

    # Create a mock config with ThreadExternalConfig
    config_dict = {
        "network": {
            "fabric_id": "0",
            "thread": {
                "operational_dataset_hex": "0e080000000000010000000300001335060004001ff"
                "fe00208fedcba9876543210070800000000000000050800000000000000030d4f70656"
                "e54687265616444656d6f01021234041011223344556677889900aabbccddeeff000c0"
                "402a0f7f8",
                "ba_host": "127.0.0.1",
                "ba_port": 5684,
            },
            "wifi": {"ssid": "testharness", "password": "wifi-password"},
        },
        "dut_config": {
            "pairing_mode": "thread-meshcop",
            "setup_code": "20202021",
            "discriminator": "3840",
            "chip_use_paa_certs": False,
            "trace_log": True,
        },
        "test_parameters": None,
    }

    test_suite._ChipSuite__config_matter = TestEnvironmentConfigMatter(**config_dict)

    with mock.patch.object(
        target=test_suite.runner.chip_server,
        attribute="generate_manual_pairing_code_with_chip_tool",
        return_value="MT:ABC123",
    ), mock.patch.object(
        target=test_suite.runner,
        attribute="pairing_thread",
        return_value=False,  # Pairing fails
    ) as mock_pairing_thread:
        result = await test_suite._ChipSuite__pair_with_dut_thread()

    assert result is False
    mock_pairing_thread.assert_called_once()


def _config_dict_with_th_config(th_config: dict) -> dict:
    return {
        "network": {
            "fabric_id": "0",
            "thread": {
                "operational_dataset_hex": "0e080000000000010000000300001335060004001ff"
                "fe00208fedcba9876543210070800000000000000050800000000000000030d4f70656"
                "e54687265616444656d6f01021234041011223344556677889900aabbccddeeff000c0"
                "402a0f7f8",
                "ba_host": "127.0.0.1",
                "ba_port": 5684,
            },
            "wifi": {"ssid": "testharness", "password": "wifi-password"},
        },
        "dut_config": {
            "pairing_mode": "thread-meshcop",
            "setup_code": "20202021",
            "discriminator": "3840",
            "chip_use_paa_certs": False,
            "trace_log": True,
        },
        "test_parameters": None,
        "th_config": th_config,
    }


@pytest.mark.parametrize(
    "th_config_value, env_value, expected",
    [
        (True, False, True),  # config override True beats env False
        (False, True, False),  # config override False beats env True
        (None, True, True),  # unset config defers to env True
        (None, False, False),  # unset config defers to env False
    ],
)
def test_container_logs_enabled_matrix(th_config_value, env_value, expected) -> None:
    test_suite = ChipSuite(TestSuiteExecution())
    config_dict = _config_dict_with_th_config(
        {"enable_container_logs": th_config_value}
    )
    test_suite._ChipSuite__config_matter = TestEnvironmentConfigMatter(**config_dict)

    with mock.patch(
        "test_collections.matter.sdk_tests.support.yaml_tests.models.chip_suite"
        ".settings"
    ) as mock_settings:
        mock_settings.ENABLE_CONTAINER_LOGS = env_value
        assert test_suite._container_logs_enabled() is expected


def test_container_logs_enabled_defers_to_env_when_th_config_absent() -> None:
    test_suite = ChipSuite(TestSuiteExecution())
    config_dict = _config_dict_with_th_config({})
    del config_dict["th_config"]
    test_suite._ChipSuite__config_matter = TestEnvironmentConfigMatter(**config_dict)

    with mock.patch(
        "test_collections.matter.sdk_tests.support.yaml_tests.models.chip_suite"
        ".settings"
    ) as mock_settings:
        mock_settings.ENABLE_CONTAINER_LOGS = True
        assert test_suite._container_logs_enabled() is True
