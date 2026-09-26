#
# Copyright (c) 2026 Project CHIP Authors
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
import secrets
from typing import Callable

THREAD_NETWORK_KEY_SIZE = 16
THREAD_EXTENDED_PAN_ID_SIZE = 8
THREAD_NETWORK_NAME_SUFFIX_SIZE = 5
THREAD_BROADCAST_PAN_ID = 0xFFFF
THREAD_PROHIBITED_EXTENDED_PAN_IDS = (
    bytes(THREAD_EXTENDED_PAN_ID_SIZE),
    bytes([0xFF]) * THREAD_EXTENDED_PAN_ID_SIZE,
)

RandomBytes = Callable[[int], bytes]


def generate_thread_default_identity(
    random_bytes: RandomBytes = secrets.token_bytes,
) -> dict[str, str]:
    """Generate the Thread identity persisted in one new Project's defaults.

    Fixtures that intentionally share a Project/config continue to share this
    identity; this does not enforce a physical RCP-to-Project relationship.
    """
    network_key = random_bytes(THREAD_NETWORK_KEY_SIZE).hex()

    extended_pan_id = random_bytes(THREAD_EXTENDED_PAN_ID_SIZE)
    while extended_pan_id in THREAD_PROHIBITED_EXTENDED_PAN_IDS:
        extended_pan_id = random_bytes(THREAD_EXTENDED_PAN_ID_SIZE)

    pan_id = THREAD_BROADCAST_PAN_ID
    while pan_id == THREAD_BROADCAST_PAN_ID:
        pan_id = int.from_bytes(random_bytes(2), byteorder="big")

    network_name_suffix = random_bytes(THREAD_NETWORK_NAME_SUFFIX_SIZE).hex()

    return {
        "panid": f"0x{pan_id:04x}",
        "extpanid": extended_pan_id.hex(),
        "networkkey": network_key,
        "networkname": f"TH-{network_name_suffix}",
    }
