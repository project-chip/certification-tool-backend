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
"""Tests for the GET /api/v1/projects/{id}/logs endpoint."""
from http import HTTPStatus
from io import BytesIO
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.tests.utils.project import create_random_project
from app.tests.utils.test_run_execution import create_random_test_run_execution

BASE_URL = f"{settings.API_V1_STR}/projects"


def test_download_project_logs_flat_returns_zip(
    client: TestClient, db: Session
) -> None:
    """Flat log download returns a zip archive with one .log file per execution."""
    project = create_random_project(db, config={})
    exec1 = create_random_test_run_execution(db, project_id=project.id)
    exec2 = create_random_test_run_execution(db, project_id=project.id)

    url = f"{BASE_URL}/{project.id}/logs"
    response = client.get(url)

    assert response.status_code == HTTPStatus.OK
    assert response.headers["content-type"] == "application/zip"
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["content-disposition"].endswith("-logs.zip\"")

    with ZipFile(BytesIO(response.content)) as zf:
        names = zf.namelist()
        assert any(name.endswith(".log") for name in names)
        assert any(str(exec1.id) in name for name in names)
        assert any(str(exec2.id) in name for name in names)


def test_download_project_logs_grouped_returns_zip_of_zips(
    client: TestClient, db: Session
) -> None:
    """Grouped log download returns a zip archive with one inner .zip per execution."""
    project = create_random_project(db, config={})
    exec1 = create_random_test_run_execution(db, project_id=project.id)

    url = f"{BASE_URL}/{project.id}/logs?grouped=true"
    response = client.get(url)

    assert response.status_code == HTTPStatus.OK
    assert response.headers["content-type"] == "application/zip"

    with ZipFile(BytesIO(response.content)) as zf:
        names = zf.namelist()
        assert any(name.endswith(".zip") for name in names)
        assert any(str(exec1.id) in name for name in names)


def test_download_project_logs_empty_project_returns_empty_zip(
    client: TestClient, db: Session
) -> None:
    """A project with no executions returns a valid but empty zip."""
    project = create_random_project(db, config={})

    url = f"{BASE_URL}/{project.id}/logs"
    response = client.get(url)

    assert response.status_code == HTTPStatus.OK
    with ZipFile(BytesIO(response.content)) as zf:
        assert zf.namelist() == []


def test_download_project_logs_filename_derived_from_project_name(
    client: TestClient, db: Session
) -> None:
    """The Content-Disposition filename is derived from the project name."""
    project = create_random_project(db, config={})

    url = f"{BASE_URL}/{project.id}/logs"
    response = client.get(url)

    assert response.status_code == HTTPStatus.OK
    content_disposition = response.headers["content-disposition"]
    assert "logs.zip" in content_disposition


def test_download_project_logs_not_found(client: TestClient) -> None:
    """Returns 404 when the project does not exist."""
    url = f"{BASE_URL}/999999/logs"
    response = client.get(url)

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_download_project_logs_flat_entry_names(
    client: TestClient, db: Session
) -> None:
    """Each flat log entry in the zip is named <id>-<title>.log."""
    project = create_random_project(db, config={})
    execution = create_random_test_run_execution(db, project_id=project.id)

    url = f"{BASE_URL}/{project.id}/logs"
    response = client.get(url)

    assert response.status_code == HTTPStatus.OK
    with ZipFile(BytesIO(response.content)) as zf:
        expected_entry = f"{execution.id}-{execution.title}.log"
        assert expected_entry in zf.namelist()


def test_download_project_logs_grouped_entry_names(
    client: TestClient, db: Session
) -> None:
    """Each grouped log entry in the zip is named <id>-<title>.zip."""
    project = create_random_project(db, config={})
    execution = create_random_test_run_execution(db, project_id=project.id)

    url = f"{BASE_URL}/{project.id}/logs?grouped=true"
    response = client.get(url)

    assert response.status_code == HTTPStatus.OK
    with ZipFile(BytesIO(response.content)) as zf:
        expected_entry = f"{execution.id}-{execution.title}.zip"
        assert expected_entry in zf.namelist()
