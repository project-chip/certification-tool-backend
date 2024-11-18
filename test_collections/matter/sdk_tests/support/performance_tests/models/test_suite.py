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

from ...sdk_container import SDKContainer


class PerformanceSuiteType(Enum):
    PERFORMANCE = 1


# Custom Type variable used to annotate the factory methods of classmethod.
T = TypeVar("T", bound="PerformanceTestSuite")


class PerformanceTestSuite(TestSuite):
    """Base class for all Performance tests based test suites.

    This class provides a class factory that will dynamically declare a new sub-class
    based on the suite-type.
    """

    performance_test_version: str
    suite_name: str
    sdk_container: SDKContainer = SDKContainer()

    @classmethod
    def class_factory(
        cls, suite_type: PerformanceSuiteType, name: str, performance_test_version: str
    ) -> Type[T]:
        """Dynamically declares a subclass based on the type of test suite."""
        suite_class: Type[PerformanceTestSuite] = PerformanceTestSuite

        return suite_class.__class_factory(
            name=name, performance_test_version=performance_test_version
        )

    @classmethod
    def __class_factory(cls, name: str, performance_test_version: str) -> Type[T]:
        """Common class factory method for all subclasses of PythonTestSuite."""

        return type(
            name,
            (cls,),
            {
                "name": name,
                "performance_test_version": performance_test_version,
                "metadata": {
                    "public_id": (
                        name
                        if performance_test_version != "custom"
                        else name + "-custom"
                    ),
                    "version": "0.0.1",
                    "title": name,
                    "description": name,
                },
            },
        )

    async def setup(self) -> None:
        """Override Setup to log Python Test version and set PICS."""
        logger.info("Suite Setup")
        logger.info(f"Python Test Version: {self.performance_test_version}")

        logger.info("Setting up SDK container")
        await self.sdk_container.start()

    async def cleanup(self) -> None:
        logger.info("Suite Cleanup")

        logger.info("Stopping SDK container")
        try:
            self.sdk_container.destroy()
        except Exception:
            pass
