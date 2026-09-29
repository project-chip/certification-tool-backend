#
# Copyright (c) 2026 Project CHIP Authors
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
from typing import Any, List, Optional, Tuple
from unittest import mock

import pytest
from jeepney import HeaderFields, Message, MessageFlag, new_error, new_method_return

from .. import system_bus
from ..system_bus import DBusError, SystemBus, SystemBusUnavailable

SERVICE = "org.freedesktop.network1"
PATH = "/org/freedesktop/network1"
INTERFACE = "org.freedesktop.network1.Manager"


class FakeConnection:
    """Answers each call with the next scripted reply, or raises it."""

    def __init__(self, answers: List[Any]) -> None:
        self.__answers = list(answers)
        self.sent: List[Message] = []
        self.closed = False

    def send_and_get_reply(
        self, message: Message, timeout: Optional[float] = None
    ) -> Message:
        message.header.serial = len(self.sent) + 1
        self.sent.append(message)
        answer = self.__answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        signature, body = answer
        if isinstance(signature, str) and signature.startswith("!"):
            return new_error(message, signature[1:], "s", body)
        return new_method_return(message, signature, body)

    def close(self) -> None:
        self.closed = True


def returns(signature: Optional[str], body: Tuple[Any, ...]) -> Tuple[Any, Any]:
    return (signature, body)


def fails(name: str, message: str = "") -> Tuple[Any, Any]:
    return ("!" + name, (message,))


def connected(connection: FakeConnection) -> Any:
    return mock.patch.object(
        system_bus, "open_dbus_connection", return_value=connection
    )


def test_call_returns_the_reply_body() -> None:
    connection = FakeConnection([returns("io", (4, "/link/_34"))])

    with connected(connection), SystemBus() as bus:
        assert bus.call(SERVICE, PATH, INTERFACE, "GetLinkByName", "s", ("wlan1",)) == (
            4,
            "/link/_34",
        )

    assert connection.closed


def test_call_raises_the_error_name() -> None:
    connection = FakeConnection([fails(system_bus.SERVICE_UNKNOWN, "no owner")])

    with connected(connection), SystemBus() as bus:
        try:
            bus.call(SERVICE, PATH, INTERFACE, "GetLinkByName", "s", ("wlan1",))
        except DBusError as error:
            assert error.name == system_bus.SERVICE_UNKNOWN
            assert "no owner" in str(error)
        else:
            raise AssertionError("An error reply should have raised DBusError")


def test_call_does_not_activate_the_service() -> None:
    connection = FakeConnection([returns(None, ())])

    with connected(connection), SystemBus() as bus:
        bus.call(SERVICE, PATH, INTERFACE, "Reload")

    assert connection.sent[0].header.flags & MessageFlag.no_auto_start


def test_properties_unwraps_the_variants() -> None:
    values = {"AdministrativeState": ("s", "unmanaged"), "Index": ("i", 4)}
    connection = FakeConnection([returns("a{sv}", (values,))])

    with connected(connection), SystemBus() as bus:
        properties = bus.properties(SERVICE, PATH, INTERFACE)

    assert properties == {"AdministrativeState": "unmanaged", "Index": 4}

    asked = connection.sent[0]
    assert asked.header.fields[HeaderFields.member] == "GetAll"
    assert (
        asked.header.fields[HeaderFields.interface] == system_bus.PROPERTIES_INTERFACE
    )
    assert asked.body == (INTERFACE,)


def test_a_service_that_does_not_answer_is_unavailable() -> None:
    connection = FakeConnection([TimeoutError("no reply in 5 seconds")])

    with connected(connection), SystemBus() as bus:
        with pytest.raises(SystemBusUnavailable):
            bus.call(SERVICE, PATH, INTERFACE, "GetLinkByName", "s", ("wlan1",))


def test_a_bus_that_cannot_be_connected_to_is_unavailable() -> None:
    missing = mock.patch.object(
        system_bus,
        "open_dbus_connection",
        side_effect=FileNotFoundError("/var/run/dbus/system_bus_socket"),
    )

    with missing, pytest.raises(SystemBusUnavailable):
        with SystemBus():
            pass


def test_calling_outside_the_with_block_is_a_programming_error() -> None:
    with pytest.raises(RuntimeError):
        SystemBus().call(SERVICE, PATH, INTERFACE, "GetLinkByName", "s", ("wlan1",))
