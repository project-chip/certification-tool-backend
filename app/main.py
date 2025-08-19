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
from commands import (
    available_tests,
    create_project,
    delete_project,
    list_projects,
    run_tests,
    run_tests_cli,
    test_run_execution_history,
    update_project,
    versions,
)
from commands.versions import get_cli_version


@click.group()
@click.version_option(version=f"{get_cli_version()}")
def root() -> None:
    pass


root.add_command(available_tests)
root.add_command(run_tests)
root.add_command(test_run_execution_history)
root.add_command(list_projects)
root.add_command(create_project)
root.add_command(delete_project)
root.add_command(update_project)
root.add_command(run_tests_cli)
root.add_command(versions)


if __name__ == "__main__":
    root()
