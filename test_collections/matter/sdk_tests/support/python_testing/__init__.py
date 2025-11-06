#
# Copyright (c) 2025 Project CHIP Authors
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
from typing import TYPE_CHECKING

if TYPE_CHECKING or not os.getenv("DRY_RUN"):
    from app.test_engine.models.test_declarations import TestCollectionDeclaration

# Global variables to hold test collections (initialized later during startup)
sdk_python_collection: "TestCollectionDeclaration | None" = None
sdk_mandatory_python_collection: "TestCollectionDeclaration | None" = None
custom_python_collection: "TestCollectionDeclaration | None" = None

# Import initialization functions only in non-DRY_RUN mode
if not os.getenv("DRY_RUN"):
    from .test_manager import initialize_python_tests, initialize_python_tests_sync

__all__ = [
    "sdk_python_collection",
    "sdk_mandatory_python_collection",
    "custom_python_collection",
    "initialize_python_tests",
    "initialize_python_tests_sync",
]
