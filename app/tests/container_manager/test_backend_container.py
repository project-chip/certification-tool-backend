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
from pathlib import Path
from unittest import mock

from app.container_manager.backend_container import (
    backend_container,
    backend_mount_on_host,
)
from app.container_manager.container_manager import container_manager
from app.tests.utils.docker import Container, make_fake_container

DEFAULT_MOUNT_SRC = "/test/path/chip-cert-tool/backend"
DEFAULT_MOUNT_WORKING_DIR = "/app"


def fake_backend_container(
    working_dir: str = DEFAULT_MOUNT_WORKING_DIR,
    mount_src: str = DEFAULT_MOUNT_SRC,
    mount_dst: str = "/app",
) -> Container:
    return make_fake_container(
        attrs={
            "Mounts": [{"Source": mount_src, "Destination": mount_dst}],
            "Config": {
                "WorkingDir": working_dir,
            },
        }
    )


def test_backend_container() -> None:
    with mock.patch.object(container_manager, "get_container") as get_container:
        _ = backend_container()
        get_container.assert_called_once()


def test_backend_mount_on_host() -> None:
    """When backend source folder is mounted directly at `/app`,
    backend_mount_on_host returns backend source folder correctly."""
    with mock.patch(
        "app.container_manager.backend_container.backend_container",
        return_value=fake_backend_container(),
    ):
        path = backend_mount_on_host()
        assert path == Path(DEFAULT_MOUNT_SRC)


def test_backend_mount_on_host_dev_test() -> None:
    """When parent folder to backend source folder is mounted directly at `/app`,
    and workingDir is changed to `/app/backend`,
    backend_mount_on_host returns backend source folder correctly."""
    root_folder = "/test/path/chip-cert-tool/"
    with mock.patch(
        "app.container_manager.backend_container.backend_container",
        return_value=fake_backend_container(
            mount_src=root_folder, working_dir="/app/backend"
        ),
    ):
        path = backend_mount_on_host()
        assert path == Path(root_folder) / "backend"
