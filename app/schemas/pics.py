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
from pydantic import BaseModel


class PICSItem(BaseModel):
    number: str
    enabled: bool


class PICSCluster(BaseModel):
    name: str
    items: dict[str, PICSItem] = {}

    def enabled_items(self) -> list[PICSItem]:
        return list([item for item in self.items.values() if item.enabled])


class PICS(BaseModel):
    clusters: dict[str, PICSCluster] = {}

    def all_enabled_items(self) -> list[PICSItem]:
        # flatten all enabled items for all clusters
        return sum([c.enabled_items() for c in self.clusters.values()], [])


class PICSApplicableTestCases(BaseModel):
    test_cases: list[str]


class PICSError(Exception):
    """Raised when an error occurs during execution."""
