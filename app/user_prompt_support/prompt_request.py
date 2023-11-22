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
from typing import Dict, Optional

from pydantic import BaseModel

from app.constants.websockets_constants import MessageTypeEnum

default_timeout_s = 60  # Seconds


class PromptRequest(BaseModel):
    prompt: Optional[str]
    timeout: int = default_timeout_s

    @property
    def messageType(self) -> MessageTypeEnum:
        return MessageTypeEnum.INVALID_MESSAGE


class OptionsSelectPromptRequest(PromptRequest):
    options: Dict[str, int]

    @property
    def messageType(self) -> MessageTypeEnum:
        return MessageTypeEnum.OPTIONS_REQUEST


class TextInputPromptRequest(PromptRequest):
    placeholder_text: Optional[str]
    default_value: Optional[str]
    regex_pattern: Optional[str]

    @property
    def messageType(self) -> MessageTypeEnum:
        return MessageTypeEnum.PROMPT_REQUEST


class UploadFilePromptRequest(PromptRequest):
    path: str = "api/v1/test_run_execution/file_upload/"

    @property
    def messageType(self) -> MessageTypeEnum:
        return MessageTypeEnum.FILE_UPLOAD_REQUEST
