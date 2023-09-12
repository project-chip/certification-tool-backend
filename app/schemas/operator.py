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


class OperatorBase(BaseModel):
    """Base schema for Operator, with shared properties."""

    name: Optional[str]


class OperatorCreate(OperatorBase):
    """Create schema.

    Name is required for new Operators.
    """

    name: str


class OperatorUpdate(OperatorBase):
    """Update Schema.

    Same as the base schema, only name can be changed"""


class OperatorInDBBase(OperatorBase):
    """Base schema for operator in DB.

    Id, and name are required fields.
    """

    id: int
    name: str

    class Config:
        """Configure DB schemas to support parsing from ORM models."""

        orm_mode = True


class Operator(OperatorInDBBase):
    """Default schema, used when return data to API clients"""


class OperatorInDB(OperatorInDBBase):
    """Full database schema.

    Has internal fields for tracking model changes.
    """

    created_at: datetime
    updated_at: datetime


class OperatorToExport(OperatorBase):
    name: str

    class Config:
        """Configure DB schemas to support parsing from ORM models."""

        orm_mode = True
