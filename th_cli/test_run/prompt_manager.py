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
import json
import os
import re
from typing import Any, Union

import aioconsole
import click
import httpx

# from loguru import logger
from websockets.client import WebSocketClientProtocol

from th_cli.colorize import colorize_error, colorize_key_value, italic
from th_cli.config import config

from .video_handler import VideoStreamHandler

from .socket_schemas import (
    OptionsSelectPromptRequest,
    PromptRequest,
    PromptResponse,
    TextInputPromptRequest,
    StreamVerificationPromptRequest,
    ImageVerificationPromptRequest,
    TwoWayTalkVerificationRequest,
    PushAVStreamVerificationRequest,
    UserResponseStatusEnum,
)

# Constants
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB in bytes


async def handle_prompt(socket: WebSocketClientProtocol, request: PromptRequest) -> None:
    click.echo("=======================================")
    if isinstance(request, OptionsSelectPromptRequest):
        await __handle_options_prompt(socket=socket, prompt=request)
    elif isinstance(request, TextInputPromptRequest):
        await __handle_text_prompt(socket=socket, prompt=request)
    elif isinstance(request, StreamVerificationPromptRequest):
        await __handle_video_prompt(socket=socket, prompt=request)
    elif isinstance(request, ImageVerificationPromptRequest):
        await __handle_image_prompt(socket=socket, prompt=request)
    elif isinstance(request, (TwoWayTalkVerificationRequest, PushAVStreamVerificationRequest)):
        await __handle_options_prompt(socket=socket, prompt=request)
    else:
        click.echo(colorize_error(f"Unsupported prompt request: {request.__class__.__name__}"))
    click.echo("=======================================")


async def handle_file_upload_request(socket: WebSocketClientProtocol, request: PromptRequest) -> None:
    """Handle file upload requests from the backend."""
    click.echo("=======================================")
    await __handle_file_upload_prompt(socket=socket, prompt=request)
    click.echo("=======================================")


async def __handle_options_prompt(socket: WebSocketClientProtocol, prompt: OptionsSelectPromptRequest) -> None:
    try:
        user_answer = await asyncio.wait_for(__prompt_user_for_option(prompt), float(prompt.timeout))
        await __send_prompt_response(socket=socket, input=user_answer, prompt=prompt)
    except asyncio.exceptions.TimeoutError:
        click.echo(colorize_error("Prompt timed out"), err=True)
        pass


async def __prompt_user_for_option(prompt: OptionsSelectPromptRequest) -> int:
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
    return await __prompt_user_for_option(prompt)


async def __handle_text_prompt(socket: WebSocketClientProtocol, prompt: TextInputPromptRequest) -> None:
    try:
        user_answer = await asyncio.wait_for(__prompt_user_for_text_input(prompt), float(prompt.timeout))
        await __send_prompt_response(socket=socket, input=user_answer, prompt=prompt)
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
            await __send_prompt_response(socket=socket, input="", prompt=prompt)
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
            await __send_prompt_response(socket=socket, input="", prompt=prompt)
            return

        file_size = os.path.getsize(file_path)

        # Check file size limit
        if file_size > MAX_FILE_SIZE:
            click.echo(f"❌ File too large: {file_size} bytes (max: {MAX_FILE_SIZE} bytes)", err=True)
            await __send_prompt_response(socket=socket, input="", prompt=prompt)
            return

        click.echo(f"File selected: {file_path} (size: {file_size:,} bytes)")

        # Build upload URL - handle both hostname and hostname:port formats
        base_url = config.hostname
        if not base_url.startswith(("http://", "https://")):
            base_url = f"http://{base_url}"
        upload_url = f"{base_url}/api/v1/test_run_executions/file_upload/"

        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as file:
                files = {"file": (os.path.basename(file_path), file, "application/octet-stream")}

                response = await client.post(upload_url, files=files)

                if response.status_code == 200:
                    click.echo("✅ File uploaded successfully")
                    await __send_prompt_response(socket=socket, input="SUCCESS", prompt=prompt)
                else:
                    click.echo(f"❌ File upload failed: {response.status_code} - {response.text}", err=True)
                    await __send_prompt_response(socket=socket, input="", prompt=prompt)

    except httpx.RequestError as e:
        click.echo(f"❌ Network error during file upload: {str(e)}", err=True)
        await __send_prompt_response(socket=socket, input="", prompt=prompt)
    except httpx.HTTPStatusError as e:
        click.echo(f"❌ HTTP error during file upload: {e.response.status_code} - {e.response.text}", err=True)
        await __send_prompt_response(socket=socket, input="", prompt=prompt)
    except Exception as e:
        click.echo(f"❌ Unexpected error uploading file: {str(e)}", err=True)
        await __send_prompt_response(socket=socket, input="", prompt=prompt)


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


async def __send_prompt_response(
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


async def __handle_video_prompt(socket: WebSocketClientProtocol, prompt: StreamVerificationPromptRequest) -> None:
    """Handle video stream verification prompts."""
    try:
        # Create video handler and start capturing
        video_handler = VideoStreamHandler()
        video_file = await video_handler.start_video_capture(str(prompt.message_id))

        click.echo(italic(prompt.prompt))
        click.echo(f"📹 Video stream is being captured to: {video_file}")
        click.echo("Watch the video stream and answer the verification question:")

        # Show options to user
        for key in prompt.options.keys():
            id = prompt.options[key]
            click.echo(f"  {colorize_key_value(str(id), key)}")

        # Get user response
        user_answer = await asyncio.wait_for(__prompt_user_for_option(prompt), float(prompt.timeout))

        # Stop video capture
        final_video_file = await video_handler.stop_video_capture()
        if final_video_file:
            click.echo(f"✅ Video saved to: {final_video_file}")

        await __send_prompt_response(socket=socket, input=user_answer, prompt=prompt)

    except asyncio.exceptions.TimeoutError:
        click.echo(colorize_error("Video prompt timed out"), err=True)
        # Try to stop video capture on timeout
        video_handler = VideoStreamHandler()
        await video_handler.stop_video_capture()
    except Exception as e:
        click.echo(colorize_error(f"Error handling video prompt: {e}"), err=True)


async def __handle_image_prompt(socket: WebSocketClientProtocol, prompt: ImageVerificationPromptRequest) -> None:
    """Handle image verification prompts."""
    try:
        # Save image from hex string
        video_handler = VideoStreamHandler()
        image_file = video_handler.save_image_from_hex(prompt.image_hex_str, str(prompt.message_id))

        click.echo(italic(prompt.prompt))
        click.echo(f"🖼️  Image saved to: {image_file}")
        click.echo("Please view the image and answer the verification question:")

        # Show options to user
        for key in prompt.options.keys():
            id = prompt.options[key]
            click.echo(f"  {colorize_key_value(str(id), key)}")

        user_answer = await asyncio.wait_for(__prompt_user_for_option(prompt), float(prompt.timeout))
        await __send_prompt_response(socket=socket, input=user_answer, prompt=prompt)

    except asyncio.exceptions.TimeoutError:
        click.echo(colorize_error("Image prompt timed out"), err=True)
    except Exception as e:
        click.echo(colorize_error(f"Error handling image prompt: {e}"), err=True)
