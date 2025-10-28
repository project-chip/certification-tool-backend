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
from typing import List, Optional

from pydantic import BaseModel

from app.models import TestStateEnum


# Shared properties
class TestStepExecutionBase(BaseModel):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"
    state: TestStateEnum
    title: str
    execution_index: int


# Properties shared by models stored in DB
class TestStepExecutionInDBBase(TestStepExecutionBase):
    id: int
    test_case_execution_id: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    errors: Optional[List[str]]
    failures: Optional[List[str]]
    execution_index: int

    class Config:
        orm_mode = True


# Properties to return to client
class TestStepExecution(TestStepExecutionInDBBase):
    pass


# Additional Properties properties stored in DB
class TestStepExecutionInDB(TestStepExecutionInDBBase):
    created_at: datetime


# Schema used for Export test step executions
class TestStepExecutionToExport(TestStepExecutionBase):
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    errors: Optional[List[str]]
    failures: Optional[List[str]]
    created_at: datetime

    class Config:
        orm_mode = True
