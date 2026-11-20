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

"""Which network interfaces the host's Avahi daemon leaves out.

Reads the host's avahi-daemon.conf, which docker-compose mounts into this
container read-only at HOST_AVAHI_CONF, and asks systemd over the system bus when
the running daemon started, to tell whether it has loaded that file.
"""

import configparser
from pathlib import Path
from typing import List, Optional

from app.test_engine.logger import test_engine_logger as logger

from .system_bus import DBusError, SystemBus, SystemBusUnavailable

HOST_AVAHI_CONF = Path("/host/etc/avahi/avahi-daemon.conf")

SERVER_SECTION = "server"

SYSTEMD_SERVICE = "org.freedesktop.systemd1"
SYSTEMD_PATH = "/org/freedesktop/systemd1"
SYSTEMD_MANAGER_INTERFACE = "org.freedesktop.systemd1.Manager"
SYSTEMD_UNIT_INTERFACE = "org.freedesktop.systemd1.Unit"
AVAHI_UNIT = "avahi-daemon.service"


def __interface_list(
    server: configparser.SectionProxy, key: str
) -> Optional[List[str]]:
    """Splits a comma-separated interface list option the way Avahi does.

    Entries are stripped of spaces and tabs and lowercased, for Avahi's
    case-insensitive match. Returns None when the option is unset, and a list
    (possibly of empty names) when it is set, even to nothing.
    """
    if key not in server:
        return None
    return [name.strip(" \t").lower() for name in server[key].split(",")]


def avahi_excluded_interfaces(
    ifnames: List[str], conf_path: Path = HOST_AVAHI_CONF
) -> List[str]:
    """Names those of ifnames that the host's Avahi configuration excludes.

    An interface is excluded when deny-interfaces lists it, or when
    allow-interfaces is set and does not list it. Returns nothing if the
    configuration could not be read.
    """
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    try:
        with open(conf_path, encoding="utf-8") as conf:
            parser.read_file(conf)
    except (OSError, configparser.Error) as error:
        logger.warning(
            f"Host Avahi config: Unable to check which interfaces Avahi uses: {error}"
        )
        return []

    if not parser.has_section(SERVER_SECTION):
        return []
    server = parser[SERVER_SECTION]

    allowed = __interface_list(server, "allow-interfaces")
    denied = __interface_list(server, "deny-interfaces") or []
    return [
        ifname
        for ifname in ifnames
        if ifname.lower() in denied
        or (allowed is not None and ifname.lower() not in allowed)
    ]


def __avahi_started_usec() -> Optional[int]:
    """When the running avahi-daemon.service started, in microseconds since the
    epoch, or None if it is not running or systemd could not be asked."""
    try:
        with SystemBus() as bus:
            (unit,) = bus.call(
                SYSTEMD_SERVICE,
                SYSTEMD_PATH,
                SYSTEMD_MANAGER_INTERFACE,
                "GetUnit",
                "s",
                (AVAHI_UNIT,),
            )
            properties = bus.properties(SYSTEMD_SERVICE, unit, SYSTEMD_UNIT_INTERFACE)
    except (SystemBusUnavailable, DBusError) as error:
        logger.warning(
            f"Host Avahi config: Unable to check when {AVAHI_UNIT} started: {error}"
        )
        return None

    if properties.get("ActiveState") != "active":
        return None
    return properties.get("ActiveEnterTimestamp")


def avahi_restart_pending(conf_path: Path = HOST_AVAHI_CONF) -> bool:
    """Whether the host's avahi-daemon.conf changed after the daemon started.

    False when the file is missing or the daemon's start time is unknown.
    """
    try:
        modified_usec = conf_path.stat().st_mtime_ns // 1000
    except OSError:
        return False

    started_usec = __avahi_started_usec()
    return started_usec is not None and modified_usec > started_usec
