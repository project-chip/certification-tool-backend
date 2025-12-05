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
# type: ignore
# Ignore mypy type check for this file

import asyncio
from asyncio import sleep
from http import HTTPStatus
from unittest.mock import ANY, MagicMock, patch

import pytest
from faker import Faker
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import crud, schemas
from app.api.api_v1.endpoints.test_run_executions import DEFAULT_CLI_PROJECT_NAME
from app.core.config import settings
from app.main import app
from app.models import TestRunExecution, TestStateEnum
from app.models.project import Project
from app.test_engine import (
    TEST_ENGINE_ABORTING_TESTING_MESSAGE,
    TEST_ENGINE_BUSY_MESSAGE,
    TEST_ENGINE_NOT_ACTIVE_MESSAGE,
    TEST_RUN_ALREADY_EXECUTED_MESSAGE,
)
from app.test_engine.test_runner import TestRunner, TestRunnerState
from app.tests.test_engine.test_runner import load_test_run_for_test_cases
from app.tests.utils.operator import create_random_operator
from app.tests.utils.project import create_random_project
from app.tests.utils.test_run_config import create_random_test_run_config
from app.tests.utils.test_run_execution import (
    create_random_test_run_execution,
    create_random_test_run_execution_archived,
    create_random_test_run_execution_with_test_case_states,
    create_test_run_execution_with_some_test_cases,
)
from app.tests.utils.utils import random_lower_string
from app.tests.utils.validate_json_response import validate_json_response
from app.utils import remove_title_date

client = TestClient(app)


@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)


@pytest.fixture
def test_run_execution_create():
    return schemas.test_run_execution.TestRunExecutionCreate(
        title="Test Run",
        description="Test Description",
        project_id=1,
        operator_id=1,
    )


@pytest.fixture
def test_selection():
    return {"sample_tests": {"SampleTestSuite1": {"TCSS1001": 1, "TCSS1002": 1}}}


@pytest.fixture
def default_config():
    return {
        "network": {
            "wifi": {"ssid": "test_ssid", "password": "test_password"},
            "thread": {
                "channel": 15,
                "panid": "0x1234",
                "extpanid": "1122334455667788",
                "networkkey": "00112233445566778899aabbccddeeff",
                "networkname": "TestThread",
                "rcp_serial_path": "/dev/ttyACM0",
                "rcp_baudrate": 115200,
                "on_mesh_prefix": "fd11:22::",
                "network_interface": "wpan0",
                "dataset": "test-dataset",
                "operational_dataset_hex": "0e080000000000010000000300000e09",
            },
        },
        "test_parameters": {
            "matter_qa_url": "http://localhost:8080",
        },
        "dut_config": {
            "discriminator": "1234",
            "setup_code": "12345678",
            "pairing_mode": "ble-wifi",
            "chip_use_paa_certs": False,
            "trace_log": True,
        },
    }


faker = Faker()


def test_create_test_run_execution_with_selected_tests_succeeds(
    client: TestClient,
) -> None:
    """This unit test will test the create API for TestRunExecution.
    The selected tests are passed directly in the json payload. This is expected to
    succeed, and the API should respond with HTTP status 200 OK
    """
    title = "Foo"
    description = random_lower_string()
    json_data = {
        "test_run_execution_in": {
            "title": title,
            "description": description,
        },
        "selected_tests": {
            "sample_tests": {
                "SampleTestSuite1": {
                    "TCSS1001": 1,
                    "TCSS1002": 2,
                    "TCSS1003": 2,
                    "TCSS1004": 5,
                    "TCSS1005": 8,
                },
            },
        },
    }
    response = client.post(
        f"{settings.API_V1_STR}/test_run_executions/",
        json=json_data,
    )
    assert response.status_code == HTTPStatus.OK
    content = response.json()
    assert isinstance(content, dict)
    assert content.get("title") == title
    assert content.get("description") == description


def test_create_test_run_execution_with_selected_tests_and_operator_succeeds(
    client: TestClient, db: Session
) -> None:
    """This unit test will test the create API for TestRunExecution.
    The selected tests are passed directly in the json payload. This is expected to
    succeed, and the API should respond with HTTP status 200 OK
    """
    title = "Foo"
    operator = create_random_operator(db)
    json_data = {
        "test_run_execution_in": {"title": title, "operator_id": operator.id},
        "selected_tests": {
            "sample_tests": {
                "SampleTestSuite1": {"TCSS1001": 1},
            },
        },
    }
    response = client.post(
        f"{settings.API_V1_STR}/test_run_executions/",
        json=json_data,
    )
    assert response.status_code == HTTPStatus.OK
    content = response.json()
    assert isinstance(content, dict)
    assert content.get("title") == title

    response_operator = content.get("operator")
    assert response_operator is not None
    assert "id" in response_operator
    assert response_operator["id"] == operator.id
    assert "name" in response_operator
    assert response_operator["name"] == operator.name


def test_create_test_run_execution_with_selected_tests_project_operator_succeeds(
    client: TestClient, db: Session
) -> None:
    """This test will create a new test run execution. A success is expected.
    The selected tests, the project and the operator reference are passed directly by
    JSON payload.
    """

    title = "TestRunExecutionFoo"
    project = create_random_project(db, config={})
    operator = create_random_operator(db)
    json_data = {
        "test_run_execution_in": {
            "title": title,
            "operator_id": operator.id,
            "project_id": project.id,
        },
        "selected_tests": {
            "sample_tests": {
                "SampleTestSuite1": {"TCSS1001": 1},
            },
        },
    }
    response = client.post(
        f"{settings.API_V1_STR}/test_run_executions/",
        json=json_data,
    )
    assert response.status_code == HTTPStatus.OK
    content = response.json()
    assert content.get("title") == title
    assert content.get("project_id") == project.id

    response_operator = content.get("operator")
    assert response_operator is not None
    assert "id" in response_operator
    assert response_operator["id"] == operator.id
    assert "name" in response_operator
    assert response_operator["name"] == operator.name


def test_create_test_run_execution_with_test_run_config_and_selected_tests_succeeds(
    client: TestClient, db: Session
) -> None:
    """This test will create a new test run execution. A success is expected.
    The selected tests are passed directly by JSON payload.
    Also, one reference to a test run config is also included, but this is ignored by
    the API by assigning None.
    """

    test_run_config = create_random_test_run_config(db)
    title = "TestRunExecutionFoo"
    description = random_lower_string()
    json_data = {
        "test_run_execution_in": {
            "title": title,
            "description": description,
            "test_run_config_id": test_run_config.id,
        },
        "selected_tests": {
            "sample_tests": {
                "SampleTestSuite1": {
                    "TCSS1001": 1,
                    "TCSS1002": 2,
                    "TCSS1003": 4,
                    "TCSS1004": 8,
                    "TCSS1005": 16,
                },
            },
        },
    }
    response = client.post(
        f"{settings.API_V1_STR}/test_run_executions/",
        json=json_data,
    )
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_content={
            "title": title,
            "description": description,
            "test_run_config_id": None,
            "certification_mode": False,
        },
    )


def test_create_test_run_execution_with_selected_tests_with_two_suites_succeeds(
    client: TestClient,
) -> None:
    """This test will create a new test run execution with two suites selected.
    A success is expected.
    The selected tests are passed directly by JSON payload.
    """

    title = "TestRunExecutionFoo"
    description = random_lower_string()
    json_data = {
        "test_run_execution_in": {
            "title": title,
            "description": description,
        },
        "selected_tests": {
            "sample_tests": {
                "SampleTestSuite1": {
                    "TCSS1001": 1,
                    "TCSS1002": 2,
                    "TCSS1003": 4,
                    "TCSS1004": 8,
                    "TCSS1005": 16,
                },
                "SampleTestSuite2": {
                    "TCSS2001": 1,
                    "TCSS2002": 2,
                    "TCSS2003": 4,
                    "TCSS2004": 8,
                    "TCSS2005": 16,
                },
            },
        },
    }
    response = client.post(
        f"{settings.API_V1_STR}/test_run_executions/",
        json=json_data,
    )
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_keys=["id", "test_suite_executions"],
        expected_content={
            "title": title,
            "description": description,
            "certification_mode": False,
        },
    )

    content = response.json()
    suites = content.get("test_suite_executions")
    returned_suites = [s["public_id"] for s in suites]
    selected_tests = json_data["selected_tests"]["sample_tests"].keys()
    for selected_suite in selected_tests:
        assert selected_suite in returned_suites


def test_create_test_run_execution_cer_with_test_run_config_and_selected_tests_succeeds(
    client: TestClient, db: Session
) -> None:
    """This test will create a new test run execution. A success is expected.
    The selected tests are passed directly by JSON payload.
    Also, one reference to a test run config is also included, but this is ignored by
    the API by assigning None.
    """

    test_run_config = create_random_test_run_config(db)
    title = "TestRunExecutionFoo"
    description = random_lower_string()
    json_data = {
        "test_run_execution_in": {
            "title": title,
            "description": description,
            "test_run_config_id": test_run_config.id,
        },
        "selected_tests": {
            "sample_tests": {
                "SampleTestSuite1": {
                    "TCSS1001": 1,
                    "TCSS1002": 2,
                    "TCSS1003": 4,
                    "TCSS1004": 8,
                    "TCSS1005": 16,
                },
            },
        },
    }
    response = client.post(
        f"{settings.API_V1_STR}/test_run_executions/?certification_mode=True",
        json=json_data,
    )
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_content={
            "title": title,
            "description": description,
            "test_run_config_id": None,
            "certification_mode": True,
        },
    )


def test_create_test_run_execution_cert_with_selected_tests_with_3_suites_succeeds(
    client: TestClient,
) -> None:
    """This test will create a new test run execution with two suites selected.
    A success is expected.
    The selected tests are passed directly by JSON payload.
    """

    title = "TestRunExecutionFoo"
    description = random_lower_string()
    json_data = {
        "test_run_execution_in": {
            "title": title,
            "description": description,
        },
        "selected_tests": {
            "sample_tests": {
                "SampleTestSuite1": {
                    "TCSS1001": 1,
                    "TCSS1002": 2,
                    "TCSS1003": 4,
                    "TCSS1004": 8,
                    "TCSS1005": 16,
                },
                "SampleTestSuite2": {
                    "TCSS2001": 1,
                    "TCSS2002": 2,
                    "TCSS2003": 4,
                    "TCSS2004": 8,
                    "TCSS2005": 16,
                },
                "SampleTestSuite3Mandatory": {
                    "TCSS3001": 1,
                },
            },
        },
    }
    response = client.post(
        f"{settings.API_V1_STR}/test_run_executions/?certification_mode=True",
        json=json_data,
    )
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_keys=["id", "test_suite_executions"],
        expected_content={
            "title": title,
            "description": description,
            "certification_mode": True,
        },
    )

    content = response.json()
    suites = content.get("test_suite_executions")
    returned_suites = [s["public_id"] for s in suites]
    selected_tests = json_data["selected_tests"]["sample_tests"].keys()
    for selected_suite in selected_tests:
        assert selected_suite in returned_suites


def test_create_test_run_execution_without_selected_tests_fails(
    client: TestClient,
) -> None:
    """This test will try to create a new test run execution. A failure is expected.
    The selected tests is a required argument for this API and it's missing in this
    example.
    """

    title = "TestRunExecutionFoo"
    description = random_lower_string()
    json_data = {
        "test_run_execution_in": {
            "title": title,
            "description": description,
        }
    }
    response = client.post(
        f"{settings.API_V1_STR}/test_run_executions/",
        json=json_data,
    )
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        expected_keys=["detail"],
    )


def test_rename_test_run_execution_succeeds(client: TestClient, db: Session) -> None:
    renamed_title = "TestRunExecutionFoo"
    selected_tests = {
        "sample_tests": {
            "SampleTestSuite1": {"TCSS1001": 1, "TCSS1002": 2, "TCSS1003": 3}
        }
    }
    test_run_execution = create_random_test_run_execution(
        db=db, selected_tests=selected_tests
    )
    response = client.put(
        f"{settings.API_V1_STR}/test_run_executions/{test_run_execution.id}/"
        f"rename?new_execution_name={renamed_title}"
    )

    assert response.status_code == HTTPStatus.OK
    content = response.json()
    assert isinstance(content, dict)
    assert content.get("title") == renamed_title

    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_keys=["title"],
    )


def test_create_cli_test_run_execution_new_project(
    mock_db, test_run_execution_create, test_selection, default_config
):
    """Test creating a CLI test run execution with a new project"""
    # Mock project not found
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None

    # Mock test run execution creation
    mock_test_run = TestRunExecution(
        id=1,
        title=test_run_execution_create.title,
        description=test_run_execution_create.description,
        project_id=1,
        operator_id=1,
    )

    # Configure mock to return mock_test_run when needed
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        None,
        mock_test_run,
    ]

    with patch(
        "app.api.api_v1.endpoints.test_run_executions.get_db", return_value=mock_db
    ):
        response = client.post(
            f"{settings.API_V1_STR}/test_run_executions/cli",
            json={
                "test_run_execution_in": test_run_execution_create.dict(),
                "selected_tests": test_selection,
                "config": default_config,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == test_run_execution_create.title
    assert data["description"] == test_run_execution_create.description


def test_create_cli_test_run_execution_existing_project(
    mock_db, test_run_execution_create, test_selection, default_config
):
    """Test creating a CLI test run execution with an existing project"""
    # Mock existing project
    mock_project = Project(
        id=1,
        name=DEFAULT_CLI_PROJECT_NAME,
        config={},
    )
    mock_db.query.return_value.filter.return_value.first.return_value = mock_project
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None

    with patch(
        "app.api.api_v1.endpoints.test_run_executions.get_db", return_value=mock_db
    ):
        response = client.post(
            f"{settings.API_V1_STR}/test_run_executions/cli",
            json={
                "test_run_execution_in": test_run_execution_create.dict(),
                "selected_tests": test_selection,
                "config": default_config,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == test_run_execution_create.title
    assert data["description"] == test_run_execution_create.description


def test_create_cli_test_run_execution_default_config(
    mock_db, test_run_execution_create, test_selection
):
    """Test creating a CLI test run execution with default config"""
    # Mock project not found
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None

    with patch(
        "app.api.api_v1.endpoints.test_run_executions.get_db", return_value=mock_db
    ):
        response = client.post(
            f"{settings.API_V1_STR}/test_run_executions/cli",
            json={
                "test_run_execution_in": test_run_execution_create.dict(),
                "selected_tests": test_selection,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == test_run_execution_create.title
    assert data["description"] == test_run_execution_create.description


def test_create_cli_test_run_execution_invalid_data(mock_db):
    """Test creating a CLI test run execution with invalid data"""
    with patch(
        "app.api.api_v1.endpoints.test_run_executions.get_db", return_value=mock_db
    ):
        response = client.post(
            f"{settings.API_V1_STR}/test_run_executions/cli",
            json={
                "test_run_execution_in": {},
                "selected_tests": {},
            },
        )

    assert response.status_code == 422  # Validation error


def test_rename_not_valid_test_run_execution_fails(
    client: TestClient, db: Session
) -> None:
    renamed_title = "TestRunExecutionFoo"
    response = client.put(
        f"{settings.API_V1_STR}/test_run_executions/-999/"
        f"rename?new_execution_name={renamed_title}"
    )

    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.NOT_FOUND,
        expected_keys=["detail"],
    )


def test_rename_empty_execution_name_fails(client: TestClient, db: Session) -> None:
    renamed_title = " "
    selected_tests = {
        "sample_tests": {
            "SampleTestSuite1": {"TCSS1001": 1, "TCSS1002": 2, "TCSS1003": 3}
        }
    }
    test_run_execution = create_random_test_run_execution(
        db=db, selected_tests=selected_tests
    )

    response = client.put(
        f"{settings.API_V1_STR}/test_run_executions/{test_run_execution.id}/"
        f"rename?new_execution_name={renamed_title}"
    )

    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        expected_keys=["detail"],
    )


def test_repeat_existing_test_run_execution_with_two_suites_succeeds(
    client: TestClient, db: Session
) -> None:
    """This test will repeat all the tests from a previous created test run execution.
    A success is expected.
    We use a sample collection, suites and test cases to create the test run execution
    that will be repeated. The title and description are provided by the JSON payload.
    """

    selected_tests = {
        "sample_tests": {
            "SampleTestSuite1": {"TCSS1001": 1, "TCSS1002": 2, "TCSS1003": 3},
            "SampleTestSuite2": {"TCSS2004": 4, "TCSS2005": 5, "TCSS2006": 6},
        }
    }
    test_run_execution = create_random_test_run_execution(
        db=db, selected_tests=selected_tests
    )

    base_title = remove_title_date(test_run_execution.title)
    response = client.post(
        f"{settings.API_V1_STR}/test_run_executions/{test_run_execution.id}/repeat",
    )

    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_keys=["id", "title", "description", "test_suite_executions"],
        expected_content={
            "description": test_run_execution.description,
            "certification_mode": False,
        },
    )

    content = response.json()
    assert test_run_execution.id != content.get("id")
    assert base_title == remove_title_date(content.get("title"))

    suites = content.get("test_suite_executions")
    returned_suites = [s["public_id"] for s in suites]
    for selected_suite in selected_tests["sample_tests"].keys():
        assert selected_suite in returned_suites


def test_repeat_existing_test_run_execution_with_title_succeeds(
    client: TestClient, db: Session
) -> None:
    """This test will repeat all the tests from a previous created test run execution,
    with a custom title instead of the old name.
    A success is expected.
    """
    title = "TestRunExecutionFoo"
    selected_tests = {
        "sample_tests": {
            "SampleTestSuite1": {"TCSS1001": 1, "TCSS1002": 2, "TCSS1003": 3}
        }
    }
    test_run_execution = create_random_test_run_execution(
        db=db, selected_tests=selected_tests
    )
    url = f"{settings.API_V1_STR}/test_run_executions/{test_run_execution.id}/repeat"
    response = client.post(url + f"?title={title}")

    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_keys=["id", "title", "description", "test_suite_executions"],
        expected_content={"certification_mode": False},
    )
    content = response.json()
    assert title == remove_title_date(content.get("title"))


def test_repeat_existing_test_run_execution_certification_mode_with_two_suites_succeeds(
    client: TestClient, db: Session
) -> None:
    """This test will repeat all the tests from a previous created test run execution.
    A success is expected.
    We use a sample collection, suites and test cases to create the test run execution
    that will be repeated. The title and description are provided by the JSON payload.
    """

    selected_tests = {
        "sample_tests": {
            "SampleTestSuite1": {"TCSS1001": 1, "TCSS1002": 2, "TCSS1003": 3},
            "SampleTestSuite2": {"TCSS2004": 4, "TCSS2005": 5, "TCSS2006": 6},
        }
    }
    test_run_execution = create_random_test_run_execution(
        db=db, selected_tests=selected_tests, certification_mode=True
    )

    base_title = remove_title_date(test_run_execution.title)
    response = client.post(
        f"{settings.API_V1_STR}/test_run_executions/{test_run_execution.id}/repeat",
    )

    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_keys=["id", "title", "description", "test_suite_executions"],
        expected_content={
            "description": test_run_execution.description,
            "certification_mode": True,
        },
    )

    content = response.json()
    assert test_run_execution.id != content.get("id")
    assert base_title == remove_title_date(content.get("title"))

    suites = content.get("test_suite_executions")
    returned_suites = [s["public_id"] for s in suites]
    for selected_suite in selected_tests["sample_tests"].keys():
        assert selected_suite in returned_suites


def test_repeat_existing_test_run_execution_certification_mode_with_title_succeeds(
    client: TestClient, db: Session
) -> None:
    """This test will repeat all the tests from a previous created test run execution,
    with a custom title instead of the old name.
    A success is expected.
    """
    title = "TestRunExecutionFoo"
    selected_tests = {
        "sample_tests": {
            "SampleTestSuite1": {"TCSS1001": 1, "TCSS1002": 2, "TCSS1003": 3}
        }
    }
    test_run_execution = create_random_test_run_execution(
        db=db, selected_tests=selected_tests, certification_mode=True
    )
    url = f"{settings.API_V1_STR}/test_run_executions/{test_run_execution.id}/repeat"
    response = client.post(url + f"?title={title}")

    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_keys=["id", "title", "description", "test_suite_executions"],
        expected_content={"certification_mode": True},
    )
    content = response.json()
    assert title == remove_title_date(content.get("title"))


def test_repeat_non_existing_test_run_execution_fails(
    client: TestClient, db: Session
) -> None:
    """This test will try to repeat a non-existing test run execution.
    A failure is expected.
    A temporary test run execution is created and deleted it in sequence. The repeat
    feature will not have nothing to repeat anymore then.
    """
    test_run_execution_id = create_test_run_execution_with_some_test_cases(db=db).id
    crud.test_run_execution.remove(db=db, id=test_run_execution_id)

    response = client.post(
        f"{settings.API_V1_STR}/test_run_executions/{test_run_execution_id}/repeat",
    )

    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.NOT_FOUND,
        expected_keys=["detail"],
    )


def test_read_multiple_test_run_executions(client: TestClient, db: Session) -> None:
    # We generate a random test run for this test.
    # To validate the statistics, we create the run with a random number of test cases
    # with a known amount being in a passed/pending state.
    # (A total between 4 and 20 test cases)
    test_case_states = {
        TestStateEnum.PASSED: faker.pyint(2, 10),
        TestStateEnum.PENDING: faker.pyint(2, 10),
    }
    test_case_count = sum(test_case_states.values())

    # Create random data for testing
    new_test_run_execution = create_random_test_run_execution_with_test_case_states(
        db, test_case_states
    )

    # Currently, our API uses pagination to only return part of the data.
    # This is implemented using skip and limit.
    # Default is skip = 0 and limit = 100, which will return the first 100 entries.
    # In our testing we create some new test data, these will always end up in the end
    # of the list, we compute the "offset" so that we're sure to get the latest records.
    count = db.scalar(select(func.count(TestRunExecution.id))) or 0
    offset = max(0, count - 100)

    response = client.get(
        f"{settings.API_V1_STR}/test_run_executions?skip={offset}",
    )

    assert response.status_code == HTTPStatus.OK
    content = response.json()
    assert isinstance(content, list)
    for test_run in content:
        assert test_run["title"] is not None
        assert test_run["test_case_stats"] is not None

        # Assert data of new test_run_execution
        if test_run["id"] == new_test_run_execution.id:
            assert test_run["title"] == new_test_run_execution.title
            assert test_run["state"] == new_test_run_execution.state
            assert test_run["started_at"] == new_test_run_execution.started_at
            assert test_run["completed_at"] == new_test_run_execution.completed_at

            # Assert stats of new test_run_execution
            stats = test_run["test_case_stats"]
            assert isinstance(stats, dict)
            assert stats["test_case_count"] == test_case_count
            for state, count in test_case_states.items():
                stats["states"][state.name] = count


def test_read_multiple_test_run_executions_by_archived(
    client: TestClient, db: Session
) -> None:
    test_run_execution = create_random_test_run_execution_archived(db)

    limit = db.scalar(select(func.count(TestRunExecution.id))) or 0

    response = client.get(
        f"{settings.API_V1_STR}/test_run_executions?limit={limit}",
    )
    assert response.status_code == HTTPStatus.OK
    content = response.json()
    assert isinstance(content, list)
    assert not any(test_run.get("id") == test_run_execution.id for test_run in content)

    response = client.get(
        f"{settings.API_V1_STR}/test_run_executions?limit={limit}&archived=true",
    )
    assert response.status_code == HTTPStatus.OK
    content = response.json()
    assert isinstance(content, list)
    assert any(test_run.get("id") == test_run_execution.id for test_run in content)


def test_read_multiple_test_run_executions_by_project(
    client: TestClient, db: Session
) -> None:
    project = create_random_project(db, config={})
    test_run_execution = create_random_test_run_execution(db, project_id=project.id)

    response = client.get(
        f"{settings.API_V1_STR}/test_run_executions?project_id={project.id}",
    )
    assert response.status_code == HTTPStatus.OK
    content = response.json()
    assert isinstance(content, list)
    assert any(test_run.get("id") == test_run_execution.id for test_run in content)

    project2 = create_random_project(db, config={})
    response = client.get(
        f"{settings.API_V1_STR}/test_run_executions?project_id={project2.id}",
    )
    assert response.status_code == HTTPStatus.OK
    content = response.json()
    assert isinstance(content, list)
    assert len(content) == 0


def test_read_multiple_test_run_executions_with_search_query(
    client: TestClient, db: Session
) -> None:
    title = "This is bananas"
    test_run_execution = create_random_test_run_execution(db, title=title)

    response = client.get(
        f"{settings.API_V1_STR}/test_run_executions?search_query=Bananas",
    )

    assert response.status_code == 200
    content = response.json()
    assert isinstance(content, list)
    assert any(test_run.get("id") == test_run_execution.id for test_run in content)

    response = client.get(
        f"{settings.API_V1_STR}/test_run_executions?search_query=Oranges",
    )

    assert response.status_code == 200
    content = response.json()
    assert isinstance(content, list)
    assert not any(test_run.get("id") == test_run_execution.id for test_run in content)


def test_read_test_run_execution(client: TestClient, db: Session) -> None:
    # We generate a random test run for this test.
    # To validate that all test cases are returned in the response,
    # we create the run with a random number of passed test cases (2-10)
    test_case_states = {TestStateEnum.PASSED: faker.pyint(2, 10)}
    test_case_count = sum(test_case_states.values())

    new_test_run_execution = create_random_test_run_execution_with_test_case_states(
        db, test_case_states
    )

    # Get variables for asserts
    new_first_test_suite_execution = new_test_run_execution.test_suite_executions[0]
    new_test_suite_metadata = new_first_test_suite_execution.test_suite_metadata
    new_first_test_case_execution = new_first_test_suite_execution.test_case_executions[
        0
    ]
    new_test_case_metadata = new_first_test_case_execution.test_case_metadata

    # Perform request
    response = client.get(
        f"{settings.API_V1_STR}/test_run_executions/{new_test_run_execution.id}",
    )

    assert response.status_code == HTTPStatus.OK
    content = response.json()
    assert isinstance(content, dict)

    # Assert Test Run Execution fields
    assert content["id"] == new_test_run_execution.id
    assert content["title"] == new_test_run_execution.title
    assert content["state"] == new_test_run_execution.state
    assert content["started_at"] == new_test_run_execution.started_at
    assert content["completed_at"] == new_test_run_execution.completed_at
    test_suite_executions = content["test_suite_executions"]

    # Assert nested Test Suite Execution fields
    assert isinstance(test_suite_executions, list)
    assert len(test_suite_executions) == len(
        new_test_run_execution.test_suite_executions
    )
    first_test_suite_execution = test_suite_executions[0]
    assert first_test_suite_execution["id"] == new_first_test_suite_execution.id
    assert first_test_suite_execution["state"] == new_first_test_suite_execution.state
    assert (
        first_test_suite_execution["public_id"]
        == new_first_test_suite_execution.public_id
    )

    # Assert Test Suite Metadata
    test_suite_metadata = first_test_suite_execution["test_suite_metadata"]
    assert isinstance(test_suite_metadata, dict)
    assert test_suite_metadata["public_id"] == new_test_suite_metadata.public_id
    assert test_suite_metadata["title"] == new_test_suite_metadata.title
    assert test_suite_metadata["description"] == new_test_suite_metadata.description
    assert test_suite_metadata["version"] == new_test_suite_metadata.version
    assert test_suite_metadata["source_hash"] == new_test_suite_metadata.source_hash
    assert test_suite_metadata["id"] == new_test_suite_metadata.id

    # Assert nested Test Case Executions
    test_case_executions = first_test_suite_execution["test_case_executions"]
    assert isinstance(test_case_executions, list)
    assert len(test_case_executions) == test_case_count

    first_test_case_execution = test_case_executions[0]
    assert isinstance(first_test_case_execution, dict)

    assert first_test_case_execution["id"] == new_first_test_case_execution.id
    assert first_test_case_execution["state"] == new_first_test_case_execution.state
    assert (
        first_test_case_execution["public_id"]
        == new_first_test_case_execution.public_id
    )

    assert isinstance(first_test_case_execution["test_step_executions"], list)

    # Assert Test Case Metadata
    test_case_metadata = first_test_case_execution["test_case_metadata"]
    assert isinstance(test_case_metadata, dict)
    assert test_case_metadata["public_id"] == new_test_case_metadata.public_id
    assert test_case_metadata["title"] == new_test_case_metadata.title
    assert test_case_metadata["description"] == new_test_case_metadata.description
    assert test_case_metadata["version"] == new_test_case_metadata.version
    assert test_case_metadata["source_hash"] == new_test_case_metadata.source_hash
    assert test_case_metadata["id"] == new_test_case_metadata.id


@pytest.mark.asyncio
async def test_test_run_execution_start(async_client: AsyncClient, db: Session) -> None:
    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)

    # First attempt to start test run
    response = await async_client.post(
        f"{settings.API_V1_STR}/test_run_executions/{test_run_execution.id}/start",
    )

    # Assert 200 OK and that test run data is returned
    assert response.status_code == HTTPStatus.OK
    content = response.json()
    assert isinstance(content, dict)
    assert content["id"] == test_run_execution.id


@pytest.mark.asyncio
async def test_test_run_execution_busy(async_client: AsyncClient, db: Session) -> None:
    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)

    # Start TestRunner (singleton)
    test_runner = TestRunner()
    test_runner.load_test_run(test_run_execution.id)
    run_task = asyncio.create_task(test_runner.run())

    # Yield event loop
    await sleep(0)

    # First attempt to start test run while test is running
    response = await async_client.post(
        f"{settings.API_V1_STR}/test_run_executions/{test_run_execution.id}/start",
    )

    # Assert 409 stats and a detail error message
    assert response.status_code == HTTPStatus.CONFLICT
    content = response.json()
    assert isinstance(content, dict)
    assert "detail" in content.keys()
    assert content["detail"] == TEST_ENGINE_BUSY_MESSAGE

    # Wait for test runner to complete
    await run_task

    # Attempt to start a test run again
    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)
    response = await async_client.post(
        f"{settings.API_V1_STR}/test_run_executions/{test_run_execution.id}/start",
    )

    # Assert 200 OK and that test run data is returned
    assert response.status_code == HTTPStatus.OK
    content = response.json()
    assert isinstance(content, dict)
    assert content["id"] == test_run_execution.id


@pytest.mark.asyncio
async def test_test_run_execution_cancel_not_running(
    async_client: AsyncClient, db: Session
) -> None:
    # Request abort testing
    response = await async_client.post(
        f"{settings.API_V1_STR}/test_run_executions/abort-testing",
    )

    # Assert 409 stats and a detail error message
    assert response.status_code == HTTPStatus.CONFLICT
    content = response.json()
    assert isinstance(content, dict)
    assert "detail" in content.keys()
    assert content["detail"] == TEST_ENGINE_NOT_ACTIVE_MESSAGE


@pytest.mark.asyncio
async def test_test_run_execution_cancel(
    async_client: AsyncClient, db: Session
) -> None:
    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)

    # Start TestRunner (singleton)
    test_runner = TestRunner()
    test_runner.load_test_run(test_run_execution.id)

    # Save test_run reference to inspect models after completion
    test_run = test_runner.test_run
    assert test_run is not None

    run_task = asyncio.create_task(test_runner.run())

    # Yield event loop
    await sleep(0)

    # Request abort testing
    response = await async_client.post(
        f"{settings.API_V1_STR}/test_run_executions/abort-testing",
    )

    # Assert 200 OK and that detail is provided
    assert response.status_code == HTTPStatus.OK
    content = response.json()
    assert isinstance(content, dict)
    assert "detail" in content.keys()
    assert content["detail"] == TEST_ENGINE_ABORTING_TESTING_MESSAGE

    # Wait for run to complete
    await run_task

    # We don't know how far the testing got, but the last test_suite and test_case
    # should be cancelled
    last_test_suite = test_run.test_suites[-1]
    assert last_test_suite is not None
    assert last_test_suite.state == TestStateEnum.CANCELLED

    last_test_case = last_test_suite.test_cases[-1]
    assert last_test_case is not None
    assert last_test_case.state == TestStateEnum.CANCELLED


@pytest.mark.asyncio
async def test_test_run_execution_rerun_error(
    async_client: AsyncClient, db: Session
) -> None:
    """Start executing a test_run_execution that has already been executed.

    This is expected to fail and the API is expected to throw an error.

    Args:
        async_client (AsyncClient): HTTP client fixture for performing API calls.
        db (Session): Database fixture for creating test data.
    """

    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)

    # Execute test run once
    test_runner = TestRunner()
    test_runner.load_test_run(test_run_execution.id)
    await test_runner.run()

    # Attempt to start test run again
    response = await async_client.post(
        f"{settings.API_V1_STR}/test_run_executions/{test_run_execution.id}/start"
    )

    # Assert 409 stats and a detail error message
    assert response.status_code == HTTPStatus.CONFLICT
    content = response.json()
    assert isinstance(content, dict)
    assert "detail" in content.keys()
    assert content["detail"] == TEST_RUN_ALREADY_EXECUTED_MESSAGE


@pytest.mark.asyncio
async def test_remove_test_run_execution_success(
    async_client: AsyncClient, db: Session
) -> None:
    """
    Test the removal of test run execution
    """
    operator = create_random_operator(db)
    test_run_execution = create_test_run_execution_with_some_test_cases(
        db=db, operator_id=operator.id
    )

    # Execute test run once
    test_runner = TestRunner()
    test_runner.load_test_run(test_run_execution.id)
    await test_runner.run()
    assert test_runner.state == TestRunnerState.IDLE

    # Remove test run execution
    response = await async_client.delete(
        f"{settings.API_V1_STR}/test_run_executions/{test_run_execution.id}",
    )

    # Assert 200 OK and that test run data is returned
    assert response.status_code == HTTPStatus.OK
    content = response.json()
    assert isinstance(content, dict)
    assert content["id"] == test_run_execution.id

    response = await async_client.delete(
        f"{settings.API_V1_STR}/test_run_executions/{test_run_execution.id}",
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_remove_test_run_execution_failed_running(
    async_client: AsyncClient, db: Session
) -> None:
    """
    Test the removal of test run execution when test run is still running
    """
    test_run_execution = create_test_run_execution_with_some_test_cases(db=db)

    # Execute test run once
    test_runner = TestRunner()
    test_runner.load_test_run(test_run_execution.id)

    run_task = asyncio.create_task(test_runner.run())

    # Yield the run loop to allow run task to be scheduled now
    # See https://docs.python.org/3.10/library/asyncio-task.html#sleeping
    await asyncio.sleep(0)

    assert test_runner.state == TestRunnerState.RUNNING

    # Remove test run execution
    response = await async_client.delete(
        f"{settings.API_V1_STR}/test_run_executions/{test_run_execution.id}",
    )

    # Assert 409 test run still running
    assert response.status_code == HTTPStatus.CONFLICT

    # Ensure test runner finishes before next unit test
    await run_task


def test_test_runner_status_idle(client: TestClient) -> None:
    """Get Test Runner status when test runner is idle."""
    response = client.get(f"{settings.API_V1_STR}/test_run_executions/status")

    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_content={"state": "idle"},
        dissalowed_keys=["test_run_execution"],
    )


@pytest.mark.asyncio
async def test_test_runner_status_running(
    async_client: AsyncClient, db: Session
) -> None:
    selected_tests = {
        "tool_unit_tests": {
            "TestSuiteExpected": {"TCTRExpectedPass": 1},
        }
    }

    test_runner = load_test_run_for_test_cases(db=db, test_cases=selected_tests)

    # Start running tests (async)
    run_task = asyncio.create_task(test_runner.run())

    # Yield the run loop to allow run task to be scheduled now
    # See https://docs.python.org/3.10/library/asyncio-task.html#sleeping
    await asyncio.sleep(0)

    assert test_runner.state == TestRunnerState.RUNNING

    response = await async_client.get(
        f"{settings.API_V1_STR}/test_run_executions/status"
    )

    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_content={"state": "running"},
        expected_keys=["test_run_execution_id"],
    )

    # Ensure test runner finishes before next unit test
    await run_task


def test_archive_project(client: TestClient, db: Session) -> None:
    test_run_execution = create_random_test_run_execution(db)
    response = client.post(
        f"{settings.API_V1_STR}/test_run_executions/{test_run_execution.id}/archive"
    )
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_content={"id": test_run_execution.id, "certification_mode": False},
        expected_keys=["archived_at"],
    )


def test_unarchive_test_run_execution(client: TestClient, db: Session) -> None:
    test_run_execution = create_random_test_run_execution(db)
    response = client.post(
        f"{settings.API_V1_STR}/test_run_executions/{test_run_execution.id}/unarchive"
    )
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_content={
            "id": test_run_execution.id,
            "archived_at": None,
            "certification_mode": False,
        },
    )


def test_archive_project_certification_mode(client: TestClient, db: Session) -> None:
    test_run_execution = create_random_test_run_execution(db, certification_mode=True)
    response = client.post(
        f"{settings.API_V1_STR}/test_run_executions/{test_run_execution.id}/archive"
    )
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_content={"id": test_run_execution.id, "certification_mode": True},
        expected_keys=["archived_at"],
    )


def test_unarchive_test_run_execution_certification_mode(
    client: TestClient, db: Session
) -> None:
    test_run_execution = create_random_test_run_execution(db, certification_mode=True)
    response = client.post(
        f"{settings.API_V1_STR}/test_run_executions/{test_run_execution.id}/unarchive"
    )
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_content={
            "id": test_run_execution.id,
            "archived_at": None,
            "certification_mode": True,
        },
    )


def test_archive_project_with_description(client: TestClient, db: Session) -> None:
    description = random_lower_string()
    test_run_execution = create_random_test_run_execution(db, description=description)
    response = client.post(
        f"{settings.API_V1_STR}/test_run_executions/{test_run_execution.id}/archive"
    )
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_content={"id": test_run_execution.id, "description": description},
        expected_keys=["archived_at", "description"],
    )


def test_unarchive_test_run_execution_description(
    client: TestClient, db: Session
) -> None:
    description = random_lower_string()
    test_run_execution = create_random_test_run_execution(db, description=description)
    response = client.post(
        f"{settings.API_V1_STR}/test_run_executions/{test_run_execution.id}/unarchive"
    )
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_content={
            "id": test_run_execution.id,
            "archived_at": None,
            "description": description,
        },
        expected_keys=["description"],
    )


def test_operations_missing_test_run(client: TestClient, db: Session) -> None:
    """Test HTTP errors when attempting operations on an invalid record id.

    Will create and delete a test run, to ensure the id is invalid."""
    test_run = create_random_test_run_execution(db)
    id = test_run.id
    crud.test_run_execution.remove(db=db, id=id)

    # Get
    response = client.get(f"{settings.API_V1_STR}/test_run_executions/{id}")
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.NOT_FOUND,
        expected_keys=["detail"],
    )

    # Delete
    response = client.delete(f"{settings.API_V1_STR}/test_run_executions/{id}")
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.NOT_FOUND,
        expected_keys=["detail"],
    )

    # Archive
    response = client.post(f"{settings.API_V1_STR}/test_run_executions/{id}/archive")
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.NOT_FOUND,
        expected_keys=["detail"],
    )

    # Unarchive
    response = client.post(f"{settings.API_V1_STR}/test_run_executions/{id}/unarchive")
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.NOT_FOUND,
        expected_keys=["detail"],
    )

    # Start Run
    response = client.post(f"{settings.API_V1_STR}/test_run_executions/{id}/start")
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.NOT_FOUND,
        expected_keys=["detail"],
    )

    # Download log
    response = client.get(f"{settings.API_V1_STR}/test_run_executions/{id}/log")
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.NOT_FOUND,
        expected_keys=["detail"],
    )


def test_create_cli_test_run_execution_with_valid_project_id_in_execution(
    mock_db, test_run_execution_create, test_selection, default_config
):
    """Test creating a CLI test run execution with a valid project_id in
    test_run_execution_in"""
    # Set project_id in the test_run_execution_create object
    test_run_execution_create.project_id = 123

    # Mock existing project with specific ID
    mock_project = Project(
        id=123,
        name="Specific Test Project",
        config={},
    )

    # Mock test run execution
    mock_test_run = TestRunExecution(
        id=1,
        title=test_run_execution_create.title,
        description=test_run_execution_create.description,
        project_id=123,
        operator_id=1,
        certification_mode=False,
        state=TestStateEnum.PENDING,
        started_at=None,
        completed_at=None,
        imported_at=None,
        archived_at=None,
    )

    with patch(
        "app.api.api_v1.endpoints.test_run_executions.get_db", return_value=mock_db
    ), patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.project.get",
        return_value=mock_project,
    ), patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.project.update",
        return_value=mock_project,
    ), patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.test_run_execution.create",
        return_value=mock_test_run,
    ):
        response = client.post(
            f"{settings.API_V1_STR}/test_run_executions/cli",
            json={
                "test_run_execution_in": test_run_execution_create.dict(),
                "selected_tests": test_selection,
                "config": default_config,
                "pics": {},
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == test_run_execution_create.title
    assert data["project_id"] == 123


def test_create_cli_test_run_execution_with_invalid_project_id_in_execution(
    mock_db, test_run_execution_create, test_selection, default_config
):
    """Test creating a CLI test run execution with an invalid project_id in
    test_run_execution_in"""
    # Set invalid project_id in the test_run_execution_create object
    test_run_execution_create.project_id = 999

    with patch(
        "app.api.api_v1.endpoints.test_run_executions.get_db", return_value=mock_db
    ), patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.project.get",
        return_value=None,
    ):
        response = client.post(
            f"{settings.API_V1_STR}/test_run_executions/cli",
            json={
                "test_run_execution_in": test_run_execution_create.dict(),
                "selected_tests": test_selection,
                "config": default_config,
                "pics": {},
            },
        )

    assert response.status_code == HTTPStatus.NOT_FOUND
    data = response.json()
    assert "Project with ID 999 not found" in data["detail"]


def test_create_cli_test_run_execution_without_project_id_in_execution_uses_default(
    mock_db, test_run_execution_create, test_selection, default_config
):
    """Test creating a CLI test run execution without project_id in
    test_run_execution_in uses default CLI project"""
    # Ensure project_id is None in test_run_execution_create
    test_run_execution_create.project_id = None

    # Mock default CLI project
    mock_cli_project = Project(
        id=1,
        name=DEFAULT_CLI_PROJECT_NAME,
        config={},
    )

    mock_test_run = TestRunExecution(
        id=1,
        title=test_run_execution_create.title,
        description=test_run_execution_create.description,
        project_id=1,
        operator_id=1,
        certification_mode=False,
        state=TestStateEnum.PENDING,
        started_at=None,
        completed_at=None,
        imported_at=None,
        archived_at=None,
    )

    # Comprehensive mocking for all possible paths in the CLI project flow
    with patch(
        "app.api.api_v1.endpoints.test_run_executions.get_db", return_value=mock_db
    ), patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.project.get_by_name",
        return_value=mock_cli_project,
    ), patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.project.update",
        return_value=mock_cli_project,
    ), patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.project.create",
        return_value=mock_cli_project,
    ), patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.test_run_execution.create",
        return_value=mock_test_run,
    ):
        response = client.post(
            f"{settings.API_V1_STR}/test_run_executions/cli",
            json={
                "test_run_execution_in": test_run_execution_create.dict(),
                "selected_tests": test_selection,
                "config": default_config,
                "pics": {},
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == test_run_execution_create.title
    assert data["project_id"] == 1  # Default CLI project ID


def test_create_cli_test_run_execution_creates_default_project_when_missing(
    mock_db, test_run_execution_create, test_selection, default_config
):
    """Test creating a CLI test run execution creates default CLI project if it doesn't
    exist"""
    # Ensure project_id is None in test_run_execution_create
    test_run_execution_create.project_id = None

    mock_new_project = Project(
        id=1,
        name=DEFAULT_CLI_PROJECT_NAME,
        config=default_config,
    )

    mock_test_run = TestRunExecution(
        id=1,
        title=test_run_execution_create.title,
        description=test_run_execution_create.description,
        project_id=1,
        operator_id=1,
        certification_mode=False,
        state=TestStateEnum.PENDING,
    )

    with patch(
        "app.api.api_v1.endpoints.test_run_executions.get_db", return_value=mock_db
    ), patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.project.get_by_name",
        return_value=None,
    ), patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.project.create",
        return_value=mock_new_project,
    ), patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.project.update",
        return_value=mock_new_project,
    ), patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.test_run_execution.create",
        return_value=mock_test_run,
    ):
        response = client.post(
            f"{settings.API_V1_STR}/test_run_executions/cli",
            json={
                "test_run_execution_in": test_run_execution_create.dict(),
                "selected_tests": test_selection,
                "config": default_config,
                "pics": {},
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == test_run_execution_create.title
    assert data["project_id"] == 1


def test_create_cli_test_run_execution_with_none_project_id_uses_default(
    mock_db, test_run_execution_create, test_selection, default_config
):
    """Test creating a CLI test run execution with project_id=None uses the default
    CLI project."""
    # Set project_id to None to test the default project logic
    test_run_execution_create.project_id = None

    # Mock default CLI project
    mock_cli_project = Project(
        id=1,
        name=DEFAULT_CLI_PROJECT_NAME,
        config={},
    )

    mock_test_run = TestRunExecution(
        id=1,
        title=test_run_execution_create.title,
        description=test_run_execution_create.description,
        project_id=1,
        operator_id=1,
        certification_mode=False,
        state=TestStateEnum.PENDING,
        started_at=None,
        completed_at=None,
        imported_at=None,
        archived_at=None,
    )

    # Comprehensive mocking for all possible paths in the CLI project flow
    with patch(
        "app.api.api_v1.endpoints.test_run_executions.get_db", return_value=mock_db
    ), patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.project.get_by_name",
        return_value=mock_cli_project,
    ), patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.project.update",
        return_value=mock_cli_project,
    ), patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.project.create",
        return_value=mock_cli_project,
    ), patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.test_run_execution.create",
        return_value=mock_test_run,
    ):
        response = client.post(
            f"{settings.API_V1_STR}/test_run_executions/cli",
            json={
                "test_run_execution_in": test_run_execution_create.dict(),
                "selected_tests": test_selection,
                "config": default_config,
                "pics": {},
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == test_run_execution_create.title
    assert data["project_id"] == 1  # Default CLI project ID


def test_create_cli_test_run_execution_updates_existing_project_with_config(
    mock_db, test_run_execution_create, test_selection, default_config
):
    """Test that when project_id is provided, the existing project is updated with the
    config."""
    # Set project_id in the test_run_execution_create object
    test_run_execution_create.project_id = 123

    # Mock existing project with specific ID
    mock_project = Project(
        id=123,
        name="Existing Test Project",
        config={"old_key": "old_value"},
    )

    # Updated project after config update
    mock_updated_project = Project(
        id=123,
        name="Existing Test Project",
        config=default_config,
    )

    # Mock test run execution
    mock_test_run = TestRunExecution(
        id=1,
        title=test_run_execution_create.title,
        description=test_run_execution_create.description,
        project_id=123,
        operator_id=1,
        certification_mode=False,
        state=TestStateEnum.PENDING,
        started_at=None,
        completed_at=None,
        imported_at=None,
        archived_at=None,
    )

    with patch(
        "app.api.api_v1.endpoints.test_run_executions.get_db", return_value=mock_db
    ), patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.project.get",
        return_value=mock_project,
    ) as mock_get, patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.project.update",
        return_value=mock_updated_project,
    ) as mock_update, patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.test_run_execution.create",
        return_value=mock_test_run,
    ):
        response = client.post(
            f"{settings.API_V1_STR}/test_run_executions/cli",
            json={
                "test_run_execution_in": test_run_execution_create.dict(),
                "selected_tests": test_selection,
                "config": default_config,
                "pics": {},
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == test_run_execution_create.title
    assert data["project_id"] == 123

    # Verify that project.get was called with the correct ID
    mock_get.assert_called_once_with(db=ANY, id=123)

    # Verify that project.update was called to update the config
    mock_update.assert_called_once()
    args, kwargs = mock_update.call_args
    assert kwargs["db"] is not None
    assert kwargs["db_obj"] == mock_project
    # Verify the ProjectUpdate object has the config
    project_update = kwargs["obj_in"]
    assert project_update.config == default_config


def test_create_cli_test_run_execution_updates_existing_project_with_config_and_pics(
    mock_db, test_run_execution_create, test_selection, default_config
):
    """Test that when project_id is provided, the existing project is updated with both
    config and PICS."""
    # Set project_id in the test_run_execution_create object
    test_run_execution_create.project_id = 456

    # Sample PICS data
    pics_data = {
        "clusters": {
            "OnOff": {
                "name": "OnOff",
                "items": {
                    "OO.S.A0000": {"number": "OO.S.A0000", "enabled": True},
                    "OO.S.C00.Rsp": {"number": "OO.S.C00.Rsp", "enabled": False},
                },
            }
        }
    }

    # Mock existing project with specific ID
    mock_project = Project(
        id=456,
        name="Existing Test Project",
        config={"old_key": "old_value"},
        pics=None,
    )

    # Updated project after config and PICS update
    mock_updated_project = Project(
        id=456,
        name="Existing Test Project",
        config=default_config,
        pics=pics_data,
    )

    # Mock test run execution
    mock_test_run = TestRunExecution(
        id=1,
        title=test_run_execution_create.title,
        description=test_run_execution_create.description,
        project_id=456,
        operator_id=1,
        certification_mode=False,
        state=TestStateEnum.PENDING,
        started_at=None,
        completed_at=None,
        imported_at=None,
        archived_at=None,
    )

    with patch(
        "app.api.api_v1.endpoints.test_run_executions.get_db", return_value=mock_db
    ), patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.project.get",
        return_value=mock_project,
    ) as mock_get, patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.project.update",
        return_value=mock_updated_project,
    ) as mock_update, patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.test_run_execution.create",
        return_value=mock_test_run,
    ):
        response = client.post(
            f"{settings.API_V1_STR}/test_run_executions/cli",
            json={
                "test_run_execution_in": test_run_execution_create.dict(),
                "selected_tests": test_selection,
                "config": default_config,
                "pics": pics_data,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == test_run_execution_create.title
    assert data["project_id"] == 456

    # Verify that project.get was called with the correct ID
    mock_get.assert_called_once_with(db=ANY, id=456)

    # Verify that project.update was called to update both config and PICS
    mock_update.assert_called_once()
    args, kwargs = mock_update.call_args
    assert kwargs["db"] is not None
    assert kwargs["db_obj"] == mock_project
    # Verify the ProjectUpdate object has both config and PICS
    project_update = kwargs["obj_in"]
    assert project_update.config == default_config
    assert project_update.pics is not None
    assert project_update.pics.clusters["OnOff"].name == "OnOff"


def test_create_cli_test_run_execution_updates_existing_project_config_only_no_pics(
    mock_db, test_run_execution_create, test_selection, default_config
):
    """Test that when project_id is provided without PICS, only config is updated."""
    # Set project_id in the test_run_execution_create object
    test_run_execution_create.project_id = 789

    # Mock existing project with specific ID and existing PICS
    mock_project = Project(
        id=789,
        name="Existing Test Project",
        config={"old_key": "old_value"},
        pics={"clusters": {"existing": "data"}},
    )

    # Updated project after config update only
    mock_updated_project = Project(
        id=789,
        name="Existing Test Project",
        config=default_config,
        pics={"clusters": {"existing": "data"}},  # PICS should remain unchanged
    )

    # Mock test run execution
    mock_test_run = TestRunExecution(
        id=1,
        title=test_run_execution_create.title,
        description=test_run_execution_create.description,
        project_id=789,
        operator_id=1,
        certification_mode=False,
        state=TestStateEnum.PENDING,
        started_at=None,
        completed_at=None,
        imported_at=None,
        archived_at=None,
    )

    with patch(
        "app.api.api_v1.endpoints.test_run_executions.get_db", return_value=mock_db
    ), patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.project.get",
        return_value=mock_project,
    ) as mock_get, patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.project.update",
        return_value=mock_updated_project,
    ) as mock_update, patch(
        "app.api.api_v1.endpoints.test_run_executions.crud.test_run_execution.create",
        return_value=mock_test_run,
    ):
        response = client.post(
            f"{settings.API_V1_STR}/test_run_executions/cli",
            json={
                "test_run_execution_in": test_run_execution_create.dict(),
                "selected_tests": test_selection,
                "config": default_config,
                "pics": {},  # Empty PICS
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == test_run_execution_create.title
    assert data["project_id"] == 789

    # Verify that project.get was called with the correct ID
    mock_get.assert_called_once_with(db=ANY, id=789)

    # Verify that project.update was called to update only config
    mock_update.assert_called_once()
    args, kwargs = mock_update.call_args
    assert kwargs["db"] is not None
    assert kwargs["db_obj"] == mock_project
    # Verify the ProjectUpdate object has config but no PICS
    project_update = kwargs["obj_in"]
    assert project_update.config == default_config
    # PICS should be set to empty PICS object when empty dict is provided
    assert project_update.pics is not None
    assert project_update.pics.clusters == {}
