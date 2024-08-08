#
# Copyright (c) 2024 Project CHIP Authors
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
from typing import TYPE_CHECKING

from sqlalchemy import VARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from .test_collection_execution import TestCollectionExecution  # noqa: F401


class TestCollectionMetadata(Base):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(nullable=False)

    path: Mapped[str] = mapped_column(nullable=False)
    version: Mapped[str] = mapped_column(nullable=False)
    source_hash: Mapped[str] = mapped_column(VARCHAR(64), nullable=False, index=True)
    mandatory: Mapped[bool] = mapped_column(default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    test_collection_executions: Mapped[list["TestCollectionExecution"]] = relationship(
        "TestCollectionExecution",
        back_populates="test_collection_metadata",
        uselist=True,
    )
