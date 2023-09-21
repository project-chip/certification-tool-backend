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
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase, CRUDOperationNotSupported
from app.models.test_run_config import TestRunConfig
from app.schemas.test_run_config import TestRunConfigCreate, TestRunConfigUpdate
from app.test_engine.test_script_manager import test_script_manager


class CRUDTestRunConfig(
    CRUDBase[TestRunConfig, TestRunConfigCreate, TestRunConfigUpdate]
):
    # We overrite the create method, to add validation of valid selected tests
    def create(self, db: Session, *, obj_in: TestRunConfigCreate) -> TestRunConfig:
        test_script_manager.validate_test_selection(obj_in.selected_tests)
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = TestRunConfig(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> TestRunConfig:
        raise CRUDOperationNotSupported("You cannot remove Test Run Config")


test_run_config = CRUDTestRunConfig(TestRunConfig)
