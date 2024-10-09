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

from __future__ import annotations

from enum import IntEnum
from typing import Callable, Optional

import loguru

from app.user_prompt_support.prompt_request import OptionsSelectPromptRequest
from app.user_prompt_support.user_prompt_support import UserPromptSupport


class PromptOption(IntEnum):
    PASS = 1
    FAIL = 2


async def prompt_for_commissioning_mode(
    prompt_support: UserPromptSupport,
    logger: loguru.Logger,
    on_success: Optional[Callable] = None,
    on_failure: Optional[Callable] = None,
) -> PromptOption:
    prompt = "Make sure the DUT is in Commissioning Mode"
    options = {
        "DONE": PromptOption.PASS,
        "FAILED": PromptOption.FAIL,
    }
    prompt_request = OptionsSelectPromptRequest(prompt=prompt, options=options)

    logger.info(f'User prompt: "{prompt}"')
    prompt_response = await prompt_support.send_prompt_request(prompt_request)

    match prompt_response.response:
        case PromptOption.PASS:
            logger.info("User chose prompt option DONE")
            if on_success:
                on_success()

        case PromptOption.FAIL:
            logger.info("User chose prompt option FAILED")
            if on_failure:
                on_failure()

        case _:
            raise ValueError(
                f"Received unknown prompt option for \
                        commissioning step: {prompt_response.response}"
            )
    return prompt_response.response
