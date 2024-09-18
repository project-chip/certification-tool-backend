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

from ..models.sdk_test_folder import SDKTestFolder
from .models.python_test_models import PythonTestType
from .models.python_test_parser import parse_python_script
from .models.test_declarations import (
    PythonCaseDeclaration,
    PythonCollectionDeclaration,
    PythonSuiteDeclaration,
)
from .models.test_suite import SuiteType

###
# This file hosts logic to load and parse Stress/Stability test cases, located in
# `./models/rpc_client/`.
#
# This is a temporary solution since those tests should come from SDK.
#
###

STRESS_TEST_PATH = Path(__file__).resolve().parent / "scripts/sdk/"
STRESS_TEST_FOLDER = SDKTestFolder(path=STRESS_TEST_PATH, filename_pattern="TC_*")


def _init_test_suites(
    python_test_version: str,
) -> dict[SuiteType, PythonSuiteDeclaration]:
    return {
        SuiteType.COMMISSIONING: PythonSuiteDeclaration(
            name="Performance Test Suite",
            suite_type=SuiteType.COMMISSIONING,
            version=python_test_version,
        ),
        SuiteType.NO_COMMISSIONING: PythonSuiteDeclaration(
            name="Performance Test Suite",
            suite_type=SuiteType.NO_COMMISSIONING,
            version=python_test_version,
        ),
        SuiteType.LEGACY: PythonSuiteDeclaration(
            name="Performance Test Suite",
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


def _parse_all_sdk_python_tests(
    python_test_files: list[Path], python_test_version: str
) -> list[PythonSuiteDeclaration]:
    """Parse all python test files and add them into Automated Suite"""
    suites = _init_test_suites(python_test_version)

    for python_test_file in python_test_files:
        test_cases = _parse_python_script_to_test_case_declarations(
            python_test_path=python_test_file,
            python_test_version=python_test_version,
        )

        for test_case in test_cases:
            python_test_type = test_case.class_ref.python_test.python_test_type
            if python_test_type == PythonTestType.COMMISSIONING:
                suites[SuiteType.COMMISSIONING].add_test_case(test_case)
            elif python_test_type == PythonTestType.NO_COMMISSIONING:
                suites[SuiteType.NO_COMMISSIONING].add_test_case(test_case)
            else:
                suites[SuiteType.LEGACY].add_test_case(test_case)

    return [s for s in list(suites.values()) if len(s.test_cases) != 0]


def sdk_performance_test_collection(
    python_test_folder: SDKTestFolder = STRESS_TEST_FOLDER,
) -> PythonCollectionDeclaration:
    """Declare a new collection of test suites."""
    collection = PythonCollectionDeclaration(
        name="SDK Performance Tests", folder=python_test_folder
    )

    files = python_test_folder.file_paths(extension=".py")
    version = python_test_folder.version
    suites = _parse_all_sdk_python_tests(
        python_test_files=files, python_test_version=version
    )

    for suite in suites:
        suite.sort_test_cases()
        collection.add_test_suite(suite)

    return collection
