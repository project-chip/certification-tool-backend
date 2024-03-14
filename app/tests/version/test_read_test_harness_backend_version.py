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
import os
from pathlib import Path
from unittest import mock

import pytest

from app import utils
from app.version import (
    SHA_FILEPATH,
    VERSION_FILEPATH,
    read_test_harness_backend_version,
    read_matter_sdk_sha,
)


def _write_contents_to_file(filepath: Path, contents: str) -> None:
    f = open(filepath, "w")
    f.write(contents)
    f.close()


def _remove_file(filepath: Path) -> None:
    if os.path.exists(path=filepath):
        os.remove(path=filepath)


@pytest.mark.serial
def test_read_test_harness_backend_version() -> None:
    expected_db_revision = "aabbccdd"  # spell-checker:disable-line
    expected_version_value = "v0.99"
    expected_sha_value = "0fb2dd9"

    _write_contents_to_file(VERSION_FILEPATH, expected_version_value)
    _write_contents_to_file(SHA_FILEPATH, expected_sha_value)

    with mock.patch.object(
        target=utils,
        attribute="get_db_revision",
        return_value=expected_db_revision,
    ) as mock_utils:
        backend_version = read_test_harness_backend_version()
        assert backend_version.version == expected_version_value
        assert backend_version.sha == expected_sha_value
        assert backend_version.db_revision == expected_db_revision
        matter_sdk_sha = read_matter_sdk_sha()
        if matter_sdk_sha is not None:
            assert backend_version.sdk_sha == matter_sdk_sha

    mock_utils.assert_called_once()


@pytest.mark.serial
def test_read_test_harness_backend_version_with_empty_files() -> None:
    expected_version_value = "Unknown"
    expected_sha_value = "Unknown"

    _write_contents_to_file(VERSION_FILEPATH, "")
    _write_contents_to_file(SHA_FILEPATH, "")

    backend_version = read_test_harness_backend_version()
    assert backend_version.version == expected_version_value
    assert backend_version.sha == expected_sha_value
    matter_sdk_sha = read_matter_sdk_sha()
    if matter_sdk_sha is not None:
        assert backend_version.sdk_sha == matter_sdk_sha


@pytest.mark.serial
def test_read_test_harness_backend_version_with_missing_files() -> None:
    expected_version_value = "Unknown"
    expected_sha_value = "Unknown"

    # Remove files if it exists
    _remove_file(filepath=VERSION_FILEPATH)
    _remove_file(filepath=SHA_FILEPATH)

    backend_version = read_test_harness_backend_version()
    assert backend_version.version == expected_version_value
    assert backend_version.sha == expected_sha_value
    matter_sdk_sha = read_matter_sdk_sha()
    if matter_sdk_sha is not None:
        assert backend_version.sdk_sha == matter_sdk_sha
