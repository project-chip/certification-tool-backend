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

"""A small client for the host's D-Bus system bus.

Only what is needed to ask a host service about its own state: call a method,
read an interface's properties, and tell an error reply apart from a service that
is not running at all. Bus names, object paths and interfaces are passed as
strings, so that nothing outside this module depends on the D-Bus library.

The bus is the host's, over the socket docker-compose mounts into this container
at /var/run/dbus, which is where jeepney looks by default.
"""

from types import TracebackType
from typing import Any, Dict, Optional, Tuple, Type

from jeepney import (
    AuthenticationError,
    DBusAddress,
    HeaderFields,
    MessageFlag,
    MessageType,
    new_method_call,
)
from jeepney.io.blocking import DBusConnection, open_dbus_connection

PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"

# What the bus itself answers when nothing owns the name a call was addressed to,
# which is how a service that is not installed, or not running, presents.
SERVICE_UNKNOWN = "org.freedesktop.DBus.Error.ServiceUnknown"

# Every call made through here is a local daemon reporting its own state, so one
# that does not answer promptly is wedged rather than busy.
CALL_TIMEOUT = 5.0


class SystemBusUnavailable(Exception):
    """The bus could not be asked: no socket, nothing listening, or no answer."""


class DBusError(Exception):
    """An error reply, carrying the error name so that a caller can match on it."""

    def __init__(self, name: str, message: str = "") -> None:
        super().__init__(f"{name}: {message}" if message else name)
        self.name = name


class SystemBus:
    """A connection to the system bus, open for the duration of a with block.

    Every failure that is not a service answering is a SystemBusUnavailable, so a
    caller has two cases to handle: an answer it did not like, or no answer.

    Calls never activate a service. Asking whether one is running must not be the
    thing that starts it, so a service that is installed but stopped answers
    SERVICE_UNKNOWN here, the same as one that is not installed at all.
    """

    def __init__(self, timeout: float = CALL_TIMEOUT) -> None:
        self.__timeout = timeout
        self.__connection: Optional[DBusConnection] = None

    def __enter__(self) -> "SystemBus":
        try:
            self.__connection = open_dbus_connection(bus="SYSTEM")
        except (OSError, AuthenticationError) as error:
            raise SystemBusUnavailable(
                f"could not connect to the system bus: {error}"
            ) from error
        return self

    def __exit__(
        self,
        exception_type: Optional[Type[BaseException]],
        exception: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        if self.__connection is not None:
            self.__connection.close()
            self.__connection = None

    def call(
        self,
        service: str,
        path: str,
        interface: str,
        method: str,
        signature: Optional[str] = None,
        body: Tuple[Any, ...] = (),
    ) -> Tuple[Any, ...]:
        """Calls a method and returns the values in the reply.

        Raises DBusError if the service answered with an error, and
        SystemBusUnavailable if it did not answer at all.
        """
        if self.__connection is None:
            raise RuntimeError("A SystemBus is only usable inside its with block")

        address = DBusAddress(path, bus_name=service, interface=interface)
        message = new_method_call(address, method, signature, body)
        # Without this the bus starts an installed but stopped service to answer,
        # instead of answering SERVICE_UNKNOWN itself. See the class docstring.
        message.header.flags |= MessageFlag.no_auto_start

        try:
            reply = self.__connection.send_and_get_reply(
                message, timeout=self.__timeout
            )
        except OSError as error:
            # Includes TimeoutError, which is an OSError in the versions of Python
            # this runs on.
            raise SystemBusUnavailable(
                f"{service} did not answer {interface}.{method}: {error}"
            ) from error

        if reply.header.message_type is MessageType.error:
            name = reply.header.fields.get(HeaderFields.error_name, "(no error name)")
            detail = reply.body[0] if reply.body else ""
            raise DBusError(name, detail if isinstance(detail, str) else "")

        return reply.body

    def properties(self, service: str, path: str, interface: str) -> Dict[str, Any]:
        """Reads every property of one interface, unwrapping the variants.

        One call for the whole interface rather than one per property, so that a
        caller reading several of them cannot see a half-answered object.
        """
        (values,) = self.call(
            service,
            path,
            PROPERTIES_INTERFACE,
            "GetAll",
            "s",
            (interface,),
        )
        return {name: value for name, (_signature, value) in values.items()}
