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
from datetime import datetime

from pydantic import BaseModel


# Shared properties
class TestCaseMetadataBase(BaseModel):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"
    public_id: str
    title: str
    description: str
    version: str
    source_hash: str
    mandatory: bool = False

    class Config:
        orm_mode = True


# Properties shared by models stored in DB
class TestCaseMetadataInDBBase(TestCaseMetadataBase):
    id: int


# Properties to return to client
class TestCaseMetadata(TestCaseMetadataInDBBase):
    pass


# Additional Properties properties stored in DB
class TestCaseMetadataInDB(TestCaseMetadataInDBBase):
    created_at: datetime
