#
# Copyright (c) 2026 Project CHIP Authors
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
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from .test_run_execution import TestRunExecution  # noqa: F401


class TestRunLogEntry(Base):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Position of the entry within the run. Preserves ordering independent of
    # insert timing: entries are produced on a background thread and flushed in
    # batches, so id order is not guaranteed to match log order.
    seq: Mapped[int] = mapped_column(nullable=False)

    level: Mapped[str] = mapped_column(String, nullable=False)
    # Epoch seconds, matching the in-memory schema and existing log formatting.
    timestamp: Mapped[float] = mapped_column(nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)

    # Positional indices into the run's children (execution_index values), kept
    # as plain ints to match how log_utils resolves them by subscript.
    test_suite_execution_index: Mapped[Optional[int]]
    test_case_execution_index: Mapped[Optional[int]]
    test_step_execution_index: Mapped[Optional[int]]

    test_run_execution_id: Mapped[int] = mapped_column(
        ForeignKey("testrunexecution.id", ondelete="CASCADE"), nullable=False
    )
    test_run_execution: Mapped["TestRunExecution"] = relationship(
        "TestRunExecution", back_populates="log"
    )

    __table_args__ = (
        # Every read of the log wants one run's entries in seq order.
        Index("ix_testrunlogentry_run_seq", "test_run_execution_id", "seq"),
    )
