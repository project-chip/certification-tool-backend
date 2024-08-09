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

# Verify if this execution comes from python_tests_validator.
if not os.getenv("DRY_RUN"):
    from typing import Optional

    from app.test_engine.models.test_declarations import TestCollectionDeclaration

    from .sdk_python_tests import (
        custom_python_test_collection,
        sdk_mandatory_python_test_collection,
        sdk_python_test_collection,
    )

    # Test engine will auto load TestCollectionDeclarations declared inside the package
    # initializer
    sdk_python_collection: TestCollectionDeclaration = sdk_python_test_collection()
    sdk_mandatory_python_collection: TestCollectionDeclaration = (
        sdk_mandatory_python_test_collection()
    )

    custom_python_collection: Optional[
        TestCollectionDeclaration
    ] = custom_python_test_collection()
