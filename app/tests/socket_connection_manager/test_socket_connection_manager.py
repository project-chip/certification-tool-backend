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
import json
from typing import Any, Dict
from unittest import mock

import pytest
from fastapi import WebSocket
from starlette.websockets import WebSocketState
from websockets.exceptions import ConnectionClosedOK

from app.constants.websockets_constants import (
    INVALID_JSON_ERROR_STR,
    MESSAGE_ID_KEY,
    MessageKeysEnum,
    MessageTypeEnum,
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


def __expected_response_dict_okay() -> Dict[MessageKeysEnum, Any]:
    return {
        MessageKeysEnum.TYPE: MessageTypeEnum.PROMPT_RESPONSE,
        MessageKeysEnum.PAYLOAD: {
            RESPONSE_KEY: 1,
            STATUS_CODE_KEY: UserResponseStatusEnum.OKAY,
            MESSAGE_ID_KEY: 1,
        },
    }
