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
from typing import Dict

from pydantic import BaseModel

# {<TestCase.public_id>:iterations}
TestCaseSelection = Dict[str, int]
# {<TestSuite.public_id>:selected_test_cases}
TestSuiteSelection = Dict[str, TestCaseSelection]
# {<TestCollection.name>:selected_test_suites}
TestSelection = Dict[str, TestSuiteSelection]


class SelectedTestCase(BaseModel):
    public_id: str
    iterations: int = 1


class SelectedTestSuite(BaseModel):
    public_id: str
    test_cases: list[SelectedTestCase] = []


class SelectedCollection(BaseModel):
    collection_name: str
    test_suites: list[SelectedTestSuite] = []


class SelectedTests(BaseModel):
    collections: list[SelectedCollection] = []
