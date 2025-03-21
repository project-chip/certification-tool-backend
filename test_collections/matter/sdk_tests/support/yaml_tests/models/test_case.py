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
from typing import Any, Type, TypeVar

from app.test_engine.logger import test_engine_logger
from app.test_engine.models import (
    ManualTestCase,
    ManualVerificationTestStep,
    TestCase,
    TestStep,
)
from app.test_engine.models.test_case import CUSTOM_TEST_IDENTIFIER

from ...chip.chip_server import ChipServerType
from ...models.matter_test_models import MatterTestStep, MatterTestType
from ...yaml_tests.models.chip_test import ChipManualPromptTest, ChipTest
from .yaml_test_models import YamlTest

# Custom type variable used to annotate the factory method in YamlTestCase.
T = TypeVar("T", bound="YamlTestCase")


class YamlTestCase(TestCase):
    """Base class for all YAML based test cases.

    This class provides a class factory that will dynamically declare a new sub-class
    based on the test-type the YAML test is expressing.

    The YamlTest will be stored as a class property that will be used at run-time in all
    instances of such subclass.
    """

    yaml_test: YamlTest
    yaml_version: str

    @classmethod
    def pics(cls) -> set[str]:
        """Test Case level PICS. Read directly from parsed yaml."""
        return cls.yaml_test.PICS

    @classmethod
    def default_test_parameters(cls) -> dict[str, Any]:
        """Yaml config dict, sometimes have a nested dict with type and default value.
        Only defaultValue is used in this case.
        """
        parameters = {}
        for param_name, value in cls.yaml_test.config.items():
            if isinstance(value, dict):
                if "defaultValue" in value:
                    parameters[param_name] = value["defaultValue"]
            else:
                parameters[param_name] = value
        return parameters

    async def setup(self) -> None:
        """Override Setup to log YAML version."""
        test_engine_logger.info(f"YAML Version: {self.yaml_version}")
        try:
            await super().setup()
        except NotImplementedError:
            pass

    @classmethod
    def class_factory(cls, test: YamlTest, yaml_version: str) -> Type[T]:
        """Dynamically declares a subclass based on the type of YAML test."""
        case_class: Type[YamlTestCase]
        if test.type == MatterTestType.MANUAL:
            case_class = YamlManualTestCase
        elif test.type == MatterTestType.SEMI_AUTOMATED:
            case_class = YamlSemiAutomatedChipTestCase
        elif test.type == MatterTestType.SIMULATED:
            case_class = YamlSimulatedTestCase
        else:  # Automated
            case_class = YamlChipTestCase

        return case_class.__class_factory(test=test, yaml_version=yaml_version)

    @classmethod
    def __class_factory(cls, test: YamlTest, yaml_version: str) -> Type[T]:
        """Common class factory method for all subclasses of YamlTestCase."""
        identifier = cls.__test_identifier(test.name)
        class_name = cls.__class_name(identifier)
        title = cls.__title(identifier=identifier, test_yaml=test)

        return type(
            class_name,
            (cls,),
            {
                "yaml_test": test,
                "yaml_version": yaml_version,
                "chip_test_identifier": class_name,
                "metadata": {
                    "public_id": (
                        identifier
                        if yaml_version != CUSTOM_TEST_IDENTIFIER
                        else identifier + "-" + CUSTOM_TEST_IDENTIFIER
                    ),
                    "version": "0.0.1",
                    "title": title,
                    "description": test.name,
                },
            },
        )

    @staticmethod
    def __test_identifier(name: str) -> str:
        """Find TC-XX-1.1 in YAML title.
        Note some have [TC-XX-1.1] and others TC-XX-1.1
        """
        title_pattern = re.compile(r"(?P<title>TC-[^\s\]]*)")
        if match := re.search(title_pattern, name):
            return match["title"]
        else:
            return name

    @staticmethod
    def __class_name(identifier: str) -> str:
        """Replace all non-alphanumeric characters with _ to make valid class name."""
        return re.sub("[^0-9a-zA-Z]+", "_", identifier)

    @staticmethod
    def __has_steps_disabled(test_yaml: YamlTest) -> bool:
        """If some but not all steps are disabled, return true. False otherwise."""
        len_disabled_steps = len([s for s in test_yaml.steps if not s.disabled])

        if len_disabled_steps == 0:
            return False
        else:
            return len_disabled_steps < len(test_yaml.steps)

    @classmethod
    def __title(cls, identifier: str, test_yaml: YamlTest) -> str:
        """Annotate Title with Semi-automated and Steps Disabled tests in the test
        title.
        """
        title = identifier

        if test_yaml.type == MatterTestType.SEMI_AUTOMATED:
            title += " (Semi-automated)"

        if cls.__has_steps_disabled(test_yaml):
            title += " (Steps Disabled)"

        return title

    def _append_automated_test_step(self, yaml_step: MatterTestStep) -> None:
        """
        Disabled steps are ignored.
        (Such tests will be marked as 'Steps Disabled' elsewhere)

        UserPrompt are special cases that will prompt test operator for input.
        """
        if yaml_step.disabled:
            test_engine_logger.info(
                f"{self.public_id()}: skipping disabled step: {yaml_step.label}"
            )
            return

        step = TestStep(yaml_step.label)
        if yaml_step.command == "UserPrompt":
            step = ManualVerificationTestStep(
                name=yaml_step.label,
                verification=yaml_step.verification,
            )

        self.test_steps.append(step)


class YamlManualTestCase(YamlTestCase, ManualTestCase):
    def create_test_steps(self) -> None:
        """This is a manual test case. All yaml steps are included as
        ManualVerificationTestSteps.
        """
        self.test_steps = []
        for step in self.yaml_test.steps:
            self.test_steps.append(
                ManualVerificationTestStep(
                    name=step.label, verification=step.verification
                )
            )


class YamlChipTestCase(YamlTestCase, ChipTest):
    """Automated test cases using chip-tool."""

    server_type = ChipServerType.CHIP_TOOL

    def create_test_steps(self) -> None:
        self.test_steps = [TestStep("Start chip-tool test")]
        for step in self.yaml_test.steps:
            self._append_automated_test_step(step)


class YamlSemiAutomatedChipTestCase(YamlChipTestCase, ChipManualPromptTest):
    """Semi-Automated test cases, need special step for users to attach logs
    for manual steps, so inheriting from ChipManualPromptTest.
    """


class YamlSimulatedTestCase(YamlTestCase, ChipTest):
    """Simulated test cases using chip-app"""

    server_type = ChipServerType.CHIP_APP

    def create_test_steps(self) -> None:
        self.test_steps = [TestStep("Start chip-app test")]
        for step in self.yaml_test.steps:
            self._append_automated_test_step(step)
