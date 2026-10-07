#
# Copyright (c) 2025 Project CHIP Authors
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
import asyncio
from typing import Any, Dict
from unittest import mock

# from unittest.mock import call
import pytest
from sqlalchemy.orm import Session

from app.constants.shared_constants import (
    MessageKeysEnum,
    MessageTypeEnum,
    TestStateEnum,
)
from app.models.test_run_execution import TestRunExecution
from app.schemas.test_run_log_entry import TestRunLogEntry
from app.test_engine.models import TestRun
from app.test_engine.test_ui_observer import (
    LOG_RECORDS_BROADCAST_CHUNK_SIZE,
    TestUIObserver,
    TestUpdateTypeEnum,
)
from app.tests.utils.broadcast import (
    assert_final_run_state_sent_last,
    log_record_payloads,
    run_states,
)


@pytest.mark.asyncio
async def test_test_ui_observer_test_run_log(
    db: Session, broadcast_mock: mock.AsyncMock
) -> None:
    ui_observer = TestUIObserver()
    run = TestRun(test_run_execution=TestRunExecution())
    run.subscribe([ui_observer])

    # Assert send is called with all all messages appended
    log_entries = [
        TestRunLogEntry(level="info", timestamp=0.0, message="Message1"),
        TestRunLogEntry(level="info", timestamp=1.0, message="Message2"),
    ]
    run.log = log_entries
    run.notify()
    await ui_observer.complete_tasks()
    assert log_record_payloads(broadcast_mock) == [log_entries]
    broadcast_mock.reset_mock()

    # Assert send_log is not called when no new logs are added
    run.notify()
    await ui_observer.complete_tasks()
    assert log_record_payloads(broadcast_mock) == []
    broadcast_mock.reset_mock()

    # Assert only new log events are in call
    additional_log_entries = [
        TestRunLogEntry(level="info", timestamp=2.0, message="Message3"),
        TestRunLogEntry(level="info", timestamp=3.0, message="Message4"),
    ]
    run.log.extend(additional_log_entries)
    assert len(run.log) == 4
    run.notify()
    await ui_observer.complete_tasks()
    assert log_record_payloads(broadcast_mock) == [additional_log_entries]


@pytest.mark.asyncio
async def test_test_ui_observer_test_run_log_chunks_large_batches(
    db: Session, broadcast_mock: mock.AsyncMock
) -> None:
    """A single flush containing more entries than the broadcast chunk size
    must be split into multiple smaller messages instead of one large one
    (regression test for issue #1072's unbounded-broadcast-batch bug, where
    a dense burst of log lines could become a single multi-MB websocket
    message with no yield point during serialization)."""
    ui_observer = TestUIObserver()
    run = TestRun(test_run_execution=TestRunExecution())
    run.subscribe([ui_observer])

    extra = 50
    log_entries = [
        TestRunLogEntry(level="info", timestamp=float(i), message=f"Message{i}")
        for i in range(LOG_RECORDS_BROADCAST_CHUNK_SIZE + extra)
    ]
    run.log = log_entries
    run.notify()
    await ui_observer.complete_tasks()

    chunks = log_record_payloads(broadcast_mock)
    assert len(chunks) == 2
    assert chunks[0] == log_entries[:LOG_RECORDS_BROADCAST_CHUNK_SIZE]
    assert chunks[1] == log_entries[LOG_RECORDS_BROADCAST_CHUNK_SIZE:]


@pytest.mark.asyncio
async def test_test_ui_observer_test_run_log_chunks_delivered_in_order(
    db: Session, broadcast_mock: mock.AsyncMock
) -> None:
    """Chunks of one flush must be broadcast in order, even though the
    actual sends happen inside an awaited task rather than synchronously
    (regression test: chunks used to be scheduled as independently-created
    tasks, which don't guarantee delivery order relative to each other if
    websocket.send_text() ever actually yields, e.g. under backpressure)."""
    ui_observer = TestUIObserver()
    send_order: list[int] = []

    async def _recording_broadcast(message: dict) -> None:
        # Ignore the TEST_UPDATE state-change message notify() also fires -
        # only TEST_LOG_RECORDS chunks are relevant to ordering here.
        if message[MessageKeysEnum.TYPE] != MessageTypeEnum.TEST_LOG_RECORDS:
            return
        # Simulate send_text() genuinely yielding control (e.g. under
        # backpressure) - if chunks were sent via independent tasks, this
        # would let a later chunk's task finish first.
        payload = message[MessageKeysEnum.PAYLOAD]
        first_entry_index = int(payload[0].message.removeprefix("Message"))
        await asyncio.sleep(0)
        send_order.append(first_entry_index)

    broadcast_mock.side_effect = _recording_broadcast

    run = TestRun(test_run_execution=TestRunExecution())
    run.subscribe([ui_observer])

    extra = 50
    log_entries = [
        TestRunLogEntry(level="info", timestamp=float(i), message=f"Message{i}")
        for i in range(LOG_RECORDS_BROADCAST_CHUNK_SIZE + extra)
    ]
    run.log = log_entries
    run.notify()
    await ui_observer.complete_tasks()

    assert send_order == [0, LOG_RECORDS_BROADCAST_CHUNK_SIZE]


def _completed_run(ui_observer: TestUIObserver) -> TestRun:
    """A test run observed by ui_observer that has executed and completed."""
    run = TestRun(test_run_execution=TestRunExecution())
    run.subscribe([ui_observer])
    run.mark_as_executing()
    run.mark_as_completed()
    return run


@pytest.mark.asyncio
async def test_test_ui_observer_sends_non_terminal_run_state_immediately(
    db: Session, broadcast_mock: mock.AsyncMock
) -> None:
    ui_observer = TestUIObserver()
    run = TestRun(test_run_execution=TestRunExecution())
    run.subscribe([ui_observer])

    run.mark_as_executing()
    await ui_observer.complete_tasks()

    assert run_states(broadcast_mock) == [TestStateEnum.EXECUTING]


@pytest.mark.asyncio
@pytest.mark.parametrize("logs_complete", [True, False])
async def test_test_ui_observer_holds_terminal_run_state_until_final_send(
    db: Session, broadcast_mock: mock.AsyncMock, logs_complete: bool
) -> None:
    """The terminal run state must not be broadcast when the run completes, but
    only from send_final_run_state(), after the log records flushed in between
    - so clients can treat it as the run's last message."""
    ui_observer = TestUIObserver()
    run = _completed_run(ui_observer)
    await ui_observer.complete_tasks()

    # Not sent yet
    assert run_states(broadcast_mock) == [TestStateEnum.EXECUTING]

    # Final log flush, after the run completed
    final_logs = [TestRunLogEntry(level="info", timestamp=0.0, message="Last")]
    run.append_log_entries(final_logs)

    await ui_observer.send_final_run_state(logs_complete=logs_complete)

    last_message = broadcast_mock.call_args_list[-1].args[0]
    assert last_message[MessageKeysEnum.TYPE] == MessageTypeEnum.TEST_UPDATE
    assert last_message[MessageKeysEnum.PAYLOAD] == {
        "test_type": TestUpdateTypeEnum.TEST_RUN,
        "body": {
            "test_run_execution_id": None,
            "state": run.state,
            "logs_complete": logs_complete,
        },
    }
    assert log_record_payloads(broadcast_mock) == [final_logs]


@pytest.mark.asyncio
async def test_test_ui_observer_final_run_state_waits_for_queued_log_records(
    db: Session, broadcast_mock: mock.AsyncMock
) -> None:
    """The terminal run state must go out after log records that were queued
    before it, even if sending those records yields (e.g. backpressure)."""
    ui_observer = TestUIObserver()
    send_order: list[str] = []

    async def _recording_broadcast(message: dict) -> None:
        await asyncio.sleep(0)
        send_order.append(message[MessageKeysEnum.TYPE])

    broadcast_mock.side_effect = _recording_broadcast

    run = _completed_run(ui_observer)
    run.append_log_entries(
        [TestRunLogEntry(level="info", timestamp=0.0, message="Last")]
    )

    await ui_observer.send_final_run_state(logs_complete=True)

    assert send_order[-2:] == [
        MessageTypeEnum.TEST_LOG_RECORDS,
        MessageTypeEnum.TEST_UPDATE,
    ]


@pytest.mark.asyncio
async def test_test_ui_observer_final_run_state_sent_when_queued_update_fails(
    db: Session, broadcast_mock: mock.AsyncMock
) -> None:
    """A queued update that fails to send must not stop the terminal run state
    from going out, nor let it overtake updates queued before it."""
    ui_observer = TestUIObserver()

    async def _failing_log_broadcast(message: dict) -> None:
        await asyncio.sleep(0)
        if message[MessageKeysEnum.TYPE] == MessageTypeEnum.TEST_LOG_RECORDS:
            raise RuntimeError("Send failed")

    broadcast_mock.side_effect = _failing_log_broadcast

    run = _completed_run(ui_observer)
    run.append_log_entries(
        [TestRunLogEntry(level="info", timestamp=0.0, message="Last")]
    )

    await ui_observer.send_final_run_state(logs_complete=True)

    assert run_states(broadcast_mock) == [
        TestStateEnum.EXECUTING,
        run.state,
    ]
    assert_final_run_state_sent_last(broadcast_mock, run.state, logs_complete=True)


@pytest.mark.asyncio
async def test_test_ui_observer_final_run_state_sent_once(
    db: Session, broadcast_mock: mock.AsyncMock
) -> None:
    ui_observer = TestUIObserver()

    # Nothing held back: no-op
    await ui_observer.send_final_run_state(logs_complete=True)
    assert broadcast_mock.call_count == 0

    run = _completed_run(ui_observer)

    await ui_observer.send_final_run_state(logs_complete=True)
    await ui_observer.send_final_run_state(logs_complete=True)

    assert run_states(broadcast_mock) == [
        TestStateEnum.EXECUTING,
        run.state,
    ]


def __expected_test_run_log_dict() -> Dict[str, Any]:
    return {
        MessageKeysEnum.TYPE: MessageTypeEnum.TEST_LOG_RECORDS,
        MessageKeysEnum.PAYLOAD: [Any],
    }


def __expected_test_run_state_dict(id: int) -> Dict[str, Any]:
    return {
        MessageKeysEnum.TYPE: MessageTypeEnum.TEST_UPDATE,
        MessageKeysEnum.PAYLOAD: {
            "test_type": TestUpdateTypeEnum.TEST_RUN,
            "body": {"test_run_execution_id": id, "state": TestStateEnum.EXECUTING},
        },
    }


def __expected_test_suite_dict(index: int) -> Dict[str, Any]:
    return {
        MessageKeysEnum.TYPE: MessageTypeEnum.TEST_UPDATE,
        MessageKeysEnum.PAYLOAD: {
            "test_type": TestUpdateTypeEnum.TEST_SUITE,
            "body": {
                "test_suite_execution_index": index,
                "state": TestStateEnum.EXECUTING,
                "errors": [],
            },
        },
    }


def __expected_test_case_dict(index: int, suite_index: int) -> Dict[str, Any]:
    return {
        MessageKeysEnum.TYPE: MessageTypeEnum.TEST_UPDATE,
        MessageKeysEnum.PAYLOAD: {
            "test_type": TestUpdateTypeEnum.TEST_CASE,
            "body": {
                "test_suite_execution_index": suite_index,
                "test_case_execution_index": index,
                "state": TestStateEnum.EXECUTING,
                "errors": [],
            },
        },
    }


def __expected_test_step_dict(
    index: int, case_index: int, suite_index: int
) -> Dict[str, Any]:
    return {
        MessageKeysEnum.TYPE: MessageTypeEnum.TEST_UPDATE,
        MessageKeysEnum.PAYLOAD: {
            "test_type": TestUpdateTypeEnum.TEST_STEP,
            "body": {
                "test_suite_execution_index": suite_index,
                "test_case_execution_index": case_index,
                "test_step_execution_index": index,
                "state": TestStateEnum.EXECUTING,
                "errors": [],
                "failures": [],
            },
        },
    }
