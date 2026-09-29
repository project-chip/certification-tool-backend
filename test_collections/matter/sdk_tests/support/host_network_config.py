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

"""Which host services manage a network interface.

Each service that could be managing one is asked directly, over the system bus.
Deliberately not by looking for symptoms -- an interface with no link-local
address, say -- because the symptoms vary with the service and with what it is
doing, while "does anything else manage this" is one question with one answer.

Reporting is all this does. The Wi-Fi fixture is the caller that cares, and what
it makes of an answer is in require_unclaimed_interfaces in wifi_container.py.
"""

from typing import Callable, Dict, List, Mapping

from app.test_engine.logger import test_engine_logger as logger

from .system_bus import DBusError, SystemBus, SystemBusUnavailable

NETWORK_MANAGER_SERVICE = "org.freedesktop.NetworkManager"
NETWORK_MANAGER_PATH = "/org/freedesktop/NetworkManager"
NETWORK_MANAGER_DEVICE_INTERFACE = "org.freedesktop.NetworkManager.Device"

NETWORKD_SERVICE = "org.freedesktop.network1"
NETWORKD_PATH = "/org/freedesktop/network1"
NETWORKD_MANAGER_INTERFACE = "org.freedesktop.network1.Manager"
NETWORKD_LINK_INTERFACE = "org.freedesktop.network1.Link"
NETWORKD_UNMANAGED = "unmanaged"

SUPPLICANT_SERVICE = "fi.w1.wpa_supplicant1"
SUPPLICANT_PATH = "/fi/w1/wpa_supplicant1"


def __network_manager_manages(bus: SystemBus, ifname: str) -> bool:
    (device,) = bus.call(
        NETWORK_MANAGER_SERVICE,
        NETWORK_MANAGER_PATH,
        NETWORK_MANAGER_SERVICE,
        "GetDeviceByIpIface",
        "s",
        (ifname,),
    )
    properties = bus.properties(
        NETWORK_MANAGER_SERVICE, device, NETWORK_MANAGER_DEVICE_INTERFACE
    )
    return bool(properties.get("Managed"))


def __networkd_manages(bus: SystemBus, ifname: str) -> bool:
    # networkd keeps a record of every link on the machine, so having one is not
    # a claim: only a link it is configuring has an administrative state other
    # than "unmanaged".
    _index, link = bus.call(
        NETWORKD_SERVICE,
        NETWORKD_PATH,
        NETWORKD_MANAGER_INTERFACE,
        "GetLinkByName",
        "s",
        (ifname,),
    )
    state = bus.properties(NETWORKD_SERVICE, link, NETWORKD_LINK_INTERFACE).get(
        "AdministrativeState"
    )
    return state is not None and state != NETWORKD_UNMANAGED


def __supplicant_manages(bus: SystemBus, ifname: str) -> bool:
    # Unlike the other two, holding the interface at all is the claim: one the
    # host's supplicant has been given is one it is driving.
    bus.call(
        SUPPLICANT_SERVICE,
        SUPPLICANT_PATH,
        SUPPLICANT_SERVICE,
        "GetInterface",
        "s",
        (ifname,),
    )
    return True


CLAIMANTS: Mapping[str, Callable[[SystemBus, str], bool]] = {
    "NetworkManager": __network_manager_manages,
    "systemd-networkd": __networkd_manages,
    "wpa_supplicant": __supplicant_manages,
}


def __claimants_of(bus: SystemBus, ifname: str) -> List[str]:
    """Names the services that say they manage this interface.

    An error reply is never read as a claim. This check exists to stop a
    misconfigured host from wasting a run, and must not become the thing that
    stops a working one, so a service that is not running, does not know the
    interface, or answers something unexpected is taken as not managing it.
    """
    claimants = []
    for service, manages in CLAIMANTS.items():
        try:
            if manages(bus, ifname):
                claimants.append(service)
        except DBusError as error:
            logger.debug(
                f"Host network config: {service} query for {ifname} returned {error}"
            )
    return claimants


def interface_claims(ifnames: List[str]) -> Dict[str, List[str]]:
    """Names the host services managing each of these interfaces.

    Returns nothing at all if the system bus could not be reached: a host this
    cannot ask is not a host it can accuse.
    """
    try:
        with SystemBus() as bus:
            return {ifname: __claimants_of(bus, ifname) for ifname in ifnames}
    except SystemBusUnavailable as error:
        logger.warning(
            "Host network config: Unable to check which host services manage"
            f" {', '.join(ifnames)}: {error}"
        )
        return {}
