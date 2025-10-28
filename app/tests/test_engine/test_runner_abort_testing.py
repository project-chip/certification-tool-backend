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
import asyncio
from typing import Tuple

import pytest
from sqlalchemy.orm import Session

from app.models import TestStateEnum
from app.test_engine.test_runner import TestRunner
from app.tests.utils.test_runner import (
    get_test_case_for_public_id,
    get_test_suite_for_public_id,
    load_test_run_for_test_cases,
)
from test_collections.tool_unit_tests.test_suite_expected import TestSuiteExpected
from test_collections.tool_unit_tests.test_suite_expected.tctr_expected_pass import (
    TCTRExpectedPass,
)
from test_collections.tool_unit_tests.test_suite_never_ending import (
    TestSuiteNeverEnding,
)
from test_collections.tool_unit_tests.test_suite_never_ending.tc_never_ending import (
    TCNeverEnding,
    TCNeverEndingV2,
)


@pytest.mark.asyncio
async def test_abort_suite_setup(db: Session) -> None:
    test_suite, test_case = __load_abort_tests(db)
    test_suite.never_end_during_setup = True
    await __run_abort_tests()

    assert test_suite.state is TestStateEnum.CANCELLED
    assert len(test_suite.errors) == 0

    assert test_case.state == TestStateEnum.CANCELLED
    assert len(test_case.errors) == 0

    assert len(test_case.test_steps) == 3
    for step in test_case.test_steps:
        assert step.state == TestStateEnum.CANCELLED


@pytest.mark.asyncio
async def test_abort_suite_cleanup(db: Session) -> None:
    test_suite, test_case = __load_abort_tests(db)
    test_suite.never_end_during_cleanup = True
    await __run_abort_tests()

    assert test_suite.state == TestStateEnum.PASSED
    assert len(test_suite.errors) == 0

    assert test_case.state == TestStateEnum.PASSED
    assert len(test_case.errors) == 0

    assert len(test_case.test_steps) == 3
    for step in test_case.test_steps:
        assert step.state == TestStateEnum.PASSED


@pytest.mark.asyncio
async def test_abort_suite_cleanup_2_suites(db: Session) -> None:
    test_suite_1, test_case_1, test_suite_2, test_case_2 = __load_abort_tests_2_suites(
        db
    )
    test_suite_1.never_end_during_cleanup = True
    await __run_abort_tests()

    assert test_suite_1.state == TestStateEnum.PASSED
    assert len(test_suite_1.errors) == 0

    assert test_case_1.state == TestStateEnum.PASSED
    assert len(test_case_1.errors) == 0

    assert len(test_case_1.test_steps) == 3
    for step in test_case_1.test_steps:
        assert step.state == TestStateEnum.PASSED

    assert test_suite_2.state == TestStateEnum.CANCELLED
    assert len(test_suite_2.errors) == 0

    assert test_case_2.state == TestStateEnum.CANCELLED
    assert len(test_case_2.errors) == 0

    assert len(test_case_2.test_steps) == 3
    for step in test_case_2.test_steps:
        assert step.state == TestStateEnum.CANCELLED


@pytest.mark.asyncio
async def test_abort_case_setup(db: Session) -> None:
    test_suite, test_case = __load_abort_tests(db)
    test_case.never_end_during_setup = True
    await __run_abort_tests()

    assert test_suite.state == TestStateEnum.CANCELLED
    assert len(test_suite.errors) == 0

    assert test_case.state == TestStateEnum.CANCELLED
    assert len(test_case.errors) == 0

    assert len(test_case.test_steps) == 3
    for step in test_case.test_steps:
        assert step.state == TestStateEnum.CANCELLED


@pytest.mark.asyncio
async def test_abort_case_execution(db: Session) -> None:
    test_suite, test_case = __load_abort_tests(db)
    test_case.never_end_during_execute = True
    await __run_abort_tests()

    assert test_suite.state == TestStateEnum.CANCELLED
    assert len(test_suite.errors) == 0

    assert test_case.state == TestStateEnum.CANCELLED
    assert len(test_case.errors) == 0

    assert len(test_case.test_steps) == 3
    assert test_case.test_steps[0].state == TestStateEnum.PASSED
    assert test_case.test_steps[1].state == TestStateEnum.CANCELLED
    assert test_case.test_steps[2].state == TestStateEnum.CANCELLED


@pytest.mark.asyncio
async def test_abort_case_cleanup(db: Session) -> None:
    test_suite, test_case = __load_abort_tests(db)
    test_case.never_end_during_cleanup = True
    await __run_abort_tests()

    assert test_suite.state == TestStateEnum.PASSED
    assert len(test_suite.errors) == 0

    assert test_case.state == TestStateEnum.PASSED
    assert len(test_case.errors) == 0

    assert len(test_case.test_steps) == 3
    assert test_case.test_steps[0].state == TestStateEnum.PASSED
    assert test_case.test_steps[1].state == TestStateEnum.PASSED
    assert test_case.test_steps[2].state == TestStateEnum.PASSED


@pytest.mark.asyncio
async def test_abort_case_cleanup_2_suites(db: Session) -> None:
    test_suite_1, test_case_1, test_suite_2, test_case_2 = __load_abort_tests_2_suites(
        db
    )
    test_case_1.never_end_during_cleanup = True
    await __run_abort_tests()

    assert test_suite_1.state == TestStateEnum.PASSED
    assert len(test_suite_1.errors) == 0

    assert test_case_1.state == TestStateEnum.PASSED
    assert len(test_case_1.errors) == 0

    assert len(test_case_1.test_steps) == 3
    assert test_case_1.test_steps[0].state == TestStateEnum.PASSED
    assert test_case_1.test_steps[1].state == TestStateEnum.PASSED
    assert test_case_1.test_steps[2].state == TestStateEnum.PASSED

    assert test_suite_2.state == TestStateEnum.CANCELLED
    assert len(test_suite_2.errors) == 0

    assert test_case_2.state == TestStateEnum.CANCELLED
    assert len(test_case_2.errors) == 0

    assert len(test_case_2.test_steps) == 3
    assert test_case_2.test_steps[0].state == TestStateEnum.CANCELLED
    assert test_case_2.test_steps[1].state == TestStateEnum.CANCELLED
    assert test_case_2.test_steps[2].state == TestStateEnum.CANCELLED


@pytest.mark.asyncio
async def test_abort_case_cleanup_2_tests_1_suite(db: Session) -> None:
    test_suite_1, test_case_1, test_case_2 = __load_abort_tests_2_tests_1_suite(db)
    test_case_1.never_end_during_cleanup = True
    await __run_abort_tests()

    assert test_suite_1.state == TestStateEnum.CANCELLED
    assert len(test_suite_1.errors) == 0

    assert test_case_1.state == TestStateEnum.PASSED
    assert len(test_case_1.errors) == 0

    assert len(test_case_1.test_steps) == 3
    assert test_case_1.test_steps[0].state == TestStateEnum.PASSED
    assert test_case_1.test_steps[1].state == TestStateEnum.PASSED
    assert test_case_1.test_steps[2].state == TestStateEnum.PASSED

    assert test_case_2.state == TestStateEnum.CANCELLED
    assert len(test_case_2.errors) == 0

    assert len(test_case_2.test_steps) == 3
    assert test_case_2.test_steps[0].state == TestStateEnum.CANCELLED
    assert test_case_2.test_steps[1].state == TestStateEnum.CANCELLED
    assert test_case_2.test_steps[2].state == TestStateEnum.CANCELLED


def __load_abort_tests(db: Session) -> Tuple[TestSuiteNeverEnding, TCNeverEnding]:
    test_suite_id = "TestSuiteNeverEnding"
    test_case_id = "TCNeverEnding"
    selected_tests = {"tool_unit_tests": {test_suite_id: {test_case_id: 1}}}
    test_runner = load_test_run_for_test_cases(db=db, test_cases=selected_tests)
    run = test_runner.test_run
    assert run is not None

    test_suite = get_test_suite_for_public_id(test_run=run, public_id=test_suite_id)
    assert test_suite is not None
    assert isinstance(test_suite, TestSuiteNeverEnding)

    test_case = get_test_case_for_public_id(
        test_suite=test_suite, public_id=test_case_id
    )
    assert test_case is not None
    assert isinstance(test_case, TCNeverEnding)

    return test_suite, test_case


def __load_abort_tests_2_suites(
    db: Session,
) -> Tuple[TestSuiteNeverEnding, TCNeverEnding, TestSuiteExpected, TCTRExpectedPass]:
    test_suite_id_1 = "TestSuiteNeverEnding"
    test_case_id_1 = "TCNeverEnding"

    test_suite_id_2 = "TestSuiteExpected"
    test_case_id_2 = "TCTRExpectedPass"

    selected_tests = {
        "tool_unit_tests": {
            test_suite_id_1: {test_case_id_1: 1},
            test_suite_id_2: {test_case_id_2: 1},
        }
    }
    test_runner = load_test_run_for_test_cases(db=db, test_cases=selected_tests)
    run = test_runner.test_run
    assert run is not None

    test_suite_1 = get_test_suite_for_public_id(test_run=run, public_id=test_suite_id_1)
    assert test_suite_1 is not None
    assert isinstance(test_suite_1, TestSuiteNeverEnding)

    test_suite_2 = get_test_suite_for_public_id(test_run=run, public_id=test_suite_id_2)
    assert test_suite_2 is not None
    assert isinstance(test_suite_2, TestSuiteExpected)

    test_case_1 = get_test_case_for_public_id(
        test_suite=test_suite_1, public_id=test_case_id_1
    )
    assert test_case_1 is not None
    assert isinstance(test_case_1, TCNeverEnding)

    test_case_2 = get_test_case_for_public_id(
        test_suite=test_suite_2, public_id=test_case_id_2
    )
    assert test_case_2 is not None
    assert isinstance(test_case_2, TCTRExpectedPass)

    return test_suite_1, test_case_1, test_suite_2, test_case_2


def __load_abort_tests_2_tests_1_suite(
    db: Session,
) -> Tuple[TestSuiteNeverEnding, TCNeverEnding, TCNeverEndingV2]:
    test_suite_id_1 = "TestSuiteNeverEnding"
    test_case_id_1 = "TCNeverEnding"
    test_case_id_2 = "TCNeverEndingV2"

    selected_tests = {
        "tool_unit_tests": {
            test_suite_id_1: {test_case_id_1: 1, test_case_id_2: 2},
        }
    }
    test_runner = load_test_run_for_test_cases(db=db, test_cases=selected_tests)
    run = test_runner.test_run
    assert run is not None

    test_suite_1 = get_test_suite_for_public_id(test_run=run, public_id=test_suite_id_1)
    assert test_suite_1 is not None
    assert isinstance(test_suite_1, TestSuiteNeverEnding)

    test_case_1 = get_test_case_for_public_id(
        test_suite=test_suite_1, public_id=test_case_id_1
    )
    assert test_case_1 is not None
    assert isinstance(test_case_1, TCNeverEnding)

    test_case_2 = get_test_case_for_public_id(
        test_suite=test_suite_1, public_id=test_case_id_2
    )
    assert test_case_2 is not None
    assert isinstance(test_case_2, TCNeverEndingV2)

    return test_suite_1, test_case_1, test_case_2


async def __run_abort_tests() -> None:
    runner = TestRunner()
    run_task = asyncio.create_task(runner.run())
    await asyncio.sleep(1)
    runner.abort_testing()
    await run_task
