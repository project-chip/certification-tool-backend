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
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel


class DutPairingModeEnum(str, Enum):
    ON_NETWORK = "onnetwork"
    BLE_WIFI = "ble-wifi"
    BLE_THREAD = "ble-thread"


class WiFiConfig(BaseModel):
    ssid: str
    password: str


class ThreadDataset(BaseModel):
    channel: str
    panid: str
    extpanid: str
    networkkey: str
    networkname: str


class ThreadAutoConfig(BaseModel):
    rcp_serial_path: str
    rcp_baudrate: int
    on_mesh_prefix: str
    network_interface: str
    dataset: ThreadDataset
    otbr_docker_image: Optional[str]


class ThreadExternalConfig(BaseModel):
    operational_dataset_hex: str


class NetworkConfig(BaseModel):
    wifi: WiFiConfig
    thread: Union[ThreadAutoConfig, ThreadExternalConfig]


class DutConfig(BaseModel):
    discriminator: str
    setup_code: str
    pairing_mode: DutPairingModeEnum
    chip_timeout: Optional[str]
    chip_use_paa_certs: bool = False
    trace_log: bool = True


class TestEnvironmentConfig(BaseModel):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"

    network: NetworkConfig
    dut_config: DutConfig
    # TODO(#490): Need to be refactored to support real PIXIT format
    test_parameters: Optional[dict[str, Any]]
