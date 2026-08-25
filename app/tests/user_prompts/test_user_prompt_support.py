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
from unittest import mock

import pytest

from app.user_prompt_support import user_prompt_manager
from app.user_prompt_support.constants import UserResponseStatusEnum
from app.user_prompt_support.prompt_request import PromptRequest, default_timeout_s
from app.user_prompt_support.prompt_response import PromptResponse
from app.user_prompt_support.user_prompt_support import (
    UserPromptError,
    UserPromptSupport,
)


@pytest.mark.asyncio
async def test_send_prompt_request_no_response() -> None:
    """
    Validate that send_prompt_request() raises an exception upon no response.
    """
    prompt_support = UserPromptSupport()

    with mock.patch.object(
        user_prompt_manager.user_prompt_manager,
        "send_prompt_request",
        return_value=None,
    ) as send_prompt_request:
        with pytest.raises(UserPromptError):
            await prompt_support.send_prompt_request(prompt_request=mock.MagicMock())
            send_prompt_request.assert_called_once()


class _ConfigurablePromptSupport(UserPromptSupport):
    """Test-only mixin host exposing a settable `.config`, mirroring how
    TestCase/TestSuite provide it to UserPromptSupport in production."""

    def __init__(self, config: dict) -> None:
        self.config: dict = config


async def _send_and_capture_timeout(
    prompt_support: UserPromptSupport, prompt_request: PromptRequest
) -> int:
    """Send prompt_request and return the timeout that reached user_prompt_manager."""
    captured: dict = {}

    async def _capture(prompt_request: PromptRequest) -> PromptResponse:
        captured["timeout"] = prompt_request.timeout
        return PromptResponse(status_code=UserResponseStatusEnum.OKAY, response="ok")

    with mock.patch.object(
        user_prompt_manager.user_prompt_manager,
        "send_prompt_request",
        side_effect=_capture,
    ):
        await prompt_support.send_prompt_request(prompt_request=prompt_request)

    return captured["timeout"]


@pytest.mark.asyncio
async def test_send_prompt_request_resolves_timeout_from_config() -> None:
    """An unspecified timeout is resolved from th_config.prompt_timeout_seconds."""
    prompt_support = _ConfigurablePromptSupport(
        {"th_config": {"prompt_timeout_seconds": 300}}
    )

    timeout = await _send_and_capture_timeout(
        prompt_support, PromptRequest(prompt="hi")
    )

    assert timeout == 300


@pytest.mark.asyncio
async def test_send_prompt_request_falls_back_without_config_attribute() -> None:
    """No `.config` attribute at all (e.g. TestStep-based mixins) falls back safely."""
    prompt_support = UserPromptSupport()

    timeout = await _send_and_capture_timeout(
        prompt_support, PromptRequest(prompt="hi")
    )

    assert timeout == default_timeout_s


@pytest.mark.asyncio
async def test_send_prompt_request_falls_back_with_empty_config() -> None:
    """An empty/absent th_config key falls back to the default timeout."""
    prompt_support = _ConfigurablePromptSupport({})

    timeout = await _send_and_capture_timeout(
        prompt_support, PromptRequest(prompt="hi")
    )

    assert timeout == default_timeout_s


@pytest.mark.asyncio
async def test_send_prompt_request_falls_back_with_null_th_config() -> None:
    """A hand-edited "th_config": null must not raise AttributeError."""
    prompt_support = _ConfigurablePromptSupport({"th_config": None})

    timeout = await _send_and_capture_timeout(
        prompt_support, PromptRequest(prompt="hi")
    )

    assert timeout == default_timeout_s


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "prompt_timeout_seconds",
    ["not-a-number", 0, -5, True],
)
async def test_send_prompt_request_falls_back_with_malformed_value(
    prompt_timeout_seconds: object,
) -> None:
    """A malformed/invalid configured value falls back safely instead of crashing."""
    prompt_support = _ConfigurablePromptSupport(
        {"th_config": {"prompt_timeout_seconds": prompt_timeout_seconds}}
    )

    timeout = await _send_and_capture_timeout(
        prompt_support, PromptRequest(prompt="hi")
    )

    assert timeout == default_timeout_s


@pytest.mark.asyncio
async def test_send_prompt_request_explicit_timeout_wins_over_config() -> None:
    """A caller-supplied timeout is never overridden by th_config."""
    prompt_support = _ConfigurablePromptSupport(
        {"th_config": {"prompt_timeout_seconds": 300}}
    )

    timeout = await _send_and_capture_timeout(
        prompt_support, PromptRequest(prompt="hi", timeout=5)
    )

    assert timeout == 5
