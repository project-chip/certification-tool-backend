#
# Copyright (c) 2026 Project CHIP Authors
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
from io import BytesIO
from typing import BinaryIO, Optional
from unittest import mock

from app.test_engine.models.manual_test_case import (
    MANUAL_LOG_CHUNK_LINES,
    ManualLogUploadStep,
)


class FakeUploadFile:
    """Minimal stand-in for FastAPI's UploadFile used by handle_uploaded_file."""

    def __init__(self, content: bytes, content_type: str = "text/plain") -> None:
        self.file: BinaryIO = BytesIO(content)
        self.filename: Optional[str] = "manual_log.txt"
        self.content_type = content_type


@mock.patch("app.test_engine.models.manual_test_case.logger")
def test_handle_uploaded_file_rejects_unsupported_content_type(
    mock_logger: mock.Mock,
) -> None:
    step = ManualLogUploadStep("Prompt Manual Log Upload")
    step.append_failure = mock.Mock()  # type: ignore[method-assign]

    step.handle_uploaded_file(FakeUploadFile(b"irrelevant", content_type="image/png"))

    step.append_failure.assert_called_once()
    mock_logger.info.assert_not_called()


@mock.patch("app.test_engine.models.manual_test_case.logger")
def test_handle_uploaded_file_batches_lines_into_chunks(mock_logger: mock.Mock) -> None:
    """A large uploaded log must not result in one logger.info() call per line.

    Regression test for GitHub issue #1062: logging one entry per line floods
    the same channel used to broadcast updates over the websocket and to
    persist to the DB, stalling the event loop long enough that the
    websocket's ping/pong keepalive times out mid-upload.
    """
    line_count = MANUAL_LOG_CHUNK_LINES * 2 + 3
    content = "\n".join(f"line-{i}" for i in range(line_count)).encode("utf-8")

    step = ManualLogUploadStep("Prompt Manual Log Upload")
    step.append_failure = mock.Mock()  # type: ignore[method-assign]

    step.handle_uploaded_file(FakeUploadFile(content))

    step.append_failure.assert_not_called()

    # "Uploading manual log: ...", "---- Start ----", N chunk(s), "---- End ----"
    info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
    assert info_calls[0].startswith("Uploading manual log:")
    assert info_calls[1] == "---- Start of Manual Log ----"
    assert info_calls[-1] == "---- End of Manual Log ----"

    chunk_calls = info_calls[2:-1]
    # 2 full chunks + 1 partial chunk, never one call per line.
    assert len(chunk_calls) == 3
    assert chunk_calls[0].count("\n") == MANUAL_LOG_CHUNK_LINES - 1
    assert chunk_calls[-1].count("\n") == 2  # trailing partial chunk of 3 lines

    # All lines are still present, in order, across the batched calls.
    reconstructed = "\n".join(chunk_calls).splitlines()
    assert reconstructed == [f"line-{i}" for i in range(line_count)]


@mock.patch("app.test_engine.models.manual_test_case.logger")
def test_handle_uploaded_file_replaces_invalid_utf8_and_warns_once(
    mock_logger: mock.Mock,
) -> None:
    content = b"good line\n\xff\xfe bad line\ngood line 2\n"

    step = ManualLogUploadStep("Prompt Manual Log Upload")
    step.append_failure = mock.Mock()  # type: ignore[method-assign]

    step.handle_uploaded_file(FakeUploadFile(content))

    mock_logger.warning.assert_called_once()
    info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
    body = "\n".join(info_calls[2:-1])
    assert "�" in body


@mock.patch("app.test_engine.models.manual_test_case.logger")
def test_handle_uploaded_file_strips_windows_line_endings(
    mock_logger: mock.Mock,
) -> None:
    """Windows-style CRLF line endings must not leave a stray \\r in each line.

    Regression test: an earlier version of this fix used .rstrip("\\n"), which
    left a trailing \\r on every line of a CRLF-terminated file, corrupting the
    joined chunk with embedded carriage returns.
    """
    content = b"line one\r\nline two\r\nline three\r\n"

    step = ManualLogUploadStep("Prompt Manual Log Upload")
    step.append_failure = mock.Mock()  # type: ignore[method-assign]

    step.handle_uploaded_file(FakeUploadFile(content))

    info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
    body = "\n".join(info_calls[2:-1])
    assert "\r" not in body
    assert body.splitlines() == ["line one", "line two", "line three"]
