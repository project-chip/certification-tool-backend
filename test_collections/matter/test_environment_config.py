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
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel

from app.schemas.test_environment_config import TestEnvironmentConfig, ThreadAutoConfig


class TestEnvironmentConfigMatterError(Exception):
    """Raised when the validation for the matter config fails"""


class DutPairingModeEnum(str, Enum):
    ON_NETWORK = "onnetwork"
    BLE_WIFI = "ble-wifi"
    BLE_THREAD = "ble-thread"
    WIFIPAF_WIFI = "wifipaf-wifi"
    NFC_THREAD = "nfc-thread"


class WiFiConfig(BaseModel):
    ssid: str
    password: str


class NFCReaderConfig(BaseModel):
    usb_reader_bus: str
    usb_reader_device: str


class ThreadExternalConfig(BaseModel):
    operational_dataset_hex: str


class NetworkConfig(BaseModel):
    wifi: WiFiConfig
    thread: Union[ThreadAutoConfig, ThreadExternalConfig]
    nfc_reader: Optional[NFCReaderConfig]


class EnhancedSetupFlowConfig(BaseModel):
    tc_version: int
    tc_user_response: int


class DutConfig(BaseModel):
    discriminator: Optional[str]
    setup_code: str
    pairing_mode: DutPairingModeEnum
    chip_timeout: Optional[str]
    chip_use_paa_certs: bool = False
    trace_log: bool = True
    enhanced_setup_flow: Optional[EnhancedSetupFlowConfig] = None


class TestEnvironmentConfigMatter(TestEnvironmentConfig):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"

    network: NetworkConfig
    dut_config: DutConfig

    def validate_model(self, dict_model: dict) -> None:
        valid_properties = list(DutConfig.__annotations__.keys())

        if dict_model:
            dut_config = dict_model.get("dut_config")
            network = dict_model.get("network")
            test_parameters = dict_model.get("test_parameters")

            # If both qr-code and manual-code are provided the test run execution
            # will fail
            if (
                test_parameters
                and "qr-code" in test_parameters
                and "manual-code" in test_parameters
            ):
                raise TestEnvironmentConfigMatterError(
                    "Please inform just one of either: qr-code or manual-code"
                )

            if not dut_config or not network:
                raise TestEnvironmentConfigMatterError(
                    "The dut_config and network configuration are mandatory"
                )

            if not isinstance(dut_config, dict):
                dut_config = dut_config.__dict__

            # Discriminator field must be informed when pairing_mode is other
            # than nfc_thread
            if (
                dut_config
                and dut_config["pairing_mode"] != DutPairingModeEnum.NFC_THREAD
                and "discriminator" not in dut_config
            ):
                raise TestEnvironmentConfigMatterError(
                    "The discriminator is mandatory for pairing mode "
                    f" {dut_config['pairing_mode']}"
                )

            # Discriminator field must NOT be informed when pairing_mode is nfc_thread
            if (
                dut_config
                and dut_config["pairing_mode"] == DutPairingModeEnum.NFC_THREAD
                and "discriminator" in dut_config
            ):
                raise TestEnvironmentConfigMatterError(
                    "The discriminator must not be informed for pairing mode "
                    f"{dut_config['pairing_mode']}"
                )

            # Check if the informed field in dut_config is valid
            for field, _ in dut_config.items():
                if field not in valid_properties:
                    raise TestEnvironmentConfigMatterError(
                        f"The field {field} is not a valid dut_config configuration:"
                        f" {valid_properties}"
                    )

            # All DutConfig fields but chip_timeout and enhanced_setup_flow are
            # mandatory
            mandatory_fields = valid_properties.copy()
            mandatory_fields.remove("chip_timeout")

            # discriminator is not mandatory for nfc_thread pairing mode
            if dut_config["pairing_mode"] == DutPairingModeEnum.NFC_THREAD:
                mandatory_fields.remove("discriminator")

            mandatory_fields.remove("enhanced_setup_flow")

            for field in mandatory_fields:
                if field not in dut_config:
                    raise TestEnvironmentConfigMatterError(
                        f"The field {field} is required for dut_config configuration"
                    )
