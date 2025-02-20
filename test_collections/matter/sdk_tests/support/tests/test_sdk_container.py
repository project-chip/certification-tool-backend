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

# type: ignore
# Ignore mypy type check for this file

from unittest import mock

import pytest

from app.container_manager import container_manager
from app.tests.conftest import real_sdk_container  # noqa: F401
from app.tests.utils.docker import make_fake_container
from test_collections.matter.config import matter_settings

from ..exec_run_in_container import ExecResultExtended


@pytest.mark.asyncio
async def test_start(real_sdk_container) -> None:  # noqa
    # Values to verify
    docker_image = f"{matter_settings.SDK_DOCKER_IMAGE}:\
{matter_settings.SDK_DOCKER_TAG}"

    with mock.patch.object(
        target=real_sdk_container, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=container_manager, attribute="get_container", return_value=None
    ), mock.patch.object(
        target=container_manager, attribute="create_container"
    ) as mock_create_container:
        await real_sdk_container.start()

    mock_create_container.assert_called_once_with(
        docker_image, real_sdk_container.run_parameters
    )
    assert real_sdk_container._SDKContainer__container is not None

    # clean up:
    real_sdk_container._SDKContainer__container = None


@pytest.mark.asyncio
async def test_not_start_when_running(real_sdk_container) -> None:  # noqa
    with mock.patch.object(
        target=real_sdk_container, attribute="is_running", return_value=True
    ), mock.patch.object(
        target=container_manager, attribute="create_container"
    ) as mock_create_container:
        await real_sdk_container.start()

    mock_create_container.assert_not_called()
    assert real_sdk_container._SDKContainer__container is None


@pytest.mark.asyncio
async def test_destroy_container_running(real_sdk_container) -> None:  # noqa
    with mock.patch.object(
        target=real_sdk_container, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=container_manager, attribute="get_container", return_value=None
    ), mock.patch.object(
        target=container_manager, attribute="destroy"
    ) as mock_destroy, mock.patch.object(
        target=container_manager, attribute="create_container"
    ):
        await real_sdk_container.start()

        assert real_sdk_container._SDKContainer__container is not None

        real_sdk_container.destroy()

    mock_destroy.assert_called()
    assert real_sdk_container._SDKContainer__container is None


@pytest.mark.asyncio
async def test_destroy_container_not_running(real_sdk_container) -> None:  # noqa
    with mock.patch.object(
        target=container_manager, attribute="destroy"
    ) as mock_destroy:
        real_sdk_container.destroy()

    mock_destroy.assert_not_called()
    assert real_sdk_container._SDKContainer__container is None


@pytest.mark.asyncio
async def test_destroy_container_once(real_sdk_container) -> None:  # noqa
    with mock.patch.object(
        target=real_sdk_container, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=container_manager, attribute="get_container", return_value=None
    ), mock.patch.object(
        target=container_manager, attribute="destroy"
    ) as mock_destroy, mock.patch.object(
        target=container_manager,
        attribute="create_container",
        return_value=make_fake_container(),
    ):
        await real_sdk_container.start()

        real_sdk_container.destroy()
        real_sdk_container.destroy()

    mock_destroy.assert_called_once()
    assert real_sdk_container._SDKContainer__container is None


def test_send_command_without_starting(real_sdk_container) -> None:  # noqa
    try:
        real_sdk_container.send_command("--help", prefix="cmd-prefix")
        assert False
    except Exception as e:
        # Not able to check SDKContainerNotRunning type since it's mocked at conftest.py
        assert type(e).__name__ == "SDKContainerNotRunning"
        assert True


@pytest.mark.asyncio
async def test_send_command_default_prefix(real_sdk_container) -> None:  # noqa
    fake_container = make_fake_container()
    cmd = "--help"
    cmd_prefix = "cmd-prefix"
    mock_result = ExecResultExtended(0, "log output".encode(), "ID", mock.MagicMock())

    with mock.patch.object(
        target=real_sdk_container, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=container_manager, attribute="get_container", return_value=None
    ), mock.patch.object(
        target=container_manager,
        attribute="create_container",
        return_value=fake_container,
    ), mock.patch(
        target=(
            "test_collections.matter.sdk_tests.support.sdk_container"
            ".exec_run_in_container"
        ),
        return_value=mock_result,
    ) as mock_exec_run:
        await real_sdk_container.start()

        result = real_sdk_container.send_command(cmd, prefix=cmd_prefix)

    mock_exec_run.assert_called_once_with(
        fake_container,
        f"{cmd_prefix} {cmd}",
        socket=False,
        stream=False,
        stdin=True,
        detach=False,
    )
    assert result == mock_result

    # clean up:
    real_sdk_container._SDKContainer__last_exec_id = None
    real_sdk_container._SDKContainer__container = None


@pytest.mark.asyncio
async def test_send_command_custom_prefix(real_sdk_container) -> None:  # noqa
    fake_container = make_fake_container()
    cmd = "--help"
    cmd_prefix = "cat"
    mock_result = ExecResultExtended(0, "log output".encode(), "ID", mock.MagicMock())

    with mock.patch.object(
        target=real_sdk_container, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=container_manager, attribute="get_container", return_value=None
    ), mock.patch.object(
        target=container_manager,
        attribute="create_container",
        return_value=fake_container,
    ), mock.patch(
        target=(
            "test_collections.matter.sdk_tests.support.sdk_container"
            ".exec_run_in_container"
        ),
        return_value=mock_result,
    ) as mock_exec_run:
        await real_sdk_container.start()

        result = real_sdk_container.send_command(cmd, prefix=cmd_prefix)

    mock_exec_run.assert_called_once_with(
        fake_container,
        f"{cmd_prefix} {cmd}",
        socket=False,
        stream=False,
        stdin=True,
        detach=False,
    )
    assert result == mock_result

    # clean up:
    real_sdk_container._SDKContainer__last_exec_id = None
    real_sdk_container._SDKContainer__container = None
