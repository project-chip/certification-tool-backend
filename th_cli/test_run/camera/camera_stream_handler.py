#
# Copyright (c) 2025 Project CHIP Authors
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
import queue
import time
from pathlib import Path
from typing import Optional

import click
from loguru import logger

from th_cli.th_utils.ffmpeg_converter import VideoFileConverter
from .camera_http_server import CameraHTTPServer
from .websocket_manager import VideoWebSocketManager


class CameraStreamHandler:
    """Main coordinator for camera streaming functionality."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / "videos"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Components
        self.websocket_manager = VideoWebSocketManager()
        self.http_server = CameraHTTPServer()

        # State
        self.current_stream_file: Optional[Path] = None
        self.video_queue = queue.Queue()  # Raw H.264 data for live streaming
        self.mp4_queue = queue.Queue()    # Converted MP4 data for live streaming
        self.response_queue = queue.Queue()  # User responses from web UI
        self.prompt_options = {}  # Store prompt options
        self.prompt_text = ""     # Store prompt text

    def set_prompt_data(self, prompt_text: str, options: dict):
        """Set prompt text and options for the web UI."""
        self.prompt_text = prompt_text
        self.prompt_options = options
        logger.info(f"Set prompt options: {options}")

    async def start_video_capture_and_stream(self, prompt_id: str, stream_port: int = 8999) -> Path:
        """Start capturing video stream to file AND serve via HTTP."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"video_verification_{prompt_id}_{timestamp}.bin"
        self.current_stream_file = self.output_dir / filename

        logger.info(f"Starting video capture to: {self.current_stream_file}")

        # Start HTTP server with current prompt data
        self.http_server.start(
            mp4_queue=self.mp4_queue,
            response_queue=self.response_queue,
            video_handler=self,
            prompt_options=self.prompt_options,
            prompt_text=self.prompt_text
        )

        # Start background task for video capture
        asyncio.create_task(self._initialize_video_capture())

        return self.current_stream_file

    async def _initialize_video_capture(self) -> None:
        """Initialize video capture with retry logic."""
        # Try to connect and start capturing
        if await self.websocket_manager.wait_and_connect_with_retry():
            await self.websocket_manager.start_capture_and_stream(
                self.current_stream_file,
                self.video_queue,
                self.mp4_queue
            )

    async def wait_for_user_response(self, timeout: float) -> Optional[int]:
        """Wait for user response from web UI."""
        logger.info(f"Waiting for user response from web UI (timeout: {timeout}s)...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if we have a response (non-blocking)
                response = self.response_queue.get_nowait()
                logger.info(f"Received user response: {response}")
                return response
            except queue.Empty:
                # No response yet, wait a bit and try again
                await asyncio.sleep(0.1)
                continue

        logger.warning("User response timed out")
        return None

    async def stop_video_capture_and_stream(self) -> Optional[Path]:
        """Stop video capture and HTTP streaming."""
        # Stop WebSocket manager
        await self.websocket_manager.stop()

        # Stop HTTP server
        self.http_server.stop()

        # Signal end of both streams
        for q in [self.video_queue, self.mp4_queue]:
            if not q.full():
                try:
                    q.put_nowait(None)
                except queue.Full:
                    pass

        if self.current_stream_file and self.current_stream_file.exists():
            file_size = self.current_stream_file.stat().st_size
            logger.info(f"Video capture saved: {self.current_stream_file}, size: {file_size} bytes")
            return self.current_stream_file
        else:
            logger.info("No video data captured")
            return None

    def convert_video_to_mp4(self, bin_file_path: Path) -> Optional[Path]:
        """Convert .bin video file to .mp4 using ffmpeg if available."""
        return VideoFileConverter.convert_video_to_mp4(bin_file_path)

    def cleanup(self) -> None:
        """Clean up resources."""
        asyncio.create_task(self.websocket_manager.stop())
        self.http_server.stop()