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
from asyncio import Task
from datetime import datetime
from typing import Callable, Generator, Optional, Union

from loguru import logger
from sqlalchemy import inspect
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

# How often pending updates are flushed to the DB while a run is in progress,
# instead of only once at the very end of the run.
DB_FLUSH_INTERVAL = 2.0


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
        self.__flush_task: Optional[Task] = None
        self.__stop_flushing = asyncio.Event()

    def start(self) -> None:
        """Start periodically flushing pending updates to the DB.

        Without this, __pending only ever drains in the single apply_updates()
        call made after the run finishes, so a run's full log/state is written
        to the DB in one large commit at the end instead of incrementally.
        Not started automatically in __init__ so unit tests that only
        exercise dispatch()/apply_updates() directly aren't left with a
        dangling background task.
        """
        self.__flush_task = asyncio.create_task(self.__periodically_apply_updates())

    async def __periodically_apply_updates(self) -> None:
        # Only wait on the stop event between flushes, never cancel a flush
        # itself: dispatch() can still be mutating ORM objects that a
        # half-finished apply_updates() removed from __pending but hasn't
        # saved yet, so cutting it off mid-save would drop or corrupt that
        # update instead of just deferring it to the next tick.
        while not self.__stop_flushing.is_set():
            try:
                await asyncio.wait_for(
                    self.__stop_flushing.wait(), timeout=DB_FLUSH_INTERVAL
                )
            except asyncio.TimeoutError:
                pass
            await self.apply_updates()

    async def finish(self) -> None:
        """Stop periodic flushing and apply any updates still pending."""
        if self.__flush_task is not None:
            self.__stop_flushing.set()
            await self.__flush_task
            self.__flush_task = None
        await self.apply_updates()

    async def apply_updates(self) -> None:
        pending = self.__pending
        self.__pending = {}
        for data in pending.values():
            await self.__save(data)

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

        # Append only the log entries produced since the last update, as rows on
        # the related table. This keeps writes O(n) over the run instead of
        # rewriting the whole log on every flush.
        new_entries = observable.log[self.__entries_written :]
        for entry in new_entries:
            test_run_execution.log.append(
                TestRunLogEntry(
                    level=entry.level,
                    timestamp=entry.timestamp,
                    message=entry.message,
                    test_suite_execution_index=entry.test_suite_execution_index,
                    test_case_execution_index=entry.test_case_execution_index,
                    test_step_execution_index=entry.test_step_execution_index,
                )
            )
        self.__entries_written += len(new_entries)

        if test_run_execution.started_at is None:
            test_run_execution.started_at = datetime.now()

        if self.isCompleted(observable.state):
            test_run_execution.completed_at = datetime.now()

        self.__enqueue(test_run_execution)

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
        # session.commit() runs synchronously on the caller (the event loop
        # thread), not offloaded via asyncio.to_thread: dispatch() can mutate
        # this same Session's ORM objects at any point while the periodic
        # flush task is running, and SQLAlchemy Sessions aren't thread-safe,
        # so committing from a worker thread while the loop keeps mutating
        # objects on it is a real race, not just a theoretical one. Each
        # periodic flush's commit is small (updates since the last tick), so
        # this doesn't reintroduce the O(n) end-of-run stall the periodic
        # flush loop exists to avoid.
        session.commit()
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
