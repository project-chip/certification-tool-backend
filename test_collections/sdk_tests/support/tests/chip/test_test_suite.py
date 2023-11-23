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
# type: ignore
# Ignore mypy type check for this file

from unittest import mock

import pytest

from app.models.test_suite_execution import TestSuiteExecution
from app.user_prompt_support.constants import UserResponseStatusEnum
from app.user_prompt_support.prompt_response import PromptResponse
from test_collections.sdk_tests.support.chip.test_case import PromptOption
from test_collections.sdk_tests.support.chip.test_suite import (
    ChipSuite,
    DUTCommissioningError,
    SuiteSetupError,
)

RETRY_PROMPT_RESPONSE = PromptResponse(
    response=PromptOption.RETRY, status_code=UserResponseStatusEnum.OKAY
)
CANCEL_PROMPT_RESPONSE = PromptResponse(
    response=PromptOption.CANCEL, status_code=UserResponseStatusEnum.OKAY
)
UNEXPECTED_PROMPT_RESPONSE = PromptResponse(
    response="unexpected", status_code=UserResponseStatusEnum.INVALID
)


@pytest.mark.asyncio
async def test_test_suite_commission_dut_allowing_retries_success() -> None:
    test_suite = ChipSuite(TestSuiteExecution())

    with mock.patch.object(
        target=test_suite,
        attribute="_ChipSuite__pair_with_dut",
        side_effect=None,
    ) as mock_pair_with_dut, mock.patch.object(
        target=test_suite,
        attribute="send_prompt_request",
        return_value=None,
    ) as mock_send_prompt_request:
        await test_suite._ChipSuite__commission_dut_allowing_retries()

        mock_pair_with_dut.assert_called_once()
        mock_send_prompt_request.assert_not_called()
        assert test_suite._ChipSuite__dut_commissioned_successfully is True


@pytest.mark.asyncio
async def test_test_suite_commission_dut_allowing_retries_retry_success() -> None:
    test_suite = ChipSuite(TestSuiteExecution())

    with mock.patch.object(
        target=test_suite,
        attribute="_ChipSuite__pair_with_dut",
        side_effect=[
            DUTCommissioningError(),
            DUTCommissioningError(),
            DUTCommissioningError(),
            None,
        ],
    ) as mock_pair_with_dut, mock.patch.object(
        target=test_suite,
        attribute="send_prompt_request",
        side_effect=[
            RETRY_PROMPT_RESPONSE,
            RETRY_PROMPT_RESPONSE,
            RETRY_PROMPT_RESPONSE,
        ],
    ) as mock_send_prompt_request:
        await test_suite._ChipSuite__commission_dut_allowing_retries()

        # __pair_with_dut should be called 3 times with an error and once with success
        assert mock_pair_with_dut.call_count == 4
        # mock_send_prompt_request should be called once for each error
        assert mock_send_prompt_request.call_count == 3
        assert test_suite._ChipSuite__dut_commissioned_successfully is True


@pytest.mark.asyncio
async def test_test_suite_commission_dut_allowing_retries_retry_cancel() -> None:
    test_suite = ChipSuite(TestSuiteExecution())

    with mock.patch.object(
        target=test_suite,
        attribute="_ChipSuite__pair_with_dut",
        side_effect=[
            DUTCommissioningError(),
            DUTCommissioningError(),
            DUTCommissioningError(),
        ],
    ) as mock_pair_with_dut, mock.patch.object(
        target=test_suite,
        attribute="send_prompt_request",
        side_effect=[
            RETRY_PROMPT_RESPONSE,
            RETRY_PROMPT_RESPONSE,
            CANCEL_PROMPT_RESPONSE,
        ],
    ) as mock_send_prompt_request:
        with pytest.raises(SuiteSetupError):
            await test_suite._ChipSuite__commission_dut_allowing_retries()

        # __pair_with_dut should be called 3 times with an error
        assert mock_pair_with_dut.call_count == 3
        # mock_send_prompt_request should be called once for each error
        assert mock_send_prompt_request.call_count == 3
        assert test_suite._ChipSuite__dut_commissioned_successfully is False


@pytest.mark.asyncio
async def test_test_suite_commission_dut_allowing_retries_retry_unexpected() -> None:
    test_suite = ChipSuite(TestSuiteExecution())

    with mock.patch.object(
        target=test_suite,
        attribute="_ChipSuite__pair_with_dut",
        side_effect=[
            DUTCommissioningError(),
            DUTCommissioningError(),
            DUTCommissioningError(),
        ],
    ) as mock_pair_with_dut, mock.patch.object(
        target=test_suite,
        attribute="send_prompt_request",
        side_effect=[
            RETRY_PROMPT_RESPONSE,
            RETRY_PROMPT_RESPONSE,
            UNEXPECTED_PROMPT_RESPONSE,
        ],
    ) as mock_send_prompt_request:
        with pytest.raises(ValueError):
            await test_suite._ChipSuite__commission_dut_allowing_retries()

        # __pair_with_dut should be called 3 times with an error
        assert mock_pair_with_dut.call_count == 3
        # mock_send_prompt_request should be called once for each error
        assert mock_send_prompt_request.call_count == 3
        assert test_suite._ChipSuite__dut_commissioned_successfully is False
