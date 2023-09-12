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
