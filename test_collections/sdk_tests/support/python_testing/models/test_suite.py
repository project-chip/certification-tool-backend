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
from enum import Enum
from typing import Type, TypeVar

from app.chip_tool.chip_tool import ChipToolTestType
from app.chip_tool.test_suite import ChipToolSuite
from app.test_engine.logger import test_engine_logger as logger
from app.test_engine.models import TestSuite


class PythonTestSuiteFactoryError(Exception):
    pass


class SuiteType(Enum):
    SIMULATED = 1
    AUTOMATED = 2


# Custom Type variable used to annotate the factory methods of classmethod.
T = TypeVar("T", bound="PythonTestSuite")


class PythonTestSuite(TestSuite):
    """Base class for all Python tests based test suites.

    This class provides a class factory that will dynamically declare a new sub-class
    based on the suite-type.
    """

    python_test_version: str
    suite_name: str

    async def setup(self) -> None:
        """Override Setup to log Python Test version."""
        logger.info(f"Python Test Version: {self.python_test_version}")

    @classmethod
    def class_factory(
        cls, suite_type: SuiteType, name: str, python_test_version: str
    ) -> Type[T]:
        """Dynamically declares a subclass based on the type of test suite."""
        suite_class = PythonTestSuite

        if suite_type == SuiteType.SIMULATED:
            suite_class = SimulatedPythonTestSuite
        elif suite_type == SuiteType.AUTOMATED:
            suite_class = ChipToolPythonTestSuite

        return suite_class.__class_factory(name=name, python_test_version=python_test_version)

    @classmethod
    def __class_factory(cls, name: str, python_test_version: str) -> Type[T]:
        """Common class factory method for all subclasses of PythonTestSuite."""

        return type(
            name,
            (cls,),
            {
                "name": name,
                "python_test_version": python_test_version,
                "metadata": {
                    "public_id": name,
                    "version": "0.0.1",
                    "title": name,
                    "description": name,
                },
            },
        )


class ChipToolPythonTestSuite(PythonTestSuite, ChipToolSuite):
    test_type = ChipToolTestType.CHIP_TOOL

    async def setup(self) -> None:
        """Due top multi inheritance, we need to call setup on both super classes."""
        await PythonTestSuite.setup(self)
        await ChipToolSuite.setup(self)


class SimulatedPythonTestSuite(ChipToolPythonTestSuite):
    test_type = ChipToolTestType.CHIP_APP
