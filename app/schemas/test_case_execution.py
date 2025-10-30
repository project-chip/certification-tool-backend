#
# Copyright (c) 2025 Project CHIP Authors
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
from typing import List, Optional

from pydantic import BaseModel

from app.models import TestStateEnum

from .test_case_metadata import TestCaseMetadata, TestCaseMetadataBase
from .test_step_execution import TestStepExecution, TestStepExecutionToExport


# Shared properties
class TestCaseExecutionBase(BaseModel):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"
    state: TestStateEnum
    public_id: str
    execution_index: int


# Properties shared by models stored in DB
class TestCaseExecutionInDBBase(TestCaseExecutionBase):
    id: int
    test_suite_execution_id: int
    test_case_metadata_id: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    errors: Optional[List[str]]
    execution_index: int

    class Config:
        orm_mode = True


# Properties to return to client
class TestCaseExecution(TestCaseExecutionInDBBase):
    test_case_metadata: TestCaseMetadata
    test_step_executions: List[TestStepExecution]


# Additional Properties properties stored in DB
class TestCaseExecutionInDB(TestCaseExecutionInDBBase):
    created_at: datetime


# Schema used for Export test case executions
class TestCaseExecutionToExport(TestCaseExecutionBase):
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    errors: Optional[List[str]]
    test_case_metadata: TestCaseMetadataBase
    test_step_executions: List[TestStepExecutionToExport]
    created_at: datetime

    class Config:
        orm_mode = True
