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
from unittest import mock

from ...yaml_tests.models.test_declarations import (
    YamlCaseDeclaration,
    YamlSuiteDeclaration,
)
from ...yaml_tests.models.test_suite import SuiteType
from ...yaml_tests.models.yaml_test_models import YamlTest


def test_yaml_suite_declaration() -> None:
    name = "TestName"
    type = SuiteType.AUTOMATED
    version = "SomeVersionStr"

    with mock.patch(
        "test_collections.sdk_tests.support.yaml_tests.models."
        "test_suite.YamlTestSuite.class_factory"
    ) as class_factory, mock.patch(
        "app.test_engine.models.test_declarations.TestSuiteDeclaration.__init__"
    ) as declaration_init:
        YamlSuiteDeclaration(name=name, suite_type=type, version=version)
        class_factory.assert_called_once_with(
            name=name, suite_type=type, yaml_version=version
        )
        declaration_init.assert_called_once()


def test_yaml_case_declaration() -> None:
    test = YamlTest(name="TestTest", config={}, tests=[])
    version = "SomeVersionStr"
    with mock.patch(
        "test_collections.sdk_tests.support.yaml_tests.models."
        "test_case.YamlTestCase.class_factory"
    ) as class_factory, mock.patch(
        "app.test_engine.models.test_declarations.TestCaseDeclaration.__init__"
    ) as declaration_init:
        YamlCaseDeclaration(test=test, yaml_version=version)
        class_factory.assert_called_once_with(test=test, yaml_version=version)
        declaration_init.assert_called_once()
