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
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import loguru
from docker.models.containers import Container

from app.container_manager import container_manager
from app.schemas.pics import PICS, PICSError
from app.singleton import Singleton
from app.test_engine.logger import test_engine_logger as logger
from test_collections.matter.config import matter_settings

from .exec_run_in_container import ExecResultExtended, exec_run_in_container
from .pics import set_pics_command

# Trace mount
LOCAL_LOGS_PATH = Path("/var/tmp")
DOCKER_LOGS_PATH = "/logs"

# PAA Cert mount
LOCAL_PAA_CERTS_PATH = Path("/var/paa-root-certs")
DOCKER_PAA_CERTS_PATH = "/paa-root-certs"

# Credentials Development mount
LOCAL_CREDENTIALS_DEVELOPMENT_PATH = Path("/var/credentials/development")
DOCKER_CREDENTIALS_DEVELOPMENT_PATH = "/credentials/development"

# Python Testing Folder
LOCAL_TEST_COLLECTIONS_PATH = (
    "/home/ubuntu/certification-tool/backend/test_collections/matter"
)

LOCAL_PYTHON_TESTING_PATH = Path(
    LOCAL_TEST_COLLECTIONS_PATH + "/sdk_tests/sdk_checkout/python_testing"
)
DOCKER_PYTHON_TESTING_PATH = "/root/python_testing"

MAPPED_DATA_MODEL_VOLUME = "mapped_data_model_volume"
DOCKER_DATA_MODEL_PATH = DOCKER_PYTHON_TESTING_PATH + "/data_model"


# RPC Client Running on SDK Container
LOCAL_RPC_PYTHON_TESTING_PATH = Path(
    LOCAL_TEST_COLLECTIONS_PATH + "/sdk_tests/support/python_testing/models/rpc_client/"
    "test_harness_client.py"
)
DOCKER_RPC_PYTHON_TESTING_PATH = "/root/python_testing/scripts/sdk/matter_testing_infrastructure/chip/testing/test_harness_client.py"  # noqa

# Stress/Stability Test Script (For now it is injected on SDK container.)
LOCAL_STRESS_TEST_SCRIPT_PATH = Path(
    LOCAL_TEST_COLLECTIONS_PATH + "/sdk_tests/support/performance_tests/scripts/sdk/"
    "TC_COMMISSIONING_1_0.py"
)
DOCKER_STRESS_TEST_SCRIPT_PATH = (
    "/root/python_testing/scripts/sdk/TC_COMMISSIONING_1_0.py"
)

LOCAL_STRESS_TEST_ACCESSORY_MANAGER_SCRIPT_PATH = Path(
    LOCAL_TEST_COLLECTIONS_PATH + "/sdk_tests/support/performance_tests/scripts/sdk/"
    "accessory_manager.py"
)
DOCKER_STRESS_TEST_ACCESSORY_MANAGER_SCRIPT_PATH = (
    "/root/python_testing/scripts/sdk/accessory_manager.py"
)

LOCAL_STRESS_TEST_SIMULATED_ACCESSORY_SCRIPT_PATH = Path(
    LOCAL_TEST_COLLECTIONS_PATH + "/sdk_tests/support/performance_tests/scripts/sdk/"
    "simulated_accessory.py"
)
DOCKER_STRESS_TEST_SIMULATED_ACCESSORY_SCRIPT_PATH = (
    "/root/python_testing/scripts/sdk/simulated_accessory.py"
)


class SDKContainerNotRunning(Exception):
    """Raised when we attempt to use the docker container, but it is not running"""


class SDKContainerRetrieveExitCodeError(Exception):
    """Raised when there's an error in the attempt to retrieve an execution's exit
    code"""


class SDKContainer(metaclass=Singleton):
    """
    Base class for the SDK container to be setup and managed.

    Usage:
    Create an instance by calling initializer. When ready to use, ...
    """

    container_name = matter_settings.SDK_CONTAINER_NAME
    image_tag = f"{matter_settings.SDK_DOCKER_IMAGE}:{matter_settings.SDK_DOCKER_TAG}"
    run_parameters = {
        "privileged": True,
        "detach": True,
        "network": "host",
        "name": container_name,
        "command": "tail -f /dev/null",  # while true
        "volumes": {
            "/var/run/dbus/system_bus_socket": {
                "bind": "/var/run/dbus/system_bus_socket",
                "mode": "rw",
            },
            LOCAL_LOGS_PATH: {
                "bind": DOCKER_LOGS_PATH,
                "mode": "rw",
            },
            LOCAL_PAA_CERTS_PATH: {
                "bind": DOCKER_PAA_CERTS_PATH,
                "mode": "ro",
            },
            LOCAL_CREDENTIALS_DEVELOPMENT_PATH: {
                "bind": DOCKER_CREDENTIALS_DEVELOPMENT_PATH,
                "mode": "ro",
            },
            LOCAL_PYTHON_TESTING_PATH: {
                "bind": DOCKER_PYTHON_TESTING_PATH,
                "mode": "rw",
            },
            MAPPED_DATA_MODEL_VOLUME: {
                "bind": DOCKER_DATA_MODEL_PATH,
                "mode": "rw",
            },
            LOCAL_RPC_PYTHON_TESTING_PATH: {
                "bind": DOCKER_RPC_PYTHON_TESTING_PATH,
                "mode": "rw",
            },
            LOCAL_STRESS_TEST_SCRIPT_PATH: {
                "bind": DOCKER_STRESS_TEST_SCRIPT_PATH,
                "mode": "rw",
            },
            LOCAL_STRESS_TEST_ACCESSORY_MANAGER_SCRIPT_PATH: {
                "bind": DOCKER_STRESS_TEST_ACCESSORY_MANAGER_SCRIPT_PATH,
                "mode": "rw",
            },
            LOCAL_STRESS_TEST_SIMULATED_ACCESSORY_SCRIPT_PATH: {
                "bind": DOCKER_STRESS_TEST_SIMULATED_ACCESSORY_SCRIPT_PATH,
                "mode": "rw",
            },
        },
    }

    def __init__(
        self,
        logger: loguru.Logger = logger,
    ) -> None:
        """
        Args:
            logger (Logger, optional): Optional logger injection. Defaults to standard
            self.logger.
        """
        self.__container: Optional[Container] = None

        self.__pics_file_created = False
        self.logger = logger

    @property
    def pics_file_created(self) -> bool:
        return self.__pics_file_created

    def __destroy_existing_container(self) -> None:
        """This will kill and remove any existing container using the same name."""
        existing_container = container_manager.get_container(self.container_name)
        if existing_container is not None:
            logger.info(
                f'Existing container named "{self.container_name}" found. Destroying.'
            )
            container_manager.destroy(existing_container)

    def is_running(self) -> bool:
        if self.__container is None:
            return False
        else:
            return container_manager.is_running(self.__container)

    async def start(self) -> None:
        """Creates the SDK container.

        Returns only when the container is created.
        """

        if self.is_running():
            self.logger.info(
                "SDK container already running, no need to start a new container"
            )
            return

        # Ensure there's no existing container running using the same name.
        self.__destroy_existing_container()

        # Async return when the container is running
        self.__container = await container_manager.create_container(
            self.image_tag, self.run_parameters
        )

        self.logger.info(
            f"{self.container_name} container started"
            f" with configuration: {self.run_parameters}"
        )

    def destroy(self) -> None:
        """Destroy the container."""
        if self.__container is not None:
            container_manager.destroy(self.__container)
        self.__container = None

    def send_command(
        self,
        command: Union[str, list],
        prefix: str,
        is_stream: bool = False,
        is_socket: bool = False,
        is_detach: bool = False,
    ) -> ExecResultExtended:
        if self.__container is None:
            raise SDKContainerNotRunning()

        full_cmd = [prefix]
        if isinstance(command, list):
            full_cmd += command
        else:
            full_cmd.append(str(command))

        self.logger.info("Sending command to SDK container: " + " ".join(full_cmd))

        result = exec_run_in_container(
            self.__container,
            " ".join(full_cmd),
            socket=is_socket,
            stream=is_stream,
            stdin=True,
            detach=is_detach,
        )

        return result

    def exec_exit_code(self, exec_id: str) -> Optional[int]:
        if self.__container is None:
            raise SDKContainerRetrieveExitCodeError(
                "No SDK container, cannot get execution exit code"
            )

        exec_data = self.__container.client.api.exec_inspect(exec_id)

        if exec_data is None:
            raise SDKContainerRetrieveExitCodeError(
                f"Docker didn't return any execution metadata for exec_id {exec_id}"
            )

        return exec_data.get("ExitCode")

    def set_pics(self, pics: PICS) -> None:
        """Sends command to create pics file.

        Args:
            pics (PICS): PICS that contains all the pics codes

        Raises:
            PICSError: If creating PICS file inside the container fails.
        """
        # List of default PICS which needs to set specifically in TH are added here.
        # These PICS are applicable for CI / Chip tool testing purposes only.
        # These PICS are unknown / not visible to external users.

        prefix, cmd = set_pics_command(pics)

        exec_result = self.send_command(cmd, prefix=prefix)

        if exec_result.exit_code != 0:
            raise PICSError("Creating PICS file failed")

        self.__pics_file_created = True

    def reset_pics_state(self) -> None:
        self.__pics_file_created = False
