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

from .utils import (
    EXECUTABLE,
    RUNNER_CLASS_PATH,
    generate_command_arguments,
    handle_logs,
)


class SuiteType(Enum):
    AUTOMATED = 1


class DUTCommissioningError(Exception):
    pass


# Custom Type variable used to annotate the factory methods of classmethod.
T = TypeVar("T", bound="PythonTestSuite")


class PythonTestSuite(TestSuite):
    """Base class for all Python tests based test suites.

    This class provides a class factory that will dynamically declare a new sub-class
    based on the suite-type.
    """

    python_test_version: str
    suite_name: str
    chip_tool: ChipTool = ChipTool(logger)

    @classmethod
    def class_factory(
        cls, suite_type: SuiteType, name: str, python_test_version: str
    ) -> Type[T]:
        """Dynamically declares a subclass based on the type of test suite."""
        return type(
            name,
            (cls,),
            {
                "name": name,
                "python_test_version": python_test_version,
                "metadata": {
                    "public_id": name
                    if python_test_version != "custom"
                    else name + "-custom",
                    "version": "0.0.1",
                    "title": name,
                    "description": name,
                },
            },
        )

    async def setup(self) -> None:
        """Override Setup to log Python Test version and set PICS."""
        logger.info("Suite Setup")
        logger.info(f"Python Test Version: {self.python_test_version}")

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

        exit_code = self.chip_tool.exec_exit_code(exec_result.exec_id)

        if exit_code:
            raise DUTCommissioningError("Failed to commission DUT")
