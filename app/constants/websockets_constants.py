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

MESSAGE_ID_KEY = "message_id"

INVALID_JSON_ERROR_STR = "The message received is not a valid JSON object"
MISSING_TYPE_ERROR_STR = "The message is missing a type key"
NO_HANDLER_FOR_MSG_ERROR_STR = "There is no handler registered for this message type"


# Enum Keys for different types of messages currently supported by the tool
class MessageTypeEnum(str, Enum):
    PROMPT_REQUEST = "prompt_request"
    OPTIONS_REQUEST = "options_request"
    MESSAGE_REQUEST = "message_request"    
    PROMPT_RESPONSE = "prompt_response"
    TEST_UPDATE = "test_update"
    TIME_OUT_NOTIFICATION = "time_out_notification"
    TEST_LOG_RECORDS = "test_log_records"
    INVALID_MESSAGE = "invalid_message"


# Enum keys used with messages at the top level
class MessageKeysEnum(str, Enum):
    TYPE = "type"
    PAYLOAD = "payload"
