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
from datetime import datetime
from typing import Callable, Generator, Optional, Union

from loguru import logger
from sqlalchemy import func, insert, inspect, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import TestStateEnum
from app.models.test_case_execution import TestCaseExecution
from app.models.test_run_execution import TestRunExecution
from app.models.test_run_log_entry import TestRunLogEntry
from app.models.test_step_execution import TestStepExecution
from app.models.test_suite_execution import TestSuiteExecution
from app.test_engine.models import TestCase, TestRun, TestStep, TestSuite
from app.test_engine.test_observer import Observer

ExecutionObj = Union[
    TestCaseExecution, TestStepExecution, TestSuiteExecution, TestRunExecution
]

# Max rows per bulk INSERT, to bound statement/memory size when a run flushes a
# very large backlog (hundreds of thousands of entries) in one go.
LOG_INSERT_CHUNK_SIZE = 5000


class TestDBObserver(Observer):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"

    def __init__(
        self, db_generator: Callable[[], Generator[Session, None, None]] = get_db
    ) -> None:
        self.__db_generator = db_generator
        # Keyed by id(execution_obj) instead of a plain queue: dispatch() can
        # re-notify the SAME object many times (e.g. once per 0.5s log-flush
        # tick for the whole run) before apply_updates() ever drains this -
        # a dict collapses those into a single pending save per distinct
        # object instead of committing the same (increasingly large) object
        # redundantly once per notification.
        self.__pending: dict[int, ExecutionObj] = {}
        # How many of the run's in-memory log entries have been turned into
        # rows. Counted here rather than read back from the relationship: this
        # observer is built per run (see TestRunner.run) and is the only thing
        # appending, while a PENDING execution can still carry entries from an
        # earlier attempt that was interrupted before it left PENDING. Taking
        # the position from the persisted collection would then skip exactly
        # that many new entries.
        self.__entries_written = 0
        # Next seq to assign to a new log row, initialized lazily from
        # MAX(seq)+1 for the run (a resumed PENDING run may already have rows,
        # see above) and then tracked here, so the run's log relationship is
        # never loaded just to find the append position.
        self.__next_seq: Optional[int] = None
        # New log rows waiting to be bulk-inserted, as plain column dicts
        # instead of ORM objects: building and unit-of-work-tracking one
        # TestRunLogEntry per line is the dominant cost for large logs.
        self.__pending_log_rows: list[dict] = []

    async def apply_updates(self) -> None:
        pending = self.__pending
        self.__pending = {}
        log_rows = self.__pending_log_rows
        self.__pending_log_rows = []

        if log_rows:
            # Same session as the state save below, so the rows commit together
            # with the run's state. test_run_execution is always enqueued
            # alongside new rows, so there is always a pending object to
            # commit through.
            session = self.__session_for(pending)
            await asyncio.to_thread(self.__bulk_insert_log_rows, session, log_rows)

        for data in pending.values():
            await self.__save(data)

    def __session_for(self, pending: dict[int, ExecutionObj]) -> Session:
        for execution_obj in pending.values():
            insp = inspect(execution_obj)
            if insp is not None and insp.session is not None:
                return insp.session
        return next(self.__db_generator())

    @staticmethod
    def __bulk_insert_log_rows(session: Session, rows: list[dict]) -> None:
        for i in range(0, len(rows), LOG_INSERT_CHUNK_SIZE):
            chunk = rows[i : i + LOG_INSERT_CHUNK_SIZE]
            session.execute(insert(TestRunLogEntry), chunk)

    def dispatch(
        self, observable: Union[TestRun, TestSuite, TestCase, TestStep]
    ) -> None:
        logger.debug("Received Dispatch event")
        if observable is not None:
            if isinstance(observable, TestRun):
                self.__onTestRunUpdate(observable)
            elif isinstance(observable, TestSuite):
                self.__onTestSuiteUpdate(observable)
            elif isinstance(observable, TestCase):
                self.__onTestCaseUpdate(observable)
            elif isinstance(observable, TestStep):
                self.__onTestStepUpdate(observable)

    def __enqueue(self, execution_obj: ExecutionObj) -> None:
        self.__pending[id(execution_obj)] = execution_obj

    def __onTestRunUpdate(self, observable: "TestRun") -> None:
        logger.debug("Test Run Observer received", observable)
        test_run_execution = observable.test_run_execution
        test_run_execution.state = observable.state

        # Stage only the log entries produced since the last update, as plain
        # rows for a bulk insert in apply_updates(). This keeps writes O(n) over
        # the run instead of rewriting the whole log on every flush. seq is
        # assigned here (what ordering_list would do on an ORM append), since
        # the bulk path bypasses the relationship.
        new_entries = observable.log[self.__entries_written :]
        if new_entries:
            if self.__next_seq is None:
                self.__next_seq = self.__initial_seq(test_run_execution)
            self.__pending_log_rows.extend(
                {
                    "test_run_execution_id": test_run_execution.id,
                    "seq": self.__next_seq + i,
                    "level": entry.level,
                    "timestamp": entry.timestamp,
                    "message": entry.message,
                    "test_suite_execution_index": entry.test_suite_execution_index,
                    "test_case_execution_index": entry.test_case_execution_index,
                    "test_step_execution_index": entry.test_step_execution_index,
                }
                for i, entry in enumerate(new_entries)
            )
            self.__next_seq += len(new_entries)
        self.__entries_written += len(new_entries)

        if test_run_execution.started_at is None:
            test_run_execution.started_at = datetime.now()

        if self.isCompleted(observable.state):
            test_run_execution.completed_at = datetime.now()

        self.__enqueue(test_run_execution)

    def __initial_seq(self, test_run_execution: TestRunExecution) -> int:
        insp = inspect(test_run_execution)
        session = (insp.session if insp is not None else None) or next(
            self.__db_generator()
        )
        max_seq = session.execute(
            select(func.max(TestRunLogEntry.seq)).where(
                TestRunLogEntry.test_run_execution_id == test_run_execution.id
            )
        ).scalar_one()
        return 0 if max_seq is None else max_seq + 1

    def __onTestSuiteUpdate(self, observable: "TestSuite") -> None:
        logger.debug("Test Suite Observer received", observable)
        if observable.test_suite_execution is not None:
            observable.test_suite_execution.state = observable.state
            if observable.errors:
                observable.test_suite_execution.errors = observable.errors

            if observable.test_suite_execution.started_at is None:
                observable.test_suite_execution.started_at = datetime.now()

            if self.isCompleted(observable.state):
                observable.test_suite_execution.completed_at = datetime.now()

            self.__enqueue(observable.test_suite_execution)

    def __onTestCaseUpdate(self, observable: "TestCase") -> None:
        logger.debug("Test Case Observer received", observable)
        if observable.test_case_execution is not None:
            observable.test_case_execution.state = observable.state
            if observable.errors:
                observable.test_case_execution.errors = observable.errors

            if observable.test_case_execution.started_at is None:
                observable.test_case_execution.started_at = datetime.now()

            if self.isCompleted(observable.state):
                observable.test_case_execution.completed_at = datetime.now()

            self.__enqueue(observable.test_case_execution)

    def __onTestStepUpdate(self, observable: "TestStep") -> None:
        logger.debug("Test Step Observer received", observable)
        if observable.test_step_execution is not None:
            observable.test_step_execution.state = observable.state
            if observable.errors:
                observable.test_step_execution.errors = observable.errors
            if observable.failures:
                observable.test_step_execution.failures = observable.failures

            if observable.test_step_execution.started_at is None:
                observable.test_step_execution.started_at = datetime.now()

            if self.isCompleted(observable.state):
                observable.test_step_execution.completed_at = datetime.now()

            self.__enqueue(observable.test_step_execution)

    async def __save(self, execution_obj: ExecutionObj) -> None:
        # We get the session from the model it self to avoid overriding values when
        # using a different session
        insp = inspect(execution_obj)
        if insp is None or (session := insp.session) is None:
            logger.error(
                f"No Database session found for execution object: {execution_obj}."
            )
            session = next(self.__db_generator())
            session.add(execution_obj)
        session.expire_on_commit = False
        # session.commit() is a blocking, synchronous SQLAlchemy call. It can
        # be a large write (e.g. a run's full log), so keep it off the event
        # loop rather than stalling every other coroutine (websocket pings,
        # other requests) for however long it takes.
        await asyncio.to_thread(session.commit)
        logger.debug(
            f"Saved {execution_obj.__class__} {execution_obj.id}"
            f" with state {execution_obj.state}"
        )

    @staticmethod
    def isCompleted(state: TestStateEnum) -> bool:
        if state is not TestStateEnum.PENDING and state is not TestStateEnum.EXECUTING:
            return True
        else:
            return False
