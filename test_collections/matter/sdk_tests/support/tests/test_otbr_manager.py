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

# type: ignore
# Ignore mypy type check for this file

import pytest

from test_collections.matter.sdk_tests.support.otbr_manager.otbr_manager import (
    ThreadBorderRouter,
    ThreadBorderRouterError,
)

# ThreadBorderRouter.__mesh_local_prefix_from_extpanid is name-mangled since it's
# defined as a "private" staticmethod.
_derive = ThreadBorderRouter._ThreadBorderRouter__mesh_local_prefix_from_extpanid


def test_mesh_local_prefix_from_extpanid_is_deterministic() -> None:
    prefix = _derive("5b35dead5b35beef")
    assert prefix == "fd35:dead:5b35:beef::"
    # Calling again with the same extpanid must produce the exact same prefix,
    # unlike OpenThread's own "dataset init new" which randomizes it every call.
    assert _derive("5b35dead5b35beef") == prefix


def test_mesh_local_prefix_from_extpanid_is_a_ula_prefix() -> None:
    # Thread mesh-local prefixes are ULA addresses and must start with 0xfd.
    assert _derive("1111111122222222").startswith("fd")


def test_mesh_local_prefix_from_extpanid_is_case_insensitive() -> None:
    assert _derive("5B35DEAD5B35BEEF") == _derive("5b35dead5b35beef")


def test_mesh_local_prefix_from_extpanid_different_inputs_differ() -> None:
    assert _derive("5b35dead5b35beef") != _derive("1111111122222222")


@pytest.mark.parametrize(
    "invalid_extpanid",
    [
        "",
        "not-hex-at-all!!",
        "5b35dead5b35bee",  # 15 chars, one short
        "5b35dead5b35beefff",  # 18 chars, too long
    ],
)
def test_mesh_local_prefix_from_extpanid_rejects_invalid_input(
    invalid_extpanid: str,
) -> None:
    with pytest.raises(ThreadBorderRouterError):
        _derive(invalid_extpanid)
