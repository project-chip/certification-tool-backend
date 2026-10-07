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
"""Helpers for inspecting the messages a mocked websocket broadcast() sent."""
from typing import Any
from unittest import mock

from app.constants.shared_constants import (
    MessageKeysEnum,
    MessageTypeEnum,
    TestStateEnum,
)
from app.schemas.test_run_log_entry import TestRunLogEntry
from app.test_engine.test_ui_observer import TestUpdateTypeEnum


def broadcast_payloads(
    broadcast_mock: mock.AsyncMock, message_type: MessageTypeEnum
) -> list[Any]:
    """The payloads of the broadcast messages of one type, in send order."""
    return [
        call.args[0][MessageKeysEnum.PAYLOAD]
        for call in broadcast_mock.call_args_list
        if call.args[0][MessageKeysEnum.TYPE] == message_type
    ]


def log_record_payloads(
    broadcast_mock: mock.AsyncMock,
) -> list[list[TestRunLogEntry]]:
    """The broadcast TEST_LOG_RECORDS payloads, one list of entries per
    message."""
    return broadcast_payloads(broadcast_mock, MessageTypeEnum.TEST_LOG_RECORDS)


def logged_messages(broadcast_mock: mock.AsyncMock) -> list[str]:
    """The messages of every broadcast log entry, in send order."""
    return [
        entry.message
        for payload in log_record_payloads(broadcast_mock)
        for entry in payload
    ]


def run_states(broadcast_mock: mock.AsyncMock) -> list[TestStateEnum]:
    """The states of the broadcast test run state updates, in send order."""
    return [
        payload["body"]["state"]
        for payload in broadcast_payloads(broadcast_mock, MessageTypeEnum.TEST_UPDATE)
        if payload["test_type"] == TestUpdateTypeEnum.TEST_RUN
    ]


def assert_final_run_state_sent_last(
    broadcast_mock: mock.AsyncMock, state: TestStateEnum, logs_complete: bool
) -> None:
    """Assert the last broadcast message is the run's terminal state update.

    Args:
        broadcast_mock (mock.AsyncMock): The patched websocket broadcast.
        state (TestStateEnum): The expected terminal run state.
        logs_complete (bool): The expected logs_complete flag.
    """
    last_message = broadcast_mock.call_args_list[-1].args[0]
    assert last_message[MessageKeysEnum.TYPE] == MessageTypeEnum.TEST_UPDATE
    body = last_message[MessageKeysEnum.PAYLOAD]["body"]
    assert body["state"] == state
    assert body["logs_complete"] is logs_complete
