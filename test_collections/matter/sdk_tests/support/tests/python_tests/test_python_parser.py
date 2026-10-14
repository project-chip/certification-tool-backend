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

from ...python_testing.models import python_test_parser
from ...python_testing.models.python_test_models import PythonTestType
from ...python_testing.models.python_test_parser import parse_python_script


def test_python_file_parser() -> None:
    parent_path = Path(__file__).parent
    file_path = parent_path.joinpath("test_python_script/python_tests_info.json")

    tests = parse_python_script(file_path)

    assert len(tests) == 4
    assert "sdk/TC_Commissioning_Sample" == str(tests[0].path)
    assert len(tests[0].steps) == 3
    assert tests[0].description == "Commissioning Sample TC Description"
    assert "MCORE.ROLE.COMMISSIONEE" in tests[0].PICS
    assert len(tests[0].PICS) == 2
    count = sum(1 for test in tests if str(test.path) == "sdk/TC_SameClass")
    assert count == 2


def test_python_parser_device_requirement() -> None:
    """The device-requirement marker decides the test type when present, and the
    first step's is_commissioning flag decides otherwise."""
    parent_path = Path(__file__).parent
    file_path = parent_path.joinpath(
        "test_python_script/python_tests_info_markers.json"
    )

    with mock.patch.object(python_test_parser, "logger") as mock_logger:
        tests = {test.name: test for test in parse_python_script(file_path)}

    expected_types = {
        "TC_Marker_Commissioned": PythonTestType.COMMISSIONING,
        "TC_Marker_Commissioner": PythonTestType.NO_COMMISSIONING,
        "TC_Marker_Uncommissioned": PythonTestType.NO_COMMISSIONING,
        # No marker, or JSON from an SDK without markers: the step flag decides
        "TC_No_Marker_Flagged": PythonTestType.COMMISSIONING,
        "TC_Old_Json_Flagged": PythonTestType.COMMISSIONING,
        "TC_Old_Json_Unflagged": PythonTestType.NO_COMMISSIONING,
        # The marker wins over a contradicting step flag
        "TC_Contradiction": PythonTestType.NO_COMMISSIONING,
        # LEGACY and MANDATORY still take precedence over the marker
        "TC_Marker_Legacy": PythonTestType.LEGACY,
        "TC_IDM_12_1": PythonTestType.MANDATORY,
    }
    assert {
        name: test.python_test_type for name, test in tests.items()
    } == expected_types

    assert all(step.is_commissioning for step in tests["TC_Marker_Commissioned"].steps)

    mock_logger.warning.assert_called_once()
    assert "TC_Contradiction" in mock_logger.warning.call_args.args[0]
