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

default_config = {
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
        "chip_use_paa_certs": False,
        "trace_log": True,
    },
    "test_parameters": None,
}


def create_random_project(
    db: Session, config: dict, pics: Optional[PICS] = PICS()
) -> models.Project:
    name = random_lower_string()
    wifi_ssid = random_lower_string()
    project_in = ProjectCreate(name=name, wifi_ssid=wifi_ssid, pics=pics)
    project_in.config = config

    return crud.project.create(db=db, obj_in=project_in)


def create_random_project_archived(db: Session, config: dict) -> models.Project:
    project = create_random_project(db=db, config=config)
    return crud.project.archive(db=db, db_obj=project)
