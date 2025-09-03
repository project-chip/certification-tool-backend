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
from th_cli.exceptions import CLIError, handle_api_error


@click.command()
@click.option(
    "--id",
    "-i",
    required=True,
    type=int,
    help="Test Run Execution ID to fetch logs for",
)
def test_run_execution_log(id: int) -> None:
    """Print test execution log for a given test run execution ID"""
    try:
        with closing(get_client()) as client:
            sync_apis = SyncApis(client)
            __fetch_test_run_execution_log(sync_apis, id)
    except CLIError:
        raise  # Re-raise CLI Errors as-is


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
