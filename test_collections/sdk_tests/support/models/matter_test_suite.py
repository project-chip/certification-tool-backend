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
from typing import Generator, Type, TypeVar, cast

from app.test_engine.logger import test_engine_logger as logger
from app.test_engine.models import TestSuite
from test_collections.sdk_tests.support.chip_tool import ChipTool
from test_collections.sdk_tests.support.chip_tool.chip_tool import ChipToolTestType
from test_collections.sdk_tests.support.chip_tool.test_suite import ChipToolSuite
from test_collections.sdk_tests.support.python_testing.models.utils import (
    EXECUTABLE,
    RUNNER_CLASS_PATH,
    generate_command_arguments,
    handle_logs,
)


class MatterTestSuiteFactoryError(Exception):
    pass


class SuiteFamilyType(Enum):
    YAML = 1
    PYTHON = 2


class SuiteType(Enum):
    SIMULATED = 1
    AUTOMATED = 2
    MANUAL = 3


# Custom Type variable used to annotate the factory methods of classmethod.
T = TypeVar("T", bound="MatterTestSuite")


class MatterTestSuite(TestSuite):
    """Base class for all YAML based test suites.

    This class provides a class factory that will dynamically declare a new sub-class
    based on the suite-type.
    """

    version: str
    suite_name: str

    async def setup(self) -> None:
        """Override Setup to log YAML version."""
        logger.info(f"YAML Version: {self.version}")

    @classmethod
    def class_factory(
        cls,
        suite_family_type: SuiteFamilyType,
        suite_type: SuiteType,
        name: str,
        version: str,
    ) -> Type[T]:
        """Dynamically declares a subclass based on the type of test suite."""
        suite_class = MatterTestSuite

        if suite_family_type == SuiteFamilyType.YAML:
            if suite_type == SuiteType.MANUAL:
                suite_class = ManualYamlTestSuite
            elif suite_type == SuiteType.SIMULATED:
                suite_class = SimulatedYamlTestSuite
            elif suite_type == SuiteType.AUTOMATED:
                suite_class = ChipToolYamlTestSuite
        else:
            suite_class = PythonTestSuite

        return suite_class.__class_factory(name=name, version=version)

    @classmethod
    def __class_factory(cls, name: str, version: str) -> Type[T]:
        """Common class factory method for all subclasses of YamlTestSuite."""

        return type(
            name,
            (cls,),
            {
                "name": name,
                "version": version,
                "metadata": {
                    "public_id": name,
                    "version": "0.0.1",
                    "title": name,
                    "description": name,
                },
            },
        )


class ManualYamlTestSuite(MatterTestSuite):
    async def setup(self) -> None:
        await super().setup()
        logger.info("This is the MANUAL test suite setup.")

    async def cleanup(self) -> None:
        logger.info("This is the MANUAL test suite cleanup.")


class ChipToolYamlTestSuite(MatterTestSuite, ChipToolSuite):
    test_type = ChipToolTestType.CHIP_TOOL

    async def setup(self) -> None:
        """Due top multi inheritance, we need to call setup on both super classes."""
        await MatterTestSuite.setup(self)
        await ChipToolSuite.setup(self)


class SimulatedYamlTestSuite(ChipToolYamlTestSuite):
    test_type = ChipToolTestType.CHIP_APP


class PythonTestSuite(MatterTestSuite):
    """Base class for all Python tests based test suites.

    This class provides a class factory that will dynamically declare a new sub-class
    based on the suite-type.
    """

    chip_tool: ChipTool = ChipTool(logger)

    async def setup(self) -> None:
        """Override Setup to log Python Test version and set PICS."""
        logger.info("Suite Setup")
        logger.info(f"Python Test Version: {self.version}")

        logger.info("Starting SDK container")
        await self.chip_tool.start_container()

        if len(self.pics.clusters) > 0:
            logger.info("Create PICS file for DUT")
            self.chip_tool.set_pics(pics=self.pics, in_container=True)
        else:
            self.chip_tool.reset_pics_state()

        logger.info("Commission DUT")
        self.commission_device()

    async def cleanup(self) -> None:
        logger.info("Suite Cleanup")

        logger.info("Stopping SDK container")
        await self.chip_tool.destroy_device()

    def commission_device(self) -> None:
        command = [f"{RUNNER_CLASS_PATH} commission"]
        command_arguments = generate_command_arguments(config=self.config)
        command.extend(command_arguments)

        exec_result = self.chip_tool.send_command(
            command,
            prefix=EXECUTABLE,
            is_stream=True,
            is_socket=False,
        )

        handle_logs(cast(Generator, exec_result.output), logger)
