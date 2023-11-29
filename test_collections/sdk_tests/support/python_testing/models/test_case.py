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
from asyncio import sleep
from multiprocessing.managers import BaseManager
from typing import Any, Type, TypeVar

from app.chip_tool.chip_tool import ChipTool
from app.models import TestCaseExecution
from app.test_engine.logger import logger, test_engine_logger
from app.test_engine.models import TestCase, TestStep

from .python_test_models import PythonTest
from .python_testing_hooks_proxy import SDKPythonTestRunnerHooks

# Custom type variable used to annotate the factory method in PythonTestCase.
T = TypeVar("T", bound="PythonTestCase")

# Command line params
RUNNER_CLASS = "test_harness_client.py"
RUNNER_CLASS_PATH = "/root/python_testing/"
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

    def __init__(self, test_case_execution: TestCaseExecution) -> None:
        super().__init__(test_case_execution=test_case_execution)
        self.chip_tool: ChipTool
        self.__runned = 0
        self.test_stop_called = False

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
        self.current_test_step.mark_as_not_applicable(
            f"Test step skipped: {name}. {expression} == False"
        )
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
        self.next_step()

    def step_unknown(self) -> None:
        self.__runned += 1

    @classmethod
    def pics(cls) -> set[str]:
        """Test Case level PICS. Read directly from parsed Python Test."""
        return cls.python_test.PICS

    async def setup(self) -> None:
        """Override Setup to log Python Test version."""
        test_engine_logger.info(f"Python Test Version: {self.python_test_version}")
        try:
            self.chip_tool = ChipTool()
            await self.chip_tool.start_container()
            assert self.chip_tool.is_running()
        except NotImplementedError:
            pass

    @classmethod
    def class_factory(cls, test: PythonTest, python_test_version: str) -> Type[T]:
        """class factory method for PythonTestCase."""
        return type(
            test.name,
            (cls,),
            {
                "python_test": test,
                "python_test_version": python_test_version,
                "chip_tool_test_identifier": test.name,
                "metadata": {
                    "public_id": test.name,
                    "version": "0.0.1",
                    "title": test.name,
                    "description": test.description,
                },
            },
        )

    async def execute(self) -> None:
        try:
            logger.info("Running Python Test: " + self.metadata["title"])
            BaseManager.register("TestRunnerHooks", SDKPythonTestRunnerHooks)
            manager = BaseManager(address=("0.0.0.0", 50000), authkey=b"abc")
            manager.start()
            test_runner_hooks = manager.TestRunnerHooks()  # type: ignore
            runner_class = RUNNER_CLASS_PATH + RUNNER_CLASS
            # TODO Ignoring stream from docker execution
            self.chip_tool.send_command(
                f"{runner_class} {self.metadata['title']}",
                prefix=EXECUTABLE,
                is_stream=True,
                is_socket=False,
            ).output

            while ((update := test_runner_hooks.update_test()) is not None) or (
                not test_runner_hooks.is_finished()
            ):
                if not update:
                    continue

                self.__handle_update(update)
                await sleep(0.001)
        finally:
            pass

    def __handle_update(self, update: dict) -> None:
        for func_name, kwargs in update.items():
            self.__call_function_from_name(self, func_name, kwargs)

    def __call_function_from_name(self, obj, func_name, kwargs) -> None:  # type: ignore
        func = getattr(obj, func_name, None)
        if not func:
            raise AttributeError(f"{func_name} is not a method of {obj}")
        if not callable(func):
            raise TypeError(f"{func_name} is not callable")
        func(**kwargs)

    async def cleanup(self) -> None:
        logger.info("Test Cleanup")

    def create_test_steps(self) -> None:
        self.test_steps = [TestStep("Start Python test")]
        for step in self.python_test.steps:
            python_test_step = TestStep(step.label)
            self.test_steps.append(python_test_step)
