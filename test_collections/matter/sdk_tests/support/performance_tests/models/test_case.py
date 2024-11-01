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
from enum import IntEnum
from inspect import iscoroutinefunction
from multiprocessing.managers import BaseManager
from pathlib import Path
from typing import Any, Type, TypeVar

from app.models import TestCaseExecution
from app.test_engine.logger import PYTHON_TEST_LEVEL
from app.test_engine.logger import test_engine_logger as logger
from app.test_engine.models import TestStep
from app.test_engine.models.test_case import CUSTOM_TEST_IDENTIFIER
from test_collections.matter.sdk_tests.support.python_testing.models.test_case import (
    PythonTestCase,
)
from test_collections.matter.test_environment_config import TestEnvironmentConfigMatter

from ...pics import PICS_FILE_PATH
from .python_test_models import PythonTest
from .python_testing_hooks_proxy import (
    SDKPythonTestResultBase,
    SDKPythonTestRunnerHooks,
)
from .utils import EXECUTABLE, RUNNER_CLASS_PATH, generate_command_arguments


class PromptOption(IntEnum):
    YES = 1
    NO = 2


# Custom type variable used to annotate the factory method in PerformanceTestCase.
T = TypeVar("T", bound="PerformanceTestCase")


class PerformanceTestCaseError(Exception):
    pass


class PerformanceTestCase(PythonTestCase):
    """Base class for all Python Test based test cases.

    This class provides a class factory that will dynamically declare a new sub-class
    based on the test-type the Python test is expressing.

    The PythonTest will be stored as a class property that will be used at run-time
    in all instances of such subclass.
    """

    def __init__(self, test_case_execution: TestCaseExecution) -> None:
        super().__init__(test_case_execution=test_case_execution)
        self.step_execution_times = []  # type: ignore[var-annotated]

    def test_start(
        self, filename: str, name: str, count: int, steps: list[str] = []
    ) -> None:
        self.step_over()

    def step_skipped(self, name: str, expression: str) -> None:
        self.current_test_step.mark_as_not_applicable("Test step skipped")
        self.step_over()

    def step_start(self, name: str) -> None:
        pass

    def step_success(self, logger: Any, logs: str, duration: int, request: Any) -> None:
        duration_ms = int(duration / 1000)
        self.step_execution_times.append(duration_ms)
        self.analytics = self.generate_analytics_data()
        self.step_over()

    def generate_analytics_data(self) -> dict[str, str]:
        print(self.step_execution_times)
        self.step_execution_times.sort()
        print(self.step_execution_times)
        sorted_list_size = len(self.step_execution_times)
        p50_index = int(sorted_list_size * (50 / 100))
        p95_index = int(sorted_list_size * (95 / 100))
        p99_index = int(sorted_list_size * (99 / 100))

        try:
            return {
                "p50": f"{self.step_execution_times[p50_index]}",
                "p95": f"{self.step_execution_times[p95_index]}",
                "p99": f"{self.step_execution_times[p99_index]}",
                "unit": "ms",
            }
        except:  # noqa: E722
            logger.info("Error generating analytics data for step execution times.")
        return {"p50": "0", "p95": "0", "p99": "0", "unit": "ms"}

    @classmethod
    def pics(cls) -> set[str]:
        """Test Case level PICS. Read directly from parsed Python Test."""
        return cls.python_test.PICS

    @classmethod
    def class_factory(cls, test: PythonTest, python_test_version: str) -> Type[T]:
        """Dynamically declares a subclass based on the type of Python test."""
        case_class: Type[PerformanceTestCase] = PerformanceTestCase

        return case_class.__class_factory(
            test=test, python_test_version=python_test_version
        )

    @classmethod
    def __class_factory(cls, test: PythonTest, python_test_version: str) -> Type[T]:
        """class factory method for PerformanceTestCase."""
        title = cls.__title(test.name)
        class_name = cls.__class_name(test.name)

        return type(
            class_name,
            (cls,),
            {
                "python_test": test,
                "python_test_version": python_test_version,
                "metadata": {
                    "public_id": (
                        test.name
                        if python_test_version != CUSTOM_TEST_IDENTIFIER
                        else test.name + "-" + CUSTOM_TEST_IDENTIFIER
                    ),
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
        """Retrieve the test title in format TC-ABC-1.2"""
        title: str = ""
        elements = identifier.split("_")

        if len(elements) > 2:
            title = "-".join(elements[0:2]) + "-" + ".".join(elements[2:])
        else:
            title = identifier.replace("_", "-")

        return title

    async def cleanup(self) -> None:
        logger.info("Test Cleanup")
        try:
            self.sdk_container.destroy()
        except Exception:
            pass

    def handle_logs_temp(self) -> None:
        sdk_tests_path = Path(Path(__file__).parents[3])
        file_output_path = (
            sdk_tests_path / "sdk_checkout/python_testing/test_output.txt"
        )

        filter_entries = [
            "INFO Successfully",
            "INFO Performing next",
            "INFO Internal Control",
            "'kEstablishing' --> 'kActive'",
            "SecureChannel:PBKDFParamRequest",
            "Discovered Device:",
            "|=====",
        ]

        # This is a temporary workaround since Python Test are generating a
        # big amount of log
        sdk_tests_path = Path(Path(__file__).parents[3])
        file_output_path = (
            sdk_tests_path / "sdk_checkout/python_testing/test_output.txt"
        )
        with open(file_output_path) as f:
            for line in f:
                if any(specific_string in line for specific_string in filter_entries):
                    logger.log(PYTHON_TEST_LEVEL, line)
            # lines = f.read()
            # logger.log(PYTHON_TEST_LEVEL, lines)

    async def execute(self) -> None:
        try:
            logger.info("Running Stress & Stability Test: " + self.python_test.name)

            BaseManager.register("TestRunnerHooks", SDKPythonTestRunnerHooks)
            manager = BaseManager(address=("0.0.0.0", 50000), authkey=b"abc")
            manager.start()
            test_runner_hooks = manager.TestRunnerHooks()  # type: ignore

            if not self.python_test.path:
                raise PerformanceTestCaseError(
                    f"Missing file path for python test {self.python_test.name}"
                )

            # get script path including folder (sdk or custom) and excluding extension
            test_script_relative_path = Path(
                *self.python_test.path.parts[-2:]
            ).with_suffix("")

            command = [
                f"{RUNNER_CLASS_PATH} {test_script_relative_path}"
                f" {self.python_test.class_name} --tests test_{self.python_test.name}"
            ]

            # Generate the command argument by getting the test_parameters from
            # project configuration
            # comissioning method is omitted because it's handled by the test suite
            command_arguments = generate_command_arguments(
                config=TestEnvironmentConfigMatter(**self.config),
                omit_commissioning_method=True,
            )
            command.extend(command_arguments)

            if self.sdk_container.pics_file_created:
                command.append(f" --PICS {PICS_FILE_PATH}")

            command.append(f" --interactions {(len(self.test_steps) - 2)}")

            self.sdk_container.send_command(
                command,
                prefix=EXECUTABLE,
                is_stream=False,
                is_socket=False,
                is_detach=True,
            )

            while ((update := test_runner_hooks.update_test()) is not None) or (
                not test_runner_hooks.is_finished()
            ):
                if not update:
                    await sleep(0.0001)
                    continue

                await self.__handle_update(update)

            # Step: Show test logs

            # Python tests that don't follow the template only have the 2 default steps
            # and, at this point, will still be in the first step because of the
            # step_over method. So we have to explicitly move on to the next step here.
            # The tests that do follow the template will have additional steps and will
            # have already been moved to the correct step by the hooks' step methods.
            if len(self.test_steps) == 2:
                self.next_step()

            logger.info("---- Start of Performance test logs ----")
            self.handle_logs_temp()
            # Uncomment line bellow when the workaround has a definitive solution
            # handle_logs(cast(Generator, exec_result.output), logger)

            logger.info("---- End of Performance test logs ----")

            self.current_test_step.mark_as_completed()
        finally:
            pass

    async def __handle_update(self, update: SDKPythonTestResultBase) -> None:
        await self.__call_function_from_name(update.type.value, update.params_dict())

    async def __call_function_from_name(self, func_name: str, kwargs: Any) -> None:
        func = getattr(self, func_name, None)
        if not func:
            raise AttributeError(f"{func_name} is not a method of {self}")
        if not callable(func):
            raise TypeError(f"{func_name} is not callable")

        if iscoroutinefunction(func):
            await func(**kwargs)
        else:
            func(**kwargs)

    def create_test_steps(self) -> None:
        self.test_steps = [TestStep("Start Performance test")]
        for step in self.python_test.steps:
            python_test_step = TestStep(step.label)
            self.test_steps.append(python_test_step)
        self.test_steps.append(TestStep("Show test logs"))
