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
from sqlalchemy.orm import Session

from app.crud.base import CRUDBaseRead
from app.models.test_step_execution import TestStepExecution
from app.test_engine.models import TestStep


class CRUDTestStepExecution(CRUDBaseRead[TestStepExecution]):
    def update_db_with_received_test_steps(
        self,
        db: Session,
        steps: list[TestStep],
        start_execution_index: int,
        test_case_execution_id: int,
    ) -> None:
        execution_index = start_execution_index
        for step in steps:
            execution = TestStepExecution(
                title=step.name,
                execution_index=execution_index,
                test_case_execution_id=test_case_execution_id,
            )
            step.test_step_execution = execution
            execution_index += 1
            db.add(execution)

        db.commit()


test_step_execution = CRUDTestStepExecution(TestStepExecution)
