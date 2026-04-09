#
# Copyright (c) 2023-2026 Project CHIP Authors
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

from pydantic import BaseModel

from app.models import TestStateEnum

from .operator import Operator, OperatorToExport
from .test_run_config import TestRunConfigToExport
from .test_run_log_entry import TestRunLogEntry
from .test_suite_execution import TestSuiteExecution, TestSuiteExecutionToExport


# Special schema for representing stats for a Test Run
class TestRunExecutionStats(BaseModel):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"
    test_case_count: int = 0
    states: dict[TestStateEnum, int] = {}


# Shared properties
class TestRunExecutionBase(BaseModel):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"

    title: str
    description: str | None
    execution_config: dict | None = None
    execution_pics: dict | None = None
    certification_mode: bool = False


# Base + properties that represent relationhips
class TestRunExecutionBaseWithRelationships(TestRunExecutionBase):
    test_run_config_id: int | None
    project_id: int | None


# Properties additional fields on  creation
class TestRunExecutionCreate(TestRunExecutionBaseWithRelationships):
    # TODO(#124): Require project ID when UI supports project management.
    operator_id: int | None


# Properties shared by models stored in DB
class TestRunExecutionInDBBase(TestRunExecutionBaseWithRelationships):
    id: int
    state: TestStateEnum
    started_at: datetime | None
    completed_at: datetime | None
    imported_at: datetime | None
    archived_at: datetime | None

    class Config:
        orm_mode = True


# Properties to return to client
class TestRunExecution(TestRunExecutionInDBBase):
    operator: Operator | None


# Properties to return to client
class TestRunExecutionWithStats(TestRunExecution):
    test_case_stats: TestRunExecutionStats


# Properties to return to client
class TestRunExecutionWithChildren(TestRunExecution):
    test_suite_executions: list[TestSuiteExecution] | None


class TestRunExecutionUpdate(TestRunExecutionBase):
    pass

    class Config:
        orm_mode = True


# Additional Properties properties stored in DB
class TestRunExecutionInDB(TestRunExecutionInDBBase):
    operator_id: int | None
    created_at: datetime
    log: list[TestRunLogEntry]


# Shared properties between export and import schemas
class TestRunExecutionExportImportBase(TestRunExecutionBase):
    state: TestStateEnum
    started_at: datetime | None
    completed_at: datetime | None
    archived_at: datetime | None
    test_suite_executions: list[TestSuiteExecutionToExport] | None
    created_at: datetime
    log: list[TestRunLogEntry]

    class Config:
        orm_mode = True


# Schema used to export test run executions
class TestRunExecutionToExport(TestRunExecutionExportImportBase):
    operator: OperatorToExport | None
    test_run_config: TestRunConfigToExport | None


# Schema used to export test run executions
class ExportedTestRunExecution(BaseModel):
    db_revision: str
    test_run_execution: TestRunExecutionToExport

    class Config:
        orm_mode = True


# Schema used to import test run executions
class TestRunExecutionToImport(TestRunExecutionExportImportBase):
    project_id: int | None
    operator_id: int | None
    imported_at: datetime | None
    test_run_config_id: int | None
