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
import re

from app.thread_default_identity import generate_thread_default_identity


def test_generate_thread_default_identity_rejects_prohibited_extended_pan_ids() -> None:
    random_values = iter(
        [
            bytes.fromhex("102132435465768798a9bacbdcedfe0f"),
            bytes.fromhex("0000000000000000"),
            bytes.fromhex("ffffffffffffffff"),
            bytes.fromhex("0123456789abcdef"),
            bytes.fromhex("abcd"),
            bytes.fromhex("a1b2c3d4e5"),
        ]
    )
    requested_sizes = []

    def random_bytes(size: int) -> bytes:
        requested_sizes.append(size)
        value = next(random_values)
        assert len(value) == size
        return value

    identity = generate_thread_default_identity(random_bytes)

    assert requested_sizes == [16, 8, 8, 8, 2, 5]
    assert identity["extpanid"] == "0123456789abcdef"
    assert re.fullmatch(r"[0-9a-f]{16}", identity["extpanid"])


def test_generate_thread_default_identity_uses_valid_thread_values() -> None:
    random_values = iter(
        [
            bytes.fromhex("102132435465768798a9bacbdcedfe0f"),
            bytes.fromhex("0123456789abcdef"),
            bytes.fromhex("ffff"),
            bytes.fromhex("abcd"),
            bytes.fromhex("a1b2c3d4e5"),
        ]
    )
    requested_sizes = []

    def random_bytes(size: int) -> bytes:
        requested_sizes.append(size)
        value = next(random_values)
        assert len(value) == size
        return value

    identity = generate_thread_default_identity(random_bytes)

    assert requested_sizes == [16, 8, 2, 2, 5]
    assert identity["networkkey"] == "102132435465768798a9bacbdcedfe0f"
    assert re.fullmatch(r"[0-9a-f]{32}", identity["networkkey"])
    assert identity["extpanid"] == "0123456789abcdef"
    assert re.fullmatch(r"[0-9a-f]{16}", identity["extpanid"])
    assert identity["panid"] == "0xabcd"
    assert 0 <= int(identity["panid"], 16) <= 0xFFFE
    assert identity["networkname"] == "TH-a1b2c3d4e5"
    assert re.fullmatch(r"TH-[0-9a-f]{10}", identity["networkname"])
    assert 1 <= len(identity["networkname"].encode("ascii")) <= 16
