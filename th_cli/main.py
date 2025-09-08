#!/usr/bin/env python3
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

import click

from th_cli.colorize import colorize_cmd_help, colorize_error, colorize_key_value
from th_cli.commands import abort_testing, available_tests, project, run_tests, test_run_execution, test_runner_status
from th_cli.utils import get_cli_sha, get_cli_version, get_versions


def get_extended_help() -> str:
    """Get extended help text including version information"""
    cli_version = get_cli_version()
    cli_sha = get_cli_sha()

    help_text = colorize_cmd_help("th-cli", "A CLI tool for Matter Test Harness")
    help_text += f"\n{colorize_key_value('Version', cli_version)}"
    help_text += f"\n{colorize_key_value('CLI SHA', cli_sha)}"

    # Try to get server versions, but don't fail if unavailable
    try:
        versions_data = get_versions()
        if versions_data:
            for key, value in versions_data.items():
                help_text += f"\n{colorize_key_value(key, value)}"
    except Exception:
        help_text += colorize_error("\nNot able to retrieve versions from server.")

    return help_text


@click.group(help=colorize_cmd_help("th-cli", "A CLI tool for Matter Test Harness"))
@click.version_option(version=get_extended_help())
def root() -> None:
    pass


root.add_command(abort_testing)
root.add_command(available_tests)
root.add_command(project)
root.add_command(run_tests)
root.add_command(test_run_execution)
root.add_command(test_runner_status)


if __name__ == "__main__":
    root()
