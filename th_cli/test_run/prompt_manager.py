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
import datetime
import json
import os
import re
from pathlib import Path
from typing import Any, Union, Optional

import aioconsole
import aiofiles
import click
import httpx

# from loguru import logger
from websockets.client import WebSocketClientProtocol

from th_cli.colorize import colorize_error, colorize_key_value, italic
from th_cli.config import config

from .socket_schemas import (
    OptionsSelectPromptRequest,
    PromptRequest,
    PromptResponse,
    TextInputPromptRequest,
    StreamVerificationPromptRequest,
    UserResponseStatusEnum,
)

# Constants
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB in bytes

# Global video handler instance for reuse
_video_handler_instance = None


async def handle_prompt(socket: WebSocketClientProtocol, request: PromptRequest, message_type: str = None) -> None:
    """Handle all types of prompts with correct inheritance order."""
    click.echo("=======================================")

    # Import MessageTypeEnum here to avoid circular imports
    from .socket_schemas import MessageTypeEnum

    if message_type == MessageTypeEnum.STREAM_VERIFICATION_REQUEST or isinstance(request, StreamVerificationPromptRequest):
        await __handle_stream_verification_prompt(socket=socket, prompt=request)
    elif isinstance(request, OptionsSelectPromptRequest):
        await __handle_options_prompt(socket=socket, prompt=request)
    elif isinstance(request, TextInputPromptRequest):
        await __handle_text_prompt(socket=socket, prompt=request)
    else:
        click.echo(colorize_error(f"Unsupported prompt request: {request.__class__.__name__}"))

    click.echo("=======================================")

def _get_video_handler():
    """Get or create a reusable video handler instance."""
    global _video_handler_instance
    if _video_handler_instance is None:
        # Import here to avoid circular import
        from .camera import CameraStreamHandler
        _video_handler_instance = CameraStreamHandler()
    return _video_handler_instance


async def _cleanup_video_handler():
    """Clean up the global video handler instance."""
    global _video_handler_instance
    if _video_handler_instance is not None:
        try:
            await _video_handler_instance.stop_video_capture_and_stream()
        except Exception:
            pass  # Ignore cleanup errors


async def __handle_stream_verification_prompt(socket: WebSocketClientProtocol, prompt: PromptRequest) -> None:
    """Handle video stream verification prompts."""
    try:
        # Validate prompt has required attributes
        if not hasattr(prompt, 'options') or not prompt.options:
            click.echo(colorize_error("Video prompt missing required options"), err=True)
            return

        # Get reusable video handler instance
        video_handler = _get_video_handler()
        video_handler.set_prompt_data(prompt.prompt, prompt.options)

        # Start capturing with streaming
        video_file = await video_handler.start_video_capture_and_stream(str(prompt.message_id))

        # Wait 1.5 seconds to ensure stream transmission has started
        await asyncio.sleep(1.5)

        click.echo(italic(prompt.prompt))
        click.echo(f"🎬 Please verify the video at: http://{config.hostname}:8999/")

        click.echo("Waiting for your response in the web interface...")

        # Wait for user response from web UI instead of CLI input
        user_answer = await video_handler.wait_for_user_response(float(prompt.timeout))

        if user_answer is None:
            click.echo(colorize_error("No response received from web interface"), err=True)
            return

        # Display the user's selected response
        selected_option = None
        for option_text, option_id in prompt.options.items():
            if option_id == user_answer:
                selected_option = option_text
                break

        if selected_option:
            click.echo(f"✅ User selected: {colorize_key_value(str(user_answer), selected_option)}")
        else:
            click.echo(f"✅ User response: {user_answer}")

        # Stop video capture and streaming
        final_video_file = await video_handler.stop_video_capture_and_stream()

        await _send_prompt_response(socket=socket, input=user_answer, prompt=prompt)

    except asyncio.exceptions.TimeoutError:
        click.echo(colorize_error("Video prompt timed out"), err=True)
        # Clean up using the shared instance
        await _cleanup_video_handler()
    except Exception as e:
        click.echo(colorize_error(f"Error handling video prompt: {e}"), err=True)
        # Clean up using the shared instance
        await _cleanup_video_handler()


async def handle_file_upload_request(socket: WebSocketClientProtocol, request: PromptRequest) -> None:
    """Handle file upload requests from the backend."""
    click.echo("=======================================")
    await __handle_file_upload_prompt(socket=socket, prompt=request)
    click.echo("=======================================")


async def __handle_options_prompt(socket: WebSocketClientProtocol, prompt: OptionsSelectPromptRequest) -> None:
    try:
        user_answer = await asyncio.wait_for(_prompt_user_for_option(prompt), float(prompt.timeout))
        await _send_prompt_response(socket=socket, input=user_answer, prompt=prompt)
    except asyncio.exceptions.TimeoutError:
        click.echo(colorize_error("Prompt timed out"), err=True)
        pass


async def _prompt_user_for_option(prompt: OptionsSelectPromptRequest) -> int:
    # Print Prompt
    click.echo(italic(prompt.prompt))
    for key in prompt.options.keys():
        id = prompt.options[key]
        click.echo(f"  {colorize_key_value(str(id), key)}")
    click.echo(italic("Please enter a number for an option above: "))

    # Wait for input async
    input = await aioconsole.ainput()

    # validate input
    try:
        input_int = int(input)
        if input_int in prompt.options.values():
            return input_int
    except ValueError:
        pass

    # Recursively Retry
    await asyncio.sleep(0.1)
    click.echo(colorize_error(f"Invalid input {input}"), err=True)
    return await _prompt_user_for_option(prompt)


async def __handle_text_prompt(socket: WebSocketClientProtocol, prompt: TextInputPromptRequest) -> None:
    try:
        user_answer = await asyncio.wait_for(__prompt_user_for_text_input(prompt), float(prompt.timeout))
        await _send_prompt_response(socket=socket, input=user_answer, prompt=prompt)
    except asyncio.exceptions.TimeoutError:
        click.echo(colorize_error("Prompt timed out"), err=True)
        pass


async def __handle_file_upload_prompt(socket: WebSocketClientProtocol, prompt: PromptRequest) -> None:
    """Handle the file upload prompt and user interaction."""
    try:
        file_path = await asyncio.wait_for(__prompt_user_for_file_upload(prompt), float(prompt.timeout))
        if file_path:
            await __upload_file_and_send_response(socket=socket, file_path=file_path, prompt=prompt)
        else:
            # User cancelled or provided empty path
            await _send_prompt_response(socket=socket, input="", prompt=prompt)
    except asyncio.exceptions.TimeoutError:
        click.echo("File upload prompt timed out", err=True)
        pass


async def __prompt_user_for_text_input(prompt: TextInputPromptRequest) -> str:
    # Print Prompt
    click.echo(italic(prompt.prompt))

    # TODO: default value, placeholder.

    # Wait for input async
    input = await aioconsole.ainput()

    # validate input
    if __valid_text_input(input=input, prompt=prompt):
        return input

    # Recursively Retry
    await asyncio.sleep(0.1)
    click.echo(colorize_error(f"Invalid input {input}"), err=True)
    return await __prompt_user_for_text_input(prompt)


async def __prompt_user_for_file_upload(prompt: PromptRequest) -> str:
    """Prompt the user to provide a file path for upload."""
    # Print Prompt
    click.echo(prompt.prompt)

    while True:
        click.echo("Enter the path to the file to upload (or press Enter to skip): ")

        # Wait for input async
        file_path = await aioconsole.ainput()

        # If user just pressed Enter, return empty string
        if not file_path.strip():
            return ""

        # Validate file path and type
        if __valid_file_upload(file_path=file_path, prompt=prompt):
            return file_path

        # Show error and retry (avoiding recursion)
        await asyncio.sleep(0.1)
        click.echo(f"Invalid file path or type: {file_path}", err=True)


async def __upload_file_and_send_response(
    socket: WebSocketClientProtocol, file_path: str, prompt: PromptRequest
) -> None:
    """Send file path as response - let backend handle actual upload."""
    try:
        if not os.path.isfile(file_path):
            click.echo(f"Error: File '{file_path}' does not exist or is not accessible", err=True)
            await _send_prompt_response(socket=socket, input="", prompt=prompt)
            return

        file_size = os.path.getsize(file_path)

        # Check file size limit
        if file_size > MAX_FILE_SIZE:
            click.echo(f"❌ File too large: {file_size} bytes (max: {MAX_FILE_SIZE} bytes)", err=True)
            await _send_prompt_response(socket=socket, input="", prompt=prompt)
            return

        click.echo(f"File selected: {file_path} (size: {file_size:,} bytes)")

        # Build upload URL - handle both hostname and hostname:port formats
        base_url = config.hostname
        if not base_url.startswith(("http://", "https://")):
            base_url = f"http://{base_url}"
        upload_url = f"{base_url}/api/v1/test_run_executions/file_upload/"

        async with httpx.AsyncClient() as client:
            # Read file asynchronously using aiofiles
            async with aiofiles.open(file_path, 'rb') as f:
                file_content = await f.read()

            files = {"file": (os.path.basename(file_path), file_content, "application/octet-stream")}
            response = await client.post(upload_url, files=files)

            if response.status_code == 200:
                click.echo("✅ File uploaded successfully")
                await _send_prompt_response(socket=socket, input="SUCCESS", prompt=prompt)
            else:
                click.echo(f"❌ File upload failed: {response.status_code} - {response.text}", err=True)
                await _send_prompt_response(socket=socket, input="", prompt=prompt)

    except httpx.RequestError as e:
        click.echo(f"❌ Network error during file upload: {str(e)}", err=True)
        await _send_prompt_response(socket=socket, input="", prompt=prompt)
    except httpx.HTTPStatusError as e:
        click.echo(f"❌ HTTP error during file upload: {e.response.status_code} - {e.response.text}", err=True)
        await _send_prompt_response(socket=socket, input="", prompt=prompt)
    except Exception as e:
        click.echo(f"❌ Unexpected error uploading file: {str(e)}", err=True)
        await _send_prompt_response(socket=socket, input="", prompt=prompt)


def __valid_text_input(input: Any, prompt: TextInputPromptRequest) -> bool:
    if not isinstance(input, str):
        return False

    if prompt.regex_pattern is None:
        return True

    return re.match(prompt.regex_pattern, input) is not None


def __valid_file_upload(file_path: str, prompt: PromptRequest) -> bool:
    """Validate that the file path is valid and the file is accessible."""

    if not os.path.isfile(file_path) or not os.access(file_path, os.R_OK):
        return False

    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext not in [".txt", ".log"]:
        click.echo(f"Error: Invalid file type '{file_ext}'. Only .txt and .log files are supported.", err=True)
        return False

    return True


async def _send_prompt_response(
    socket: WebSocketClientProtocol, input: Union[str, int], prompt: PromptRequest
) -> None:
    response = PromptResponse(
        response=input,
        status_code=UserResponseStatusEnum.OKAY,
        message_id=prompt.message_id,
    )
    payload_dict = {
        "type": "prompt_response",
        "payload": response.dict(),
    }
    payload = json.dumps(payload_dict)
    await socket.send(payload)
