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
import base64
import queue
import threading
from typing import Optional

import websockets
from loguru import logger
from websockets.client import WebSocketClientProtocol
from websockets.client import connect as websocket_connect

from th_cli.config import config
from th_cli.th_utils.ffmpeg_converter import FFmpegStreamConverter


class VideoWebSocketManager:
    """Manages WebSocket connection for video streaming."""

    def __init__(self):
        self.video_websocket: Optional[WebSocketClientProtocol] = None
        self.streaming_active = False
        self.ffmpeg_converter: Optional[FFmpegStreamConverter] = None

    async def connect(self) -> bool:
        """Connect to the video WebSocket endpoint."""
        video_ws_url = f"ws://{config.hostname}/api/v1/ws/video"
        logger.info(f"Connecting to video stream: {video_ws_url}")

        try:
            self.video_websocket = await websocket_connect(video_ws_url, ping_timeout=None)
            logger.info("Video WebSocket connected successfully")

            # Test if we can send/receive data
            try:
                pong = await self.video_websocket.ping()
                await asyncio.wait_for(pong, timeout=5.0)
                logger.info("Video WebSocket ping/pong successful")
            except Exception as e:
                logger.warning(f"Video WebSocket ping failed: {e}")

            return True

        except Exception as e:
            logger.error(f"Failed to connect to video WebSocket: {e}")
            return False

    async def start_capture_and_stream(self, stream_file, mp4_queue):
        """Start capturing video data and streaming it."""
        if not self.video_websocket:
            logger.error("WebSocket not connected")
            return

        self.streaming_active = True

        # Start FFmpeg converter
        self.ffmpeg_converter = FFmpegStreamConverter()
        if self.ffmpeg_converter.start_conversion():
            logger.info("FFmpeg converter started - will serve MP4")
            # Start thread to transfer converted data
            threading.Thread(target=self._transfer_converted_data, args=(mp4_queue,), daemon=True).start()
        else:
            logger.warning("FFmpeg not available - will serve raw H.264")
            self.ffmpeg_converter = None

        # Start capturing video data
        await self._capture_video_data(stream_file, mp4_queue)

    async def _capture_video_data(self, stream_file, mp4_queue):
        """Capture video stream data and save to file."""
        logger.info("Starting video capture and streaming loop")
        stream_data = bytearray()

        try:
            with open(stream_file, 'wb') as f:
                while self.streaming_active:
                    try:
                        # Receive video data from WebSocket
                        data = await asyncio.wait_for(self.video_websocket.recv(), timeout=1.0)
                        logger.debug(f"Received data: {type(data)}, size: {len(data) if isinstance(data, (bytes, str)) else 'unknown'}")

                        video_data = None
                        if isinstance(data, bytes):
                            # Write binary data directly
                            f.write(data)
                            stream_data.extend(data)
                            video_data = data
                            logger.debug(f"Processing binary data: {len(data)} bytes")
                        elif isinstance(data, str):
                            try:
                                # Try to decode base64 if it's text
                                decoded_data = base64.b64decode(data)
                                f.write(decoded_data)
                                stream_data.extend(decoded_data)
                                video_data = decoded_data
                                logger.debug(f"Decoded base64 data: {len(decoded_data)} bytes")
                            except Exception as e:
                                # If not base64, log and continue
                                logger.debug(f"Received non-binary data (not base64): {data[:100]}... - {e}")

                        # Feed data to FFmpeg converter
                        if video_data:
                            # Feed data to FFmpeg converter if available
                            if self.ffmpeg_converter:
                                self.ffmpeg_converter.feed_data(video_data)

                        f.flush()  # Ensure data is written immediately

                    except asyncio.TimeoutError:
                        # No data received, continue listening
                        logger.debug("No video data received (timeout)")
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        logger.info("Video stream connection closed")
                        break
                    except Exception as e:
                        logger.error(f"Error in video data loop: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error capturing video data: {e}")
        finally:
            logger.info("Video capture loop ended")

    def _transfer_converted_data(self, mp4_queue):
        """Transfer converted MP4 data from FFmpeg to HTTP queue for live streaming."""
        logger.info("Starting LIVE MP4 data transfer thread")
        while self.streaming_active and self.ffmpeg_converter:
            mp4_data = self.ffmpeg_converter.get_converted_data(timeout=1.0)
            if mp4_data:
                try:
                    mp4_queue.put_nowait(mp4_data)
                    logger.debug(f"Transferred {len(mp4_data)} bytes of MP4 data for live stream")
                except queue.Full:
                    logger.warning("MP4 queue full, dropping frame")
        logger.info("LIVE MP4 data transfer thread ended")

    async def stop(self):
        """Stop video capture and streaming."""
        self.streaming_active = False

        # Stop FFmpeg converter
        if self.ffmpeg_converter:
            logger.info("Stopping FFmpeg converter")
            self.ffmpeg_converter.stop()
            self.ffmpeg_converter = None

        # Stop WebSocket
        if self.video_websocket:
            try:
                await self.video_websocket.close()
            except Exception as e:
                logger.debug(f"Error closing video WebSocket: {e}")
            finally:
                self.video_websocket = None

    async def wait_and_connect_with_retry(self, max_attempts: int = 30):
        """Wait for video stream to become available and connect with retry."""
        logger.info("Waiting for video stream to become available...")

        attempt = 0
        while attempt < max_attempts:
            try:
                if await self.connect():
                    logger.info("Video WebSocket connected successfully")
                    return True

            except Exception as e:
                attempt += 1
                logger.debug(f"Video WebSocket connection attempt {attempt} failed: {e}")
                if attempt < max_attempts:
                    await asyncio.sleep(1)  # Wait 1 second before retry
                else:
                    logger.warning("Could not connect to video WebSocket after 30 attempts")
                    break

        return False