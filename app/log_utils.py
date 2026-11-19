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
import io
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from itertools import chain
from typing import (
    IO,
    Any,
    Callable,
    Dict,
    Generator,
    Iterable,
    Iterator,
    List,
    Mapping,
    Tuple,
    Union,
    cast,
)
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import tuple_
from sqlalchemy.orm import Session

from app import crud, models, schemas

LOG_SECTION_TEMPLATE = "--------------------- {} ---------------------\n"

# Size of the byte chunks handed to StreamingResponse.
STREAM_CHUNK_SIZE = 64 * 1024

# Log entries reach the formatting helpers either as rows read from the
# testrunlogentry table or as the pydantic entries that the test engine deals
# in. Both expose level/timestamp/message.
LogEntry = Union[schemas.TestRunLogEntry, models.TestRunLogEntry]


def format_log_line(log_line: LogEntry, json_entries: bool) -> str:
    """Format one log entry as a newline-terminated line, either as JSON or as
    `level | timestamp | message`."""
    if json_entries:
        # Via the schema rather than log_line.json(), so that either a
        # pydantic entry or a TestRunLogEntry row can be formatted; the
        # rows have no .json().
        return schemas.TestRunLogEntry.from_orm(log_line).json() + "\n"
    timestamp = datetime.fromtimestamp(log_line.timestamp).strftime(
        "%Y-%m-%d %H:%M:%S.%f"
    )
    return f"{log_line.level:10} | {timestamp} | {log_line.message}\n"


def log_generator(log_entries: Iterable[LogEntry], json_entries: bool) -> Generator:
    for log_line in log_entries:
        yield format_log_line(log_line, json_entries=json_entries)


def chunk_text(
    parts: Iterable[str], chunk_size: int = STREAM_CHUNK_SIZE
) -> Iterator[bytes]:
    """Encode text parts as UTF-8 and regroup them into chunks of roughly
    `chunk_size` bytes."""
    buffer: List[bytes] = []
    size = 0
    for part in parts:
        data = part.encode()
        buffer.append(data)
        size += len(data)
        if size >= chunk_size:
            yield b"".join(buffer)
            buffer = []
            size = 0
    if buffer:
        yield b"".join(buffer)


class _ZipStreamSink(io.RawIOBase):
    """Non-seekable file object that collects the bytes ZipFile writes until
    they are drained.

    Because it can't seek, ZipFile writes each entry's sizes and CRC in a data
    descriptor after the entry instead of going back to patch its header.
    """

    def __init__(self) -> None:
        super().__init__()
        self._chunks: List[bytes] = []
        self.size = 0

    def writable(self) -> bool:
        return True

    def write(self, data: bytes) -> int:  # type: ignore[override]
        self._chunks.append(bytes(data))
        self.size += len(data)
        return len(data)

    def drain(self) -> bytes:
        data = b"".join(self._chunks)
        self._chunks = []
        self.size = 0
        return data


def stream_zip(
    write_entries: Callable[[ZipFile], Iterator[None]],
    chunk_size: int = STREAM_CHUNK_SIZE,
) -> Iterator[bytes]:
    """Build a deflate-compressed zip archive incrementally and yield its bytes
    as they're made.

    `write_entries` writes into the given ZipFile and yields after each piece
    of work; whenever at least `chunk_size` bytes have accumulated they are
    yielded. The remaining bytes, including the central directory, are yielded
    once `write_entries` finishes.
    """
    sink = _ZipStreamSink()
    with ZipFile(
        file=cast(IO[bytes], sink), mode="w", compression=ZIP_DEFLATED
    ) as zip_file:
        for _ in write_entries(zip_file):
            if sink.size >= chunk_size:
                yield sink.drain()
    yield sink.drain()


def write_zip_entry(
    zip_file: ZipFile, name: str, parts: Iterable[Union[str, bytes]]
) -> Iterator[None]:
    """Write `parts` into a new zip entry, yielding after each part."""
    with zip_file.open(name, mode="w") as entry:
        for part in parts:
            entry.write(part.encode() if isinstance(part, str) else part)
            yield


@dataclass
class GroupedLogPlan:
    """Section titles for a run's grouped log archive.

    suite_titles maps a test suite index to its public id. cases_by_state maps
    each test case state to the (suite index, case index) pairs of the test
    cases that finished in that state, and their public ids. Only suites and
    cases that have log entries are included.
    """

    suite_titles: Dict[int, str] = field(default_factory=dict)
    cases_by_state: Dict[models.TestStateEnum, Dict[Tuple[int, int], str]] = field(
        default_factory=dict
    )


def plan_grouped_log(
    db: Session, test_run_execution: models.TestRunExecution
) -> GroupedLogPlan:
    """Resolve the suites and test cases referenced by a run's log entries.

    Log entries have indexes for test suite, test case and test step
    executions. General TH logs have no test suite index; test suite logs have
    a test suite index but no test case index; test case logs have both.

    Raises IndexError if a log entry refers to a suite or case the run
    doesn't have.
    """
    plan = GroupedLogPlan()
    for suite, case in crud.test_run_execution.log_entry_groups(
        db=db, run_id=test_run_execution.id
    ):
        if suite is None:
            continue
        suite_execution = test_run_execution.test_suite_executions[suite]
        if case is None:
            plan.suite_titles[suite] = suite_execution.public_id
        else:
            case_execution = suite_execution.test_case_executions[case]
            plan.cases_by_state.setdefault(case_execution.state, {})[
                (suite, case)
            ] = case_execution.public_id
    return plan


def write_grouped_log_entries(
    zip_file: ZipFile, db: Session, run_id: int, plan: GroupedLogPlan
) -> Iterator[None]:
    """Write a run's logs into `zip_file`, grouped by test case state.

    The archive contains:
    - summary.txt: the test cases with logs, listed per state;
    - test_suites_setup_and_cleanup.log: general logs, then each test suite's
      logs that aren't tied to a test case;
    - <state>_test_cases.log (one per state): general logs, then the logs of
      each test case that finished in that state.

    Entries are read from the database in streaming batches, one query per
    file, and sections are ordered by test suite index, then test case index.
    The general logs are read once, while the suites file is written, and
    spooled to a temporary file that is replayed into each state file.
    """
    suite_index = models.TestRunLogEntry.test_suite_execution_index
    case_index = models.TestRunLogEntry.test_case_execution_index

    yield from write_zip_entry(
        zip_file, "summary.txt", [_summary_text(cases_by_state=plan.cases_by_state)]
    )

    with tempfile.SpooledTemporaryFile(max_size=10 * 1024 * 1024) as general:

        def spool_general_lines() -> Iterator[bytes]:
            for line in chain(
                [LOG_SECTION_TEMPLATE.format("Test run general logs")],
                log_generator(
                    crud.test_run_execution.iter_log_entries(
                        db=db, run_id=run_id, criteria=[suite_index.is_(None)]
                    ),
                    json_entries=False,
                ),
            ):
                data = line.encode()
                general.write(data)
                yield data

        def replay_general_lines() -> Iterator[bytes]:
            general.seek(0)
            yield from iter(lambda: general.read(STREAM_CHUNK_SIZE), b"")

        suite_entries = crud.test_run_execution.iter_log_entries(
            db=db,
            run_id=run_id,
            criteria=[suite_index.is_not(None), case_index.is_(None)],
            order_by=[suite_index],
        )
        yield from write_zip_entry(
            zip_file,
            "test_suites_setup_and_cleanup.log",
            chain(
                spool_general_lines(),
                _sectioned_log_lines(
                    entries=suite_entries,
                    section_key=lambda entry: entry.test_suite_execution_index,
                    section_titles=plan.suite_titles,
                ),
            ),
        )

        for state, case_titles in plan.cases_by_state.items():
            case_entries = crud.test_run_execution.iter_log_entries(
                db=db,
                run_id=run_id,
                criteria=[tuple_(suite_index, case_index).in_(list(case_titles))],
                order_by=[suite_index, case_index],
            )
            yield from write_zip_entry(
                zip_file,
                f"{state}_test_cases.log",
                chain(
                    replay_general_lines(),
                    _sectioned_log_lines(
                        entries=case_entries,
                        section_key=lambda entry: (
                            entry.test_suite_execution_index,
                            entry.test_case_execution_index,
                        ),
                        section_titles=case_titles,
                    ),
                ),
            )


def _sectioned_log_lines(
    entries: Iterable[models.TestRunLogEntry],
    section_key: Callable[[models.TestRunLogEntry], Any],
    section_titles: Mapping[Any, str],
) -> Iterator[str]:
    """Format entries, emitting a section header whenever `section_key`
    changes. Entries must already be ordered by section."""
    current_key: Any = object()
    for entry in entries:
        key = section_key(entry)
        if key != current_key:
            current_key = key
            yield LOG_SECTION_TEMPLATE.format(f"{section_titles[key]} logs")
        yield format_log_line(entry, json_entries=False)


def _summary_text(
    cases_by_state: Dict[models.TestStateEnum, Dict[Tuple[int, int], str]]
) -> str:
    test_case_count = sum(len(cases) for cases in cases_by_state.values())

    if test_case_count == 0:
        return "No test case has been executed"

    content: List[str] = []
    for state, cases in cases_by_state.items():
        content.append(
            LOG_SECTION_TEMPLATE.format(
                f'"{state}" test cases ({len(cases)}/{test_case_count})'
            )
        )
        content.extend(f"{public_id}\n" for public_id in cases.values())

    return "".join(content)
