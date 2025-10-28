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
from datetime import datetime
from typing import Any, Dict, Optional

from faker import Faker
from sqlalchemy.orm import Session

from app import models
from app.models import TestStateEnum, TestSuiteExecution
from app.tests.utils.test_run_execution import create_random_test_run_execution
from app.tests.utils.test_suite_metadata import create_random_test_suite_metadata
from app.tests.utils.utils import random_lower_string, random_test_public_id

fake = Faker()


def random_test_suite_execution_dict(
    public_id: Optional[str] = None,
    collection_id: Optional[str] = None,
    state: Optional[TestStateEnum] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    test_run_execution_id: Optional[int] = None,
    test_suite_metadata_id: Optional[int] = None,
) -> Dict[str, Any]:
    output: Dict[str, Any] = {}

    # Public id is not optional
    if public_id is None:
        public_id = random_test_public_id()
    output["public_id"] = public_id

    # Collection id is not optional
    if collection_id is None:
        collection_id = random_lower_string()
    output["collection_id"] = collection_id

    # State is optional, include if present
    if state is not None:
        output["state"] = state

    # Started At is optional, include if present
    if started_at is not None:
        output["started_at"] = started_at

    # Completed At is optional, include if present
    if completed_at is not None:
        output["completed_at"] = completed_at

    # test_suite_metadata_id is optional, include if present
    if test_suite_metadata_id is not None:
        output["test_suite_metadata_id"] = test_suite_metadata_id

    # test_run_execution_id is optional, include if present
    if test_run_execution_id is not None:
        output["test_run_execution_id"] = test_run_execution_id

    return output


def create_random_test_suite_execution(db: Session) -> models.TestSuiteExecution:
    # Generate random data for fields
    test_suite_execution_base_dict = random_test_suite_execution_dict()

    # Create parent test_run_execution
    test_run_execution = create_random_test_run_execution(db)

    # Create related metadata
    test_suite_metadata = create_random_test_suite_metadata(db)

    # Create Model
    test_suite_execution = TestSuiteExecution(**test_suite_execution_base_dict)
    db.add(test_suite_execution)

    # Associate metadata
    test_suite_execution.test_suite_metadata = test_suite_metadata

    # Add to Parent run
    test_run_execution.test_suite_executions.append(test_suite_execution)
    db.commit()

    return test_suite_execution
