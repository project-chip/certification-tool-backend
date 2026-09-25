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
"""Move test run log to its own table

Replaces the single JSON `log` column on testrunexecution (which was rewritten
in full on every flush, giving O(n^2) writes for large logs) with an
append-only testrunlogentry table. Existing log blobs are backfilled into rows.

Revision ID: b7e2f1a9c3d4
Revises: b1f9e3d7c2a5
Create Date: 2026-06-24 00:00:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "b7e2f1a9c3d4"
down_revision = "b1f9e3d7c2a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "testrunlogentry",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("timestamp", sa.Float(), nullable=False),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("test_suite_execution_index", sa.Integer(), nullable=True),
        sa.Column("test_case_execution_index", sa.Integer(), nullable=True),
        sa.Column("test_step_execution_index", sa.Integer(), nullable=True),
        sa.Column("test_run_execution_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["test_run_execution_id"],
            ["testrunexecution.id"],
            name=op.f("fk_testrunlogentry_test_run_execution_id_testrunexecution"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_testrunlogentry")),
    )
    op.create_index(
        "ix_testrunlogentry_run_seq",
        "testrunlogentry",
        ["test_run_execution_id", "seq"],
        unique=False,
    )

    _backfill_entries_from_json()

    op.drop_column("testrunexecution", "log")


def _backfill_entries_from_json() -> None:
    """Copy each run's JSON log array into individual testrunlogentry rows.

    Done entirely server side. A single run's log can reach tens of MB, and
    psycopg2 buffers a whole result set client side, so selecting the logs into
    Python would hold every run's log in memory at once -- on the Raspberry Pi
    the harness runs on, that is enough to fail the migration. Postgres instead
    expands the arrays and writes the rows without the data leaving the server.

    json_typeof guards against a run whose log is JSON null rather than an
    array; json_array_elements errors on a scalar.
    """
    op.execute(
        """
        INSERT INTO testrunlogentry (
            test_run_execution_id, seq, level, timestamp, message,
            test_suite_execution_index, test_case_execution_index,
            test_step_execution_index
        )
        SELECT run.id,
               entry.ord - 1,
               entry.value ->> 'level',
               (entry.value ->> 'timestamp')::double precision,
               entry.value ->> 'message',
               (entry.value ->> 'test_suite_execution_index')::integer,
               (entry.value ->> 'test_case_execution_index')::integer,
               (entry.value ->> 'test_step_execution_index')::integer
        FROM testrunexecution AS run
        CROSS JOIN json_array_elements(run.log)
            WITH ORDINALITY AS entry(value, ord)
        WHERE run.log IS NOT NULL AND json_typeof(run.log) = 'array'
        """
    )


def downgrade() -> None:
    op.add_column(
        "testrunexecution",
        sa.Column(
            "log",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )

    _repack_entries_into_json()

    op.drop_index("ix_testrunlogentry_run_seq", table_name="testrunlogentry")
    op.drop_table("testrunlogentry")
    # Drop the helper default now that existing rows are populated.
    op.alter_column("testrunexecution", "log", server_default=None)


def _repack_entries_into_json() -> None:
    """Rebuild the JSON log array on testrunexecution from the entry rows.

    Server side for the same reason as the backfill: a run's entries should
    never all be resident in the migration process at once.
    """
    op.execute(
        """
        UPDATE testrunexecution AS run
        SET log = COALESCE(
            (
                SELECT json_agg(
                           json_build_object(
                               'level', e.level,
                               'timestamp', e.timestamp,
                               'message', e.message,
                               'test_suite_execution_index',
                               e.test_suite_execution_index,
                               'test_case_execution_index',
                               e.test_case_execution_index,
                               'test_step_execution_index',
                               e.test_step_execution_index
                           )
                           ORDER BY e.seq
                       )
                FROM testrunlogentry AS e
                WHERE e.test_run_execution_id = run.id
            ),
            '[]'::json
        )
        """
    )
