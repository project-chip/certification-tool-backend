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
from .constants import UserResponseStatusEnum
from .prompt_request import PromptRequest
from .prompt_response import PromptResponse
from .user_prompt_manager import user_prompt_manager


class UserPromptError(Exception):
    pass


class InvalidPromptInput(Exception):
    pass


class UserPromptSupport(object):
    async def send_prompt_request(
        self, prompt_request: PromptRequest
    ) -> PromptResponse:
        response = await user_prompt_manager.send_prompt_request(prompt_request)

        if response is None:
            raise UserPromptError("No prompt response returned")
        return response

    async def invoke_prompt_and_get_str_response(
        self, prompt_request: PromptRequest
    ) -> str:
        prompt_response = await self.send_prompt_request(prompt_request=prompt_request)
        if (
            prompt_response.status_code != UserResponseStatusEnum.OKAY
            or not prompt_response.response_str
        ):
            raise InvalidPromptInput(
                f"""Expected input type str but received {type(prompt_response)}.
                Received user response {prompt_response}."""
            )
        return prompt_response.response_str

    async def invoke_prompt_and_get_int_response(
        self, prompt_request: PromptRequest
    ) -> int:
        prompt_response = await self.send_prompt_request(prompt_request=prompt_request)
        if (
            prompt_response.status_code != UserResponseStatusEnum.OKAY
            or not isinstance(prompt_response.response, int)
            or isinstance(prompt_response.response, bool)
        ):
            raise InvalidPromptInput(
                f"""Expected input type int but received {type(prompt_response)}.
                Received user response {prompt_response}."""
            )
        return prompt_response.response
