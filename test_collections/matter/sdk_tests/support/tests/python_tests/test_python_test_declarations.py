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
# flake8: noqa
# Ignore flake8 check for this file
from unittest import mock

from ...python_testing.models.python_test_models import PythonTest, PythonTestType
from ...python_testing.models.test_declarations import (
    PythonCaseDeclaration,
    PythonSuiteDeclaration,
)
from ...python_testing.models.test_suite import SuiteType


def test_python_suite_declaration() -> None:
    name = "TestName"
    type = SuiteType.COMMISSIONING
    version = "SomeVersionStr"

    with mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite.PythonTestSuite.class_factory"
    ) as class_factory, mock.patch(
        "app.test_engine.models.test_declarations.TestSuiteDeclaration.__init__"
    ) as declaration_init:
        PythonSuiteDeclaration(name=name, suite_type=type, version=version)
        class_factory.assert_called_once_with(
            name=name, suite_type=type, python_test_version=version, mandatory=False
        )
        declaration_init.assert_called_once()


def test_python_case_declaration() -> None:
    test = PythonTest(
        name="TestTest",
        description="TestTest description",
        config={},
        steps=[],
        class_name="TC_TestTest",
        python_test_type=PythonTestType.COMMISSIONING,
        mandatory=True,
    )
    version = "SomeVersionStr"
    with mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_case.PythonTestCase.class_factory"
    ) as class_factory, mock.patch(
        "app.test_engine.models.test_declarations.TestCaseDeclaration.__init__"
    ) as declaration_init:
        PythonCaseDeclaration(test=test, python_test_version=version, mandatory=True)
        class_factory.assert_called_once_with(
            test=test, python_test_version=version, mandatory=True
        )
        declaration_init.assert_called_once()
