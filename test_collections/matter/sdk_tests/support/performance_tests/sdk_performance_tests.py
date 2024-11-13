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
from .models.performance_tests_parser import parse_performance_tests
from .models.test_declarations import (
    PerformanceCaseDeclaration,
    PerformanceCollectionDeclaration,
    PerformanceSuiteDeclaration,
)
from .models.test_suite import PerformanceSuiteType

###
# This file hosts logic to load and parse Stress/Stability test cases, located in
# `./scripts/sdk/`.
#
# This is a temporary solution since those tests should come from SDK.
#
###

STRESS_TEST_PATH = Path(__file__).resolve().parent / "scripts/sdk/"
STRESS_TEST_FOLDER = SDKTestFolder(path=STRESS_TEST_PATH, filename_pattern="TC_*")


def _init_test_suites(
    performance_test_version: str,
) -> dict[PerformanceSuiteType, PerformanceSuiteDeclaration]:
    return {
        PerformanceSuiteType.PERFORMANCE: PerformanceSuiteDeclaration(
            name="Performance Test Suite",
            suite_type=PerformanceSuiteType.PERFORMANCE,
            version=performance_test_version,
        ),
    }


def _parse_performance_tests_to_test_case_declarations(
    performance_test_path: Path, performance_test_version: str
) -> list[PerformanceCaseDeclaration]:
    performance_tests = parse_performance_tests(performance_test_path)

    return [
        PerformanceCaseDeclaration(
            test=performance_test, performance_test_version=performance_test_version
        )
        for performance_test in performance_tests
    ]


def _parse_all_sdk_python_tests(
    performance_test_files: list[Path], performance_test_version: str
) -> list[PerformanceSuiteDeclaration]:
    """Parse all python test files and add them into Automated Suite"""
    suites = _init_test_suites(performance_test_version)

    for performance_test_file in performance_test_files:
        test_cases = _parse_performance_tests_to_test_case_declarations(
            performance_test_path=performance_test_file,
            performance_test_version=performance_test_version,
        )

        for test_case in test_cases:
            suites[PerformanceSuiteType.PERFORMANCE].add_test_case(test_case)

    return [s for s in list(suites.values()) if len(s.test_cases) != 0]


def sdk_performance_test_collection(
    performance_test_folder: SDKTestFolder = STRESS_TEST_FOLDER,
) -> PerformanceCollectionDeclaration:
    """Declare a new collection of test suites."""
    collection = PerformanceCollectionDeclaration(
        name="SDK Performance Tests", folder=performance_test_folder
    )

    files = performance_test_folder.file_paths(extension=".py")
    version = performance_test_folder.version
    suites = _parse_all_sdk_python_tests(
        performance_test_files=files, performance_test_version=version
    )

    for suite in suites:
        suite.sort_test_cases()
        collection.add_test_suite(suite)

    return collection
