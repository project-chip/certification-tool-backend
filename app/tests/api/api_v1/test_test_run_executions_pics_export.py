#
# Copyright (c) 2026 Project CHIP Authors
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
"""Tests for the GET /api/v1/test_run_executions/{id}/pics_export endpoint."""
from http import HTTPStatus
from io import BytesIO, StringIO
from zipfile import ZipFile

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.pics.pics_parser import PICSParser
from app.tests.utils.project import create_random_project
from app.tests.utils.test_pics_data import (
    create_random_pics,
    create_random_project_with_pics,
)
from app.tests.utils.test_run_execution import create_random_test_run_execution

BASE_URL = f"{settings.API_V1_STR}/test_run_executions"


class _NamedStringIO(StringIO):
    """PICSParser reads `file.name` for logging; plain StringIO lacks it."""

    name = "exported.xml"


def test_pics_export_returns_zip_of_project_pics(
    client: TestClient, db: Session
) -> None:
    """When the execution has no explicit execution_pics override at
    creation time, its execution_pics is snapshotted from the project's
    PICS at that time, and the export reflects that snapshot."""
    project = create_random_project_with_pics(db, config={})
    execution = create_random_test_run_execution(db, project_id=project.id)

    response = client.get(f"{BASE_URL}/{execution.id}/pics_export")

    assert response.status_code == HTTPStatus.OK
    assert response.headers["content-type"] == "application/zip"
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["content-disposition"].endswith('-pics.zip"')

    with ZipFile(BytesIO(response.content)) as zf:
        names = zf.namelist()
        assert names == ["On_Off.xml"]

        parsed = PICSParser.parse(file=_NamedStringIO(zf.read(names[0]).decode()))
        expected_cluster = project.pics.clusters["On/Off"]
        assert parsed.name == expected_cluster.name
        for number, item in expected_cluster.items.items():
            assert parsed.items[number].enabled == item.enabled


def test_pics_export_reflects_pics_at_execution_time_not_current_project_pics(
    client: TestClient, db: Session
) -> None:
    """The export must reflect what PICS were in effect when the execution
    was created, even if the project's PICS are edited afterwards.

    This is the scenario the feature exists for (replacing log-scraping,
    which reflected historical PICS): editing a project's PICS after a run
    completed must not silently rewrite what that historical run appears
    to have used.
    """
    project = create_random_project_with_pics(db, config={})
    original_cluster = project.pics.clusters["On/Off"]
    original_states = {
        num: item.enabled for num, item in original_cluster.items.items()
    }

    execution = create_random_test_run_execution(db, project_id=project.id)

    # Edit the project's PICS *after* the execution was created: flip every
    # item to the opposite of its original state. Mutate the model directly
    # (rather than crud.project.update, which also validates/requires the
    # program config and isn't what's under test here).
    edited_pics = create_random_pics()
    for item in edited_pics.clusters["On/Off"].items.values():
        item.enabled = not original_states[item.number]
    project.pics = edited_pics
    db.add(project)
    db.commit()

    response = client.get(f"{BASE_URL}/{execution.id}/pics_export")

    assert response.status_code == HTTPStatus.OK
    with ZipFile(BytesIO(response.content)) as zf:
        parsed = PICSParser.parse(file=_NamedStringIO(zf.read("On_Off.xml").decode()))
        # Must match the ORIGINAL states (as of execution creation), not the
        # project's current (edited, now-inverted) states.
        for number, original_enabled in original_states.items():
            assert parsed.items[number].enabled == original_enabled


def test_pics_export_prefers_execution_pics_over_project_pics(
    client: TestClient, db: Session
) -> None:
    """When execution_pics is set on the execution, the export reflects it
    instead of the (possibly since-changed) project PICS."""
    project = create_random_project_with_pics(db, config={})
    execution = create_random_test_run_execution(db, project_id=project.id)

    execution_pics = {
        "clusters": {
            "TestCluster": {
                "name": "TestCluster",
                "items": {"TC.S.A0000": {"number": "TC.S.A0000", "enabled": True}},
            }
        }
    }
    execution.execution_pics = execution_pics
    db.add(execution)
    db.commit()

    response = client.get(f"{BASE_URL}/{execution.id}/pics_export")

    assert response.status_code == HTTPStatus.OK
    with ZipFile(BytesIO(response.content)) as zf:
        names = zf.namelist()
        assert names == ["TestCluster.xml"]

        parsed = PICSParser.parse(file=_NamedStringIO(zf.read(names[0]).decode()))
        assert parsed.items["TC.S.A0000"].enabled is True


def test_pics_export_with_no_pics_returns_not_found(
    client: TestClient, db: Session
) -> None:
    """A project with no PICS configured returns 404 instead of an empty zip."""
    project = create_random_project(db, config={})
    execution = create_random_test_run_execution(db, project_id=project.id)

    response = client.get(f"{BASE_URL}/{execution.id}/pics_export")

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_pics_export_with_empty_execution_pics_returns_not_found(
    client: TestClient, db: Session
) -> None:
    """An execution_pics override with no clusters also returns 404, even if
    the project itself has PICS configured."""
    project = create_random_project_with_pics(db, config={})
    execution = create_random_test_run_execution(db, project_id=project.id)

    execution.execution_pics = {"clusters": {}}
    db.add(execution)
    db.commit()

    response = client.get(f"{BASE_URL}/{execution.id}/pics_export")

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_pics_export_not_found(client: TestClient) -> None:
    """Returns 404 when the test run execution does not exist."""
    response = client.get(f"{BASE_URL}/999999/pics_export")

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_pics_export_sanitizes_title_in_content_disposition(
    client: TestClient, db: Session
) -> None:
    """A title containing quotes/CR/LF must not break or inject into the
    Content-Disposition header."""
    project = create_random_project_with_pics(db, config={})
    execution = create_random_test_run_execution(
        db, project_id=project.id, title='evil" \r\nX-Injected: true'
    )

    response = client.get(f"{BASE_URL}/{execution.id}/pics_export")

    assert response.status_code == HTTPStatus.OK
    content_disposition = response.headers["content-disposition"]
    assert "\r" not in content_disposition
    assert "\n" not in content_disposition
    assert content_disposition.count('"') == 2
    assert "X-Injected" not in response.headers
