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
from typing import List

from fastapi.encoders import jsonable_encoder

from app import log_utils, models, schemas
from app.models import TestStateEnum
from app.schemas import TestRunLogEntry

mocked_log: List[TestRunLogEntry] = [
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878223.0,
        message="General log 0",
        test_suite_execution_index=None,
        test_case_execution_index=None,
        test_step_execution_index=None,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878224.0,
        message="General log 1",
        test_suite_execution_index=None,
        test_case_execution_index=None,
        test_step_execution_index=None,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878225.0,
        message="General log 2",
        test_suite_execution_index=None,
        test_case_execution_index=None,
        test_step_execution_index=None,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878226.0,
        message="Test suite 0 log 0",
        test_suite_execution_index=0,
        test_case_execution_index=None,
        test_step_execution_index=None,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878227.0,
        message="Test suite 0 log 1",
        test_suite_execution_index=0,
        test_case_execution_index=None,
        test_step_execution_index=None,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878228.0,
        message="Test suite 0 log 2",
        test_suite_execution_index=0,
        test_case_execution_index=None,
        test_step_execution_index=None,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878229.0,
        message="Test suite 0 case 0 log 0",
        test_suite_execution_index=0,
        test_case_execution_index=0,
        test_step_execution_index=None,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878230.0,
        message="Test suite 0 case 0 log 1",
        test_suite_execution_index=0,
        test_case_execution_index=0,
        test_step_execution_index=None,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878231.0,
        message="Test suite 0 case 0 step 0 log 0",
        test_suite_execution_index=0,
        test_case_execution_index=0,
        test_step_execution_index=0,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878232.0,
        message="Test suite 0 case 0 step 1 log 0",
        test_suite_execution_index=0,
        test_case_execution_index=0,
        test_step_execution_index=1,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878233.0,
        message="Test suite 0 case 0 log 2",
        test_suite_execution_index=0,
        test_case_execution_index=0,
        test_step_execution_index=None,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878234.0,
        message="Test suite 0 log 3",
        test_suite_execution_index=0,
        test_case_execution_index=None,
        test_step_execution_index=None,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878235.0,
        message="Test suite 1 log 0",
        test_suite_execution_index=1,
        test_case_execution_index=None,
        test_step_execution_index=None,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878236.0,
        message="Test suite 1 log 1",
        test_suite_execution_index=1,
        test_case_execution_index=None,
        test_step_execution_index=None,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878237.0,
        message="Test suite 1 case 0 log 0",
        test_suite_execution_index=1,
        test_case_execution_index=0,
        test_step_execution_index=None,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878238.0,
        message="Test suite 1 case 0 log 1",
        test_suite_execution_index=1,
        test_case_execution_index=0,
        test_step_execution_index=None,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878239.0,
        message="Test suite 1 case 0 step 0 log 0",
        test_suite_execution_index=1,
        test_case_execution_index=0,
        test_step_execution_index=0,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878240.0,
        message="Test suite 1 case 0 step 1 log 0",
        test_suite_execution_index=1,
        test_case_execution_index=0,
        test_step_execution_index=1,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878241.0,
        message="Test suite 1 case 0 log 2",
        test_suite_execution_index=1,
        test_case_execution_index=0,
        test_step_execution_index=None,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878229.0,
        message="Test suite 1 case 1 log 0",
        test_suite_execution_index=1,
        test_case_execution_index=1,
        test_step_execution_index=None,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878242.0,
        message="Test suite 1 case 1 step 0 log 0",
        test_suite_execution_index=1,
        test_case_execution_index=1,
        test_step_execution_index=0,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878243.0,
        message="Test suite 1 case 1 step 0 log 1",
        test_suite_execution_index=1,
        test_case_execution_index=1,
        test_step_execution_index=0,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878244.0,
        message="Test suite 1 case 2 log 0",
        test_suite_execution_index=1,
        test_case_execution_index=2,
        test_step_execution_index=None,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878254.0,
        message="Test suite 1 case 3 log 0",
        test_suite_execution_index=1,
        test_case_execution_index=3,
        test_step_execution_index=None,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878255.0,
        message="Test suite 1 case 3 step 0 log 0",
        test_suite_execution_index=1,
        test_case_execution_index=3,
        test_step_execution_index=0,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878265.0,
        message="Test suite 1 log 2",
        test_suite_execution_index=1,
        test_case_execution_index=None,
        test_step_execution_index=None,
    ),
    TestRunLogEntry(
        level="INFO",
        timestamp=1684878276.0,
        message="General log 3",
        test_suite_execution_index=None,
        test_case_execution_index=None,
        test_step_execution_index=None,
    ),
]

mocked_test_run_execution = schemas.TestRunExecutionWithChildren(
    title="Mocked test run",
    id=1,
    state=TestStateEnum.ERROR,
    operator=schemas.Operator(name="John Doe", id=1),
    test_suite_executions=[
        schemas.TestSuiteExecution(
            state=TestStateEnum.PASSED,
            public_id="Suite0",
            execution_index=0,
            collection_id="Collection0",
            id=1,
            test_run_execution_id=1,
            test_suite_metadata_id=1,
            test_case_executions=[
                schemas.TestCaseExecution(
                    state=TestStateEnum.PASSED,
                    public_id="TC-X-1.1",
                    execution_index=0,
                    id=1,
                    test_suite_execution_id=1,
                    test_case_metadata_id=1,
                    test_case_metadata=schemas.TestCaseMetadata(
                        public_id="TC-X-1.1",
                        title="[TC-X-1.1] Title",
                        description="First test case",
                        version="1.0",
                        source_hash="abc123",
                        id=1,
                    ),
                    test_step_executions=[
                        schemas.TestStepExecution(
                            state=TestStateEnum.PASSED,
                            title="First step",
                            execution_index=0,
                            id=1,
                            test_case_execution_id=1,
                        ),
                        schemas.TestStepExecution(
                            state=TestStateEnum.PASSED,
                            title="Second step",
                            execution_index=1,
                            id=2,
                            test_case_execution_id=1,
                        ),
                    ],
                )
            ],
            test_suite_metadata=schemas.TestSuiteMetadata(
                public_id="Suite0",
                title="Suite 0",
                description="First suite",
                version="1.0",
                source_hash="abc123",
                id=1,
            ),
        ),
        schemas.TestSuiteExecution(
            state=TestStateEnum.ERROR,
            public_id="Suite1",
            execution_index=1,
            collection_id="Collection0",
            id=2,
            test_run_execution_id=1,
            test_suite_metadata_id=2,
            test_case_executions=[
                schemas.TestCaseExecution(
                    state=TestStateEnum.ERROR,
                    public_id="TC-Y-1.1",
                    execution_index=0,
                    id=2,
                    test_suite_execution_id=2,
                    test_case_metadata_id=2,
                    test_case_metadata=schemas.TestCaseMetadata(
                        public_id="TC-Y-1.1",
                        title="[TC-Y-1.1] Title",
                        description="First test case",
                        version="1.0",
                        source_hash="abc123",
                        id=2,
                    ),
                    test_step_executions=[
                        schemas.TestStepExecution(
                            state=TestStateEnum.PASSED,
                            title="First step",
                            execution_index=0,
                            id=3,
                            test_case_execution_id=2,
                        ),
                        schemas.TestStepExecution(
                            state=TestStateEnum.ERROR,
                            title="Second step",
                            execution_index=1,
                            id=4,
                            test_case_execution_id=2,
                            errors=["error"],
                        ),
                    ],
                ),
                schemas.TestCaseExecution(
                    state=TestStateEnum.FAILED,
                    public_id="TC-Y-1.2",
                    execution_index=1,
                    id=3,
                    test_suite_execution_id=2,
                    test_case_metadata_id=3,
                    test_case_metadata=schemas.TestCaseMetadata(
                        public_id="TC-Y-1.2",
                        title="[TC-Y-1.2] Title",
                        description="Second test case",
                        version="1.0",
                        source_hash="abc123",
                        id=3,
                    ),
                    test_step_executions=[
                        schemas.TestStepExecution(
                            state=TestStateEnum.FAILED,
                            title="First step",
                            execution_index=0,
                            id=5,
                            test_case_execution_id=3,
                            failures=["failure"],
                        )
                    ],
                ),
                schemas.TestCaseExecution(
                    state=TestStateEnum.PASSED,
                    public_id="TC-Y-1.3",
                    execution_index=2,
                    id=4,
                    test_suite_execution_id=2,
                    test_case_metadata_id=4,
                    test_case_metadata=schemas.TestCaseMetadata(
                        public_id="TC-Y-1.3",
                        title="[TC-Y-1.3] Title",
                        description="Third test case",
                        version="1.0",
                        source_hash="abc123",
                        id=4,
                    ),
                    test_step_executions=[],
                ),
                schemas.TestCaseExecution(
                    state=TestStateEnum.NOT_APPLICABLE,
                    public_id="TC-Y-1.4",
                    execution_index=1,
                    id=5,
                    test_suite_execution_id=2,
                    test_case_metadata_id=5,
                    test_case_metadata=schemas.TestCaseMetadata(
                        public_id="TC-Y-1.4",
                        title="[TC-Y-1.4] Title",
                        description="Fourth test case",
                        version="1.0",
                        source_hash="abc123",
                        id=5,
                    ),
                    test_step_executions=[
                        schemas.TestStepExecution(
                            state=TestStateEnum.PASSED,
                            title="First step",
                            execution_index=0,
                            id=5,
                            test_case_execution_id=5,
                        )
                    ],
                ),
            ],
            test_suite_metadata=schemas.TestSuiteMetadata(
                public_id="Suite1",
                title="Suite 1",
                description="Second suite",
                version="1.0",
                source_hash="abc123",
                id=2,
            ),
        ),
    ],
)


def test_group_test_run_execution_logs() -> None:
    test_run_execution = models.TestRunExecution(
        **jsonable_encoder(mocked_test_run_execution)
    )
    test_run_execution.log = mocked_log

    grouped_logs = log_utils.group_test_run_execution_logs(test_run_execution)

    assert len(grouped_logs.general) == 4
    assert len(grouped_logs.suites) == 2
    assert len(grouped_logs.suites["Suite0"]) == 4
    assert len(grouped_logs.suites["Suite1"]) == 3
    assert len(grouped_logs.cases) == 4
    assert len(grouped_logs.cases[TestStateEnum.PASSED]) == 2
    assert len(grouped_logs.cases[TestStateEnum.ERROR]) == 1
    assert len(grouped_logs.cases[TestStateEnum.FAILED]) == 1
    assert len(grouped_logs.cases[TestStateEnum.NOT_APPLICABLE]) == 1
    assert len(grouped_logs.cases[TestStateEnum.PASSED]["TC-X-1.1"]) == 5
    assert len(grouped_logs.cases[TestStateEnum.PASSED]["TC-Y-1.3"]) == 1
    assert len(grouped_logs.cases[TestStateEnum.ERROR]["TC-Y-1.1"]) == 5
    assert len(grouped_logs.cases[TestStateEnum.FAILED]["TC-Y-1.2"]) == 3
    assert len(grouped_logs.cases[TestStateEnum.NOT_APPLICABLE]["TC-Y-1.4"]) == 2
