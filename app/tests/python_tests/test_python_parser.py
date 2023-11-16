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
    PythonParserException,
    parse_python_test,
)

sample_invalid_python_file_content = """
class TC_Sample(MatterBaseTest):

    def steps_TC_Sample(self) -> list[TestStep]:
        steps = [
            TestStep(1, "Commissioning, already done", is_commissioning=True),
            TestStep(2, "Second step"),
            TestStep(3, "Third step"),
        ]
        return steps

    def test_steps_TC_Sample(self):
        print("Test execution")

"""

sample_python_file_content = """
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


def test_python_file_parser_throws_pythonparserexception() -> None:
    file_path = Path("/test/file.py")

    with mock.patch(
        "test_collections.sdk_tests.support.python_testing.models.python_test_parser."
        "open",
        new=mock.mock_open(read_data=sample_invalid_python_file_content),
    ):
        try:
            parse_python_test(file_path)
        except PythonParserException as e:
            assert (
                "Test Case file does not have methods desc_file or steps_file" == str(e)
            )


def test_python_file_parser() -> None:
    file_path = Path("/test/TC_Sample.py")

    # We mock builtin `open` method to read sample python file content,
    # to avoid having to load a real file.
    with mock.patch(
        "test_collections.sdk_tests.support.python_testing.models.python_test_parser."
        "open",
        new=mock.mock_open(read_data=sample_python_file_content),
    ) as file_open:
        test = parse_python_test(file_path)

        file_open.assert_called_once_with(file_path, "r")
        assert test.path == file_path
