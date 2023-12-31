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
"""Add Operator

Revision ID: f5af3855be39
Revises: 6494682dab86
Create Date: 2021-08-19 21:18:16.371500

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f5af3855be39"
down_revision = "6494682dab86"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "operator",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_operator")),
    )
    op.create_index(op.f("ix_operator_id"), "operator", ["id"], unique=False)
    op.add_column(
        "testrunexecution", sa.Column("operator_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        op.f("fk_testrunexecution_operator_id_operator"),
        "testrunexecution",
        "operator",
        ["operator_id"],
        ["id"],
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        op.f("fk_testrunexecution_operator_id_operator"),
        "testrunexecution",
        type_="foreignkey",
    )
    op.drop_column("testrunexecution", "operator_id")
    op.drop_index(op.f("ix_operator_id"), table_name="operator")
    op.drop_table("operator")
    # ### end Alembic commands ###
