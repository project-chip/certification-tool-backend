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
from unittest import mock

import pytest
from sqlalchemy.orm import Session

from app import crud
from app.models import TestStateEnum
from app.schemas.test_run_execution import TestRunExecutionCreate
from app.test_engine.models import TestRun
from app.test_engine.test_db_observer import TestDBObserver
from app.test_engine.test_log_handler import TestLogHandler
from app.test_engine.test_runner import (
    AbortError,
    LoadingError,
    TestRunner,
    TestRunnerState,
)
from app.test_engine.test_script_manager import TestCaseNotFound
from app.tests.utils.broadcast import assert_final_run_state_sent_last, logged_messages
from app.tests.utils.test_run_execution import create_random_test_run_execution
from app.tests.utils.test_runner import (
    get_test_case_for_public_id,
    get_test_suite_for_public_id,
    load_and_run_tool_unit_tests,
    load_test_run_for_test_cases,
)
from test_collections.tool_unit_tests.test_suite_expected import (
    TestSuiteExpected,
    TestSuiteExpected2,
)
from test_collections.tool_unit_tests.test_suite_expected.tctr_expected_case_not_applicable import (  # noqa: E501
    TCTRExpectedCaseNotApplicable,
)
from test_collections.tool_unit_tests.test_suite_expected.tctr_expected_error import (
    TCTRExpectedError,
)
from test_collections.tool_unit_tests.test_suite_expected.tctr_expected_fail import (
    TCTRExpectedFail,
)
from test_collections.tool_unit_tests.test_suite_expected.tctr_expected_not_applicable import (  # noqa: E501
    TCTRExpectedNotApplicable,
)
from test_collections.tool_unit_tests.test_suite_expected.tctr_expected_pass import (
    TCTRExpectedPass,
)


@pytest.mark.asyncio
async def test_test_runner(db: Session) -> None:
    selected_tests = {
        "sample_tests": {
            "SampleTestSuite1": {"TCSS1001": 1, "TCSS1002": 2},
            "SampleTestSuite2": {"TCSS2003": 3},
        }
    }

    # Prepare data for test_run_execution
    test_run_execution_title = "Test Execution title"
    test_run_execution_data = TestRunExecutionCreate(title=test_run_execution_title)

    test_run_execution = crud.test_run_execution.create(
        db=db, obj_in=test_run_execution_data, selected_tests=selected_tests
    )

    assert test_run_execution is not None

    # Get TestRunner (singleton)
    test_runner = TestRunner()

    # Ensure initial state is IDLE
    assert test_runner.state == TestRunnerState.IDLE

    # Load tests and assert state is READY
    test_runner.load_test_run(test_run_execution.id)
    assert test_runner.state == TestRunnerState.READY

    # Start running tests (async)
    run_task = asyncio.create_task(test_runner.run())

    # Yield the run loop to allow run task to be scheduled now
    # See https://docs.python.org/3.10/library/asyncio-task.html#sleeping
    await asyncio.sleep(0)

    # Assert state is initally RUNNING
    assert test_runner.state == TestRunnerState.RUNNING

    # Wait for TestRunner to complete run
    await run_task

    # Assert state goes back to IDLE
    assert test_runner.state == TestRunnerState.IDLE


@pytest.mark.asyncio
async def test_test_runner_abort_in_memory(db: Session) -> None:
    selected_tests = {
        "tool_unit_tests": {
            "TestSuiteAsync": {
                "TCTRNeverEnding": 1,
                "TCTRInstantPass": 1,
            },
        }
    }

    test_run_execution = create_random_test_run_execution(
        db=db, selected_tests=selected_tests
    )

    assert test_run_execution is not None

    # Get TestRunner (singleton)
    test_runner = TestRunner()

    # Load tests and assert state is READY
    test_runner.load_test_run(test_run_execution.id)

    # Save test_run reference to inspect models after completion
    test_run = test_runner.test_run
    assert test_run is not None

    # Start running tests (async)
    run_task = asyncio.create_task(test_runner.run())

    # Yield the run loop to allow run task to be scheduled now
    # See https://docs.python.org/3.10/library/asyncio-task.html#sleeping
    await asyncio.sleep(0)

    # Abort testing and wait for run_task (to be cancelled)
    test_runner.abort_testing()
    await run_task

    # As our first test case is never ending, we know that at least the
    # never ending test step and everything after is expected to be cancelled:

    test_suite = get_test_suite_for_public_id(
        test_run=test_run, public_id="TestSuiteAsync"
    )
    assert test_suite is not None

    # Assert "NeverEnding" test case cancelled (at least 2 last cancelled)
    first_test_case = get_test_case_for_public_id(
        test_suite=test_suite, public_id="TCTRNeverEnding"
    )
    assert first_test_case is not None
    assert first_test_case.state == TestStateEnum.CANCELLED

    # we assert that all test_steps are cancelled except the first
    for step in first_test_case.test_steps[1:]:
        assert step.state == TestStateEnum.CANCELLED

    # Assert reming tests are also cancelled(all steps cancelled)
    second_test_case = get_test_case_for_public_id(
        test_suite=test_suite, public_id="TCTRInstantPass"
    )
    assert second_test_case is not None
    assert second_test_case.state == TestStateEnum.CANCELLED
    for step in second_test_case.test_steps:
        assert step.state == TestStateEnum.CANCELLED

    # Assert test runner returns to idle after aborting testing
    assert test_runner.state == TestRunnerState.IDLE


@pytest.mark.asyncio
async def test_test_runner_abort_db_sync(db: Session) -> None:
    selected_tests = {
        "tool_unit_tests": {
            "TestSuiteAsync": {
                "TCTRNeverEnding": 1,
                "TCTRInstantPass": 1,
            },
        }
    }

    test_run_execution = create_random_test_run_execution(
        db=db, selected_tests=selected_tests
    )

    assert test_run_execution is not None

    # Get TestRunner (singleton)
    test_runner = TestRunner()

    # Load tests and assert state is Ready
    test_runner.load_test_run(test_run_execution.id)

    # Remove in-memory model instances from Session, so later crud operations
    # will not use stale data from this db session. This will cascade expunge
    # test_suites and test_cases.
    db.expunge(test_run_execution)

    # Start running tests (async)
    run_task = asyncio.create_task(test_runner.run())

    # Yield the run loop to allow run task to be scheduled now
    # See https://docs.python.org/3.10/library/asyncio-task.html#sleeping
    await asyncio.sleep(0)

    # Abort testing and wait for run_task (to be cancelled)
    test_runner.abort_testing()
    await run_task

    # As our first test case is never ending, we know that at least the
    # never ending test step and everything after is expected to be cancelled:
    db_test_run_execution = crud.test_run_execution.get(db=db, id=test_run_execution.id)
    assert db_test_run_execution is not None
    assert db_test_run_execution.test_suite_execution_count == 1
    assert db_test_run_execution.state == TestStateEnum.CANCELLED

    db_test_suite_execution = db_test_run_execution.test_suite_executions[0]
    assert db_test_suite_execution is not None

    # Assert "NeverEnding" test case cancelled (at least 2 last cancelled)
    assert db_test_suite_execution.test_case_execution_count == 2

    db_first_test_case = db_test_suite_execution.test_case_executions[0]
    assert db_first_test_case is not None
    # we assume the order is preserved from the selected tests
    # but need to verify
    assert db_first_test_case.public_id == "TCTRNeverEnding"
    assert db_first_test_case.state == TestStateEnum.CANCELLED

    # we assert that all test_steps are cancelled except the first
    for step in db_first_test_case.test_step_executions[1:]:
        assert step.state == TestStateEnum.CANCELLED

    # Assert reming tests are also cancelled(all steps cancelled)
    db_second_test_case = db_test_suite_execution.test_case_executions[1]
    assert db_second_test_case is not None
    assert db_second_test_case.public_id == "TCTRInstantPass"
    assert db_second_test_case.state == TestStateEnum.CANCELLED
    for step in db_second_test_case.test_step_executions:
        assert step.state == TestStateEnum.CANCELLED

    # Assert test runner returns to idle after aborting testing
    assert test_runner.state == TestRunnerState.IDLE


@pytest.mark.asyncio
async def test_runner_test_state_pass(db: Session) -> None:
    """Load and run a test_run that passes.

    Args:
        db (Session): Database fixture for creating test models.
    """
    runner, run, suite, case = await load_and_run_tool_unit_tests(
        db, TestSuiteExpected, TCTRExpectedPass
    )
    assert runner.state == TestRunnerState.IDLE
    assert run.state == TestStateEnum.PASSED
    assert suite.state == TestStateEnum.PASSED
    assert case.state == TestStateEnum.PASSED


def _assert_db_run_state(db: Session, run: TestRun, state: TestStateEnum) -> None:
    """Assert the run's saved test run execution has the given state.

    Args:
        db (Session): Database fixture for creating test models.
        run (TestRun): The test run whose saved state to check.
        state (TestStateEnum): The expected state.
    """
    db_test_run_execution = crud.test_run_execution.get(
        db=db, id=run.test_run_execution.id
    )
    assert db_test_run_execution is not None
    db.refresh(db_test_run_execution)
    assert db_test_run_execution.state == state


@pytest.mark.asyncio
async def test_runner_sends_final_run_state_after_all_logs(
    db: Session, broadcast_mock: mock.AsyncMock
) -> None:
    """The terminal run state must be the run's last websocket message, sent
    after the final log flush and flagged logs_complete, so clients can stop
    listening as soon as it arrives.

    Args:
        db (Session): Database fixture for creating test models.
        broadcast_mock (mock.AsyncMock): The patched websocket broadcast.
    """
    await load_and_run_tool_unit_tests(db, TestSuiteExpected, TCTRExpectedPass)

    assert_final_run_state_sent_last(
        broadcast_mock, TestStateEnum.PASSED, logs_complete=True
    )
    # The "Test Run Completed" line is logged after the run state turns
    # terminal; it must still be delivered before the final state update.
    assert "Test Run Completed [PASSED]" in logged_messages(broadcast_mock)


@pytest.mark.asyncio
async def test_runner_tears_down_run_that_raises(
    db: Session, broadcast_mock: mock.AsyncMock, finish_spy: mock.AsyncMock
) -> None:
    """A run that raises must still be torn down: the log handler finished (so
    its log sink doesn't capture later runs' records), its last log records and
    DB updates flushed, and the final run state sent with logs_complete.

    Args:
        db (Session): Database fixture for creating test models.
        broadcast_mock (mock.AsyncMock): The patched websocket broadcast.
        finish_spy (mock.AsyncMock): Spy on TestLogHandler.finish().
    """
    run_suite = TestSuiteExpected.run

    async def _run_then_raise(suite: TestSuiteExpected) -> None:
        await run_suite(suite)
        raise RuntimeError("Test suite failed")

    with mock.patch.object(TestSuiteExpected, "run", _run_then_raise):
        runner, run, _, _ = await load_and_run_tool_unit_tests(
            db, TestSuiteExpected, TCTRExpectedPass
        )

    finish_spy.assert_awaited_once()
    assert runner.state == TestRunnerState.IDLE
    assert run.state == TestStateEnum.PASSED
    _assert_db_run_state(db, run, TestStateEnum.PASSED)

    assert_final_run_state_sent_last(
        broadcast_mock, TestStateEnum.PASSED, logs_complete=True
    )
    assert "Test Run Completed [PASSED]" in logged_messages(broadcast_mock)


@pytest.mark.asyncio
async def test_runner_teardown_continues_after_log_flush_fails(
    db: Session, broadcast_mock: mock.AsyncMock
) -> None:
    """A failing final log flush must not skip the rest of the teardown: the
    observers are still detached, the DB still saved with the run's final
    state, and the final run state still sent - flagged logs incomplete.

    Args:
        db (Session): Database fixture for creating test models.
        broadcast_mock (mock.AsyncMock): The patched websocket broadcast.
    """
    real_finish = TestLogHandler.finish

    async def _finish_then_raise(log_handler: TestLogHandler) -> None:
        # Really finish first, so the log sink doesn't leak into later tests.
        await real_finish(log_handler)
        raise RuntimeError("Log flush failed")

    with mock.patch.object(TestLogHandler, "finish", _finish_then_raise):
        runner, run, _, _ = await load_and_run_tool_unit_tests(
            db, TestSuiteExpected, TCTRExpectedPass
        )

    assert runner.state == TestRunnerState.IDLE
    assert len(run.observers) == 0
    _assert_db_run_state(db, run, TestStateEnum.PASSED)
    assert_final_run_state_sent_last(
        broadcast_mock, TestStateEnum.PASSED, logs_complete=False
    )


@pytest.mark.asyncio
async def test_runner_sends_final_run_state_when_cancelled_during_teardown(
    db: Session, broadcast_mock: mock.AsyncMock
) -> None:
    """Cancelling the run task (e.g. on server shutdown) mid-teardown must
    still send the final run state and free the runner for the next run.

    Args:
        db (Session): Database fixture for creating test models.
        broadcast_mock (mock.AsyncMock): The patched websocket broadcast.
    """
    with mock.patch.object(
        TestDBObserver, "apply_updates", side_effect=asyncio.CancelledError
    ), pytest.raises(asyncio.CancelledError):
        await load_and_run_tool_unit_tests(db, TestSuiteExpected, TCTRExpectedPass)

    runner = TestRunner()
    assert runner.state == TestRunnerState.IDLE
    assert runner.test_run is None
    # The teardown was cancelled before it could report its outcome, so the
    # logs are conservatively flagged incomplete.
    assert_final_run_state_sent_last(
        broadcast_mock, TestStateEnum.PASSED, logs_complete=False
    )


@pytest.mark.asyncio
async def test_runner_finishes_log_handler_when_subscribe_fails(
    db: Session, finish_spy: mock.AsyncMock
) -> None:
    """If subscribing the observers fails, the log handler created just before
    must still be finished, so its log sink doesn't capture later runs' log
    records.

    Args:
        db (Session): Database fixture for creating test models.
        finish_spy (mock.AsyncMock): Spy on TestLogHandler.finish().
    """
    with mock.patch.object(
        TestRun, "subscribe", side_effect=RuntimeError("Subscribe failed")
    ):
        runner, _, _, _ = await load_and_run_tool_unit_tests(
            db, TestSuiteExpected, TCTRExpectedPass
        )

    finish_spy.assert_awaited_once()
    assert runner.state == TestRunnerState.IDLE


@pytest.mark.asyncio
async def test_runner_test_state_fail(db: Session) -> None:
    """Load and run a test_run that fails.

    Args:
        db (Session): Database fixture for creating test models.
    """
    runner, run, suite, case = await load_and_run_tool_unit_tests(
        db, TestSuiteExpected, TCTRExpectedFail
    )

    assert runner.state == TestRunnerState.IDLE
    assert run.state == TestStateEnum.FAILED
    assert suite.state == TestStateEnum.FAILED
    assert case.state == TestStateEnum.FAILED


@pytest.mark.asyncio
async def test_runner_test_state_error(db: Session) -> None:
    """Load and run a test_run that has a test case that errors out.

    Args:
        db (Session): Database fixture for creating test models.
    """
    runner, run, suite, case = await load_and_run_tool_unit_tests(
        db, TestSuiteExpected, TCTRExpectedError
    )

    assert runner.state == TestRunnerState.IDLE
    assert run.state == TestStateEnum.ERROR
    assert suite.state == TestStateEnum.ERROR
    assert case.state == TestStateEnum.ERROR


@pytest.mark.asyncio
async def test_runner_test_step_not_applicable(db: Session) -> None:
    """Load and run a test_run that passes.

    Args:
        db (Session): Database fixture for creating test models.
    """
    runner, run, suite, case = await load_and_run_tool_unit_tests(
        db, TestSuiteExpected, TCTRExpectedNotApplicable
    )
    assert runner.state == TestRunnerState.IDLE
    assert run.state == TestStateEnum.PASSED
    assert suite.state == TestStateEnum.PASSED
    assert case.state == TestStateEnum.PASSED
    # Index 1 corresponds to test step 2 which is expected
    # to be in NOT_APPLICABLE state.
    assert case.test_steps[1].state == TestStateEnum.NOT_APPLICABLE


@pytest.mark.asyncio
async def test_runner_not_all_test_cases_not_applicable(db: Session) -> None:
    """Load and run a test_run that is not applicable.

    Args:
        db (Session): Database fixture for creating test models.
    """

    test_cases = {
        "tool_unit_tests": {
            TestSuiteExpected.public_id(): {
                TCTRExpectedCaseNotApplicable.public_id(): 1,
                TCTRExpectedPass.public_id(): 1,
            },
            TestSuiteExpected2.public_id(): {
                TCTRExpectedCaseNotApplicable.public_id(): 1,
            },
        }
    }

    runner = load_test_run_for_test_cases(db, test_cases)
    run = runner.test_run
    assert run is not None

    await runner.run()

    assert runner.state == TestRunnerState.IDLE
    assert run.state == TestStateEnum.PASSED
    assert run.test_suites[0].state == TestStateEnum.PASSED
    assert run.test_suites[0].test_cases[0].state == TestStateEnum.NOT_APPLICABLE
    assert run.test_suites[0].test_cases[1].state == TestStateEnum.PASSED
    assert run.test_suites[1].state == TestStateEnum.NOT_APPLICABLE
    assert run.test_suites[1].test_cases[0].state == TestStateEnum.NOT_APPLICABLE


@pytest.mark.asyncio
async def test_runner_all_test_cases_not_applicable(db: Session) -> None:
    """Load and run a test_run that is not applicable.

    Args:
        db (Session): Database fixture for creating test models.
    """

    test_cases = {
        "tool_unit_tests": {
            TestSuiteExpected.public_id(): {
                TCTRExpectedCaseNotApplicable.public_id(): 1,
            },
            TestSuiteExpected2.public_id(): {
                TCTRExpectedCaseNotApplicable.public_id(): 1,
            },
        }
    }

    runner = load_test_run_for_test_cases(db, test_cases)
    run = runner.test_run
    assert run is not None

    await runner.run()

    assert runner.state == TestRunnerState.IDLE
    assert run.state == TestStateEnum.NOT_APPLICABLE
    assert run.test_suites[0].state == TestStateEnum.NOT_APPLICABLE
    assert run.test_suites[0].test_cases[0].state == TestStateEnum.NOT_APPLICABLE
    assert run.test_suites[1].state == TestStateEnum.NOT_APPLICABLE
    assert run.test_suites[1].test_cases[0].state == TestStateEnum.NOT_APPLICABLE


@pytest.mark.asyncio
async def test_test_runner_load_finished_test_run(db: Session) -> None:
    """Load a test_run_execution that has already been executed.

    This is expected to fail, and the test runner should raise a LoadingError.
    Args:
        db (Session): Database fixture for creating test data.
    """

    runner, run, _, _ = await load_and_run_tool_unit_tests(
        db, TestSuiteExpected, TCTRExpectedPass
    )

    # Attempt to load test run again and expect loading error
    with pytest.raises(LoadingError):
        runner.load_test_run(test_run_execution_id=run.test_run_execution.id)

    assert runner.state == TestRunnerState.IDLE


@pytest.mark.asyncio
async def test_test_runner_load__load_multiple_runs_simultaneously(db: Session) -> None:
    """Load a test_run_execution while another is loaded.

    It should not be allowed to load more than one test_run_execution and
    the test runner should raise a LoadingError.

    Args:
        db (Session): Database fixture for creating test data.
    """
    selected_tests = {
        "tool_unit_tests": {
            "TestSuiteExpected": {"TCTRExpectedPass": 1},
        }
    }

    test_runner = load_test_run_for_test_cases(db=db, test_cases=selected_tests)
    assert test_runner.state != TestRunnerState.IDLE

    # Create a 2nd test and attempt to load it
    test_run_execution = create_random_test_run_execution(
        db=db, selected_tests=selected_tests
    )

    with pytest.raises(LoadingError):
        test_runner.load_test_run(test_run_execution.id)

    # reset test runner, to leave in clean state
    test_runner.abort_testing()
    assert test_runner.test_run is None
    assert test_runner.state is TestRunnerState.IDLE


def test_test_runner_abort_no_run(db: Session) -> None:
    """This test case will try to abort testing while no test run is being executed.

    This should not be allowed and the test runner should raise an AbortError.
    """
    test_runner = TestRunner()
    assert test_runner.state == TestRunnerState.IDLE

    with pytest.raises(AbortError):
        test_runner.abort_testing()


@pytest.mark.asyncio
async def test_test_runner_non_existant_test_case(db: Session) -> None:
    """When a non existing test case is provided, the test harness should
    throw a test case not found error and not a keyerror exception.
    Args:
        db (Session): Database fixture for creating test data.
    """
    selected_tests = {
        "tool_unit_tests": {
            "TestSuiteExpected": {"TCNonExistant": 1},
        }
    }

    with pytest.raises(TestCaseNotFound):
        load_test_run_for_test_cases(db=db, test_cases=selected_tests)
