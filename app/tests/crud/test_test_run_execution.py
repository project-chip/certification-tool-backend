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

from copy import deepcopy
from typing import Dict, Optional
from unittest import mock
from unittest.mock import call

import pytest
from faker import Faker
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.crud.crud_test_run_execution import ImportError
from app.models.test_enums import TestStateEnum
from app.schemas import SelectedTests
from app.schemas.test_run_execution import (
    TestRunExecutionCreate,
    TestRunExecutionWithStats,
)
from app.tests.utils.operator import operator_base_dict
from app.tests.utils.project import create_random_project
from app.tests.utils.test_run_execution import (
    create_random_test_run_execution,
    create_random_test_run_execution_archived,
    create_random_test_run_execution_with_test_case_states,
    random_test_run_execution_dict,
    test_run_execution_base_dict,
)
from app.tests.utils.utils import random_lower_string

faker = Faker()


def test_get_test_run_execution(db: Session) -> None:
    # Create build new test_run_execution object
    title = random_lower_string()
    description = random_lower_string()
    test_run_execution_dict = random_test_run_execution_dict(
        title=title, description=description
    )

    test_run_execution_in = TestRunExecutionCreate(**test_run_execution_dict)

    # Save create test_run_execution in DB
    test_run_execution = crud.test_run_execution.create(
        db=db, obj_in=test_run_execution_in
    )

    # load stored test_run_execution from DB
    stored_test_run_execution = crud.test_run_execution.get(
        db=db, id=test_run_execution.id
    )

    # assert stored values match
    assert stored_test_run_execution
    assert test_run_execution.id == stored_test_run_execution.id
    assert test_run_execution.title == stored_test_run_execution.title
    assert test_run_execution.description == stored_test_run_execution.description


def test_test_run_archive(db: Session) -> None:
    run = create_random_test_run_execution(db=db)
    assert run.archived_at is None

    archived_run = crud.test_run_execution.archive(db=db, db_obj=run)

    assert archived_run
    assert archived_run.archived_at is not None


def test_test_run_unarchive(db: Session) -> None:
    archived_run = create_random_test_run_execution_archived(db=db)

    assert archived_run
    assert archived_run.archived_at is not None

    unarchived_run = crud.test_run_execution.unarchive(db=db, db_obj=archived_run)

    assert unarchived_run
    assert unarchived_run.archived_at is None


def test_test_run_archive_with_description(db: Session) -> None:
    description = random_lower_string()
    run = create_random_test_run_execution(db=db)
    assert run.archived_at is None
    run.description = description

    archived_run = crud.test_run_execution.archive(db=db, db_obj=run)

    assert archived_run
    assert archived_run.archived_at is not None
    assert archived_run.description is not None
    assert archived_run.description == description


def test_test_run_unarchive_with_description(db: Session) -> None:
    description = random_lower_string()
    archived_run = create_random_test_run_execution_archived(db=db)
    archived_run.description = description

    assert archived_run
    assert archived_run.archived_at is not None
    assert archived_run.description is not None

    unarchived_run = crud.test_run_execution.unarchive(db=db, db_obj=archived_run)

    assert unarchived_run
    assert unarchived_run.archived_at is None
    assert unarchived_run.description is not None
    assert unarchived_run.description == description


def test_delete_test_run_execution(db: Session) -> None:
    # Create build new test_run_execution object
    title = random_lower_string()
    test_run_execution_dict = random_test_run_execution_dict(title=title)

    test_run_execution_in = TestRunExecutionCreate(**test_run_execution_dict)

    # Save create test_run_execution in DB
    test_run_execution = crud.test_run_execution.create(
        db=db, obj_in=test_run_execution_in
    )

    # Make sure DB session doesn't reuse models
    db.expunge(test_run_execution)

    test_run_execution_deleted = crud.test_run_execution.remove(
        db=db, id=test_run_execution.id
    )
    assert test_run_execution_deleted is not None
    assert test_run_execution.id == test_run_execution_deleted.id
    assert test_run_execution.title == test_run_execution_deleted.title

    # load stored test_run_execution from DB
    test_run_execution_none = crud.test_run_execution.get(
        db=db, id=test_run_execution.id
    )

    assert test_run_execution_none is None


def test_delete_test_run_execution_with_a_test_suite(db: Session) -> None:
    # Create build new test_run_execution object
    title = random_lower_string()
    test_run_execution_dict = random_test_run_execution_dict(title=title)

    test_run_execution_in = TestRunExecutionCreate(**test_run_execution_dict)
    selected_tests = {
        "collections": [
            {
                "public_id": "sample_tests",
                "test_suites": [
                    {
                        "public_id": "SampleTestSuite1",
                        "test_cases": [{"public_id": "TCSS1001", "iterations": 1}],
                    }
                ],
            }
        ]
    }

    # Save create test_run_execution in DB
    test_run_execution = crud.test_run_execution.create_with_selected_tests(
        db=db,
        obj_in=test_run_execution_in,
        selected_tests=SelectedTests(**selected_tests),
    )
    assert len(test_run_execution.test_suite_executions) == 1
    suite = test_run_execution.test_suite_executions[0]

    # Make sure DB session doesn't reuse models
    db.expunge(test_run_execution)

    test_run_execution_deleted = crud.test_run_execution.remove(
        db=db, id=test_run_execution.id
    )
    assert test_run_execution_deleted is not None
    assert test_run_execution.id == test_run_execution_deleted.id
    assert test_run_execution.title == test_run_execution_deleted.title

    # load stored test_run_execution from DB
    test_run_execution_none = crud.test_run_execution.get(
        db=db, id=test_run_execution.id
    )
    assert test_run_execution_none is None

    # Verify that the test_suite is also deleted
    suite_db = db.get(models.TestSuiteExecution, suite.id)
    assert suite_db is None


def test_get_test_run_execution_with_state_stats(db: Session) -> None:
    # We generate a random test run for this test.
    # To validate the statistics, we create the run with a random number of test cases
    # for each state (between 2 and 10 per state)
    expected_state_stats: Dict[TestStateEnum, int] = {}
    for state in TestStateEnum:
        expected_state_stats[state] = faker.pyint(2, 10)

    total_test_case_count = sum(expected_state_stats.values())

    # Create test run
    test_run_execution = create_random_test_run_execution_with_test_case_states(
        db, expected_state_stats
    )

    # Run CRUD operation we're testing (disable pagination)
    all_with_stats = crud.test_run_execution.get_multi_with_stats(
        db, skip=None, limit=None
    )

    # find created test_run in list
    test_run_with_stats: TestRunExecutionWithStats = next(
        filter(lambda x: x.id == test_run_execution.id, all_with_stats)
    )

    # Assert stats
    assert test_run_with_stats is not None
    assert test_run_with_stats.test_case_stats is not None
    assert test_run_with_stats.test_case_stats.test_case_count == total_test_case_count

    # Assert that the state counts are correct:
    for state, count in test_run_with_stats.test_case_stats.states.items():
        assert expected_state_stats[state] == count


def test_get_test_run_executions_by_project(db: Session) -> None:
    project = create_random_project(db)
    test_run_execution = create_random_test_run_execution(db, project_id=project.id)
    archived_test_run_execution = create_random_test_run_execution_archived(
        db, project_id=project.id
    )

    test_run_executions = crud.test_run_execution.get_multi_with_stats(
        db, project_id=project.id
    )

    assert any(t.id == test_run_execution.id for t in test_run_executions)
    assert not any(t.id == archived_test_run_execution.id for t in test_run_executions)

    project2 = create_random_project(db)
    test_run_executions = crud.test_run_execution.get_multi_with_stats(
        db, project_id=project2.id
    )
    assert not any(t.id == test_run_execution.id for t in test_run_executions)
    assert not any(t.id == archived_test_run_execution.id for t in test_run_executions)


def test_get_test_run_executions_archived_by_project(db: Session) -> None:
    project = create_random_project(db)
    test_run_execution = create_random_test_run_execution(db, project_id=project.id)
    archived_test_run_execution = create_random_test_run_execution_archived(
        db, project_id=project.id
    )

    test_run_executions = crud.test_run_execution.get_multi_with_stats(
        db, project_id=project.id, archived=True
    )

    assert not any(t.id == test_run_execution.id for t in test_run_executions)
    assert any(t.id == archived_test_run_execution.id for t in test_run_executions)

    project2 = create_random_project(db)
    test_run_executions = crud.test_run_execution.get_multi_with_stats(
        db, project_id=project2.id, archived=True
    )
    assert not any(t.id == test_run_execution.id for t in test_run_executions)
    assert not any(t.id == archived_test_run_execution.id for t in test_run_executions)


def test_create_test_run_execution_from_selected_tests(db: Session) -> None:
    first_test_case_identifier = "TCSS1001"
    selected_tests = {
        "collections": [
            {
                "public_id": "sample_tests",
                "test_suites": [
                    {
                        "public_id": "SampleTestSuite1",
                        "test_cases": [
                            {"public_id": first_test_case_identifier, "iterations": 1},
                            {"public_id": "TCSS1002", "iterations": 2},
                            {"public_id": "TCSS1003", "iterations": 3},
                        ],
                    }
                ],
            }
        ]
    }

    values = [
        x["iterations"]
        for x in selected_tests["collections"][0]["test_suites"][0]["test_cases"]
    ]
    total_test_case_count = sum(values)

    # Prepare data for test_run_execution
    test_run_execution_title = "Test Execution title"
    test_run_execution_data = TestRunExecutionCreate(title=test_run_execution_title)

    test_run_execution = crud.test_run_execution.create_with_selected_tests(
        db=db,
        obj_in=test_run_execution_data,
        selected_tests=SelectedTests(**selected_tests),
    )

    # Assert direct properties
    assert test_run_execution.title == test_run_execution_title

    # Assert created test_suite_executions
    test_suite_executions = test_run_execution.test_suite_executions
    assert len(test_suite_executions) > 0

    first_test_suite_execution = test_suite_executions[0]
    test_case_executions = first_test_suite_execution.test_case_executions
    assert len(test_case_executions) == total_test_case_count

    first_test_case_execution = test_case_executions[0]
    assert first_test_case_execution.public_id == first_test_case_identifier

    remaining_test_cases = [
        x for x in selected_tests["collections"][0]["test_suites"][0]["test_cases"]
    ]
    for test_case_execution in test_case_executions:
        public_id = test_case_execution.public_id
        # Assert all test case public id's match
        assert public_id in [c["public_id"] for c in remaining_test_cases]
        test_case = next(c for c in remaining_test_cases if c["public_id"] == public_id)
        test_case["iterations"] -= 1

    # Assert the correct number of test cases where created
    for test_case in remaining_test_cases:
        assert test_case["iterations"] == 0


def test_get_test_run_executions_by_search_query(db: Session) -> None:
    title = "Test Title"
    description = "test description"
    test_run_execution = create_random_test_run_execution(
        db, title=title, description=description
    )

    # Don't include unrelated
    __search_assert_presence(
        db, query="Bananas", run_id=test_run_execution.id, expected=False
    )

    # Find in title
    __search_assert_presence(
        db, query="Title", run_id=test_run_execution.id, expected=True
    )

    # Find in title: case insensitive
    __search_assert_presence(
        db, query="TiTlE", run_id=test_run_execution.id, expected=True
    )

    # Find in description
    __search_assert_presence(
        db, query="description", run_id=test_run_execution.id, expected=True
    )

    # Find in description: case insensitive
    __search_assert_presence(
        db, query="DeScRiPtIoN", run_id=test_run_execution.id, expected=True
    )


def test_get_test_run_executions_by_search_query_archived(db: Session) -> None:
    title = "Test Title"
    description = "test description"
    test_run_execution = create_random_test_run_execution_archived(
        db, title=title, description=description
    )

    # Don't include archived
    __search_assert_presence(
        db, query="Title", run_id=test_run_execution.id, expected=False, archived=False
    )

    # Find in archived
    __search_assert_presence(
        db, query="Title", run_id=test_run_execution.id, expected=True, archived=True
    )


def test_get_test_run_executions_by_search_query_and_project_id(db: Session) -> None:
    title = "Test Title"
    description = "test description"
    project = create_random_project(db)
    test_run_execution = create_random_test_run_execution(
        db, title=title, description=description, project_id=project.id
    )

    # Don't find with wrong project_id
    __search_assert_presence(
        db,
        query="Title",
        run_id=test_run_execution.id,
        expected=False,
        project_id=project.id + 1,
    )

    # Find when searching with project id
    __search_assert_presence(
        db,
        query="Title",
        run_id=test_run_execution.id,
        expected=True,
        project_id=project.id,
    )


def __search_assert_presence(
    db: Session,
    query: str,
    run_id: int,
    expected: bool,
    project_id: Optional[int] = None,
    archived: bool = False,
) -> None:
    test_run_executions = crud.test_run_execution.get_multi(
        db, project_id=project_id, archived=archived, search_query=query, limit=None
    )

    if expected:
        assert any(t.id == run_id for t in test_run_executions)
    else:
        assert not any(t.id == run_id for t in test_run_executions)


def test_import_execution_invalid_project_id() -> None:
    test_run_execution_dict = deepcopy(test_run_execution_base_dict)
    test_run_execution_dict["operator"] = deepcopy(operator_base_dict)

    with mock.patch.object(
        target=crud.project, attribute="get", return_value=None
    ) as mocked_project_get, pytest.raises(ImportError):
        crud.test_run_execution.import_execution(
            db=mock.MagicMock(),
            project_id=1,
            execution=test_run_execution_dict,
        )

    mocked_project_get.assert_called_once()


def test_import_execution_success() -> None:
    mocked_db = mock.MagicMock()

    test_run_execution_dict = deepcopy(test_run_execution_base_dict)
    test_run_execution_dict["operator"] = deepcopy(operator_base_dict)

    project_id = 42
    operator_id = 2
    operator_name = operator_base_dict.get("name")

    with mock.patch.object(
        target=crud.operator,
        attribute="get_or_create",
        return_value=operator_id,
    ) as mocked_get_or_create:
        imported_test_run = crud.test_run_execution.import_execution(
            db=mocked_db,
            project_id=project_id,
            execution=schemas.TestRunExecutionToExport(**test_run_execution_dict),
        )

        mocked_get_or_create.assert_called_once_with(
            db=mocked_db, name=operator_name, commit=False
        )

        call.add(imported_test_run) in mocked_db.mock_calls
        call.commit() in mocked_db.mock_calls
        call.refresh(imported_test_run) in mocked_db.mock_calls

        assert imported_test_run.project_id == project_id
        assert imported_test_run.title == test_run_execution_dict.get("title")
        assert imported_test_run.operator_id == operator_id
