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
from http import HTTPStatus
from json import JSONDecodeError

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.tests.utils.test_runner import load_and_run_tool_unit_tests
from test_collections.tool_unit_tests.test_suite_expected import TestSuiteExpected
from test_collections.tool_unit_tests.test_suite_expected.tctr_expected_pass import (
    TCTRExpectedPass,
)


def process_log_messages(log_lines: list[str]) -> list[str]:
    """Process log lines and combine multi-line messages.

    Args:
        log_lines: List of log lines to process

    Returns:
        List of processed messages where multi-line entries are combined
    """
    processed_messages: list[str] = []
    current_message: list[str] = []

    for line in log_lines:
        if not line:
            continue

        message = line.split(" | ")[-1].strip()

        if message in ["Project config:", "Project PICS:"]:
            if current_message:
                processed_messages.append("\n".join(current_message))
            current_message = [message]
        elif message.startswith(("{", "clusters=")) or not message:
            if current_message:
                current_message.append(message)
            else:
                processed_messages.append(message)
        else:
            if current_message:
                processed_messages.append("\n".join(current_message))
                current_message = []
            processed_messages.append(message)

    if current_message:
        processed_messages.append("\n".join(current_message))

    return processed_messages


@pytest.mark.asyncio
async def test_test_run_execution_response_log(
    async_client: AsyncClient, db: Session
) -> None:
    _, run, _, _ = await load_and_run_tool_unit_tests(
        db, TestSuiteExpected, TCTRExpectedPass
    )

    run_db = run.test_run_execution
    id = run_db.id
    url = f"{settings.API_V1_STR}/test_run_executions/{id}/log"
    response = await async_client.get(url)

    assert response.status_code == HTTPStatus.OK

    content_disposition_header = response.headers.get("content-disposition")
    assert content_disposition_header is None

    content_type_header = response.headers.get("content-type")
    assert content_type_header is not None
    assert isinstance(content_type_header, str)
    assert content_type_header == "text/plain; charset=utf-8"

    response_log_lines = response.text.split("\n")
    if response_log_lines[-1] == "":
        response_log_lines.pop()

    # check response is not JSON
    response_first_line = response_log_lines[0]
    with pytest.raises(JSONDecodeError):
        json.loads(response_first_line)

    response_messages = process_log_messages(response_log_lines)
    db_messages = [log_entry.message for log_entry in run_db.log]

    assert len(response_messages) == len(db_messages)
    for i, (resp_msg, db_msg) in enumerate(zip(response_messages, db_messages)):
        if resp_msg != db_msg:
            pytest.fail(
                f"Message mismatch at index {i}:\n"
                f"Response: {resp_msg}\nDatabase: {db_msg}"
            )


@pytest.mark.asyncio
async def test_test_run_execution_download_log(
    async_client: AsyncClient, db: Session
) -> None:
    _, run, _, _ = await load_and_run_tool_unit_tests(
        db, TestSuiteExpected, TCTRExpectedPass
    )

    run_db = run.test_run_execution
    id = run_db.id
    url = f"{settings.API_V1_STR}/test_run_executions/{id}/log?download=true"
    response = await async_client.get(url)

    assert response.status_code == HTTPStatus.OK

    content_disposition_header = response.headers.get("content-disposition")
    assert content_disposition_header is not None
    assert isinstance(content_disposition_header, str)
    expected_filename = f"{id}-{run_db.title}.log"
    assert content_disposition_header == f'attachment; filename="{expected_filename}"'

    content_type_header = response.headers.get("content-type")
    assert content_type_header is not None
    assert isinstance(content_type_header, str)
    assert content_type_header == "text/plain; charset=utf-8"

    file_lines = response.text.split("\n")
    if file_lines[-1] == "":
        file_lines.pop()

    # check response is not JSON
    file_first_line = file_lines[0]
    with pytest.raises(JSONDecodeError):
        json.loads(file_first_line)

    processed_lines = process_log_messages(file_lines)
    assert len(processed_lines) == len(run_db.log)


@pytest.mark.asyncio
async def test_test_run_execution_json_log(
    async_client: AsyncClient, db: Session
) -> None:
    _, run, _, _ = await load_and_run_tool_unit_tests(
        db, TestSuiteExpected, TCTRExpectedPass
    )

    run_db = run.test_run_execution
    id = run_db.id
    url = f"{settings.API_V1_STR}/test_run_executions/{id}/log?json_entries=true"
    response = await async_client.get(url)

    assert response.status_code == HTTPStatus.OK

    content_disposition_header = response.headers.get("content-disposition")
    assert content_disposition_header is None

    content_type_header = response.headers.get("content-type")
    assert content_type_header is not None
    assert isinstance(content_type_header, str)
    assert content_type_header == "text/plain; charset=utf-8"

    response_log_lines = response.text.split("\n")
    # Downloaded file have empty line in the end.
    assert len(response_log_lines) - 1 == len(run_db.log)

    # check response is JSON
    response_first_line = response_log_lines[0]
    parsed_line = json.loads(response_first_line)
    original_first_line = run_db.log[0]
    assert parsed_line == original_first_line
