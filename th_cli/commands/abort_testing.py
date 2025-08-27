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

import click

from th_cli.api_lib_autogen.api_client import SyncApis
from th_cli.api_lib_autogen.exceptions import UnexpectedResponse
from th_cli.client import get_client
from th_cli.exceptions import handle_api_error


@click.command()
def abort_testing() -> None:
    """Cancel the current testing"""
    client = None
    try:
        client = get_client()
        sync_apis = SyncApis(client)
        test_run_executions_api = sync_apis.test_run_executions_api

        response = test_run_executions_api.abort_testing_api_v1_test_run_executions_abort_testing_post()
        click.echo(response.get("detail", "Testing aborted"))
    except CLIError:
        raise  # Re-raise CLI Errors as-is
    except UnexpectedResponse as e:
        handle_api_error(e, "abort testing")
    finally:
        if client:
            client.close()
