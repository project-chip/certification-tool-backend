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

from app.test_engine.logger import test_engine_logger as logger
from app.test_engine.models import TestSuite

from ...chip.chip_server import ChipServerType
from ...yaml_tests.models.chip_suite import ChipSuite


class YamlTestSuiteFactoryError(Exception):
    pass


class SuiteType(Enum):
    SIMULATED = 1
    AUTOMATED = 2
    MANUAL = 3


# Custom Type variable used to annotate the factory methods of classmethod.
T = TypeVar("T", bound="YamlTestSuite")


class YamlTestSuite(TestSuite):
    """Base class for all YAML based test suites.

    This class provides a class factory that will dynamically declare a new sub-class
    based on the suite-type.
    """

    yaml_version: str
    suite_name: str

    async def setup(self) -> None:
        """Override Setup to log YAML version."""
        logger.info(f"YAML Version: {self.yaml_version}")

    @classmethod
    def class_factory(
        cls, suite_type: SuiteType, name: str, yaml_version: str
    ) -> Type[T]:
        """Dynamically declares a subclass based on the type of test suite."""
        suite_class = YamlTestSuite

        if suite_type == SuiteType.MANUAL:
            suite_class = ManualYamlTestSuite
        elif suite_type == SuiteType.SIMULATED:
            suite_class = SimulatedYamlTestSuite
        elif suite_type == SuiteType.AUTOMATED:
            suite_class = ChipYamlTestSuite

        return suite_class.__class_factory(name=name, yaml_version=yaml_version)

    @classmethod
    def __class_factory(cls, name: str, yaml_version: str) -> Type[T]:
        """Common class factory method for all subclasses of YamlTestSuite."""

        return type(
            name,
            (cls,),
            {
                "name": name,
                "yaml_version": yaml_version,
                "metadata": {
                    "public_id": name,
                    "version": "0.0.1",
                    "title": name,
                    "description": name,
                },
            },
        )


class ManualYamlTestSuite(YamlTestSuite):
    async def setup(self) -> None:
        await super().setup()
        logger.info("This is the MANUAL test suite setup.")

    async def cleanup(self) -> None:
        logger.info("This is the MANUAL test suite cleanup.")


class ChipYamlTestSuite(YamlTestSuite, ChipSuite):
    server_type = ChipServerType.CHIP_TOOL

    async def setup(self) -> None:
        """Due top multi inheritance, we need to call setup on both super classes."""
        await YamlTestSuite.setup(self)
        await ChipSuite.setup(self)


class SimulatedYamlTestSuite(ChipYamlTestSuite):
    server_type = ChipServerType.CHIP_APP
