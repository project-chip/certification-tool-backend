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
from typing import Any, Dict
from unittest import mock

# from unittest.mock import call
import pytest
from sqlalchemy.orm import Session

from app.constants.websockets_constants import MessageKeysEnum, MessageTypeEnum
from app.models.test_enums import TestStateEnum
from app.models.test_run_execution import TestRunExecution
from app.schemas.test_run_log_entry import TestRunLogEntry
from app.test_engine.models import TestRun
from app.test_engine.test_ui_observer import TestUIObserver, TestUpdateTypeEnum


@pytest.mark.asyncio
async def test_test_ui_observer_test_run_log(db: Session) -> None:
    ui_observer = TestUIObserver()
    with mock.patch.object(
        ui_observer, "_TestUIObserver__send_log_records_message"
    ) as send_log_mock:
        run = TestRun(test_run_execution=TestRunExecution())
        run.subscribe([ui_observer])

        # Assert send is called with all all messages appended
        log_entries = [
            TestRunLogEntry(level="info", timestamp=0.0, message="Message1"),
            TestRunLogEntry(level="info", timestamp=1.0, message="Message2"),
        ]
        run.log = log_entries
        run.notify()
        send_log_mock.assert_called_once_with(log_entries)
        send_log_mock.reset_mock()

        # Assert send_log is not called when no new logs are added
        run.notify()
        send_log_mock.assert_not_called()
        send_log_mock.reset_mock()

        # Assert only new log events are in call
        additional_log_entries = [
            TestRunLogEntry(level="info", timestamp=2.0, message="Message3"),
            TestRunLogEntry(level="info", timestamp=3.0, message="Message4"),
        ]
        run.log.extend(additional_log_entries)
        assert len(run.log) == 4
        run.notify()
        send_log_mock.assert_called_once_with(additional_log_entries)

        # cleanup
        await ui_observer.complete_tasks()


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
