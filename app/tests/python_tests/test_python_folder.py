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

from test_collections.sdk_tests.support.python_testing.models.python_test_folder import (
    PythonTestFolder,
)

test_python_path = Path("/test/python")


def test_python_folder_version() -> None:
    version_file_content = "python_test_version"

    # We mock open to read version_file_content and Path exists to ignore that we're
    # testing with a fake path
    with mock.patch(
        "test_collections.sdk_tests.support.python_testing.models.python_test_folder.open",
        new=mock.mock_open(read_data=version_file_content),
    ), mock.patch.object(target=Path, attribute="exists", return_value=True) as _:
        python_test_folder = PythonTestFolder(test_python_path)

        assert python_test_folder.version == version_file_content


def test_python_folder_version_missing() -> None:
    expected_version = "Unknown"
    with mock.patch.object(target=Path, attribute="exists", return_value=False) as _:
        python_folder = PythonTestFolder(test_python_path)
        assert python_folder.version == expected_version


def test_python_folder_filename_pattern() -> None:
    """Test PythonTestFolder will search for files with filename pattern."""
    with mock.patch.object(target=Path, attribute="glob") as path_glob:
        # Default file_name_patter: *
        python_folder = PythonTestFolder(test_python_path)
        _ = python_folder.python_file_paths()
        path_glob.assert_called_once_with("*.py")

        path_glob.reset_mock()
        pattern = "TC_*"
        python_test_folder = PythonTestFolder(
            test_python_path, filename_pattern=pattern
        )
        _ = python_test_folder.python_file_paths()
        path_glob.assert_called_once_with(f"{pattern}.py")
