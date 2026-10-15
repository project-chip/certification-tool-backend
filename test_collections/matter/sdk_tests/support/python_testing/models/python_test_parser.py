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
import json
import re
from pathlib import Path
from typing import Any, Optional

from app.test_engine.logger import test_engine_logger as logger

from ...models.matter_test_models import MatterTestStep
from .python_test_models import PythonTest, PythonTestType

TC_TEST_FUNCTION_PATTERN = re.compile(r"test_(?P<title>TC_[\S]+)")

mandatory_python_tcs_public_id = [
    "TC_IDM_10_2",
    "TC_IDM_10_3",
    "TC_IDM_10_4",
    "TC_IDM_10_5",
    "TC_IDM_12_1",
]

# Whether each SDK device-requirement marker (matter.testing.matter_testing) needs the
# DUT commissioned before the test runs. Tests without a marker, from SDKs that
# predate the markers, or with a marker missing here, fall back to the first step's
# is_commissioning flag.
device_requirement_needs_commissioning = {
    "MatterTestCommissionedDevice": True,
    "MatterTestUncommissionedDevice": False,
    "MatterTestCommissioner": False,
    "CertificationUnitTestNoDevice": False,
}


def parse_python_script(path: Path) -> list[PythonTest]:
    """Parse a JSON file of SDK Python test info into a list of PythonTest models.

    The JSON file is generated from the SDK's Python test scripts and holds one entry
    per test function, with its class name, description, PICS, path and steps.

    Args:
        path (Path): Path to the JSON file.

    Returns:
        list[PythonTest]: Parsed tests, annotated with their file path and test type.
    """
    python_tests: list[PythonTest] = []

    with open(path, "r") as json_file:
        parsed_scripts = json.load(json_file)

    if len(parsed_scripts) == 0:
        return python_tests

    for script_info in parsed_scripts["tests"]:
        if "function" in script_info:
            test_function = script_info["function"]
            test_name = __test_case_name(test_function)
            if test_name is None:
                logger.info(f"Failed to parse test name [{test_function}].")
                continue

            test_description = script_info["desc"]
            test_pics = script_info["pics"]
            test_path = script_info["path"]
            test_class_name = script_info["class_name"]
            parsed_steps = script_info["steps"]

            is_commissioning = __needs_commissioning(script_info, test_name)
            test_steps: list[MatterTestStep] = []
            for step in parsed_steps:
                step_description = step["description"]

                test_steps.append(
                    MatterTestStep(
                        label=step_description,
                        is_commissioning=is_commissioning,
                    )
                )

            # - PythonTestType.MANDATORY: Mandatory test cases
            # - PythonTestType.LEGACY: Tests that have only one step and with this
            #   name: "Run entire test"
            # - PythonTestType.COMMISSIONING: Test cases whose device-requirement
            #   marker, or first step's is_commissioning flag, needs a commissioned DUT
            # - PythonTestType.NO_COMMISSIONING: All other test cases
            if test_name in mandatory_python_tcs_public_id:
                python_test_type = PythonTestType.MANDATORY
            elif len(test_steps) == 1 and test_steps[0].label == "Run entire test":
                python_test_type = PythonTestType.LEGACY
            elif is_commissioning:
                python_test_type = PythonTestType.COMMISSIONING
            else:
                python_test_type = PythonTestType.NO_COMMISSIONING

            python_tests.append(
                PythonTest(
                    name=test_name,
                    description=test_description,
                    steps=test_steps,
                    config={},  # Currently config is not configured in Python Testing
                    PICS=test_pics,
                    path=test_path,
                    class_name=test_class_name,
                    python_test_type=python_test_type,
                )
            )

    return python_tests


def __test_case_name(function_name: str) -> Optional[str]:
    """Extract test case name from methods that match the pattern "test_TC_[\\S]+".

    Args:
        methods (str): Function name.

    Returns:
        str: Test case name.
    """
    if match := re.match(TC_TEST_FUNCTION_PATTERN, function_name):
        if name := match["title"]:
            return name

    return None


def __needs_commissioning(script_info: dict[str, Any], test_name: str) -> bool:
    """Whether the DUT must be commissioned before the test runs.

    The test class's device-requirement marker decides when present. Otherwise the
    first step's is_commissioning flag decides, as for SDKs without markers and for
    tests that declare no marker. A marker this TH doesn't know, or conflicting
    markers (reported in device_requirement_error), also fall back to the flag,
    with a warning.

    Args:
        script_info (dict[str, Any]): Test info entry from the parsed JSON file.
        test_name (str): Test case name, used for logging.

    Returns:
        bool: True if the DUT must be commissioned before the test runs.
    """
    steps = script_info["steps"]
    step_flag = bool(steps[0].get("is_commissioning", False)) if steps else False

    marker = script_info.get("device_requirement")
    if marker is None:
        error = script_info.get("device_requirement_error")
        if error:
            logger.warning(
                f"{test_name}: {error}. Using the first step's is_commissioning flag."
            )
        return step_flag
    if marker not in device_requirement_needs_commissioning:
        logger.warning(
            f"{test_name}: unknown device-requirement marker {marker}. Using the "
            "first step's is_commissioning flag."
        )
        return step_flag

    needs_commissioning = device_requirement_needs_commissioning[marker]
    if step_flag and not needs_commissioning:
        logger.warning(
            f"{test_name}: first step sets is_commissioning but the test class is "
            f"{marker}. Using {marker}."
        )
    return needs_commissioning
