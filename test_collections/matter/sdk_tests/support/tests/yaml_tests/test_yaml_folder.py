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

from ...models.sdk_test_folder import SDKTestFolder

test_yaml_path = Path("/test/yaml")


def test_yaml_folder_version() -> None:
    version_file_content = "yaml_version"

    # We mock open to read version_file_content and Path exists to ignore that we're
    # testing with a fake path
    with mock.patch(
        "test_collections.matter.sdk_tests.support.models.sdk_test_folder.open",
        new=mock.mock_open(read_data=version_file_content),
    ), mock.patch.object(target=Path, attribute="exists", return_value=True) as _:
        yaml_folder = SDKTestFolder(test_yaml_path)

        assert yaml_folder.version == version_file_content


def test_yaml_folder_version_missing() -> None:
    expected_version = "Unknown"
    with mock.patch.object(target=Path, attribute="exists", return_value=False) as _:
        yaml_folder = SDKTestFolder(test_yaml_path)
        assert yaml_folder.version == expected_version


def test_yaml_folder_filename_pattern() -> None:
    """Test SDKTestFolder will search for files with filename pattern."""
    with mock.patch.object(target=Path, attribute="glob") as path_glob:
        # Default file_name_patter: *
        yaml_folder = SDKTestFolder(test_yaml_path)
        _ = yaml_folder.file_paths(extension=".y*ml")
        path_glob.assert_called_once_with("*.y*ml")

        path_glob.reset_mock()
        pattern = "TC_*"
        yaml_folder = SDKTestFolder(test_yaml_path, filename_pattern=pattern)
        _ = yaml_folder.file_paths(extension=".y*ml")
        path_glob.assert_called_once_with(f"{pattern}.y*ml")
