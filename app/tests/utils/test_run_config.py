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
from typing import Any, Dict, Optional

from faker import Faker
from sqlalchemy.orm import Session

from app import crud, models
from app.schemas.test_run_config import TestRunConfigCreate

fake = Faker()


def random_test_run_config_dict(
    name: Optional[str] = None,
    dut_name: Optional[str] = None,
    selected_tests: Optional[Dict[str, Dict[str, Dict[str, int]]]] = None,
) -> dict:
    output = {}

    # Name is not optional,
    if name is None:
        name = fake.text(max_nb_chars=20)
    output["name"] = name

    # DUT Name is not optional,
    if dut_name is None:
        dut_name = fake.text(max_nb_chars=20)
    output["dut_name"] = dut_name

    # Selected Test Cases is not optional,
    if selected_tests is None:
        selected_tests = {}

    output["selected_tests"] = selected_tests

    return output


def create_random_test_run_config(db: Session, **kwargs: Any) -> models.TestRunConfig:
    test_run_config_in = TestRunConfigCreate(**random_test_run_config_dict(**kwargs))
    return crud.test_run_config.create(db, obj_in=test_run_config_in)


test_run_config_base_dict = {
    "name": "test_test_run_config",
    "dut_name": "test_dut_test_run_config",
    "selected_tests": {"SDK YAML Tests": {"FirstChipToolSuite": {"TC-ACE-1.1": 1}}},
    "created_at": "2023-06-27T14:02:56.902898",
}
