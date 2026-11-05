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
from typing import Dict, Optional

from pydantic import BaseModel


class TestMetadata(BaseModel):
    public_id: str
    version: str
    title: str
    description: str
    mandatory: bool = False


class TestCase(BaseModel):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"
    metadata: TestMetadata


class TestSuite(BaseModel):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"
    metadata: TestMetadata
    test_cases: Dict[str, TestCase]


class TestCollection(BaseModel):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"
    name: str
    path: str
    test_suites: Dict[str, TestSuite]


class TestCollections(BaseModel):
    test_collections: Dict[str, TestCollection]


class TestCaseChange(BaseModel):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"
    collection: str
    test_suite: str
    test_case: str


class ScriptError(BaseModel):
    """A test script that could not be parsed or loaded during a rescan."""

    # Path or name of the offending script, when it can be determined. Some
    # failures (e.g. a whole batch failing in the SDK container) are not
    # attributable to a single script.
    script: Optional[str] = None
    reason: str


class RescanChanges(BaseModel):
    """Difference between the test cases known before and after a rescan."""

    added: list[TestCaseChange] = []
    modified: list[TestCaseChange] = []
    removed: list[TestCaseChange] = []
    errors: list[ScriptError] = []
    # Names of all collections present after the rescan, so clients can report
    # the ones that did not change.
    collections: list[str] = []


class RescanTestCollections(TestCollections):
    # Additive on top of the plain TestCollections response, so clients that
    # only read test_collections keep working.
    changes: RescanChanges
