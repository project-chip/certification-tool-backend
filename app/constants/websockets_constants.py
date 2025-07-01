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

from fastapi import WebSocket

MESSAGE_ID_KEY = "message_id"

INVALID_JSON_ERROR_STR = "The message received is not a valid JSON object"
MISSING_TYPE_ERROR_STR = "The message is missing a type key"
NO_HANDLER_FOR_MSG_ERROR_STR = "There is no handler registered for this message type"

UDP_SOCKET_PORT = 5000
UDP_SOCKET_INTERFACE = "0.0.0.0"


# Enum Keys for different types of messages currently supported by the tool
class MessageTypeEnum(str, Enum):
    PROMPT_REQUEST = "prompt_request"
    OPTIONS_REQUEST = "options_request"
    MESSAGE_REQUEST = "message_request"
    FILE_UPLOAD_REQUEST = "file_upload_request"
    PROMPT_RESPONSE = "prompt_response"
    TEST_UPDATE = "test_update"
    TIME_OUT_NOTIFICATION = "time_out_notification"
    TEST_LOG_RECORDS = "test_log_records"
    INVALID_MESSAGE = "invalid_message"
    STREAM_VERIFICATION_REQUEST = "stream_verification_request"


class WebSocketTypeEnum(str, Enum):
    MAIN = "main"
    VIDEO = "video"


class WebSocketConnection:
    def __init__(self, websocket: WebSocket, socket_type: WebSocketTypeEnum) -> None:
        self.websocket = websocket
        self.type = socket_type


# Enum keys used with messages at the top level
class MessageKeysEnum(str, Enum):
    TYPE = "type"
    PAYLOAD = "payload"
