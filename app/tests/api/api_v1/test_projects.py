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
# flake8: noqa
# Ignore flake8 check for this file
import json
from http import HTTPStatus
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core.config import settings
from app.default_environment_config import default_environment_config
from app.tests.utils.project import (
    create_random_project,
    create_random_project_archived,
)
from app.tests.utils.test_pics_data import create_random_project_with_pics
from app.tests.utils.validate_json_response import validate_json_response

invalid_dut_config = {
    "name": "foo",
    "config": {
        "network": {
            "fabric_id": "0",
            "thread": {
                "dataset": {
                    "channel": "15",
                    "panid": "0x1234",
                    "extpanid": "1111111122222222",
                    "networkkey": "00112233445566778899aabbccddeeff",
                    "networkname": "DEMO",
                },
                "rcp_serial_path": "/dev/ttyACM0",
                "rcp_baudrate": 115200,
                "on_mesh_prefix": "fd11:22::/64",
                "network_interface": "eth0",
            },
            "wifi": {"ssid": "testharness", "password": "wifi-password"},
        },
        "dut_config": {
            "pairing_mode": "onnetwork",
            "setup_code": "20202021",
            "discriminator": "3840",
            "chip_use_paa_certs": "false",
            "invalid_arg": "any value",
        },
    },
}

project_json_data = {
    "name": "New Project IMPORTED",
    "config": {
        "test_parameters": None,
        "network": {
            "wifi": {"ssid": "testharness", "password": "wifi-password"},
            "thread": {
                "rcp_serial_path": "/dev/ttyACM0",
                "rcp_baudrate": 115200,
                "on_mesh_prefix": "fd11:22::/64",
                "network_interface": "eth0",
                "dataset": {
                    "channel": "15",
                    "panid": "0x1234",
                    "extpanid": "1111111122222222",
                    "networkkey": "00112233445566778899aabbccddeeff",
                    "networkname": "DEMO",
                },
                "otbr_docker_image": None,
            },
        },
        "dut_config": {
            "discriminator": "3840",
            "setup_code": "20202021",
            "pairing_mode": "onnetwork",
            "chip_timeout": None,
            "chip_use_paa_certs": False,
            "trace_log": True,
        },
    },
    "pics": {
        "clusters": {
            "Access Control cluster": {
                "name": "Test PICS",
                "items": {
                    "ACL.S": {"number": "PICS.S", "enabled": False},
                    "ACL.C": {"number": "PICS.C", "enabled": True},
                },
            }
        }
    },
}


def test_create_project_default_config(client: TestClient) -> None:
    data: dict[str, Any] = {"name": "Foo"}
    response = client.post(
        f"{settings.API_V1_STR}/projects/",
        json=data,
    )

    expected_data = data
    expected_data["config"] = default_environment_config

    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_content=expected_data,
        expected_keys=["id", "created_at", "updated_at", "config"],
    )


def test_create_project_custom_config(client: TestClient) -> None:
    custom_config = default_environment_config.copy(deep=True)  # type: ignore
    data: dict[str, Any] = {"name": "Foo", "config": custom_config.dict()}
    response = client.post(
        f"{settings.API_V1_STR}/projects/",
        json=data,
    )

    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_content=data,
        expected_keys=["id", "created_at", "updated_at", "config"],
    )


def test_create_project_invalid_dut_config(client: TestClient) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/projects/",
        json=invalid_dut_config,
    )

    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        expected_content={
            "detail": "The informed configuration has one or more invalid properties. "
            "Exception message: The field invalid_arg is not a valid dut_config "
            "configuration: ['discriminator', 'setup_code', 'pairing_mode', "
            "'chip_timeout', 'chip_use_paa_certs', 'trace_log']"
        },
        expected_keys=["detail"],
    )


def test_default_project_config(client: TestClient) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/projects/default_config",
    )

    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_content=default_environment_config.dict(),  # type: ignore
    )


def test_read_project(client: TestClient, db: Session) -> None:
    project = create_random_project(db, config={})
    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.id}",
    )

    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_content={
            "id": project.id,
            "name": project.name,
        },
        expected_keys=["created_at", "updated_at"],
    )


def test_read_multiple_project(client: TestClient, db: Session) -> None:
    project1 = create_random_project(db, config={})
    project2 = create_random_project(db, config={})
    limit = db.scalar(select(func.count(models.Project.id))) or 0
    response = client.get(
        f"{settings.API_V1_STR}/projects?limit={limit}",
    )
    assert response.status_code == HTTPStatus.OK
    content = response.json()
    assert isinstance(content, list)
    assert any(project.get("id") == project1.id for project in content)
    assert any(project.get("id") == project2.id for project in content)


def test_read_multiple_project_by_archived(client: TestClient, db: Session) -> None:
    archived = create_random_project_archived(db, config={})
    limit = db.scalar(select(func.count(models.Project.id))) or 0

    response = client.get(
        f"{settings.API_V1_STR}/projects?limit={limit}",
    )
    assert response.status_code == HTTPStatus.OK
    content = response.json()
    assert isinstance(content, list)
    assert not any(project.get("id") == archived.id for project in content)

    response = client.get(
        f"{settings.API_V1_STR}/projects?limit={limit}&archived=true",
    )
    assert response.status_code == HTTPStatus.OK
    content = response.json()
    assert isinstance(content, list)
    assert any(project.get("id") == archived.id for project in content)


def test_update_project(client: TestClient, db: Session) -> None:
    project = create_random_project(db, config={})
    data = jsonable_encoder(project)
    data["name"] = "Updated Name"

    response = client.put(
        f"{settings.API_V1_STR}/projects/{project.id}",
        json=data,
    )

    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_content={
            "id": project.id,
            "name": data["name"],
        },
    )


def test_update_project_invalid_dut_config(client: TestClient, db: Session) -> None:
    project = create_random_project(db, config={})
    response = client.put(
        f"{settings.API_V1_STR}/projects/{project.id}",
        json=invalid_dut_config,
    )

    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        expected_content={
            "detail": "The informed configuration has one or more invalid properties. "
            "Exception message: The field invalid_arg is not a valid dut_config "
            "configuration: ['discriminator', 'setup_code', 'pairing_mode', "
            "'chip_timeout', 'chip_use_paa_certs', 'trace_log']"
        },
        expected_keys=["detail"],
    )


def test_delete_project(client: TestClient, db: Session) -> None:
    project = create_random_project(db, config={})
    response = client.delete(f"{settings.API_V1_STR}/projects/{project.id}")
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_content={
            "id": project.id,
            "name": project.name,
        },
    )


def test_archive_project(client: TestClient, db: Session) -> None:
    project = create_random_project(db, config={})
    response = client.post(f"{settings.API_V1_STR}/projects/{project.id}/archive")
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_content={
            "id": project.id,
            "name": project.name,
        },
        expected_keys=["archived_at"],
    )


def test_unarchive_project(client: TestClient, db: Session) -> None:
    project = create_random_project(db, config={})
    response = client.post(f"{settings.API_V1_STR}/projects/{project.id}/unarchive")
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_content={
            "id": project.id,
            "name": project.name,
            "archived_at": None,
        },
    )


def test_operations_missing_test_run(client: TestClient, db: Session) -> None:
    """Test HTTP errors when attempting operations on an invalid record id.

    Will create and delete a project, to ensure the id is invalid."""
    test_run = create_random_project(db, config={})
    id = test_run.id
    crud.project.remove(db=db, id=id)

    # Get
    response = client.get(f"{settings.API_V1_STR}/projects/{id}")
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.NOT_FOUND,
        expected_keys=["detail"],
    )

    # Update
    response = client.put(
        f"{settings.API_V1_STR}/projects/{id}",
        json={"name": "Updated Name"},
    )
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.NOT_FOUND,
        expected_keys=["detail"],
    )

    # Delete
    response = client.delete(f"{settings.API_V1_STR}/projects/{id}")
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.NOT_FOUND,
        expected_keys=["detail"],
    )

    # Archive
    response = client.post(f"{settings.API_V1_STR}/projects/{id}/archive")
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.NOT_FOUND,
        expected_keys=["detail"],
    )

    # Unarchive
    response = client.post(f"{settings.API_V1_STR}/projects/{id}/unarchive")
    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.NOT_FOUND,
        expected_keys=["detail"],
    )


def test_upload_pics(client: TestClient, db: Session) -> None:
    project = create_random_project(db, config={})
    pics_file = Path(__file__).parent.parent.parent / "utils" / "test_pics.xml"
    upload_files = {"file": pics_file.read_text()}
    response = client.put(
        f"{settings.API_V1_STR}/projects/{project.id}/upload_pics",
        files=upload_files,
    )

    content = response.json()
    assert content["pics"] is not None


def test_pics_cluster_type(client: TestClient, db: Session) -> None:
    project = create_random_project_with_pics(db=db, config={})

    cluster_name = "On/Off"
    pics_cluster_type_url = (
        f"{settings.API_V1_STR}/projects/{project.id}/pics_cluster_type"
        f"?cluster_name={cluster_name}"
    )

    response = client.delete(pics_cluster_type_url)

    content = response.json()
    assert content["pics"] is not None
    assert len(content["pics"]["clusters"]) == 0


def test_applicable_test_cases(client: TestClient, db: Session) -> None:
    project = create_random_project_with_pics(db=db, config={})
    # retrieve applicable test cases
    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.id}/applicable_test_cases",
    )

    content = response.json()
    assert content["test_cases"] is not None
    assert len(content["test_cases"]) > 0
    assert "TC_Pics (Test)" in content["test_cases"]


def test_applicable_test_cases_empty_pics(client: TestClient, db: Session) -> None:
    project = create_random_project(db, config={})

    # retrieve applicable test cases
    response2 = client.get(
        f"{settings.API_V1_STR}/projects/{project.id}/applicable_test_cases",
    )

    content = response2.json()
    assert content["test_cases"] is not None
    # the project is created with empty pics
    # expected value: applicable_test_cases == 0
    assert len(content["test_cases"]) == 0


def test_export_project(client: TestClient, db: Session) -> None:
    project = create_random_project_with_pics(db=db, config={})
    project_create_schema = schemas.ProjectCreate(**project.__dict__)
    # retrieve the project config
    response = client.get(
        f"{settings.API_V1_STR}/projects/{project.id}/export",
    )

    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_content=jsonable_encoder(project_create_schema),
    )


def test_import_project(client: TestClient, db: Session) -> None:
    imported_file_content = json.dumps(project_json_data).encode("utf-8")
    data = BytesIO(imported_file_content)

    files = {
        "import_file": (
            "project.json",
            data,
            "multipart/form-data",
        )
    }

    response = client.post(f"{settings.API_V1_STR}/projects/import", files=files)

    validate_json_response(
        response=response,
        expected_status_code=HTTPStatus.OK,
        expected_content=project_json_data,
    )
