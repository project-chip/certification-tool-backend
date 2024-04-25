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

default_matter_config = {
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
    "test_parameters": None,
}

default_config_no_dut = {
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
    "test_parameters": None,
}

default_config_invalid_dut_renamed_property = {
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
        "pairing_mode_invalid": "onnetwork",
        "setup_code": "20202021",
        "discriminator": "3840",
        "chip_use_paa_certs": False,
        "trace_log": True,
    },
    "test_parameters": None,
}

default_config_invalid_dut_added_property = {
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
        "new_property": "any-value",
        "pairing_mode": "onnetwork",
        "setup_code": "20202021",
        "discriminator": "3840",
        "chip_use_paa_certs": False,
        "trace_log": True,
    },
    "test_parameters": None,
}

default_config_no_network = {
    "dut_config": {
        "pairing_mode": "onnetwork",
        "setup_code": "20202021",
        "discriminator": "3840",
        "chip_use_paa_certs": False,
        "trace_log": True,
    },
    "test_parameters": None,
}
