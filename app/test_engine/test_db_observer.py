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
from sqlalchemy import func, insert, inspect, select
from sqlalchemy.engine import Engine
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
Dispatched = Union[TestRun, TestSuite, TestCase, TestStep]

# Max rows per bulk INSERT, to bound statement/memory size when a run flushes a
# very large backlog (hundreds of thousands of entries) in one go.
LOG_INSERT_CHUNK_SIZE = 5000

# How often pending updates are flushed to the DB while a run is in progress,
# instead of only once at the very end of the run.
DB_FLUSH_INTERVAL = 2.0


def _insert_log_rows(
    engine: Engine, rows: list[dict], skip_persisted: bool = False
) -> None:
    """Insert log rows in their own transaction, on their own connection.

    Runs in a worker thread. It never touches the ORM Session (which belongs to
    the event loop thread), so writing thousands of rows does not block the loop
    and a failure leaves the Session alone.

    A failure normally means nothing was committed, but not always: the commit
    itself can fail after the server applied it (e.g. the connection drops while
    the COMMIT is acknowledged). The rows of a run are inserted in seq order in
    one transaction, so after a failed attempt the caller sets `skip_persisted`
    and the highest persisted seq of the run tells which rows are already there.
    """
    with engine.begin() as connection:
        if skip_persisted:
            persisted_up_to = connection.execute(
                select(func.max(TestRunLogEntry.seq)).where(
                    TestRunLogEntry.test_run_execution_id
                    == rows[0]["test_run_execution_id"]
                )
            ).scalar_one()
            if persisted_up_to is not None:
                rows = [row for row in rows if row["seq"] > persisted_up_to]
        for i in range(0, len(rows), LOG_INSERT_CHUNK_SIZE):
            connection.execute(
                insert(TestRunLogEntry), rows[i : i + LOG_INSERT_CHUNK_SIZE]
            )


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
        # Set when a log insert failed: it may still have been committed, so the
        # next attempt checks what is persisted before inserting (see
        # _insert_log_rows).
        self.__verify_persisted = False
        # Observables dispatched since the last successful flush. A failed state
        # commit rolls the Session back, which discards the ORM changes that
        # dispatch() made; they are re-applied from these objects (the test
        # engine is the source of truth) before the next attempt.
        self.__dirty_observables: dict[int, Dispatched] = {}
        self.__reapply_observables = False
        self.__flush_task: Optional[Task] = None
        self.__stop_flushing = asyncio.Event()

    def start(self) -> None:
        """Start periodically flushing pending updates to the DB.

        Without this, __pending only drains in the single apply_updates() call
        after the run finishes, so a run's state and full log are written in
        one huge commit at the end: a crash before then loses every result
        (the run stays "pending" with an empty log), and the whole log has to
        stay in memory until then. Not started in __init__ so unit tests that
        only call dispatch()/apply_updates() aren't left with a dangling task.
        """
        self.__flush_task = asyncio.create_task(self.__periodically_apply_updates())

    async def __periodically_apply_updates(self) -> None:
        # Wait on the stop event between flushes but never cancel a flush
        # itself: cutting apply_updates() off mid-save could drop or corrupt
        # updates it had already taken out of __pending.
        while not self.__stop_flushing.is_set():
            try:
                await asyncio.wait_for(
                    self.__stop_flushing.wait(), timeout=DB_FLUSH_INTERVAL
                )
            except asyncio.TimeoutError:
                pass
            try:
                await self.apply_updates()
            except Exception:
                # A transient DB error must not end incremental persistence for
                # the rest of the run: log rows of a failed insert were kept and
                # are retried on the next tick.
                logger.exception("Failed to flush test run updates; will retry")

    async def finish(self) -> None:
        """Stop periodic flushing and apply any updates still pending."""
        if self.__flush_task is not None:
            self.__stop_flushing.set()
            await self.__flush_task
            self.__flush_task = None
        await self.apply_updates()

    async def apply_updates(self) -> None:
        if self.__reapply_observables:
            # A previous state commit failed and rolled the Session back,
            # discarding the ORM changes dispatch() had made: apply them again.
            # The flag is only cleared once that worked, so a failure here (e.g.
            # the DB is still down) is retried on the next flush.
            for observable in list(self.__dirty_observables.values()):
                self.dispatch(observable)
            self.__reapply_observables = False

        pending = self.__pending
        self.__pending = {}
        observables = self.__dirty_observables
        self.__dirty_observables = {}
        log_rows = self.__pending_log_rows
        self.__pending_log_rows = []

        if log_rows:
            # Own connection and transaction, in a worker thread (see
            # _insert_log_rows). test_run_execution is always enqueued alongside
            # new rows, so there is always a pending object to find the engine
            # through.
            engine = self.__session_for(pending).get_bind().engine
            try:
                await asyncio.to_thread(
                    _insert_log_rows, engine, log_rows, self.__verify_persisted
                )
            except Exception:
                # Keep the rows (before any staged since, which have higher seq
                # values) and the pending objects for the next flush. The insert
                # may have been committed anyway, so that flush checks first.
                self.__pending_log_rows[:0] = log_rows
                self.__verify_persisted = True
                for key, execution_obj in pending.items():
                    self.__pending.setdefault(key, execution_obj)
                self.__dirty_observables = {**observables, **self.__dirty_observables}
                raise
            self.__verify_persisted = False

        try:
            for data in pending.values():
                await self.__save(data)
        except Exception:
            # __save rolled the Session back, so the changes of the objects in
            # this batch are gone: re-apply them from their observables.
            self.__dirty_observables = {**observables, **self.__dirty_observables}
            self.__reapply_observables = True
            raise

    def __session_for(self, pending: dict[int, ExecutionObj]) -> Session:
        for execution_obj in pending.values():
            insp = inspect(execution_obj)
            if insp is not None and insp.session is not None:
                return insp.session
        return next(self.__db_generator())

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
            self.__dirty_observables[id(observable)] = observable

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
        new_entries = observable.log_entries_since(self.__entries_written)
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
        # The entries are now staged as rows, so TestRun may drop them from
        # memory (always report, even with nothing new: see release_log()).
        observable.release_log(self, self.__entries_written)

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
        # be a large write, but with periodic flushes each commit only covers
        # the updates since the last tick. It runs on the event loop thread
        # rather than asyncio.to_thread: dispatch() mutates this Session's ORM
        # objects at any point while a flush is running, and Sessions aren't
        # thread-safe, so committing from a worker would be a real race.
        try:
            session.commit()
        except Exception:
            # A failed commit leaves the Session unusable until it is rolled
            # back; without this, every later flush would fail as well.
            session.rollback()
            raise
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
