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
from typing import Dict

from sqlalchemy.orm import Session

from app import models
from app.schemas.pics import PICS, PICSCluster
from app.tests.utils.project import create_random_project

test_pics_item1: Dict = {"number": "AB.C", "enabled": True}
test_pics_item2: Dict = {"number": "AB.C.A0004", "enabled": True}
test_pics_item3: Dict = {"number": "XY.C", "enabled": False}
test_pics_item4: Dict = {"number": "AB.S.C0003", "enabled": True}

test_pics_items: Dict = {
    "AB.C": test_pics_item1,
    "AB.C.A0004": test_pics_item2,
    "XY.C": test_pics_item3,
    "AB.S.C0003": test_pics_item4,
}

test_pics_cluster: Dict = {"name": "On/Off", "items": test_pics_items}


def create_random_pics() -> PICS:
    pics = PICS()
    pics.clusters["On/Off"] = PICSCluster(**test_pics_cluster)
    return pics


def create_random_project_with_pics(db: Session) -> models.Project:
    return create_random_project(db=db, pics=create_random_pics())
