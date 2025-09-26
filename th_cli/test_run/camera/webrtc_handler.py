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
import json
import queue
from typing import Dict, Optional

from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaStreamTrack
from loguru import logger


class H264VideoTrack(MediaStreamTrack):
    """Custom video track that streams H.264 data directly."""

    kind = "video"

    def __init__(self, video_queue: queue.Queue):
        super().__init__()
        self.video_queue = video_queue
        self._start_time = None

    async def recv(self):
        """Receive H.264 frame from queue and convert to WebRTC frame."""
        try:
            # Get H.264 data from queue (non-blocking)
            h264_data = self.video_queue.get_nowait()
            if h264_data is None:  # End of stream signal
                raise ConnectionError("End of stream")

            # For now, we'll use a simple approach - this needs proper H.264 parsing
            # In a full implementation, you'd parse H.264 NAL units and create proper frames
            logger.debug(f"Received H.264 data: {len(h264_data)} bytes")

            # This is a simplified approach - proper implementation would need:
            # 1. H.264 NAL unit parsing
            # 2. Frame timing calculation
            # 3. Proper VideoFrame creation with H.264 data

            # For now, return None to indicate no frame available
            await asyncio.sleep(0.033)  # ~30fps timing
            return None

        except queue.Empty:
            # No data available, wait a bit
            await asyncio.sleep(0.001)
            return None


class WebRTCHandler:
    """Handles WebRTC peer connections for direct H.264 streaming."""

    def __init__(self):
        self.peer_connections: Dict[str, RTCPeerConnection] = {}
        self.video_track: Optional[H264VideoTrack] = None

    def set_video_source(self, video_queue: queue.Queue):
        """Set the H.264 video source queue."""
        self.video_track = H264VideoTrack(video_queue)
        logger.info("WebRTC video source configured")

    async def create_peer_connection(self, session_id: str) -> RTCPeerConnection:
        """Create a new WebRTC peer connection."""
        configuration = RTCConfiguration([])
        pc = RTCPeerConnection(configuration)

        # Add video track if available
        if self.video_track:
            pc.addTrack(self.video_track)
            logger.info("Added H.264 video track to peer connection")

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"WebRTC connection state: {pc.connectionState}")

        @pc.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            logger.info(f"ICE connection state: {pc.iceConnectionState}")

        self.peer_connections[session_id] = pc
        return pc

    async def handle_offer(self, session_id: str, offer_data: dict) -> dict:
        """Handle WebRTC offer and create answer."""
        try:
            pc = await self.create_peer_connection(session_id)

            # Set remote description (offer)
            offer = RTCSessionDescription(
                sdp=offer_data["sdp"],
                type=offer_data["type"]
            )
            await pc.setRemoteDescription(offer)
            logger.info("Set remote description (offer)")

            # Create answer
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            logger.info("Created and set local description (answer)")

            return {
                "type": answer.type,
                "sdp": answer.sdp
            }

        except Exception as e:
            logger.error(f"Error handling WebRTC offer: {e}")
            raise

    async def handle_ice_candidate(self, session_id: str, candidate_data: dict):
        """Handle ICE candidate."""
        try:
            pc = self.peer_connections.get(session_id)
            if not pc:
                logger.error(f"No peer connection found for session {session_id}")
                return

            # Add ICE candidate (implementation depends on aiortc version)
            # This is a simplified version - you may need to adjust based on the exact aiortc API
            logger.info(f"Received ICE candidate for session {session_id}")

        except Exception as e:
            logger.error(f"Error handling ICE candidate: {e}")

    async def close_connection(self, session_id: str):
        """Close WebRTC peer connection."""
        pc = self.peer_connections.pop(session_id, None)
        if pc:
            await pc.close()
            logger.info(f"Closed WebRTC connection for session {session_id}")

    async def cleanup(self):
        """Clean up all peer connections."""
        for session_id in list(self.peer_connections.keys()):
            await self.close_connection(session_id)
        logger.info("WebRTC handler cleaned up")