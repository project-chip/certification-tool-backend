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

from fastapi import APIRouter, WebSocket
from fastapi.websockets import WebSocketDisconnect

from app.constants.websockets_constants import WebSocketConnection, WebSocketTypeEnum
from app.socket_connection_manager import SocketConnectionManager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    socket_connection_manager = SocketConnectionManager()
    connection = WebSocketConnection(websocket, WebSocketTypeEnum.MAIN)
    await socket_connection_manager.connect(connection)
    try:
        while True:
            # WebSocketDisconnect is not raised unless we poll
            # https://github.com/tiangolo/fastapi/issues/3008
            try:
                message = await asyncio.wait_for(websocket.receive_text(), 0.1)
                await socket_connection_manager.received_message(
                    websocket=websocket, message=message
                )
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        socket_connection_manager.disconnect(connection)


@router.websocket("/ws/video")
async def websocket_video_endpoint(websocket: WebSocket) -> None:
    socket_connection_manager = SocketConnectionManager()
    connection = WebSocketConnection(websocket, WebSocketTypeEnum.VIDEO)
    await socket_connection_manager.connect(connection)
    await socket_connection_manager.relay_video_frames(connection)


@router.websocket("/ws/webrtc/controller")
async def websocket_webrtc_controller_endpoint(websocket: WebSocket) -> None:
    socket_connection_manager = SocketConnectionManager()
    connection = WebSocketConnection(websocket, WebSocketTypeEnum.WEBRTC_CONTROLLER)
    try:
        if await socket_connection_manager.connect(connection):
            await socket_connection_manager.start_webrtc_signaling(connection)
    except Exception:
        socket_connection_manager.disconnect(connection)


@router.websocket("/ws/webrtc/peer")
async def websocket_webrtc_peer_endpoint(websocket: WebSocket) -> None:
    socket_connection_manager = SocketConnectionManager()
    connection = WebSocketConnection(websocket, WebSocketTypeEnum.WEBRTC_PEER)
    try:
        if await socket_connection_manager.connect(connection):
            await socket_connection_manager.start_webrtc_signaling(connection)
    except Exception:
        socket_connection_manager.disconnect(connection)
