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
import re
from pathlib import Path
from typing import Optional

from test_collections.matter.config import matter_settings
from test_collections.matter.sdk_tests.support.exec_run_in_container import (
    ExecResultExtended,
)
from test_collections.matter.sdk_tests.support.models.sdk_test_folder import (
    SDKTestFolder,
)
from test_collections.matter.sdk_tests.support.sdk_container import SDKContainer

# Make these constants synced with "test_harness_client.py"
GET_TEST_INFO_ARGUMENT = "--get-test-info"
TEST_INFO_JSON_FILENAME = "test_info.json"

# Pattern to match TC_*.py format
# TC_ followed by at least one character/digit, then .py
TC_FILENAME_PATTERN = r"^TC_.+\.py$"

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
PYTHON_TESTS_IGNORE_FILE = SDK_TESTS_PATH / "python_tests_ignore.txt"
PYTHON_TESTS_INCLUDE_FILE = SDK_TESTS_PATH / "python_tests_include.txt"

CONTAINER_TH_CLIENT_EXEC = "python3 /root/python_testing/scripts/sdk/matter_testing_infrastructure/chip/testing/test_harness_client.py"  # noqa

sdk_container: SDKContainer = SDKContainer()


def __get_error_message_from_result(result: ExecResultExtended) -> str:
    """Extract error message from command result, preferring JSON detail if available.

    Args:
        result: ExecResultExtended from sdk_container.send_command()

    Returns:
        str: Error message from JSON detail or command output
    """
    error_message = None
    # Try to get error from JSON file first
    if JSON_OUTPUT_FILE_PATH.exists():
        try:
            with open(JSON_OUTPUT_FILE_PATH, "r") as json_file:
                json_data = json.load(json_file)
                if isinstance(json_data, dict) and "detail" in json_data:
                    error_message = json_data["detail"]
        except (json.JSONDecodeError, KeyError):
            pass

    # Fall back to command output if JSON error not available
    if error_message is None:
        error_message = (
            result.output.decode("utf-8")
            if isinstance(result.output, bytes)
            else str(result.output)
        )

    return error_message


def load_ignore_list() -> set[str]:
    """Load the list of Python test files to ignore.

    Returns:
        set[str]: Set of filenames to ignore (e.g., {'TC_TEST_1_1.py'})
    """
    ignore_list = set()
    if PYTHON_TESTS_IGNORE_FILE.exists():
        with open(PYTHON_TESTS_IGNORE_FILE, "r") as f:
            for line in f:
                # Strip whitespace and skip empty lines or comments
                filename = line.strip()
                if filename and not filename.startswith("#"):
                    ignore_list.add(filename)
    return ignore_list


def load_include_list() -> set[str]:
    """Load the list of Python test files to always include (bypass regex check).

    Returns:
        set[str]: Set of filenames to always include (e.g., {'TCP_Tests.py'})
    """
    include_list = set()
    if PYTHON_TESTS_INCLUDE_FILE.exists():
        with open(PYTHON_TESTS_INCLUDE_FILE, "r") as f:
            for line in f:
                # Strip whitespace and skip empty lines or comments
                filename = line.strip()
                if filename and not filename.startswith("#"):
                    include_list.add(filename)
    return include_list


def base_test_classes(module: ast.Module) -> list[ast.ClassDef]:
    """Find classes that inherit from MatterBaseTest.

    Args:
        module (ast.Module): Python module.

    Returns:
        list[ast.ClassDef]: List of classes from the given module that inherit from
        MatterBaseTest.
    """

    # Get all imported classes that could be base test classes
    imported_base_classes = set()
    for node in module.body:
        if isinstance(node, ast.ImportFrom):
            # Include imports from support_modules, matter_testing,
            # or any module ending with Base/Test
            if node.module and (
                "support_modules" in node.module
                or "matter_testing" in node.module
                or node.module.endswith("TestBase")
                or "TestBase" in node.module
            ):
                for alias in node.names:
                    imported_base_classes.add(alias.name)

    def inherits_from_matter_base_test(
        class_def: ast.ClassDef, visited: Optional[set] = None
    ) -> bool:
        if visited is None:
            visited = set()

        if class_def.name in visited:
            return False
        visited.add(class_def.name)

        # Check direct inheritance from MatterBaseTest or imported base classes
        for base in class_def.bases:
            if isinstance(base, ast.Name):
                if base.id == "MatterBaseTest" or base.id in imported_base_classes:
                    return True

        # Check inheritance from parent classes in the same module
        for base in class_def.bases:
            if isinstance(base, ast.Name):
                parent_class = next(
                    (
                        c
                        for c in module.body
                        if isinstance(c, ast.ClassDef) and c.name == base.id
                    ),
                    None,
                )
                if parent_class and inherits_from_matter_base_test(
                    parent_class, visited.copy()
                ):
                    return True

        return False

    return [
        c
        for c in module.body
        if isinstance(c, ast.ClassDef) and inherits_from_matter_base_test(c)
    ]


def get_command_list(test_folder: SDKTestFolder) -> list:
    python_script_commands = []
    python_test_files = test_folder.file_paths(extension=".py")
    python_test_files.sort()

    # Use the constant pattern for TC filename validation
    tc_pattern = re.compile(TC_FILENAME_PATTERN)

    # Load ignore and include lists
    ignore_list = load_ignore_list()
    include_list = load_include_list()

    for python_test_file in python_test_files:
        # Check if file is in include list (bypass regex check)
        if python_test_file.name in include_list:
            print(f"Including {python_test_file.name} (in include list)")
        # Check if the file follows the TC_*.py pattern
        elif not tc_pattern.match(python_test_file.name):
            continue

        # Check if the file is in the ignore list
        if python_test_file.name in ignore_list:
            print(f"Skipping {python_test_file.name} (in ignore list)")
            continue

        parent_folder = python_test_file.parent.name
        try:
            with open(python_test_file, "r") as python_file:
                parsed_python_file = ast.parse(python_file.read())
        except SyntaxError:
            # Skip files with syntax errors (e.g., unterminated strings)
            print(f"Warning: Skipping {python_test_file.name} due to syntax error")
            continue

        test_classes = base_test_classes(parsed_python_file)
        for test_class in test_classes:
            # Add file path and class name
            script_command = [
                f"{parent_folder}/{python_test_file.stem}",
                f"{test_class.name}",
            ]

            python_script_commands.append(script_command)

    return python_script_commands


async def process_commands_sdk_container(
    commands: list, json_output_file: Path, grouped_commands: bool = False
) -> None:
    test_function_count: int = 0
    invalid_test_function_count: int = 0
    complete_json: list[dict] = []
    errors_found: list[str] = []
    warnings_found: list[str] = []

    sdk_container: SDKContainer = SDKContainer()
    await sdk_container.start()

    try:
        if grouped_commands:
            (
                test_function_count,
                invalid_test_function_count,
            ) = await __process_grouped_commands(
                sdk_container,
                commands,
                complete_json,
                errors_found,
                warnings_found,
            )
        else:
            (
                test_function_count,
                invalid_test_function_count,
            ) = await __process_individual_commands(
                sdk_container,
                commands,
                complete_json,
                errors_found,
                warnings_found,
            )

        # Create a wrapper object with sdk_sha at root level
        json_output = {"sdk_sha": matter_settings.SDK_SHA, "tests": complete_json}

        with open(json_output_file, "w") as json_file:
            json.dump(json_output, json_file, indent=4, sort_keys=True)

        __print_report(
            json_output_file,
            test_function_count,
            invalid_test_function_count,
            warnings_found,
            errors_found,
        )

    finally:
        sdk_container.destroy()


async def __process_grouped_commands(
    sdk_container: SDKContainer,
    commands: list,
    complete_json: list,
    errors_found: list[str],
    warnings_found: list[str],
) -> tuple[int, int]:
    test_function_count: int = 0
    invalid_test_function_count: int = 0

    command_string = " ".join(
        ["--test-list"]
        + [item for sublist in commands for item in sublist]
        + [GET_TEST_INFO_ARGUMENT]
    )

    result = sdk_container.send_command(
        command_string,
        prefix=CONTAINER_TH_CLIENT_EXEC,
    )

    if result.exit_code != 0:
        error_message = __get_error_message_from_result(result)
        errors_found.append(
            f"Failed running command: {command_string}.\n"
            f"Error message: {error_message}"
        )
        return test_function_count, invalid_test_function_count

    if not JSON_OUTPUT_FILE_PATH.exists():
        errors_found.append(
            f"Command succeeded but expected JSON output file not found: {JSON_OUTPUT_FILE_PATH}"  # noqa
        )
        return test_function_count, invalid_test_function_count

    with open(JSON_OUTPUT_FILE_PATH, "r") as json_file:
        json_data = json.load(json_file)

        for json_dict in json_data:
            test_function_count += 1

            if "info" not in json_dict and "script_path" in json_dict:
                errors_found.append(
                    f"Failed running command: {command_string}.\n"
                    "Error message details: "
                    f"{json_dict.get('detail', 'No detail provided')}\n"
                    "Error message script_path: "
                    f"{json_dict.get('script_path', 'No script path provided')}\n"
                )
                invalid_test_function_count += 1
                continue

            for json_dict_info in json_dict["info"]:
                json_dict_info["path"] = json_dict["script_path"]
                json_dict_info["class_name"] = json_dict["class_name"]
                function = json_dict_info["function"]
                if not function.startswith("test_TC_"):
                    invalid_test_function_count += 1
                    warnings_found.append(
                        f"Warning: File path: {json_dict_info['path']}  "
                        f"Class: {json_dict_info['class_name']}. "
                        f"Invalid test function: {function}"
                    )
                complete_json.append(json_dict_info)

    return test_function_count, invalid_test_function_count


async def __process_individual_commands(
    sdk_container: SDKContainer,
    commands: list,
    complete_json: list,
    errors_found: list[str],
    warnings_found: list[str],
) -> tuple[int, int]:
    test_function_count: int = 0
    invalid_test_function_count: int = 0
    total_commands = len(commands)
    for index, command in enumerate(commands):
        print(f"Progress {index+1}/{total_commands}...")
        command_string = " ".join(command + [GET_TEST_INFO_ARGUMENT])
        result = sdk_container.send_command(
            command_string,
            prefix=CONTAINER_TH_CLIENT_EXEC,
        )

        if result.exit_code != 0:
            error_message = __get_error_message_from_result(result)
            errors_found.append(
                f"Failed running command: {command}.\n"
                f"Error message: {error_message}"
            )
            continue

        if not JSON_OUTPUT_FILE_PATH.exists():
            errors_found.append(
                f"Command succeeded but expected JSON output file not found: {JSON_OUTPUT_FILE_PATH}"  # noqa
            )
            continue

        with open(JSON_OUTPUT_FILE_PATH, "r") as json_file:
            json_data = json.load(json_file)

            for json_dict in json_data:
                test_function_count += 1

                json_dict["path"] = command[0]
                json_dict["class_name"] = command[1]
                if "function" in json_dict:
                    function = json_dict["function"]
                    if not function.startswith("test_TC_"):
                        invalid_test_function_count += 1
                        warnings_found.append(
                            f"Warning: File path: {json_dict['path']}  "
                            f"Class: {json_dict['class_name']}. "
                            f"Invalid test function: {function}"
                        )
                complete_json.append(json_dict)

    return test_function_count, invalid_test_function_count


def __print_report(
    json_output_file: Path,
    test_function_count: int,
    invalid_test_function_count: int,
    warnings_found: list[str],
    errors_found: list[str],
) -> None:
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
    grouped_commands: bool = False,
) -> None:
    python_scripts_command_list = get_command_list(test_folder=test_folder)

    await process_commands_sdk_container(
        python_scripts_command_list,
        json_output_file=json_output_file,
        grouped_commands=grouped_commands,
    )


if __name__ == "__main__":
    asyncio.run(generate_python_test_json_file(grouped_commands=True))
