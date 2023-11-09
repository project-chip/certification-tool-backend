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
import asyncio
import os
import re
import signal
import subprocess
import sys
import threading
import time
from asyncio import create_task, run
from multiprocessing import Process
from multiprocessing.managers import BaseManager
from queue import Empty, Queue
from typing import Any, Type, TypeVar

# TODO check if this should be changed to  SDK python testing specific entries
from matter_chip_tool_adapter.decoder import MatterLog
from matter_yamltests.hooks import TestRunnerHooks

from app.chip_tool.chip_tool import ChipToolTestType
from app.chip_tool.test_case import ChipToolTest
from app.test_engine.logger import (
    CHIP_LOG_FORMAT,
    CHIPTOOL_LEVEL,
    logger,
    test_engine_logger,
)
from app.test_engine.models import ManualVerificationTestStep, TestCase, TestStep

from .python_testing_hooks_proxy import SDKPythonTestRunnerHooks
from .python_testing_test_models import (
    PythonTestingTest,
    PythonTestingTestStep,
    PythonTestingTestType,
)

# Custom type variable used to annotate the factory method in PythonTestingTestCase.
T = TypeVar("T", bound="PythonTestingTestCase")

class PythonTestingTestCase(TestCase, TestRunnerHooks):
    """Base class for all Python Testing based test cases.

    This class provides a class factory that will dynamically declare a new sub-class
    based on the test-type the Python Testing test is expressing.

    The PythonTestingTest will be stored as a class property that will be used at run-time in all
    instances of such subclass.
    """

    python_test: PythonTestingTest
    python_testing_version: str
    test_finished: bool

    def reset(self):
        self.start_called = False
        self.stop_called = False
        self.test_start_called = False
        self.test_stop_called = False
        self.step_skipped_list = []
        self.step_success_count = 0
        self.step_failure_count = 0
        self.step_unknown_count = 0

    def start(self, count: int):
        pass

    def stop(self, duration: int):
        pass

    def test_start(self, filename: str, name: str, count: int):
        pass
        # Dont know if it is necessary for python testing (came from chip_tool)
        # self.next_step()

    def test_stop(self, exception: Exception, duration: int):
        self.current_test_step.mark_as_completed()

    def step_skipped(self, name: str, expression: str):
        self.current_test_step.mark_as_not_applicable(
            f"Test step skipped: {name}. {expression} == False"
        )
        self.__index += 1
        self.__skipped += 1
        self.next_step()

    def step_start(self, name: str):
        pass

    def step_success(self, logger, logs, duration: int, request):
        self.__handle_logs(logs)
        self.next_step()

    def step_failure(self, logger, logs, duration: int, request, received):
        self.__handle_logs(logs)
        self.__report_failures(logger, request, received)
        self.next_step()

    def step_unknown(self):
        self.__runned += 1

    def is_finished(self) -> bool:
        return self.is_finished

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
                "Test Step Failure: \n " f"Expected: '<Empty>' \n Received:  '<Empty>'"
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
        """Python Testing config dict, sometimes have a nested dict with type and default value.
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
        """Override Setup to log Python Testing version."""
        test_engine_logger.info(
            f"Python Testing Version: {self.python_testing_version}"
        )
        try:
            await super().setup()
        except NotImplementedError:
            pass

    @classmethod
    def class_factory(
        cls, test: PythonTestingTest, python_testing_version: str
    ) -> Type[T]:
        """Dynamically declares a subclass based on the type of Python Testing test."""
        case_class: Type[PythonTestingChipToolTestCase]

        if test.type == PythonTestingTestType.AUTOMATED:
            case_class = PythonTestingChipToolTestCase

        return case_class.__class_factory(
            test=test, python_testing_version=python_testing_version
        )

    @classmethod
    def __class_factory(
        cls, test: PythonTestingTest, python_testing_version: str
    ) -> Type[T]:
        """Common class factory method for all subclasses of PythonTestingTestCase."""
        identifier = cls.__test_identifier(test.name)
        class_name = cls.__class_name(identifier)
        title = cls.__title(identifier=identifier, python_test=test)

        return type(
            class_name,
            (cls,),
            {
                "python_test": test,
                "python_testing_version": python_testing_version,
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
        """Find TC-XX-1.1 in Python Testing title.
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

    @staticmethod
    def __has_steps_disabled(python_test: PythonTestingTest) -> bool:
        """If some but not all steps are disabled, return true. False otherwise."""
        len_disabled_steps = len([s for s in python_test.steps if not s.disabled])

        if len_disabled_steps == 0:
            return False
        else:
            return len_disabled_steps < len(python_test.steps)

    @classmethod
    def __title(cls, identifier: str, python_test: PythonTestingTest) -> str:
        """Annotate Title with Semi-automated and Steps Disabled tests in the test
        title.
        """
        title = identifier

        if cls.__has_steps_disabled(python_test):
            title += " (Steps Disabled)"

        return title

    def _append_automated_test_step(
        self, python_test_step: PythonTestingTestStep
    ) -> None:
        """
        Disabled steps are ignored.
        (Such tests will be marked as 'Steps Disabled' elsewhere)

        UserPrompt are special cases that will prompt test operator for input.
        """
        if python_test_step.disabled:
            test_engine_logger.info(
                f"{self.public_id()}: skipping disabled step: {python_test_step.label}"
            )
            return

        step = TestStep(python_test_step.label)
        if python_test_step.command == "UserPrompt":
            step = ManualVerificationTestStep(
                name=python_test_step.label,
                verification=python_test_step.verification,
            )

        self.test_steps.append(step)

    async def setup(self) -> None:
        self.__step_success_count = 0
        self.__step_failure_count = 0

    def run_command(self, cmd):
        os.system(cmd)

    async def execute(self) -> None:
        try:
            logger.info("Running Python Test: " + self.metadata["title"])

            # NOTE that this aproach invalidates  parallel  execution since test_case_instance object is shared  by the class
            # TODO: Same approach could work from TestCase side: create test_case_instance inside PythonTestingTestCase to avoid using SDKPythonTestRunnerHooks

            BaseManager.register("TestRunnerHooks", SDKPythonTestRunnerHooks)
            manager = BaseManager(address=("0.0.0.0", 50000), authkey=b"abc")
            manager.start()

            test_runner_hooks = manager.TestRunnerHooks()

            command = (
                "docker run -it --network host --privileged"
                " -v /var/paa-root-certs:/root/paa-root-certs"
                " -v /var/run/dbus/system_bus_socket:/var/run/dbus/system_bus_socket:rw"
                " -v /home/ubuntu/chip-certification-tool/backend/sdk_content/python_testing2:/root/python_testing2"
                " connectedhomeip/chip-cert-bins:19771ed7101321d68b87d05201d42d00adf5368f"
                " python3 python_testing2/hello_external_runner.py "
                f" {self.metadata['title']}"
            )
            # Start the command in a new process
            p = Process(target=self.run_command, args=(command,))
            p.start()

            while ((update := test_runner_hooks.updates_test()) is not None) or (
                not test_runner_hooks.finished()
            ):
                if not update:
                    continue

                def handle_update(update: dict):
                    # key, value = next(iter(update))

                    def call_function(obj, func_name, kwargs):
                        # getattr retrieves a method with func_name from obj, if it exists.
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


class PythonTestingChipToolTestCase(PythonTestingTestCase, ChipToolTest):
    """Automated test cases using chip-tool."""

    test_type = ChipToolTestType.CHIP_TOOL

    def create_test_steps(self) -> None:
        for step in self.python_test.steps:
            self._append_automated_test_step(step)

