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
import logging
from unittest import mock

import pytest
from sqlalchemy.orm import Session

from app import crud
from app.default_environment_config import default_environment_config
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.tests.utils.project import (
    create_random_project,
    create_random_project_archived,
)
from app.tests.utils.test_run_execution import create_random_test_run_execution
from app.tests.utils.utils import random_lower_string

GENERATED_THREAD_IDENTITY = {
    "panid": "0xabcd",
    "extpanid": "0123456789abcdef",
    "networkkey": "fedcba98765432100123456789abcdef",
    "networkname": "TH-a1b2c3d4e5",
}


def test_create_project(db: Session) -> None:
    name = random_lower_string()
    wifi_ssid = random_lower_string()
    project_in = ProjectCreate(name=name, wifi_ssid=wifi_ssid)

    project_in.config = {}
    project = crud.project.create(db=db, obj_in=project_in)
    assert project.name == name


def test_create_project_no_config_informed(db: Session) -> None:
    name = random_lower_string()
    wifi_ssid = random_lower_string()
    project_in = ProjectCreate(name=name, wifi_ssid=wifi_ssid)
    static_default_config = default_environment_config.dict()  # type: ignore

    with mock.patch(
        "app.crud.crud_project.generate_thread_default_identity",
        return_value=GENERATED_THREAD_IDENTITY,
    ):
        project = crud.project.create(db=db, obj_in=project_in)

    assert project.name == name
    assert project.config["network"]["thread"]["dataset"] == {
        **static_default_config["network"]["thread"]["dataset"],
        **GENERATED_THREAD_IDENTITY,
    }
    assert default_environment_config.dict() == static_default_config  # type: ignore
    assert project_in.config is None


def test_two_new_projects_receive_different_thread_identities(db: Session) -> None:
    second_identity = {
        "panid": "0x4567",
        "extpanid": "fedcba9876543210",
        "networkkey": "0123456789abcdeffedcba9876543210",
        "networkname": "TH-0123456789",
    }

    with mock.patch(
        "app.crud.crud_project.generate_thread_default_identity",
        side_effect=[GENERATED_THREAD_IDENTITY, second_identity],
    ):
        first = crud.project.create(
            db=db, obj_in=ProjectCreate(name=random_lower_string())
        )
        second = crud.project.create(
            db=db, obj_in=ProjectCreate(name=random_lower_string())
        )

    first_dataset = first.config["network"]["thread"]["dataset"]
    second_dataset = second.config["network"]["thread"]["dataset"]
    assert first_dataset["networkkey"] != second_dataset["networkkey"]
    assert first_dataset["extpanid"] != second_dataset["extpanid"]
    assert first_dataset["panid"] != second_dataset["panid"]
    assert first_dataset["networkname"] != second_dataset["networkname"]


def test_explicit_project_config_is_preserved(db: Session) -> None:
    explicit_config = default_environment_config.dict()  # type: ignore

    with mock.patch(
        "app.crud.crud_project.generate_thread_default_identity"
    ) as generate_identity:
        project = crud.project.create(
            db=db,
            obj_in=ProjectCreate(name=random_lower_string(), config=explicit_config),
        )

    generate_identity.assert_not_called()
    assert project.config == explicit_config


def test_generated_network_key_is_not_logged(
    db: Session, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG), mock.patch(
        "app.crud.crud_project.generate_thread_default_identity",
        return_value=GENERATED_THREAD_IDENTITY,
    ):
        crud.project.create(db=db, obj_in=ProjectCreate(name=random_lower_string()))

    assert GENERATED_THREAD_IDENTITY["networkkey"] not in caplog.text


def test_get_project(db: Session) -> None:
    project = create_random_project(db=db, config={})

    stored_project = crud.project.get(db=db, id=project.id)
    assert stored_project
    assert project.id == stored_project.id
    assert project.name == stored_project.name


def test_project_archive(db: Session) -> None:
    project = create_random_project(db=db, config={})
    assert project.archived_at is None

    archived_project = crud.project.archive(db=db, db_obj=project)

    assert archived_project
    assert archived_project.archived_at is not None


def test_project_unarchive(db: Session) -> None:
    archived_project = create_random_project_archived(db, config={})

    assert archived_project
    assert archived_project.archived_at is not None

    unarchived_project = crud.project.unarchive(db=db, db_obj=archived_project)

    assert unarchived_project
    assert unarchived_project.archived_at is None


def test_get_multi_project(db: Session) -> None:
    project1 = create_random_project(db, config={})
    project2 = create_random_project(db, config={})
    project_archived = create_random_project_archived(db, config={})

    # disable skip and limit, do disable default pagination
    projects = crud.project.get_multi(db=db, skip=None, limit=None)
    assert projects

    # project_archived shouldn't be in the list
    assert any(p.id == project1.id for p in projects)
    assert any(p.id == project2.id for p in projects)
    assert not any(p.id == project_archived.id for p in projects)


def test_get_multi_project_archived(db: Session) -> None:
    project1 = create_random_project_archived(db, config={})
    project2 = create_random_project_archived(db, config={})
    project_not_archived = create_random_project(db, config={})

    # disable skip and limit, do disable default pagination
    projects = crud.project.get_multi(db=db, archived=True, skip=None, limit=None)

    # project_not_archived shouldn't be in the list
    assert any(p.id == project1.id for p in projects)
    assert any(p.id == project2.id for p in projects)
    assert not any(p.id == project_not_archived.id for p in projects)


def test_update_project(db: Session) -> None:
    explicit_config = default_environment_config.dict()  # type: ignore
    project = create_random_project(db=db, config=explicit_config)

    new_name = random_lower_string()
    project_update = ProjectUpdate(name=new_name)

    with mock.patch(
        "app.crud.crud_project.generate_thread_default_identity"
    ) as generate_identity:
        updated_project = crud.project.update(
            db=db, db_obj=project, obj_in=project_update
        )
        stored_project = crud.project.get(db=db, id=project.id)

    generate_identity.assert_not_called()
    assert project.id == updated_project.id
    assert updated_project.name == new_name
    assert updated_project.config == explicit_config
    assert stored_project
    assert stored_project.config == explicit_config


def test_delete_project(db: Session) -> None:
    project = create_random_project(db=db, config={})

    project2 = crud.project.remove(db=db, id=project.id)
    assert project2 is not None
    assert project2.id == project.id
    assert project2.name == project.name

    project3 = crud.project.get(db=db, id=project.id)
    assert project3 is None


def test_delete_project_with_nested_test_run(db: Session) -> None:
    test_run = create_random_test_run_execution(db)
    project = test_run.project

    # Make sure DB session doesn't reuse models
    db.expunge(project)

    project2 = crud.project.remove(db=db, id=project.id)
    assert project2 is not None
    assert project2.id == project.id
    assert project2.name == project.name

    project3 = crud.project.get(db=db, id=project.id)
    assert project3 is None

    # Verify that the nested test_run is deleted.
    test_run2 = crud.test_run_execution.get(db=db, id=test_run.id)
    assert test_run2 is None
