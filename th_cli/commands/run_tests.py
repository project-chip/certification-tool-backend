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

import click

import th_cli.api_lib_autogen.models as m
import th_cli.test_run.logging as test_logging
from th_cli.api_lib_autogen.api_client import AsyncApis
from th_cli.api_lib_autogen.exceptions import UnexpectedResponse
from th_cli.async_cmd import async_cmd
from th_cli.client import get_client
from th_cli.colorize import (
    colorize_cmd_help,
    colorize_header,
    colorize_help,
    colorize_key_value,
    italic,
    set_colors_enabled,
)
from th_cli.exceptions import CLIError, handle_api_error
from th_cli.test_run.websocket import TestRunSocket
from th_cli.utils import (
    build_test_selection,
    convert_nested_to_dict,
    merge_properties_to_config,
    read_pics_config,
    read_properties_file,
)
from th_cli.validation import validate_directory_path, validate_file_path, validate_test_ids


@click.command(
    no_args_is_help=True,
    short_help=colorize_help("CLI execution of a test run"),
    help=colorize_cmd_help("run_tests", "CLI execution of a test run from selected tests"),
)
@click.option(
    "--tests-list",
    "-t",
    required=True,
    help=colorize_help("List of test cases to execute. For example: TC-ACE-1.1,TC_ACE_1_3"),
)
@click.option(
    "--title",
    "-n",
    default=lambda: str(datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")),
    show_default="timestamp",
    help=colorize_help("Name of the test run execution"),
)
@click.option(
    "--config",
    "-c",
    type=click.Path(file_okay=True, dir_okay=False),
    help=colorize_help(
        "Property config file location. This "
        "information is optional — if not provided, the default_config.properties "
        "file will be used."
    ),
)
@click.option(
    "--pics-config-folder",
    "-p",
    type=click.Path(file_okay=False, dir_okay=True),
    help=colorize_help("Directory containing PICS XML configuration files. If not provided, no PICS will be used."),
)
@click.option(
    "--project-id",
    type=int,
    help=colorize_help(
        "Project ID that this test run belongs to. " "If not provided, uses the default 'CLI Execution Project' in TH."
    ),
)
@click.option(
    "--no-color",
    is_flag=True,
    help=colorize_help("Disable colored output for test execution status."),
)
@async_cmd
async def run_tests(
    title: str,
    tests_list: str,
    config: str = None,
    pics_config_folder: str = None,
    project_id: int = None,
    no_color: bool = False,
) -> None:
    """CLI execution of a test run from selected tests"""

    # Set color preference if specified
    if no_color:
        set_colors_enabled(False)

    # Validate inputs and convert each test separated by comma to a list
    validated_test_ids = validate_test_ids(tests_list)

    if config:
        config_path = validate_file_path(config, must_exist=True)
        config = str(config_path)

    if pics_config_folder:
        pics_path = validate_directory_path(pics_config_folder, must_exist=True)
        pics_config_folder = str(pics_path)

    client = None
    try:
        client = get_client()
        async_apis = AsyncApis(client)
        projects_api = async_apis.projects_api
        test_collections_api = async_apis.test_collections_api

        # Configure new log output for test.
        log_path = test_logging.configure_logger_for_run(title=title)

        # Get default config and convert to dict
        default_config = await projects_api.default_config_api_v1_projects_default_config_get()
        default_config_dict = convert_nested_to_dict(default_config)

        # If config file is provided, read and parse it
        if not config:
            config = "default_config.properties"

        config_data = read_properties_file(config)
        click.echo(colorize_key_value("Read config from file", config_data))
        cli_config_dict = merge_properties_to_config(config_data, default_config_dict)
        click.echo(colorize_key_value("CLI Config for test run execution", cli_config_dict))

        # Read PICS configuration if provided
        pics = read_pics_config(pics_config_folder)
        click.echo(colorize_key_value("PICS Used", json.dumps(pics, indent=2)))

        # Retrieve available test collections to build test selection
        test_collections = await test_collections_api.read_test_collections_api_v1_test_collections_get()
        selected_tests_dict = build_test_selection(test_collections, validated_test_ids)

        click.echo(colorize_key_value("Selected tests", json.dumps(selected_tests_dict, indent=2)))

        new_test_run = await __create_new_test_run_cli(
            async_apis,
            selected_tests=selected_tests_dict,
            title=title,
            config=cli_config_dict,
            pics=pics,
            project_id=project_id,
        )
        socket = TestRunSocket(new_test_run)
        socket_task = asyncio.create_task(socket.connect_websocket())
        new_test_run = await __start_test_run(async_apis, new_test_run)
        socket.run = new_test_run
        await socket_task
        click.echo(colorize_key_value("Log output in", italic(log_path)))
    except CLIError:
        raise  # Re-raise CLI errors
    except Exception as e:
        raise CLIError(f"Unexpected error during test execution: {e}")
    finally:
        if client:
            await client.aclose()


async def __create_new_test_run_cli(
    async_apis: AsyncApis,
    selected_tests: dict,
    title: str,
    config: Optional[dict] = None,
    pics: Optional[dict] = None,
    project_id: Optional[int] = None,
) -> m.TestRunExecutionWithChildren:
    click.echo(colorize_key_value("Creating new test run with title", title))

    test_run_in = m.TestRunExecutionCreate(title=title, project_id=project_id)
    json_body = m.BodyCreateTestRunExecutionCliApiV1TestRunExecutionsCliPost(
        test_run_execution_in=test_run_in, selected_tests=selected_tests, config=config, pics=pics
    )

    try:
        test_run_executions_api = async_apis.test_run_executions_api
        return await test_run_executions_api.create_test_run_execution_cli_api_v1_test_run_executions_cli_post(
            json_body
        )
    except UnexpectedResponse as e:
        handle_api_error(e, "create test run execution")


async def __start_test_run(
    async_apis: AsyncApis, test_run: m.TestRunExecutionWithChildren
) -> m.TestRunExecutionWithChildren:
    header = colorize_header("Starting Test run")
    title = colorize_key_value("Title", test_run.title)
    id = colorize_key_value("ID", str(test_run.id))

    click.echo("")
    click.echo(f"{header}:\n- {title}\n- {id}\n")

    try:
        test_run_executions_api = async_apis.test_run_executions_api
        return await test_run_executions_api.start_test_run_execution_api_v1_test_run_executions_id_start_post(
            id=test_run.id
        )
    except UnexpectedResponse as e:
        handle_api_error(e, "start test run")
