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
# import sqlalchemy as JSONB
from typing import Any, Optional, Type

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, parse_obj_as
from sqlalchemy.types import JSON, TypeDecorator


class PydanticBaseType(TypeDecorator):
    """Pydantic type.
    SAVING:
    - Uses SQLAlchemy JSON type under the hood.
    - Accepts the pydantic model and converts it to a dict on save.
    - SQLAlchemy engine JSON-encodes the dict to a string.
    RETRIEVING:
    - Pulls the string from the database.
    - SQLAlchemy engine JSON-decodes the string to a dict.
    - Uses the dict to create a pydantic model.
    """

    impl = JSON

    def __init__(self, pydantic_type: Type[BaseModel]):
        super().__init__()
        self.pydantic_type = pydantic_type

    def process_bind_param(self, value: Any, _: Any) -> Any:
        return jsonable_encoder(value) if value is not None else None


class PydanticModelType(PydanticBaseType):
    def process_result_value(self, value: Any, _: Any) -> Optional[BaseModel]:
        if value is None:
            return None
        return parse_obj_as(self.pydantic_type, value)


class PydanticListType(PydanticBaseType):
    def process_result_value(self, value: Any, _: Any) -> Optional[list[BaseModel]]:
        if value is None:
            return None
        return parse_obj_as(
            list[self.pydantic_type], obj=value  # type: ignore[name-defined]
        )
