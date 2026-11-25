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
from pathlib import Path
from typing import Callable, Optional

import loguru

from app.constants.shared_constants import NFC_PAIRING_MODES
from app.user_prompt_support.prompt_request import OptionsSelectPromptRequest
from app.user_prompt_support.user_prompt_support import UserPromptSupport

ADMIN_STORAGE_FILE_DEFAULT_NAME = "admin_storage.json"
# Retrieve the root folder
ADMIN_STORAGE_FILE_HOST_PATH = Path(__file__).parents[3].parent
ADMIN_STORAGE_FILE_HOST = ADMIN_STORAGE_FILE_HOST_PATH.joinpath(
    ADMIN_STORAGE_FILE_DEFAULT_NAME
)

ADMIN_STORAGE_FILE_CONTAINER_DEFAULT_PATH = Path("/root")


class PromptOption(IntEnum):
    PASS = 1
    FAIL = 2


async def __prompt_pass_fail_options(
    prompt_support: UserPromptSupport,
    logger: loguru.Logger,
    prompt: str,
    options: dict,
    on_success: Optional[Callable] = None,
    on_failure: Optional[Callable] = None,
) -> PromptOption:
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
                prompt_response.unexpected_response_message("commissioning step")
            )
    return prompt_response.response


async def prompt_for_commissioning_mode(
    prompt_support: UserPromptSupport,
    logger: loguru.Logger,
    on_success: Optional[Callable] = None,
    on_failure: Optional[Callable] = None,
    dut_hint: Optional[str] = None,
) -> PromptOption:
    options = {
        "DONE": PromptOption.PASS,
        "FAILED": PromptOption.FAIL,
    }

    prompt = "Make sure the DUT is in Commissioning Mode"
    if dut_hint:
        prompt += f" ({dut_hint})"

    prompt_response = await __prompt_pass_fail_options(
        prompt_support=prompt_support,
        logger=logger,
        prompt=prompt,
        options=options,
        on_success=on_success,
        on_failure=on_failure,
    )

    return prompt_response


def dut_commissioning_hint(config: Optional[dict]) -> Optional[str]:
    """Describe the DUT values the Test Harness will look for when commissioning.

    Shown in the commissioning prompts so a DUT advertising other values is noticed
    before waiting for the discovery to time out. Returns None when there is nothing
    to show, e.g. NFC pairing, where the onboarding data is read from the NFC tag.
    """
    dut_config = config.get("dut_config") if isinstance(config, dict) else None
    if not isinstance(dut_config, dict):
        return None

    # The config may carry the pairing mode as a plain string or as the enum.
    pairing_mode = dut_config.get("pairing_mode")
    if getattr(pairing_mode, "value", pairing_mode) in NFC_PAIRING_MODES:
        return None

    details = [
        f"{label} {value}"
        for label, value in (
            ("discriminator", dut_config.get("discriminator")),
            ("setup code", dut_config.get("setup_code")),
        )
        if value
    ]
    if not details:
        return None
    return "looking for " + ", ".join(details)


async def prompt_reuse_commissioning(
    prompt_support: UserPromptSupport,
    logger: loguru.Logger,
) -> PromptOption:
    options = {
        "YES": PromptOption.PASS,
        "NO": PromptOption.FAIL,
    }

    prompt_response = await __prompt_pass_fail_options(
        prompt_support=prompt_support,
        logger=logger,
        prompt="Do you want to reuse the previous commissioning information?\n"
        "If you select NO, a new commissioning will be performed",
        options=options,
        on_success=None,
        on_failure=None,
    )

    return prompt_response
