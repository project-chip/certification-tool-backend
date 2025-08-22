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
import asyncio
import datetime
import json

import click

import th_cli.api_lib_autogen.models as m
import th_cli.test_run.logging as test_logging
from th_cli.api_lib_autogen.api_client import AsyncApis
from th_cli.api_lib_autogen.exceptions import UnexpectedResponse
from th_cli.async_cmd import async_cmd
from th_cli.client import get_client
from th_cli.exceptions import CLIError, handle_api_error, handle_file_error
from th_cli.test_run.websocket import TestRunSocket
from th_cli.utils import build_test_selection
from th_cli.validation import validate_file_path, validate_test_ids


@click.command(no_args_is_help=True)
@click.option(
    "--project-id",
    "-i",
    required=True,
    help="Project ID that this test run belongs to",
)
@click.option(
    "--title",
    "-n",
    help="Name of the test run execution",
    default=lambda: str(datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")),
    show_default="timestamp",
)
@click.option(
    "--tests-list",
    "-t",
    help="List of test cases to execute. Separated by commas (,) and without any blank spaces. "
    "For example: TC-ACE-1.1,TC_ACE_1_3",
)
@click.option(
    "--selected-tests",
    "-s",
    help="JSON string with selected tests. "
    'Format: \'{"collection_name":{"test_suite_id":{"test_case_id": <iterations>}}}\' '
    'For example: \'{"SDK YAML Tests":{"FirstChipToolSuite":{"TC-ACE-1.1": 1}}}\'',
)
@click.option("--file", "-f", help="JSON file location")
@async_cmd
async def run_tests(selected_tests: str, title: str, file: str, project_id: int, tests_list: str = None) -> None:
    """Create a new test run from selected tests"""

    # Configure new log output for test.
    log_path = test_logging.configure_logger_for_run(title=title)

    try:
        client = get_client()
        async_apis = AsyncApis(client)
        test_collections_api = async_apis.test_collections_api

        # Check if tests_list is provided
        if tests_list:
            validated_test_ids = validate_test_ids(tests_list)  # Validate and convert test list
            test_collections = await test_collections_api.read_test_collections_api_v1_test_collections_get()
            selected_tests_dict = build_test_selection(test_collections, validated_test_ids)
        else:
            selected_tests_dict = __parse_selected_tests(selected_tests, file)

        click.echo(f"Selected tests: {json.dumps(selected_tests_dict, indent=2)}")
        new_test_run = await __create_new_test_run(
            async_apis=async_apis, selected_tests=selected_tests_dict, title=title, project_id=project_id
        )
        socket = TestRunSocket(new_test_run)
        socket_task = asyncio.create_task(socket.connect_websocket())
        new_test_run = await __start_test_run(async_apis, new_test_run)
        socket.run = new_test_run
        await socket_task
        click.echo(f"Log output in: '{log_path}'")
    except UnexpectedResponse as e:
        handle_api_error(e, "run test execution")
    finally:
        await client.aclose()


async def __create_new_test_run(async_apis: AsyncApis, selected_tests: dict, title: str, project_id: int) -> None:
    click.echo(f"Creating new test run with title: {title}")

    test_run_in = m.TestRunExecutionCreate(title=title, project_id=project_id)
    json_body = m.BodyCreateTestRunExecutionApiV1TestRunExecutionsPost(
        test_run_execution_in=test_run_in, selected_tests=selected_tests
    )

    try:
        test_run_executions_api = async_apis.test_run_executions_api
        return await test_run_executions_api.create_test_run_execution_api_v1_test_run_executions_post(json_body)
    except UnexpectedResponse as e:
        handle_api_error(e, "create test run execution")


async def __start_test_run(
    async_apis: AsyncApis, test_run: m.TestRunExecutionWithChildren
) -> m.TestRunExecutionWithChildren:
    click.echo(f"Starting Test run: Title: {test_run.title}, id: {test_run.id}")

    try:
        test_run_executions_api = async_apis.test_run_executions_api
        return await test_run_executions_api.start_test_run_execution_api_v1_test_run_executions_id_start_post(
            id=test_run.id
        )
    except UnexpectedResponse as e:
        handle_api_error(e, "start test run execution")


def __parse_selected_tests(json_str: str, filename: str) -> dict:
    try:
        if filename:
            validated_filename = validate_file_path(filename, must_exist=True)
            filename = str(validated_filename)
            json_file = open(filename, "r")
            json_str = json_file.read()
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise CLIError(f"Failed to parse JSON parameter: {e.msg}")
    except FileNotFoundError as e:
        handle_file_error(e, "json file")
