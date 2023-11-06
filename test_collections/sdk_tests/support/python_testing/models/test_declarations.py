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
from typing import Type

from app.test_engine.models.test_declarations import (
    TestCaseDeclaration,
    TestCollectionDeclaration,
    TestSuiteDeclaration,
)

from .test_case import PythonTestCase
from .test_suite import SuiteType, PythonTestSuite
from .python_test_folder import PythonTestFolder
from .python_test_models import PythonTest, PythonTestType


class PythonCollectionDeclaration(TestCollectionDeclaration):
    def __init__(self, folder: PythonTestFolder, name: str) -> None:
        super().__init__(path=str(folder.path), name=name)
        self.python_test_version = folder.version


class PythonSuiteDeclaration(TestSuiteDeclaration):
    """Direct initialization for Python Test Suite."""

    class_ref: Type[PythonTestSuite]

    def __init__(self, name: str, suite_type: SuiteType, version: str) -> None:
        super().__init__(
            PythonTestSuite.class_factory(
                name=name,
                suite_type=suite_type,
                python_test_version=version,
            )
        )


class PythonCaseDeclaration(TestCaseDeclaration):
    """Direct initialization for Python Test Case."""

    class_ref: Type[PythonTestCase]

    def __init__(self, test: PythonTest, python_test_version: str) -> None:
        super().__init__(
            PythonTestCase.class_factory(test=test, python_test_version=python_test_version)
        )

    @property
    def test_type(self) -> PythonTestType:
        return self.class_ref.python_test.type
