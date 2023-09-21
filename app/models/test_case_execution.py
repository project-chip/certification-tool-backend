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
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

from .test_enums import TestStateEnum

if TYPE_CHECKING:
    from .test_case_metadata import TestCaseMetadata  # noqa: F401
    from .test_step_execution import TestStepExecution  # noqa: F401
    from .test_suite_execution import TestSuiteExecution  # noqa: F401


class TestCaseExecution(Base):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    public_id: Mapped[str] = mapped_column(nullable=False)
    execution_index: Mapped[int] = mapped_column(nullable=False)

    state: Mapped[TestStateEnum] = mapped_column(
        Enum(TestStateEnum), nullable=False, default=TestStateEnum.PENDING
    )

    created_at: Mapped[datetime] = mapped_column(default=datetime.now, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    errors: Mapped[list[str]] = mapped_column(
        ARRAY(String, dimensions=1), nullable=False, default=[]
    )

    test_case_metadata_id: Mapped[int] = mapped_column(
        ForeignKey("testcasemetadata.id"), nullable=False
    )
    test_case_metadata: Mapped["TestCaseMetadata"] = relationship(
        "TestCaseMetadata", back_populates="test_case_executions"
    )

    test_suite_execution_id: Mapped[int] = mapped_column(
        ForeignKey("testsuiteexecution.id"), nullable=False
    )
    test_suite_execution: Mapped["TestSuiteExecution"] = relationship(
        "TestSuiteExecution", back_populates="test_case_executions"
    )

    test_step_executions: Mapped[list["TestStepExecution"]] = relationship(
        "TestStepExecution",
        back_populates="test_case_execution",
        uselist=True,
        order_by="TestStepExecution.execution_index",
        collection_class=ordering_list("execution_index"),
        cascade="all, delete-orphan",
    )
