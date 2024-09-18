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
from typing import List, Optional

from app.models.test_enums import TestStateEnum
from app.models.test_step_execution import TestStepExecution
from app.test_engine.logger import test_engine_logger as logger
from app.test_engine.models.utils import LogSeparator
from app.test_engine.test_observable import TestObservable


class TestStep(TestObservable):
    """
    Test Step is a run-time object for a test step
    """

    __test__ = False  # Needed to indicate to PyTest that this is not a "test"

    def __init__(self, name: str, state: TestStateEnum = TestStateEnum.PENDING) -> None:
        super().__init__()
        self.errors: List[str] = []
        self.failures: List[str] = []
        self.name = name
        self.__state = state
        self.test_step_execution: Optional[TestStepExecution] = None

    @property
    def state(self) -> TestStateEnum:
        return self.__state

    @state.setter
    def state(self, value: TestStateEnum) -> None:
        if self.__state != value:
            self.__state = value
            self.notify()

    def record_error(self, msg: str) -> None:
        self.state = TestStateEnum.ERROR
        self.errors.append(msg)
        logger.error(f"Test Step Error: {msg}")
        self.notify()

    def append_failure(self, msg: str) -> None:
        self.state = TestStateEnum.FAILED
        logger.warning(f"Test Failure: {msg}")
        self.failures.append(msg)

    def mark_as_executing(self) -> None:
        # TODO: Do we need to check state before? as a precondition, and raise an
        # exception if not met?
        self.state = TestStateEnum.EXECUTING
        self.__print_log_separator()
        logger.info(f"Executing Test Step: {self.name}")

    def mark_as_not_applicable(self, msg: str) -> None:
        self.state = TestStateEnum.NOT_APPLICABLE
        logger.warning(f"Test Step Not Applicable: {self.name} - {msg}")

    def completed(self) -> bool:
        return self.state not in [TestStateEnum.PENDING, TestStateEnum.EXECUTING]

    def cancel(self) -> None:
        # Only cancel if test step is not already completed
        if self.completed():
            return
        logger.info("Cancel test step")
        self.state = TestStateEnum.CANCELLED

    def mark_as_completed(self) -> None:
        if self.completed():
            return

        if self.errors is not None and len(self.errors) > 0:
            self.state = TestStateEnum.ERROR
        elif len(self.failures) > 0:
            self.state = TestStateEnum.FAILED
        else:
            self.state = TestStateEnum.PASSED

        logger.info(f"Test Step Completed [{self.state.name}]: {self.name}")
        self.__print_log_separator()

    def __print_log_separator(self) -> None:
        logger.info(LogSeparator.TEST_STEP.value)
