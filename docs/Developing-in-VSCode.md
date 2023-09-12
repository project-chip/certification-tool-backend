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
# Developing Matter TH Backend in VSCode

This guide will explain the most basic development 

### Run in debbugger
- Backend can be started in debug mode via the green play button in 
Run and Debug tab in sidebar. (Also with <kbd>F5</kbd>)
- <kbd>⌘ Command</kbd> + <kbd>⇧ Shift</kbd> + <kbd>F5</kbd> will restart the process
- breakpoints can be set by clicking to the left of a python line


### Use git in VSCode
You can use git integration in VSCode, from inside the container.

**Note:** if you get an error with public key denied, you need to share your ssh key
with ssh-agent. See platform specific guide here: 
(https://code.visualstudio.com/remote/advancedcontainers/sharing-git-credentials)[https://code.visualstudio.com/remote/advancedcontainers/sharing-git-credentials]

## Testing

Tests are implemented with `pytest` and stored in `tests` folder in the root of the 
project.

- VSCode will automatically discover tests in the project
- Tests can be run from the Testing tab in the sidebar or individually by clicking the 
testing icon in the code view, to the left of the line number, on the line declaring the
test.
- Tests also be run in debug mode by right-clicking and selecting `Debug Test`.

To run all tests and generate code coverage report run shell script `scripts/test.sh`.

## Linting, formatting and type checking

The project is configured to be 
- linted with `flake8`
- autoformated via `black` and `isort`, 
- type checked with `mypy`
- spell checked with `cspell`

All of these are automatically running on save-file in VSCode, and problems identified
will be shown in the PROBLEMS tab (<kbd>⌘ Command</kbd> + <kbd>⇧ Shift</kbd> + <kbd>M</kbd>).

- Linting is also available via shell script in `scripts/lint.sh`
- Autoformatting is also available via shell script in `scripts/format.sh`


## Reset DB
-   Run the `scripts/reset_db.py` file to drop and create a database, and run all the database migrations.