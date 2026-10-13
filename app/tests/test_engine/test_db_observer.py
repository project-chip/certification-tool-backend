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
from typing import Callable
from unittest import mock

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import TestStateEnum
from app.models.test_run_log_entry import TestRunLogEntry as TestRunLogEntryModel
from app.schemas.test_run_log_entry import TestRunLogEntry
from app.test_engine import test_db_observer as db_observer_module
from app.test_engine.test_db_observer import LOG_INSERT_CHUNK_SIZE, TestDBObserver
from app.test_engine.test_script_manager import TestScriptManager
from app.tests.utils.test_run_execution import (
    create_test_run_execution_with_some_test_cases,
)


@pytest.mark.asyncio
async def test_test_db_observer_test_run_started_at(db: Session) -> None:
    test_script_manager = TestScriptManager()
    test_db_observer = TestDBObserver()

    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)

    # Getting newly created test run
    test_run = test_script_manager.get_test_run(db, test_run_execution)

    # Changing Test run state to executing state
    test_run.state = TestStateEnum.EXECUTING

    test_db_observer.dispatch(test_run)
    assert TestStateEnum.EXECUTING == test_run_execution.state
    assert test_run_execution.started_at is not None
    assert test_run_execution.completed_at is None
    assert len(test_run.log) == 0

    # Note original start time
    start_time = test_run_execution.started_at

    # Wait/sleep and Dispatch again to trigger DB update
    log_entry = TestRunLogEntry(level="info", timestamp=0.0, message="Message1")
    test_run.append_log_entries([log_entry])
    await asyncio.sleep(2)

    test_db_observer.dispatch(test_run)
    await test_db_observer.apply_updates()
    assert TestStateEnum.EXECUTING == test_run_execution.state
    assert (
        db.query(TestRunLogEntryModel)
        .filter_by(test_run_execution_id=test_run_execution.id)
        .count()
        == 1
    )
    assert test_run_execution.started_at == start_time
    assert test_run_execution.completed_at is None
    assert len(test_run.log) == 1


@pytest.mark.asyncio
async def test_test_db_observer_test_suite_started_at(db: Session) -> None:
    test_script_manager = TestScriptManager()
    test_db_observer = TestDBObserver()

    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)

    # Getting newly created test suites
    test_run = test_script_manager.get_test_run(db, test_run_execution)
    test_suites = test_run.test_suites
    assert 1 == len(test_suites)
    test_suite = test_suites[0]

    # Changing Test suite state to executing state
    test_suite.state = TestStateEnum.EXECUTING

    test_db_observer.dispatch(test_suite)
    assert TestStateEnum.EXECUTING == test_run_execution.test_suite_executions[0].state
    assert test_run_execution.test_suite_executions[0].started_at is not None
    assert test_run_execution.test_suite_executions[0].completed_at is None
    assert len(test_run_execution.log) == 0

    # Note original start time
    start_time = test_run_execution.test_suite_executions[0].started_at

    # Wait/sleep and Dispatch again to trigger DB update
    test_run_execution.append_to_log(
        TestRunLogEntryModel(message="Wait for 2 seconds", level="Debug", timestamp=0)
    )
    await asyncio.sleep(2)

    test_db_observer.dispatch(test_suite)
    assert TestStateEnum.EXECUTING == test_run_execution.test_suite_executions[0].state
    assert test_run_execution.test_suite_executions[0].started_at == start_time
    assert test_run_execution.test_suite_executions[0].completed_at is None
    assert len(test_run_execution.log) == 1


@pytest.mark.asyncio
async def test_test_db_observer_test_case_started_at(db: Session) -> None:
    test_script_manager = TestScriptManager()
    test_db_observer = TestDBObserver()

    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)

    # Getting newly created test suites
    test_run = test_script_manager.get_test_run(db, test_run_execution)
    test_suites = test_run.test_suites
    assert 1 == len(test_suites)
    test_suite = test_suites[0]

    assert 6 == len(test_suite.test_cases)
    test_case = test_suite.test_cases[0]

    # Changing Test case state to executing state
    test_case.state = TestStateEnum.EXECUTING

    test_db_observer.dispatch(test_case)
    assert TestStateEnum.EXECUTING == test_case.test_case_execution.state
    assert test_case.test_case_execution.started_at is not None
    assert test_case.test_case_execution.completed_at is None

    # Note original start time
    start_time = test_case.test_case_execution.started_at

    # Wait/sleep and Dispatch again to trigger DB update
    await asyncio.sleep(2)

    test_db_observer.dispatch(test_case)
    assert TestStateEnum.EXECUTING == test_case.test_case_execution.state
    assert test_case.test_case_execution.started_at == start_time
    assert test_case.test_case_execution.completed_at is None


@pytest.mark.asyncio
async def test_test_db_observer_test_step_started_at(db: Session) -> None:
    test_script_manager = TestScriptManager()
    test_db_observer = TestDBObserver()

    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)

    # Getting newly created test suites
    test_run = test_script_manager.get_test_run(db, test_run_execution)
    test_suites = test_run.test_suites
    assert 1 == len(test_suites)
    test_suite = test_suites[0]

    assert 6 == len(test_suite.test_cases)
    test_case = test_suite.test_cases[0]

    test_step = test_case.test_steps[0]

    # Changing Test case state to executing state
    test_step.state = TestStateEnum.EXECUTING

    test_db_observer.dispatch(test_step)
    assert TestStateEnum.EXECUTING == test_step.state
    assert test_step.test_step_execution is not None
    assert test_step.test_step_execution.started_at is not None
    assert test_step.test_step_execution.completed_at is None

    # Note original start time
    start_time = test_step.test_step_execution.started_at

    # Wait/sleep and Dispatch again to trigger DB update
    await asyncio.sleep(2)

    test_db_observer.dispatch(test_step)
    assert TestStateEnum.EXECUTING == test_step.state
    assert test_step.test_step_execution is not None
    assert test_step.test_step_execution.started_at == start_time
    assert test_step.test_step_execution.completed_at is None


def test_test_db_observer_update(db: Session) -> None:
    test_script_manager = TestScriptManager()
    test_db_observer = TestDBObserver()

    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)

    # Getting newly created test suites
    test_run = test_script_manager.get_test_run(db, test_run_execution)
    test_suites = test_run.test_suites
    assert 1 == len(test_suites)
    test_suite = test_suites[0]

    # Changing Test suite state to executing state
    test_suite.state = TestStateEnum.EXECUTING

    test_db_observer.dispatch(test_suite)
    assert TestStateEnum.EXECUTING == test_run_execution.test_suite_executions[0].state
    assert test_run_execution.test_suite_executions[0].started_at is not None

    # Adding an error to a Test suite
    suite_error = "This is a test suite error"
    test_suite.record_error(suite_error)

    test_db_observer.dispatch(test_suite)
    assert test_suite.test_suite_execution.errors is not None
    assert suite_error in test_suite.test_suite_execution.errors

    # Changing Test suite state to passed state

    test_suite.state = TestStateEnum.PASSED

    test_db_observer.dispatch(test_suite)
    assert TestStateEnum.PASSED == test_run_execution.test_suite_executions[0].state
    assert test_run_execution.test_suite_executions[0].completed_at is not None

    # Fetching Test cases.
    assert 6 == len(test_suite.test_cases)
    test_case = test_suite.test_cases[0]

    # Changing Test case state to executing state

    test_case.state = TestStateEnum.EXECUTING

    test_db_observer.dispatch(test_case)
    assert TestStateEnum.EXECUTING == test_case.test_case_execution.state
    assert test_case.test_case_execution.started_at is not None

    # Adding an error to a Test case
    case_error = "This is a test case error"
    test_case.record_error(case_error)

    test_db_observer.dispatch(test_case)
    assert test_case.test_case_execution.errors is not None
    assert case_error in test_case.test_case_execution.errors

    # Changing Test case state to passed state

    test_case.state = TestStateEnum.PASSED

    test_db_observer.dispatch(test_case)
    assert TestStateEnum.PASSED == test_case.test_case_execution.state
    assert test_case.test_case_execution.completed_at is not None

    test_step = test_case.test_steps[0]

    # Changing Test step state to executing state

    test_step.state = TestStateEnum.EXECUTING

    test_db_observer.dispatch(test_step)
    assert test_step.test_step_execution is not None

    assert TestStateEnum.EXECUTING == test_step.test_step_execution.state
    assert test_step.test_step_execution.started_at is not None

    # Changing Test step state to passed state

    test_step.state = TestStateEnum.PASSED

    test_db_observer.dispatch(test_step)
    assert TestStateEnum.PASSED == test_step.test_step_execution.state
    assert test_step.test_step_execution.completed_at is not None

    # Adding an error to a Test step
    step_error = "This is a test step error"
    test_step.errors = [step_error]

    test_db_observer.dispatch(test_step)
    assert test_step.test_step_execution.errors is not None
    assert step_error in test_step.test_step_execution.errors

    # Adding a failure to a Test step
    step_failure = "This is a test step failure"
    test_step.failures = [step_failure]

    test_db_observer.dispatch(test_step)
    assert test_step.test_step_execution.failures is not None
    assert step_failure in test_step.test_step_execution.failures

    # Adding a test case with the DB session is closed, expecting new session to be
    # created and save operation to succeed.
    test_step.state = TestStateEnum.EXECUTING
    db.close()
    test_db_observer.dispatch(test_step)
    assert TestStateEnum.EXECUTING == test_step.test_step_execution.state


@pytest.mark.asyncio
async def test_test_db_observer_dedups_repeated_run_updates(db: Session) -> None:
    """Repeated dispatch() calls for the same TestRunExecution before
    apply_updates() runs must collapse into a single commit, instead of one
    redundant commit per dispatch (regression test for issue #1072's
    DB-write storm, where ~1,400 redundant commits of the same growing log
    blocked the event loop for the whole duration of a large test run)."""
    test_script_manager = TestScriptManager()
    test_db_observer = TestDBObserver()

    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)
    test_run = test_script_manager.get_test_run(db, test_run_execution)
    test_run.state = TestStateEnum.EXECUTING

    with mock.patch.object(Session, "commit") as mock_commit:
        # Simulate several rapid dispatch() calls for the same object, as
        # happens once per ~0.5s log-flush tick during a run.
        for _ in range(5):
            test_db_observer.dispatch(test_run)

        await test_db_observer.apply_updates()

    assert mock_commit.call_count == 1


@pytest.mark.asyncio
async def test_test_db_observer_appends_only_new_log_entries(db: Session) -> None:
    """Each run update must persist only the entries added since the previous
    one. Rewriting the whole log on every update is what made writes O(n^2)
    over a run (issue #1072)."""
    test_script_manager = TestScriptManager()
    test_db_observer = TestDBObserver()

    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)
    test_run = test_script_manager.get_test_run(db, test_run_execution)
    test_run.state = TestStateEnum.EXECUTING

    test_run.append_log_entries(
        [TestRunLogEntry(level="INFO", timestamp=1.0, message="first")]
    )
    test_db_observer.dispatch(test_run)
    await test_db_observer.apply_updates()

    first_id = (
        db.query(TestRunLogEntryModel)
        .filter_by(test_run_execution_id=test_run_execution.id, seq=0)
        .one()
        .id
    )

    test_run.append_log_entries(
        [TestRunLogEntry(level="INFO", timestamp=2.0, message="second")]
    )
    test_db_observer.dispatch(test_run)
    await test_db_observer.apply_updates()

    # The already-persisted entry is not rewritten, and seq reflects the order
    # the entries were produced in.
    persisted = (
        db.query(TestRunLogEntryModel)
        .filter_by(test_run_execution_id=test_run_execution.id)
        .order_by(TestRunLogEntryModel.seq)
        .all()
    )
    assert [(e.seq, e.message) for e in persisted] == [(0, "first"), (1, "second")]
    assert persisted[0].id == first_id


@pytest.mark.asyncio
async def test_test_db_observer_keeps_entries_of_a_resumed_run(db: Session) -> None:
    """A PENDING execution can already carry entries from an attempt that was
    interrupted before it left PENDING (load_test_run only accepts PENDING, and
    the observer commits state and entries together). Deriving the append
    position from the persisted collection skipped exactly that many new
    entries, losing the start of the new attempt's log."""
    test_script_manager = TestScriptManager()
    test_db_observer = TestDBObserver()

    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)
    test_run_execution.log.append(
        TestRunLogEntryModel(level="INFO", timestamp=1.0, message="earlier attempt")
    )
    db.commit()

    test_run = test_script_manager.get_test_run(db, test_run_execution)
    test_run.state = TestStateEnum.EXECUTING
    test_run.append_log_entries(
        [TestRunLogEntry(level="INFO", timestamp=2.0, message="new attempt")]
    )

    test_db_observer.dispatch(test_run)
    await test_db_observer.apply_updates()

    persisted = (
        db.query(TestRunLogEntryModel)
        .filter_by(test_run_execution_id=test_run_execution.id)
        .order_by(TestRunLogEntryModel.seq)
        .all()
    )
    assert [(e.seq, e.message) for e in persisted] == [
        (0, "earlier attempt"),
        (1, "new attempt"),
    ]


@pytest.mark.asyncio
async def test_test_db_observer_bulk_inserts_in_chunks(db: Session) -> None:
    """A backlog larger than LOG_INSERT_CHUNK_SIZE is split across several
    INSERTs, with seq continuous across the chunk boundaries."""
    test_script_manager = TestScriptManager()
    test_db_observer = TestDBObserver()

    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)
    test_run = test_script_manager.get_test_run(db, test_run_execution)
    test_run.state = TestStateEnum.EXECUTING

    total = LOG_INSERT_CHUNK_SIZE * 2 + 7
    test_run.append_log_entries(
        [
            TestRunLogEntry(level="INFO", timestamp=float(i), message=f"m{i}")
            for i in range(total)
        ]
    )
    test_db_observer.dispatch(test_run)
    await test_db_observer.apply_updates()

    persisted = (
        db.query(TestRunLogEntryModel)
        .filter_by(test_run_execution_id=test_run_execution.id)
        .order_by(TestRunLogEntryModel.seq)
        .all()
    )
    assert [(e.seq, e.message) for e in persisted] == [
        (i, f"m{i}") for i in range(total)
    ]


@pytest.mark.asyncio
async def test_test_db_observer_flushes_periodically_during_run(db: Session) -> None:
    """With start(), entries reach the table without any apply_updates() call,
    so a crash mid-run doesn't lose everything (issue #1149)."""
    test_script_manager = TestScriptManager()
    test_db_observer = TestDBObserver()

    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)
    test_run = test_script_manager.get_test_run(db, test_run_execution)
    test_run.state = TestStateEnum.EXECUTING
    test_run.subscribe([test_db_observer])

    with mock.patch("app.test_engine.test_db_observer.DB_FLUSH_INTERVAL", 0.05):
        test_db_observer.start()
        test_run.append_log_entries(
            [TestRunLogEntry(level="INFO", timestamp=1.0, message="mid-run")]
        )
        await asyncio.sleep(0.3)

        persisted = (
            db.query(TestRunLogEntryModel)
            .filter_by(test_run_execution_id=test_run_execution.id)
            .all()
        )
        assert [e.message for e in persisted] == ["mid-run"]

        await test_db_observer.finish()


@pytest.mark.asyncio
async def test_test_run_log_trimmed_only_after_all_consumers_release(
    db: Session,
) -> None:
    """Entries are dropped from memory only once every log-consuming observer
    has moved past them, and never when no consumer has registered."""
    test_script_manager = TestScriptManager()
    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)
    test_run = test_script_manager.get_test_run(db, test_run_execution)

    def entries(n: int, start: int = 0) -> list[TestRunLogEntry]:
        return [
            TestRunLogEntry(level="INFO", timestamp=float(i), message=f"m{i}")
            for i in range(start, start + n)
        ]

    # No consumer registered: nothing is trimmed.
    test_run.append_log_entries(entries(3))
    assert len(test_run.log) == 3 and test_run.log_count == 3

    fast, slow = mock.MagicMock(), mock.MagicMock()
    test_run.release_log(fast, 3)
    test_run.release_log(slow, 1)
    test_run.append_log_entries(entries(2, start=3))
    # Trimmed up to the slowest consumer (position 1), not the fastest.
    assert test_run.log_count == 5
    assert [e.message for e in test_run.log_entries_since(1)] == [
        "m1",
        "m2",
        "m3",
        "m4",
    ]

    # Only the slow consumer has caught up: still held for the fast one (at 3).
    test_run.release_log(slow, 5)
    test_run.append_log_entries([])
    assert [e.message for e in test_run.log_entries_since(3)] == ["m3", "m4"]
    assert test_run.log_count == 5

    # Once every consumer has released everything, nothing is held.
    test_run.release_log(fast, 5)
    test_run.append_log_entries([])
    assert len(test_run.log) == 0 and test_run.log_count == 5


def _flaky_insert(failures: int) -> Callable[[Engine, list[dict]], None]:
    """Wrap the real bulk insert so its first `failures` calls raise."""
    real_insert = db_observer_module._insert_log_rows
    calls = {"count": 0}

    def flaky(engine: Engine, rows: list[dict], skip_persisted: bool = False) -> None:
        calls["count"] += 1
        if calls["count"] <= failures:
            raise RuntimeError("db down")
        real_insert(engine, rows, skip_persisted)

    return flaky


@pytest.mark.asyncio
async def test_test_db_observer_failed_insert_keeps_rows_for_retry(
    db: Session,
) -> None:
    """A failed bulk insert must neither lose rows nor reorder them: they stay
    staged and the next flush writes them, in order, before newer ones."""
    test_script_manager = TestScriptManager()
    test_db_observer = TestDBObserver()

    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)
    test_run = test_script_manager.get_test_run(db, test_run_execution)
    test_run.state = TestStateEnum.EXECUTING

    test_run.append_log_entries(
        [
            TestRunLogEntry(level="INFO", timestamp=1.0, message="a"),
            TestRunLogEntry(level="INFO", timestamp=2.0, message="b"),
        ]
    )
    with mock.patch(
        "app.test_engine.test_db_observer._insert_log_rows",
        side_effect=_flaky_insert(failures=1),
    ):
        test_db_observer.dispatch(test_run)
        with pytest.raises(RuntimeError):
            await test_db_observer.apply_updates()

        # Nothing was committed, and more entries arrive before the retry.
        assert (
            db.query(TestRunLogEntryModel)
            .filter_by(test_run_execution_id=test_run_execution.id)
            .count()
            == 0
        )
        test_run.append_log_entries(
            [TestRunLogEntry(level="INFO", timestamp=3.0, message="c")]
        )
        test_db_observer.dispatch(test_run)
        await test_db_observer.apply_updates()

    persisted = (
        db.query(TestRunLogEntryModel)
        .filter_by(test_run_execution_id=test_run_execution.id)
        .order_by(TestRunLogEntryModel.seq)
        .all()
    )
    assert [(e.seq, e.message) for e in persisted] == [(0, "a"), (1, "b"), (2, "c")]


@pytest.mark.asyncio
async def test_test_db_observer_periodic_flush_survives_a_failed_flush(
    db: Session,
) -> None:
    """One failing flush must not end incremental persistence for the run."""
    test_script_manager = TestScriptManager()
    test_db_observer = TestDBObserver()

    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)
    test_run = test_script_manager.get_test_run(db, test_run_execution)
    test_run.state = TestStateEnum.EXECUTING
    test_run.subscribe([test_db_observer])

    with mock.patch("app.test_engine.test_db_observer.DB_FLUSH_INTERVAL", 0.05):
        with mock.patch(
            "app.test_engine.test_db_observer._insert_log_rows",
            side_effect=_flaky_insert(failures=1),
        ):
            test_db_observer.start()
            test_run.append_log_entries(
                [TestRunLogEntry(level="INFO", timestamp=1.0, message="survivor")]
            )
            await asyncio.sleep(0.4)

            persisted = (
                db.query(TestRunLogEntryModel)
                .filter_by(test_run_execution_id=test_run_execution.id)
                .all()
            )
            assert [e.message for e in persisted] == ["survivor"]

            # The flush task is still alive, so finish() has nothing to re-raise.
            await test_db_observer.finish()


@pytest.mark.asyncio
async def test_test_db_observer_retry_after_ambiguous_commit_does_not_duplicate(
    db: Session,
) -> None:
    """An insert can fail after the server already committed it (e.g. the
    connection drops while the COMMIT is acknowledged). Retrying the same rows
    must not write them a second time."""
    test_script_manager = TestScriptManager()
    test_db_observer = TestDBObserver()

    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)
    test_run = test_script_manager.get_test_run(db, test_run_execution)
    test_run.state = TestStateEnum.EXECUTING

    real_insert = db_observer_module._insert_log_rows
    calls = {"count": 0}

    def commit_then_fail(
        engine: Engine, rows: list[dict], skip_persisted: bool = False
    ) -> None:
        calls["count"] += 1
        real_insert(engine, rows, skip_persisted)
        if calls["count"] == 1:
            raise RuntimeError("connection lost while acknowledging the COMMIT")

    test_run.append_log_entries(
        [
            TestRunLogEntry(level="INFO", timestamp=1.0, message="a"),
            TestRunLogEntry(level="INFO", timestamp=2.0, message="b"),
        ]
    )
    with mock.patch(
        "app.test_engine.test_db_observer._insert_log_rows",
        side_effect=commit_then_fail,
    ):
        test_db_observer.dispatch(test_run)
        with pytest.raises(RuntimeError):
            await test_db_observer.apply_updates()

        test_run.append_log_entries(
            [TestRunLogEntry(level="INFO", timestamp=3.0, message="c")]
        )
        test_db_observer.dispatch(test_run)
        await test_db_observer.apply_updates()

    persisted = (
        db.query(TestRunLogEntryModel)
        .filter_by(test_run_execution_id=test_run_execution.id)
        .order_by(TestRunLogEntryModel.seq)
        .all()
    )
    assert [(e.seq, e.message) for e in persisted] == [(0, "a"), (1, "b"), (2, "c")]


@pytest.mark.asyncio
async def test_test_db_observer_reapplies_state_after_failed_commit(
    db: Session,
) -> None:
    """A failed state commit rolls the Session back, which discards the changes
    dispatch() had made. They must be applied again: a test case that is never
    dispatched again would otherwise keep a stale state in the DB."""
    test_script_manager = TestScriptManager()
    test_db_observer = TestDBObserver()

    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)
    test_run = test_script_manager.get_test_run(db, test_run_execution)
    test_case = test_run.test_suites[0].test_cases[0]
    test_case.state = TestStateEnum.PASSED
    test_db_observer.dispatch(test_case)

    real_commit = Session.commit
    calls = {"count": 0}

    def flaky_commit(self: Session) -> None:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("db down")
        real_commit(self)

    with mock.patch.object(Session, "commit", flaky_commit):
        with pytest.raises(RuntimeError):
            await test_db_observer.apply_updates()
        # Nothing dispatches the test case again before the next flush.
        await test_db_observer.apply_updates()

    # Read the state back from the DB, not from the in-memory object.
    db.expire_all()
    assert test_case.test_case_execution.state == TestStateEnum.PASSED
    assert calls["count"] == 2
