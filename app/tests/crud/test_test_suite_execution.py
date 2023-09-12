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
from app.models import TestSuiteExecution
from app.tests.utils.test_run_execution import create_random_test_run_execution
from app.tests.utils.test_suite_execution import random_test_suite_execution_dict
from app.tests.utils.test_suite_metadata import create_random_test_suite_metadata


def test_get_test_suite_execution(db: Session) -> None:
    # Create required relations for test_suite_execution
    test_suite_metadata = create_random_test_suite_metadata(db)
    test_run_execution = create_random_test_run_execution(db)

    # Create build new test_suite_execution object
    test_suite_execution_dict = random_test_suite_execution_dict(
        public_id=test_suite_metadata.public_id,
        test_suite_metadata_id=test_suite_metadata.id,
        test_run_execution_id=test_run_execution.id,
    )
    test_suite_execution = TestSuiteExecution(**test_suite_execution_dict)

    # Save create test_suite_execution in DB
    test_run_execution.test_suite_executions.append(test_suite_execution)
    db.commit()

    # Load stored test_suite_execution form DB
    stored_test_suite_execution = crud.test_suite_execution.get(
        db=db, id=test_suite_execution.id
    )

    # assert created db values match
    assert stored_test_suite_execution is not None
    assert stored_test_suite_execution.public_id == test_suite_metadata.public_id

    # assert relations
    assert stored_test_suite_execution.test_suite_metadata.id == test_suite_metadata.id
    assert stored_test_suite_execution.test_run_execution.id == test_run_execution.id
