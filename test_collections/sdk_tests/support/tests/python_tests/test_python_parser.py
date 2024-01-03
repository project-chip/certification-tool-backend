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
from unittest import mock

from test_collections.sdk_tests.support.python_testing.models.python_test_parser import (
    parse_python_script,
)

sample_single_test_python_file_content = """
class TC_Sample(MatterBaseTest):

    def desc_TC_Sample(self) -> str:
        return "Sample TC Description"

    def steps_TC_Sample(self) -> list[TestStep]:
        steps = [
            TestStep(1, "Commissioning, already done", is_commissioning=True),
            TestStep(2, "Second step"),
            TestStep(3, "Third step"),
        ]
        return steps

    def test_TC_Sample(self):
        print("Test execution")
    
    def pics_TC_Sample(self):
        pics =  ["MCORE.ROLE.COMMISSIONEE"]

"""

sample_multi_tests_single_class_python_file_content = """
class TC_CommonSample(MatterBaseTest):

    def steps_TC_Sample_1_1(self) -> list[TestStep]:
        steps = [
            TestStep(1, "Commissioning, already done", is_commissioning=True),
            TestStep(2, "Second step"),
            TestStep(3, "Third step"),
        ]
        return steps

    def test_TC_ABC_1_1(self):
        print("Test execution")

    def test_TC_Sample_1_1(self):
        print("Test execution")

    def test_TC_Sample_1_2(self):
        print("Test execution")

"""

sample_multi_tests_multi_classes_python_file_content = """
class TC_CommonSample(MatterBaseTest):

    def steps_TC_Sample_1_1(self) -> list[TestStep]:
        steps = [
            TestStep(1, "Commissioning, already done", is_commissioning=True),
            TestStep(2, "Second step"),
            TestStep(3, "Third step"),
        ]
        return steps

    def test_TC_ABC_1_1(self):
        print("Test execution")

    def test_TC_Sample_1_1(self):
        print("Test execution")

    def test_TC_Sample_1_2(self):
        print("Test execution")

class TC_CommonSample_2(MatterBaseTest):

    def test_TC_ABC_1_2(self):
        print("Test execution")

    def test_TC_DEF_1_3(self):
        print("Test execution")

"""


def test_single_test_python_file_parser() -> None:
    file_path = Path("/test/TC_Sample.py")

    # We mock builtin `open` method to read sample python file content,
    # to avoid having to load a real file.
    with mock.patch(
        "test_collections.sdk_tests.support.python_testing.models.python_test_parser."
        "open",
        new=mock.mock_open(read_data=sample_single_test_python_file_content),
    ) as file_open:
        tests = parse_python_script(file_path)

    file_open.assert_called_once_with(file_path, "r")

    assert len(tests) is 1
    assert all(test.path == file_path for test in tests)
    assert len(tests[0].steps) is 3
    assert tests[0].description == "Sample TC Description"
    assert "MCORE.ROLE.COMMISSIONEE" in tests[0].PICS
    assert len(tests[0].PICS) is 1


def test_multi_tests_single_class_python_file_parser() -> None:
    file_path = Path("/test/TC_Sample.py")

    # We mock builtin `open` method to read sample python file content,
    # to avoid having to load a real file.
    with mock.patch(
        "test_collections.sdk_tests.support.python_testing.models.python_test_parser."
        "open",
        new=mock.mock_open(
            read_data=sample_multi_tests_single_class_python_file_content
        ),
    ) as file_open:
        tests = parse_python_script(file_path)

    file_open.assert_called_once_with(file_path, "r")

    assert len(tests) is 3
    assert all(test.path == file_path for test in tests)
    test_names = [test.name for test in tests]
    assert "TC_ABC_1_1" in test_names
    assert "TC_Sample_1_1" in test_names
    assert "TC_Sample_1_2" in test_names


def test_multi_tests_multi_classes_python_file_parser() -> None:
    file_path = Path("/test/TC_Sample.py")

    # We mock builtin `open` method to read sample python file content,
    # to avoid having to load a real file.
    with mock.patch(
        "test_collections.sdk_tests.support.python_testing.models.python_test_parser."
        "open",
        new=mock.mock_open(
            read_data=sample_multi_tests_multi_classes_python_file_content
        ),
    ) as file_open:
        tests = parse_python_script(file_path)

    file_open.assert_called_once_with(file_path, "r")

    assert len(tests) is 5
    assert all(test.path == file_path for test in tests)
    test_names = [test.name for test in tests]
    assert "TC_ABC_1_1" in test_names
    assert "TC_Sample_1_1" in test_names
    assert "TC_Sample_1_2" in test_names
    assert "TC_ABC_1_2" in test_names
    assert "TC_DEF_1_3" in test_names
