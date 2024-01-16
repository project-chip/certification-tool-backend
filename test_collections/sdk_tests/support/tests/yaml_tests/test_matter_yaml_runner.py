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

from subprocess import CompletedProcess
from unittest import mock

import pytest
from matter_yamltests.hooks import TestParserHooks, TestRunnerHooks
from matter_yamltests.parser_builder import TestParserBuilderConfig
from matter_yamltests.runner import TestRunnerConfig
from matter_yamltests.websocket_runner import WebSocketRunner, WebSocketRunnerConfig

from app.core.config import settings
from app.schemas.pics import PICSError
from app.tests.utils.test_pics_data import create_random_pics
from test_collections.sdk_tests.support.chip.chip_server import (
    ChipServer,
    ChipServerType,
)
from test_collections.sdk_tests.support.pics import (
    PICS_FILE_PATH,
    SHELL_OPTION,
    SHELL_PATH,
)
from test_collections.sdk_tests.support.yaml_tests.matter_yaml_runner import (
    TEST_DEFAULT_TIMEOUT_IN_SEC,
    TEST_RUNNER_OPTIONS,
    MatterYAMLRunner,
)


@pytest.mark.asyncio
async def test_setup() -> None:
    runner: MatterYAMLRunner = MatterYAMLRunner()
    chip_server: ChipServer = ChipServer()
    test_type = ChipServerType.CHIP_TOOL

    with mock.patch(
        target="test_collections.sdk_tests.support.yaml_tests.matter_yaml_runner"
        ".backend_container"
    ), mock.patch.object(target=chip_server, attribute="start") as mock_start:
        await runner.setup(test_type, False)

    mock_start.assert_awaited_once_with(test_type, False)
    assert runner._MatterYAMLRunner__test_harness_runner is not None

    # clean up:
    runner._MatterYAMLRunner__test_harness_runner = None
    runner._MatterYAMLRunner__chip_tool_log = None


@pytest.mark.asyncio
async def test_setup_using_paa_certs() -> None:
    runner: MatterYAMLRunner = MatterYAMLRunner()
    chip_server: ChipServer = ChipServer()
    test_type = ChipServerType.CHIP_TOOL

    with mock.patch(
        target="test_collections.sdk_tests.support.yaml_tests.matter_yaml_runner"
        ".backend_container"
    ), mock.patch.object(target=chip_server, attribute="start") as mock_start:
        await runner.setup(test_type, use_paa_certs=True)

    mock_start.assert_awaited_once_with(test_type, True)
    assert runner._MatterYAMLRunner__test_harness_runner is not None

    # clean up:
    runner._MatterYAMLRunner__test_harness_runner = None
    runner._MatterYAMLRunner__chip_tool_log = None


@pytest.mark.asyncio
async def test_set_pics() -> None:
    runner: MatterYAMLRunner = MatterYAMLRunner()
    pics = create_random_pics()

    # expected PICS = PICS from create_random_pics() + \n + DEFAULT PICS
    expected_pics_data = (
        "AB.C=1\nAB.C.A0004=1\nXY.C=0\nAB.S.C0003=1\n"
        "PICS_SDK_CI_ONLY=0\nPICS_SKIP_SAMPLE_APP=1\n"
        "PICS_USER_PROMPT=1"
    )
    expected_command = (
        f"{SHELL_PATH} {SHELL_OPTION} \"echo '{expected_pics_data}' "
        f'> {PICS_FILE_PATH}"'
    )

    with mock.patch(
        target="test_collections.sdk_tests.support.yaml_tests.matter_yaml_runner"
        ".subprocess.run",
        return_value=CompletedProcess(expected_command, 0),
    ) as mock_run:
        runner.set_pics(pics)

    mock_run.assert_called_once_with(expected_command, shell=True)
    assert runner._MatterYAMLRunner__pics_file_created is True

    # clean up:
    runner._MatterYAMLRunner__pics_file_created = False
    runner._MatterYAMLRunner__last_exec_id = None
    runner._MatterYAMLRunner__chip_tool_container = None


def test_set_pics_with_error() -> None:
    runner: MatterYAMLRunner = MatterYAMLRunner()
    pics = create_random_pics()

    with mock.patch(
        target="test_collections.sdk_tests.support.yaml_tests.matter_yaml_runner"
        ".subprocess.run",
        return_value=CompletedProcess("", 1),
    ), pytest.raises(PICSError):
        runner.set_pics(pics)
        assert runner._MatterYAMLRunner__pics_file_created is False


@pytest.mark.asyncio
async def test_run_test_default_config() -> None:
    runner: MatterYAMLRunner = MatterYAMLRunner()
    chip_server: ChipServer = ChipServer()
    test_type = ChipServerType.CHIP_TOOL
    test_id = "TC_TEST_ID"
    runner._MatterYAMLRunner__test_harness_runner = WebSocketRunner(
        WebSocketRunnerConfig()
    )
    runner._MatterYAMLRunner__server_started = True

    with mock.patch(
        target="test_collections.sdk_tests.support.yaml_tests.matter_yaml_runner"
        ".WebSocketRunner.is_connected",
        new_callable=mock.PropertyMock,
        return_value=True,
    ), mock.patch(
        target="test_collections.sdk_tests.support.yaml_tests.matter_yaml_runner"
        ".WebSocketRunner.run",
        return_value=True,
    ) as mock_run:
        await runner.run_test(
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
    assert parser_options["nodeId"] == f"{hex(chip_server.node_id)}"
    assert parser_options["timeout"] == f"{TEST_DEFAULT_TIMEOUT_IN_SEC}"
    # runner_config is the 2nd parameter in WebSocketRunner.run
    runner_config: TestRunnerConfig = mock_run.mock_calls[0].args[1]
    assert runner_config.options is TEST_RUNNER_OPTIONS
    assert runner_config.auto_start_stop is False

    # clean up:
    runner._MatterYAMLRunner__server_started = False
    chip_server._ChipServer__node_id = None


@pytest.mark.asyncio
async def test_run_test_custom_timeout() -> None:
    runner: MatterYAMLRunner = MatterYAMLRunner()
    test_type = ChipServerType.CHIP_TOOL
    test_id = "TC_TEST_ID"
    test_timeout = "10"
    runner._MatterYAMLRunner__test_harness_runner = WebSocketRunner(
        WebSocketRunnerConfig()
    )
    runner._MatterYAMLRunner__server_started = True

    with mock.patch(
        target="test_collections.sdk_tests.support.yaml_tests.matter_yaml_runner"
        ".WebSocketRunner.is_connected",
        new_callable=mock.PropertyMock,
        return_value=True,
    ), mock.patch(
        target="test_collections.sdk_tests.support.yaml_tests.matter_yaml_runner"
        ".WebSocketRunner.run",
        return_value=True,
    ) as mock_run:
        await runner.run_test(
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
    runner._MatterYAMLRunner__server_started = False


@pytest.mark.asyncio
async def test_run_test_with_custom_parameter() -> None:
    runner: MatterYAMLRunner = MatterYAMLRunner()
    test_type = ChipServerType.CHIP_TOOL
    test_id = "TC_TEST_ID"
    test_param_name = "param1"
    test_param_value = "value"
    runner._MatterYAMLRunner__test_harness_runner = WebSocketRunner(
        WebSocketRunnerConfig()
    )
    runner._MatterYAMLRunner__server_started = True

    with mock.patch(
        target="test_collections.sdk_tests.support.yaml_tests.matter_yaml_runner"
        ".WebSocketRunner.is_connected",
        new_callable=mock.PropertyMock,
        return_value=True,
    ), mock.patch(
        target="test_collections.sdk_tests.support.yaml_tests.matter_yaml_runner"
        ".WebSocketRunner.run",
        return_value=True,
    ) as mock_run:
        await runner.run_test(
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
    runner._MatterYAMLRunner__server_started = False


@pytest.mark.asyncio
async def test_run_test_with_endpoint_parameter() -> None:
    runner: MatterYAMLRunner = MatterYAMLRunner()
    test_type = ChipServerType.CHIP_TOOL
    test_id = "TC_TEST_ID"
    test_param_name = "endpoint"
    test_param_value = 1
    runner._MatterYAMLRunner__test_harness_runner = WebSocketRunner(
        WebSocketRunnerConfig()
    )
    runner._MatterYAMLRunner__server_started = True

    with mock.patch(
        target="test_collections.sdk_tests.support.yaml_tests.matter_yaml_runner"
        ".WebSocketRunner.is_connected",
        new_callable=mock.PropertyMock,
        return_value=True,
    ), mock.patch(
        target="test_collections.sdk_tests.support.yaml_tests.matter_yaml_runner"
        ".WebSocketRunner.run",
        return_value=True,
    ) as mock_run:
        await runner.run_test(
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
    runner._MatterYAMLRunner__server_started = False


@pytest.mark.asyncio
async def test_run_test_with_nodeID_and_cluster_parameters() -> None:
    runner: MatterYAMLRunner = MatterYAMLRunner()
    test_type = ChipServerType.CHIP_TOOL
    test_id = "TC_TEST_ID"
    test_param_name = "endpoint"
    test_param_value = 1
    runner._MatterYAMLRunner__test_harness_runner = WebSocketRunner(
        WebSocketRunnerConfig()
    )
    runner._MatterYAMLRunner__server_started = True

    with mock.patch(
        target="test_collections.sdk_tests.support.yaml_tests.matter_yaml_runner"
        ".WebSocketRunner.is_connected",
        new_callable=mock.PropertyMock,
        return_value=True,
    ), mock.patch(
        target="test_collections.sdk_tests.support.yaml_tests.matter_yaml_runner"
        ".WebSocketRunner.run",
        return_value=True,
    ) as mock_run:
        await runner.run_test(
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
    runner._MatterYAMLRunner__server_started = False


@pytest.mark.asyncio
async def test_pairing_on_network_command_params() -> None:
    original_trace_setting_value = settings.CHIP_TOOL_TRACE
    if original_trace_setting_value is True:
        settings.CHIP_TOOL_TRACE = False

    # Attributes
    runner: MatterYAMLRunner = MatterYAMLRunner()
    chip_server: ChipServer = ChipServer()
    discriminator = "1234"
    setup_code = "0123456"

    with mock.patch.object(
        target=runner,
        attribute="send_websocket_command",
        return_value='{"results": []}',
    ) as mock_send_websocket_command:
        result = await runner.pairing_on_network(
            setup_code=setup_code,
            discriminator=discriminator,
        )

    expected_params = f"{hex(chip_server.node_id)} {setup_code} {discriminator}"
    expected_command = f"pairing onnetwork-long {expected_params}"

    assert result is True
    mock_send_websocket_command.assert_awaited_once_with(expected_command)

    # clean up:
    settings.CHIP_TOOL_TRACE = original_trace_setting_value
    chip_server._ChipServer__node_id = None


@pytest.mark.asyncio
async def test_pairing_ble_wifi_command_params() -> None:
    original_trace_setting_value = settings.CHIP_TOOL_TRACE
    if original_trace_setting_value is True:
        settings.CHIP_TOOL_TRACE = False

    # Attributes
    runner: MatterYAMLRunner = MatterYAMLRunner()
    chip_server: ChipServer = ChipServer()
    discriminator = "1234"
    setup_code = "0123456"
    ssid = "WifiIsGood"
    password = "WifiIsGoodAndSecret"

    with mock.patch.object(
        target=runner,
        attribute="send_websocket_command",
        return_value='{"results": []}',
    ) as mock_send_websocket_command:
        result = await runner.pairing_ble_wifi(
            ssid=ssid,
            password=password,
            setup_code=setup_code,
            discriminator=discriminator,
        )

    expected_params = (
        f"{hex(chip_server.node_id)} {ssid} {password} {setup_code} {discriminator}"
    )
    expected_command = f"pairing ble-wifi {expected_params}"

    assert result is True
    mock_send_websocket_command.assert_awaited_once_with(expected_command)

    # clean up:
    settings.CHIP_TOOL_TRACE = original_trace_setting_value
    chip_server._ChipServer__node_id = None


@pytest.mark.asyncio
async def test_pairing_ble_thread_command_params() -> None:
    original_trace_setting_value = settings.CHIP_TOOL_TRACE
    if original_trace_setting_value is True:
        settings.CHIP_TOOL_TRACE = False

    # Attributes
    runner: MatterYAMLRunner = MatterYAMLRunner()
    chip_server: ChipServer = ChipServer()
    discriminator = "1234"
    hex_dataset = "c0ffee"
    setup_code = "0123456"

    with mock.patch.object(
        target=runner,
        attribute="send_websocket_command",
        return_value='{"results": []}',
        # '{  "results": [{ "error": "FAILURE" }]
    ) as mock_send_websocket_command:
        result = await runner.pairing_ble_thread(
            hex_dataset=hex_dataset,
            setup_code=setup_code,
            discriminator=discriminator,
        )

    expected_params = (
        f"{hex(chip_server.node_id)} hex:{hex_dataset} {setup_code} {discriminator}"
    )
    expected_command = f"pairing ble-thread {expected_params}"

    assert result is True
    mock_send_websocket_command.assert_awaited_once_with(expected_command)

    # clean up:
    settings.CHIP_TOOL_TRACE = original_trace_setting_value
    chip_server._ChipServer__node_id = None
