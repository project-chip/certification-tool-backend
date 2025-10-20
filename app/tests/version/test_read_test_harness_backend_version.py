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
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from app import utils_db
from app.version import (
    _get_matter_settings,
    read_matter_sdk_docker_tag,
    read_matter_sdk_sha,
    read_test_harness_backend_version,
)


@pytest.mark.serial
def test_read_test_harness_backend_version() -> None:
    expected_db_revision = "aabbccdd"  # spell-checker:disable-line
    expected_version_value = "v0.99"
    expected_sha_value = "0fb2dd9"

    # Create temporary files instead of modifying real files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        version_file_path = temp_dir_path / "version.txt"
        sha_file_path = temp_dir_path / "sha.txt"

        version_file_path.write_text(expected_version_value)
        sha_file_path.write_text(expected_sha_value)

        with mock.patch("app.version.VERSION_FILEPATH", version_file_path), mock.patch(
            "app.version.SHA_FILEPATH", sha_file_path
        ), mock.patch.object(
            target=utils_db,
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
            matter_sdk_docker_tag = read_matter_sdk_docker_tag()
            if matter_sdk_docker_tag is not None:
                assert backend_version.sdk_docker_tag == matter_sdk_docker_tag

        mock_utils.assert_called_once()


@pytest.mark.serial
def test_read_test_harness_backend_version_with_empty_files() -> None:
    expected_version_value = "Unknown"
    expected_sha_value = "Unknown"
    expected_db_revision = "aabbccdd"  # spell-checker:disable-line

    # Create temporary empty files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        version_file_path = temp_dir_path / "version.txt"
        sha_file_path = temp_dir_path / "sha.txt"

        version_file_path.write_text("")
        sha_file_path.write_text("")

        with mock.patch("app.version.VERSION_FILEPATH", version_file_path), mock.patch(
            "app.version.SHA_FILEPATH", sha_file_path
        ), mock.patch.object(
            target=utils_db,
            attribute="get_db_revision",
            return_value=expected_db_revision,
        ):
            backend_version = read_test_harness_backend_version()
            assert backend_version.version == expected_version_value
            assert backend_version.sha == expected_sha_value
            assert backend_version.db_revision == expected_db_revision
            matter_sdk_sha = read_matter_sdk_sha()
            if matter_sdk_sha is not None:
                assert backend_version.sdk_sha == matter_sdk_sha
            matter_sdk_docker_tag = read_matter_sdk_docker_tag()
            if matter_sdk_docker_tag is not None:
                assert backend_version.sdk_docker_tag == matter_sdk_docker_tag


@pytest.mark.serial
def test_read_test_harness_backend_version_with_missing_files() -> None:
    expected_version_value = "Unknown"
    expected_sha_value = "Unknown"
    expected_db_revision = "aabbccdd"  # spell-checker:disable-line

    # Create temporary file paths that don't exist
    with tempfile.TemporaryDirectory() as temp_dir:
        nonexistent_version_file = Path(temp_dir) / "nonexistent_version"
        nonexistent_sha_file = Path(temp_dir) / "nonexistent_sha"

        # Mock the file paths to use our non-existent files
        with mock.patch(
            "app.version.VERSION_FILEPATH", nonexistent_version_file
        ), mock.patch(
            "app.version.SHA_FILEPATH", nonexistent_sha_file
        ), mock.patch.object(
            target=utils_db,
            attribute="get_db_revision",
            return_value=expected_db_revision,
        ):
            backend_version = read_test_harness_backend_version()
            assert backend_version.version == expected_version_value
            assert backend_version.sha == expected_sha_value
            assert backend_version.db_revision == expected_db_revision
            matter_sdk_sha = read_matter_sdk_sha()
            if matter_sdk_sha is not None:
                assert backend_version.sdk_sha == matter_sdk_sha
            matter_sdk_docker_tag = read_matter_sdk_docker_tag()
            if matter_sdk_docker_tag is not None:
                assert backend_version.sdk_docker_tag == matter_sdk_docker_tag


@pytest.mark.serial
def test_get_matter_settings() -> None:
    """Test _get_matter_settings returns matter_settings when module exists."""
    matter_settings = _get_matter_settings()
    if matter_settings is not None:
        # If the module is available, verify it has the expected attributes
        assert hasattr(matter_settings, "SDK_SHA")
        assert hasattr(matter_settings, "SDK_DOCKER_TAG")


@pytest.mark.serial
def test_read_matter_sdk_sha() -> None:
    """Test read_matter_sdk_sha returns shortened SHA."""
    sdk_sha = read_matter_sdk_sha()
    if sdk_sha is not None:
        # SHA should be shortened to 7 characters
        assert len(sdk_sha) == 7
        # Verify it matches the expected format
        assert isinstance(sdk_sha, str)


@pytest.mark.serial
def test_read_matter_sdk_docker_tag() -> None:
    """Test read_matter_sdk_docker_tag returns docker tag."""
    sdk_docker_tag = read_matter_sdk_docker_tag()
    if sdk_docker_tag is not None:
        # Docker tag should be a non-empty string
        assert isinstance(sdk_docker_tag, str)
        assert len(sdk_docker_tag) > 0


@pytest.mark.serial
def test_read_matter_sdk_sha_and_docker_tag_consistency() -> None:
    """Test that SDK SHA and Docker Tag are both available or both None."""
    sdk_sha = read_matter_sdk_sha()
    sdk_docker_tag = read_matter_sdk_docker_tag()

    # Both should be None or both should have values
    # (they come from the same module)
    assert (sdk_sha is None) == (sdk_docker_tag is None)
