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
from multiprocessing.managers import BaseManager
from typing import Any, Generator, Type, TypeVar, cast

from app.models import TestCaseExecution
from app.test_engine.logger import test_engine_logger as logger
from app.test_engine.models import TestCase, TestStep
from app.test_engine.models.test_case import CUSTOM_TEST_IDENTIFIER
from app.user_prompt_support.prompt_request import OptionsSelectPromptRequest
from app.user_prompt_support.user_prompt_support import UserPromptSupport

from ...chip.chip_tool import PICS_FILE_PATH
from ...sdk_container import SDKContainer
from ...utils import prompt_for_commissioning_mode
from .python_test_models import PythonTest, PythonTestType
from .python_testing_hooks_proxy import (
    SDKPythonTestResultBase,
    SDKPythonTestRunnerHooks,
)
from .utils import (
    EXECUTABLE,
    RUNNER_CLASS_PATH,
    commission_device,
    generate_command_arguments,
    handle_logs,
)


class PromptOption(IntEnum):
    YES = 1
    NO = 2


# Custom type variable used to annotate the factory method in PythonTestCase.
T = TypeVar("T", bound="PythonTestCase")


class PythonTestCaseError(Exception):
    pass


class PythonTestCase(TestCase, UserPromptSupport):
    """Base class for all Python Test based test cases.

    This class provides a class factory that will dynamically declare a new sub-class
    based on the test-type the Python test is expressing.

    The PythonTest will be stored as a class property that will be used at run-time
    in all instances of such subclass.
    """

    sdk_container: SDKContainer = SDKContainer(logger)
    python_test: PythonTest
    python_test_version: str

    def __init__(self, test_case_execution: TestCaseExecution) -> None:
        super().__init__(test_case_execution=test_case_execution)
        self.__runned = 0
        self.test_stop_called = False

    # Move to the next step if the test case has additional steps apart from the 2
    # deafult ones
    def step_over(self) -> None:
        # Python tests that don't follow the template only have the default steps "Start
        # Python test" and "Show test logs", but inside the file there can be more than
        # one test case, so the hooks' step methods will continue to be called
        if len(self.test_steps) == 2:
            return

        self.next_step()

    def start(self, count: int) -> None:
        pass

    def stop(self, duration: int) -> None:
        if not self.test_stop_called:
            self.current_test_step.mark_as_completed()

    def test_start(self, filename: str, name: str, count: int) -> None:
        self.step_over()

    def test_stop(self, exception: Exception, duration: int) -> None:
        self.test_stop_called = True

    def step_skipped(self, name: str, expression: str) -> None:
        self.current_test_step.mark_as_not_applicable("Test step skipped")
        self.step_over()

    def step_start(self, name: str) -> None:
        pass

    def step_success(self, logger: Any, logs: str, duration: int, request: Any) -> None:
        self.step_over()

    def step_failure(
        self, logger: Any, logs: str, duration: int, request: Any, received: Any
    ) -> None:
        self.mark_step_failure("Python test step failure")

        # Python tests with only 2 steps are the ones that don't follow the template.
        # In the case of a test file with multiple test cases, more than one of these
        # tests can fail and so this method will be called for each of them. These
        # failures should be reported in the first step and moving to the logs step
        # should only happen after all test cases are executed.
        if len(self.test_steps) > 2:
            # Python tests stop when there's a failure. We need to skip the next steps
            # and execute only the last one, which shows the logs
            self.skip_to_last_step()

    def step_unknown(self) -> None:
        self.__runned += 1

    @classmethod
    def pics(cls) -> set[str]:
        """Test Case level PICS. Read directly from parsed Python Test."""
        return cls.python_test.PICS

    @classmethod
    def class_factory(cls, test: PythonTest, python_test_version: str) -> Type[T]:
        """Dynamically declares a subclass based on the type of Python test."""
        case_class: Type[PythonTestCase]

        if test.python_test_type == PythonTestType.NO_COMMISSIONING:
            case_class = NoCommissioningPythonTestCase
        elif test.python_test_type == PythonTestType.LEGACY:
            case_class = LegacyPythonTestCase
        else:  # Commissioning
            case_class = PythonTestCase

        return case_class.__class_factory(
            test=test, python_test_version=python_test_version
        )

    @classmethod
    def __class_factory(cls, test: PythonTest, python_test_version: str) -> Type[T]:
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
                    "public_id": test.name
                    if python_test_version != CUSTOM_TEST_IDENTIFIER
                    else test.name + "-" + CUSTOM_TEST_IDENTIFIER,
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

            if not self.python_test.path:
                raise PythonTestCaseError(
                    f"Missing file path for python test {self.python_test.name}"
                )

            # THIS IS A WORKAROUND CODE for TE2
            # Issue: https://github.com/project-chip/certification-tool/issues/152
            test_name = self.python_test.name
            if test_name == "TC_DGGEN_2_4":  # spell-checker: disable
                test_name = "TC_GEN_2_4"
            elif test_name in [
                "TC_DT_1_1",
                "TC_IDM_10_1",
                "TC_IDM_11_1",
                "TC_DESC_2_2",
            ]:
                test_name = test_name[3:]

            command = [
                f"{RUNNER_CLASS_PATH} {self.python_test.path.stem}"
                f" {self.python_test.class_name} --tests test_{test_name}"
            ]

            # Generate the command argument by getting the test_parameters from
            # project configuration
            # comissioning method is omitted because it's handled by the test suite
            command_arguments = generate_command_arguments(
                config=self.config, omit_commissioning_method=True
            )
            command.extend(command_arguments)

            if self.sdk_container.pics_file_created:
                command.append(f" --PICS {PICS_FILE_PATH}")

            exec_result = self.sdk_container.send_command(
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

            # Python tests that don't follow the template only have the 2 default steps
            # and, at this point, will still be in the first step because of the
            # step_over method. So we have to explicitly move on to the next step here.
            # The tests that do follow the template will have additional steps and will
            # have already been moved to the correct step by the hooks' step methods.
            if len(self.test_steps) == 2:
                self.next_step()

            logger.info("---- Start of Python test logs ----")
            handle_logs(cast(Generator, exec_result.output), logger)
            logger.info("---- End of Python test logs ----")

            self.current_test_step.mark_as_completed()
        finally:
            pass

    def skip_to_last_step(self) -> None:
        self.current_test_step.mark_as_completed()
        self.current_test_step_index = len(self.test_steps) - 1
        self.current_test_step.mark_as_executing()

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


class NoCommissioningPythonTestCase(PythonTestCase):
    async def setup(self) -> None:
        await super().setup()
        await prompt_for_commissioning_mode(self, logger, None, self.cancel)


class LegacyPythonTestCase(PythonTestCase):
    async def setup(self) -> None:
        await super().setup()
        await prompt_for_commissioning_mode(self, logger, None, self.cancel)
        await self.prompt_about_commissioning()

    async def prompt_about_commissioning(self) -> None:
        """Prompt the user to ask about commissioning

        Raises:
            ValueError: Prompt response is unexpected
        """

        prompt = "Should the DUT be commissioned to run this test case?"
        options = {
            "YES": PromptOption.YES,
            "NO": PromptOption.NO,
        }
        prompt_request = OptionsSelectPromptRequest(prompt=prompt, options=options)
        logger.info(f'User prompt: "{prompt}"')
        prompt_response = await self.send_prompt_request(prompt_request)

        match prompt_response.response:
            case PromptOption.YES:
                logger.info("User chose prompt option YES")
                logger.info("Commission DUT")
                commission_device(self.config, logger)

            case PromptOption.NO:
                logger.info("User chose prompt option NO")

            case _:
                raise ValueError(
                    f"Received unknown prompt option for \
                        commissioning step: {prompt_response.response}"
                )
