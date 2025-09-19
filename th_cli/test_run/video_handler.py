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
import base64
import datetime
import os
from pathlib import Path
from typing import Optional

import click
import websockets
from loguru import logger
from websockets.client import WebSocketClientProtocol
from websockets.client import connect as websocket_connect

from th_cli.config import config


class VideoStreamHandler:
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / "videos"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.video_websocket: Optional[WebSocketClientProtocol] = None
        self.current_stream_file: Optional[Path] = None
        self.stream_data = bytearray()

    async def connect_video_stream(self) -> None:
        """Connect to the video WebSocket endpoint."""
        video_ws_url = f"ws://{config.hostname}/api/v1/ws/video"
        logger.info(f"Connecting to video stream: {video_ws_url}")

        try:
            self.video_websocket = await websocket_connect(video_ws_url, ping_timeout=None)
            logger.info("Video WebSocket connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to video WebSocket: {e}")
            raise

    async def start_video_capture(self, prompt_id: str) -> Path:
        """Start capturing video stream to file."""
        if not self.video_websocket:
            await self.connect_video_stream()

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"video_verification_{prompt_id}_{timestamp}.bin"
        self.current_stream_file = self.output_dir / filename

        logger.info(f"Starting video capture to: {self.current_stream_file}")
        click.echo(f"📹 Capturing video stream to: {self.current_stream_file}")

        # Start background task to capture video data
        asyncio.create_task(self._capture_video_data())

        return self.current_stream_file

    async def _capture_video_data(self) -> None:
        """Background task to capture video stream data."""
        if not self.video_websocket or not self.current_stream_file:
            return

        try:
            with open(self.current_stream_file, 'wb') as f:
                while True:
                    try:
                        # Receive video data from WebSocket
                        data = await asyncio.wait_for(self.video_websocket.recv(), timeout=1.0)

                        if isinstance(data, bytes):
                            # Write binary data directly
                            f.write(data)
                            self.stream_data.extend(data)
                        elif isinstance(data, str):
                            try:
                                # Try to decode base64 if it's text
                                decoded_data = base64.b64decode(data)
                                f.write(decoded_data)
                                self.stream_data.extend(decoded_data)
                            except Exception:
                                # If not base64, log and continue
                                logger.debug(f"Received non-binary data: {data[:100]}...")

                        f.flush()  # Ensure data is written immediately

                    except asyncio.TimeoutError:
                        # No data received, continue listening
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        logger.info("Video stream connection closed")
                        break

        except Exception as e:
            logger.error(f"Error capturing video data: {e}")

    async def stop_video_capture(self) -> Optional[Path]:
        """Stop video capture and return the file path."""
        if self.video_websocket:
            try:
                await self.video_websocket.close()
            except Exception as e:
                logger.debug(f"Error closing video WebSocket: {e}")
            finally:
                self.video_websocket = None

        if self.current_stream_file and self.current_stream_file.exists():
            file_size = self.current_stream_file.stat().st_size
            click.echo(f"✅ Video capture completed: {self.current_stream_file} ({file_size} bytes)")
            logger.info(f"Video capture saved: {self.current_stream_file}, size: {file_size} bytes")
            return self.current_stream_file
        else:
            click.echo("⚠️  No video data captured")
            return None

    def save_image_from_hex(self, image_hex_str: str, prompt_id: str) -> Path:
        """Save image from hex string to file."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"image_verification_{prompt_id}_{timestamp}.jpg"
        image_path = self.output_dir / filename

        try:
            # Convert hex string to bytes
            hex_array = image_hex_str.split(',')
            byte_array = bytes([int(hex_val, 16) for hex_val in hex_array])

            # Save to file
            with open(image_path, 'wb') as f:
                f.write(byte_array)

            click.echo(f"🖼️  Image saved to: {image_path}")
            logger.info(f"Image verification saved: {image_path}")
            return image_path

        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            raise

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.video_websocket:
            asyncio.create_task(self.video_websocket.close())