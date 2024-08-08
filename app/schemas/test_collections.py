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


class TestMetadata(BaseModel):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"
    public_id: str
    version: str
    title: str
    description: str
    mandatory: bool = False


class TestCollectionMetadata(BaseModel):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"
    name: str
    version: str
    path: str
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
    metadata: TestCollectionMetadata
    test_suites: Dict[str, TestSuite]


class TestCollections(BaseModel):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"
    test_collections: Dict[str, TestCollection]
