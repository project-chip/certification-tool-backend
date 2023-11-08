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

from app.chip_tool.chip_tool import ChipToolTestType
from app.chip_tool.test_case import ChipToolManualPromptTest, ChipToolTest
from app.test_engine.logger import test_engine_logger
from app.test_engine.models import (
    ManualTestCase,
    ManualVerificationTestStep,
    TestCase,
    TestStep,
)

from .python_test_models import PythonTest, PythonTestStep, PythonTestType

# Custom type variable used to annotate the factory method in PythonTestCase.
T = TypeVar("T", bound="PythonTestCase")


class PythonTestCase(TestCase):
    """Base class for all Python based test cases.

    This class provides a class factory that will dynamically declare a new sub-class
    based on the test-type the Python test is expressing.

    The PythonTest will be stored as a class property that will be used at run-time in all
    instances of such subclass.
    """

    python_test: PythonTest
    python_test_version: str

    @classmethod
    def pics(cls) -> set[str]:
        """Test Case level PICS. Read directly from parsed python test."""
        return cls.python_test.PICS

    @classmethod
    def default_test_parameters(cls) -> dict[str, Any]:
        """Python test config dict, sometimes have a nested dict with type and default value.
        Only defaultValue is used in this case.
        """
        parameters = {}
        for param_name, value in cls.python_test.config.items():
            if isinstance(value, dict):
                if "defaultValue" in value:
                    parameters[param_name] = value["defaultValue"]
            else:
                parameters[param_name] = value
        return parameters

    async def setup(self) -> None:
        """Override Setup to log Python Test version."""
        test_engine_logger.info(f"Python Test Version: {self.python_test_version}")
        try:
            await super().setup()
        except NotImplementedError:
            pass

    @classmethod
    def class_factory(cls, test: PythonTest, python_test_version: str) -> Type[T]:
        """Dynamically declares a subclass based on the type of Python test."""
        case_class: Type[PythonTestCase] = PythonChipToolTestCase

        return case_class.__class_factory(
            test=test, python_test_version=python_test_version
        )

    @classmethod
    def __class_factory(cls, test: PythonTest, python_test_version: str) -> Type[T]:
        """Common class factory method for all subclasses of PythonTestCase."""
        identifier = cls.__test_identifier(test.name)
        class_name = cls.__class_name(identifier)
        title = identifier

        return type(
            class_name,
            (cls,),
            {
                "python_test": test,
                "python_test_version": python_test_version,
                "chip_tool_test_identifier": class_name,
                "metadata": {
                    "public_id": identifier,
                    "version": "0.0.1",
                    "title": title,
                    "description": test.name,
                },
            },
        )

    @staticmethod
    def __test_identifier(name: str) -> str:
        """Find TC-XX-1.1 in Python test title.
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

    def _append_automated_test_step(self, python_test_step: PythonTestStep) -> None:
        """
        Disabled steps are ignored.
        (Such tests will be marked as 'Steps Disabled' elsewhere)

        UserPrompt are special cases that will prompt test operator for input.
        """

        step = TestStep(python_test_step.label)
        self.test_steps.append(step)


class PythonChipToolTestCase(PythonTestCase, ChipToolTest):
    """Automated Python test cases."""

    test_type = ChipToolTestType.PYTHON_TEST

    def create_test_steps(self) -> None:
        self.test_steps = [TestStep("Start Python test")]
        for step in self.python_test.steps:
            self._append_automated_test_step(step)
