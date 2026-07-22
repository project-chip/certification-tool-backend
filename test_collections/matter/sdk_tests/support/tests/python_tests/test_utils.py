#
# Copyright (c) 2025 Project CHIP Authors
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

from app.constants.shared_constants import DutPairingModeEnum
from app.default_environment_config import default_environment_config
from app.test_engine.logger import test_engine_logger
from test_collections.matter.test_environment_config import (
    DutConfig,
    TestEnvironmentConfigMatter,
    ThreadExternalConfig,
)

from ...exec_run_in_container import ExecResultExtended
from ...python_testing.models.utils import (
    EXECUTABLE,
    RUNNER_CLASS_PATH,
    DUTCommissioningError,
    commission_device,
    generate_command_arguments,
)
from ...sdk_container import SDKContainer

# ---------------------------------------------------------------------------
# Helpers shared by the new json-arg / typed-arg tests
# ---------------------------------------------------------------------------


def _on_network_config(test_parameters: dict) -> TestEnvironmentConfigMatter:
    """Return a deep-copied default config with ON_NETWORK pairing and the
    given test_parameters dict."""
    cfg = default_environment_config.copy(deep=True)  # type: ignore
    cfg.dut_config = DutConfig(
        discriminator="3840",
        setup_code="20202021",
        pairing_mode=DutPairingModeEnum.ON_NETWORK,
        chip_timeout=None,
    )
    cfg.test_parameters = test_parameters
    return cfg


@pytest.mark.asyncio
async def test_generate_command_arguments_with_null_value_attribute() -> None:
    # Mock config
    mock_config = default_environment_config.copy(deep=True)  # type: ignore

    mock_config.test_parameters = {"test-argument": None}

    mock_dut_config = DutConfig(
        discriminator="123",
        setup_code="1234",
        pairing_mode=DutPairingModeEnum.ON_NETWORK,
        chip_timeout=None,
    )

    mock_config.dut_config = mock_dut_config

    arguments = await generate_command_arguments(
        config=mock_config, omit_commissioning_method=False
    )

    assert [
        "--trace-to json:log",
        "--commissioning-method on-network",
        "--discriminator 123",
        "--passcode 1234",
        "--test-argument ",
    ] == arguments


@pytest.mark.asyncio
async def test_generate_command_arguments_on_network() -> None:
    # Mock config
    mock_config = default_environment_config.copy(deep=True)  # type: ignore

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
        chip_timeout=None,
    )

    mock_config.dut_config = mock_dut_config

    arguments = await generate_command_arguments(
        config=mock_config, omit_commissioning_method=False
    )

    assert [
        "--trace-to json:log",
        "--commissioning-method on-network",
        "--discriminator 123",
        "--passcode 1234",
        "--paa-trust-store-path /paa-root-certs",
        "--storage_path /root/admin_storage.json",
    ] == arguments


@pytest.mark.asyncio
async def test_generate_command_arguments_ble_wifi_pairing_mode() -> None:
    # Mock config
    mock_config = default_environment_config.copy(deep=True)  # type: ignore

    mock_config.test_parameters = {
        "paa-trust-store-path": "/paa-root-certs",
        "storage_path": "/root/admin_storage.json",
    }

    mock_dut_config = DutConfig(
        discriminator="147",
        setup_code="357",
        pairing_mode=DutPairingModeEnum.BLE_WIFI,
        chip_timeout=None,
    )

    mock_config.dut_config = mock_dut_config

    arguments = await generate_command_arguments(
        config=mock_config, omit_commissioning_method=False
    )

    assert [
        "--trace-to json:log",
        f"--commissioning-method {DutPairingModeEnum.BLE_WIFI.value}",
        "--wifi-ssid testharness",
        "--wifi-passphrase wifi-password",
        "--discriminator 147",
        "--passcode 357",
        "--paa-trust-store-path /paa-root-certs",
        "--storage_path /root/admin_storage.json",
    ] == arguments


@pytest.mark.asyncio
async def test_generate_command_arguments_nfc_wifi_pairing_mode() -> None:
    # Mock config
    mock_config = default_environment_config.copy(deep=True)  # type: ignore

    mock_config.test_parameters = {
        "paa-trust-store-path": "/paa-root-certs",
        "storage_path": "/root/admin_storage.json",
    }

    mock_dut_config = DutConfig(
        pairing_mode=DutPairingModeEnum.NFC_WIFI,
        chip_timeout=None,
    )

    mock_config.dut_config = mock_dut_config

    arguments = await generate_command_arguments(
        config=mock_config, omit_commissioning_method=False
    )

    assert [
        "--trace-to json:log",
        f"--commissioning-method {DutPairingModeEnum.NFC_WIFI.value}",
        "--wifi-ssid testharness",
        "--wifi-passphrase wifi-password",
        "--paa-trust-store-path /paa-root-certs",
        "--storage_path /root/admin_storage.json",
        "--int-arg",
        "NFC_Reader_index:0",
    ] == arguments


@pytest.mark.asyncio
async def test_generate_command_arguments_ble_thread() -> None:
    # Mock config
    mock_config = default_environment_config.copy(deep=True)  # type: ignore

    mock_config.test_parameters = {
        "paa-trust-store-path": "/paa-root-certs",
        "storage_path": "/root/admin_storage.json",
    }

    mock_dut_config = DutConfig(
        discriminator="456",
        setup_code="8765",
        pairing_mode=DutPairingModeEnum.BLE_THREAD,
        chip_timeout=None,
    )

    mock_config.dut_config = mock_dut_config

    with mock.patch(
        (
            "test_collections.matter.sdk_tests.support.python_testing.models.utils"
            ".__thread_dataset_hex"
        ),
        return_value=(
            "0e08000000000001000035060004001fffe00708fd47156040435d2b041069c13cc038488"
            "0328b9d2d7a6ee891150c0402a0f7f8000300000f01021234020811111111222222220510"
            "00112233445566778899aabbccddeeff030444454d4f"
        ),
    ):
        arguments = await generate_command_arguments(
            config=mock_config, omit_commissioning_method=False
        )

        assert [
            "--trace-to json:log",
            "--commissioning-method ble-thread",
            (
                "--thread-dataset-hex 0e08000000000001000035060004001fffe00708fd4715604"
                "0435d2b041069c13cc0384880328b9d2d7a6ee891150c0402a0f7f8000300000f01021"
                "23402081111111122222222051000112233445566778899aabbccddeeff030444454d4"
                "f"
            ),
            "--discriminator 456",
            "--passcode 8765",
            "--paa-trust-store-path /paa-root-certs",
            "--storage_path /root/admin_storage.json",
        ] == arguments


@pytest.mark.asyncio
async def test_generate_command_arguments_ble_thread_for_external_network() -> None:
    # Mock config
    mock_config = default_environment_config.copy(deep=True)  # type: ignore

    mock_config.test_parameters = {
        "paa-trust-store-path": "/paa-root-certs",
        "storage_path": "/root/admin_storage.json",
    }

    mock_dut_config = DutConfig(
        discriminator="456",
        setup_code="8765",
        pairing_mode=DutPairingModeEnum.BLE_THREAD,
        chip_timeout=None,
    )

    mock_config.dut_config = mock_dut_config

    mock_config.network.thread = ThreadExternalConfig(
        operational_dataset_hex=(
            "0e08000000000001000035060004001fffe00708fd17e4031e5ea4f20410d477d767e424a5"
            "f2ef25c16fc9b621e90c0402a0f7f8000300000f0102123402081111111122222222051000"
            "112233445566778899aabbccddeeff030444454d4f"
        )
    )

    arguments = await generate_command_arguments(
        config=mock_config, omit_commissioning_method=False
    )

    assert [
        "--trace-to json:log",
        "--commissioning-method ble-thread",
        (
            "--thread-dataset-hex 0e08000000000001000035060004001fffe00708fd17e4031e5ea"
            "4f20410d477d767e424a5f2ef25c16fc9b621e90c0402a0f7f8000300000f0102123402081"
            "111111122222222051000112233445566778899aabbccddeeff030444454d4f"
        ),
        "--discriminator 456",
        "--passcode 8765",
        "--paa-trust-store-path /paa-root-certs",
        "--storage_path /root/admin_storage.json",
    ] == arguments


@pytest.mark.asyncio
async def test_generate_command_arguments_nfc_thread() -> None:
    # Mock config
    mock_config = default_environment_config.copy(deep=True)  # type: ignore

    mock_config.test_parameters = {
        "paa-trust-store-path": "/paa-root-certs",
        "storage_path": "/root/admin_storage.json",
    }

    mock_dut_config = DutConfig(
        pairing_mode=DutPairingModeEnum.NFC_THREAD,
        chip_timeout=None,
    )

    mock_config.dut_config = mock_dut_config

    with mock.patch(
        (
            "test_collections.matter.sdk_tests.support.python_testing.models.utils"
            ".__thread_dataset_hex"
        ),
        return_value=(
            "0e08000000000001000035060004001fffe00708fd47156040435d2b041069c13cc038488"
            "0328b9d2d7a6ee891150c0402a0f7f8000300000f01021234020811111111222222220510"
            "00112233445566778899aabbccddeeff030444454d4f"
        ),
    ):
        arguments = await generate_command_arguments(
            config=mock_config, omit_commissioning_method=False
        )

        assert [
            "--trace-to json:log",
            "--commissioning-method nfc-thread",
            (
                "--thread-dataset-hex 0e08000000000001000035060004001fffe00708fd4715604"
                "0435d2b041069c13cc0384880328b9d2d7a6ee891150c0402a0f7f8000300000f01021"
                "23402081111111122222222051000112233445566778899aabbccddeeff030444454d4"
                "f"
            ),
            "--paa-trust-store-path /paa-root-certs",
            "--storage_path /root/admin_storage.json",
            "--int-arg",
            "NFC_Reader_index:0",
        ] == arguments
        assert "--discriminator" not in " ".join(arguments)
        assert "--passcode" not in " ".join(arguments)


@pytest.mark.asyncio
async def test_generate_command_arguments_nfc_thread_for_external_network() -> None:
    # Mock config
    mock_config = default_environment_config.copy(deep=True)  # type: ignore

    mock_config.test_parameters = {
        "paa-trust-store-path": "/paa-root-certs",
        "storage_path": "/root/admin_storage.json",
    }

    mock_dut_config = DutConfig(
        pairing_mode=DutPairingModeEnum.NFC_THREAD,
        chip_timeout=None,
    )

    mock_config.dut_config = mock_dut_config

    mock_config.network.thread = ThreadExternalConfig(
        operational_dataset_hex=(
            "0e08000000000001000035060004001fffe00708fd17e4031e5ea4f20410d477d767e424a5"
            "f2ef25c16fc9b621e90c0402a0f7f8000300000f0102123402081111111122222222051000"
            "112233445566778899aabbccddeeff030444454d4f"
        )
    )

    arguments = await generate_command_arguments(
        config=mock_config, omit_commissioning_method=False
    )

    assert [
        "--trace-to json:log",
        "--commissioning-method nfc-thread",
        (
            "--thread-dataset-hex 0e08000000000001000035060004001fffe00708fd17e4031e5ea"
            "4f20410d477d767e424a5f2ef25c16fc9b621e90c0402a0f7f8000300000f0102123402081"
            "111111122222222051000112233445566778899aabbccddeeff030444454d4f"
        ),
        "--paa-trust-store-path /paa-root-certs",
        "--storage_path /root/admin_storage.json",
        "--int-arg",
        "NFC_Reader_index:0",
    ] == arguments
    assert "--discriminator" not in " ".join(arguments)
    assert "--passcode" not in " ".join(arguments)


NFC_PAIRING_MODES_PARAMS = [
    pytest.param(DutPairingModeEnum.NFC_THREAD, id="nfc-thread"),
    pytest.param(DutPairingModeEnum.NFC_WIFI, id="nfc-wifi"),
]

MOCK_THREAD_DATASET = (
    "0e08000000000001000035060004001fffe00708fd47156040435d2b041069c13cc038488"
    "0328b9d2d7a6ee891150c0402a0f7f8000300000f01021234020811111111222222220510"
    "00112233445566778899aabbccddeeff030444454d4f"
)

THREAD_DATASET_PATCH = mock.patch(
    "test_collections.matter.sdk_tests.support.python_testing.models.utils"
    ".__thread_dataset_hex",
    return_value=MOCK_THREAD_DATASET,
)


async def _nfc_arguments(pairing_mode: DutPairingModeEnum, **dut_kwargs: str) -> list:
    """Helper: build command arguments for a given NFC pairing mode and DutConfig
    kwargs."""
    mock_config = default_environment_config.copy(deep=True)  # type: ignore
    mock_config.test_parameters = None
    mock_config.dut_config = DutConfig(
        pairing_mode=pairing_mode, chip_timeout=None, **dut_kwargs
    )
    with THREAD_DATASET_PATCH:
        return await generate_command_arguments(
            config=mock_config, omit_commissioning_method=False
        )


def _assert_no_discriminator_or_passcode(arguments: list) -> None:
    joined = " ".join(arguments)
    assert "--discriminator" not in joined
    assert "--passcode" not in joined


@pytest.mark.asyncio
@pytest.mark.parametrize("pairing_mode", NFC_PAIRING_MODES_PARAMS)
async def test_nfc_with_discriminator_and_setup_code_not_passed_to_sdk(
    pairing_mode: DutPairingModeEnum,
) -> None:
    """Scenario 1: both discriminator and setup_code set — neither passed to SDK."""
    arguments = await _nfc_arguments(
        pairing_mode, discriminator="3840", setup_code="20202021"
    )
    _assert_no_discriminator_or_passcode(arguments)


@pytest.mark.asyncio
@pytest.mark.parametrize("pairing_mode", NFC_PAIRING_MODES_PARAMS)
async def test_nfc_with_only_discriminator_not_passed_to_sdk(
    pairing_mode: DutPairingModeEnum,
) -> None:
    """Scenario 2: only discriminator set — not passed to SDK."""
    arguments = await _nfc_arguments(pairing_mode, discriminator="3840")
    _assert_no_discriminator_or_passcode(arguments)


@pytest.mark.asyncio
@pytest.mark.parametrize("pairing_mode", NFC_PAIRING_MODES_PARAMS)
async def test_nfc_with_only_setup_code_not_passed_to_sdk(
    pairing_mode: DutPairingModeEnum,
) -> None:
    """Scenario 3: only setup_code set — not passed to SDK."""
    arguments = await _nfc_arguments(pairing_mode, setup_code="20202021")
    _assert_no_discriminator_or_passcode(arguments)


@pytest.mark.asyncio
@pytest.mark.parametrize("pairing_mode", NFC_PAIRING_MODES_PARAMS)
async def test_nfc_without_discriminator_and_setup_code_not_passed_to_sdk(
    pairing_mode: DutPairingModeEnum,
) -> None:
    """Scenario 4: neither discriminator nor setup_code set — not passed to SDK."""
    arguments = await _nfc_arguments(pairing_mode)
    _assert_no_discriminator_or_passcode(arguments)


@pytest.mark.asyncio
@pytest.mark.parametrize("pairing_mode", NFC_PAIRING_MODES_PARAMS)
async def test_nfc_logs_warning_when_discriminator_or_setup_code_set(
    pairing_mode: DutPairingModeEnum,
) -> None:
    """Warning is logged for NFC modes when discriminator or setup_code are provided."""
    with mock.patch.object(test_engine_logger, "warning") as mock_warn:
        await _nfc_arguments(pairing_mode, discriminator="3840", setup_code="20202021")
        mock_warn.assert_called_once()
        assert "ignored" in mock_warn.call_args[0][0]


@pytest.mark.asyncio
@pytest.mark.parametrize("pairing_mode", NFC_PAIRING_MODES_PARAMS)
async def test_nfc_no_warning_when_discriminator_and_setup_code_not_set(
    pairing_mode: DutPairingModeEnum,
) -> None:
    """No warning is logged for NFC modes when discriminator and setup_code are
    absent."""
    with mock.patch.object(test_engine_logger, "warning") as mock_warn:
        await _nfc_arguments(pairing_mode)
        mock_warn.assert_not_called()


@pytest.mark.asyncio
async def test_generate_command_arguments_no_test_parameter_informed() -> None:
    # Mock config
    mock_config = default_environment_config.copy(deep=True)  # type: ignore

    mock_config.test_parameters = None

    mock_dut_config = DutConfig(
        discriminator="456",
        setup_code="8765",
        pairing_mode=DutPairingModeEnum.BLE_THREAD,
        chip_timeout=None,
    )

    mock_config.dut_config = mock_dut_config

    with mock.patch(
        (
            "test_collections.matter.sdk_tests.support.python_testing.models.utils"
            ".__thread_dataset_hex"
        ),
        return_value=(
            "0e08000000000001000035060004001fffe00708fd47156040435d2b041069c13cc0384880"
            "328b9d2d7a6ee891150c0402a0f7f8000300000f0102123402081111111122222222051000"
            "112233445566778899aabbccddeeff030444454d4f"
        ),
    ):
        arguments = await generate_command_arguments(
            config=mock_config, omit_commissioning_method=False
        )

        assert [
            "--trace-to json:log",
            "--commissioning-method ble-thread",
            (
                "--thread-dataset-hex 0e08000000000001000035060004001fffe00708fd4715604"
                "0435d2b041069c13cc0384880328b9d2d7a6ee891150c0402a0f7f8000300000f01021"
                "23402081111111122222222051000112233445566778899aabbccddeeff030444454d4"
                "f"
            ),
            "--discriminator 456",
            "--passcode 8765",
        ] == arguments


@pytest.mark.asyncio
async def test_generate_command_arguments_trace_log_false_informed() -> None:
    # Mock config
    mock_config = default_environment_config.copy(deep=True)  # type: ignore

    mock_config.test_parameters = None

    mock_dut_config = DutConfig(
        discriminator="456",
        setup_code="8765",
        pairing_mode=DutPairingModeEnum.BLE_THREAD,
        trace_log=False,
        chip_timeout=None,
    )

    mock_config.dut_config = mock_dut_config

    with mock.patch(
        (
            "test_collections.matter.sdk_tests.support.python_testing.models.utils"
            ".__thread_dataset_hex"
        ),
        return_value=(
            "0e08000000000001000035060004001fffe00708fd17e4031e5ea4f20410d477d767e424a5"
            "f2ef25c16fc9b621e90c0402a0f7f8000300000f0102123402081111111122222222051000"
            "112233445566778899aabbccddeeff030444454d4f"
        ),
    ):
        arguments = await generate_command_arguments(
            config=mock_config, omit_commissioning_method=False
        )

        assert [
            "--commissioning-method ble-thread",
            (
                "--thread-dataset-hex 0e08000000000001000035060004001fffe00708fd17e4031"
                "e5ea4f20410d477d767e424a5f2ef25c16fc9b621e90c0402a0f7f8000300000f01021"
                "23402081111111122222222051000112233445566778899aabbccddeeff030444454d4"
                "f"
            ),
            "--discriminator 456",
            "--passcode 8765",
        ] == arguments


@pytest.mark.asyncio
async def test_generate_command_arguments_omit_comissioning_method() -> None:
    # Mock config
    mock_config = default_environment_config.copy(deep=True)  # type: ignore

    mock_dut_config = DutConfig(
        discriminator="456",
        setup_code="8765",
        pairing_mode=DutPairingModeEnum.ON_NETWORK,
        chip_timeout=None,
    )

    mock_config.dut_config = mock_dut_config

    arguments = await generate_command_arguments(
        config=mock_config, omit_commissioning_method=True
    )

    assert [
        "--trace-to json:log",
        "--in-test-commissioning-method on-network",
        "--discriminator 456",
        "--passcode 8765",
    ] == arguments


@pytest.mark.asyncio
async def test_commission_device() -> None:
    sdk_container: SDKContainer = SDKContainer()

    command_args = ["arg1", "arg2", "arg3"]
    expected_command = [f"{RUNNER_CLASS_PATH} --commission"]
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
    ) as mock_handle_logs, mock.patch(
        target="test_collections.matter.sdk_tests.support.python_testing.models.utils"
        ".log_test_output_file"
    ) as mock_log_test_output, mock.patch.object(
        target=sdk_container, attribute="exec_exit_code", return_value=0
    ):
        await commission_device(
            default_environment_config, test_engine_logger  # type: ignore
        )

    mock_send_command.assert_called_once_with(
        expected_command, prefix=EXECUTABLE, is_stream=True, is_socket=False
    )
    mock_handle_logs.assert_called_once()
    mock_log_test_output.assert_called_once()


@pytest.mark.asyncio
async def test_commission_device_failure() -> None:
    sdk_container: SDKContainer = SDKContainer()

    command_args = ["arg1", "arg2", "arg3"]
    expected_command = [f"{RUNNER_CLASS_PATH} --commission"]
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
        await commission_device(
            default_environment_config, test_engine_logger  # type: ignore
        )

    mock_send_command.assert_called_once_with(
        expected_command, prefix=EXECUTABLE, is_stream=True, is_socket=False
    )
    mock_handle_logs.assert_called_once()


# ---------------------------------------------------------------------------
# Tests for the new typed-arg / json-arg handling in generate_command_arguments
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_command_arguments_json_arg_string_value() -> None:
    """json-arg with a plain JSON string value is emitted as two separate list
    entries: '--json-arg' and the single-quoted NAME:JSON pair."""
    json_value = 'PIXIT.ZONEMGMT.Zone1:{"vertices":[{"x":0,"y":0},{"x":100,"y":100}]}'
    cfg = _on_network_config({"json-arg": json_value})

    arguments = await generate_command_arguments(cfg)

    assert "--json-arg" in arguments
    idx = arguments.index("--json-arg")
    assert arguments[idx + 1] == f"'{json_value}'"


@pytest.mark.asyncio
async def test_generate_command_arguments_json_arg_dict_value() -> None:
    """json-arg with a dict value (Pydantic parsed it as a nested object) is
    serialized to compact JSON and single-quoted."""
    cfg = _on_network_config({"json-arg": "PIXIT.X:1"})
    # Override with a dict value to exercise the json.dumps path
    cfg.test_parameters = {
        "json-arg": {"vertices": [{"x": 0, "y": 0}, {"x": 100, "y": 100}]}
    }

    arguments = await generate_command_arguments(cfg)

    assert "--json-arg" in arguments
    idx = arguments.index("--json-arg")
    # dict serialized to compact JSON and single-quoted because it contains {
    assert arguments[idx + 1] == '\'{"vertices":[{"x":0,"y":0},{"x":100,"y":100}]}\''


@pytest.mark.asyncio
async def test_generate_command_arguments_int_arg_single_pair() -> None:
    """int-arg with a single NAME:VALUE pair (no special chars) is NOT
    single-quoted."""
    cfg = _on_network_config({"int-arg": "PIXIT.ACE.APPENDPOINT:1"})

    arguments = await generate_command_arguments(cfg)

    assert "--int-arg" in arguments
    idx = arguments.index("--int-arg")
    assert arguments[idx + 1] == "PIXIT.ACE.APPENDPOINT:1"


@pytest.mark.asyncio
async def test_generate_command_arguments_int_arg_multiple_pairs() -> None:
    """int-arg with multiple space-separated NAME:VALUE pairs produces one
    '--int-arg' flag followed by each pair as a separate list entry."""
    cfg = _on_network_config(
        {"int-arg": "PIXIT.ACE.APPENDPOINT:1 PIXIT.ACE.APPDEVTYPEID:256"}
    )

    arguments = await generate_command_arguments(cfg)

    assert "--int-arg" in arguments
    idx = arguments.index("--int-arg")
    assert arguments[idx + 1] == "PIXIT.ACE.APPENDPOINT:1"
    assert arguments[idx + 2] == "PIXIT.ACE.APPDEVTYPEID:256"


@pytest.mark.asyncio
async def test_generate_command_arguments_string_arg_multiple_pairs() -> None:
    """string-arg with multiple space-separated NAME:VALUE pairs is split into
    individual list entries, none of which are quoted (no special chars)."""
    cfg = _on_network_config(
        {"string-arg": "PIXIT.ACE.APPCLUSTER:OnOff PIXIT.ACE.APPATTRIBUTE:OnOff"}
    )

    arguments = await generate_command_arguments(cfg)

    assert "--string-arg" in arguments
    idx = arguments.index("--string-arg")
    assert arguments[idx + 1] == "PIXIT.ACE.APPCLUSTER:OnOff"
    assert arguments[idx + 2] == "PIXIT.ACE.APPATTRIBUTE:OnOff"


@pytest.mark.asyncio
async def test_generate_command_arguments_json_arg_and_int_arg_together() -> None:
    """json-arg and int-arg can coexist; each is handled independently."""
    cfg = _on_network_config(
        {
            "json-arg": 'PIXIT.ZONE:{"vertices":[{"x":0,"y":0}]}',
            "int-arg": "PIXIT.ACE.APPENDPOINT:1",
        }
    )

    arguments = await generate_command_arguments(cfg)

    assert "--json-arg" in arguments
    assert "--int-arg" in arguments

    json_idx = arguments.index("--json-arg")
    assert arguments[json_idx + 1] == '\'PIXIT.ZONE:{"vertices":[{"x":0,"y":0}]}\''

    int_idx = arguments.index("--int-arg")
    assert arguments[int_idx + 1] == "PIXIT.ACE.APPENDPOINT:1"


@pytest.mark.asyncio
async def test_generate_command_arguments_non_split_arg_unchanged() -> None:
    """Args not in _SPLIT_ARGS (e.g. paa-trust-store-path) are still emitted
    as a single '--flag value' string, unchanged by the new logic."""
    cfg = _on_network_config({"paa-trust-store-path": "/paa-root-certs"})

    arguments = await generate_command_arguments(cfg)

    assert "--paa-trust-store-path /paa-root-certs" in arguments


@pytest.mark.asyncio
async def test_generate_command_arguments_json_arg_value_with_spaces() -> None:
    """json-arg where the JSON value contains spaces is kept as a single token.
    This validates that shlex.split() is used instead of a naive split(' ')."""
    json_value = 'PIXIT.Key:{"name":"some name with spaces"}'
    cfg = _on_network_config({"json-arg": json_value})

    arguments = await generate_command_arguments(cfg)

    assert "--json-arg" in arguments
    idx = arguments.index("--json-arg")
    assert arguments[idx + 1] == f"'{json_value}'"


@pytest.mark.asyncio
async def test_generate_command_arguments_json_arg_null_value() -> None:
    """json-arg with a None value emits '--json-arg' with no following value
    (empty string is skipped by the pair loop)."""
    cfg = _on_network_config({"json-arg": None})

    arguments = await generate_command_arguments(cfg)

    assert "--json-arg" in arguments
    idx = arguments.index("--json-arg")
    # Nothing follows --json-arg when the value is None/empty
    assert idx == len(arguments) - 1


@pytest.mark.asyncio
async def test_generate_command_arguments_float_arg_single_pair() -> None:
    """float-arg with a single NAME:VALUE pair (no special chars) is NOT
    single-quoted."""
    cfg = _on_network_config({"float-arg": "PIXIT.SENSOR.TOLERANCE:0.5"})

    arguments = await generate_command_arguments(cfg)

    assert "--float-arg" in arguments
    idx = arguments.index("--float-arg")
    assert arguments[idx + 1] == "PIXIT.SENSOR.TOLERANCE:0.5"


@pytest.mark.asyncio
async def test_generate_command_arguments_float_arg_multiple_pairs() -> None:
    """float-arg with multiple space-separated NAME:VALUE pairs produces one
    '--float-arg' flag followed by each pair as a separate list entry."""
    cfg = _on_network_config(
        {"float-arg": "PIXIT.SENSOR.MIN:0.0 PIXIT.SENSOR.MAX:100.0"}
    )

    arguments = await generate_command_arguments(cfg)

    assert "--float-arg" in arguments
    idx = arguments.index("--float-arg")
    assert arguments[idx + 1] == "PIXIT.SENSOR.MIN:0.0"
    assert arguments[idx + 2] == "PIXIT.SENSOR.MAX:100.0"


@pytest.mark.asyncio
async def test_generate_command_arguments_bool_arg_single_pair() -> None:
    """bool-arg with a single NAME:VALUE pair is NOT single-quoted."""
    cfg = _on_network_config({"bool-arg": "PIXIT.TEST.ENABLED:True"})

    arguments = await generate_command_arguments(cfg)

    assert "--bool-arg" in arguments
    idx = arguments.index("--bool-arg")
    assert arguments[idx + 1] == "PIXIT.TEST.ENABLED:True"


@pytest.mark.asyncio
async def test_generate_command_arguments_bool_arg_multiple_pairs() -> None:
    """bool-arg with multiple space-separated NAME:VALUE pairs produces one
    '--bool-arg' flag followed by each pair as a separate list entry."""
    cfg = _on_network_config(
        {"bool-arg": "PIXIT.TEST.FEATURE_A:True PIXIT.TEST.FEATURE_B:False"}
    )

    arguments = await generate_command_arguments(cfg)

    assert "--bool-arg" in arguments
    idx = arguments.index("--bool-arg")
    assert arguments[idx + 1] == "PIXIT.TEST.FEATURE_A:True"
    assert arguments[idx + 2] == "PIXIT.TEST.FEATURE_B:False"


@pytest.mark.asyncio
async def test_generate_command_arguments_hex_arg_single_pair() -> None:
    """hex-arg with a single NAME:VALUE pair (no special chars) is NOT
    single-quoted."""
    cfg = _on_network_config({"hex-arg": "PIXIT.COMMISSIONING.DATASET:DEADBEEF"})

    arguments = await generate_command_arguments(cfg)

    assert "--hex-arg" in arguments
    idx = arguments.index("--hex-arg")
    assert arguments[idx + 1] == "PIXIT.COMMISSIONING.DATASET:DEADBEEF"


@pytest.mark.asyncio
async def test_generate_command_arguments_hex_arg_multiple_pairs() -> None:
    """hex-arg with multiple space-separated NAME:VALUE pairs produces one
    '--hex-arg' flag followed by each pair as a separate list entry."""
    cfg = _on_network_config(
        {"hex-arg": "PIXIT.DATASET.ACTIVE:AABBCCDD PIXIT.DATASET.PENDING:11223344"}
    )

    arguments = await generate_command_arguments(cfg)

    assert "--hex-arg" in arguments
    idx = arguments.index("--hex-arg")
    assert arguments[idx + 1] == "PIXIT.DATASET.ACTIVE:AABBCCDD"
    assert arguments[idx + 2] == "PIXIT.DATASET.PENDING:11223344"


# ---------------------------------------------------------------------------
# Tests for NFC_Reader_index default / explicit value injection
# ---------------------------------------------------------------------------


async def _nfc_arguments_with_params(
    pairing_mode: DutPairingModeEnum, test_parameters: dict | None
) -> list:
    """Helper: build command arguments for a given NFC pairing mode and
    test_parameters dict."""
    mock_config = default_environment_config.copy(deep=True)  # type: ignore
    mock_config.test_parameters = test_parameters
    mock_config.dut_config = DutConfig(pairing_mode=pairing_mode, chip_timeout=None)
    with THREAD_DATASET_PATCH:
        return await generate_command_arguments(
            config=mock_config, omit_commissioning_method=False
        )


def _assert_nfc_reader_index(arguments: list, expected_index: int) -> None:
    assert "--int-arg" in arguments
    idx = arguments.index("--int-arg")
    assert arguments[idx + 1] == f"NFC_Reader_index:{expected_index}"


@pytest.mark.asyncio
@pytest.mark.parametrize("pairing_mode", NFC_PAIRING_MODES_PARAMS)
async def test_nfc_reader_index_defaults_to_zero_when_not_provided(
    pairing_mode: DutPairingModeEnum,
) -> None:
    """NFC_Reader_index:0 is injected into int-arg when test_parameters is None."""
    arguments = await _nfc_arguments_with_params(pairing_mode, test_parameters=None)
    _assert_nfc_reader_index(arguments, 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("pairing_mode", NFC_PAIRING_MODES_PARAMS)
async def test_nfc_reader_index_defaults_to_zero_when_params_present_but_key_absent(
    pairing_mode: DutPairingModeEnum,
) -> None:
    """NFC_Reader_index:0 is injected when test_parameters exists but int-arg does
    not contain NFC_Reader_index."""
    arguments = await _nfc_arguments_with_params(
        pairing_mode, test_parameters={"paa-trust-store-path": "/paa-root-certs"}
    )
    _assert_nfc_reader_index(arguments, 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("pairing_mode", NFC_PAIRING_MODES_PARAMS)
async def test_nfc_reader_index_uses_provided_value(
    pairing_mode: DutPairingModeEnum,
) -> None:
    """NFC_Reader_index uses the value already in int-arg when explicitly set."""
    arguments = await _nfc_arguments_with_params(
        pairing_mode, test_parameters={"int-arg": "NFC_Reader_index:2"}
    )
    _assert_nfc_reader_index(arguments, 2)


@pytest.mark.asyncio
@pytest.mark.parametrize("pairing_mode", NFC_PAIRING_MODES_PARAMS)
async def test_nfc_reader_index_not_duplicated_when_already_in_int_arg(
    pairing_mode: DutPairingModeEnum,
) -> None:
    """NFC_Reader_index is not injected a second time when already present in
    int-arg."""
    arguments = await _nfc_arguments_with_params(
        pairing_mode, test_parameters={"int-arg": "NFC_Reader_index:1"}
    )
    joined = " ".join(arguments)
    assert joined.count("NFC_Reader_index") == 1


@pytest.mark.asyncio
async def test_nfc_reader_index_not_injected_for_non_nfc_modes() -> None:
    """--int-arg NFC_Reader_index is never injected for non-NFC pairing modes."""
    cfg = _on_network_config(test_parameters={})
    arguments = await generate_command_arguments(cfg)
    joined = " ".join(arguments)
    assert "NFC_Reader_index" not in joined
