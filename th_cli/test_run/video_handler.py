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
import json
import os
import socket
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional
from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
import queue

import click
import websockets
from loguru import logger
from websockets.client import WebSocketClientProtocol
from websockets.client import connect as websocket_connect

from th_cli.config import config


class FFmpegStreamConverter:
    """Converts H.264 raw stream to MP4 in real-time using FFmpeg."""

    def __init__(self):
        self.ffmpeg_process = None
        self.output_queue = queue.Queue()

    def start_conversion(self):
        """Start FFmpeg process for real-time conversion."""
        try:
            # FFmpeg command to convert H.264 raw input to MP4 output
            cmd = [
                'ffmpeg',
                '-f', 'h264',           # Input format: H.264 raw
                '-i', 'pipe:0',         # Read from stdin
                '-c:v', 'copy',         # Copy video stream (no re-encoding)
                '-f', 'mp4',            # Output format: MP4
                '-movflags', 'frag_keyframe+empty_moov',  # Enable streaming
                'pipe:1'                # Write to stdout
            ]

            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Start thread to read FFmpeg output
            threading.Thread(
                target=self._read_ffmpeg_output,
                daemon=True
            ).start()

            logger.info("FFmpeg converter started successfully")
            return True

        except FileNotFoundError:
            logger.error("FFmpeg not found - raw H.264 streaming only")
            return False
        except Exception as e:
            logger.error(f"Failed to start FFmpeg converter: {e}")
            return False

    def _read_ffmpeg_output(self):
        """Read converted MP4 data from FFmpeg stdout."""
        try:
            while self.ffmpeg_process and self.ffmpeg_process.poll() is None:
                data = self.ffmpeg_process.stdout.read(8192)
                if data:
                    try:
                        self.output_queue.put_nowait(data)
                    except queue.Full:
                        pass  # Drop frames if queue is full
        except Exception as e:
            logger.error(f"Error reading FFmpeg output: {e}")

    def feed_data(self, h264_data: bytes):
        """Feed H.264 raw data to FFmpeg for conversion."""
        if self.ffmpeg_process and self.ffmpeg_process.stdin:
            try:
                self.ffmpeg_process.stdin.write(h264_data)
                self.ffmpeg_process.stdin.flush()
            except Exception as e:
                logger.error(f"Error feeding data to FFmpeg: {e}")

    def get_converted_data(self, timeout=1.0):
        """Get converted MP4 data."""
        try:
            return self.output_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self):
        """Stop FFmpeg conversion."""
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.stdin.close()
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait(timeout=5)
            except Exception as e:
                logger.error(f"Error stopping FFmpeg: {e}")
            finally:
                self.ffmpeg_process = None


class VideoStreamingHandler(BaseHTTPRequestHandler):
    """HTTP handler for streaming video data."""

    def do_GET(self):
        logger.info(f"GET request received: {self.path}")
        if self.path == '/video.mp4':
            self.stream_video()
        elif self.path == '/':
            self.serve_player()
        else:
            logger.warning(f"404 for GET {self.path}")
            self.send_error(404)

    def do_POST(self):
        logger.info(f"POST request received: {self.path}")
        if self.path == '/submit_response':
            self.handle_response()
        else:
            logger.warning(f"404 for POST {self.path}")
            self.send_error(404)

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def stream_video(self):
        """Stream video data as HTTP response."""
        logger.info("HTTP client connected for video stream")
        self.send_response(200)
        self.send_header('Content-Type', 'video/mp4')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()

        # Get the MP4 queue from the server (converted data)
        mp4_queue = getattr(self.server, 'mp4_queue', None)
        if not mp4_queue:
            logger.error("No MP4 queue found on server")
            return

        logger.info("Starting to stream MP4 data to HTTP client")
        bytes_sent = 0
        try:
            while True:
                try:
                    # Get converted MP4 data from queue
                    data = mp4_queue.get(timeout=1.0)
                    if data is None:  # Signal to stop
                        logger.info("Received end-of-stream signal")
                        break

                    self.wfile.write(data)
                    self.wfile.flush()
                    bytes_sent += len(data)
                    logger.debug(f"Sent {len(data)} bytes MP4 to HTTP client (total: {bytes_sent})")

                except queue.Empty:
                    logger.debug("No MP4 data in queue, continuing...")
                    continue
                except Exception as e:
                    logger.debug(f"Error streaming MP4: {e}")
                    break

        except Exception as e:
            logger.error(f"MP4 streaming error: {e}")

        logger.info(f"HTTP MP4 stream ended, total bytes sent: {bytes_sent}")

    def handle_response(self):
        """Handle user response from web UI."""
        logger.info(f"Received POST request to {self.path}")
        try:
            # Check if Content-Length header exists
            if 'Content-Length' not in self.headers:
                logger.error("Missing Content-Length header")
                self.send_error(400, "Missing Content-Length header")
                return

            content_length = int(self.headers['Content-Length'])
            logger.info(f"Reading {content_length} bytes from request body")

            post_data = self.rfile.read(content_length)
            logger.info(f"Raw POST data: {post_data}")

            response_data = json.loads(post_data.decode('utf-8'))
            logger.info(f"Parsed JSON data: {response_data}")

            response_value = int(response_data.get('response'))
            logger.info(f"Extracted response value: {response_value}")

            # Send response to the response queue
            response_queue = getattr(self.server, 'response_queue', None)
            if response_queue:
                try:
                    response_queue.put_nowait(response_value)
                    logger.info(f"Response {response_value} queued successfully")
                except queue.Full:
                    logger.error("Response queue is full")
                    self.send_error(500, "Response queue is full")
                    return
            else:
                logger.error("No response queue found on server")
                self.send_error(500, "No response queue available")
                return

            # Send success response
            logger.info("Sending success response to client")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response_json = '{"status": "success"}'
            self.wfile.write(response_json.encode())
            logger.info("Success response sent")

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(f'{{"error": "Invalid JSON: {str(e)}"}}'.encode())
        except ValueError as e:
            logger.error(f"Value error: {e}")
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(f'{{"error": "Invalid response value: {str(e)}"}}'.encode())
        except Exception as e:
            logger.error(f"Unexpected error handling response: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(f'{{"error": "Server error: {str(e)}"}}'.encode())

    def serve_player(self):
        """Serve a video player similar to the frontend modal."""
        # Get dynamic data from server
        prompt_options = getattr(self.server, 'prompt_options', {})
        prompt_text = getattr(self.server, 'prompt_text', 'Video Verification')

        # Generate radio button options dynamically
        radio_options_html = ""
        for key, value in prompt_options.items():
            radio_options_html += f'''
            <div class="popup-radio-row" data-value="{value}" onclick="selectOption({value})">
                <input type="radio" id="radio_{value}" name="group_1" value="{value}">
                <label for="radio_{value}">{key}</label>
            </div>
            '''

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>WebRTC Video Verification</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: #f5f5f5;
                    margin: 0;
                    padding: 20px;
                    display: flex;
                    justify-content: center;
                    align-items: flex-start;
                    min-height: 100vh;
                }}

                .p-dialog {{
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                    max-width: 700px;
                    width: 100%;
                    margin: 20px;
                }}

                .p-dialog-header {{
                    padding: 16px 20px;
                    border-bottom: 1px solid #e0e0e0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    background: #fafafa;
                    border-radius: 8px 8px 0 0;
                }}

                .p-dialog-title {{
                    font-size: 18px;
                    font-weight: 600;
                    color: #333;
                }}

                .p-dialog-content {{
                    padding: 20px;
                }}

                .subheader {{
                    font-size: 16px;
                    color: #555;
                    margin-bottom: 20px;
                    font-weight: 500;
                }}

                .video-container {{
                    text-align: center;
                    margin: 20px 0;
                    background: #000;
                    border-radius: 4px;
                    padding: 10px;
                }}

                video, canvas {{
                    width: 640px;
                    height: 480px;
                    max-width: 100%;
                    border: 2px solid #ddd;
                    border-radius: 4px;
                    background: #000;
                }}

                .input-items-div {{
                    margin: 20px 0;
                }}

                .popup-radio-div {{
                    display: flex;
                    gap: 20px;
                    justify-content: center;
                    margin: 20px 0;
                    flex-wrap: wrap;
                }}

                .popup-radio-row {{
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 10px 15px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    cursor: pointer;
                    transition: all 0.2s;
                    min-width: 100px;
                    justify-content: center;
                }}

                .popup-radio-row:hover {{
                    background: #f0f0f0;
                    border-color: #2196F3;
                }}

                .popup-radio-row.selected {{
                    background: #e3f2fd;
                    border-color: #2196F3;
                }}

                input[type="radio"] {{
                    margin-right: 8px;
                    transform: scale(1.2);
                }}

                label {{
                    font-weight: 500;
                    color: #333;
                    cursor: pointer;
                    font-size: 14px;
                }}

                .buttons-div {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e0e0e0;
                }}

                .popup-button {{
                    background: #2196F3;
                    color: white;
                    border: none;
                    padding: 12px 30px;
                    border-radius: 4px;
                    font-size: 16px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.2s;
                    min-width: 120px;
                }}

                .popup-button:hover {{
                    background: #1976D2;
                }}

                .popup-button:disabled {{
                    background: #ccc;
                    cursor: not-allowed;
                }}

                .close-btn {{
                    background: none;
                    border: none;
                    font-size: 20px;
                    cursor: pointer;
                    color: #666;
                    padding: 5px;
                    border-radius: 50%;
                    width: 30px;
                    height: 30px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}

                .close-btn:hover {{
                    background: #f0f0f0;
                }}

                .status-info {{
                    background: #e8f5e8;
                    border: 1px solid #4caf50;
                    padding: 10px;
                    border-radius: 4px;
                    margin: 10px 0;
                    font-size: 14px;
                    color: #2e7d32;
                }}

                .submitting {{
                    background: #ff9800 !important;
                    cursor: wait !important;
                }}
            </style>
            <script>
                let selectedValue = null;

                function selectOption(value) {{
                    selectedValue = value;

                    // Update visual selection
                    document.querySelectorAll('.popup-radio-row').forEach(row => {{
                        row.classList.remove('selected');
                    }});
                    document.querySelector(`[data-value="${{value}}"]`).classList.add('selected');

                    // Update radio buttons
                    document.querySelectorAll('input[type="radio"]').forEach(radio => {{
                        radio.checked = radio.value === value.toString();
                    }});

                    // Enable submit button
                    document.getElementById('submitBtn').disabled = false;
                }}

                async function submitResponse() {{
                    if (selectedValue) {{
                        const button = document.getElementById('submitBtn');
                        button.classList.add('submitting');
                        button.textContent = 'Submitting...';
                        button.disabled = true;

                        console.log('Submitting response:', selectedValue);

                        try {{
                            const payload = {{ response: selectedValue }};
                            console.log('Sending payload:', JSON.stringify(payload));

                            const response = await fetch('/submit_response', {{
                                method: 'POST',
                                headers: {{
                                    'Content-Type': 'application/json',
                                }},
                                body: JSON.stringify(payload)
                            }});

                            console.log('Response status:', response.status);
                            console.log('Response headers:', [...response.headers.entries()]);

                            if (response.ok) {{
                                const responseData = await response.json();
                                console.log('Response data:', responseData);

                                button.textContent = 'Response Sent!';
                                button.style.background = '#4caf50';

                                // Close window after short delay
                                setTimeout(() => {{
                                    window.close();
                                }}, 1000);
                            }} else {{
                                const errorText = await response.text();
                                console.error('Server error response:', errorText);
                                throw new Error(`Server error: ${{response.status}} - ${{errorText}}`);
                            }}
                        }} catch (error) {{
                            console.error('Error submitting response:', error);
                            button.textContent = 'Error - Try Again';
                            button.style.background = '#f44336';
                            button.disabled = false;
                            button.classList.remove('submitting');

                            // Show error details in console
                            console.error('Full error details:', error);

                            setTimeout(() => {{
                                button.textContent = 'Submit';
                                button.style.background = '#2196F3';
                            }}, 3000);
                        }}
                    }}
                }}

                // Initialize video
                window.onload = function() {{
                    const video = document.getElementById('videoElement');
                    video.addEventListener('loadstart', () => {{
                        console.log('Video loading started');
                    }});
                    video.addEventListener('loadeddata', () => {{
                        console.log('Video data loaded');
                    }});
                    video.addEventListener('error', (e) => {{
                        console.error('Video error:', e);
                    }});

                    // Test server connectivity
                    console.log('Testing server connectivity...');
                    fetch('/submit_response', {{
                        method: 'OPTIONS'
                    }})
                    .then(response => {{
                        console.log('Server connectivity test - Status:', response.status);
                        console.log('Server connectivity test - Headers:', [...response.headers.entries()]);
                    }})
                    .catch(error => {{
                        console.error('Server connectivity test failed:', error);
                    }});
                }};
            </script>
        </head>
        <body>
            <div class="p-dialog" role="dialog">
                <div class="p-dialog-header">
                    <span class="p-dialog-title">WebRTC Video Verification</span>
                    <button class="close-btn" onclick="window.close()">×</button>
                </div>

                <div class="p-dialog-content">
                    <div class="subheader">
                        {prompt_text}
                    </div>

                    <div class="status-info">
                        🎬 Live video stream from CLI - converted H.264 to MP4 using FFmpeg
                    </div>

                    <div class="video-container">
                        <video id="videoElement" controls autoplay muted>
                            <source src="/video.mp4" type="video/mp4">
                            Your browser does not support the video tag.
                        </video>
                    </div>

                    <div class="input-items-div">
                        <div class="popup-radio-div">
                            {radio_options_html}
                        </div>
                    </div>

                    <div class="buttons-div">
                        <button id="submitBtn" class="popup-button" onclick="submitResponse()" disabled>
                            Submit
                        </button>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        # Suppress HTTP logs
        pass


class VideoStreamHandler:
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / "videos"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.video_websocket: Optional[WebSocketClientProtocol] = None
        self.current_stream_file: Optional[Path] = None
        self.stream_data = bytearray()
        self.http_server = None
        self.video_queue = queue.Queue()  # Raw H.264 data
        self.mp4_queue = queue.Queue()    # Converted MP4 data
        self.response_queue = queue.Queue()  # User responses from web UI
        self.streaming_active = False
        self.ffmpeg_converter = None
        self.prompt_options = {}  # Store prompt options
        self.prompt_text = ""     # Store prompt text

    async def connect_video_stream(self) -> None:
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

        except Exception as e:
            logger.error(f"Failed to connect to video WebSocket: {e}")
            raise

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

        # Start HTTP server AFTER prompt data is set
        self.start_http_server(stream_port)

        # Don't connect to WebSocket yet - wait for the test to start
        # The video stream will be available once the test starts sending data
        self.streaming_active = True

        # Start background task that will connect when needed
        asyncio.create_task(self._wait_and_capture_video_data())

        return self.current_stream_file

    def start_http_server(self, port: int = 8999):
        """Start HTTP server for video streaming."""
        try:
            # Use ThreadingHTTPServer for better concurrency
            self.http_server = ThreadingHTTPServer(('0.0.0.0', port), VideoStreamingHandler)
            self.http_server.allow_reuse_address = True

            # Set all required attributes on the server
            self.http_server.mp4_queue = self.mp4_queue
            self.http_server.response_queue = self.response_queue
            self.http_server.prompt_options = getattr(self, 'prompt_options', {})
            self.http_server.prompt_text = getattr(self, 'prompt_text', 'Video Verification')

            logger.info(f"HTTP server configured with prompt_options: {self.http_server.prompt_options}")
            logger.info(f"HTTP server configured with prompt_text: {self.http_server.prompt_text}")

            def run_server():
                logger.info(f"Starting HTTP video server on port {port}")
                try:
                    self.http_server.serve_forever()
                except Exception as e:
                    logger.error(f"HTTP server error: {e}")

            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            logger.info(f"HTTP server thread started on port {port}")

            # Give the server a moment to start
            time.sleep(0.5)

        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")

    async def _wait_and_capture_video_data(self) -> None:
        """Wait for video stream to become available and then capture."""
        logger.info("Waiting for video stream to become available...")

        max_attempts = 30  # Try for 30 seconds
        attempt = 0

        while self.streaming_active and attempt < max_attempts:
            try:
                # Try to connect to video WebSocket
                if not self.video_websocket:
                    await self.connect_video_stream()

                # If connected, start capturing
                if self.video_websocket:
                    logger.info("Video WebSocket connected, starting capture")

                    # Start FFmpeg converter
                    self.ffmpeg_converter = FFmpegStreamConverter()
                    if self.ffmpeg_converter.start_conversion():
                        logger.info("FFmpeg converter started - will serve MP4")
                        # Start thread to transfer converted data
                        threading.Thread(target=self._transfer_converted_data, daemon=True).start()
                    else:
                        logger.warning("FFmpeg not available - will serve raw H.264")
                        self.ffmpeg_converter = None

                    await self._capture_and_stream_video_data()
                    break

            except Exception as e:
                attempt += 1
                logger.debug(f"Video WebSocket connection attempt {attempt} failed: {e}")
                if attempt < max_attempts:
                    await asyncio.sleep(1)  # Wait 1 second before retry
                else:
                    logger.warning("Could not connect to video WebSocket after 30 attempts")
                    break

    def _transfer_converted_data(self):
        """Transfer converted MP4 data from FFmpeg to HTTP queue."""
        logger.info("Starting MP4 data transfer thread")
        while self.streaming_active and self.ffmpeg_converter:
            mp4_data = self.ffmpeg_converter.get_converted_data(timeout=1.0)
            if mp4_data:
                try:
                    self.mp4_queue.put_nowait(mp4_data)
                    logger.debug(f"Transferred {len(mp4_data)} bytes of MP4 data")
                except queue.Full:
                    logger.warning("MP4 queue full, dropping frame")
        logger.info("MP4 data transfer thread ended")

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

    async def _capture_and_stream_video_data(self) -> None:
        """Background task to capture video stream data and feed HTTP stream."""
        if not self.video_websocket or not self.current_stream_file:
            logger.error("Missing video websocket or stream file")
            return

        logger.info("Starting video capture and streaming loop")
        try:
            with open(self.current_stream_file, 'wb') as f:
                while self.streaming_active:
                    try:
                        # Receive video data from WebSocket
                        data = await asyncio.wait_for(self.video_websocket.recv(), timeout=1.0)
                        logger.debug(f"Received data: {type(data)}, size: {len(data) if isinstance(data, (bytes, str)) else 'unknown'}")

                        video_data = None
                        if isinstance(data, bytes):
                            # Write binary data directly
                            f.write(data)
                            self.stream_data.extend(data)
                            video_data = data
                            logger.debug(f"Processing binary data: {len(data)} bytes")
                        elif isinstance(data, str):
                            try:
                                # Try to decode base64 if it's text
                                decoded_data = base64.b64decode(data)
                                f.write(decoded_data)
                                self.stream_data.extend(decoded_data)
                                video_data = decoded_data
                                logger.debug(f"Decoded base64 data: {len(decoded_data)} bytes")
                            except Exception as e:
                                # If not base64, log and continue
                                logger.debug(f"Received non-binary data (not base64): {data[:100]}... - {e}")

                        # Feed HTTP stream
                        if video_data:
                            # Feed data to FFmpeg converter if available
                            if self.ffmpeg_converter:
                                self.ffmpeg_converter.feed_data(video_data)

                            # Also keep raw data in queue for fallback
                            if not self.video_queue.full():
                                try:
                                    self.video_queue.put_nowait(video_data)
                                    logger.debug(f"Added {len(video_data)} bytes to raw video queue")
                                except queue.Full:
                                    logger.warning("Raw video queue full, dropping frame")
                            else:
                                logger.warning("Raw video queue full, cannot add data")

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
            logger.info("Video capture loop ended, signaling end of stream")
            # Signal end of stream
            if not self.video_queue.full():
                try:
                    self.video_queue.put_nowait(None)
                    logger.debug("Sent end-of-stream signal")
                except queue.Full:
                    pass

    async def stop_video_capture_and_stream(self) -> Optional[Path]:
        """Stop video capture and HTTP streaming."""
        self.streaming_active = False

        # Stop FFmpeg converter
        if self.ffmpeg_converter:
            logger.info("Stopping FFmpeg converter")
            self.ffmpeg_converter.stop()
            self.ffmpeg_converter = None

        # Stop HTTP server
        if self.http_server:
            try:
                self.http_server.shutdown()
                self.http_server = None
            except Exception as e:
                logger.debug(f"Error stopping HTTP server: {e}")

        # Stop WebSocket
        if self.video_websocket:
            try:
                await self.video_websocket.close()
            except Exception as e:
                logger.debug(f"Error closing video WebSocket: {e}")
            finally:
                self.video_websocket = None

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

    def convert_video_to_mp4(self, bin_file_path: Path) -> Optional[Path]:
        """Convert .bin video file to .mp4 using ffmpeg if available."""
        try:
            # Check if ffmpeg is available
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

        try:
            # Create MP4 filename
            mp4_file = bin_file_path.with_suffix('.mp4')

            # Convert using ffmpeg
            # Assuming the .bin contains H.264 raw stream
            cmd = [
                'ffmpeg', '-y',  # -y to overwrite existing files
                '-f', 'h264',    # Input format
                '-i', str(bin_file_path),  # Input file
                '-c:v', 'copy',  # Copy video stream without re-encoding
                str(mp4_file)    # Output file
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and mp4_file.exists():
                click.echo(f"🎬 Video converted to MP4: {mp4_file}")
                return mp4_file
            else:
                logger.debug(f"FFmpeg conversion failed: {result.stderr}")
                return None

        except Exception as e:
            logger.debug(f"Video conversion error: {e}")
            return None

    def analyze_video_format(self, video_file: Path) -> dict:
        """Analyze the video file to determine format and provide viewing options."""
        try:
            # Read first few bytes to detect format
            with open(video_file, 'rb') as f:
                header = f.read(32)

            file_size = video_file.stat().st_size

            analysis = {
                'file_size': file_size,
                'format': 'unknown',
                'viewing_commands': [],
                'notes': ''
            }

            # Check for common video format signatures
            if header.startswith(b'\x00\x00\x00\x01'):
                analysis['format'] = 'H.264 NAL units'
                analysis['viewing_commands'] = [
                    f"# Try with VLC (most likely to work):",
                    f"vlc '{video_file}'",
                    f"",
                    f"# Try with FFplay:",
                    f"ffplay -f h264 '{video_file}'",
                    f"",
                    f"# Try converting to MP4:",
                    f"ffmpeg -f h264 -i '{video_file}' -c:v copy output.mp4",
                    f"ffmpeg -f h264 -i '{video_file}' -c:v libx264 -preset fast output.mp4"
                ]
                analysis['notes'] = 'H.264 raw stream - VLC should handle this'

            elif header.startswith(b'ftyp') or b'moov' in header[:32]:
                analysis['format'] = 'MP4/MOV container'
                analysis['viewing_commands'] = [
                    f"# Should open directly with system default player:",
                    f"open '{video_file}'  # macOS",
                    f"xdg-open '{video_file}'  # Linux",
                    f"start '{video_file}'  # Windows",
                    f"",
                    f"# Or with VLC:",
                    f"vlc '{video_file}'"
                ]
                analysis['notes'] = 'MP4/MOV format - should work with most video players'

            elif header.startswith(b'RIFF') and b'AVI ' in header[:32]:
                analysis['format'] = 'AVI container'
                analysis['viewing_commands'] = [
                    f"# Try with VLC:",
                    f"vlc '{video_file}'"
                ]
                analysis['notes'] = 'AVI format - use VLC'

            else:
                # Try to detect other patterns
                hex_header = header.hex()
                analysis['format'] = f'Unknown (header: {hex_header[:16]}...)'
                analysis['viewing_commands'] = [
                    f"# Try these formats with FFplay:",
                    f"ffplay -f h264 '{video_file}'",
                    f"ffplay -f rawvideo -pixel_format yuv420p -video_size 640x480 '{video_file}'",
                    f"ffplay -f mjpeg '{video_file}'",
                    f"",
                    f"# Try with VLC (auto-detect):",
                    f"vlc '{video_file}'",
                    f"",
                    f"# Try converting with different formats:",
                    f"ffmpeg -f h264 -i '{video_file}' -c:v libx264 output.mp4",
                    f"ffmpeg -f rawvideo -pixel_format yuv420p -video_size 640x480 -i '{video_file}' output.mp4"
                ]
                analysis['notes'] = 'Unknown format - try multiple approaches'

            return analysis

        except Exception as e:
            return {
                'file_size': 0,
                'format': f'Error analyzing: {e}',
                'viewing_commands': [f"# Could not analyze file: {e}"],
                'notes': 'Analysis failed'
            }

    def serve_video_http(self, video_file: Path, port: int = 8999) -> None:
        """Serve video file via simple HTTP server for easy access."""
        try:
            import threading
            import http.server
            import socketserver
            import os

            # Change to video directory
            original_dir = os.getcwd()
            os.chdir(video_file.parent)

            class QuietHTTPServer(socketserver.TCPServer):
                def server_bind(self):
                    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    super().server_bind()

            # Start HTTP server in background
            handler = http.server.SimpleHTTPRequestHandler
            httpd = QuietHTTPServer(("", port), handler)

            def serve():
                httpd.serve_forever()

            server_thread = threading.Thread(target=serve, daemon=True)
            server_thread.start()

            click.echo(f"🌐 Video server started at:")
            click.echo(f"   http://192.168.20.144:{port}/{video_file.name}")
            click.echo(f"   Access from your browser or: curl -O http://{config.hostname}:{port}/{video_file.name}")
            click.echo(f"   Press Ctrl+C to stop server")

            # Keep server running for a while
            import time
            time.sleep(60)  # Run for 1 minute
            httpd.shutdown()
            os.chdir(original_dir)

        except Exception as e:
            logger.debug(f"HTTP server error: {e}")
            click.echo("⚠️  Could not start HTTP server")

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.video_websocket:
            asyncio.create_task(self.video_websocket.close())