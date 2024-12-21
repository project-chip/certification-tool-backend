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

from ...python_testing.models.python_test_parser import parse_python_script


def test_python_file_parser() -> None:
    file_path = Path(
        "/app/backend/test_collections/matter/sdk_tests/support/tests/python_tests/test_python_script/python_tests_info.json"
    )

    tests = parse_python_script(file_path)

    assert len(tests) == 4
    assert "sdk/TC_Commissioning_Sample" == str(tests[0].path)
    assert len(tests[0].steps) == 3
    assert tests[0].description == "Commissioning Sample TC Description"
    assert "MCORE.ROLE.COMMISSIONEE" in tests[0].PICS
    assert len(tests[0].PICS) == 2
    count = sum(1 for test in tests if str(test.path) == "sdk/TC_SameClass")
    assert count == 2
