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
import re
from asyncio import sleep
from multiprocessing.managers import BaseManager
from typing import Any, Generator, Type, TypeVar, cast

from app.models import TestCaseExecution
from app.test_engine.logger import test_engine_logger as logger
from app.test_engine.models import TestCase, TestStep
from test_collections.sdk_tests.support.chip_tool.chip_tool import (
    PICS_FILE_PATH,
    ChipTool,
)

from .python_test_models import PythonTest
from .python_testing_hooks_proxy import (
    SDKPythonTestResultBase,
    SDKPythonTestRunnerHooks,
)
from .utils import (
    EXECUTABLE,
    RUNNER_CLASS_PATH,
    generate_command_arguments,
    handle_logs,
)

# Custom type variable used to annotate the factory method in PythonTestCase.
T = TypeVar("T", bound="PythonTestCase")


class PythonTestCase(TestCase):
    """Base class for all Python Test based test cases.

    This class provides a class factory that will dynamically declare a new sub-class
    based on the test-type the Python test is expressing.

    The PythonTest will be stored as a class property that will be used at run-time
    in all instances of such subclass.
    """

    python_test: PythonTest
    python_test_version: str

    def __init__(self, test_case_execution: TestCaseExecution) -> None:
        super().__init__(test_case_execution=test_case_execution)
        self.chip_tool: ChipTool = ChipTool(logger)
        self.__runned = 0
        self.test_stop_called = False

    def next_step(self) -> None:
        # Python tests that don't follow the template only have the default step "Start
        # Python test", but inside the file there can be more than one test case, so the
        # hooks steps methods will continue to be called
        if len(self.test_steps) == 1:
            return

        super().next_step()

    def start(self, count: int) -> None:
        pass

    def stop(self, duration: int) -> None:
        if not self.test_stop_called:
            self.current_test_step.mark_as_completed()

    def test_start(self, filename: str, name: str, count: int) -> None:
        self.next_step()

    def test_stop(self, exception: Exception, duration: int) -> None:
        self.test_stop_called = True
        self.current_test_step.mark_as_completed()

    def step_skipped(self, name: str, expression: str) -> None:
        self.current_test_step.mark_as_not_applicable("Test step skipped")
        self.next_step()

    def step_start(self, name: str) -> None:
        pass

    def step_success(self, logger: Any, logs: str, duration: int, request: Any) -> None:
        # TODO Handle Logs properly
        self.next_step()

    def step_failure(
        self, logger: Any, logs: str, duration: int, request: Any, received: Any
    ) -> None:
        # TODO Handle Logs properly
        self.mark_step_failure("Python test step failure")
        self.next_step()

    def step_unknown(self) -> None:
        self.__runned += 1

    @classmethod
    def pics(cls) -> set[str]:
        """Test Case level PICS. Read directly from parsed Python Test."""
        return cls.python_test.PICS

    @classmethod
    def class_factory(cls, test: PythonTest, python_test_version: str) -> Type[T]:
        """class factory method for PythonTestCase."""
        title = cls.__title(test.name)
        class_name = cls.__class_name(test.name)

        return type(
            class_name,
            (cls,),
            {
                "python_test": test,
                "python_test_version": python_test_version,
                "metadata": {
                    "public_id": test.name,
                    "version": "0.0.1",
                    "title": title,
                    "description": test.description,
                },
            },
        )

    @staticmethod
    def __class_name(identifier: str) -> str:
        """Replace all non-alphanumeric characters with _ to make valid class name."""
        return re.sub("[^0-9a-zA-Z]+", "_", identifier)

    @staticmethod
    def __title(identifier: str) -> str:
        """Retrieve the test title in format TC_ABC_1_2"""
        title: str = ""
        elements = identifier.split("_")

        if len(elements) > 2:
            title = "-".join(elements[0:2]) + "-" + ".".join(elements[2:])
        else:
            title = identifier.replace("_", "-")

        return title

    async def setup(self) -> None:
        logger.info("Test Setup")

    async def cleanup(self) -> None:
        logger.info("Test Cleanup")

    async def execute(self) -> None:
        try:
            logger.info("Running Python Test: " + self.python_test.name)

            BaseManager.register("TestRunnerHooks", SDKPythonTestRunnerHooks)
            manager = BaseManager(address=("0.0.0.0", 50000), authkey=b"abc")
            manager.start()
            test_runner_hooks = manager.TestRunnerHooks()  # type: ignore

            command = [f"{RUNNER_CLASS_PATH} {self.python_test.name}"]

            # Generate the command argument by getting the test_parameters from
            # project configuration
            # comissioning method is omitted because it's handled by the test suite
            command_arguments = generate_command_arguments(
                config=self.config, omit_commissioning_method=True
            )
            command.extend(command_arguments)

            if self.chip_tool.pics_file_created:
                command.append(f" --PICS {PICS_FILE_PATH}")

            exec_result = self.chip_tool.send_command(
                command,
                prefix=EXECUTABLE,
                is_stream=True,
                is_socket=False,
            )

            while ((update := test_runner_hooks.update_test()) is not None) or (
                not test_runner_hooks.is_finished()
            ):
                if not update:
                    await sleep(0.0001)
                    continue

                self.__handle_update(update)

            # Step: Show test logs
            self.next_step()
            logger.info("---- Start of Python test logs ----")
            handle_logs(cast(Generator, exec_result.output), logger)
            logger.info("---- End of Python test logs ----")
        finally:
            pass

    def __handle_update(self, update: SDKPythonTestResultBase) -> None:
        self.__call_function_from_name(update.type.value, update.params_dict())

    def __call_function_from_name(self, func_name: str, kwargs: Any) -> None:
        func = getattr(self, func_name, None)
        if not func:
            raise AttributeError(f"{func_name} is not a method of {self}")
        if not callable(func):
            raise TypeError(f"{func_name} is not callable")
        func(**kwargs)

    def create_test_steps(self) -> None:
        self.test_steps = [TestStep("Start Python test")]
        for step in self.python_test.steps:
            python_test_step = TestStep(step.label)
            self.test_steps.append(python_test_step)
        self.test_steps.append(TestStep("Show test logs"))
