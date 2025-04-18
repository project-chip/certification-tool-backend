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
import re
from pathlib import Path

from loguru import logger
from pydantic import ValidationError

from ...models.matter_test_models import MatterTestType
from .test_suite import SuiteType
from .yaml_test_models import YamlTest


class YamlParserException(Exception):
    """Raised when an error occurs during the parser of yaml file."""


def _get_types(test: YamlTest) -> tuple[MatterTestType, SuiteType]:
    """Determine the type of a test based on the parsed yaml.

    This is mainly determined by the number of disabled test steps.

    Args:
        test (YamlTest): parsed yaml model

    Returns:
        tuple[MatterTestType, SuiteType]:
            SuiteType:
              - Manual: All steps disabled
              - Semi-Automated: some steps are disabled
              - Automated: no disabled steps
              - Simulated: Tests where file name have "Simulated"
            SuiteType:
              -  SIMULATED: Simulated Test Suite
              -  AUTOMATED: Automated Test Suite
              -  MANUAL: Manual Test Suite
              -  CAMERA_AUTOMATED: Automated Camera Test Suite
    """
    camera_test_pattern = r"\[TC-WEBRTC-\d+\.\d+\]"

    if test.path is not None and "Simulated" in str(test.path):
        return MatterTestType.SIMULATED, SuiteType.SIMULATED

    steps = test.steps

    # If all disabled:
    if all(s.disabled is True for s in steps):
        return MatterTestType.MANUAL, SuiteType.MANUAL

    # if any step has a UserPrompt, PromptWithResponse or VerifyVideoStream command,
    # categorize as semi-automated
    if any(
        s.command in ["UserPrompt", "PromptWithResponse", "VerifyVideoStream"]
        for s in steps
    ):
        if re.search(camera_test_pattern, test.name):
            return MatterTestType.SEMI_AUTOMATED, SuiteType.CAMERA_AUTOMATED
        else:
            return MatterTestType.SEMI_AUTOMATED, SuiteType.AUTOMATED

    # Otherwise
    # If test case is camera related, then return SuiteType.CAMERA_AUTOMATED
    if re.search(camera_test_pattern, test.name):
        return MatterTestType.AUTOMATED, SuiteType.CAMERA_AUTOMATED
    else:
        return MatterTestType.AUTOMATED, SuiteType.AUTOMATED


def parse_yaml_test(path: Path) -> YamlTest:
    """Parse a single YAML file into YamlTest model.

    This will also annotate parsed yaml with it's path and test type.
    """
    with open(path, "r") as file:
        try:
            yaml_str = file.read()
            test = YamlTest.parse_raw(yaml_str, proto="yaml")
            test.path = path
            test_type, suite_type = _get_types(test)
            test.type = test_type
            test.suite_type = suite_type
        except ValidationError as e:
            logger.error(str(e))
            raise YamlParserException(f"The YAML file {path} is invalid") from e

        return test
