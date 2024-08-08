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
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ARRAY, Enum, ForeignKey, String, func, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

from .test_enums import TestStateEnum
from .test_suite_execution import TestSuiteExecution

if TYPE_CHECKING:
    from .test_collection_metadata import TestCollectionMetadata  # noqa: F401
    from .test_run_execution import TestRunExecution  # noqa: F401


class TestCollectionExecution(Base):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(nullable=False)
    execution_index: Mapped[int] = mapped_column(nullable=False)
    mandatory: Mapped[bool] = mapped_column(default=False, nullable=False)

    state: Mapped[TestStateEnum] = mapped_column(
        Enum(TestStateEnum), nullable=False, default=TestStateEnum.PENDING
    )

    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    started_at: Mapped[Optional[datetime]]
    completed_at: Mapped[Optional[datetime]]

    errors: Mapped[list[str]] = mapped_column(
        ARRAY(String, dimensions=1), nullable=False, default=[]
    )

    test_collection_metadata_id: Mapped[int] = mapped_column(
        ForeignKey("testcollectionmetadata.id"), nullable=False
    )
    test_collection_metadata: Mapped["TestCollectionMetadata"] = relationship(
        "TestCollectionMetadata", back_populates="test_collection_executions"
    )

    test_run_execution_id: Mapped[int] = mapped_column(
        ForeignKey("testrunexecution.id"), nullable=False
    )
    test_run_execution: Mapped["TestRunExecution"] = relationship(
        "TestRunExecution", back_populates="test_collection_executions"
    )

    test_suite_executions: Mapped[list["TestSuiteExecution"]] = relationship(
        TestSuiteExecution,
        back_populates="test_collection_execution",
        uselist=True,
        order_by="TestSuiteExecution.execution_index",
        collection_class=ordering_list("execution_index"),
        cascade="all, delete-orphan",
    )

    @hybrid_property
    def test_suite_execution_count(self) -> int:
        return (
            self.obj_session().scalar(
                select(func.count())
                .select_from(TestSuiteExecution)
                .filter(TestSuiteExecution.test_collection_execution == self)
            )
            or 0
        )
