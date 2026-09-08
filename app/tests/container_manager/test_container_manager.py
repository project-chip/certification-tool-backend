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
import importlib
from asyncio import TimeoutError as AsyncioTimeoutError
from pathlib import Path
from unittest import mock

import pytest
from docker.errors import NotFound

from app.container_manager.container_manager import (
    container_manager,
    resolve_container_logs_enabled,
)
from app.core.config import settings
from app.tests.utils.docker import FAKE_ID, Container, make_fake_container

# `app/container_manager/__init__.py` does `from .container_manager import
# container_manager`, which shadows the submodule name with the singleton
# instance in the package's own namespace. That means any attribute-chain
# resolution of "app.container_manager.container_manager" (whether via a
# mock.patch string, or via `import app.container_manager.container_manager as
# x`, which also resolves by attribute traversal) lands on the *instance*, not
# the module. importlib.import_module() does a genuine sys.modules lookup
# instead, so it reliably returns the actual module object.
container_manager_module = importlib.import_module(
    "app.container_manager.container_manager"
)

DEFAULT_MOUNT_SRC = "/test/path/chip-cert-tool/backend"
DEFAULT_MOUNT_WORKING_DIR = "/app"


def test_resolve_container_logs_enabled_explicit_true_wins() -> None:
    with mock.patch.object(settings, "ENABLE_CONTAINER_LOGS", False):
        assert resolve_container_logs_enabled(True) is True


def test_resolve_container_logs_enabled_explicit_false_wins() -> None:
    with mock.patch.object(settings, "ENABLE_CONTAINER_LOGS", True):
        assert resolve_container_logs_enabled(False) is False


def test_resolve_container_logs_enabled_defers_to_settings_when_none() -> None:
    with mock.patch.object(settings, "ENABLE_CONTAINER_LOGS", True):
        assert resolve_container_logs_enabled(None) is True

    with mock.patch.object(settings, "ENABLE_CONTAINER_LOGS", False):
        assert resolve_container_logs_enabled(None) is False


@pytest.mark.asyncio
async def test_create_container_logs_shell_commands_when_enabled() -> None:
    with mock.patch(
        "docker.models.containers.ContainerCollection.run"
    ), mock.patch.object(
        container_manager, "is_running", return_value=True
    ), mock.patch.object(
        container_manager_module, "logger"
    ) as mock_logger:
        await container_manager.create_container(
            docker_image_tag="org/image:tag", enable_container_logs=True
        )

    # One log line for the equivalent "docker run" command, one for "Container
    # running for ...".
    assert mock_logger.info.call_count == 2


@pytest.mark.asyncio
async def test_create_container_no_logs_when_disabled() -> None:
    with mock.patch(
        "docker.models.containers.ContainerCollection.run"
    ), mock.patch.object(
        container_manager, "is_running", return_value=True
    ), mock.patch.object(
        container_manager_module, "logger"
    ) as mock_logger:
        await container_manager.create_container(
            docker_image_tag="org/image:tag", enable_container_logs=False
        )

    mock_logger.info.assert_not_called()


@pytest.mark.asyncio
async def test_create_container() -> None:
    with mock.patch(
        "docker.models.containers.ContainerCollection.run"
    ) as docker_run, mock.patch(
        "app.container_manager.container_manager.is_running",
        return_value=True,
    ):
        await container_manager.create_container(docker_image_tag="org/image:tag")
        docker_run.assert_called_once()


@pytest.mark.asyncio
async def test_create_container_timeout() -> None:
    with mock.patch("docker.models.containers.ContainerCollection.run"), mock.patch(
        "app.container_manager.container_manager.is_running",
        return_value=False,
    ):
        with pytest.raises(AsyncioTimeoutError):
            await container_manager.create_container(docker_image_tag="org/image:tag")


def test_get_container_found() -> None:
    with mock.patch(
        "docker.models.containers.ContainerCollection.get",
        return_value=make_fake_container(),
    ):
        container = container_manager.get_container("test_name")
        assert container is not None


def test_get_container_not_found() -> None:
    with mock.patch(
        "docker.models.containers.ContainerCollection.get",
        side_effect=NotFound("Fake container not found error"),
    ):
        container = container_manager.get_container("test_name")
        assert container is None


def test_container_is_running() -> None:
    with mock.patch(
        "app.container_manager.container_manager.get_container",
        return_value=make_fake_container({"State": {"Status": "running"}}),
    ):
        assert container_manager.is_running(Container()) is True


def test_container_is_not_running() -> None:
    with mock.patch(
        "app.container_manager.container_manager.get_container",
        return_value=make_fake_container({"State": {"Status": "stopped"}}),
    ):
        assert container_manager.is_running(Container()) is False


def test_destroy_kills_by_default() -> None:
    container = make_fake_container({"Id": FAKE_ID, "State": {"Status": "running"}})
    with mock.patch.object(container, "kill") as kill, mock.patch.object(
        container, "stop"
    ) as stop, mock.patch.object(container, "remove") as remove, mock.patch(
        "app.container_manager.container_manager.get_container",
        return_value=container,
    ):
        container_manager.destroy(container)
        kill.assert_called_once()
        stop.assert_not_called()
        remove.assert_called_once_with(force=True)


def test_destroy_graceful_stops_instead_of_kill() -> None:
    container = make_fake_container({"Id": FAKE_ID, "State": {"Status": "running"}})
    with mock.patch.object(container, "kill") as kill, mock.patch.object(
        container, "stop"
    ) as stop, mock.patch.object(container, "remove") as remove, mock.patch(
        "app.container_manager.container_manager.get_container",
        return_value=container,
    ):
        container_manager.destroy(container, graceful=True)
        stop.assert_called_once()
        kill.assert_not_called()
        remove.assert_called_once_with(force=True)


def test_destroy_graceful_falls_back_to_kill_on_stop_failure() -> None:
    from docker.errors import APIError

    container = make_fake_container({"Id": FAKE_ID, "State": {"Status": "running"}})
    with mock.patch.object(
        container, "stop", side_effect=APIError("stop failed")
    ), mock.patch.object(container, "kill") as kill, mock.patch.object(
        container, "remove"
    ) as remove, mock.patch(
        "app.container_manager.container_manager.get_container",
        return_value=container,
    ):
        container_manager.destroy(container, graceful=True)
        kill.assert_called_once()
        remove.assert_called_once_with(force=True)


def test_destroy_logs_shell_commands_when_enabled() -> None:
    container = make_fake_container({"Id": FAKE_ID, "State": {"Status": "running"}})
    with mock.patch.object(container, "kill"), mock.patch.object(
        container, "remove"
    ), mock.patch(
        "app.container_manager.container_manager.get_container",
        return_value=container,
    ), mock.patch.object(
        container_manager_module, "logger"
    ) as mock_logger:
        container_manager.destroy(container, enable_container_logs=True)

    # One log line for the "docker kill" command, one for "docker rm".
    assert mock_logger.info.call_count == 2


def test_destroy_no_logs_when_disabled() -> None:
    container = make_fake_container({"Id": FAKE_ID, "State": {"Status": "running"}})
    with mock.patch.object(container, "kill"), mock.patch.object(
        container, "remove"
    ), mock.patch(
        "app.container_manager.container_manager.get_container",
        return_value=container,
    ), mock.patch.object(
        container_manager_module, "logger"
    ) as mock_logger:
        container_manager.destroy(container, enable_container_logs=False)

    mock_logger.info.assert_not_called()


def test_remove_containers_for_image_removes_stale_containers() -> None:
    stale_container = make_fake_container(
        {"Id": FAKE_ID, "State": {"Status": "running"}}
    )
    with mock.patch.object(stale_container, "stop") as stop, mock.patch.object(
        stale_container, "remove"
    ) as remove, mock.patch(
        "docker.models.containers.ContainerCollection.list",
        return_value=[stale_container],
    ), mock.patch(
        "app.container_manager.container_manager.get_container",
        return_value=stale_container,
    ):
        container_manager.remove_containers_for_image("org/image:tag")
        # remove_containers_for_image always destroys gracefully.
        stop.assert_called_once()
        remove.assert_called_once_with(force=True)


def test_remove_containers_for_image_no_stale_containers() -> None:
    with mock.patch(
        "docker.models.containers.ContainerCollection.list",
        return_value=[],
    ):
        # Should simply do nothing when there is nothing to clean up.
        container_manager.remove_containers_for_image("org/image:tag")


def test_get_working_dir() -> None:
    working_dir = "/test"
    container = make_fake_container({"Config": {"WorkingDir": working_dir}})
    assert container_manager.get_working_dir(container) == working_dir


def test_get_working_dir_none() -> None:
    container = make_fake_container({"Config": {}})
    assert container_manager.get_working_dir(container) is None

    container = make_fake_container()
    assert container_manager.get_working_dir(container) is None


def test_get_mount_source_for_destination() -> None:
    test_source = "/host/path"
    test_dest = "/container/path"
    container = make_fake_container(
        attrs={
            "Mounts": [{"Source": test_source, "Destination": test_dest}],
        }
    )
    # Test existing mount destination
    src = container_manager.get_mount_source_for_destination(
        container, destination=test_dest
    )
    assert src == test_source

    # Test missing mount destination
    src = container_manager.get_mount_source_for_destination(
        container, destination="/missing/dest"
    )
    assert src is None


def test_get_mount_source_for_destination_no_mount() -> None:
    src = container_manager.get_mount_source_for_destination(
        make_fake_container(), destination="/some/path"
    )
    assert src is None


def test_get_mount_source_for_destination_invalid_attrs() -> None:
    test_dest = "/container/path"
    container = make_fake_container(
        attrs={
            "Mounts": [{"No-Source": None, "Destination": test_dest}],
        }
    )

    src = container_manager.get_mount_source_for_destination(
        container, destination=test_dest
    )
    assert src is None


def test_copy_file_from_container_logs_when_enabled(tmp_path: Path) -> None:
    container = make_fake_container({"Id": FAKE_ID, "Name": "test-container"})
    with mock.patch.object(
        container, "get_archive", return_value=(iter([b"data"]), {})
    ), mock.patch.object(container_manager_module, "logger") as mock_logger:
        container_manager.copy_file_from_container(
            container=container,
            container_file_path=Path("/some/path"),
            destination_path=tmp_path,
            destination_file_name="out.txt",
            enable_container_logs=True,
        )

    # One log line for the "### File Copy" message, one for the equivalent
    # "docker cp" command.
    assert mock_logger.info.call_count == 2
    assert (tmp_path / "out.txt").read_bytes() == b"data"


def test_copy_file_from_container_no_logs_when_disabled(tmp_path: Path) -> None:
    container = make_fake_container({"Id": FAKE_ID, "Name": "test-container"})
    with mock.patch.object(
        container, "get_archive", return_value=(iter([b"data"]), {})
    ), mock.patch.object(container_manager_module, "logger") as mock_logger:
        container_manager.copy_file_from_container(
            container=container,
            container_file_path=Path("/some/path"),
            destination_path=tmp_path,
            destination_file_name="out.txt",
            enable_container_logs=False,
        )

    mock_logger.info.assert_not_called()


def test_copy_file_to_container_logs_when_enabled(tmp_path: Path) -> None:
    import io
    import tarfile

    host_file = tmp_path / "source.tar"
    content = b"hello"
    with tarfile.open(host_file, "w") as tar:
        info = tarfile.TarInfo(name="file.txt")
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))

    container = make_fake_container({"Id": FAKE_ID, "Name": "test-container"})
    with mock.patch.object(container, "put_archive"), mock.patch.object(
        container_manager_module, "logger"
    ) as mock_logger:
        container_manager.copy_file_to_container(
            container=container,
            host_file_path=host_file,
            destination_container_path=Path("/dest/file.txt"),
            enable_container_logs=True,
        )

    # One log line for the "### File Copy" message, one for the equivalent
    # "docker cp" command.
    assert mock_logger.info.call_count == 2


def test_copy_file_to_container_no_logs_when_disabled(tmp_path: Path) -> None:
    import io
    import tarfile

    host_file = tmp_path / "source.tar"
    content = b"hello"
    with tarfile.open(host_file, "w") as tar:
        info = tarfile.TarInfo(name="file.txt")
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))

    container = make_fake_container({"Id": FAKE_ID, "Name": "test-container"})
    with mock.patch.object(container, "put_archive"), mock.patch.object(
        container_manager_module, "logger"
    ) as mock_logger:
        container_manager.copy_file_to_container(
            container=container,
            host_file_path=host_file,
            destination_container_path=Path("/dest/file.txt"),
            enable_container_logs=False,
        )

    mock_logger.info.assert_not_called()
