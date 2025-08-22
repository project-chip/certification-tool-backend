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
from typing import Optional

import click

from th_cli.api_lib_autogen.api_client import SyncApis
from th_cli.api_lib_autogen.exceptions import UnexpectedResponse
from th_cli.client import get_client
from th_cli.exceptions import CLIError, handle_api_error
from th_cli.utils import __print_json

table_format = "{:<5} {:30} {:10} {:40}"


@click.command()
@click.option(
    "--id",
    "-i",
    default=None,
    required=False,
    type=int,
    help="Fetch specific Test Run via ID",
)
@click.option(
    "--skip",
    "-s",
    default=None,
    required=False,
    type=int,
    help="The first N Test Runs to skip, ordered by ID",
)
@click.option(
    "--limit",
    "-l",
    default=None,
    required=False,
    type=int,
    help="Maximun number of test runs to fetch",
)
@click.option(
    "--json",
    is_flag=True,
    help="Print JSON response for more details",
)
def test_run_execution_history(
    id: Optional[int], skip: Optional[int], limit: Optional[int], json: Optional[bool]
) -> None:
    """Read test run execution history"""

    try:
        client = get_client()
        sync_apis = SyncApis(client)
        if id is not None:
            __test_run_execution_by_id(sync_apis, id, json)
        elif skip is not None or limit is not None:
            __test_run_execution_batch(sync_apis, json, skip, limit)
        else:
            __test_run_execution_batch(sync_apis, json)
    except CLIError:
        raise  # Re-raise CLI Errors as-is
    finally:
        if client:
            client.close()


def __test_run_execution_by_id(sync_apis: SyncApis, id: int, json: bool) -> None:
    try:
        test_run_execution_api = sync_apis.test_run_executions_api
        test_run_execution = test_run_execution_api.read_test_run_execution_api_v1_test_run_executions_id_get(id=id)
        if json:
            __print_json(test_run_execution)
        else:
            __print_table_test_execution(test_run_execution.dict())
    except UnexpectedResponse as e:
        handle_api_error(e, "create test run execution")


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
        handle_api_error(e, "create test run execution")


def __print_table_test_executions(test_execution: list) -> None:
    __print_table_header()
    if isinstance(test_execution, list):
        for item_dict in test_execution:
            __print_table_test_execution(item_dict.dict(), print_header=False)


def __print_table_test_execution(item: dict, print_header=True) -> None:
    print_header and __print_table_header()
    click.echo(
        table_format.format(item.get("id"), item.get("title"), (item.get("state")).name, item.get("error", "No Error"))
    )


def __print_table_header() -> None:
    click.echo(table_format.format("ID", "Title", "State", "Error"))
