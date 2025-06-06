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

https://github.com/project-chip/certification-tool

# CSA Certification Tool - CLI

CLI tool for using the CSA Test Harness

## Requirements

1. Python >= 3.10
2. Poetry installed (see: https://python-poetry.org/docs/#installation)

## Setup

1. Open terminal in the root folder `poetry install`
2. Change the url in config.json

```json
    "hostname" : "192.168.x.x" //Change this to your Raspberry Pi IP address/localhost for local development
```

3. Run `./cli.sh --help` to check available commands

## Commands

```
Commands:
  available-tests             Get a list of available tests
  run-tests                   Create a new test run from selected tests
  test-run-execution-history  Read test run execution history
  list-projects               Get a list of projects
  create-project              Creates a project
  delete-project              Deletes a project
  update-project              Updates a project with full test env config file
  run-tests-cli               Simplified CLI execution of a test run from selected tests
```

### available-tests

Run `./cli.sh available-tests` to get a list of tests available in Test Harness, printed in YAML. For JSON respond, use `./cli.sh available-tests --json` .

### run-tests

Run `./cli.sh run-tests --file /path/to/file --project-id {id}` to run a test.

A `test config json` and `project ID` is required. For example, `{"sample_tests":{"SampleTestSuite1":{"TCSS1001": 1}}}`. Keys `sample_tests`, `SampleTestSuite1` and `TCSS1001` is mapped to the results from command `available-tests`. This triggers backend to run Test Case TCSS1001 once. Change the number to run a Test Case multiple times. Project id indicates which project this test run belongs to.

### test-run-execution-history

Run `./cli.sh test-run-execution-history` to fetch the history of test runs. Use `--skip` and `--limit` for pagination

Run `./cli.sh test-run-execution-history --id {id}` with a test run execution id to fetch the information for that test run.

For JSON respond, add `--json` to the command.

### create-project

Run `./cli.sh create-project --name {project name} --config {config file}` to create a new project. Project name is required.

### list-projects

Run `./cli.sh list-projects` to fetch projects. Use `--skip` and `--limit` for pagination. Use `--archived` to fetch archived projects only.

Run `./cli.sh list-projects --id {id}` with a project id to fetch the information for that specific project.

For JSON respond, add `--json` to the command.

### delete-project

Run `./cli.sh delete-project --id {id}` to delete a project.

### update-project

Run `./cli.sh update-project --id {id} --config path/to/config` to update a project. Both parameters are required. Config must be a full test environment config file.

### run-tests-cli

Run `./cli.sh run-tests-cli --tests-list <tests> [--title <title>] [-c <config>]` to execute a test run using the simplified CLI flow.

This command simplifies test execution by allowing you to run selected test cases directly, with minimal configuration defined in a property file.

Required:
--tests-list: Comma-separated list of test case identifiers.
Example: --tests-list TC-ACE-1.1,TC_ACE_1_3

Optional:
--title: Custom title for the test run. If not provided, the current timestamp will be used as the default.
--config: Path to the property config file. If not specified, default_config.properties will be used.

## Development

The source files are organized in `./app`.

### Add new command

The project uses [click](https://click.palletsprojects.com/) to declare commands.
To add a new `command` to the CLI:

-   Add a new file in `./app/commands`
-   Import the new command in `./app/commands/__init__.py`
-   Import and add the new command to the `root` group in `./app/main.py`

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

### Linting and formatting

The GitHub Project will run linting with Black, Flake8 and mypy on PRs. But these are also available
in convenient scripts:

-   `./scripts/lint.sh`
-   `./scripts/format.sh`

The VS Code dev-container is also configured to do this automatically on file save.
