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
from tempfile import SpooledTemporaryFile
from typing import List
from zipfile import ZipFile

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


def mocked_log_rows() -> List[models.TestRunLogEntry]:
    """The same entries as ORM rows, for assigning to TestRunExecution.log.

    `log` is a relationship rather than a JSON column, so it holds mapped
    instances; assigning the pydantic entries straight into it fails in
    SQLAlchemy's backref event with "no attribute '_sa_instance_state'".
    """
    return [models.TestRunLogEntry(**entry.dict()) for entry in mocked_log]


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
    test_run_execution.log = mocked_log_rows()

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


def test_create_grouped_log_zip_file_returns_valid_zip() -> None:
    """create_grouped_log_zip_file() returns a SpooledTemporaryFile (not a
    BytesIO) so peak memory for large log exports is bounded by disk
    spillover instead of holding the whole compressed archive in RAM. Verify
    it's still a valid, readable zip archive despite the type change."""
    test_run_execution = models.TestRunExecution(
        **jsonable_encoder(mocked_test_run_execution)
    )
    test_run_execution.log = mocked_log_rows()

    grouped_logs = log_utils.group_test_run_execution_logs(test_run_execution)
    zip_buffer = log_utils.create_grouped_log_zip_file(grouped_logs=grouped_logs)

    assert isinstance(zip_buffer, SpooledTemporaryFile)

    with ZipFile(zip_buffer) as zf:
        names = zf.namelist()
        assert "summary.txt" in names
        assert "test_suites_setup_and_cleanup.log" in names
        assert f"{TestStateEnum.PASSED}_test_cases.log" in names

    zip_buffer.close()


def test_iter_and_close_streams_and_closes_spooled_temporary_file() -> None:
    """Regression test: iter_and_close() must work with a SpooledTemporaryFile
    specifically (not just a BytesIO), since SpooledTemporaryFile forwards
    read()/seek() via __getattr__ but doesn't implement __iter__/__next__
    itself - passing one directly to StreamingResponse raises "TypeError:
    '...' object is not an iterator"."""
    file_obj = SpooledTemporaryFile(max_size=1024)
    content = b"a" * 10 + b"b" * 10
    file_obj.write(content)
    file_obj.seek(0)

    chunks = list(log_utils.iter_and_close(file_obj, chunk_size=10))

    assert chunks == [b"a" * 10, b"b" * 10]
    assert file_obj.closed
