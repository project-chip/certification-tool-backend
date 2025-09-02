<!--
 *
 * Copyright (c) 2023 Project CHIP Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
-->

# Instructions

Please refer to the main repository for how to use these tools [here](https://github.com/project-chip/certification-tool)


# CSA Certification Tool - CLI

CLI tool for using the CSA Test Harness

## Requirements

1. Ubuntu Server OS
2. Python >= 3.10
3. Poetry installed (see: https://python-poetry.org/docs/#installation)

## Setup

1. Open terminal in the root folder and run the command `./scripts/th_cli_install.sh`
2. Change the url in config.json if required:

```json
    "hostname" : "192.168.x.x" //Change this to your Raspberry Pi IP address/localhost for local development
```

3. Run `th-cli --help` to check available commands

## Commands

```
Commands:
  abort-testing               Abort the current test execution
  available-tests             Get a list of available tests
  create-project              Creates a project
  delete-project              Deletes a project
  list-projects               Get a list of projects
  run-tests                   Create a new test run from selected tests
  test-run-execution-history  Read test run execution history
  test-runner-status          Get the current Matter test runner status
  update-project              Updates a project with full test env config file
  versions                    Get application versions information
```

### available-tests

Run `th-cli available-tests` to get a list of tests available in Test Harness, printed in YAML. For JSON respond, use `th-cli available-tests --json` .

### run-tests

Run `th-cli run-tests --tests-list <tests> [--title, -n <title>] [--config, -c <config>] [--pics-config-folder, -p <pics-config-folder>] [--project-id <ID>] [--no-color]` to start a new test execution.

Required:
- `--tests-list`: Comma-separated list of test case identifiers (e.g. --tests-list TC-ACE-1.1,TC_ACE_1_3)

Optional:
- `--title`: Custom title for the test run. If not provided, the current timestamp will be used as the default.
- `--config`: Path to the property config file. If not specified, default_config.properties will be used.
- `--pics-config-folder`: Path to the folder that contains PICS files. If not specified, no PICS file will be used.
- `--project-id`: Project ID that this test run belongs to. If not provided, uses the default 'CLI Execution Project' in TH.
- `--no-color`: Disable all colors from the CLI's output text of this test run execution

### test-run-execution-history

Run `th-cli test-run-execution-history` to fetch the history of test runs. Use `--skip` and `--limit` for pagination

Run `th-cli test-run-execution-history --id {id}` with a test run execution id to fetch the information for that test run.

For JSON respond, add `--json` to the command.

### create-project

Run `th-cli create-project --name {project name} --config {config file}` to create a new project. Project name is required.

### list-projects

Run `th-cli list-projects` to fetch projects. Use `--skip` and `--limit` for pagination. Use `--archived` to fetch archived projects only.

Run `th-cli list-projects --id {id}` with a project id to fetch the information for that specific project.

For JSON respond, add `--json` to the command.

### delete-project

Run `th-cli delete-project --id {id}` to delete a project.

### update-project

Run `th-cli update-project --id {id} --config {config file}` to update a project. Both parameters are required. Config must be a full test environment config file.

## Command Colors
By default, the CLI application presents colored texts for all the available commands, specially for the log of test run executions from the `th-cli run-tests` command.
If the users need to disable the colors from the tool's output, they may use one of the options presented below:

1. Use the option flag `--no-color` from the `run-tests` command to remove color for that execution (e.g `th-cli run-tests --no-color -t TC-ACE-1.1`)
2. Prepend the environment variable `TH_CLI_NO_COLOR` set to True to the `run-test` command (e.g `TH_CLI_NO_COLOR=1 th-cli run-tests -t TC-ACE-1.1`)
3. Export the environment variable and use the CLI normally on the same terminal instance (e.g Use `export TH_CLI_NO_COLOR=1` before using the CLI commands)

For the item `3` above, it's possible to change permanently adding the `TH_CLI_NO_COLOR=1` variable to the shell profile (e.g. `~/.bashrc`).
After that, resetting that terminal or any new one will present no color for all the CLI commands.

## Development

The source files are organized in `./th_cli/`.

### Add new command

The project uses [click](https://click.palletsprojects.com/) to declare commands.
To add a new `command` to the CLI:

-   Add a new file in `./th_cli/commands`
-   Import the new command in `./th_cli/commands/__init__.py`
-   Import and add the new command to the `root` group in `./th_cli/main.py`

### VS Code Environment

This project comes with a pre-configured dev-container for VS Code. This takes care of all dependencies and configuring
type-checker, linters and auto-formatting.

### Test Harness API Client

A major component of the CLI is the calling the Test Harness API. We're auto-generating a python client for this API
using [fastapi_client](https://github.com/dmontagu/fastapi_client) based on the `openapi.json` published by the
Test Harness backend.

To update our client:

-   update `openapi.json` in the root of this project
-   run `./scripts/generate_client` (This requires Docker to be installed)

### New Dependencies

The project dependencies are managed with [Poetry](https://python-poetry.org).
To add a new dependency, run `poetry add <package-name>`.

#### Checking Dependencies

The project dependencies may be scanned to look for known vulnerabilities or conflicts for all the poetry packages
configured. For that, run the following command after the tool installation to verify the current status of the
required dependencies:

-  `poetry run python ./scripts/check_deps.py`

### Linting and formatting

The GitHub Project will run linting with Black, Flake8 and mypy on PRs. But these are also available
in convenient scripts:

-   `./scripts/lint.sh`
-   `./scripts/format.sh`

The VS Code dev-container is also configured to do this automatically on file save.
