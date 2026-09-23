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

"""Implementation of the Wi-Fi fixture container."""

import asyncio
from asyncio.tasks import wait_for
from typing import Any, Optional

from docker.models.containers import Container

from app.container_manager import container_manager
from app.singleton import Singleton
from app.test_engine.logger import test_engine_logger as logger
from test_collections.matter.test_environment_config import WiFiConfig

# Built from `wifi_container` in this repository.
# Tracking :latest until the image lands in main and there is a commit to pin.
DEFAULT_DOCKER_IMAGE = "ghcr.io/project-chip/csa-certification-tool-wifi:latest"

CONTAINER_NAME = "certification-tool-wifi"

# The one directory the fixture and the tests share, holding the daemons' control
# sockets and the configuration written for them. The same path on the host and in
# every container, so that a control client's reply socket resolves to the same
# file in the daemon's mount namespace as in its own.
WIFI_FIXTURE_ROOT = "/run/wifi-fixture"

# Startup is a container start and two daemons that hold no interface yet, so this
# only has to cover a slow first start from a cold page cache.
WIFI_FIXTURE_STARTUP_TIMEOUT = 30


class WiFiContainerError(Exception):
    pass


def require_unclaimed_interfaces(ifnames: list[str]) -> None:
    """Fails unless the fixture can have these radios to itself.

    A host service that also manages one will fight the fixture for it: at best by
    suppressing the link-local IPv6 address the access point needs for a DUT to
    reach the Test Harness, at worst by taking the interface down, putting it back
    in station mode, or changing its MAC address in the middle of a test. None of
    that is the fixture's to repair.
    """
    # Imported here rather than at module scope so that a backend image without the
    # D-Bus client this needs affects Wi-Fi runs only: every Python test suite
    # reaches this module, by way of sdk_container.
    from .host_network_config import interface_claims

    claims = interface_claims(ifnames)
    managed = [
        f"{ifname} is managed by {' and '.join(services)}"
        for ifname, services in claims.items()
        if services
    ]
    if managed:
        raise WiFiContainerError(
            f"The Wi-Fi fixture requires exclusive use of the interfaces it is given,"
            f" but {', '.join(managed)}"
        )

    if claims:
        logger.info(f"No known host service manages {', '.join(ifnames)}")


class WiFiContainer(metaclass=Singleton):
    """The Wi-Fi fixture container, for the duration of a test suite.

    Usage:
    Create an instance by calling the initializer. When ready to use, start the
    container by calling start, and when done clean up by calling destroy.
    Everything in between is driven test-side over the daemons' control sockets in
    WIFI_FIXTURE_ROOT; this class only owns the container.
    """

    run_parameters: dict[str, Any] = {
        "privileged": True,
        "detach": True,
        "network": "host",
        "name": CONTAINER_NAME,
        "volumes": {WIFI_FIXTURE_ROOT: {"bind": WIFI_FIXTURE_ROOT, "mode": "rw"}},
    }

    def __init__(self) -> None:
        self.__container: Optional[Container] = None
        self.__docker_image = DEFAULT_DOCKER_IMAGE

    def __load_config(self, config: WiFiConfig) -> None:
        if not config.interfaces:
            raise WiFiContainerError(
                "Unable to start the Wi-Fi fixture as no interfaces are configured."
                " Change in settings."
            )

        # Naming the radios is all the fixture is told. It resolves them itself and
        # publishes what it managed to claim, so a dongle that failed to enumerate
        # stops the container here rather than failing a test later on.
        self.run_parameters["environment"] = [
            "WIFI_FIXTURE_IFNAMES=" + ",".join(config.interfaces)
        ]

        # This instance outlives the suite that configured it, so start from the
        # default every time rather than letting a previous suite's override stick.
        self.__docker_image = DEFAULT_DOCKER_IMAGE
        if config.docker_image is not None:
            self.__docker_image = config.docker_image
            logger.warning(
                "Overriding default Wi-Fi fixture docker image with"
                f" '{self.__docker_image}'."
            )

    def is_running(self) -> bool:
        if self.__container is None:
            return False
        return container_manager.is_running(self.__container)

    async def start(self, config: WiFiConfig) -> bool:
        """Create the fixture container with the configured radios.

        Returns true once both daemons answer on their global control socket, or
        false if the container is already running.
        """
        if self.is_running():
            logger.warning(
                "Wi-Fi fixture container is already running for " + self.__docker_image
            )
            return False

        self.__load_config(config)
        logger.info(f"Preparing Wi-Fi fixture using interfaces {config.interfaces}")

        # Check the radios are unclaimed before starting the container.
        require_unclaimed_interfaces(config.interfaces)

        # Remove anything still holding the radios: a container this instance no
        # longer tracks (a failed start, or a backend restart that dropped the
        # reference), and one started by hand for debugging. Both would keep the new
        # container's hostapd from claiming the dongle.
        self.__destroy_existing_container()
        container_manager.remove_containers_for_image(self.__docker_image)

        logger.info(f"Starting Wi-Fi fixture using docker image: {self.__docker_image}")
        self.__container = await container_manager.create_container(
            self.__docker_image, self.run_parameters
        )

        try:
            await wait_for(self.__wait_for_daemons(), WIFI_FIXTURE_STARTUP_TIMEOUT)
        except (asyncio.exceptions.TimeoutError, WiFiContainerError) as error:
            logger.warning(self.__container.logs().decode("utf-8"))
            err_msg = f"Wi-Fi fixture did not start properly: {error}"
            logger.error(err_msg)
            self.destroy()
            raise WiFiContainerError(err_msg)

        logger.info(
            f"""
            Wi-Fi fixture started: {self.__container.name}
            with configuration: {self.run_parameters}
            """
        )
        return True

    def __destroy_existing_container(self) -> None:
        """Kill and remove any existing container using the same name."""
        existing_container = container_manager.get_container(CONTAINER_NAME)
        if existing_container is not None:
            logger.info(
                f'Existing container named "{CONTAINER_NAME}" found. Destroying.'
            )
            container_manager.destroy(existing_container)

    async def __wait_for_daemons(self) -> None:
        """Wait for hostapd and wpa_supplicant to answer on their global sockets."""
        while True:
            if not self.is_running():
                raise WiFiContainerError("the container exited during startup")

            if self.__ping("hostapd_cli") and self.__ping("wpa_cli"):
                return

            await asyncio.sleep(0.5)

    def __ping(self, cli: str) -> bool:
        # Run the CLI in the container rather than talking to the socket from here,
        # so that its reply socket lands in the same mount namespace as the daemon's
        # and the backend needs no share of WIFI_FIXTURE_ROOT. The control interface
        # directory is compiled into both CLIs, so -i global is enough.
        result = self.__container.exec_run(f"{cli} -i global ping")  # type: ignore
        return result.exit_code == 0 and b"PONG" in result.output

    def destroy(self) -> None:
        """Destroy the fixture container."""
        if self.__container is None:
            return

        # Graceful stop so that the supervisor gets to signal both daemons and they
        # release the radios, rather than leaving that to the kernel reaping the
        # netlink sockets.
        container_manager.destroy(self.__container, graceful=True)
        self.__container = None
