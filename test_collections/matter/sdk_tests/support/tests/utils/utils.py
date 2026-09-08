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
from typing import Any

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

default_matter_config_with_th_config: dict[str, Any] = {
    **default_matter_config,
    "th_config": {
        "prompt_timeout_seconds": 120,
        "enable_realtime_python_test_logs": True,
        "enable_container_logs": True,
    },
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

# THREAD with ba_host, ba_port, and operational_dataset_hex (valid)
default_config_thread_valid = {
    "network": {
        "fabric_id": "0",
        "thread": {
            "operational_dataset_hex": "0e080000000000010000000300001335060004001fffe00"
            "208fedcba9876543210070800000000000000050800000000000000030d4f70656e5468726"
            "5616444656d6f01021234041011223344556677889900aabbccddeeff000c0402a0f7f8",
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

# THREAD without ba_host (invalid)
default_config_thread_no_ba_host = {
    "network": {
        "fabric_id": "0",
        "thread": {
            "operational_dataset_hex": "0e080000000000010000000300001335060004001fffe00"
            "208fedcba9876543210070800000000000000050800000000000000030d4f70656e5468726"
            "5616444656d6f01021234041011223344556677889900aabbccddeeff000c0402a0f7f8",
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

# THREAD without ba_port (invalid)
default_config_thread_no_ba_port = {
    "network": {
        "fabric_id": "0",
        "thread": {
            "operational_dataset_hex": "0e080000000000010000000300001335060004001fffe00"
            "208fedcba9876543210070800000000000000050800000000000000030d4f70656e5468726"
            "5616444656d6f01021234041011223344556677889900aabbccddeeff000c0402a0f7f8",
            "ba_host": "127.0.0.1",
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
