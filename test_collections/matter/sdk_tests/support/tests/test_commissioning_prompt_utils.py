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
# type: ignore
# Ignore mypy type check for this file

from unittest import mock

import pytest

from app.constants.shared_constants import DutPairingModeEnum
from app.user_prompt_support.constants import UserResponseStatusEnum
from app.user_prompt_support.prompt_response import PromptResponse

from ..utils import (
    PromptOption,
    dut_commissioning_hint,
    prompt_for_commissioning_mode,
)

BASE_PROMPT = "Make sure the DUT is in Commissioning Mode"


def _config(**dut_config) -> dict:
    return {"dut_config": {"pairing_mode": "onnetwork", **dut_config}}


def test_hint_lists_discriminator_and_setup_code() -> None:
    config = _config(discriminator="3437", setup_code="9198814")

    assert (
        dut_commissioning_hint(config)
        == "looking for discriminator 3437, setup code 9198814"
    )


def test_hint_lists_only_the_values_that_are_set() -> None:
    assert (
        dut_commissioning_hint(_config(discriminator="3437"))
        == "looking for discriminator 3437"
    )
    assert (
        dut_commissioning_hint(_config(setup_code="9198814"))
        == "looking for setup code 9198814"
    )


def test_hint_accepts_pairing_mode_enum() -> None:
    config = _config(discriminator="3437", setup_code="9198814")
    config["dut_config"]["pairing_mode"] = DutPairingModeEnum.BLE_WIFI

    assert dut_commissioning_hint(config) is not None


@pytest.mark.parametrize("pairing_mode", ["nfc-wifi", "nfc-thread"])
@pytest.mark.parametrize("as_enum", [False, True])
def test_hint_is_omitted_for_nfc_pairing(pairing_mode: str, as_enum: bool) -> None:
    """With NFC the onboarding data comes from the tag, not from the config."""
    config = _config(discriminator="3437", setup_code="9198814")
    config["dut_config"]["pairing_mode"] = (
        DutPairingModeEnum(pairing_mode) if as_enum else pairing_mode
    )

    assert dut_commissioning_hint(config) is None


@pytest.mark.parametrize(
    "config",
    [
        None,
        {},
        {"dut_config": None},
        {"dut_config": {"pairing_mode": "onnetwork"}},
        _config(discriminator="", setup_code=None),
        mock.Mock(),
    ],
)
def test_hint_is_none_when_nothing_to_show(config) -> None:
    assert dut_commissioning_hint(config) is None


async def _prompt_text(**kwargs) -> str:
    prompt_support = mock.Mock()
    prompt_support.send_prompt_request = mock.AsyncMock(
        return_value=PromptResponse(
            response=PromptOption.PASS, status_code=UserResponseStatusEnum.OKAY
        )
    )

    await prompt_for_commissioning_mode(prompt_support, mock.Mock(), **kwargs)

    return prompt_support.send_prompt_request.await_args.args[0].prompt


@pytest.mark.asyncio
async def test_prompt_is_unchanged_without_hint() -> None:
    assert await _prompt_text() == BASE_PROMPT


@pytest.mark.asyncio
async def test_prompt_shows_hint() -> None:
    prompt = await _prompt_text(
        dut_hint="looking for discriminator 3437, setup code 9198814"
    )

    assert (
        prompt
        == f"{BASE_PROMPT} (looking for discriminator 3437, setup code 9198814)"
    )
