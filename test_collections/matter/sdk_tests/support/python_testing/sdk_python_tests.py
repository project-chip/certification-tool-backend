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
from typing import Optional

from ..models.sdk_test_folder import SDKTestFolder
from ..paths import SDK_CHECKOUT_PATH
from .models.python_test_models import PythonTestType
from .models.python_test_parser import parse_python_script
from .models.test_declarations import (
    PythonCaseDeclaration,
    PythonCollectionDeclaration,
    PythonSuiteDeclaration,
)
from .models.test_suite import SuiteType

###
# This file hosts logic to load and parse Python test cases, located in
# `test_collections/matter/sdk_tests/sdk_checkout/python_testing/scripts/sdk`.
# The `sdk` sub-folder here is automatically maintained using the
# `test_collections/matter/sdk_tests/fetch_sdk_tests_and_runner.sh` script.
#
# The Python Tests are organized into 1 Test Suite:
#        - Automated
###

PYTHON_TEST_PATH = SDK_CHECKOUT_PATH / "python_testing/scripts"
SDK_PYTHON_TEST_PATH = PYTHON_TEST_PATH / "sdk"
SDK_PYTHON_TEST_FOLDER = SDKTestFolder(
    path=SDK_PYTHON_TEST_PATH, filename_pattern="TC*"
)

CUSTOM_PYTHON_TEST_PATH = PYTHON_TEST_PATH / "custom"
CUSTOM_PYTHON_TEST_FOLDER = SDKTestFolder(
    path=CUSTOM_PYTHON_TEST_PATH, filename_pattern="TC*"
)


def _init_test_suites(
    python_test_version: str,
) -> dict[SuiteType, PythonSuiteDeclaration]:
    return {
        SuiteType.MANDATORY: PythonSuiteDeclaration(
            name="Python Testing Suite - Mandatories",
            suite_type=SuiteType.MANDATORY,
            version=python_test_version,
            mandatory=True,
        ),
        SuiteType.COMMISSIONING: PythonSuiteDeclaration(
            name="Python Testing Suite",
            suite_type=SuiteType.COMMISSIONING,
            version=python_test_version,
        ),
        SuiteType.NO_COMMISSIONING: PythonSuiteDeclaration(
            name="Python Testing Suite - No commissioning",
            suite_type=SuiteType.NO_COMMISSIONING,
            version=python_test_version,
        ),
        SuiteType.LEGACY: PythonSuiteDeclaration(
            name="Python Testing Suite - Old script format",
            suite_type=SuiteType.LEGACY,
            version=python_test_version,
        ),
    }


def _parse_python_script_to_test_case_declarations(
    python_test_path: Path, python_test_version: str
) -> list[PythonCaseDeclaration]:
    python_tests = parse_python_script(python_test_path)

    return [
        PythonCaseDeclaration(test=python_test, python_test_version=python_test_version)
        for python_test in python_tests
    ]


def __parse_python_tests(
    python_test_files: list[Path], python_test_version: str, mandatory: bool
) -> list[PythonSuiteDeclaration]:
    suites = _init_test_suites(python_test_version)

    for python_test_file in python_test_files:
        test_cases = _parse_python_script_to_test_case_declarations(
            python_test_path=python_test_file,
            python_test_version=python_test_version,
        )

        for test_case in test_cases:
            python_test_type = test_case.class_ref.python_test.python_test_type
            if mandatory:
                if python_test_type == PythonTestType.MANDATORY:
                    suites[SuiteType.MANDATORY].add_test_case(test_case)
            else:
                if python_test_type == PythonTestType.COMMISSIONING:
                    suites[SuiteType.COMMISSIONING].add_test_case(test_case)
                elif python_test_type == PythonTestType.NO_COMMISSIONING:
                    suites[SuiteType.NO_COMMISSIONING].add_test_case(test_case)
                elif python_test_type != PythonTestType.MANDATORY:
                    suites[SuiteType.LEGACY].add_test_case(test_case)

    return [s for s in list(suites.values()) if len(s.test_cases) != 0]


def __sdk_python_test_collection(
    name: str, python_test_folder: SDKTestFolder, mandatory: bool
) -> PythonCollectionDeclaration:
    collection = PythonCollectionDeclaration(name=name, folder=python_test_folder)

    python_test_files = python_test_folder.file_paths(extension=".py")
    python_test_version = python_test_folder.version

    suites = __parse_python_tests(
        python_test_files=python_test_files,
        python_test_version=python_test_version,
        mandatory=mandatory,
    )

    for suite in suites:
        suite.sort_test_cases()
        collection.add_test_suite(suite)

    return collection


def sdk_python_test_collection(
    python_test_folder: SDKTestFolder = SDK_PYTHON_TEST_FOLDER,
) -> PythonCollectionDeclaration:
    """Declare a new collection of test suites."""
    return __sdk_python_test_collection(
        name="SDK Python Tests", python_test_folder=python_test_folder, mandatory=False
    )


def sdk_mandatory_python_test_collection(
    python_test_folder: SDKTestFolder = SDK_PYTHON_TEST_FOLDER,
) -> PythonCollectionDeclaration:
    """Declare a new collection of test suites."""
    return __sdk_python_test_collection(
        name="Mandatory SDK Python Tests",
        python_test_folder=python_test_folder,
        mandatory=True,
    )


def custom_python_test_collection(
    python_test_folder: SDKTestFolder = CUSTOM_PYTHON_TEST_FOLDER,
) -> Optional[PythonCollectionDeclaration]:
    """Declare a new collection of test suites."""
    collection = PythonCollectionDeclaration(
        name="Custom SDK Python Tests", folder=python_test_folder
    )

    python_test_files = python_test_folder.file_paths(extension=".py")
    suites = __parse_python_tests(
        python_test_files=python_test_files,
        python_test_version="custom",
        mandatory=False,
    )

    for suite in suites:
        if not suite.test_cases:
            continue
        suite.sort_test_cases()
        collection.add_test_suite(suite)

    if not collection.test_suites:
        return None

    return collection
