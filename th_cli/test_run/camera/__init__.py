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
"""
Camera handling modules for TH CLI.

This package provides modular camera/video handling functionality:
- FFmpeg conversion for H.264 to MP4
- HTTP server for camera streaming and user interaction
- WebSocket management for camera data capture
- Main camera stream handler coordinator
"""

from .camera_stream_handler import CameraStreamHandler
from th_cli.th_utils.ffmpeg_converter import FFmpegStreamConverter, VideoFileConverter
from .camera_http_server import CameraHTTPServer, VideoStreamingHandler
from .websocket_manager import VideoWebSocketManager

__all__ = [
    'CameraStreamHandler',
    'FFmpegStreamConverter',
    'VideoFileConverter',
    'CameraHTTPServer',
    'VideoStreamingHandler',
    'VideoWebSocketManager'
]