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

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

import pytest

os.environ.setdefault("SERVER_NAME", "test")
os.environ.setdefault("SERVER_HOST", "http://localhost")
os.environ.setdefault("PROJECT_NAME", "test")
os.environ.setdefault("POSTGRES_SERVER", "localhost")
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault(
    "SQLALCHEMY_DATABASE_URI", "postgresql://postgres:postgres@localhost/test"
)


def _load_otbr_manager() -> ModuleType:
    container_manager_module = ModuleType("app.container_manager")
    container_manager_module.container_manager = mock.MagicMock()
    sys.modules["app.container_manager"] = container_manager_module

    manager_path = (
        Path(__file__).parents[1]
        / "test_collections/matter/sdk_tests/support/otbr_manager/otbr_manager.py"
    )
    spec = importlib.util.spec_from_file_location(
        "otbr_manager_under_test", manager_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


otbr_manager = _load_otbr_manager()
ThreadBorderRouter = otbr_manager.ThreadBorderRouter
ThreadBorderRouterError = otbr_manager.ThreadBorderRouterError


def _border_router() -> ThreadBorderRouter:
    border_router = ThreadBorderRouter()
    border_router._ThreadBorderRouter__dataset = SimpleNamespace(
        channel="15",
        panid="0x1234",
        extpanid="1111111122222222",
        networkkey="00112233445566778899aabbccddeeff",
        networkname="DEMO",
    )
    border_router._ThreadBorderRouter__on_mesh_prefix = "fd11:22::/64"
    return border_router


@pytest.mark.asyncio
async def test_form_thread_topology_restores_and_verifies_active_dataset() -> None:
    expected_dataset = bytes.fromhex("0e0800000000000100000300000f")
    border_router = _border_router()

    with mock.patch.object(
        border_router,
        "_send_command",
        side_effect=lambda command, **_: (
            expected_dataset.hex().upper().encode()
            if command == "dataset active -x"
            else b""
        ),
    ) as send_command, mock.patch.object(
        otbr_manager.asyncio, "sleep", new=mock.AsyncMock()
    ):
        actual_dataset = await border_router.form_thread_topology(expected_dataset)

    assert actual_dataset == expected_dataset
    send_command.assert_any_call(
        f"dataset set active {expected_dataset.hex()}", sensitive=True
    )
    send_command.assert_any_call("dataset active -x", sensitive=True)


@pytest.mark.asyncio
async def test_form_thread_topology_rejects_restored_dataset_mismatch() -> None:
    expected_dataset = bytes.fromhex("0e0800000000000100000300000f")
    border_router = _border_router()

    with mock.patch.object(
        border_router,
        "_send_command",
        side_effect=lambda command, **_: (
            bytes.fromhex("0e0800000000000200000300000f").hex().encode()
            if command == "dataset active -x"
            else b""
        ),
    ), mock.patch.object(otbr_manager.asyncio, "sleep", new=mock.AsyncMock()):
        with pytest.raises(
            ThreadBorderRouterError,
            match="Restored Thread Active Dataset does not match OTBR state",
        ):
            await border_router.form_thread_topology(expected_dataset)


@pytest.mark.asyncio
async def test_form_thread_topology_generates_and_returns_canonical_dataset() -> None:
    active_dataset = bytes.fromhex("0e0800000000000100000300000f")
    border_router = _border_router()

    with mock.patch.object(
        border_router,
        "_send_command",
        side_effect=lambda command, **_: (
            active_dataset.hex().encode() if command == "dataset active -x" else b""
        ),
    ) as send_command, mock.patch.object(
        otbr_manager.asyncio, "sleep", new=mock.AsyncMock()
    ):
        actual_dataset = await border_router.form_thread_topology()

    assert actual_dataset == active_dataset
    send_command.assert_any_call(
        "dataset networkkey 00112233445566778899aabbccddeeff",
        sensitive=True,
    )
    send_command.assert_any_call("dataset active -x", sensitive=True)


def test_sensitive_otbr_command_and_response_are_not_logged() -> None:
    secret = "00112233445566778899aabbccddeeff"
    border_router = _border_router()
    response = SimpleNamespace(output=iter([f"{secret}\r\nDone\r\n".encode()]))
    border_router._ThreadBorderRouter__otbr_docker = SimpleNamespace(
        exec_run=mock.Mock(return_value=response)
    )

    with mock.patch.object(otbr_manager.logger, "debug") as debug:
        output = border_router._send_command(
            f"dataset set active {secret}", sensitive=True
        )

    assert output.decode() == secret
    assert all(secret not in str(call) for call in debug.call_args_list)
