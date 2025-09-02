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
from typing import Any

import click
import yaml

from th_cli.api_lib_autogen.api_client import SyncApis
from th_cli.api_lib_autogen.exceptions import UnexpectedResponse
from th_cli.client import get_client
from th_cli.colorize import colorize_cmd_help, colorize_dump, colorize_help
from th_cli.exceptions import CLIError, handle_api_error
from th_cli.utils import __json_string, __print_json


@click.command(
    short_help=colorize_help("List all available test cases"),
    help=colorize_cmd_help("available_tests", "Get a list of the available test cases")
)
@click.option(
    "--json",
    is_flag=True,
    default=False,
    help=colorize_help("Print JSON response for more details"),
)
def available_tests(json: bool = False) -> None:
    """Get a list of the available test cases"""
    client = None
    try:
        client = get_client()
        sync_apis: SyncApis = SyncApis(client)
        test_collections = sync_apis.test_collections_api.read_test_collections_api_v1_test_collections_get()

        if test_collections is None:
            raise CLIError("Server did not return test_collection")

        if json:
            __print_json(test_collections)
        else:
            __print_yaml(test_collections)
    except CLIError:
        raise  # Re-raise CLI Errors as-is
    except UnexpectedResponse as e:
        handle_api_error(e, "get available tests")
    except Exception as e:
        raise CLIError(
            f"Could not fetch the available tests: {e}. Please check if the API server is running and accessible."
        )
    finally:
        if client:
            client.close()


def __print_yaml(object: Any) -> None:
    yaml_dump = yaml.dump(yaml.load(__json_string(object), Loader=yaml.FullLoader))
    click.echo(colorize_dump(yaml_dump))
