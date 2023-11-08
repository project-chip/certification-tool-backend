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
# flake8: noqa
# Ignore flake8 check for this file
from pathlib import Path

import pytest

from test_collections.sdk_tests.support.python_testing.models.python_test_folder import (
    PythonTestFolder,
)
from test_collections.sdk_tests.support.python_testing.models.python_test_models import (
    PythonTestType,
)
from test_collections.sdk_tests.support.python_testing.models.test_declarations import (
    PythonCaseDeclaration,
    PythonCollectionDeclaration,
)
from test_collections.sdk_tests.support.python_testing.sdk_python_test_tests import (
    sdk_python_test_collection,
)

VERSION_FILE_FILENAME = ".version"
VERSION_FILE_PATH = Path("/app/backend/test_collections/sdk_tests/sdk_checkout/")


@pytest.fixture
def python_test_collection() -> PythonCollectionDeclaration:
    test_sdk_python_path = Path(__file__).parent / "test_python_script"
    folder = PythonTestFolder(
        path=test_sdk_python_path, filename_pattern="UnitTest_TC_*"
    )
    return sdk_python_test_collection(folder)


# def test_sdk_python_test_collection(
#     python_test_collection: PythonCollectionDeclaration,
# ) -> None:
#     assert python_test_collection.name == "SDK Python Tests"
#     assert len(python_test_collection.test_suites.keys()) == 1

#     # test version number
#     test_sdk_python_version_path = VERSION_FILE_PATH / VERSION_FILE_FILENAME
#     with open(test_sdk_python_version_path, "r") as version_file:
#         assert (
#             python_test_collection.python_test_version == version_file.read().rstrip()
#         )


def test_automated_suite(python_test_collection: PythonCollectionDeclaration) -> None:
    expected_automated_test_cases = 1

    # Assert automated tests cases
    assert "Python Testing Suite" in python_test_collection.test_suites.keys()
    automated_suite = python_test_collection.test_suites["Python Testing Suite"]
    assert len(automated_suite.test_cases) == expected_automated_test_cases

    type_count = dict.fromkeys(PythonTestType, 0)
    for test_case in automated_suite.test_cases.values():
        assert isinstance(test_case, PythonCaseDeclaration)
        type_count[test_case.test_type] += 1

    assert type_count[PythonTestType.AUTOMATED] == expected_automated_test_cases
