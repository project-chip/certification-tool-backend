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
from test_collections.sdk_tests.support.models.matter_test_suite import (
    MatterTestSuite,
    SuiteFamilyType,
    SuiteType,
)
from test_collections.sdk_tests.support.models.sdk_test_folder import SDKTestFolder

from ..python_testing.models.python_test_models import PythonTest
from ..python_testing.models.test_case import PythonTestCase
from ..yaml_tests.models.test_case import YamlTestCase
from ..yaml_tests.models.yaml_test_models import YamlTest
from .matter_test_models import MatterTestType


class MatterCollectionDeclaration(TestCollectionDeclaration):
    def __init__(self, folder: SDKTestFolder, name: str) -> None:
        super().__init__(path=str(folder.path), name=name)
        self.version = folder.version


class MatterSuiteDeclaration(TestSuiteDeclaration):
    """Direct initialization for YAML Test Suite."""

    class_ref: Type[MatterTestSuite]

    def __init__(
        self,
        name: str,
        suite_family_type: SuiteFamilyType,
        suite_type: SuiteType,
        version: str,
    ) -> None:
        super().__init__(
            MatterTestSuite.class_factory(
                name=name,
                suite_family_type=suite_family_type,
                suite_type=suite_type,
                version=version,
            )
        )


class YamlCaseDeclaration(TestCaseDeclaration):
    """Direct initialization for YAML Test Case."""

    class_ref: Type[YamlTestCase]

    def __init__(self, test: YamlTest, yaml_version: str) -> None:
        super().__init__(
            YamlTestCase.class_factory(test=test, yaml_version=yaml_version)
        )

    @property
    def test_type(self) -> MatterTestType:
        return self.class_ref.yaml_test.type


class PythonCaseDeclaration(TestCaseDeclaration):
    """Direct initialization for Python Test Case."""

    class_ref: Type[PythonTestCase]

    def __init__(self, test: PythonTest, python_test_version: str) -> None:
        super().__init__(
            PythonTestCase.class_factory(
                test=test, python_test_version=python_test_version
            )
        )

    @property
    def test_type(self) -> MatterTestType:
        return self.class_ref.python_test.type
