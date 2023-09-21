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
from typing import Optional

from sqlalchemy.orm import Session

from app import crud, models
from app.schemas.pics import PICS
from app.schemas.project import ProjectCreate
from app.tests.utils.utils import random_lower_string


def create_random_project(db: Session, pics: Optional[PICS] = PICS()) -> models.Project:
    name = random_lower_string()
    wifi_ssid = random_lower_string()
    project_in = ProjectCreate(name=name, wifi_ssid=wifi_ssid, pics=pics)
    return crud.project.create(db=db, obj_in=project_in)


def create_random_project_archived(db: Session) -> models.Project:
    project = create_random_project(db=db)
    return crud.project.archive(db=db, db_obj=project)
