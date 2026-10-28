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
from app.user_prompt_support.constants import UserResponseStatusEnum
from app.user_prompt_support.prompt_response import PromptResponse


def test_unexpected_response_message_reports_timeout() -> None:
    response = PromptResponse(response=None, status_code=UserResponseStatusEnum.TIMEOUT)

    message = response.unexpected_response_message("commissioning step")

    assert message == "Timed out waiting for user response during commissioning step."


def test_unexpected_response_message_reports_unknown_option() -> None:
    response = PromptResponse(response=42, status_code=UserResponseStatusEnum.OKAY)

    message = response.unexpected_response_message("commissioning step")

    assert message == "Received unknown prompt option for commissioning step: 42"
