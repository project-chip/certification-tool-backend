#
# Copyright (c) 2025 Project CHIP Authors
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
from typing import Optional

import api_lib_autogen.models as m
import click
import test_run.logging as test_logging
from api_lib_autogen.api_client import AsyncApis
from api_lib_autogen.exceptions import UnexpectedResponse
from async_cmd import async_cmd
from click.exceptions import Exit
from client import client
from test_run.websocket import TestRunSocket
from utils import (
    build_test_selection,
    convert_nested_to_dict,
    merge_properties_to_config,
    read_pics_config,
    read_properties_file,
)

async_apis = AsyncApis(client)
test_run_executions_api = async_apis.test_run_executions_api
test_collections_api = async_apis.test_collections_api
projects_api = async_apis.projects_api


@click.command()
@click.option(
    "--title",
    default=lambda: str(datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")),
    show_default="timestamp",
)
@click.option(
    "--config",
    "-c",
    help="Property config file location. This "
    "information is optional — if not provided, the default_config.properties "
    "file will be used.",
)
@click.option(
    "--tests-list",
    required=True,
    help="List of test cases to execute. For example: TC-ACE-1.1,TC_ACE_1_3",
)
@click.option(
    "--pics-config-folder",
    "-p",
    help="Directory containing PICS XML configuration files. If not provided, no PICS will be used.",
)
@async_cmd
async def run_tests_cli(title: str, config: str, tests_list: str, pics_config_folder: str = None) -> None:
    """Simplified CLI execution of a test run from selected tests"""

    # Configure new log output for test.
    log_path = test_logging.configure_logger_for_run(title=title)

    # Get default config and convert to dict
    default_config = await projects_api.default_config_api_v1_projects_default_config_get()
    default_config_dict = convert_nested_to_dict(default_config)

    # If config file is provided, read and parse it
    if not config:
        config = "default_config.properties"

    config_data = read_properties_file(config)
    click.echo(f"Read config from file: {config_data}")
    cli_config_dict = merge_properties_to_config(config_data, default_config_dict)
    click.echo(f"CLI Config for test run execution: {cli_config_dict}")

    # Read PICS configuration if provided
    pics = read_pics_config(pics_config_folder)
    click.echo(f"PICS Used: {json.dumps(pics, indent=2)}")

    try:
        # Convert each test separeted by comma to a list
        tests_list = [test for test in tests_list.split(",")]
        test_collections = await test_collections_api.read_test_collections_api_v1_test_collections_get()
        selected_tests_dict = build_test_selection(test_collections, tests_list)

        click.echo(f"Selected tests: {json.dumps(selected_tests_dict, indent=2)}")
        new_test_run = await __create_new_test_run_cli(
            selected_tests=selected_tests_dict, title=title, config=cli_config_dict, pics=pics
        )
        socket = TestRunSocket(new_test_run)
        socket_task = asyncio.create_task(socket.connect_websocket())
        new_test_run = await __start_test_run(new_test_run)
        socket.run = new_test_run
        await socket_task
        click.echo(f"Log output in: '{log_path}'")
    finally:
        await client.aclose()


async def __create_new_test_run_cli(
    selected_tests: dict, title: str, config: Optional[dict] = None, pics: Optional[dict] = None
) -> m.TestRunExecutionWithChildren:
    click.echo(f"Creating new test run with title: {title}")

    test_run_in = m.TestRunExecutionCreate(title=title)
    json_body = m.BodyCreateTestRunExecutionCliApiV1TestRunExecutionsCliPost(
        test_run_execution_in=test_run_in, selected_tests=selected_tests, config=config, pics=pics
    )

    try:
        return await test_run_executions_api.create_test_run_execution_cli_api_v1_test_run_executions_cli_post(
            json_body
        )
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
