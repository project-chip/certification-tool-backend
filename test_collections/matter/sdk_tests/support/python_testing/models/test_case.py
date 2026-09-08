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
import codecs
import re
from asyncio import sleep
from inspect import iscoroutinefunction
from multiprocessing.managers import BaseManager
from pathlib import Path
from socket import SocketIO
from typing import Any, Optional, Type, TypeVar

from app.constants.shared_constants import NFC_PAIRING_MODES
from app.core.config import settings
from app.models import TestCaseExecution
from app.schemas.test_environment_config import get_th_config_value
from app.test_engine.logger import PYTHON_TEST_LEVEL
from app.test_engine.logger import test_engine_logger as logger
from app.test_engine.models import TestCase, TestStep
from app.test_engine.models.manual_test_case import TestError
from app.test_engine.models.test_case import CUSTOM_TEST_IDENTIFIER
from app.user_prompt_support import PromptResponse, UserResponseStatusEnum
from app.user_prompt_support.prompt_request import (
    ImageVerificationPromptRequest,
    OptionsSelectPromptRequest,
    PromptRequest,
    PushAVStreamVerificationRequest,
    StreamVerificationPromptRequest,
    TextInputPromptRequest,
    TwoWayTalkVerificationRequest,
)
from app.user_prompt_support.user_prompt_support import UserPromptSupport
from test_collections.matter.test_environment_config import TestEnvironmentConfigMatter

from ...pics import PICS_FILE_PATH
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
    TEST_OUTPUT_FILE_PATH,
    DUTCommissioningError,
    PromptOption,
    commission_device,
    generate_command_arguments,
    should_perform_new_commissioning,
)

# Timeout for user prompts in seconds.
USER_PROMPT_TIMEOUT = 120

# Log batching configuration
LOG_BATCH_SIZE = 50  # Number of log lines to send per batch
LOG_BATCH_DELAY = 0.01  # Delay in seconds between batches (10ms)

# Marker prefix printed by the SDK before each test step's output
STEP_MARKER_PREFIX = "***** Test Step "

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
    test_socket: Optional[SocketIO]

    def __init__(self, test_case_execution: TestCaseExecution) -> None:
        super().__init__(test_case_execution=test_case_execution)
        self.__runned = 0
        self.test_stop_called = False
        self.test_socket = None
        self.file_output_path: Optional[Path] = None
        self.current_python_step_name: Optional[str] = None
        self._cached_file_content: str = ""
        self._last_file_size: int = 0
        self._last_logged_position: int = 0  # Track last logged position
        self._remaining_content_logged: bool = False
        # Incremental UTF-8 decoder for _read_file_incrementally(). A plain
        # `open(..., encoding="utf-8")` decodes each call's bytes in
        # isolation - if a multi-byte character's bytes are split across two
        # incremental reads (very possible while the file is still growing),
        # errors="replace" doesn't defer it, it corrupts it into U+FFFD
        # immediately with no way to recover. An incremental decoder holds
        # back any incomplete trailing bytes and completes the character
        # once the rest arrives on the next call.
        self._utf8_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")

    # Move to the next step if the test case has additional steps apart from the 2
    # deafult ones
    def step_over(self) -> None:
        self.next_step()

    def start(self, count: int) -> None:
        pass

    def stop(self, duration: int) -> None:
        if not self.test_stop_called:
            self.current_test_step.mark_as_completed()

    def test_start(
        self, filename: str, name: str, count: int, steps: list[str] = []
    ) -> None:
        pass

    def test_stop(self, exception: Exception, duration: int) -> None:
        self.test_stop_called = True

    def test_skipped(self, filename: str, name: str) -> None:
        self.mark_as_not_applicable()
        self.skip_to_last_step()

    def step_skipped(self, name: str, expression: str) -> None:
        # From TH perspective, Legacy test cases shows only 2 steps in UI
        # but it may have several in the script file.
        # So TH should not skip the step in order to keep the test execution flow
        skiped_msg = "Test step skipped"
        if self.python_test.python_test_type == PythonTestType.LEGACY:
            logger.info(skiped_msg)
        else:
            self.current_test_step.mark_as_not_applicable(skiped_msg)

    def step_start(self, name: str) -> None:
        self.current_python_step_name = name
        self.step_over()

    async def step_success(
        self, logger: Any, logs: str, duration: int, request: Any
    ) -> None:
        # Display logs captured during this step only if real-time logging is enabled
        if self._realtime_logs_enabled():
            await self._display_step_logs()

    def _safe_config(self) -> Optional[dict]:
        """`.config`, or None if it's unavailable (e.g. a test double with no
        wired-up project/execution chain). Used by the th_config resolvers below,
        whose contract is to fall back to the env var default rather than raise
        when project config can't be determined."""
        try:
            return self.config
        except Exception:
            return None

    def _realtime_logs_enabled(self) -> bool:
        """Whether Python test logs should be displayed incrementally per step.

        The project's th_config.enable_realtime_python_test_logs, when explicitly
        set, overrides the instance-wide ENABLE_REALTIME_PYTHON_TEST_LOGS env var.
        """
        override = get_th_config_value(
            self._safe_config(), "enable_realtime_python_test_logs"
        )
        if override is not None:
            return bool(override)
        return settings.ENABLE_REALTIME_PYTHON_TEST_LOGS

    def _container_logs_enabled(self) -> bool:
        """Whether container-operation logging is enabled.

        The project's th_config.enable_container_logs, when explicitly set,
        overrides the instance-wide ENABLE_CONTAINER_LOGS env var.
        """
        override = get_th_config_value(self._safe_config(), "enable_container_logs")
        if override is not None:
            return bool(override)
        return settings.ENABLE_CONTAINER_LOGS

    async def _display_step_logs(self) -> None:
        """Display logs that were captured during the current step."""
        # Validate file path is set and file exists
        if not self.file_output_path:
            logger.debug("Test output file not found, skipping log display")
            return

        if not self.file_output_path.exists():
            logger.debug(f"Test output file does not exist: {self.file_output_path}")
            return

        if not self.current_python_step_name:
            return

        try:
            # Read file content with incremental caching for performance
            content = self._read_file_incrementally()

            # Extract logs for the current step (returns tuple of logs and end position)
            step_logs, end_pos = self._extract_logs_for_step(
                content, self.current_python_step_name
            )

            if step_logs:
                # Send logs in batches to avoid overwhelming the UI
                for i in range(0, len(step_logs), LOG_BATCH_SIZE):
                    batch = step_logs[i : i + LOG_BATCH_SIZE]
                    for line in batch:
                        logger.log(PYTHON_TEST_LEVEL, line)
                    # Small delay between batches to allow UI to process
                    if i + LOG_BATCH_SIZE < len(step_logs):
                        await sleep(LOG_BATCH_DELAY)

                # Update last logged position with the end position from extraction
                if end_pos > self._last_logged_position:
                    self._last_logged_position = end_pos

        except (IOError, OSError) as e:
            logger.warning(f"Failed to read test output file: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error while displaying step logs: {e}", exc_info=True
            )

    def _read_file_incrementally(self) -> str:
        """Read file incrementally, caching content to avoid re-reading entire file.

        Reads in binary mode and feeds bytes through a persistent
        incremental UTF-8 decoder, rather than independently decoding each
        call's bytes in text mode. Binary-mode seeks are always byte-safe
        (unlike seeking a text-mode handle to an arbitrary byte offset), and
        the incremental decoder correctly withholds any incomplete trailing
        multi-byte character across calls instead of corrupting it.

        Returns:
            Full content of the file up to current position
        """
        # Validate file path is set
        if not self.file_output_path:
            return self._cached_file_content

        try:
            current_size = self.file_output_path.stat().st_size

            # If file hasn't grown, return cached content
            if current_size == self._last_file_size and self._cached_file_content:
                return self._cached_file_content

            # File has grown, read only new content
            if current_size > self._last_file_size and self._cached_file_content:
                with open(self.file_output_path, "rb") as f:
                    f.seek(self._last_file_size)
                    new_bytes = f.read()
                self._cached_file_content += self._utf8_decoder.decode(new_bytes)
            else:
                # First read or file was truncated - reset decoder state too,
                # so any bytes withheld from a previous (now-stale) read
                # don't get prepended to unrelated new content.
                self._utf8_decoder.reset()
                with open(self.file_output_path, "rb") as f:
                    new_bytes = f.read()
                self._cached_file_content = self._utf8_decoder.decode(new_bytes)

            self._last_file_size = current_size
            return self._cached_file_content

        except (IOError, OSError):
            return self._cached_file_content

    def _extract_logs_for_step(
        self, content: str, step_name: str
    ) -> tuple[list[str], int]:
        """Extract logs for a specific test step from the full log content.

        Args:
            content: Full content of the test output file
            step_name: The step name (as passed to step_start) to extract logs for

        Returns:
            Tuple of:
            - list of log lines for the specified step.
            - End position of step content
        """
        current_step_marker = f"{STEP_MARKER_PREFIX}{step_name}"

        # Search starting at the last logged position rather than from the
        # beginning of the file, so repeated/similar step labels across loop
        # iterations resolve to the correct occurrence and the whole
        # (growing) file isn't rescanned on every step.
        start_idx = content.find(current_step_marker, self._last_logged_position)
        if start_idx == -1:
            # No match yet (e.g. the SDK hasn't written this step's marker to
            # disk yet) — don't regress the cursor, just report nothing new.
            return ([], self._last_logged_position)

        # Find the start position of the next step's marker
        next_idx = content.find(
            STEP_MARKER_PREFIX, start_idx + len(current_step_marker)
        )

        # Extract the section between current and next step
        if next_idx != -1:
            step_content = content[start_idx:next_idx]
            end_pos = next_idx
        else:
            # Last step, extract until end of content
            step_content = content[start_idx:]
            end_pos = len(content)

        # Split into lines and return with end position
        return (step_content.split("\n"), end_pos)

    async def step_failure(
        self, logger: Any, logs: str, duration: int, request: Any, received: Any
    ) -> None:
        # Display logs captured during this step before marking as failure
        # only if real-time logging is enabled
        if self._realtime_logs_enabled():
            await self._display_step_logs()

        failure_msg = "Python test step failure"
        if logs:
            failure_msg += f": {logs}"

        self.mark_step_failure(failure_msg)
        self.skip_to_last_step()

    def step_unknown(self) -> None:
        self.__runned += 1

    async def _show_prompt_request(self, request: PromptRequest) -> None:
        user_response = await self.send_prompt_request(request)

        if self.test_socket:
            # Always send something to unblock the SDK's input() call.
            # On timeout/cancel response_str is None, so fall back to default_value
            # or an empty line — otherwise the SDK process hangs waiting on stdin.
            reply = (
                user_response.response_str
                or getattr(request, "default_value", None)
                or ""
            )
            self.test_socket._sock.sendall(  # type: ignore[attr-defined]
                f"{reply}\n".encode()
            )

        self.__evaluate_user_response_for_errors(user_response)

    async def show_prompt(
        self,
        msg: str,
        placeholder: Optional[str] = None,
        default_value: Optional[str] = None,
    ) -> None:
        prompt_request = TextInputPromptRequest(
            prompt=msg,
            placeholder_text=placeholder,
            default_value=default_value,
        )
        await self._show_prompt_request(prompt_request)

    async def show_video_prompt(self, msg: str) -> None:
        options = {
            "PASS": PromptOption.PASS,
            "FAIL": PromptOption.FAIL,
        }
        prompt_request = StreamVerificationPromptRequest(
            prompt=msg, options=options, timeout=USER_PROMPT_TIMEOUT
        )
        await self._show_prompt_request(prompt_request)

    async def show_image_prompt(self, msg: str, img_hex_str: str) -> None:
        options = {
            "PASS": PromptOption.PASS,
            "FAIL": PromptOption.FAIL,
        }
        prompt_request = ImageVerificationPromptRequest(
            prompt=msg,
            options=options,
            timeout=USER_PROMPT_TIMEOUT,
            image_hex_str=img_hex_str,
        )
        await self._show_prompt_request(prompt_request)

    async def show_push_av_stream_prompt(self, msg: str) -> None:
        options = {
            "PASS": PromptOption.PASS,
            "FAIL": PromptOption.FAIL,
        }
        prompt_request = PushAVStreamVerificationRequest(
            prompt=msg, options=options, timeout=USER_PROMPT_TIMEOUT
        )
        await self._show_prompt_request(prompt_request)

    async def show_two_way_talk_prompt(self, msg: str) -> None:
        options = {
            "PASS": PromptOption.PASS,
            "FAIL": PromptOption.FAIL,
        }
        prompt_request = TwoWayTalkVerificationRequest(
            prompt=msg, options=options, timeout=120  # 120 Seconds
        )
        await self._show_prompt_request(prompt_request)

    @classmethod
    def pics(cls) -> set[str]:
        """Test Case level PICS. Read directly from parsed Python Test."""
        return cls.python_test.PICS

    @classmethod
    def class_factory(
        cls, test: PythonTest, python_test_version: str, mandatory: bool
    ) -> Type[T]:
        """Dynamically declares a subclass based on the type of Python test."""
        case_class: Type[PythonTestCase]

        if test.python_test_type == PythonTestType.NO_COMMISSIONING:
            case_class = NoCommissioningPythonTestCase
        elif (
            test.python_test_type == PythonTestType.LEGACY
            or test.python_test_type == PythonTestType.MANDATORY
        ):
            case_class = LegacyPythonTestCase
        else:  # Commissioning
            case_class = PythonTestCase

        return case_class.__class_factory(
            test=test, python_test_version=python_test_version, mandatory=mandatory
        )

    @classmethod
    def __class_factory(
        cls, test: PythonTest, python_test_version: str, mandatory: bool
    ) -> Type[T]:
        """class factory method for PythonTestCase."""
        title = cls.__title(test.name)
        class_name = cls.__class_name(test.name)
        custom_suffix = (
            f"-{CUSTOM_TEST_IDENTIFIER}"
            if python_test_version == CUSTOM_TEST_IDENTIFIER
            else ""
        )

        return type(
            class_name,
            (cls,),
            {
                "python_test": test,
                "python_test_version": python_test_version,
                "metadata": {
                    "public_id": test.name + custom_suffix,
                    "version": "0.0.1",
                    "title": title + custom_suffix,
                    "description": test.description,
                    "mandatory": mandatory,
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

    @staticmethod
    def _get_sdk_tests_base_path() -> Path:
        """Get the base path for SDK tests directory.

        This method safely navigates the directory structure to find the sdk_tests
        directory, handling potential changes in file organization.

        Returns:
            Path to the sdk_tests base directory

        Raises:
            FileNotFoundError: If the sdk_tests directory cannot be found
        """
        current_file = Path(__file__).resolve()

        # Navigate up from current file to find sdk_tests directory
        # Current structure: .../sdk_tests/support/python_testing/models/test_case.py
        for parent in current_file.parents:
            if parent.name == "sdk_tests":
                return parent

        # Fallback: try parents[3] for backward compatibility
        try:
            return Path(__file__).parents[3]
        except IndexError:
            raise FileNotFoundError(
                f"Could not determine sdk_tests base path from {current_file}. "
                "Directory structure may have changed."
            )

    async def setup(self) -> None:
        logger.info("Test Setup")

    async def cleanup(self) -> None:
        logger.info("Test Cleanup")
        # Log any remaining content that wasn't captured by steps
        # only if real-time logging is enabled
        if self._realtime_logs_enabled():
            await self._log_remaining_content()
        else:
            # Use batch logging when real-time logging is disabled
            await self.display_batch_logs()

    async def _log_remaining_content(self) -> None:
        """Log any content from the test output file that wasn't logged yet."""
        # Check idempotency flag to prevent duplicate logging
        if self._remaining_content_logged:
            return

        # Validate file path is set
        if not self.file_output_path:
            logger.debug(
                "Test output file path not found, " "skipping remaining content logging"
            )
            return

        if not self.file_output_path.exists():
            logger.debug(f"Test output file does not exist: {self.file_output_path}")
            return

        try:
            # Reuse the incremental reader (rather than a second, independent
            # full read) to pick up anything appended since the last call and
            # fold it into the cache. This used to deliberately bypass the
            # cache "so this catch-all reliably recovers everything
            # regardless of whether the incremental/per-step read path hit
            # an error earlier" - that hedge existed because
            # _read_file_incrementally() used to be able to silently corrupt
            # content at chunk boundaries. Now that it decodes incrementally
            # and byte-safely, there's no need to duplicate the whole file
            # in memory a second time here.
            content = self._read_file_incrementally()

            # Check if there's content after the last logged position
            if self._last_logged_position < len(content):
                remaining_content = content[self._last_logged_position :]

                if remaining_content.strip():
                    logger.info("---- Remaining logs not captured by steps ----")
                    # Log in batches (like _display_step_logs) instead of one
                    # unbroken call, so a large backlog doesn't monopolize the
                    # event loop for an extended stretch in one go.
                    remaining_lines = remaining_content.split("\n")
                    for i in range(0, len(remaining_lines), LOG_BATCH_SIZE):
                        batch = remaining_lines[i : i + LOG_BATCH_SIZE]
                        for line in batch:
                            logger.log(PYTHON_TEST_LEVEL, line)
                        if i + LOG_BATCH_SIZE < len(remaining_lines):
                            await sleep(LOG_BATCH_DELAY)
                    logger.info("---- End of remaining logs ----")

            # Mark as logged to prevent duplicate calls
            self._remaining_content_logged = True

        except (IOError, OSError) as e:
            logger.warning(f"Failed to read remaining test output: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error while logging remaining content: {e}", exc_info=True
            )

    async def display_batch_logs(self) -> None:
        """Batch logging method for when real-time logging is disabled.

        This method logs all test output at once after test execution completes,
        rather than displaying logs incrementally as each step executes.
        """
        # Check idempotency flag to prevent duplicate logging
        if getattr(self, "_batch_logs_displayed", False):
            return

        # Validate file path is set
        if not self.file_output_path:
            logger.debug("Test output file not found, skipping log display")
            return

        if not self.file_output_path.exists():
            logger.debug(f"Test output file does not exist: {self.file_output_path}")
            return

        try:
            logger.info("---- Start of Python test logs ----")
            with open(
                self.file_output_path, "r", encoding="utf-8", errors="replace"
            ) as f:
                # Iterate the file object directly instead of readlines():
                # file iteration is already lazily buffered by Python, so
                # this never materializes the whole (potentially 100MB+)
                # file as one in-memory list before logging/pacing even
                # starts.
                batch_count = 0
                for line in f:
                    logger.log(PYTHON_TEST_LEVEL, line.rstrip("\n"))
                    batch_count += 1
                    if batch_count >= LOG_BATCH_SIZE:
                        batch_count = 0
                        # Yield to the event loop between batches, so a
                        # large file doesn't monopolize it for an extended
                        # stretch in one go.
                        await sleep(LOG_BATCH_DELAY)
            logger.info("---- End of Python test logs ----")
        except (IOError, OSError) as e:
            logger.warning(f"Failed to read test output file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while reading logs: {e}", exc_info=True)

        setattr(self, "_batch_logs_displayed", True)

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

            # get script path including folder (sdk or custom) and excluding extension
            test_script_relative_path = Path(
                *self.python_test.path.parts[-2:]
            ).with_suffix("")

            command = [
                f"{RUNNER_CLASS_PATH} --th-client-test {test_script_relative_path}"
                f" {self.python_test.class_name} --tests test_{self.python_test.name}"
            ]

            # Generate the command argument by getting the test_parameters from
            # project configuration
            # comissioning method is omitted because it's handled by the test suite
            config = TestEnvironmentConfigMatter(**self.config)

            # For COMMISSIONING tests running under CommissioningPythonTestSuite with
            # an NFC pairing mode, qr-code in test_parameters must be dropped —
            # the onboarding data comes from the NFC tag. For NO_COMMISSIONING tests
            # like TC_DD_1_5, qr-code is a legitimate input and must be preserved.
            pairing_mode = config.dut_config.pairing_mode
            if (
                self.python_test.python_test_type == PythonTestType.COMMISSIONING
                and pairing_mode in NFC_PAIRING_MODES
                and config.test_parameters
                and "qr-code" in config.test_parameters
            ):
                logger.warning(
                    f"pairing_mode is {pairing_mode}: qr-code in test_parameters is"
                    " ignored for Python Testing Suite - Auto commissioning."
                    "Onboarding data is read from the NFC tag."
                )
                config = config.copy(
                    update={
                        "test_parameters": {
                            k: v
                            for k, v in config.test_parameters.items()
                            if k != "qr-code"
                        }
                    }
                )

            command_arguments = await generate_command_arguments(
                config=config,
                omit_commissioning_method=True,
            )
            command.extend(command_arguments)

            if self.sdk_container.pics_file_created:
                command.append(f" --PICS {PICS_FILE_PATH}")

            exec_result = self.sdk_container.send_command(
                command,
                prefix=EXECUTABLE,
                is_stream=True,
                is_socket=True,
                enable_container_logs=self._container_logs_enabled(),
            )
            self.test_socket = exec_result.socket

            # Initialize file output path for step-by-step log capture
            try:
                sdk_tests_path = self._get_sdk_tests_base_path()
                self.file_output_path = sdk_tests_path / TEST_OUTPUT_FILE_PATH

                # Validate that the output directory exists
                output_dir = self.file_output_path.parent
                if not output_dir.exists():
                    logger.warning(
                        f"Test output directory does not exist: {output_dir}. "
                        "It will be created when tests run."
                    )
            except FileNotFoundError as e:
                logger.error(f"Failed to initialize test output path: {e}")
                self.file_output_path = None

            while ((update := test_runner_hooks.update_test()) is not None) or (
                not test_runner_hooks.is_finished()
            ):
                if not update:
                    await sleep(0.0001)
                    continue

                await self.__handle_update(update)

            # Step: Show test logs
            if self.current_test_step_index < len(self.test_steps) - 1:
                self.skip_to_last_step()

            # Check for any remaining logs that weren't captured by steps
            # or show all logs if real-time logging is disabled
            if self._realtime_logs_enabled():
                await self._log_remaining_content()
            else:
                # Use batch logging when real-time logging is disabled
                await self.display_batch_logs()

            self.current_test_step.mark_as_completed()
        finally:
            pass

    def skip_to_last_step(self) -> None:
        self.current_test_step.mark_as_completed()
        self.current_test_step_index = len(self.test_steps) - 1
        self.current_test_step.mark_as_executing()

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
        self.test_steps = [TestStep("Start Python test")]
        for step in self.python_test.steps:
            python_test_step = TestStep(step.label)
            self.test_steps.append(python_test_step)
        self.test_steps.append(TestStep("Show test logs"))

    def __evaluate_user_response_for_errors(
        self, prompt_response: PromptResponse
    ) -> None:
        if prompt_response is None:
            raise TestError("User response returned Null.")

        if prompt_response.status_code == UserResponseStatusEnum.TIMEOUT:
            raise TestError("Prompt timed out.")

        if prompt_response.status_code == UserResponseStatusEnum.CANCELLED:
            raise TestError("User cancelled the prompt.")


class NoCommissioningPythonTestCase(PythonTestCase):
    async def setup(self) -> None:
        await super().setup()

        logger.info("Setup -  No Commissioning Python Test Case")


class LegacyPythonTestCase(PythonTestCase):
    async def setup(self) -> None:
        await super().setup()

        logger.info("Setup -  Legacy Python Test Case")

        await self.prompt_about_commissioning()

    async def prompt_about_commissioning(self) -> None:
        """Prompt the user to ask about commissioning

        Raises:
            ValueError: Prompt response is unexpected
        """

        prompt = "Should the DUT be commissioned to run this test case?"
        options = {
            "YES": PromptOption.PASS,
            "NO": PromptOption.FAIL,
        }
        prompt_request = OptionsSelectPromptRequest(prompt=prompt, options=options)
        logger.info(f'User prompt: "{prompt}"')
        prompt_response = await self.send_prompt_request(prompt_request)

        match prompt_response.response:
            case PromptOption.PASS:
                config = TestEnvironmentConfigMatter(**self.config)

                # If a local copy of admin_storage.json file exists, prompt user if the
                # execution should retrieve the previous commissioning information or
                # if it should perform a new commissioning
                if await should_perform_new_commissioning(
                    self, config=config, logger=logger
                ):
                    logger.info("User chose prompt option YES")
                    user_response = await prompt_for_commissioning_mode(
                        self, logger, None, self.cancel
                    )
                    if user_response == PromptOption.FAIL:
                        raise DUTCommissioningError(
                            "User chose prompt option FAILED for DUT is in "
                            "Commissioning Mode"
                        )

                    logger.info("Commission DUT")
                    await commission_device(config, logger)

            case PromptOption.FAIL:
                logger.info("User chose prompt option NO")
                user_response = await prompt_for_commissioning_mode(
                    self, logger, None, self.cancel
                )
                if user_response == PromptOption.FAIL:
                    raise DUTCommissioningError(
                        "User chose prompt option FAILED for DUT is in "
                        "Commissioning Mode"
                    )

            case _:
                raise ValueError(
                    f"Received unknown prompt option for \
                        commissioning step: {prompt_response.response}"
                )
