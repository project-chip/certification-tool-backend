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
from th_cli.utils import __print_json


@click.command()
@click.option(
    "--json",
    is_flag=True,
    help="Print JSON response for more details",
)
def test_runner_status(json: Optional[bool]) -> None:
    """Get the current Matter test runner status"""
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
    finally:
        if client:
            client.close()


def __print_status_table(status_data: dict) -> None:
    """Print status in a formatted table"""
    click.echo("Matter Test Runner Status")
    click.echo("=" * 30)
    click.echo("")
    click.echo(f"State: {status_data.get('state', 'Unknown')}")

    if "test_run_execution_id" in status_data:
        click.echo(f"Active Test Run ID: {status_data.get('test_run_execution_id')}")
    else:
        click.echo("No active test run")
