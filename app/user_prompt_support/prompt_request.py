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
from typing import Dict, Optional

from pydantic import BaseModel

default_timeout_s = 60  # Seconds


class PromptRequestType(str, Enum):
    BASE = "base"
    OPTIONS = "options"
    TEXT = "text"
    FILE = "file"


class PromptRequest(BaseModel):
    prompt: Optional[str]
    timeout: int = default_timeout_s
    __type: PromptRequestType = PromptRequestType.BASE

    @property
    def type(self) -> PromptRequestType:
        return self.__type


class OptionsSelectPromptRequest(PromptRequest):
    __type = PromptRequestType.OPTIONS
    options: Dict[str, int]


class TextInputPromptRequest(PromptRequest):
    __type = PromptRequestType.TEXT
    placeholder_text: Optional[str]
    default_value: Optional[str]
    regex_pattern: Optional[str]


class UploadFilePromptRequest(PromptRequest):
    __type = PromptRequestType.FILE
    path: str = "api/v1/test_run_execution/file_upload/"
