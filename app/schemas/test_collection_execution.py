#
# Copyright (c) 2024 Project CHIP Authors
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

from app.models.test_enums import TestStateEnum

from .test_collection_metadata import TestCollectionMetadata, TestCollectionMetadataBase
from .test_suite_execution import TestSuiteExecution, TestSuiteExecutionToExport


# Shared properties
class TestCollectionExecutionBase(BaseModel):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"
    state: TestStateEnum
    name: str
    execution_index: int
    mandatory: bool = False


# Properties shared by models stored in DB
class TestCollectionExecutionInDBBase(TestCollectionExecutionBase):
    id: int
    test_run_execution_id: int
    test_collection_metadata_id: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    errors: Optional[List[str]]

    class Config:
        orm_mode = True


# Properties to return to client
class TestCollectionExecution(TestCollectionExecutionInDBBase):
    test_suite_executions: List[TestSuiteExecution]
    test_collection_metadata: TestCollectionMetadata


# Additional Properties properties stored in DB
class TestCollectionExecutionInDB(TestCollectionExecutionInDBBase):
    created_at: datetime


# Schema used for Export test collection executions
class TestCollectionExecutionToExport(TestCollectionExecutionBase):
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    errors: Optional[List[str]]
    test_suite_executions: List[TestSuiteExecutionToExport]
    test_collection_metadata: TestCollectionMetadataBase
    created_at: datetime

    class Config:
        orm_mode = True
