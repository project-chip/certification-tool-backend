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
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ARRAY, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

from . import TestStateEnum

if TYPE_CHECKING:
    from .test_case_execution import TestCaseExecution  # noqa: F401


class TestStepExecution(Base):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(nullable=False)
    execution_index: Mapped[int] = mapped_column(nullable=False)

    state: Mapped[TestStateEnum] = mapped_column(
        Enum(TestStateEnum), nullable=False, default=TestStateEnum.PENDING
    )

    errors: Mapped[list[str]] = mapped_column(
        ARRAY(String, dimensions=1), nullable=False, default=[]
    )
    failures: Mapped[list[str]] = mapped_column(
        ARRAY(String, dimensions=1), nullable=False, default=[]
    )

    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    started_at: Mapped[Optional[datetime]]
    completed_at: Mapped[Optional[datetime]]

    test_case_execution_id: Mapped[int] = mapped_column(
        ForeignKey("testcaseexecution.id"), nullable=False
    )
    test_case_execution: Mapped["TestCaseExecution"] = relationship(
        "TestCaseExecution", back_populates="test_step_executions"
    )
