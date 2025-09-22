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

import click
import websockets
from loguru import logger
from pydantic import ValidationError
from websockets.client import WebSocketClientProtocol
from websockets.client import connect as websocket_connect

from th_cli.api_lib_autogen.models import (
    TestCaseExecution,
    TestRunExecutionWithChildren,
    TestStepExecution,
    TestSuiteExecution,
)
from th_cli.colorize import HierarchyEnum, colorize_error, colorize_hierarchy_prefix, colorize_state
from th_cli.config import config

from .prompt_manager import handle_file_upload_request, handle_prompt
from .socket_schemas import (
    MessageTypeEnum,
    PromptRequest,
    SocketMessage,
    StreamVerificationPromptRequest,
    ImageVerificationPromptRequest,
    TestCaseUpdate,
    TestLogRecord,
    TestRunUpdate,
    TestStepUpdate,
    TestSuiteUpdate,
    TestUpdate,
    TimeOutNotification,
)

WEBSOCKET_URL = f"ws://{config.hostname}/api/v1/ws"


class TestRunSocket:
    def __init__(self, run: TestRunExecutionWithChildren):
        self.run = run

    async def connect_websocket(self) -> None:

        async with websocket_connect(WEBSOCKET_URL, ping_timeout=None) as socket:
            while True:
                try:
                    message = await socket.recv()
                except websockets.exceptions.ConnectionClosedOK:
                    return

                # skip messages that are bytes, as we're expecting a string.\
                if not isinstance(message, str):
                    click.echo(
                        colorize_error("Failed to parse incoming websocket message. got bytes, expected text"),
                        err=True,
                    )
                    continue
                try:
                    message_obj = SocketMessage.parse_raw(message)
                    await self.__handle_incoming_socket_message(socket=socket, message=message_obj)
                except ValidationError as e:
                    click.echo(colorize_error(f"Received invalid socket message: {message}"), err=True)
                    click.echo(colorize_error(e.json()), err=True)

    async def __handle_incoming_socket_message(self, socket: WebSocketClientProtocol, message: SocketMessage) -> None:
        if isinstance(message.payload, TestUpdate):
            await self.__handle_test_update(socket=socket, update=message.payload)
        elif isinstance(message.payload, PromptRequest):
            # Debug: log the message type
            logger.debug(f"Received prompt with type: {message.type}")

            # Check message type to route to appropriate handler
            if message.type == MessageTypeEnum.FILE_UPLOAD_REQUEST:
                await handle_file_upload_request(socket=socket, request=message.payload)
            elif message.type == MessageTypeEnum.STREAM_VERIFICATION_REQUEST:
                # Handle video verification with proper separators
                click.echo("=======================================")
                user_response = await self.__handle_video_verification(socket=socket, request=message.payload)
                click.echo("=======================================")
                if user_response is not None:
                    click.echo(f"✅ Response received: {user_response}")
            elif message.type == MessageTypeEnum.IMAGE_VERIFICATION_REQUEST:
                # Convert to ImageVerificationPromptRequest and handle as image
                click.echo(f"🖼️ Detected image verification request!")
                await self.__handle_image_verification(socket=socket, request=message.payload)
            elif message.type in [
                MessageTypeEnum.TWO_WAY_TALK_VERIFICATION_REQUEST,
                MessageTypeEnum.PUSH_AV_STREAM_VERIFICATION_REQUEST,
            ]:
                # Handle as specialized options prompt
                await self.__handle_specialized_prompt(socket=socket, request=message.payload, prompt_type=message.type)
            else:
                await handle_prompt(socket=socket, request=message.payload)
        elif message.type == MessageTypeEnum.TEST_LOG_RECORDS and isinstance(message.payload, list):
            self.__handle_log_record(message.payload)
        elif isinstance(message.payload, TimeOutNotification):
            # ignore time_out_notification as we handle timeout our selves
            pass
        else:
            click.echo(
                colorize_error(f"Unknown socket message type: {message.type} | payload: {message.payload}."),
                err=True,
            )

    async def __handle_test_update(self, socket: WebSocketClientProtocol, update: TestUpdate) -> None:
        if isinstance(update.body, TestStepUpdate):
            self.__log_test_step_update(update.body)
        elif isinstance(update.body, TestCaseUpdate):
            self.__log_test_case_update(update.body)
        elif isinstance(update.body, TestSuiteUpdate):
            self.__log_test_suite_update(update.body)
        elif isinstance(update.body, TestRunUpdate):
            self.__log_test_run_update(update.body)
            if update.body.state != "executing":
                # Test run ended disconnect.
                await socket.close()

    def __log_test_run_update(self, update: TestRunUpdate) -> None:
        test_run_text = colorize_hierarchy_prefix("Test Run", HierarchyEnum.TEST_RUN.value)
        colored_state = colorize_state(update.state.value)
        click.echo(f"{test_run_text} {colored_state}")

    def __log_test_suite_update(self, update: TestSuiteUpdate) -> None:
        suite = self.__suite(update.test_suite_execution_index)
        title = suite.test_suite_metadata.title
        colored_title = colorize_hierarchy_prefix(title, HierarchyEnum.TEST_SUITE.value)
        colored_state = colorize_state(update.state.value)
        click.echo(f"  - {colored_title} {colored_state}")

    def __log_test_case_update(self, update: TestCaseUpdate) -> None:
        case = self.__case(index=update.test_case_execution_index, suite_index=update.test_suite_execution_index)
        title = case.test_case_metadata.title
        colored_title = colorize_hierarchy_prefix(title, HierarchyEnum.TEST_CASE.value)
        colored_state = colorize_state(update.state.value)
        click.echo(f"      - {colored_title} {colored_state}")

    def __log_test_step_update(self, update: TestStepUpdate) -> None:
        step = self.__step(
            index=update.test_step_execution_index,
            case_index=update.test_case_execution_index,
            suite_index=update.test_suite_execution_index,
        )
        if step is not None:
            title = step.title
            colored_title = colorize_hierarchy_prefix(title, HierarchyEnum.TEST_STEP.value)
            colored_state = colorize_state(update.state.value)
            click.echo(f"            - {colored_title} {colored_state}")

    def __handle_log_record(self, records: List[TestLogRecord]) -> None:
        for record in records:
            logger.log(record.level, record.message)

    def __suite(self, index: int) -> TestSuiteExecution:
        return self.run.test_suite_executions[index]

    def __case(self, index: int, suite_index: int) -> TestCaseExecution:
        suite = self.__suite(suite_index)
        return suite.test_case_executions[index]

    def __step(self, index: int, case_index: int, suite_index: int) -> Optional[TestStepExecution]:
        case = self.__case(index=case_index, suite_index=suite_index)
        return case.test_step_executions[index]

    async def __handle_video_verification(self, socket: WebSocketClientProtocol, request: PromptRequest) -> Optional[int]:
        """Handle video verification by calling the video handler directly."""
        # Import here to avoid circular import
        from .prompt_manager import handle_video_prompt_internal

        # Convert to StreamVerificationPromptRequest
        if hasattr(request, 'options'):
            from .socket_schemas import StreamVerificationPromptRequest
            video_request = StreamVerificationPromptRequest(
                prompt=request.prompt,
                timeout=request.timeout,
                message_id=request.message_id,
                options=request.options
            )
            return await handle_video_prompt_internal(socket=socket, prompt=video_request)
        return None

    async def __handle_image_verification(self, socket: WebSocketClientProtocol, request: PromptRequest) -> None:
        """Handle image verification by calling the image handler directly."""
        # Import here to avoid circular import
        from .prompt_manager import handle_image_prompt_direct
        await handle_image_prompt_direct(socket=socket, request=request)

    async def __handle_specialized_prompt(self, socket: WebSocketClientProtocol, request: PromptRequest, prompt_type: str) -> None:
        """Handle specialized prompts like two-way talk or push AV streams."""
        click.echo(f"🎯 Handling specialized prompt: {prompt_type}")
        await handle_prompt(socket=socket, request=request)
