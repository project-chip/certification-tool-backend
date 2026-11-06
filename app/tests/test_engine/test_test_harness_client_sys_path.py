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
"""
Unit tests for the sys.path setup in the SDK container test_harness_client.py.
"""
import importlib.util
import sys
import types
from pathlib import Path
from typing import Iterator
from unittest.mock import MagicMock

import pytest

CLIENT_PATH = (
    Path(__file__).parents[3]
    / "test_collections/matter/sdk_tests/support/python_testing"
    / "models/rpc_client/test_harness_client.py"
)

_STUBBED_MODULES = [
    "matter",
    "matter.testing",
    "matter.testing.CommissioningPreTest",
    "matter.testing.matter_testing",
    "matter.testing.runner",
]


@pytest.fixture
def client_module(monkeypatch: pytest.MonkeyPatch) -> Iterator[types.ModuleType]:
    """Load test_harness_client.py with the SDK's `matter` package stubbed out.

    The client is copied into the SDK container and imports the SDK, which is not
    installed in the backend environment.
    """
    for name in _STUBBED_MODULES:
        monkeypatch.setitem(sys.modules, name, MagicMock())
    spec = importlib.util.spec_from_file_location("th_client_under_test", CLIENT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    yield module


@pytest.fixture
def scripts_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "scripts"
    (root / "custom").mkdir(parents=True)
    (root / "sdk").mkdir()
    monkeypatch.setattr(sys, "path", list(sys.path))
    return root


def _import_fresh(name: str) -> types.ModuleType:
    sys.modules.pop(name, None)
    try:
        return importlib.import_module(name)
    finally:
        sys.modules.pop(name, None)


def test_custom_precedes_sdk_on_sys_path(
    client_module: types.ModuleType, scripts_root: Path
) -> None:
    client_module.configure_sys_path(str(scripts_root))

    paths = sys.path
    assert paths.index(str(scripts_root / "custom")) < paths.index(
        str(scripts_root / "sdk")
    )
    assert str(scripts_root) in paths


def test_custom_helper_shadows_sdk_helper(
    client_module: types.ModuleType, scripts_root: Path
) -> None:
    (scripts_root / "sdk" / "FakeHelper.py").write_text("ORIGIN = 'sdk'\n")
    (scripts_root / "custom" / "FakeHelper.py").write_text("ORIGIN = 'custom'\n")

    client_module.configure_sys_path(str(scripts_root))

    assert _import_fresh("FakeHelper").ORIGIN == "custom"


def test_sdk_helper_still_resolves_without_custom_copy(
    client_module: types.ModuleType, scripts_root: Path
) -> None:
    (scripts_root / "sdk" / "FakeSdkOnlyHelper.py").write_text("ORIGIN = 'sdk'\n")

    client_module.configure_sys_path(str(scripts_root))

    assert _import_fresh("FakeSdkOnlyHelper").ORIGIN == "sdk"


def test_custom_test_script_resolves_custom_helper_via_package_import(
    client_module: types.ModuleType, scripts_root: Path
) -> None:
    """Mirrors run_test(): module is loaded as `custom.TC_X`, helper imported flat."""
    (scripts_root / "sdk" / "FakeBase.py").write_text("ORIGIN = 'sdk'\n")
    (scripts_root / "custom" / "FakeBase.py").write_text("ORIGIN = 'custom'\n")
    (scripts_root / "custom" / "TC_FAKE_1_1.py").write_text(
        "from FakeBase import ORIGIN\n"
    )

    client_module.configure_sys_path(str(scripts_root))

    module = _import_fresh("custom.TC_FAKE_1_1")
    sys.modules.pop("custom", None)
    assert module.ORIGIN == "custom"


def _import_and_keep(name: str) -> types.ModuleType:
    sys.modules.pop(name, None)
    return importlib.import_module(name)


def test_print_custom_overrides_reports_override_and_custom_only(
    client_module: types.ModuleType,
    scripts_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (scripts_root / "sdk" / "FakeOverridden.py").write_text("X = 'sdk'\n")
    (scripts_root / "custom" / "FakeOverridden.py").write_text("X = 'custom'\n")
    (scripts_root / "custom" / "FakeCustomOnly.py").write_text("X = 'custom'\n")
    (scripts_root / "sdk" / "FakeSdkOnly.py").write_text("X = 'sdk'\n")
    client_module.configure_sys_path(str(scripts_root))

    try:
        for name in ("FakeOverridden", "FakeCustomOnly", "FakeSdkOnly"):
            _import_and_keep(name)
        client_module.print_custom_overrides(str(scripts_root))
    finally:
        for name in ("FakeOverridden", "FakeCustomOnly", "FakeSdkOnly"):
            sys.modules.pop(name, None)

    lines = capsys.readouterr().out.splitlines()
    assert lines == [
        "SIDELOAD: FakeCustomOnly loaded from custom/FakeCustomOnly.py "
        "(no sdk/ counterpart)",
        "SIDELOAD: FakeOverridden loaded from custom/FakeOverridden.py, "
        "overriding sdk/FakeOverridden.py",
    ]


def test_print_custom_overrides_is_silent_without_custom_modules(
    client_module: types.ModuleType,
    scripts_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (scripts_root / "sdk" / "FakeSdkOnly.py").write_text("X = 'sdk'\n")
    client_module.configure_sys_path(str(scripts_root))

    try:
        _import_and_keep("FakeSdkOnly")
        client_module.print_custom_overrides(str(scripts_root))
    finally:
        sys.modules.pop("FakeSdkOnly", None)

    assert capsys.readouterr().out == ""


def test_print_custom_overrides_ignores_side_loaded_test_module(
    client_module: types.ModuleType,
    scripts_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (scripts_root / "custom" / "TC_FAKE_1_1.py").write_text("X = 'custom'\n")
    (scripts_root / "sdk" / "TC_FAKE_1_1.py").write_text("X = 'sdk'\n")
    client_module.configure_sys_path(str(scripts_root))

    try:
        _import_and_keep("custom.TC_FAKE_1_1")
        client_module.print_custom_overrides(str(scripts_root))
    finally:
        sys.modules.pop("custom.TC_FAKE_1_1", None)
        sys.modules.pop("custom", None)

    assert capsys.readouterr().out == ""
