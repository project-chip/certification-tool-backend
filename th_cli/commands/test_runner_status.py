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
from typing import Optional

import click

from th_cli.api_lib_autogen.api_client import SyncApis
from th_cli.client import get_client
from th_cli.colorize import colorize_cmd_help, colorize_header, colorize_help, colorize_key_value, colorize_runner_state
from th_cli.exceptions import CLIError
from th_cli.utils import __print_json


@click.command(
    short_help=colorize_help("Get the current test runner status"),
    help=colorize_cmd_help("test_runner_status", "Get the current test runner status"),
)
@click.option(
    "--json",
    is_flag=True,
    default=False,
    help=colorize_help("Print JSON response for more details"),
)
def test_runner_status(json: Optional[bool]) -> None:
    client = None
    try:
        client = get_client()
        sync_apis = SyncApis(client)
        test_run_execution_api = sync_apis.test_run_executions_api

        test_runner_status = test_run_execution_api.get_test_runner_status_api_v1_test_run_executions_status_get()
        if json:
            __print_json(test_runner_status)
        else:
            __print_status_table(test_runner_status.dict())
    except CLIError:
        raise  # Re-raise CLI Errors as-is
    finally:
        if client:
            client.close()


def __print_status_table(status_data: dict) -> None:
    """Print status in a formatted table"""
    click.echo("")
    click.echo(colorize_header("Matter Test Runner Status"))

    colorized_status = colorize_runner_state(status_data.get("state", "Unknown").value)
    click.echo(colorize_key_value("State", colorized_status))

    if "test_run_execution_id" in status_data and status_data.get("test_run_execution_id") is not None:
        click.echo(colorize_key_value("Active Test Run ID", status_data.get("test_run_execution_id")))
    else:
        click.echo("No active test run")
