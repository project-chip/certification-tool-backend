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
from pathlib import Path

from loguru import logger

from .models.python_test_folder import PythonTestFolder
from .models.python_test_parser import PythonParserException, parse_python_test
from .models.test_declarations import (
    PythonCaseDeclaration,
    PythonCollectionDeclaration,
    PythonSuiteDeclaration,
)
from .models.test_suite import SuiteType

###
# This file hosts logic load and parse Python test-cases, located in
# `test_collections/sdk_tests/sdk_checkout/python_testing/scripts/sdk`.
# The `sdk` sub-folder here is automatically maintained using the
# `test_collections/sdk_tests/fetch_sdk_tests_and_runner.sh` script.
#
# The Python Tests are organized into 1 Test Suite:
#        - Automated
###

SDK_PYTHON_TEST_PATH = Path(
    "/app/backend/test_collections/sdk_tests/sdk_checkout/python_testing/scripts/sdk"
)
SDK_PYTHON_TEST_FOLDER = PythonTestFolder(
    path=SDK_PYTHON_TEST_PATH, filename_pattern="TC*"
)


def _init_test_suites(
    python_test_version: str,
) -> dict[SuiteType, PythonSuiteDeclaration]:
    return {
        SuiteType.AUTOMATED: PythonSuiteDeclaration(
            name="Python Testing Suite",
            suite_type=SuiteType.AUTOMATED,
            version=python_test_version,
        ),
    }


def _parse_python_test_to_test_case_declaration(
    python_test_path: Path, python_test_version: str
) -> PythonCaseDeclaration:
    python_test = parse_python_test(python_test_path)
    return PythonCaseDeclaration(
        test=python_test, python_test_version=python_test_version
    )


def _parse_all_sdk_python_tests(
    python_test_files: list[Path], python_test_version: str
) -> list[PythonSuiteDeclaration]:
    """Parse all python test files and add them into Automated Suite"""
    suites = _init_test_suites(python_test_version)

    for python_test_file in python_test_files:
        try:
            test_case = _parse_python_test_to_test_case_declaration(
                python_test_path=python_test_file,
                python_test_version=python_test_version,
            )

            suites[SuiteType.AUTOMATED].add_test_case(test_case)
        except PythonParserException as e:
            # If an exception was raised during parse process, the python file will be
            # ignored and the loop will continue with the next file
            logger.error(
                f"Error while parsing Python File: {python_test_file} \nError:{e}"
            )

    return list(suites.values())


def sdk_python_test_collection(
    python_test_folder: PythonTestFolder = SDK_PYTHON_TEST_FOLDER,
) -> PythonCollectionDeclaration:
    """Declare a new collection of test suites."""
    collection = PythonCollectionDeclaration(
        name="SDK Python Tests", folder=python_test_folder
    )

    files = python_test_folder.python_file_paths()
    version = python_test_folder.version
    suites = _parse_all_sdk_python_tests(
        python_test_files=files, python_test_version=version
    )

    for suite in suites:
        suite.sort_test_cases()
        collection.add_test_suite(suite)

    return collection
