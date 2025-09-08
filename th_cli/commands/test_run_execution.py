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
from contextlib import closing
from typing import Optional

import click

from th_cli.api_lib_autogen.api_client import SyncApis
from th_cli.api_lib_autogen.exceptions import UnexpectedResponse
from th_cli.client import get_client
from th_cli.colorize import colorize_cmd_help, colorize_header, colorize_help, colorize_state, italic
from th_cli.exceptions import CLIError, handle_api_error
from th_cli.utils import __print_json

table_format_header = "{:<5} {:47} {:12} {:8}"
table_format = "{:<5} {:55} {:25} {}"


@click.command(
    short_help=colorize_help("Manage test run executions"),
    help=colorize_cmd_help(
        "test_run_execution", "List test run execution history or fetch logs for a specific execution"
    ),
)
@click.option(
    "--id",
    "-i",
    default=None,
    required=False,
    type=int,
    help=colorize_help("Fetch specific Test Run via ID"),
)
@click.option(
    "--skip",
    "-s",
    default=None,
    required=False,
    type=int,
    help=colorize_help("The first N Test Runs to skip, ordered by ID"),
)
@click.option(
    "--limit",
    "-l",
    default=None,
    required=False,
    type=int,
    help=colorize_help("Maximum number of test runs to fetch"),
)
@click.option(
    "--log",
    is_flag=True,
    default=False,
    help=colorize_help("Fetch log content for the specified test run execution ID (requires --id)"),
)
@click.option(
    "--json",
    is_flag=True,
    default=False,
    help=colorize_help("Print JSON response for more details (not applicable with --log)"),
)
def test_run_execution(id: Optional[int], skip: Optional[int], limit: Optional[int], log: bool, json: bool) -> None:
    """Manage test run executions - list history or fetch logs"""

    # Validate options
    if log and (skip is not None or limit is not None):
        raise click.ClickException("--skip and --limit options are not applicable when fetching logs (--log)")

    if log and id is None:
        raise click.ClickException("--log requires --id to specify which test run execution to fetch logs for")

    if log and json:
        raise click.ClickException("--json option is not applicable when fetching logs (--log)")

    try:
        with closing(get_client()) as client:
            sync_apis = SyncApis(client)

            if log:
                __fetch_test_run_execution_log(sync_apis, id)
            elif id is not None:
                __test_run_execution_by_id(sync_apis, id, json)
            else:
                __test_run_execution_batch(sync_apis, json, skip, limit)

    except CLIError:
        raise  # Re-raise CLI Errors as-is


def __test_run_execution_by_id(sync_apis: SyncApis, id: int, json: bool) -> None:
    try:
        test_run_execution_api = sync_apis.test_run_executions_api
        test_run_execution = test_run_execution_api.read_test_run_execution_api_v1_test_run_executions_id_get(id=id)
        if json:
            __print_json(test_run_execution)
        else:
            __print_table_test_execution(test_run_execution.dict())
    except UnexpectedResponse as e:
        handle_api_error(e, "get test run execution")


def __test_run_execution_batch(
    sync_apis: SyncApis, json: Optional[bool], skip: Optional[int] = None, limit: Optional[int] = None
) -> None:
    try:
        test_run_execution_api = sync_apis.test_run_executions_api
        test_run_executions = test_run_execution_api.read_test_run_executions_api_v1_test_run_executions_get(
            skip=skip, limit=limit
        )
        if json:
            __print_json(test_run_executions)
        else:
            __print_table_test_executions(test_run_executions)
    except UnexpectedResponse as e:
        handle_api_error(e, "get test run executions")


def __fetch_test_run_execution_log(sync_apis: SyncApis, id: int) -> None:
    try:
        test_run_execution_api = sync_apis.test_run_executions_api
        log_content = test_run_execution_api.download_log_api_v1_test_run_executions_id_log_get(
            id=id, json_entries=False, download=False
        )

        if log_content:
            click.echo(log_content)
        else:
            click.echo("No log content available for this test run execution.")

    except UnexpectedResponse as e:
        handle_api_error(e, "fetch test run execution log")


def __print_table_test_executions(test_execution: list) -> None:
    __print_table_header()
    if isinstance(test_execution, list):
        for item_dict in test_execution:
            __print_table_test_execution(item_dict.dict(), print_header=False)


def __print_table_test_execution(item: dict, print_header=True) -> None:
    print_header and __print_table_header()
    click.echo(
        table_format.format(
            item.get("id"),
            italic(item.get("title")),
            colorize_state((item.get("state")).value),
            item.get("error", "No Error"),
        )
    )


def __print_table_header() -> None:
    click.echo(colorize_header(table_format_header.format("ID", "Title", "State", "Error")))
