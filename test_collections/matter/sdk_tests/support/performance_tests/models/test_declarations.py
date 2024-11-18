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

from ...models.sdk_test_folder import SDKTestFolder
from .performance_tests_models import MatterTestType, PerformanceTest
from .test_case import PerformanceTestCase
from .test_suite import PerformanceSuiteType, PerformanceTestSuite


class PerformanceCollectionDeclaration(TestCollectionDeclaration):
    def __init__(self, folder: SDKTestFolder, name: str) -> None:
        super().__init__(path=str(folder.path), name=name)
        self.performance_test_version = folder.version


class PerformanceSuiteDeclaration(TestSuiteDeclaration):
    """Direct initialization for Python Test Suite."""

    class_ref: Type[PerformanceTestSuite]

    def __init__(
        self, name: str, suite_type: PerformanceSuiteType, version: str
    ) -> None:
        super().__init__(
            PerformanceTestSuite.class_factory(
                name=name,
                suite_type=suite_type,
                performance_test_version=version,
            )
        )


class PerformanceCaseDeclaration(TestCaseDeclaration):
    """Direct initialization for Python Test Case."""

    class_ref: Type[PerformanceTestCase]

    def __init__(self, test: PerformanceTest, performance_test_version: str) -> None:
        super().__init__(
            PerformanceTestCase.class_factory(
                test=test,
                performance_test_version=performance_test_version,
                mandatory=False,
            )
        )

    @property
    def test_type(self) -> MatterTestType:
        return self.class_ref.performance_test.type
