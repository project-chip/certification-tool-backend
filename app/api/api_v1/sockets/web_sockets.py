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
import socket

from fastapi import APIRouter, WebSocket
from fastapi.websockets import WebSocketDisconnect
from loguru import logger

from app.constants.websockets_constants import UDP_SOCKET_INTERFACE, UDP_SOCKET_PORT
from app.socket_connection_manager import SocketConnectionManager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    socket_connection_manager = SocketConnectionManager()
    await socket_connection_manager.connect(websocket)
    try:
        while True:
            # WebSocketDisconnect is not raised unless we poll
            # https://github.com/tiangolo/fastapi/issues/3008
            try:
                message = await asyncio.wait_for(websocket.receive_text(), 0.1)
                await socket_connection_manager.received_message(
                    socket=websocket, message=message
                )
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        socket_connection_manager.disconnect(websocket)


@router.websocket("/ws/video")
async def websocket_video_endpoint(websocket: WebSocket) -> None:
    try:
        await websocket.accept()
        logger.info(f'Websocket connected: "{websocket}".')
    except RuntimeError as e:
        logger.info(f'Failed to connect with error: "{e}".')
        raise e

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        sock.bind((UDP_SOCKET_INTERFACE, UDP_SOCKET_PORT))
        logger.info("UDP socket bound successfully")
        loop = asyncio.get_event_loop()
        while True:
            data, _ = await loop.run_in_executor(None, sock.recvfrom, 65536)
            # send data to ws
            await websocket.send_bytes(data)
    except WebSocketDisconnect:
        logger.error(f'Websocket for video stream disconnected: "{websocket}".')
    except Exception as e:
        logger.error(f"Failed with {e}")
    finally:
        await websocket.close()
