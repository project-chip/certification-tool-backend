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
import io
import tarfile
from asyncio import TimeoutError, wait_for
from pathlib import Path
from typing import Dict, Optional

import docker
from docker.errors import DockerException, NotFound
from docker.models.containers import Container

from app.container_manager.docker_shell_commands import (
    SHELL_CMD_LOG_PREFIX,
    docker_cp_from_container_command,
    docker_cp_to_container_command,
    docker_kill_command,
    docker_rm_command,
    docker_run_command,
)
from app.singleton import Singleton
from app.test_engine.logger import test_engine_logger as logger

# Note: Can we use a base docker image and single RPC process(OR a Bash script) entry
# point to later configure the image to be a particular type
container_bring_up_timeout = 5  # Seconds


class ContainerManager(object, metaclass=Singleton):
    def __init__(self) -> None:
        self.__client = docker.from_env()

    async def create_container(
        self, docker_image_tag: str, parameters: Dict = {}
    ) -> Container:
        container = self.__run_new_container(docker_image_tag, parameters)
        await self.__container_ready(container)
        logger.info("Container running for " + docker_image_tag)

        return container

    def destroy(self, container: Container) -> None:
        if self.is_running(container):
            # Log equivalent shell command for kill
            shell_cmd = docker_kill_command(container.name)
            logger.info(f"{SHELL_CMD_LOG_PREFIX}{shell_cmd}")
            container.kill()

        # Log equivalent shell command for remove
        shell_cmd = docker_rm_command(container.name, force=True)
        logger.info(f"{SHELL_CMD_LOG_PREFIX}{shell_cmd}")
        container.remove(force=True)

    def get_container(self, id_or_name: str) -> Optional[Container]:
        try:
            return self.__client.containers.get(id_or_name)
        except NotFound:
            logger.info(f"Did not find container by id or name: {id_or_name}.")
            return None

    def is_running(self, container: Container) -> bool:
        # NOTE: we need to get a new container reference to get updated status.
        if c := self.get_container(container.id):
            return c.status == "running"
        else:
            return False

    def get_working_dir(self, container: Container) -> Optional[str]:
        """Lookup containers WorkingDir from it's config."""
        if config := container.attrs.get("Config"):
            if working_dir := config.get("WorkingDir"):
                return working_dir

        return None

    def get_mount_source_for_destination(
        self, container: Container, destination: str
    ) -> Optional[str]:
        """Find mount source for a mount destination."""
        if mounts := container.attrs.get("Mounts"):
            # Return first mount source with mount destination we're searching for.
            return next(
                (
                    m.get("Source")
                    for m in mounts
                    if m.get("Destination") == destination
                ),
                None,
            )

        return None

    # Internal Methods
    def __run_new_container(self, docker_image_tag: str, parameters: Dict) -> Container:
        # Create containers
        try:
            # Log equivalent shell command
            shell_cmd = docker_run_command(docker_image_tag, parameters)
            logger.info(f"{SHELL_CMD_LOG_PREFIX}{shell_cmd}")

            return self.__client.containers.run(docker_image_tag, **parameters)
        except DockerException as error:
            logger.error(
                "Error occurred while creating a container from image " + str(error)
            )
            raise error

    async def __container_ready(self, container: Container) -> None:
        # Wait for the container for start running
        try:
            await wait_for(
                self.__container_started(container), container_bring_up_timeout
            )
        except TimeoutError as e:
            logger.error(
                f"Container did start timed out in {container_bring_up_timeout}s"
            )
            self.destroy(container)
            raise e

    async def __container_started(self, container: Container) -> None:
        sleep_interval = 0.2

        while True:
            # Check if the container is running, then sleep for 0.1 sec
            if self.is_running(container):
                return

            # Sleep first to give container some time
            await asyncio.sleep(sleep_interval)

    def copy_file_from_container(
        self,
        container: Container,
        container_file_path: Path,
        destination_path: Path,
        destination_file_name: str,
    ) -> None:
        try:
            logger.info(
                "### File Copy: CONTAINER->HOST"
                f" From Container Path: {str(container_file_path)}"
                f" To Host Path: {str(destination_path)}/{destination_file_name}"
                f" Container Name: {str(container.name)}"
            )

            # Log equivalent shell command
            shell_cmd = docker_cp_from_container_command(
                container.name,
                container_file_path,
                destination_path / destination_file_name,
            )
            logger.info(f"{SHELL_CMD_LOG_PREFIX}{shell_cmd}")

            stream, _ = container.get_archive(str(container_file_path))
            with open(
                f"{str(destination_path)}/{destination_file_name}",
                "wb",
            ) as f:
                for d in stream:
                    f.write(d)
        except docker.errors.APIError as e:
            logger.error(f"Error while accessing the Docker API: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

    def copy_file_to_container(
        self,
        container: Container,
        host_file_path: Path,
        destination_container_path: Path,
    ) -> None:
        try:
            logger.info(
                "### File Copy: HOST->CONTAINER"
                f" From Host Path: {str(host_file_path)}"
                f" To Container Path: {destination_container_path}"
                f" Container Name: {str(container.name)}"
            )

            # Log equivalent shell command
            shell_cmd = docker_cp_to_container_command(
                container.name, host_file_path, destination_container_path
            )
            logger.info(f"{SHELL_CMD_LOG_PREFIX}{shell_cmd}")

            tar_stream = io.BytesIO()
            with tarfile.open(f"{host_file_path}", mode="r") as tar_in:
                with tarfile.open(fileobj=tar_stream, mode="w") as tar_out:
                    for member in tar_in.getmembers():
                        # Put the file with the expected name
                        member.name = destination_container_path.name
                        tar_out.addfile(member, tar_in.extractfile(member))

            # Prepare the tar file
            tar_stream.seek(0)
            container.put_archive(f"{destination_container_path.parent}", tar_stream)

        except docker.errors.APIError as e:
            logger.error(f"Error while accessing the Docker API: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise


container_manager: ContainerManager = ContainerManager()
