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
import socket
from json import JSONDecodeError
from typing import Callable, Dict, List, Optional, Union

import pydantic
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
from loguru import logger
from starlette.websockets import WebSocketState
from websockets.exceptions import ConnectionClosedOK

from app.constants.websockets_constants import (
    INVALID_JSON_ERROR_STR,
    MISSING_TYPE_ERROR_STR,
    NO_HANDLER_FOR_MSG_ERROR_STR,
    UDP_SOCKET_INTERFACE,
    UDP_SOCKET_PORT,
    MessageKeysEnum,
    MessageTypeEnum,
    WebSocketConnection,
    WebSocketTypeEnum,
)
from app.singleton import Singleton

SocketMessageHander = Callable[[Dict, WebSocket], None]


# SocketConnectionManager manages and maintains all the active socket connections
# communicating with the tool:
#   - Handles all incoming and outgoing messages from the tool.
#   - Has a list of handlers that can register for specific message types to get
#   callbacks on those messages.
#   - Allows broadcasting as well sending personal messages to all or single client
class SocketConnectionManager(object, metaclass=Singleton):
    def __init__(self) -> None:
        self.active_connections: List[WebSocketConnection] = []
        self.__message_handlers: Dict[MessageTypeEnum, SocketMessageHander] = {}
        self._signaling_webrtc_peer: Optional[WebSocketConnection] = None
        self._signaling_webrtc_controller: Optional[WebSocketConnection] = None

    async def connect(self, connection: WebSocketConnection) -> bool:
        try:
            websocket = connection.websocket
            if connection.type in (WebSocketTypeEnum.MAIN, WebSocketTypeEnum.VIDEO):
                await self._connect(connection)
                return True

            elif connection.type == WebSocketTypeEnum.WEBRTC_CONTROLLER:
                # Replace the old controller if exists
                if self._signaling_webrtc_controller:
                    self.disconnect(self._signaling_webrtc_controller)
                await self._connect(connection)
                self._signaling_webrtc_controller = connection
                return True

            elif connection.type == WebSocketTypeEnum.WEBRTC_PEER:
                if self._signaling_webrtc_peer is None:
                    # No peer exists
                    await self._connect(connection)
                    self._signaling_webrtc_peer = connection
                    return True
                else:
                    # Existing peer is active, reject the new connection.
                    await websocket.close(reason="Peer already connected")
                    logger.error(
                        "WebRTC Peer tried to connect but there is already an "
                        "active peer connected."
                    )
                    return False
            else:
                logger.warning(
                    f"Unsupported websocket connection type: {connection.type}"
                )
                return False

        except RuntimeError as e:
            logger.info(f'Failed to connect with error: "{e}".')
            raise e

    async def _connect(self, connection: WebSocketConnection) -> None:
        websocket = connection.websocket
        await websocket.accept()
        logger.info(
            f'Websocket connected: "{connection.websocket}"'
            f' of type: "{connection.type}".'
        )
        self.active_connections.append(connection)

    def disconnect(self, connection: WebSocketConnection) -> None:
        logger.info(
            f'Websocket disconnected: "{connection.websocket}"'
            f' of type: "{connection.type}".'
        )

        if connection.type == WebSocketTypeEnum.WEBRTC_CONTROLLER:
            self._signaling_webrtc_controller = None
        elif connection.type == WebSocketTypeEnum.WEBRTC_PEER:
            self._signaling_webrtc_peer = None
        try:
            self.active_connections.remove(connection)
        except ValueError:
            pass

    async def send_personal_message(
        self, message: Union[str, dict, list], websocket: WebSocket
    ) -> None:
        # Convert dictionaries and lists to string using json
        if isinstance(message, dict) or isinstance(message, list):
            message = json.dumps(message)
        await websocket.send_text(message)

    async def broadcast(self, message: Union[str, dict, list]) -> None:
        # Convert dictionaries and lists to string using json
        if isinstance(message, dict) or isinstance(message, list):
            message = json.dumps(message, default=pydantic.json.pydantic_encoder)
        for connection in self.active_connections:
            if connection.type == WebSocketTypeEnum.MAIN:
                websocket = connection.websocket
                try:
                    await websocket.send_text(message)
                # Starlette raises websockets.exceptions.ConnectionClosedOK
                # when trying to send to a closed websocket.
                # https://github.com/encode/starlette/issues/759
                except ConnectionClosedOK:
                    if websocket.application_state != WebSocketState.DISCONNECTED:
                        await websocket.close()
                    logger.warning(
                        f'Failed to send message: "{message}"'
                        f' to websocket: "{websocket}", connection closed."'
                    )
                except RuntimeError as e:
                    logger.warning(
                        f'Failed to send: "{message}" to websocket: "{websocket}."',
                        'Error:"{e}"',
                    )
                    raise e

    async def received_message(self, websocket: WebSocket, message: str) -> None:
        try:
            json_dict = json.loads(message)
            await self.__handle_received_json(websocket, json_dict)
        except JSONDecodeError:
            await self.__notify_invalid_message(
                websocket=websocket, message=INVALID_JSON_ERROR_STR
            )

    async def relay_video_frames(self, connection: WebSocketConnection) -> None:
        if connection.type == WebSocketTypeEnum.VIDEO:
            websocket = connection.websocket
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
                sock.settimeout(1.0)
                sock.bind((UDP_SOCKET_INTERFACE, UDP_SOCKET_PORT))
                logger.info("UDP socket bound successfully")
                loop = asyncio.get_running_loop()
                while True:
                    try:
                        data, _ = await loop.run_in_executor(None, sock.recvfrom, 65536)
                        await websocket.send_bytes(data)
                    except TimeoutError:
                        try:
                            # WebSocketDisconnect is not raised unless we poll
                            # https://github.com/tiangolo/fastapi/issues/3008
                            await asyncio.wait_for(websocket.receive_text(), 0.1)
                        except asyncio.TimeoutError:
                            pass
            # Starlette raises websockets.exceptions.ConnectionClosedOK
            # when trying to send to a closed websocket.
            # https://github.com/encode/starlette/issues/759
            except (WebSocketDisconnect, ConnectionClosedOK):
                logger.error(f'Websocket for video stream disconnected: "{websocket}".')
            except Exception as e:
                logger.error(f"Failed with {e}")
            finally:
                await websocket.close()
                self.disconnect(connection)
                if sock:
                    sock.close()
        else:
            logger.error(
                f"Expected websocket connection of type {WebSocketTypeEnum.VIDEO}"
            )

    # Note: Currently we only support one message handler per type, registering the
    # handler will displace the previous handler(if any)
    def register_handler(
        self, callback: SocketMessageHander, message_type: MessageTypeEnum
    ) -> None:
        self.__message_handlers[message_type] = callback

    async def __handle_received_json(
        self, websocket: WebSocket, json_dict: dict
    ) -> None:
        message_type = json_dict[MessageKeysEnum.TYPE]
        if message_type is None:
            # Every message must have a type key for the tool to be able to route it
            await self.__notify_invalid_message(
                websocket=websocket, message=MISSING_TYPE_ERROR_STR
            )
            return

        if message_type not in self.__message_handlers.keys():
            # No handler registered for this type of message
            await self.__notify_invalid_message(
                websocket=websocket, message=NO_HANDLER_FOR_MSG_ERROR_STR
            )
            return

        message_handler = self.__message_handlers[message_type]
        message_handler(json_dict[MessageKeysEnum.PAYLOAD], websocket)

    async def __notify_invalid_message(
        self, websocket: WebSocket, message: str
    ) -> None:
        notify_message = {
            MessageKeysEnum.TYPE: MessageTypeEnum.INVALID_MESSAGE,
            MessageKeysEnum.PAYLOAD: message,
        }
        await self.send_personal_message(message=notify_message, websocket=websocket)

    async def start_webrtc_signaling(self, connection: WebSocketConnection) -> None:
        # Starts forwarding messages between Webrtc-Peer and Webrtc-Controller 1:1
        while True:
            data = await connection.websocket.receive_text()
            if connection.type == WebSocketTypeEnum.WEBRTC_PEER:
                # send msg from peer to controller
                await self._webrtc_signal_controller(data)
            elif connection.type == WebSocketTypeEnum.WEBRTC_CONTROLLER:
                # send msg from controller to peer
                await self._webrtc_signal_peer(data)

    async def _webrtc_signal_controller(self, data: str) -> None:
        if self._signaling_webrtc_controller:
            await self._signaling_webrtc_controller.websocket.send_text(data)
        else:
            logger.error("Websocket connection to Controller not found")
            # signal back peer that controller is missing
            await self._webrtc_signal_error(
                WebSocketTypeEnum.WEBRTC_PEER, "Controller not found", data
            )

    async def _webrtc_signal_peer(self, data: str) -> None:
        if self._signaling_webrtc_peer:
            await self._signaling_webrtc_peer.websocket.send_text(data)
        else:
            logger.error("Websocket connection to Peer not found")
            # signal back controller that peer is missing
            await self._webrtc_signal_error(
                WebSocketTypeEnum.WEBRTC_CONTROLLER, "Peer not found", data
            )

    async def _webrtc_signal_error(
        self, dest_type: WebSocketTypeEnum, error_msg: str, data: str
    ) -> None:
        try:
            data = json.loads(data)
            data["error"] = error_msg
        except JSONDecodeError:
            return
        if (
            dest_type == WebSocketTypeEnum.WEBRTC_CONTROLLER
            and self._signaling_webrtc_controller
        ):
            await self._signaling_webrtc_controller.websocket.send_text(
                json.dumps(data)
            )
        elif dest_type == WebSocketTypeEnum.WEBRTC_PEER and self._signaling_webrtc_peer:
            # Error in controller, signal peer to close its connection
            data["type"] = "CLOSE_PEER_CONNECTION"
            await self._signaling_webrtc_peer.websocket.send_text(json.dumps(data))


socket_connection_manager = SocketConnectionManager()
