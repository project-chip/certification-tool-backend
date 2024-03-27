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
from datetime import datetime
from queue import Empty, Queue
from typing import Callable, Generator, Union

from loguru import logger
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.test_case_execution import TestCaseExecution
from app.models.test_enums import TestStateEnum
from app.models.test_run_execution import TestRunExecution
from app.models.test_step_execution import TestStepExecution
from app.models.test_suite_execution import TestSuiteExecution
from app.test_engine.models import TestCase, TestRun, TestStep, TestSuite
from app.test_engine.test_observer import Observer


class TestDBObserver(Observer):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"

    def __init__(
        self, db_generator: Callable[[], Generator[Session, None, None]] = get_db
    ) -> None:
        self.__db_generator = db_generator
        self.data_queue: Queue = Queue()

    def apply_updates(self) -> None:
        while not self.data_queue.empty():
            try:
                data = self.data_queue.get(timeout=0.1)
                self.__save(data)
            except Empty:
                pass

    def dispatch(
        self, observable: Union[TestRun, TestSuite, TestCase, TestStep]
    ) -> None:
        logger.debug("Received Dispatch event")
        if observable is not None:
            if isinstance(observable, TestRun):
                self.__onTestRunUpdate(observable)
            elif isinstance(observable, TestSuite):
                self.__onTestSuiteUpdate(observable)
            elif isinstance(observable, TestCase):
                self.__onTestCaseUpdate(observable)
            elif isinstance(observable, TestStep):
                self.__onTestStepUpdate(observable)

    def __onTestRunUpdate(self, observable: "TestRun") -> None:
        logger.debug("Test Run Observer received", observable)
        test_run_execution = observable.test_run_execution
        test_run_execution.state = observable.state
        test_run_execution.log = observable.log

        if test_run_execution.started_at is None:
            test_run_execution.started_at = datetime.now()

        if self.isCompleted(observable.state):
            test_run_execution.completed_at = datetime.now()

        self.data_queue.put(test_run_execution)

    def __onTestSuiteUpdate(self, observable: "TestSuite") -> None:
        logger.debug("Test Suite Observer received", observable)
        if observable.test_suite_execution is not None:
            observable.test_suite_execution.state = observable.state
            if observable.errors:
                observable.test_suite_execution.errors = observable.errors

            if observable.test_suite_execution.started_at is None:
                observable.test_suite_execution.started_at = datetime.now()

            if self.isCompleted(observable.state):
                observable.test_suite_execution.completed_at = datetime.now()

            self.data_queue.put(observable.test_suite_execution)

    def __onTestCaseUpdate(self, observable: "TestCase") -> None:
        logger.debug("Test Case Observer received", observable)
        if observable.test_case_execution is not None:
            observable.test_case_execution.state = observable.state
            if observable.errors:
                observable.test_case_execution.errors = observable.errors

            if observable.test_case_execution.started_at is None:
                observable.test_case_execution.started_at = datetime.now()

            if self.isCompleted(observable.state):
                observable.test_case_execution.completed_at = datetime.now()

            self.data_queue.put(observable.test_case_execution)

    def __onTestStepUpdate(self, observable: "TestStep") -> None:
        logger.debug("Test Step Observer received", observable)
        if observable.test_step_execution is not None:
            observable.test_step_execution.state = observable.state
            if observable.errors:
                observable.test_step_execution.errors = observable.errors
            if observable.failures:
                observable.test_step_execution.failures = observable.failures

            if observable.test_step_execution.started_at is None:
                observable.test_step_execution.started_at = datetime.now()

            if self.isCompleted(observable.state):
                observable.test_step_execution.completed_at = datetime.now()

            self.data_queue.put(observable.test_step_execution)

    def __save(
        self,
        execution_obj: Union[
            TestCaseExecution, TestStepExecution, TestSuiteExecution, TestRunExecution
        ],
    ) -> None:
        # We get the session from the model it self to avoid overriding values when
        # using a different session
        insp = inspect(execution_obj)
        if insp is None or (session := insp.session) is None:  # type: ignore
            logger.error(
                f"No Database session found for execution object: {execution_obj}."
            )
            session = next(self.__db_generator())
            session.add(execution_obj)
        session.expire_on_commit = False
        session.commit()
        logger.debug(
            f"Saved {execution_obj.__class__} {execution_obj.id}"
            f" with state {execution_obj.state}"
        )

    @staticmethod
    def isCompleted(state: TestStateEnum) -> bool:
        if state is not TestStateEnum.PENDING and state is not TestStateEnum.EXECUTING:
            return True
        else:
            return False
