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
import socket
from typing import Any, Dict
from unittest import mock

import pytest
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
from starlette.websockets import WebSocketState
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from app.constants.shared_constants import MessageKeysEnum, MessageTypeEnum
from app.constants.websockets_constants import (
    INVALID_JSON_ERROR_STR,
    MESSAGE_ID_KEY,
    WebSocketConnection,
    WebSocketTypeEnum,
)
from app.socket_connection_manager import (
    SocketConnectionManager,
    socket_connection_manager,
)
from app.user_prompt_support.constants import (
    RESPONSE_KEY,
    STATUS_CODE_KEY,
    UserResponseStatusEnum,
)


@pytest.mark.asyncio
async def test_connect_successful() -> None:
    """
    Validates the following when connect() succeeds -

    1. The "active_connections" list has one entry corresponding to the new connection.
    2. The "accept" function is called.
    """

    # Ensure that the "active_connections" list is initially empty
    socket_connection_manager.active_connections.clear()
    assert len(socket_connection_manager.active_connections) == 0

    # Create a socket to initiate the connection
    socket = mock.MagicMock(spec=WebSocket)
    connection = WebSocketConnection(socket, WebSocketTypeEnum.MAIN)
    await socket_connection_manager.connect(connection=connection)

    # "active_connections" list gets an entry upon a successful socket connection
    assert len(socket_connection_manager.active_connections) == 1
    socket.accept.assert_called_once()

    # Cleanup
    socket_connection_manager.active_connections.clear()


@pytest.mark.asyncio
async def test_connect_failed() -> None:
    """
    Validates the following when connect() fails -

    1. Runtime error is raised
    2. The "active_connections" list does not have an entry for the failed connection
    3. The client state is unchanged
    """
    # Ensure that the "active_connections" list is initially empty
    socket_connection_manager.active_connections.clear()
    assert len(socket_connection_manager.active_connections) == 0

    # Create mock socket that raises RuntimeError on accept
    socket = mock.MagicMock(spec=WebSocket)
    socket.accept.side_effect = RuntimeError(
        'Cannot call "receive" once a close message has been sent.'
    )
    connection = WebSocketConnection(socket, WebSocketTypeEnum.MAIN)

    with pytest.raises(RuntimeError):
        await socket_connection_manager.connect(connection=connection)

    # Ensure that "active_connections" list does not contain the failed socket
    assert len(socket_connection_manager.active_connections) == 0
    socket.accept.assert_called_once()


def test_disconnect() -> None:
    """
    Test whether the disconnect() function removes the socket object from the list of
    active_connections.
    """
    socket_connection_manager.active_connections.clear()

    # Add a websocket object to the "active_connections" list to imitate
    # an existing active connection
    socket = mock.MagicMock(spec=WebSocket)
    connection = WebSocketConnection(socket, WebSocketTypeEnum.MAIN)
    socket_connection_manager.active_connections.append(connection)
    assert len(socket_connection_manager.active_connections) == 1

    socket_connection_manager.disconnect(connection=connection)

    # Verify that the "active_connections" list does not have the disconnected socket
    assert len(socket_connection_manager.active_connections) == 0

    # Cleanup
    socket_connection_manager.active_connections.clear()


@pytest.mark.asyncio
async def test_send_personal_message() -> None:
    """
    Validate that send_personal_message() function handles the message json conversions
    correctly.
    """
    # Create test data
    test_message = {
        MessageKeysEnum.TYPE: MessageTypeEnum.INVALID_MESSAGE,
        MessageKeysEnum.PAYLOAD: "Test message",
    }
    expected_parameter = json.dumps(test_message)

    socket = mock.MagicMock(spec=WebSocket)

    await socket_connection_manager.send_personal_message(
        message=test_message, websocket=socket
    )
    socket.send_text.assert_called_once_with(expected_parameter)


@pytest.mark.asyncio
async def test_broadcast_message_data_types() -> None:
    """
    Validate that broadcast() is able to handle messages of types String, List or
    Dictionary.
    """
    # Create test data
    test_message = "Test message"
    test_message_dict = {
        MessageKeysEnum.TYPE: MessageTypeEnum.INVALID_MESSAGE,
        MessageKeysEnum.PAYLOAD: test_message,
    }
    expected_parameter_dict = json.dumps(test_message_dict)
    test_message_list = ["test", "message", "broadcast"]
    expected_parameter_list = json.dumps(test_message_list)

    socket_connection_manager.active_connections.clear()
    # Add a websocket object to the "active_connections" list to imitate an existing
    # active connection
    socket = mock.MagicMock(spec=WebSocket)
    connection = WebSocketConnection(socket, WebSocketTypeEnum.MAIN)
    socket_connection_manager.active_connections.append(connection)
    assert len(socket_connection_manager.active_connections) == 1

    await socket_connection_manager.broadcast(message=test_message)
    socket.send_text.assert_called_with(test_message)

    await socket_connection_manager.broadcast(message=test_message_dict)
    socket.send_text.assert_called_with(expected_parameter_dict)

    await socket_connection_manager.broadcast(message=test_message_list)
    socket.send_text.assert_called_with(expected_parameter_list)

    # Cleanup
    socket_connection_manager.active_connections.clear()


@pytest.mark.asyncio
async def test_broadcast_failed_for_ConnectionClosed() -> None:
    """
    Tests if broadcast() is able to handle the event where the connection is closed.
    """
    test_message = "Test"
    socket_connection_manager.active_connections.clear()

    # Add a websocket object to the "active_connections" list to imitate
    # an existing active connection
    socket = mock.MagicMock(spec=WebSocket)
    socket.application_state = WebSocketState.CONNECTED
    connection = WebSocketConnection(socket, WebSocketTypeEnum.MAIN)

    socket_connection_manager.active_connections.append(connection)
    assert len(socket_connection_manager.active_connections) == 1

    # Force a connection closed exception
    socket.send_text.side_effect = ConnectionClosedOK(rcvd=None, sent=None)

    await socket_connection_manager.broadcast(message=test_message)
    socket.send_text.assert_called_once_with(test_message)
    socket.close.assert_called_once()

    # Cleanup
    socket_connection_manager.active_connections.clear()


@pytest.mark.asyncio
async def test_broadcast_failed_for_ConnectionClosedError() -> None:
    """
    Tests that broadcast() also handles ConnectionClosedError (an abrupt
    drop, e.g. from a missed keepalive ping under event-loop stall) the same
    way as ConnectionClosedOK: the socket is closed and the dead connection
    is removed from active_connections so it isn't retried for the rest of
    the process's life (regression test for issue #1072).
    """
    test_message = "Test"
    socket_connection_manager.active_connections.clear()

    # Add a websocket object to the "active_connections" list to imitate
    # an existing active connection
    socket = mock.MagicMock(spec=WebSocket)
    socket.application_state = WebSocketState.CONNECTED
    connection = WebSocketConnection(socket, WebSocketTypeEnum.MAIN)

    socket_connection_manager.active_connections.append(connection)
    assert len(socket_connection_manager.active_connections) == 1

    # Force an abrupt connection-closed exception
    socket.send_text.side_effect = ConnectionClosedError(rcvd=None, sent=None)

    await socket_connection_manager.broadcast(message=test_message)
    socket.send_text.assert_called_once_with(test_message)
    socket.close.assert_called_once()
    assert connection not in socket_connection_manager.active_connections

    # Cleanup
    socket_connection_manager.active_connections.clear()


@pytest.mark.asyncio
async def test_broadcast_failed_for_RuntimeError() -> None:
    """
    Tests if broadcast() is able to handle run time errors.

    Expected results:
    1. RuntimeError is raised
    2. "Send" is called in an attempt to broadcast
    """
    test_message = "Test"
    expected_parameter = {"type": "websocket.send", "text": test_message}

    # Add a websocket object to the "active_connections" list to imitate
    # an existing active connection
    socket_connection_manager.active_connections.clear()
    socket = mock.MagicMock(spec=WebSocket)
    connection = WebSocketConnection(socket, WebSocketTypeEnum.MAIN)
    socket_connection_manager.active_connections.append(connection)
    assert len(socket_connection_manager.active_connections) == 1

    socket.send_text.side_effect = RuntimeError(
        'Cannot call "receive" once a disconnect message has been received.'
    )

    with pytest.raises(RuntimeError):
        await socket_connection_manager.broadcast(message=test_message)
        socket.send_text.assert_called_with(expected_parameter)

    # Cleanup
    socket_connection_manager.active_connections.clear()


@pytest.mark.asyncio
async def test_received_message_valid_json() -> None:
    """
    Tests if received_message() is able to handle a message with valid
    JSON format.
    """
    test_message = json.dumps(__expected_response_dict_okay())
    expected_json_dict_parameter = json.loads(test_message)
    socket = mock.MagicMock()
    with mock.patch.object(
        SocketConnectionManager,
        "_SocketConnectionManager__handle_received_json",
    ) as handle_received_json:
        await socket_connection_manager.received_message(
            websocket=socket, message=test_message
        )
        handle_received_json.assert_called_once_with(
            socket, expected_json_dict_parameter
        )


@pytest.mark.asyncio
async def test_received_message_invalid_json() -> None:
    """
    Validates if received_message() is able to notify about a message with invalid
    JSON format.
    """
    socket = mock.MagicMock()
    with mock.patch.object(
        SocketConnectionManager,
        "_SocketConnectionManager__notify_invalid_message",
    ) as notify_invalid_message:
        await socket_connection_manager.received_message(
            websocket=socket, message="Invalid"
        )
        notify_invalid_message.assert_called_once_with(
            websocket=socket, message=INVALID_JSON_ERROR_STR
        )


def _bind_ephemeral_udp_port() -> int:
    """Reserve a free UDP port on loopback, then release it for the code
    under test to bind to - avoids hard-coding the real UDP_SOCKET_PORT
    (5000), which would conflict with a live TH instance or with parallel
    test workers (pytest-xdist)."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


@pytest.mark.asyncio
async def test_relay_video_frames_forwards_frames_until_disconnect() -> None:
    """
    Validates that relay_video_frames() forwards UDP frames to the websocket
    over a real (ephemeral-port, loopback) socket, and that a client
    disconnect (detected via receive_text()) cleanly cancels the pending UDP
    receive. Uses a real socket rather than mocking `sock.recvfrom()`,
    because the implementation now uses the event loop's native
    `sock_recv()` (regression coverage for the switch away from a
    thread-pool-blocking `recvfrom()`, which couldn't be cancelled once the
    underlying OS thread was blocked in it).
    """
    frame = b"fake-h264-frame"
    port = _bind_ephemeral_udp_port()

    websocket = mock.MagicMock(spec=WebSocket)
    websocket.send_bytes = mock.AsyncMock()
    websocket.close = mock.AsyncMock()

    async def _disconnect_after_first_frame() -> str:
        # Give the UDP relay task a chance to process the first frame before
        # the disconnect is "detected".
        await asyncio.sleep(0.2)
        raise WebSocketDisconnect()

    websocket.receive_text = mock.AsyncMock(side_effect=_disconnect_after_first_frame)

    connection = WebSocketConnection(websocket, WebSocketTypeEnum.VIDEO)

    with mock.patch("app.socket_connection_manager.UDP_SOCKET_PORT", port), mock.patch(
        "app.socket_connection_manager.UDP_SOCKET_INTERFACE", "127.0.0.1"
    ):
        relay_task = asyncio.ensure_future(
            socket_connection_manager.relay_video_frames(connection)
        )
        await asyncio.sleep(0.1)  # let relay_video_frames bind before sending

        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sender.sendto(frame, ("127.0.0.1", port))
        sender.close()

        await asyncio.wait_for(relay_task, timeout=2.0)

    websocket.send_bytes.assert_any_call(frame)
    websocket.close.assert_called_once()
    assert connection not in socket_connection_manager.active_connections


@pytest.mark.asyncio
async def test_relay_video_frames_cancels_pending_udp_receive_on_disconnect() -> None:
    """
    Regression test: disconnecting while the UDP receive is genuinely
    pending (no frames ever arrive) must cancel it promptly rather than
    leaving it hanging. This is the failure mode of the old
    run_in_executor()-based recvfrom(): cancelling the asyncio task couldn't
    stop the underlying OS thread once it was blocked in a real recvfrom()
    call, leaving executor work behind.
    """
    port = _bind_ephemeral_udp_port()

    websocket = mock.MagicMock(spec=WebSocket)
    websocket.send_bytes = mock.AsyncMock()
    websocket.close = mock.AsyncMock()
    websocket.receive_text = mock.AsyncMock(side_effect=WebSocketDisconnect())

    connection = WebSocketConnection(websocket, WebSocketTypeEnum.VIDEO)

    with mock.patch("app.socket_connection_manager.UDP_SOCKET_PORT", port), mock.patch(
        "app.socket_connection_manager.UDP_SOCKET_INTERFACE", "127.0.0.1"
    ):
        # No data is ever sent to `port`, so the UDP receive stays genuinely
        # pending. If disconnecting doesn't cancel it cleanly, this hangs and
        # the test fails with a TimeoutError instead of passing silently.
        await asyncio.wait_for(
            socket_connection_manager.relay_video_frames(connection), timeout=2.0
        )

    websocket.close.assert_called_once()
    assert connection not in socket_connection_manager.active_connections


@pytest.mark.asyncio
async def test_relay_video_frames_wrong_connection_type() -> None:
    """
    Validates that relay_video_frames() refuses to run for a connection that
    isn't of type VIDEO, without touching any sockets.
    """
    websocket = mock.MagicMock(spec=WebSocket)
    connection = WebSocketConnection(websocket, WebSocketTypeEnum.MAIN)

    with mock.patch("app.socket_connection_manager.socket.socket") as mock_socket_cls:
        await socket_connection_manager.relay_video_frames(connection)

        mock_socket_cls.assert_not_called()
    websocket.close.assert_not_called()


def __expected_response_dict_okay() -> Dict[MessageKeysEnum, Any]:
    return {
        MessageKeysEnum.TYPE: MessageTypeEnum.PROMPT_RESPONSE,
        MessageKeysEnum.PAYLOAD: {
            RESPONSE_KEY: 1,
            STATUS_CODE_KEY: UserResponseStatusEnum.OKAY,
            MESSAGE_ID_KEY: 1,
        },
    }
