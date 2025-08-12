#
# Copyright (c) 2024 Project CHIP Authors
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

import ast
import asyncio
import json
from pathlib import Path

from test_collections.matter.config import matter_settings
from test_collections.matter.sdk_tests.support.models.sdk_test_folder import (
    SDKTestFolder,
)
from test_collections.matter.sdk_tests.support.sdk_container import SDKContainer

# Make these constants synced with "test_harness_client.py"
GET_TEST_INFO_ARGUMENT = "--get_test_info"
TEST_INFO_JSON_FILENAME = "test_info.json"

SDK_TESTS_PATH = Path(__file__).parent.parent.parent
PYTHON_TESTING_PATH = SDK_TESTS_PATH / "sdk_checkout/python_testing"
JSON_OUTPUT_FILE_PATH = PYTHON_TESTING_PATH / TEST_INFO_JSON_FILENAME
PYTHON_SCRIPTS_PATH = PYTHON_TESTING_PATH / "scripts/sdk"
PYTHON_SCRIPTS_FOLDER = SDKTestFolder(path=PYTHON_SCRIPTS_PATH, filename_pattern="TC*")

CUSTOM_PYTHON_SCRIPTS_PATH = PYTHON_TESTING_PATH / "scripts/custom"
CUSTOM_PYTHON_SCRIPTS_FOLDER = SDKTestFolder(
    path=CUSTOM_PYTHON_SCRIPTS_PATH, filename_pattern="TC*"
)


PYTHON_TESTS_PARSED_FILE = SDK_TESTS_PATH / "python_tests_info.json"
CUSTOM_PYTHON_TESTS_PARSED_FILE = SDK_TESTS_PATH / "custom_python_tests_info.json"

CONTAINER_TH_CLIENT_EXEC = "python3 /root/python_testing/scripts/sdk/matter_testing_infrastructure/chip/testing/test_harness_client.py"  # noqa

sdk_container: SDKContainer = SDKContainer()


def base_test_classes(module: ast.Module) -> list[ast.ClassDef]:
    """Find classes that inherit from MatterBaseTest.

    Args:
        module (ast.Module): Python module.

    Returns:
        list[ast.ClassDef]: List of classes from the given module that inherit from
        MatterBaseTest.
    """
    return [
        c
        for c in module.body
        if isinstance(c, ast.ClassDef)
        and any(
            b for b in c.bases if isinstance(b, ast.Name) and b.id == "MatterBaseTest"
        )
    ]


def get_command_list(test_folder: SDKTestFolder) -> list:
    python_script_commands = []
    python_test_files = test_folder.file_paths(extension=".py")
    python_test_files.sort()

    for python_test_file in python_test_files:
        parent_folder = python_test_file.parent.name
        with open(python_test_file, "r") as python_file:
            parsed_python_file = ast.parse(python_file.read())

        test_classes = base_test_classes(parsed_python_file)
        for test_class in test_classes:
            script_command = [f"{parent_folder}/{python_test_file.stem}"]
            script_command.append(f"{test_class.name}")
            script_command.append(GET_TEST_INFO_ARGUMENT)
            python_script_commands.append(script_command)

    return python_script_commands


async def proccess_commands_sdk_container(
    commands: list,
    json_output_file: Path,
) -> None:
    complete_json = []
    errors_found: list[str] = []
    warnings_found: list[str] = []
    test_function_count = 0
    invalid_test_function_count = 0

    sdk_container: SDKContainer = SDKContainer()

    await sdk_container.start()
    total_commands = len(commands)
    for index, command in enumerate(commands):
        print(f"Progress {index}/{total_commands}...")
        command_string = " ".join(command)
        result = sdk_container.send_command(
            command_string,
            prefix=CONTAINER_TH_CLIENT_EXEC,
        )
        if result.exit_code != 0:
            try:
                with open(JSON_OUTPUT_FILE_PATH, "r") as json_file:
                    json_data = json.load(json_file)

                    errors_found.append(
                        f"Failed running command: {command}.\n"
                        f"Error message: {json_data['detail']}"
                    )
            finally:
                continue

        with open(JSON_OUTPUT_FILE_PATH, "r") as json_file:
            json_data = json.load(json_file)

            for json_dict in json_data:
                test_function_count += 1
                json_dict["path"] = command[0]
                json_dict["class_name"] = command[1]
                function = json_dict["function"]
                if not function.startswith("test_TC_"):
                    invalid_test_function_count += 1
                    warnings_found.append(
                        f"Warning: File path: {json_dict['path']}  "
                        f"Class: {json_dict['class_name']}. "
                        f"Invalid test function: {function}"
                    )
                complete_json.append(json_dict)

    sdk_container.destroy()

    # complete_json.append({"sdk_sha": matter_settings.SDK_SHA})
    # Create a wrapper object with sdk_sha at root level
    json_output = {"sdk_sha": matter_settings.SDK_SHA, "tests": complete_json}

    with open(json_output_file, "w") as json_file:
        json.dump(json_output, json_file, indent=4, sort_keys=True)
        json_file.close()

    print("###########################################################################")
    print("###############################   REPORT   ################################")
    print("###########################################################################")
    print(f">>>>>>>> Output JSON file: {json_output_file}")
    print(f">>>>>>>> Total of test functions: {test_function_count}")
    print(
        (
            ">>>>>>>> Total of invalid test functions (don't start with 'test_TC_'): "
            f"{invalid_test_function_count}"
        )
    )
    if len(warnings_found) > 0:
        print(*warnings_found, sep="\n")
    error_count = len(errors_found)
    print(f">>>>>>>> Total of scripts with error: {error_count}")
    if error_count > 0:
        for i, error in enumerate(errors_found):
            print(f"Error {i+1}: {error}")
    print("###########################################################################")


async def generate_python_test_json_file(
    test_folder: SDKTestFolder = PYTHON_SCRIPTS_FOLDER,
    json_output_file: Path = PYTHON_TESTS_PARSED_FILE,
) -> None:
    python_scripts_command_list = get_command_list(test_folder=test_folder)

    await proccess_commands_sdk_container(
        python_scripts_command_list, json_output_file=json_output_file
    )


if __name__ == "__main__":
    asyncio.run(generate_python_test_json_file())
