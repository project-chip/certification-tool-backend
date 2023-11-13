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
import os
import re
from multiprocessing.managers import BaseManager
from typing import Any, Type, TypeVar

from matter_chip_tool_adapter.decoder import MatterLog

from app.chip_tool.chip_tool import ChipTool, ChipToolTestType
from app.chip_tool.test_case import ChipToolTest
from app.models import TestCaseExecution
from app.test_engine.logger import (
    CHIP_LOG_FORMAT,
    CHIPTOOL_LEVEL,
    logger,
    test_engine_logger,
)
from app.test_engine.models import TestCase, TestStep

from .python_test_models import PythonTest
from .python_testing_hooks_proxy import SDKPythonTestRunnerHooks

# Custom type variable used to annotate the factory method in PythonTestCase.
T = TypeVar("T", bound="PythonTestCase")

# Command line params
RUNNER_CLASS = "external_runner.py"
RUNNER_CLASS_PATH = "./testing2/"
EXECUTABLE = "python3"


class PythonTestCase(TestCase):
    """Base class for all Python Test based test cases.

    This class provides a class factory that will dynamically declare a new sub-class
    based on the test-type the Python test is expressing.

    The PythonTest will be stored as a class property that will be used at run-time
    in all instances of such subclass.
    """

    python_test: PythonTest
    python_test_version: str
    test_finished: bool

    def __init__(self, test_case_execution: TestCaseExecution) -> None:
        super().__init__(test_case_execution=test_case_execution)
        self.chip_tool: ChipTool

    def start(self, count: int) -> None:
        pass

    def stop(self, duration: int) -> None:
        pass

    def test_start(self, filename: str, name: str, count: int) -> None:
        pass
        # Dont know if it is necessary for python testing (came from chip_tool)
        # self.next_step()

    def test_stop(self, exception: Exception, duration: int) -> None:
        self.current_test_step.mark_as_completed()

    def step_skipped(self, name: str, expression: str) -> None:
        self.current_test_step.mark_as_not_applicable(
            f"Test step skipped: {name}. {expression} == False"
        )
        self.next_step()

    def step_start(self, name: str) -> None:
        pass

    def step_success(self, logger: Any, logs: str, duration: int, request: Any) -> None:
        self.__handle_logs(logs)
        self.next_step()

    def step_failure(
        self, logger: Any, logs: str, duration: int, request: Any, received: Any
    ) -> None:
        self.__handle_logs(logs)
        self.__report_failures(logger, request, received)
        self.next_step()

    def step_unknown(self) -> None:
        self.__runned += 1

    def is_finished(self) -> bool:
        return self.test_finished

    def __handle_logs(self, logs: Any) -> None:
        for log_entry in logs or []:
            if not isinstance(log_entry, MatterLog):
                continue

            test_engine_logger.log(
                CHIPTOOL_LEVEL,
                CHIP_LOG_FORMAT.format(log_entry.module, log_entry.message),
            )

    def __report_failures(self, logger: Any, request: TestStep, received: Any) -> None:
        """
        The logger from runner contains all logs entries for the test step, this method
        seeks for the error entries.
        """
        if not logger:
            # It is expected the runner to return a PostProcessResponseResult,
            # but in case of returning a different type
            self.current_test_step.append_failure(
                "Test Step Failure: \n Expected: '<Empty>' \n Received:  '<Empty>'"
            )
            return

        # Iterate through the entries seeking for the errors entries
        for log_entry in logger.entries or []:
            if log_entry.is_error():
                # Check if the step error came from exception or not, since the message
                # in exception object has more details
                # TODO: There is an issue raised in SDK runner in order to improve the
                # message from log_entry:
                # https://github.com/project-chip/connectedhomeip/issues/28101
                if log_entry.exception:
                    self.current_test_step.append_failure(log_entry.exception.message)
                else:
                    self.current_test_step.append_failure(log_entry.message)

    @classmethod
    def pics(cls) -> set[str]:
        """Test Case level PICS. Read directly from parsed Python Test."""
        return cls.python_test.PICS

    @classmethod
    def default_test_parameters(cls) -> dict[str, Any]:
        """Python Testing config dict, sometimes have a nested dict with type and
        default value.
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
            self.chip_tool = ChipTool()
            await self.chip_tool.start_container_no_server()
            assert self.chip_tool.is_running()
        except NotImplementedError:
            pass

    @classmethod
    def class_factory(cls, test: PythonTest, python_test_version: str) -> Type[T]:
        """Dynamically declares a subclass based on the type of Python Test test."""
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
        """Find TC-XX-1.1 in Python Test title.
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

    def run_command(self, cmd: str) -> None:
        os.system(cmd)

    async def execute(self) -> None:
        try:
            logger.info("Running Python Test: " + self.metadata["title"])
            BaseManager.register("TestRunnerHooks", SDKPythonTestRunnerHooks)
            manager = BaseManager(address=("0.0.0.0", 50000), authkey=b"abc")
            manager.start()
            test_runner_hooks = manager.TestRunnerHooks()  # type: ignore
            runner_class = RUNNER_CLASS_PATH + RUNNER_CLASS
            self.chip_tool.send_command(
                f"{runner_class} {self.metadata['title']}", prefix=EXECUTABLE
            )
            while ((update := test_runner_hooks.update_test()) is not None) or (
                not test_runner_hooks.is_finished()
            ):
                if not update:
                    continue

                def handle_update(update: dict) -> None:
                    def call_function(obj, func_name, kwargs) -> None:  # type: ignore
                        func = getattr(obj, func_name, None)
                        if not func:
                            raise AttributeError(
                                f"{func_name} is not a method of {obj}"
                            )
                        if not callable(func):
                            raise TypeError(f"{func_name} is not callable")
                        # Call the method with the unpacked keyword arguments.
                        func(**kwargs)

                    for func_name, kwargs in update.items():
                        call_function(self, func_name, kwargs)

                handle_update(update)
        finally:
            pass

    async def cleanup(self) -> None:
        logger.info("Test Cleanup")
        self.chip_tool.destroy_device()


class PythonChipToolTestCase(PythonTestCase, ChipToolTest):
    """Automated Python test cases using chip-tool."""

    test_type = ChipToolTestType.PYTHON_TEST

    def create_test_steps(self) -> None:
        for step in self.python_test.steps:
            python_test_step = TestStep(step.label)
            self.test_steps.append(python_test_step)
