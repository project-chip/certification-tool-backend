#
# Copyright (c) 2024 Project CHIP Authors
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
from asyncio import CancelledError
from typing import List, Optional, Type, TypeVar

from app.models import Project, TestCollectionExecution
from app.models.test_enums import TestStateEnum
from app.schemas.pics import PICS
from app.test_engine.logger import test_engine_logger as logger
from app.test_engine.models.utils import LogSeparator
from app.test_engine.test_observable import TestObservable
from app.test_engine.test_observer import Observer

from .test_metadata import TestCollectionMetadata
from .test_suite import TestSuite

# Custom Type variable used to annotate the factory methods of classmethod.
T = TypeVar("T", bound="TestCollection")


class TestCollection(TestObservable):
    """
    Test collection is a run-time object for a test_collection
    """

    __test__ = False  # Needed to indicate to PyTest that this is not a "test"

    metadata: TestCollectionMetadata

    available_test_suites: List[Type[TestSuite]] = []

    def __init__(self, test_collection_execution: TestCollectionExecution):
        super().__init__()
        self.test_collection_execution = test_collection_execution
        self.current_test_suite: Optional[TestSuite] = None
        self.test_suites: List[TestSuite] = []
        self.__state = TestStateEnum.PENDING
        self.errors: List[str] = []
        self.mandatory: bool = test_collection_execution.mandatory

    @classmethod
    def class_factory(
        cls,
        name: str,
        path: str,
        mandatory: bool,
    ) -> Type[T]:
        """Dynamically declares a subclass based on the type of test collection."""
        return TestCollection.__class_factory(name=name, path=path, mandatory=mandatory)

    @classmethod
    def __class_factory(cls, name: str, path: str, mandatory: bool) -> Type[T]:
        """Common class factory method for all subclasses of PythonTestCollection."""

        return type(
            name,
            (cls,),
            {
                "name": name,
                "metadata": {
                    "name": name,
                    "version": "0.0.1",
                    "path": path,
                    "mandatory": mandatory,
                },
            },
        )

    @property
    def project(self) -> Project:
        """Convenience getter to access project with settings.

        Returns:
            Project: project in which test collection is being executed
        """
        return self.test_collection_execution.test_run_execution.project

    @property
    def config(self) -> dict:
        return self.project.config

    @classmethod
    def name(cls) -> str:
        return cls.metadata["name"]

    # @property
    # def pics(self) -> PICS:
    #     return PICS.parse_obj(self.project.pics)

    @property
    def state(self) -> TestStateEnum:
        return self.__state

    @state.setter
    def state(self, value: TestStateEnum) -> None:
        if self.__state != value:
            self.__state = value
            self.notify()

    def __compute_state(self) -> TestStateEnum:
        """
        State is computed based on test_collection errors and on on test suite states.
        """
        if self.errors is not None and len(self.errors) > 0:
            return TestStateEnum.ERROR

        # Note: These loops cannot be easily coalesced as we need to iterate through
        # and assign Test Collection State in order.
        if any(ts.state == TestStateEnum.CANCELLED for ts in self.test_suites):
            return TestStateEnum.CANCELLED

        if any(ts.state == TestStateEnum.ERROR for ts in self.test_suites):
            return TestStateEnum.ERROR

        if any(ts.state == TestStateEnum.FAILED for ts in self.test_suites):
            return TestStateEnum.FAILED

        if any(ts.state == TestStateEnum.PENDING for ts in self.test_suites):
            return TestStateEnum.PENDING

        if all(ts.state == TestStateEnum.NOT_APPLICABLE for ts in self.test_suites):
            return TestStateEnum.NOT_APPLICABLE

        return TestStateEnum.PASSED

    def completed(self) -> bool:
        return self.state not in [TestStateEnum.PENDING, TestStateEnum.EXECUTING]

    def cancel(self) -> None:
        # Only cancel if test collection is not already completed
        if self.completed():
            return

        self.cancel_remaining_suites()

        logger.info("Cancel test collection")

        self.mark_as_completed()

    def cancel_remaining_suites(self) -> None:
        for test_suite in self.test_suites:
            test_suite.cancel()

    def mark_as_completed(self) -> None:
        if self.completed():
            return

        self.state = self.__compute_state()
        logger.info(
            f"Test Collection Completed [{self.state.name}]: {self.metadata['name']}"
        )
        self.__print_log_separator()

    def mark_as_executing(self) -> None:
        self.state = TestStateEnum.EXECUTING
        self.__print_log_separator()
        logger.info(f"Test Collection Executing: {self.metadata['name']}")

    def record_error(self, msg: str) -> None:
        self.errors.append(msg)
        logger.error(f"Test Collection Error: {msg}")
        self.notify()

    def __print_log_separator(self) -> None:
        logger.info(LogSeparator.TEST_COLLECTION.value)

    #######
    # Running with error handling
    #######
    async def run(self) -> None:
        self.mark_as_executing()

        if len(self.test_suites) == 0:
            logger.warning("Test Suite list is empty, please select a test suite")
        else:
            # Only run suites if setup is successful
            if await self.__setup_catch_errors():
                await self.__run_test_suites()

            # always run test collection clean up
            await self.__cleanup_catch_errors()

        self.mark_as_completed()

    async def __setup_catch_errors(self) -> bool:
        try:
            await self.setup()
            return True

        # CancelledError needs to be raised again, as it is handled in the runner
        except CancelledError:
            self.cancel()
            # if cancelled during setup we still call cleanup()
            await self.__cleanup_catch_errors()
            raise

        # All other exceptions will cause test collection error immediately
        except Exception as e:
            error = (
                "Error occurred during setup of test collection "
                + f"{self.metadata['name']}. {e}"
            )
            self.record_error(error)
            # Cancel test suites in test collection
            self.cancel_remaining_suites()
            return False

    async def __run_test_suites(self) -> None:
        # TODO: __current_test_collection should never be non here, but we should raise
        for test_suite in self.test_suites:
            await self.__run_suite_catch_errors(test_suite)

            # # We yield the run loop after each test suite,
            # # just in case others are waiting for it. This shouldn't be needed, but if
            # # several test suites in a row has a lot of non-async code, we could be
            # # blocking the run-loop.
            # # See https://docs.python.org/3.10/library/asyncio-task.html#sleeping
            # await sleep(0)

    async def __run_suite_catch_errors(self, test_suite: TestSuite) -> None:
        try:
            self.current_test_suite = test_suite
            await test_suite.run()

        # All other exceptions will cause test suite to error immediately
        except CancelledError:
            self.cancel()
            # if cancelled during test suite we still call cleanup()
            await self.__cleanup_catch_errors()
            raise
        finally:
            self.current_test_suite = None

    async def __cleanup_catch_errors(self) -> None:
        try:
            await self.cleanup()

        # CancelledError needs to be raised again, as it is handled in the runner
        except CancelledError:
            self.cancel()
            raise

        # All other exceptions will cause test collection error immediately
        except Exception as e:
            error = (
                "Error occurred during cleanup of test collection "
                + f"{self.metadata['name']}. {e}"
            )
            self.record_error(error)

    ########
    # Subscribe/Unsubscribe Observer
    ########
    def subscribe(self, observers: List[Observer]) -> None:
        super().subscribe(observers)
        self.__subscribe_test_suites(observers)

    def __subscribe_test_suites(self, observers: List[Observer]) -> None:
        for test_suite in self.test_suites:
            test_suite.subscribe(observers)

    def unsubscribe(self, observers: List[Observer]) -> None:
        super().unsubscribe(observers)
        self.__unsubscribe_test_suites(observers)

    def __unsubscribe_test_suites(self, observers: List[Observer]) -> None:
        for test_suite in self.test_suites:
            test_suite.unsubscribe(observers)

    # To be overridden
    async def setup(self) -> None:
        logger.info("`setup` not implemented in test collection")

    # To be overridden
    async def cleanup(self) -> None:
        logger.info("`cleanup` not implemented in test collection")
