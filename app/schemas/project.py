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
from typing import Optional

from pydantic import BaseModel

from .pics import PICS
from .test_environment_config import TestEnvironmentConfig


# Shared properties
class ProjectBase(BaseModel):
    name: Optional[str]
    config: Optional[TestEnvironmentConfig]
    pics: Optional[PICS]


# Properties additional fields on  creation
class ProjectCreate(ProjectBase):
    # Required on new projects
    name: str
    pics: PICS = PICS()
    # Note config is optional, but CRUD will add default config if not set.


# Properties to receive on update (Name and config can be updated)
class ProjectUpdate(ProjectBase):
    pass

    class Config:
        orm_mode = True


# Properties shared by models stored in DB
class ProjectInDBBase(ProjectCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime]

    class Config:
        orm_mode = True


# Properties to return to client
class Project(ProjectInDBBase):
    pass

    class Config:
        orm_mode = True


# Additional Properties properties stored in DB
class ProjectInDB(ProjectInDBBase):
    pass
