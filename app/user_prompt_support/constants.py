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
from enum import IntEnum

MESSAGE_EVENT_KEY = "message_event"
RESPONSE_KEY = "response"
STATUS_CODE_KEY = "status_code"


class UserResponseStatusEnum(IntEnum):
    OKAY = 0
    CANCELLED = -1
    TIMEOUT = -2
    INVALID = -3
