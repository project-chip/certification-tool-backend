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
from test_collections.sdk_tests.support.models.sdk_test_folder import SDKTestFolder
from test_collections.sdk_tests.support.models.th_test_models import THTestType

from .test_case import YamlTestCase
from .test_suite import SuiteType, YamlTestSuite
from .yaml_test_models import YamlTest


class YamlCollectionDeclaration(TestCollectionDeclaration):
    def __init__(self, folder: SDKTestFolder, name: str) -> None:
        super().__init__(path=str(folder.path), name=name)
        self.yaml_version = folder.version


class YamlSuiteDeclaration(TestSuiteDeclaration):
    """Direct initialization for YAML Test Suite."""

    class_ref: Type[YamlTestSuite]

    def __init__(self, name: str, suite_type: SuiteType, version: str) -> None:
        super().__init__(
            YamlTestSuite.class_factory(
                name=name,
                suite_type=suite_type,
                yaml_version=version,
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
    def test_type(self) -> THTestType:
        return self.class_ref.yaml_test.type
