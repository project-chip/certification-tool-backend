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
#

from enum import Enum

"""
    Shared constants across the application.
"""


class TestStateEnum(str, Enum):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"
    PENDING = "pending"
    EXECUTING = "executing"
    PENDING_ACTUATION = "pending_actuation"  # TODO: Do we need this
    PASSED = "passed"  # Test Passed with no issued
    FAILED = "failed"  # Test Failed
    ERROR = "error"  # Test Error due to tool setup or environment
    NOT_APPLICABLE = "not_applicable"  # Test is not applicable - e.g. PICS mismatch
    CANCELLED = "cancelled"


# Enum Keys for different types of messages currently supported by the tool
class MessageTypeEnum(str, Enum):
    PROMPT_REQUEST = "prompt_request"
    PROMPT_RESPONSE = "prompt_response"
    OPTIONS_REQUEST = "options_request"
    MESSAGE_REQUEST = "message_request"
    TEST_UPDATE = "test_update"
    FILE_UPLOAD_REQUEST = "file_upload_request"
    TIME_OUT_NOTIFICATION = "time_out_notification"
    TEST_LOG_RECORDS = "test_log_records"
    INVALID_MESSAGE = "invalid_message"
    STREAM_VERIFICATION_REQUEST = "stream_verification_request"
    IMAGE_VERIFICATION_REQUEST = "image_verification_request"
    TWO_WAY_TALK_VERIFICATION_REQUEST = "two_way_talk_verification_request"
    PUSH_AV_STREAM_VERIFICATION_REQUEST = "push_av_stream_verification_request"


# Enum keys used with messages at the top level
class MessageKeysEnum(str, Enum):
    TYPE = "type"
    PAYLOAD = "payload"


# Enum for DUT Pairing Modes
class DutPairingModeEnum(str, Enum):
    ON_NETWORK = "onnetwork"
    BLE_WIFI = "ble-wifi"
    BLE_THREAD = "ble-thread"
    WIFIPAF_WIFI = "wifipaf-wifi"
    NFC_THREAD = "nfc-thread"
