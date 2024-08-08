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
from typing import Dict, List

from pydantic import BaseModel

from app.models.test_enums import TestStateEnum
from app.schemas.test_run_log_entry import TestRunLogEntry


class GroupedTestRunExecutionLogs(BaseModel):
    general: List[TestRunLogEntry] = []
    # test collections logs are indexed by the collections's name
    collections: Dict[str, List[TestRunLogEntry]] = {}
    # test suite logs are indexed by the suite's public_id
    suites: Dict[str, List[TestRunLogEntry]] = {}
    # test case logs are grouped by state and then indexed by the test case's pubic_id
    cases: Dict[TestStateEnum, Dict[str, List[TestRunLogEntry]]] = {}
