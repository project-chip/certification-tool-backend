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
from typing import Any, Optional, Union

from pydantic import BaseModel

from .constants import UserResponseStatusEnum


class PromptResponse(BaseModel):
    response: Union[Optional[int], Optional[str]]
    status_code: UserResponseStatusEnum
    response_str: Optional[str]

    # This init was created to preserve response AS-IS as str in response_str attribute
    # There a situation when the response is a str with left zeros (e.g. '0123'),
    # it is automatically converting to int removing left zeros (e.g. 123)
    def __init__(
        self,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        # Preserve the original response
        if "response" in kwargs:
            self.response_str = kwargs["response"]
