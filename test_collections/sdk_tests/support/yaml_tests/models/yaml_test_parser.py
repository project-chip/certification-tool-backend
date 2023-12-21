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

from loguru import logger
from pydantic import ValidationError

from test_collections.sdk_tests.support.models.matter_test_models import MatterTestType

from .yaml_test_models import YamlTest


class YamlTestParserException(Exception):
    """Raised when an error occurs during the parser of yaml test file."""


def _test_type(test: YamlTest) -> MatterTestType:
    """Determine the type of a test based on the parsed yaml.

    This is mainly determined by the number of disabled test steps.

    Args:
        test (YamlTest): parsed yaml model

    Returns:
        TestType:
            - Manual: All steps disabled
            - Semi-Automated: some steps are disabled
            - Automated: no disabled steps
            - Simulated: Tests where file name have "Simulated"
    """
    if test.path is not None and "Simulated" in str(test.path):
        return MatterTestType.SIMULATED

    steps = test.steps

    # If all disabled:
    if all(s.disabled is True for s in steps):
        return MatterTestType.MANUAL

    # if any step has a UserPrompt, categorize as semi-automated
    if any(s.command == "UserPrompt" for s in steps):
        return MatterTestType.SEMI_AUTOMATED

    # Otherwise Automated
    return MatterTestType.AUTOMATED


def parse_yaml_test(path: Path) -> YamlTest:
    """Parse a single YAML file into YamlTest model.

    This will also annotate parsed yaml with it's path and test type.
    """
    with open(path, "r") as file:
        try:
            yaml_str = file.read()
            test = YamlTest.parse_raw(yaml_str, proto="yaml")
            test.path = path
            test.type = _test_type(test)
        except ValidationError as e:
            logger.error(str(e))
            raise YamlTestParserException(f"The YAML file {path} is invalid") from e

        return test
