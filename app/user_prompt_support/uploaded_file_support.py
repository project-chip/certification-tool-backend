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
from abc import abstractmethod
from typing import BinaryIO, Optional, Protocol, runtime_checkable


class UploadFile(Protocol):
    """Protocol to handle file objects uploaded to the backend.

    Attributes:
        file: A tempfile containing the contents of the uploaded file.
        content_type: A str with the content type (MIME type / media type).
        filename: The name of the file.
    """

    file: BinaryIO
    filename: Optional[str]

    @property
    def content_type(self) -> Optional[str]: ...


@runtime_checkable
class UploadedFileSupport(Protocol):
    """Support class required for subclasses that request a file upload from user."""

    @abstractmethod
    def handle_uploaded_file(self, file: UploadFile) -> None:
        pass
