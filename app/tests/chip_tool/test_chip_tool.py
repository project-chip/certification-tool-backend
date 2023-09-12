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

# type: ignore
# Ignore mypy type check for this file

from subprocess import CompletedProcess
from unittest import mock

import pytest
from matter_yamltests.hooks import TestParserHooks, TestRunnerHooks
from matter_yamltests.parser_builder import TestParserBuilderConfig
from matter_yamltests.runner import TestRunnerConfig

from app.chip_tool import ChipTool
from app.chip_tool.chip_tool import (
    CHIP_APP_EXE,
    CHIP_TOOL_ARG_PAA_CERTS_PATH,
    CHIP_TOOL_CONTINUE_ON_FAILURE_VALUE,
    CHIP_TOOL_EXE,
    CHIP_TOOL_TEST_DEFAULT_TIMEOUT_IN_SEC,
    DOCKER_PAA_CERTS_PATH,
    PICS_FILE_PATH,
    SHELL_OPTION,
    SHELL_PATH,
    TEST_STEP_DELAY_VALUE,
    ChipToolNotRunning,
    ChipToolStartingError,
    ChipToolTestType,
    ChipToolUnknownTestType,
)
from app.chip_tool.exec_run_in_container import ExecResultExtended
from app.container_manager import container_manager
from app.core.config import settings
from app.schemas.pics import PICSError
from app.tests.utils.docker import make_fake_container
from app.tests.utils.test_pics_data import create_random_pics


@pytest.mark.asyncio
async def test_start_container() -> None:
    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_TOOL

    # Values to verify
    docker_image = f"{settings.SDK_DOCKER_IMAGE}:{settings.SDK_DOCKER_TAG}"

    with mock.patch.object(
        target=chip_tool, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=container_manager, attribute="get_container", return_value=None
    ), mock.patch(
        target="app.chip_tool.chip_tool.backend_container"
    ), mock.patch.object(
        target=container_manager, attribute="create_container"
    ) as mock_create_container, mock.patch.object(
        target=chip_tool, attribute="start_chip_server"
    ) as mock_start_chip_server:
        await chip_tool.start_container(test_type)

    mock_create_container.assert_called_once_with(docker_image, ChipTool.run_parameters)
    mock_start_chip_server.assert_awaited_once_with(test_type, False)
    assert chip_tool._ChipTool__chip_tool_container is not None

    # clean up:
    chip_tool._ChipTool__chip_tool_container = None


@pytest.mark.asyncio
async def test_start_container_using_paa_certs() -> None:
    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_TOOL

    # Values to verify
    docker_image = f"{settings.SDK_DOCKER_IMAGE}:{settings.SDK_DOCKER_TAG}"

    with mock.patch.object(
        target=chip_tool, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=container_manager, attribute="get_container", return_value=None
    ), mock.patch(
        target="app.chip_tool.chip_tool.backend_container"
    ), mock.patch.object(
        target=container_manager, attribute="create_container"
    ) as mock_create_container, mock.patch.object(
        target=chip_tool, attribute="start_chip_server"
    ) as mock_start_chip_server:
        await chip_tool.start_container(test_type, use_paa_certs=True)

    mock_create_container.assert_called_once_with(docker_image, ChipTool.run_parameters)
    mock_start_chip_server.assert_awaited_once_with(test_type, True)
    assert chip_tool._ChipTool__chip_tool_container is not None

    # clean up:
    chip_tool._ChipTool__chip_tool_container = None


@pytest.mark.asyncio
async def test_not_start_container_when_running() -> None:
    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_TOOL

    with mock.patch.object(
        target=chip_tool, attribute="is_running", return_value=True
    ), mock.patch.object(
        target=container_manager, attribute="create_container"
    ) as mock_create_container, mock.patch.object(
        target=chip_tool, attribute="start_chip_server"
    ) as mock_start_chip_server:
        await chip_tool.start_container(test_type)

    mock_create_container.assert_not_called()
    mock_start_chip_server.assert_not_called()
    assert chip_tool._ChipTool__chip_tool_container is None


@pytest.mark.asyncio
async def test_start_chip_server_already_started() -> None:
    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_TOOL
    chip_tool._ChipTool__server_logs = "log output".encode()
    chip_tool._ChipTool__server_started = True

    with mock.patch.object(
        target=chip_tool, attribute="send_command"
    ) as mock_send_command:
        await chip_tool.start_chip_server(test_type)

    mock_send_command.assert_not_called()

    # clean up:
    chip_tool._ChipTool__server_logs = None
    chip_tool._ChipTool__server_started = False


@pytest.mark.asyncio
async def test_start_chip_server_unsupported_test_type() -> None:
    chip_tool = ChipTool()
    test_type = "unsupported"

    with mock.patch.object(
        target=chip_tool, attribute="send_command"
    ) as mock_send_command, pytest.raises(ChipToolUnknownTestType):
        await chip_tool.start_chip_server(test_type, use_paa_certs=False)

    mock_send_command.assert_not_called()


@pytest.mark.asyncio
async def test_start_chip_server_waiting_failure() -> None:
    original_trace_setting_value = settings.CHIP_TOOL_TRACE
    if original_trace_setting_value is True:
        settings.CHIP_TOOL_TRACE = False

    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_TOOL
    mock_result = ExecResultExtended(0, "log output".encode(), "ID", mock.MagicMock())

    expected_command = ["interactive", "server"]
    expected_prefix = CHIP_TOOL_EXE

    with mock.patch.object(
        target=chip_tool, attribute="send_command", return_value=mock_result
    ) as mock_send_command, mock.patch.object(
        target=chip_tool,
        attribute="_ChipTool__wait_for_server_start",
        return_value=False,
    ), pytest.raises(
        ChipToolStartingError
    ):
        await chip_tool.start_chip_server(test_type, use_paa_certs=False)

    mock_send_command.assert_called_once_with(
        expected_command, prefix=expected_prefix, is_stream=True, is_socket=False
    )
    assert chip_tool._ChipTool__server_logs == mock_result.output
    assert chip_tool._ChipTool__server_started is False

    # clean up:
    chip_tool._ChipTool__server_logs = None
    chip_tool._ChipTool__chip_tool_server_id = None
    settings.CHIP_TOOL_TRACE = original_trace_setting_value


@pytest.mark.asyncio
async def test_start_chip_server_chip_tool() -> None:
    original_trace_setting_value = settings.CHIP_TOOL_TRACE
    if original_trace_setting_value is True:
        settings.CHIP_TOOL_TRACE = False

    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_TOOL
    mock_result = ExecResultExtended(0, "log output".encode(), "ID", mock.MagicMock())

    expected_command = ["interactive", "server"]
    expected_prefix = CHIP_TOOL_EXE

    with mock.patch.object(
        target=chip_tool, attribute="send_command", return_value=mock_result
    ) as mock_send_command, mock.patch.object(
        target=chip_tool,
        attribute="_ChipTool__wait_for_server_start",
        return_value=True,
    ):
        await chip_tool.start_chip_server(test_type, use_paa_certs=False)

    mock_send_command.assert_called_once_with(
        expected_command, prefix=expected_prefix, is_stream=True, is_socket=False
    )
    assert chip_tool._ChipTool__server_logs == mock_result.output
    assert chip_tool._ChipTool__server_started is True

    # clean up:
    chip_tool._ChipTool__server_logs = None
    chip_tool._ChipTool__chip_tool_server_id = None
    chip_tool._ChipTool__server_started = False
    settings.CHIP_TOOL_TRACE = original_trace_setting_value


@pytest.mark.asyncio
async def test_start_chip_server_chip_tool_using_paa_certs() -> None:
    original_trace_setting_value = settings.CHIP_TOOL_TRACE
    if original_trace_setting_value is True:
        settings.CHIP_TOOL_TRACE = False

    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_TOOL
    mock_result = ExecResultExtended(0, "log output".encode(), "ID", mock.MagicMock())

    expected_command = [
        "interactive",
        "server",
        f"{CHIP_TOOL_ARG_PAA_CERTS_PATH} {DOCKER_PAA_CERTS_PATH}",
    ]
    expected_prefix = CHIP_TOOL_EXE

    with mock.patch.object(
        target=chip_tool, attribute="send_command", return_value=mock_result
    ) as mock_send_command, mock.patch.object(
        target=chip_tool,
        attribute="_ChipTool__wait_for_server_start",
        return_value=True,
    ):
        await chip_tool.start_chip_server(test_type, use_paa_certs=True)

    mock_send_command.assert_called_once_with(
        expected_command, prefix=expected_prefix, is_stream=True, is_socket=False
    )
    assert chip_tool._ChipTool__server_logs == mock_result.output
    assert chip_tool._ChipTool__server_started is True

    # clean up:
    chip_tool._ChipTool__server_logs = None
    chip_tool._ChipTool__chip_tool_server_id = None
    chip_tool._ChipTool__server_started = False
    settings.CHIP_TOOL_TRACE = original_trace_setting_value


@pytest.mark.asyncio
async def test_start_chip_server_chip_app() -> None:
    original_trace_setting_value = settings.CHIP_TOOL_TRACE
    if original_trace_setting_value is True:
        settings.CHIP_TOOL_TRACE = False

    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_APP
    mock_result = ExecResultExtended(0, "log output".encode(), "ID", mock.MagicMock())

    expected_command = ["--interactive", "--port 9002"]
    expected_prefix = CHIP_APP_EXE

    with mock.patch.object(
        target=chip_tool, attribute="send_command", return_value=mock_result
    ) as mock_send_command, mock.patch.object(
        target=chip_tool,
        attribute="_ChipTool__wait_for_server_start",
        return_value=True,
    ):
        await chip_tool.start_chip_server(test_type, use_paa_certs=False)

    mock_send_command.assert_called_once_with(
        expected_command, prefix=expected_prefix, is_stream=True, is_socket=False
    )
    assert chip_tool._ChipTool__server_logs == mock_result.output
    assert chip_tool._ChipTool__server_started is True

    # clean up:
    chip_tool._ChipTool__server_logs = None
    chip_tool._ChipTool__chip_tool_server_id = None
    chip_tool._ChipTool__server_started = False
    settings.CHIP_TOOL_TRACE = original_trace_setting_value


@pytest.mark.asyncio
async def test_start_chip_server_chip_app_using_paa_certs() -> None:
    original_trace_setting_value = settings.CHIP_TOOL_TRACE
    if original_trace_setting_value is True:
        settings.CHIP_TOOL_TRACE = False

    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_APP
    mock_result = ExecResultExtended(0, "log output".encode(), "ID", mock.MagicMock())

    expected_command = [
        "--interactive",
        "--port 9002",
        f"{CHIP_TOOL_ARG_PAA_CERTS_PATH} {DOCKER_PAA_CERTS_PATH}",
    ]
    expected_prefix = CHIP_APP_EXE

    with mock.patch.object(
        target=chip_tool, attribute="send_command", return_value=mock_result
    ) as mock_send_command, mock.patch.object(
        target=chip_tool,
        attribute="_ChipTool__wait_for_server_start",
        return_value=True,
    ):
        await chip_tool.start_chip_server(test_type, use_paa_certs=True)

    mock_send_command.assert_called_once_with(
        expected_command, prefix=expected_prefix, is_stream=True, is_socket=False
    )
    assert chip_tool._ChipTool__server_logs == mock_result.output
    assert chip_tool._ChipTool__server_started is True

    # clean up:
    chip_tool._ChipTool__server_logs = None
    chip_tool._ChipTool__chip_tool_server_id = None
    chip_tool._ChipTool__server_started = False
    settings.CHIP_TOOL_TRACE = original_trace_setting_value


@pytest.mark.asyncio
async def test_destroy_container_running() -> None:
    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_TOOL

    with mock.patch.object(
        target=chip_tool, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=container_manager, attribute="get_container"
    ), mock.patch.object(
        target=container_manager, attribute="destroy"
    ) as mock_destroy, mock.patch.object(
        target=container_manager, attribute="create_container"
    ), mock.patch.object(
        target=chip_tool, attribute="start_chip_server"
    ):
        await chip_tool.start_container(test_type)
        await chip_tool.start_container(test_type)

        assert chip_tool._ChipTool__chip_tool_container is not None

        chip_tool.destroy_device()

    mock_destroy.assert_called()
    assert chip_tool._ChipTool__chip_tool_container is None


@pytest.mark.asyncio
async def test_destroy_container_not_running() -> None:
    chip_tool = ChipTool()

    with mock.patch.object(
        target=container_manager, attribute="destroy"
    ) as mock_destroy:
        chip_tool.destroy_device()

    mock_destroy.assert_not_called()
    assert chip_tool._ChipTool__chip_tool_container is None


@pytest.mark.asyncio
async def test_destroy_container_once() -> None:
    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_TOOL

    with mock.patch.object(
        target=chip_tool, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=container_manager, attribute="get_container", return_value=None
    ), mock.patch(
        target="app.chip_tool.chip_tool.backend_container"
    ), mock.patch.object(
        target=container_manager, attribute="destroy"
    ) as mock_destroy, mock.patch.object(
        target=container_manager,
        attribute="create_container",
        return_value=make_fake_container(),
    ), mock.patch.object(
        target=chip_tool, attribute="start_chip_server"
    ):
        await chip_tool.start_container(test_type)

        chip_tool.destroy_device()
        chip_tool.destroy_device()

    mock_destroy.assert_called_once()
    assert chip_tool._ChipTool__chip_tool_container is None


def test_send_command_without_starting() -> None:
    chip_tool = ChipTool()

    with pytest.raises(ChipToolNotRunning):
        chip_tool.send_command("--help", prefix=CHIP_TOOL_EXE)


@pytest.mark.asyncio
async def test_set_pics() -> None:
    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_TOOL
    pics = create_random_pics()

    # expected PICS = PICS from create_random_pics() + \n + DEFAULT PICS
    expected_pics_data = (
        "AB.C=1\nAB.C.A0004=1\nXY.C=0\nAB.S.C0003=1\n"
        "PICS_SDK_CI_ONLY=0\nPICS_SKIP_SAMPLE_APP=1\n"
        "PICS_USER_PROMPT=1"
    )
    expected_command = (
        f"{SHELL_PATH} {SHELL_OPTION} \"echo '{expected_pics_data}\n' "
        f'> {PICS_FILE_PATH}"'
    )

    with mock.patch.object(
        target=chip_tool, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=container_manager, attribute="get_container"
    ), mock.patch.object(
        target=container_manager, attribute="destroy"
    ), mock.patch.object(
        target=container_manager,
        attribute="create_container",
        return_value=make_fake_container(),
    ), mock.patch.object(
        target=chip_tool, attribute="start_chip_server"
    ), mock.patch(
        target="app.chip_tool.chip_tool.subprocess.run",
        return_value=CompletedProcess(expected_command, 0),
    ) as mock_run:
        await chip_tool.start_container(test_type)

        chip_tool.set_pics(pics)

    mock_run.assert_called_once_with(expected_command, shell=True)
    assert chip_tool._ChipTool__pics_file_created is True

    # clean up:
    chip_tool._ChipTool__pics_file_created = False
    chip_tool._ChipTool__last_exec_id = None
    chip_tool._ChipTool__chip_tool_container = None


def test_set_pics_with_error() -> None:
    chip_tool = ChipTool()
    pics = create_random_pics()

    with mock.patch(
        target="app.chip_tool.chip_tool.subprocess.run",
        return_value=CompletedProcess("", 1),
    ), pytest.raises(PICSError):
        chip_tool.set_pics(pics)
        assert chip_tool._ChipTool__pics_file_created is False

    # clean up:
    chip_tool._ChipTool__last_exec_id = None


@pytest.mark.asyncio
async def test_send_command_default_prefix() -> None:
    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_TOOL
    fake_container = make_fake_container()
    cmd = "--help"
    chip_tool_prefix = CHIP_TOOL_EXE
    mock_result = ExecResultExtended(0, "log output".encode(), "ID", mock.MagicMock())

    with mock.patch.object(
        target=chip_tool, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=container_manager, attribute="get_container"
    ), mock.patch.object(
        target=container_manager, attribute="destroy"
    ), mock.patch.object(
        target=container_manager,
        attribute="create_container",
        return_value=fake_container,
    ), mock.patch.object(
        target=chip_tool, attribute="start_chip_server"
    ), mock.patch(
        target="app.chip_tool.chip_tool.exec_run_in_container",
        return_value=mock_result,
    ) as mock_exec_run:
        await chip_tool.start_container(test_type)

        result = chip_tool.send_command(cmd, prefix=chip_tool_prefix)

    mock_exec_run.assert_called_once_with(
        fake_container,
        f"{chip_tool_prefix} {cmd}",
        socket=False,
        stream=False,
        stdin=True,
    )
    assert result == mock_result

    # clean up:
    chip_tool._ChipTool__last_exec_id = None
    chip_tool._ChipTool__chip_tool_container = None


@pytest.mark.asyncio
async def test_send_command_custom_prefix() -> None:
    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_TOOL
    fake_container = make_fake_container()
    cmd = "--help"
    chip_tool_prefix = "cat"
    mock_result = ExecResultExtended(0, "log output".encode(), "ID", mock.MagicMock())

    with mock.patch.object(
        target=chip_tool, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=container_manager, attribute="get_container"
    ), mock.patch.object(
        target=container_manager, attribute="destroy"
    ), mock.patch.object(
        target=container_manager,
        attribute="create_container",
        return_value=fake_container,
    ), mock.patch.object(
        target=chip_tool, attribute="start_chip_server"
    ), mock.patch(
        target="app.chip_tool.chip_tool.exec_run_in_container",
        return_value=mock_result,
    ) as mock_exec_run:
        await chip_tool.start_container(test_type)

        result = chip_tool.send_command(cmd, prefix=chip_tool_prefix)

    mock_exec_run.assert_called_once_with(
        fake_container,
        f"{chip_tool_prefix} {cmd}",
        socket=False,
        stream=False,
        stdin=True,
    )
    assert result == mock_result

    # clean up:
    chip_tool._ChipTool__last_exec_id = None
    chip_tool._ChipTool__chip_tool_container = None


@pytest.mark.asyncio
async def test_run_test_default_config() -> None:
    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_TOOL
    test_id = "TC_TEST_ID"
    fake_container = make_fake_container()

    with mock.patch.object(
        target=chip_tool, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=container_manager, attribute="get_container"
    ), mock.patch.object(
        target=container_manager, attribute="destroy"
    ), mock.patch.object(
        target=container_manager,
        attribute="create_container",
        return_value=fake_container,
    ), mock.patch.object(
        target=chip_tool, attribute="start_chip_server"
    ), mock.patch(
        target="app.chip_tool.chip_tool.WebSocketRunner.run",
        return_value=True,
    ) as mock_run:
        await chip_tool.start_container(test_type)

        await chip_tool.run_test(
            test_step_interface=TestRunnerHooks(),
            test_parser_hooks=TestParserHooks(),
            test_id=test_id,
            test_type=test_type,
        )

    mock_run.assert_called_once()
    # parser_builder_config is the 1st parameter in WebSocketRunner.run
    parser_builder_config: TestParserBuilderConfig = mock_run.mock_calls[0].args[0]
    assert len(parser_builder_config.tests) == 1
    assert test_id in parser_builder_config.tests[0]
    parser_options = parser_builder_config.parser_config.config_override
    assert parser_options["nodeId"] == f"{hex(chip_tool.node_id)}"
    assert parser_options["timeout"] == f"{CHIP_TOOL_TEST_DEFAULT_TIMEOUT_IN_SEC}"
    # runner_config is the 2nd parameter in WebSocketRunner.run
    runner_config: TestRunnerConfig = mock_run.mock_calls[0].args[1]
    runner_options = runner_config.options
    assert runner_options.stop_on_error is not CHIP_TOOL_CONTINUE_ON_FAILURE_VALUE
    assert runner_options.stop_on_warning is False
    assert runner_options.stop_at_number == -1
    assert runner_options.delay_in_ms == TEST_STEP_DELAY_VALUE

    # clean up:
    chip_tool._ChipTool__last_exec_id = None
    chip_tool._ChipTool__chip_tool_container = None


@pytest.mark.asyncio
async def test_run_test_custom_timeout() -> None:
    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_TOOL
    test_id = "TC_TEST_ID"
    test_timeout = "900"
    fake_container = make_fake_container()

    with mock.patch.object(
        target=chip_tool, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=container_manager, attribute="get_container"
    ), mock.patch.object(
        target=container_manager, attribute="destroy"
    ), mock.patch.object(
        target=container_manager,
        attribute="create_container",
        return_value=fake_container,
    ), mock.patch.object(
        target=chip_tool, attribute="start_chip_server"
    ), mock.patch(
        target="app.chip_tool.chip_tool.WebSocketRunner.run",
        return_value=True,
    ) as mock_run:
        await chip_tool.start_container(test_type)

        await chip_tool.run_test(
            test_step_interface=TestRunnerHooks(),
            test_parser_hooks=TestParserHooks(),
            test_id=test_id,
            test_type=test_type,
            timeout=test_timeout,
        )

    mock_run.assert_called_once()
    # parser_builder_config is the 1st parameter in WebSocketRunner.run
    parser_builder_config: TestParserBuilderConfig = mock_run.mock_calls[0].args[0]
    assert len(parser_builder_config.tests) == 1
    assert test_id in parser_builder_config.tests[0]
    parser_options = parser_builder_config.parser_config.config_override
    assert parser_options["timeout"] == f"{test_timeout}"

    # clean up:
    chip_tool._ChipTool__last_exec_id = None
    chip_tool._ChipTool__chip_tool_container = None


@pytest.mark.asyncio
async def test_run_test_with_custom_parameter() -> None:
    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_TOOL
    test_id = "TC_TEST_ID"
    test_param_name = "param1"
    test_param_value = "value"
    fake_container = make_fake_container()

    with mock.patch.object(
        target=chip_tool, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=container_manager, attribute="get_container"
    ), mock.patch.object(
        target=container_manager, attribute="destroy"
    ), mock.patch.object(
        target=container_manager,
        attribute="create_container",
        return_value=fake_container,
    ), mock.patch.object(
        target=chip_tool, attribute="start_chip_server"
    ), mock.patch(
        target="app.chip_tool.chip_tool.WebSocketRunner.run",
        return_value=True,
    ) as mock_run:
        await chip_tool.start_container(test_type)

        await chip_tool.run_test(
            test_step_interface=TestRunnerHooks(),
            test_parser_hooks=TestParserHooks(),
            test_id=test_id,
            test_type=test_type,
            test_parameters={test_param_name: test_param_value},
        )

    mock_run.assert_called_once()
    # parser_builder_config is the 1st parameter in WebSocketRunner.run
    parser_builder_config: TestParserBuilderConfig = mock_run.mock_calls[0].args[0]
    assert len(parser_builder_config.tests) == 1
    assert test_id in parser_builder_config.tests[0]
    parser_options = parser_builder_config.parser_config.config_override
    assert parser_options.get(test_param_name) is not None
    assert parser_options.get(test_param_name) == test_param_value

    # clean up:
    chip_tool._ChipTool__last_exec_id = None
    chip_tool._ChipTool__chip_tool_container = None


@pytest.mark.asyncio
async def test_run_test_with_endpoint_parameter() -> None:
    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_TOOL
    test_id = "TC_TEST_ID"
    test_param_name = "endpoint"
    test_param_value = 1
    fake_container = make_fake_container()

    with mock.patch.object(
        target=chip_tool, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=container_manager, attribute="get_container"
    ), mock.patch.object(
        target=container_manager, attribute="destroy"
    ), mock.patch.object(
        target=container_manager,
        attribute="create_container",
        return_value=fake_container,
    ), mock.patch.object(
        target=chip_tool, attribute="start_chip_server"
    ), mock.patch(
        target="app.chip_tool.chip_tool.WebSocketRunner.run",
        return_value=True,
    ) as mock_run:
        await chip_tool.start_container(test_type)

        await chip_tool.run_test(
            test_step_interface=TestRunnerHooks(),
            test_parser_hooks=TestParserHooks(),
            test_id=test_id,
            test_type=test_type,
            test_parameters={test_param_name: test_param_value},
        )

    mock_run.assert_called_once()
    # parser_builder_config is the 1st parameter in WebSocketRunner.run
    parser_builder_config: TestParserBuilderConfig = mock_run.mock_calls[0].args[0]
    assert len(parser_builder_config.tests) == 1
    assert test_id in parser_builder_config.tests[0]
    parser_options = parser_builder_config.parser_config.config_override
    assert parser_options[test_param_name] == test_param_value

    # clean up:
    chip_tool._ChipTool__last_exec_id = None
    chip_tool._ChipTool__chip_tool_container = None


@pytest.mark.asyncio
async def test_run_test_with_nodeID_and_cluster_parameters() -> None:
    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_TOOL
    test_id = "TC_TEST_ID"
    test_param_name = "endpoint"
    test_param_value = 1
    fake_container = make_fake_container()

    with mock.patch.object(
        target=chip_tool, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=container_manager, attribute="get_container"
    ), mock.patch.object(
        target=container_manager, attribute="destroy"
    ), mock.patch.object(
        target=container_manager,
        attribute="create_container",
        return_value=fake_container,
    ), mock.patch.object(
        target=chip_tool, attribute="start_chip_server"
    ), mock.patch(
        target="app.chip_tool.chip_tool.WebSocketRunner.run",
        return_value=True,
    ) as mock_run:
        await chip_tool.start_container(test_type)

        await chip_tool.run_test(
            test_step_interface=TestRunnerHooks(),
            test_parser_hooks=TestParserHooks(),
            test_id=test_id,
            test_type=test_type,
            test_parameters={
                test_param_name: test_param_value,
                "nodeId": "custom",
                "cluster": "custom",
            },
        )

    mock_run.assert_called_once()
    # parser_builder_config is the 1st parameter in WebSocketRunner.run
    parser_builder_config: TestParserBuilderConfig = mock_run.mock_calls[0].args[0]
    assert len(parser_builder_config.tests) == 1
    assert test_id in parser_builder_config.tests[0]
    parser_options = parser_builder_config.parser_config.config_override
    assert parser_options[test_param_name] == test_param_value
    assert parser_options.get("nodeId") != "custom"
    assert parser_options.get("cluster") != "custom"

    # clean up:
    chip_tool._ChipTool__last_exec_id = None
    chip_tool._ChipTool__chip_tool_container = None


@pytest.mark.asyncio
async def test_pairing_on_network_command_params() -> None:
    original_trace_setting_value = settings.CHIP_TOOL_TRACE
    if original_trace_setting_value is True:
        settings.CHIP_TOOL_TRACE = False

    # Attributes
    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_TOOL
    fake_container = make_fake_container()
    discriminator = "1234"
    setup_code = "0123456"

    with mock.patch.object(
        target=chip_tool, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=container_manager, attribute="get_container"
    ), mock.patch.object(
        target=container_manager, attribute="destroy"
    ), mock.patch.object(
        target=container_manager,
        attribute="create_container",
        return_value=fake_container,
    ), mock.patch.object(
        target=chip_tool, attribute="start_chip_server"
    ), mock.patch.object(
        target=chip_tool,
        attribute="send_websocket_command",
        return_value='{"results": []}',
    ) as mock_send_websocket_command:
        await chip_tool.start_container(test_type)

        # Send on-network pairing command
        result = await chip_tool.pairing_on_network(
            setup_code=setup_code,
            discriminator=discriminator,
        )

    expected_params = f"{hex(chip_tool.node_id)} {setup_code} {discriminator}"
    expected_command = f"pairing onnetwork-long {expected_params}"

    assert result is True
    mock_send_websocket_command.assert_awaited_once_with(expected_command)

    # clean up:
    chip_tool._ChipTool__chip_tool_container = None
    settings.CHIP_TOOL_TRACE = original_trace_setting_value


@pytest.mark.asyncio
async def test_pairing_ble_wifi_command_params() -> None:
    original_trace_setting_value = settings.CHIP_TOOL_TRACE
    if original_trace_setting_value is True:
        settings.CHIP_TOOL_TRACE = False

    # Attributes
    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_TOOL
    fake_container = make_fake_container()
    discriminator = "1234"
    setup_code = "0123456"
    ssid = "WifiIsGood"
    password = "WifiIsGoodAndSecret"

    with mock.patch.object(
        target=chip_tool, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=container_manager, attribute="get_container"
    ), mock.patch.object(
        target=container_manager, attribute="destroy"
    ), mock.patch.object(
        target=container_manager,
        attribute="create_container",
        return_value=fake_container,
    ), mock.patch.object(
        target=chip_tool, attribute="start_chip_server"
    ), mock.patch.object(
        target=chip_tool,
        attribute="send_websocket_command",
        return_value='{"results": []}',
    ) as mock_send_websocket_command:
        await chip_tool.start_container(test_type)

        # Send BLE-WIFI pairing command
        result = await chip_tool.pairing_ble_wifi(
            ssid=ssid,
            password=password,
            setup_code=setup_code,
            discriminator=discriminator,
        )

    expected_params = (
        f"{hex(chip_tool.node_id)} {ssid} {password} {setup_code} {discriminator}"
    )
    expected_command = f"pairing ble-wifi {expected_params}"

    assert result is True
    mock_send_websocket_command.assert_awaited_once_with(expected_command)

    # clean up:
    chip_tool._ChipTool__chip_tool_container = None
    settings.CHIP_TOOL_TRACE = original_trace_setting_value


@pytest.mark.asyncio
async def test_pairing_ble_thread_command_params() -> None:
    original_trace_setting_value = settings.CHIP_TOOL_TRACE
    if original_trace_setting_value is True:
        settings.CHIP_TOOL_TRACE = False

    # Attributes
    chip_tool = ChipTool()
    test_type = ChipToolTestType.CHIP_TOOL
    fake_container = make_fake_container()
    discriminator = "1234"
    hex_dataset = "c0ffee"
    setup_code = "0123456"

    with mock.patch.object(
        target=chip_tool, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=container_manager, attribute="get_container"
    ), mock.patch.object(
        target=container_manager, attribute="destroy"
    ), mock.patch.object(
        target=container_manager,
        attribute="create_container",
        return_value=fake_container,
    ), mock.patch.object(
        target=chip_tool, attribute="start_chip_server"
    ), mock.patch.object(
        target=chip_tool,
        attribute="send_websocket_command",
        return_value='{"results": []}',
        # '{  "results": [{ "error": "FAILURE" }]
    ) as mock_send_websocket_command:
        await chip_tool.start_container(test_type)

        # Send BLE-THREAD pairing command
        result = await chip_tool.pairing_ble_thread(
            hex_dataset=hex_dataset,
            setup_code=setup_code,
            discriminator=discriminator,
        )

    expected_params = (
        f"{hex(chip_tool.node_id)} hex:{hex_dataset} {setup_code} {discriminator}"
    )
    expected_command = f"pairing ble-thread {expected_params}"

    assert result is True
    mock_send_websocket_command.assert_awaited_once_with(expected_command)

    # clean up:
    chip_tool._ChipTool__chip_tool_container = None
    settings.CHIP_TOOL_TRACE = original_trace_setting_value
