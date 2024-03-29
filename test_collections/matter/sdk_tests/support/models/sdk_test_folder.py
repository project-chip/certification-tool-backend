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

from ..paths import SDK_CHECKOUT_PATH

UNKNOWN_version = "Unknown"
VERSION_FILE_FILENAME = ".version"


class SDKTestFolder:
    """Representing a folder with SDK Test files.

    Note: SDK version is read from .version file in folder on init.
    """

    def __init__(self, path: Path, filename_pattern: str = "*") -> None:
        self.path = path
        self.filename_pattern = filename_pattern
        self.version = self.__version()

    def __version(self) -> str:
        """Read version string from .version file in
        /app/backend/test_collections/matter/sdk_tests/sdk_checkout path."""
        version_file_path = SDK_CHECKOUT_PATH / VERSION_FILE_FILENAME

        if not version_file_path.exists():
            return UNKNOWN_version
        else:
            with open(version_file_path, "r") as file:
                return file.read().rstrip()

    def file_paths(self, extension: str = "*.*") -> list[Path]:
        """Get list of paths in folder.

        Filename filter can be applied if only some files should be selected.

        Args:
            extension (str): custom file extension filter. Defaults to "*.*".

        Returns:
            list[Path]: list of paths to test files.
        """
        return list(self.path.glob(self.filename_pattern + extension))
