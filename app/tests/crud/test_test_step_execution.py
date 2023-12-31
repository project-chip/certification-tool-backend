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

from app import crud
from app.models import TestStepExecution
from app.tests.utils.test_case_execution import create_random_test_case_execution
from app.tests.utils.test_step_execution import random_test_step_execution_dict
from app.tests.utils.utils import random_lower_string


def test_get_test_step_execution(db: Session) -> None:
    # Create required relations for test_step_execution
    test_case_execution = create_random_test_case_execution(db=db)

    # Create build new test_step_execution object
    title = random_lower_string()

    test_step_execution_dict = random_test_step_execution_dict(
        test_case_execution_id=test_case_execution.id,
        title=title,
    )
    test_step_execution = TestStepExecution(**test_step_execution_dict)

    # Save create test_step_execution in DB
    test_case_execution.test_step_executions.append(test_step_execution)
    db.commit()

    # Load stored test_step_execution form DB
    stored_test_step_execution = crud.test_step_execution.get(
        db=db, id=test_step_execution.id
    )

    # assert created db values match
    assert stored_test_step_execution is not None
    assert stored_test_step_execution.title == title

    # assert relations
    assert stored_test_step_execution.test_case_execution.id == test_case_execution.id
