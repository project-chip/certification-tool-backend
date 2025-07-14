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

import api_lib_autogen.models as m
import click
import test_run.logging as test_logging
from api_lib_autogen.api_client import AsyncApis
from api_lib_autogen.exceptions import UnexpectedResponse
from async_cmd import async_cmd
from click.exceptions import Exit
from client import client
from test_run.websocket import TestRunSocket
from utils import build_test_selection

async_apis = AsyncApis(client)
test_run_executions_api = async_apis.test_run_executions_api
test_collections_api = async_apis.test_collections_api


@click.command()
@click.option(
    "--selected-tests",
    "-s",
    help="JSON string with selected tests. "
    'Format: \'{"collection_name":{"test_suite_id":{"test_case_id": <iterations>}}}\' '
    'For instance: \'{"SDK YAML Tests":{"FirstChipToolSuite":{"TC-ACE-1.1": 1}}}\'',
)
@click.option(
    "--title", default=lambda: str(datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")), show_default="timestamp"
)
@click.option("--file", "-f", help="JSON file location")
@click.option(
    "--project-id",
    required=True,
    help="Project ID that this test run belongs to",
)
@click.option(
    "--tests-list",
    help="List of test cases to execute. Separated by commas (,) and without any blank spaces. "
    "For example: TC-ACE-1.1,TC_ACE_1_3",
)
@async_cmd
async def run_tests(selected_tests: str, title: str, file: str, project_id: int, tests_list: str = None) -> None:
    """Create a new test run from selected tests"""

    # Configure new log output for test.
    log_path = test_logging.configure_logger_for_run(title=title)

    try:
        # Check if tests_list is provided
        if tests_list:
            # Convert each test separeted by comma to a list
            tests_list = [test for test in tests_list.split(",")]
            test_collections = await test_collections_api.read_test_collections_api_v1_test_collections_get()
            selected_tests_dict = build_test_selection(test_collections, tests_list)
        else:
            selected_tests_dict = __parse_selected_tests(selected_tests, file)

        click.echo(f"Selected tests: {json.dumps(selected_tests_dict, indent=2)}")
        new_test_run = await __create_new_test_run(
            selected_tests=selected_tests_dict, title=title, project_id=project_id
        )
        socket = TestRunSocket(new_test_run)
        socket_task = asyncio.create_task(socket.connect_websocket())
        new_test_run = await __start_test_run(new_test_run)
        socket.run = new_test_run
        await socket_task
        click.echo(f"Log output in: '{log_path}'")
    finally:
        await client.aclose()


async def __create_new_test_run(selected_tests: dict, title: str, project_id: int) -> None:
    click.echo(f"Creating new test run with title: {title}")

    test_run_in = m.TestRunExecutionCreate(title=title, project_id=project_id)
    json_body = m.BodyCreateTestRunExecutionApiV1TestRunExecutionsPost(
        test_run_execution_in=test_run_in, selected_tests=selected_tests
    )

    try:
        return await test_run_executions_api.create_test_run_execution_api_v1_test_run_executions_post(json_body)
    except UnexpectedResponse as e:
        click.echo(f"Create test run execution failed {e.status_code}: {e.content}")
        raise Exit(code=1)


async def __start_test_run(test_run: m.TestRunExecutionWithChildren) -> m.TestRunExecutionWithChildren:
    click.echo(f"Starting Test run: Title: {test_run.title}, id: {test_run.id}")
    try:
        return await test_run_executions_api.start_test_run_execution_api_v1_test_run_executions_id_start_post(
            id=test_run.id
        )
    except UnexpectedResponse as e:
        click.echo(f"Failed to start test run: {e.status_code} {e.content}", err=True)
        raise Exit(code=1)


def __parse_selected_tests(json_str: str, filename: str) -> dict:
    try:
        if filename:
            json_file = open(filename, "r")
            json_str = json_file.read()
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        click.echo(f"Failed to parse JSON parameter: {e.msg}")
        raise Exit(code=1)
    except FileNotFoundError as e:
        click.echo(f"File not found: {e.filename} {e.strerror}.")
        raise Exit(code=1)
