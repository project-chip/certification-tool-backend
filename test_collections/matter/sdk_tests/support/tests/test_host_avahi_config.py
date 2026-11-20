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
import os
from pathlib import Path
from typing import Optional

import pytest

from .. import host_avahi_config
from ..host_avahi_config import avahi_excluded_interfaces, avahi_restart_pending

DONGLE = "wlx9cefd5f95289"


def write_conf(tmp_path: Path, server_lines: str) -> Path:
    conf = tmp_path / "avahi-daemon.conf"
    conf.write_text(
        "# comment\n"
        "[server]\n"
        "use-ipv4=yes\n"
        f"{server_lines}"
        "\n[publish]\n"
        "publish-hinfo=no\n"
    )
    return conf


@pytest.mark.parametrize(
    "server_lines, expected",
    [
        ("", []),
        ("#allow-interfaces=eth0\n", []),
        (f"allow-interfaces=eth0,wlan0,{DONGLE},wpan0\n", []),
        (f"allow-interfaces=eth0, {DONGLE}\t,wpan0\n", []),
        (f"allow-interfaces=eth0,{DONGLE.upper()}\n", []),
        ("allow-interfaces=\n", [DONGLE]),
        ("allow-interfaces=eth0,wlan0,wpan0\n", [DONGLE]),
        (f"deny-interfaces={DONGLE}\n", [DONGLE]),
        (f"deny-interfaces={DONGLE.upper()}\n", [DONGLE]),
        (f"allow-interfaces={DONGLE}\ndeny-interfaces={DONGLE}\n", [DONGLE]),
    ],
)
def test_avahi_excluded_interfaces(
    tmp_path: Path, server_lines: str, expected: list
) -> None:
    conf = write_conf(tmp_path, server_lines)
    assert avahi_excluded_interfaces([DONGLE], conf) == expected


def test_avahi_excluded_interfaces_reports_only_excluded(tmp_path: Path) -> None:
    conf = write_conf(tmp_path, "allow-interfaces=eth0,wlan1\n")
    assert avahi_excluded_interfaces(["wlan1", DONGLE], conf) == [DONGLE]


def test_avahi_excluded_interfaces_missing_conf(tmp_path: Path) -> None:
    assert avahi_excluded_interfaces([DONGLE], tmp_path / "missing.conf") == []


def test_avahi_excluded_interfaces_no_server_section(tmp_path: Path) -> None:
    conf = tmp_path / "avahi-daemon.conf"
    conf.write_text("[publish]\npublish-hinfo=no\n")
    assert avahi_excluded_interfaces([DONGLE], conf) == []


def set_conf_mtime(conf: Path, usec: int) -> None:
    os.utime(conf, ns=(usec * 1000, usec * 1000))


@pytest.mark.parametrize(
    "started_usec, expected",
    [
        (None, False),
        (1_000_000, True),
        (2_000_000, False),
        (3_000_000, False),
    ],
)
def test_avahi_restart_pending(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    started_usec: Optional[int],
    expected: bool,
) -> None:
    conf = write_conf(tmp_path, "")
    set_conf_mtime(conf, 2_000_000)
    monkeypatch.setattr(host_avahi_config, "__avahi_started_usec", lambda: started_usec)
    assert avahi_restart_pending(conf) == expected


def test_avahi_restart_pending_missing_conf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(host_avahi_config, "__avahi_started_usec", lambda: 0)
    assert not avahi_restart_pending(tmp_path / "missing.conf")
