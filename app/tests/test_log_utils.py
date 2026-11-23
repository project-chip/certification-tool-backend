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
import json
import secrets
from io import BytesIO
from typing import Any, Dict, Iterator, List, Optional
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app import log_utils, models, schemas
from app.models import TestStateEnum
from app.schemas import TestRunLogEntry
from app.tests.utils.project import create_random_project
from app.tests.utils.test_run_execution import (
    create_test_run_execution_with_some_test_cases,
)

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
                    execution_index=3,
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


def _log_entry(
    message: str, suite: Optional[int] = None, case: Optional[int] = None
) -> models.TestRunLogEntry:
    return models.TestRunLogEntry(
        level="INFO",
        timestamp=1684878223.0,
        message=message,
        test_suite_execution_index=suite,
        test_case_execution_index=case,
        test_step_execution_index=None,
    )


def _messages(text: str) -> list[str]:
    """Strip the level/timestamp prefix from each formatted line, keeping
    section headers as-is."""
    return [line.split(" | ")[-1] for line in text.splitlines()]


def _section(title: str) -> str:
    return log_utils.LOG_SECTION_TEMPLATE.format(title).rstrip("\n")


def _grouped_zip(db: Session, run: models.TestRunExecution) -> ZipFile:
    plan = log_utils.plan_grouped_log(db=db, test_run_execution=run)
    content = b"".join(
        log_utils.stream_zip(
            lambda zip_file: log_utils.write_grouped_log_entries(
                zip_file=zip_file, db=db, run_id=run.id, plan=plan
            )
        )
    )
    return ZipFile(BytesIO(content))


# Foreign keys and primary keys in mocked_test_run_execution, which the
# database assigns when the run is saved.
_DB_ASSIGNED_KEYS = {
    "id",
    "operator_id",
    "project_id",
    "test_run_execution_id",
    "test_suite_execution_id",
    "test_case_execution_id",
    "test_suite_metadata_id",
    "test_case_metadata_id",
}


def _without_db_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_db_keys(item)
            for key, item in value.items()
            if key not in _DB_ASSIGNED_KEYS
        }
    if isinstance(value, list):
        return [_without_db_keys(item) for item in value]
    return value


def _create_mocked_run(db: Session) -> models.TestRunExecution:
    """Save mocked_test_run_execution and mocked_log to the database."""
    run = models.TestRunExecution(
        **_without_db_keys(jsonable_encoder(mocked_test_run_execution))
    )
    run.project_id = create_random_project(db, config={}).id
    for row in mocked_log_rows():
        run.log.append(row)
    db.add(run)
    db.commit()
    return run


def _sections(text: str) -> Dict[str, List[str]]:
    """Split a grouped log file into its sections, keyed by section title,
    each holding its lines' messages."""
    sections: Dict[str, List[str]] = {}
    current: List[str] = []
    for line in text.splitlines():
        if line.startswith("-" * 21 + " "):
            current = sections.setdefault(line.strip("- "), [])
        else:
            current.append(line.split(" | ")[-1])
    return sections


def test_chunk_text_groups_parts_into_chunks() -> None:
    chunks = list(log_utils.chunk_text(["aaaa", "bbbb", "cc", "é"], chunk_size=6))

    assert chunks == [b"aaaabbbb", "ccé".encode()]


def test_chunk_text_yields_nothing_for_no_parts() -> None:
    assert list(log_utils.chunk_text([])) == []


def test_stream_zip_yields_a_valid_zip_in_chunks() -> None:
    lines = [f"line {i} {secrets.token_hex(32)}\n" for i in range(2000)]

    def write_entries(zip_file: ZipFile) -> Iterator[None]:
        yield from log_utils.write_zip_entry(zip_file, "a.log", lines)
        yield from log_utils.write_zip_entry(zip_file, "b.bin", [b"\x00\x01"])

    chunks = list(log_utils.stream_zip(write_entries, chunk_size=1024))

    # Bytes are produced while entries are written, not only at the end.
    assert len(chunks) > 2
    with ZipFile(BytesIO(b"".join(chunks))) as zf:
        assert zf.testzip() is None
        assert all(info.compress_type == ZIP_DEFLATED for info in zf.infolist())
        assert zf.read("a.log").decode() == "".join(lines)
        assert zf.read("b.bin") == b"\x00\x01"


def test_write_grouped_log_entries(db: Session) -> None:
    run = _create_mocked_run(db)

    with _grouped_zip(db=db, run=run) as zf:
        assert zf.namelist() == [
            "summary.txt",
            "test_suites_setup_and_cleanup.log",
            f"{TestStateEnum.PASSED}_test_cases.log",
            f"{TestStateEnum.ERROR}_test_cases.log",
            f"{TestStateEnum.FAILED}_test_cases.log",
            f"{TestStateEnum.NOT_APPLICABLE}_test_cases.log",
        ]

        assert zf.read("summary.txt").decode().splitlines() == [
            _section(f'"{TestStateEnum.PASSED}" test cases (2/5)'),
            "TC-X-1.1",
            "TC-Y-1.3",
            _section(f'"{TestStateEnum.ERROR}" test cases (1/5)'),
            "TC-Y-1.1",
            _section(f'"{TestStateEnum.FAILED}" test cases (1/5)'),
            "TC-Y-1.2",
            _section(f'"{TestStateEnum.NOT_APPLICABLE}" test cases (1/5)'),
            "TC-Y-1.4",
        ]

        general = ["General log 0", "General log 1", "General log 2", "General log 3"]

        def sizes(name: str) -> Dict[str, int]:
            sections = _sections(zf.read(name).decode())
            assert sections["Test run general logs"] == general
            return {title: len(lines) for title, lines in sections.items()}

        assert sizes("test_suites_setup_and_cleanup.log") == {
            "Test run general logs": 4,
            "Suite0 logs": 4,
            "Suite1 logs": 3,
        }
        assert sizes(f"{TestStateEnum.PASSED}_test_cases.log") == {
            "Test run general logs": 4,
            "TC-X-1.1 logs": 5,
            "TC-Y-1.3 logs": 1,
        }
        assert sizes(f"{TestStateEnum.ERROR}_test_cases.log") == {
            "Test run general logs": 4,
            "TC-Y-1.1 logs": 5,
        }
        assert sizes(f"{TestStateEnum.FAILED}_test_cases.log") == {
            "Test run general logs": 4,
            "TC-Y-1.2 logs": 3,
        }
        assert sizes(f"{TestStateEnum.NOT_APPLICABLE}_test_cases.log") == {
            "Test run general logs": 4,
            "TC-Y-1.4 logs": 2,
        }

        # Entries keep their log order within a section, step logs included.
        assert _sections(zf.read(f"{TestStateEnum.PASSED}_test_cases.log").decode())[
            "TC-X-1.1 logs"
        ] == [
            "Test suite 0 case 0 log 0",
            "Test suite 0 case 0 log 1",
            "Test suite 0 case 0 step 0 log 0",
            "Test suite 0 case 0 step 1 log 0",
            "Test suite 0 case 0 log 2",
        ]


def test_grouped_log_zip_is_valid_and_compressed(db: Session) -> None:
    run = _create_mocked_run(db)

    with _grouped_zip(db=db, run=run) as zf:
        assert zf.testzip() is None
        assert all(info.compress_type == ZIP_DEFLATED for info in zf.infolist())


def test_write_grouped_log_entries_without_test_case_logs(db: Session) -> None:
    run = create_test_run_execution_with_some_test_cases(db=db)
    run.log.append(_log_entry("general 0"))
    db.commit()

    with _grouped_zip(db=db, run=run) as zf:
        assert sorted(zf.namelist()) == [
            "summary.txt",
            "test_suites_setup_and_cleanup.log",
        ]
        assert zf.read("summary.txt").decode() == "No test case has been executed"
        assert _messages(zf.read("test_suites_setup_and_cleanup.log").decode()) == [
            _section("Test run general logs"),
            "general 0",
        ]


def test_plan_grouped_log_raises_for_unknown_test_case(db: Session) -> None:
    run = create_test_run_execution_with_some_test_cases(db=db)
    case_count = len(run.test_suite_executions[0].test_case_executions)
    run.log.append(_log_entry("orphan", suite=0, case=case_count))
    db.commit()

    with pytest.raises(IndexError):
        log_utils.plan_grouped_log(db=db, test_run_execution=run)


def test_format_log_line() -> None:
    entry = _log_entry("hello")

    assert log_utils.format_log_line(entry, json_entries=False).endswith(" | hello\n")
    assert json.loads(log_utils.format_log_line(entry, json_entries=True)) == (
        json.loads(schemas.TestRunLogEntry.from_orm(entry).json())
    )
