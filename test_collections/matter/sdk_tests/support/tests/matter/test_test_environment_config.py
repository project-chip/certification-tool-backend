#
# Copyright (c) 2024-2026 Project CHIP Authors
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
import pytest

from app.schemas.test_environment_config import TestEnvironmentConfigError
from test_collections.matter.sdk_tests.support.tests.utils.utils import (
    default_config_invalid_dut_added_property,
    default_config_invalid_dut_renamed_property,
    default_config_no_dut,
    default_config_no_network,
    default_config_thread_no_ba_host,
    default_config_thread_no_ba_port,
    default_config_thread_valid,
    default_matter_config,
)
from test_collections.matter.test_environment_config import TestEnvironmentConfigMatter


def test_create_config_matter_with_valid_config_success() -> None:
    config_matter = TestEnvironmentConfigMatter(**default_matter_config)

    assert config_matter is not None


def test_create_config_matter_with_no_config_fails() -> None:
    with pytest.raises(TestEnvironmentConfigError) as e:
        TestEnvironmentConfigMatter()
        assert "The informed configuration has one or more invalid properties." == str(
            e
        )


def test_create_config_matter_with_no_dut_config_fails() -> None:
    with pytest.raises(TestEnvironmentConfigError) as e:
        TestEnvironmentConfigMatter(**default_config_no_dut)
        assert "The informed configuration has one or more invalid properties." == str(
            e
        )


def test_create_config_matter_with_invalid_dut_config_renamed_property_fails() -> None:
    with pytest.raises(TestEnvironmentConfigError) as e:
        TestEnvironmentConfigMatter(**default_config_invalid_dut_renamed_property)
        assert "The informed configuration has one or more invalid properties." == str(
            e
        )


def test_create_config_matter_with_invalid_dut_config_added_property_fails() -> None:
    with pytest.raises(TestEnvironmentConfigError) as e:
        TestEnvironmentConfigMatter(**default_config_invalid_dut_added_property)
        assert "The informed configuration has one or more invalid properties." == str(
            e
        )


def test_create_config_matter_with_no_network_config_fails() -> None:
    with pytest.raises(TestEnvironmentConfigError) as e:
        TestEnvironmentConfigMatter(**default_config_no_network)
        assert "The informed configuration has one or more invalid properties." == str(
            e
        )


def test_create_config_matter_with_thread_valid_succeeds() -> None:
    config_matter = TestEnvironmentConfigMatter(**default_config_thread_valid)

    assert config_matter is not None
    assert config_matter.dut_config.pairing_mode == "thread"
    assert config_matter.network.thread.ba_host == "127.0.0.1"
    assert config_matter.network.thread.ba_port == 5684


def test_create_config_matter_with_thread_no_ba_host_fails() -> None:
    with pytest.raises(TestEnvironmentConfigError) as e:
        TestEnvironmentConfigMatter(**default_config_thread_no_ba_host)

    # Check for the key parts of the error message (handles both "mandatory"
    # and "mandatories")
    assert "ba_host and ba_port" in str(e.value)
    assert "mandator" in str(e.value)  # Matches both "mandatory" and "mandatories"


def test_create_config_matter_with_thread_no_ba_port_fails() -> None:
    with pytest.raises(TestEnvironmentConfigError) as e:
        TestEnvironmentConfigMatter(**default_config_thread_no_ba_port)

    # Check for the key parts of the error message (handles both "mandatory"
    # and "mandatories")
    assert "ba_host and ba_port" in str(e.value)
    assert "mandator" in str(e.value)  # Matches both "mandatory" and "mandatories"


def test_create_config_matter_with_thread_no_ba_params_fails() -> None:
    """Test that THREAD mode fails when both ba_host and ba_port are missing."""
    config = {
        "network": {
            "fabric_id": "0",
            "thread": {
                "operational_dataset_hex": "0e080000000000010000000300001335060004001ff"
                "fe00208fedcba9876543210070800000000000000050800000000000000030d4f70656"
                "e54687265616444656d6f01021234041011223344556677889900aabbccddeeff000c0"
                "402a0f7f8",
            },
            "wifi": {"ssid": "testharness", "password": "wifi-password"},
        },
        "dut_config": {
            "pairing_mode": "thread",
            "setup_code": "20202021",
            "discriminator": "3840",
            "chip_use_paa_certs": False,
            "trace_log": True,
        },
        "test_parameters": None,
    }

    with pytest.raises(TestEnvironmentConfigError) as e:
        TestEnvironmentConfigMatter(**config)

    # Check for the key parts of the error message (handles both "mandatory"
    # and "mandatories")
    assert "ba_host and ba_port" in str(e.value)
    assert "mandator" in str(e.value)  # Matches both "mandatory" and "mandatories"


def test_create_config_matter_with_thread_no_thread_config_fails() -> None:
    """Test that THREAD mode fails when thread config is missing entirely."""
    config = {
        "network": {
            "fabric_id": "0",
            "wifi": {"ssid": "testharness", "password": "wifi-password"},
        },
        "dut_config": {
            "pairing_mode": "thread",
            "setup_code": "20202021",
            "discriminator": "3840",
            "chip_use_paa_certs": False,
            "trace_log": True,
        },
        "test_parameters": None,
    }

    with pytest.raises(TestEnvironmentConfigError) as e:
        TestEnvironmentConfigMatter(**config)

    # Pydantic validation fails before custom validation, so check for either error
    error_str = str(e.value)
    assert (
        "thread" in error_str.lower() and "required" in error_str.lower()
    ) or "Thread configuration is required" in error_str


def test_create_config_matter_with_both_qr_and_manual_code_fails() -> None:
    """Test that config fails when both qr-code and manual-code are provided."""
    config = {
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
            },
            "wifi": {"ssid": "testharness", "password": "wifi-password"},
        },
        "dut_config": {
            "pairing_mode": "onnetwork",
            "setup_code": "20202021",
            "discriminator": "3840",
            "chip_use_paa_certs": False,
            "trace_log": True,
        },
        "test_parameters": {
            "qr-code": "MT:ABC123",
            "manual-code": "34970112332",
        },
    }

    with pytest.raises(TestEnvironmentConfigError) as e:
        TestEnvironmentConfigMatter(**config)

    assert "Please inform just one of either: qr-code or manual-code" in str(e.value)


def test_create_config_matter_with_only_qr_code_succeeds() -> None:
    """Test that config succeeds with only qr-code in test_parameters."""
    config = {
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
            },
            "wifi": {"ssid": "testharness", "password": "wifi-password"},
        },
        "dut_config": {
            "pairing_mode": "onnetwork",
            "setup_code": "20202021",
            "discriminator": "3840",
            "chip_use_paa_certs": False,
            "trace_log": True,
        },
        "test_parameters": {
            "qr-code": "MT:ABC123",
        },
    }

    config_matter = TestEnvironmentConfigMatter(**config)

    assert config_matter is not None
    assert config_matter.test_parameters.get("qr-code") == "MT:ABC123"
    assert "manual-code" not in config_matter.test_parameters


def test_create_config_matter_with_only_manual_code_succeeds() -> None:
    """Test that config succeeds with only manual-code in test_parameters."""
    config = {
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
            },
            "wifi": {"ssid": "testharness", "password": "wifi-password"},
        },
        "dut_config": {
            "pairing_mode": "onnetwork",
            "setup_code": "20202021",
            "discriminator": "3840",
            "chip_use_paa_certs": False,
            "trace_log": True,
        },
        "test_parameters": {
            "manual-code": "34970112332",
        },
    }

    config_matter = TestEnvironmentConfigMatter(**config)

    assert config_matter is not None
    assert config_matter.test_parameters.get("manual-code") == "34970112332"
    assert "qr-code" not in config_matter.test_parameters


@pytest.mark.parametrize(
    "pairing_mode",
    [
        "onnetwork",
        "ble-wifi",
        "ble-thread",
        "wifipaf-wifi",
        "nfc-thread",
    ],
)
def test_create_config_matter_with_non_thread_modes_no_ba_params_succeeds(
    pairing_mode: str,
) -> None:
    """Test that non-THREAD pairing modes don't require ba_host/ba_port."""
    config = {
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
            },
            "wifi": {"ssid": "testharness", "password": "wifi-password"},
        },
        "dut_config": {
            "pairing_mode": pairing_mode,
            "setup_code": "20202021",
            "discriminator": "3840",
            "chip_use_paa_certs": False,
            "trace_log": True,
        },
        "test_parameters": None,
    }

    config_matter = TestEnvironmentConfigMatter(**config)

    assert config_matter is not None
    assert config_matter.dut_config.pairing_mode == pairing_mode


def test_create_config_matter_without_discriminator_fails() -> None:
    """Test that config fails when discriminator is missing."""
    config = {
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
            },
            "wifi": {"ssid": "testharness", "password": "wifi-password"},
        },
        "dut_config": {
            "pairing_mode": "onnetwork",
            "setup_code": "20202021",
            # "discriminator": "3840",  # Missing
            "chip_use_paa_certs": False,
            "trace_log": True,
        },
        "test_parameters": None,
    }

    with pytest.raises(TestEnvironmentConfigError) as e:
        TestEnvironmentConfigMatter(**config)

    # Pydantic validation fails before custom validation, so check for either error
    error_str = str(e.value)
    assert (
        "discriminator" in error_str.lower() and "required" in error_str.lower()
    ) or "discriminator is required" in error_str


def test_create_config_matter_without_setup_code_fails() -> None:
    """Test that config fails when setup_code is missing."""
    config = {
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
            },
            "wifi": {"ssid": "testharness", "password": "wifi-password"},
        },
        "dut_config": {
            "pairing_mode": "onnetwork",
            # "setup_code": "20202021",  # Missing
            "discriminator": "3840",
            "chip_use_paa_certs": False,
            "trace_log": True,
        },
        "test_parameters": None,
    }

    with pytest.raises(TestEnvironmentConfigError) as e:
        TestEnvironmentConfigMatter(**config)

    # Pydantic validation fails before custom validation, so check for either error
    error_str = str(e.value)
    assert (
        "setup_code" in error_str.lower() and "required" in error_str.lower()
    ) or "setup_code is required" in error_str


def test_create_config_matter_without_pairing_mode_fails() -> None:
    """Test that config fails when pairing_mode is missing."""
    config = {
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
            },
            "wifi": {"ssid": "testharness", "password": "wifi-password"},
        },
        "dut_config": {
            # "pairing_mode": "onnetwork",  # Missing
            "setup_code": "20202021",
            "discriminator": "3840",
            "chip_use_paa_certs": False,
            "trace_log": True,
        },
        "test_parameters": None,
    }

    with pytest.raises(TestEnvironmentConfigError) as e:
        TestEnvironmentConfigMatter(**config)

    # Pydantic validation fails before custom validation, so check for either error
    error_str = str(e.value)
    assert (
        "pairing_mode" in error_str.lower() and "required" in error_str.lower()
    ) or "pairing_mode is required" in error_str
