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
from asyncio import CancelledError, Task, create_task
from typing import List, Optional

from app.models import Project, TestRunExecution
from app.models.test_enums import TestStateEnum
from app.schemas.test_run_log_entry import TestRunLogEntry
from app.test_engine.logger import test_engine_logger as logger
from app.test_engine.test_observable import TestObservable
from app.test_engine.test_observer import Observer
from app.user_prompt_support.prompt_request import OptionsSelectPromptRequest
from app.user_prompt_support.user_prompt_support import UserPromptSupport

from .test_collection import TestCollection


class TestRun(TestObservable, UserPromptSupport):
    """
    Test run is a run-time object for a test_run
    """

    __test__ = False  # Needed to indicate to PyTest that this is not a "test"

    def __init__(self, test_run_execution: TestRunExecution):
        super().__init__()
        self.test_run_execution = test_run_execution
        self.current_test_collection: Optional[TestCollection] = None
        self.test_collections: List[TestCollection] = []
        self.__state = TestStateEnum.PENDING
        self.__current_testing_task: Optional[Task] = None
        self.log: list[TestRunLogEntry] = []

    @property
    def project(self) -> Project:
        """Convenience getter to access project.

        Returns:
            Project: project in which test run is being executed
        """
        return self.test_run_execution.project

    @property
    def config(self) -> dict:
        """Convenience getter to access project config."""
        return self.project.config

    @property
    def state(self) -> TestStateEnum:
        return self.__state

    @state.setter
    def state(self, value: TestStateEnum) -> None:
        if self.__state != value:
            self.__state = value
            self.notify()

    def __compute_state(self) -> TestStateEnum:
        """State computed based test_collection states."""

        # Note: These loops cannot be easily coalesced as we need to iterate through
        # and assign Test Collection State in order.
        if any(tc.state == TestStateEnum.CANCELLED for tc in self.test_collections):
            return TestStateEnum.CANCELLED

        if any(tc.state == TestStateEnum.ERROR for tc in self.test_collections):
            return TestStateEnum.ERROR

        if any(tc.state == TestStateEnum.FAILED for tc in self.test_collections):
            return TestStateEnum.FAILED

        if any(tc.state == TestStateEnum.PENDING for tc in self.test_collections):
            return TestStateEnum.PENDING

        if all(
            tc.state == TestStateEnum.NOT_APPLICABLE for tc in self.test_collections
        ):
            return TestStateEnum.NOT_APPLICABLE

        return TestStateEnum.PASSED

    def completed(self) -> bool:
        return self.state not in [TestStateEnum.PENDING, TestStateEnum.EXECUTING]

    def mark_as_completed(self) -> None:
        if not self.completed():
            self.state = self.__compute_state()

        logger.info(f"Test Run Completed [{self.state.name}]")

    def mark_as_executing(self) -> None:
        self.state = TestStateEnum.EXECUTING
        logger.info("Test Run Executing")

    async def run(self) -> None:
        """This will start executing in an async task to handle aborting a test run."""
        self.mark_as_executing()

        try:
            self.__current_testing_task = create_task(self.__run_handle_errors())
            await self.__current_testing_task
        except CancelledError:
            logger.error("The test run has been cancelled")
            self.__cancel_remaining_collections()
        finally:
            self.__current_testing_task = None
            self.current_test_collection = None
            self.mark_as_completed()

    async def __run_handle_errors(self) -> None:
        """Perform the test run, by executing test collections one at a time."""
        for test_collection in self.test_collections:
            self.current_test_collection = test_collection
            await test_collection.run()

            # Check if mandatory collection failed
            if (
                self.test_run_execution.certification_mode
                and test_collection.mandatory
                and test_collection.state != TestStateEnum.PASSED
            ):
                print("Abort execution")
                self.__cancel_remaining_collections()
                self.cancel()
                await self.__display_mandatory_test_failure_prompt()
                break

    async def __display_mandatory_test_failure_prompt(self) -> None:
        prompt = (
            "At least one of the mandatory test cases failed while running in "
            "certification mode.\nAs a consequence, the remaining tests were cancelled."
        )
        options = {"OK": 1}
        prompt_request = OptionsSelectPromptRequest(prompt=prompt, options=options)

        logger.info(f'User prompt: "{prompt}"')
        await self.send_prompt_request(prompt_request)

    def cancel(self) -> None:
        """This will abort executuion of the current test collection, and mark all
        remaining suites and tests as cancelled."""
        if self.__current_testing_task is None:
            logger.error("Cannot cancel test run when no test is running")
            return

        self.__current_testing_task.cancel()
        self.__current_testing_task = None

    def __cancel_remaining_collections(self) -> None:
        """This will cancel all remaining test collections, its test suites and its
        test cases."""
        for test_collection in self.test_collections:
            # Note: cancel on a completed test_collection is a No-op
            test_collection.cancel()

    def append_log_entries(self, entries: list[TestRunLogEntry]) -> None:
        self.log.extend(entries)
        self.notify()

    def subscribe(self, observers: List[Observer]) -> None:
        """Subscribe a list of observers to test run changes, and changes on sub-models
        test collections, test cases, and test steps.

        Args:
            observers (List[Observer]): Observers to be notified of changes
        """
        super().subscribe(observers)
        self.__subscribe_test_collections(observers)

    def __subscribe_test_collections(self, observers: List[Observer]) -> None:
        """Subscribe sub-models to observers

        Args:
            observers (List[Observer]): Observers to be notified of changes
        """
        for test_collection in self.test_collections:
            test_collection.subscribe(observers)

    def unsubscribe(self, observers: List[Observer]) -> None:
        """Unsubscribe observers from changes to test run changes, and sub-models
        test collections, test cases, and test steps.

        Args:
            observers (List[Observer]): Observers to be unsubscribed
        """
        super().unsubscribe(observers)
        self.__unsubscribe_test_collections(observers)

    def __unsubscribe_test_collections(self, observers: List[Observer]) -> None:
        """Unsubscribe sub-models to observers

        Args:
            observers (List[Observer]): Observers to be unsubscribed
        """
        for test_collection in self.test_collections:
            test_collection.unsubscribe(observers)
