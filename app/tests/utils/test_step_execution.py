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
from typing import Any, Dict, List, Optional

from faker import Faker

from app.models import TestStateEnum

fake = Faker()


def random_test_step_execution_dict(
    title: Optional[str] = None,
    state: Optional[TestStateEnum] = None,
    errors: Optional[List[str]] = None,
    failures: Optional[List[str]] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    test_case_execution_id: Optional[int] = None,
) -> Dict[str, Any]:
    output = {}

    # Title is not optional,
    if title is None:
        title = fake.text(max_nb_chars=20)
    output["title"] = title

    # State is optional, include if present
    if state is not None:
        output["state"] = state

    # Errors optional
    if errors is not None:
        output["errors"] = errors

    if failures is not None:
        output["failures"] = failures

    # Started At is optional, include if present
    if started_at is not None:
        output["started_at"] = started_at

    # Completed At is optional, include if present
    if completed_at is not None:
        output["completed_at"] = completed_at

    # test_case_execution_id is optional, include if present
    if test_case_execution_id is not None:
        output["test_case_execution_id"] = test_case_execution_id

    return output
