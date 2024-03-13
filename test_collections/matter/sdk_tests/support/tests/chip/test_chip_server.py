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

# type: ignore
# Ignore mypy type check for this file

from unittest import mock

import pytest

from .....config import matterSettings

from ...chip.chip_server import (
    CHIP_APP_EXE,
    CHIP_TOOL_ARG_PAA_CERTS_PATH,
    CHIP_TOOL_EXE,
    DOCKER_PAA_CERTS_PATH,
    ChipServer,
    ChipServerStartingError,
    ChipServerType,
    UnsupportedChipServerType,
)
from ...exec_run_in_container import ExecResultExtended
from ...sdk_container import SDKContainer


@pytest.mark.asyncio
async def test_start_already_started() -> None:
    chip_server: ChipServer = ChipServer()
    sdk_container: SDKContainer = SDKContainer()
    server_type = ChipServerType.CHIP_TOOL
    chip_server._ChipServer__server_logs = "log output".encode()
    chip_server._ChipServer__server_started = True

    with mock.patch.object(
        target=sdk_container, attribute="send_command"
    ) as mock_send_command:
        await chip_server.start(server_type, use_paa_certs=False)

    mock_send_command.assert_not_called()

    # clean up:
    chip_server._ChipServer__server_logs = None
    chip_server._ChipServer__server_started = False


@pytest.mark.asyncio
async def test_start_unsupported_server_type() -> None:
    chip_server: ChipServer = ChipServer()
    sdk_container: SDKContainer = SDKContainer()
    server_type = "unsupported"

    with mock.patch.object(
        target=sdk_container, attribute="send_command"
    ) as mock_send_command, pytest.raises(UnsupportedChipServerType):
        await chip_server.start(server_type, use_paa_certs=False)

    mock_send_command.assert_not_called()

    # clean up:
    chip_server._ChipServer__node_id = None


@pytest.mark.asyncio
async def test_start_waiting_failure() -> None:
    original_trace_setting_value = matterSettings.CHIP_TOOL_TRACE
    if original_trace_setting_value is True:
        matterSettings.CHIP_TOOL_TRACE = False

    chip_server: ChipServer = ChipServer()
    sdk_container: SDKContainer = SDKContainer()
    server_type = ChipServerType.CHIP_TOOL
    mock_result = ExecResultExtended(0, "log output".encode(), "ID", mock.MagicMock())

    expected_command = ["interactive", "server"]
    expected_prefix = CHIP_TOOL_EXE

    with mock.patch.object(
        target=sdk_container, attribute="send_command", return_value=mock_result
    ) as mock_send_command, mock.patch.object(
        target=chip_server,
        attribute="_ChipServer__wait_for_server_start",
        return_value=False,
    ), pytest.raises(
        ChipServerStartingError
    ):
        await chip_server.start(server_type)

    mock_send_command.assert_called_once_with(
        expected_command, prefix=expected_prefix, is_stream=True, is_socket=False
    )
    assert chip_server._ChipServer__server_logs == mock_result.output
    assert chip_server._ChipServer__chip_server_id == mock_result.exec_id
    assert chip_server._ChipServer__server_started is False

    # clean up:
    chip_server._ChipServer__server_logs = None
    chip_server._ChipServer__chip_server_id = None
    matterSettings.CHIP_TOOL_TRACE = original_trace_setting_value


@pytest.mark.asyncio
async def test_start_chip_tool() -> None:
    original_trace_setting_value = matterSettings.CHIP_TOOL_TRACE
    if original_trace_setting_value is True:
        matterSettings.CHIP_TOOL_TRACE = False

    chip_server: ChipServer = ChipServer()
    sdk_container: SDKContainer = SDKContainer()
    server_type = ChipServerType.CHIP_TOOL
    mock_result = ExecResultExtended(0, "log output".encode(), "ID", mock.MagicMock())

    expected_command = ["interactive", "server"]
    expected_prefix = CHIP_TOOL_EXE

    with mock.patch.object(
        target=sdk_container, attribute="send_command", return_value=mock_result
    ) as mock_send_command, mock.patch.object(
        target=chip_server,
        attribute="_ChipServer__wait_for_server_start",
        return_value=True,
    ):
        await chip_server.start(server_type, use_paa_certs=False)

    mock_send_command.assert_called_once_with(
        expected_command, prefix=expected_prefix, is_stream=True, is_socket=False
    )
    assert chip_server._ChipServer__server_logs == mock_result.output
    assert chip_server._ChipServer__chip_server_id == mock_result.exec_id
    assert chip_server._ChipServer__server_started is True

    # clean up:
    chip_server._ChipServer__server_logs = None
    chip_server._ChipServer__chip_server_id = None
    chip_server._ChipServer__server_started = False
    matterSettings.CHIP_TOOL_TRACE = original_trace_setting_value


@pytest.mark.asyncio
async def test_start_chip_tool_using_paa_certs() -> None:
    original_trace_setting_value = matterSettings.CHIP_TOOL_TRACE
    if original_trace_setting_value is True:
        matterSettings.CHIP_TOOL_TRACE = False

    chip_server: ChipServer = ChipServer()
    sdk_container: SDKContainer = SDKContainer()
    server_type = ChipServerType.CHIP_TOOL
    mock_result = ExecResultExtended(0, "log output".encode(), "ID", mock.MagicMock())

    expected_command = [
        "interactive",
        "server",
        f"{CHIP_TOOL_ARG_PAA_CERTS_PATH} {DOCKER_PAA_CERTS_PATH}",
    ]
    expected_prefix = CHIP_TOOL_EXE

    with mock.patch.object(
        target=sdk_container, attribute="send_command", return_value=mock_result
    ) as mock_send_command, mock.patch.object(
        target=chip_server,
        attribute="_ChipServer__wait_for_server_start",
        return_value=True,
    ):
        await chip_server.start(server_type, use_paa_certs=True)

    mock_send_command.assert_called_once_with(
        expected_command, prefix=expected_prefix, is_stream=True, is_socket=False
    )
    assert chip_server._ChipServer__server_logs == mock_result.output
    assert chip_server._ChipServer__chip_server_id == mock_result.exec_id
    assert chip_server._ChipServer__server_started is True

    # clean up:
    chip_server._ChipServer__server_logs = None
    chip_server._ChipServer__chip_server_id = None
    chip_server._ChipServer__server_started = False
    matterSettings.CHIP_TOOL_TRACE = original_trace_setting_value


@pytest.mark.asyncio
async def test_start_chip_app() -> None:
    original_trace_setting_value = matterSettings.CHIP_TOOL_TRACE
    if original_trace_setting_value is True:
        matterSettings.CHIP_TOOL_TRACE = False

    chip_server: ChipServer = ChipServer()
    sdk_container: SDKContainer = SDKContainer()
    server_type = ChipServerType.CHIP_APP
    mock_result = ExecResultExtended(0, "log output".encode(), "ID", mock.MagicMock())

    expected_command = ["--interactive", "--port 9002"]
    expected_prefix = CHIP_APP_EXE

    with mock.patch.object(
        target=sdk_container, attribute="send_command", return_value=mock_result
    ) as mock_send_command, mock.patch.object(
        target=chip_server,
        attribute="_ChipServer__wait_for_server_start",
        return_value=True,
    ):
        await chip_server.start(server_type, use_paa_certs=False)

    mock_send_command.assert_called_once_with(
        expected_command, prefix=expected_prefix, is_stream=True, is_socket=False
    )
    assert chip_server._ChipServer__server_logs == mock_result.output
    assert chip_server._ChipServer__chip_server_id == mock_result.exec_id
    assert chip_server._ChipServer__server_started is True

    # clean up:
    chip_server._ChipServer__server_logs = None
    chip_server._ChipServer__chip_server_id = None
    chip_server._ChipServer__server_started = False
    matterSettings.CHIP_TOOL_TRACE = original_trace_setting_value


@pytest.mark.asyncio
async def test_start_chip_app_using_paa_certs() -> None:
    original_trace_setting_value = matterSettings.CHIP_TOOL_TRACE
    if original_trace_setting_value is True:
        matterSettings.CHIP_TOOL_TRACE = False

    chip_server: ChipServer = ChipServer()
    sdk_container: SDKContainer = SDKContainer()
    server_type = ChipServerType.CHIP_APP
    mock_result = ExecResultExtended(0, "log output".encode(), "ID", mock.MagicMock())

    expected_command = [
        "--interactive",
        "--port 9002",
        f"{CHIP_TOOL_ARG_PAA_CERTS_PATH} {DOCKER_PAA_CERTS_PATH}",
    ]
    expected_prefix = CHIP_APP_EXE

    with mock.patch.object(
        target=sdk_container, attribute="send_command", return_value=mock_result
    ) as mock_send_command, mock.patch.object(
        target=chip_server,
        attribute="_ChipServer__wait_for_server_start",
        return_value=True,
    ):
        await chip_server.start(server_type, use_paa_certs=True)

    mock_send_command.assert_called_once_with(
        expected_command, prefix=expected_prefix, is_stream=True, is_socket=False
    )
    assert chip_server._ChipServer__server_logs == mock_result.output
    assert chip_server._ChipServer__server_started is True

    # clean up:
    chip_server._ChipServer__server_logs = None
    chip_server._ChipServer__chip_server_id = None
    chip_server._ChipServer__server_started = False
    matterSettings.CHIP_TOOL_TRACE = original_trace_setting_value
