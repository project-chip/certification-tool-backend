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

from loguru import logger

from ..models.matter_test_models import MatterTestType
from ..models.sdk_test_folder import SDKTestFolder
from ..paths import SDK_CHECKOUT_PATH
from .models.test_declarations import (
    YamlCaseDeclaration,
    YamlCollectionDeclaration,
    YamlSuiteDeclaration,
)
from .models.test_suite import SuiteType
from .models.yaml_test_parser import YamlParserException, parse_yaml_test

###
# This file hosts logic load and parse YAML test-cases, located in
# `test_collections/yaml_tests/yaml/sdk`. The `sdk` sub-folder here is automatically
# maintained using the `scripts/fetch_sdk_yaml_tests_and_runner.sh` script.
#
# The YAML Tests are organized into 3 Test Suites:
#        - Automated and Semi-Automated using Chip-Tool
#        - Simulated using Chip-App1
#        - Manual
###

YAML_PATH = SDK_CHECKOUT_PATH / "yaml_tests/yaml"
SDK_YAML_PATH = YAML_PATH / "sdk"
SDK_YAML_TEST_FOLDER = SDKTestFolder(path=SDK_YAML_PATH, filename_pattern="Test_TC*")

CUSTOM_YAML_PATH = YAML_PATH / "custom"
CUSTOM_YAML_TEST_FOLDER = SDKTestFolder(
    path=CUSTOM_YAML_PATH, filename_pattern="Test_TC*"
)


def _init_test_suites(yaml_version: str) -> dict[SuiteType, YamlSuiteDeclaration]:
    return {
        SuiteType.MANUAL: YamlSuiteDeclaration(
            name="FirstManualSuite",
            suite_type=SuiteType.MANUAL,
            version=yaml_version,
        ),
        SuiteType.AUTOMATED: YamlSuiteDeclaration(
            name="FirstChipToolSuite",
            suite_type=SuiteType.AUTOMATED,
            version=yaml_version,
        ),
        SuiteType.SIMULATED: YamlSuiteDeclaration(
            name="FirstAppSuite",
            suite_type=SuiteType.SIMULATED,
            version=yaml_version,
        ),
    }


def _parse_yaml_to_test_case_declaration(
    yaml_path: Path, yaml_version: str
) -> YamlCaseDeclaration:
    yaml_test = parse_yaml_test(yaml_path)
    return YamlCaseDeclaration(test=yaml_test, yaml_version=yaml_version)


def _parse_all_yaml(
    yaml_files: list[Path], yaml_version: str
) -> list[YamlSuiteDeclaration]:
    """Parse all yaml files and organize them in the 3 test suites:
    - Automated and Semi-Automated using Chip-Tool
    - Simulated using Chip-App1
    - Manual
    """
    suites = _init_test_suites(yaml_version)

    for yaml_file in yaml_files:
        try:
            test_case = _parse_yaml_to_test_case_declaration(
                yaml_path=yaml_file, yaml_version=yaml_version
            )

            if test_case.test_type == MatterTestType.MANUAL:
                suites[SuiteType.MANUAL].add_test_case(test_case)
            elif test_case.test_type == MatterTestType.SIMULATED:
                suites[SuiteType.SIMULATED].add_test_case(test_case)
            else:
                suites[SuiteType.AUTOMATED].add_test_case(test_case)
        except YamlParserException:
            # If an exception was raised during parse process, the yaml file will be
            # ignored and the loop will continue with the next yaml file
            logger.error(f"Error while parsing YAML File: {yaml_file}")

    return [s for s in list(suites.values()) if len(s.test_cases) != 0]


def sdk_yaml_test_collection(
    yaml_test_folder: SDKTestFolder = SDK_YAML_TEST_FOLDER,
) -> YamlCollectionDeclaration:
    """Declare a new collection of test suites with the 3 test suites."""
    collection = YamlCollectionDeclaration(
        name="SDK YAML Tests", folder=yaml_test_folder
    )

    files = yaml_test_folder.file_paths(extension=".y*ml")
    version = yaml_test_folder.version
    suites = _parse_all_yaml(yaml_files=files, yaml_version=version)

    for suite in suites:
        suite.sort_test_cases()
        collection.add_test_suite(suite)

    return collection


def custom_yaml_test_collection(
    yaml_test_folder: SDKTestFolder = CUSTOM_YAML_TEST_FOLDER,
) -> Optional[YamlCollectionDeclaration]:
    """Declare a new collection of test suites."""
    collection = YamlCollectionDeclaration(
        name="Custom YAML Tests", folder=yaml_test_folder
    )

    files = yaml_test_folder.file_paths(extension=".y*ml")
    suites = _parse_all_yaml(yaml_files=files, yaml_version="custom")

    for suite in suites:
        if not suite.test_cases:
            continue
        suite.sort_test_cases()
        collection.add_test_suite(suite)

    if not collection.test_suites:
        return None

    return collection
