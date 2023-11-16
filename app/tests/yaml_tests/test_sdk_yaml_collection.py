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
from unittest import mock

import pytest

from test_collections.sdk_tests.support.models.sdk_test_folder import SDKTestFolder
from test_collections.sdk_tests.support.models.th_test_models import THTestType
from test_collections.sdk_tests.support.yaml_tests.models.test_declarations import (
    YamlCaseDeclaration,
    YamlCollectionDeclaration,
)
from test_collections.sdk_tests.support.yaml_tests.sdk_yaml_tests import (
    sdk_yaml_test_collection,
)


@pytest.fixture
def yaml_collection() -> YamlCollectionDeclaration:
    test_sdk_yaml_path = Path(__file__).parent / "test_yamls"
    with mock.patch.object(Path, "exists", return_value=True), mock.patch(
        "test_collections.sdk_tests.support.models.sdk_test_folder.open",
        new=mock.mock_open(read_data="unit-test-yaml-version"),
    ):
        folder = SDKTestFolder(
            path=test_sdk_yaml_path, filename_pattern="UnitTest_TC_*"
        )
        return sdk_yaml_test_collection(folder)


def test_sdk_yaml_collection(
    yaml_collection: YamlCollectionDeclaration,
) -> None:
    assert yaml_collection.name == "SDK YAML Tests"
    assert len(yaml_collection.test_suites.keys()) == 3

    # test version number
    test_sdk_yaml_version_path = "/app/backend/app/tests/yaml_tests/test_yamls/.version"
    with open(test_sdk_yaml_version_path, "r") as version_file:
        assert yaml_collection.yaml_version == version_file.read().rstrip()


def test_manual_suite(yaml_collection: YamlCollectionDeclaration) -> None:
    expected_manual_test_cases = 2

    assert "FirstManualSuite" in yaml_collection.test_suites.keys()
    manual_suite = yaml_collection.test_suites["FirstManualSuite"]
    assert len(manual_suite.test_cases) == expected_manual_test_cases
    for test_case in manual_suite.test_cases.values():
        assert isinstance(test_case, YamlCaseDeclaration)
        assert test_case.test_type == THTestType.MANUAL


def test_automated_suite(yaml_collection: YamlCollectionDeclaration) -> None:
    expected_manual_test_cases = 0
    expected_automated_test_cases = 3
    expected_semi_automated_test_cases = 1
    expected_simulated_test_cases = 0

    # Assert automated and semi-automated tests cases
    assert "FirstChipToolSuite" in yaml_collection.test_suites.keys()
    automated_suite = yaml_collection.test_suites["FirstChipToolSuite"]
    assert (
        len(automated_suite.test_cases)
        == expected_automated_test_cases + expected_semi_automated_test_cases
    )

    type_count = dict.fromkeys(THTestType, 0)
    for test_case in automated_suite.test_cases.values():
        assert isinstance(test_case, YamlCaseDeclaration)
        type_count[test_case.test_type] += 1

    assert type_count[THTestType.AUTOMATED] == expected_automated_test_cases
    assert type_count[THTestType.SEMI_AUTOMATED] == expected_semi_automated_test_cases
    assert type_count[THTestType.SIMULATED] == expected_simulated_test_cases
    assert type_count[THTestType.MANUAL] == expected_manual_test_cases


def test_simulated_suite(yaml_collection: YamlCollectionDeclaration) -> None:
    expected_simulated_test_cases = 1

    assert "FirstAppSuite" in yaml_collection.test_suites.keys()
    simulated_suite = yaml_collection.test_suites["FirstAppSuite"]
    assert len(simulated_suite.test_cases) == expected_simulated_test_cases
    for test_case in simulated_suite.test_cases.values():
        assert isinstance(test_case, YamlCaseDeclaration)
        assert test_case.test_type == THTestType.SIMULATED
