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
"""Added Thread Project Config

Revision ID: 621cc7fec168
Revises: d125c14ea922
Create Date: 2021-07-26 19:18:16.148796

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "621cc7fec168"
down_revision = "d125c14ea922"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("project", sa.Column("thread_channel", sa.String(), nullable=True))
    op.add_column("project", sa.Column("thread_extpanid", sa.String(), nullable=True))
    op.add_column("project", sa.Column("thread_masterkey", sa.String(), nullable=True))
    op.add_column(
        "project", sa.Column("thread_networkname", sa.String(), nullable=True)
    )
    op.add_column(
        "project", sa.Column("thread_on_mesh_prefix", sa.String(), nullable=True)
    )
    op.add_column("project", sa.Column("thread_panid", sa.String(), nullable=True))
    op.add_column(
        "project", sa.Column("thread_rcp_serial_path", sa.String(), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("project", "thread_rcp_serial_path")
    op.drop_column("project", "thread_panid")
    op.drop_column("project", "thread_on_mesh_prefix")
    op.drop_column("project", "thread_networkname")
    op.drop_column("project", "thread_masterkey")
    op.drop_column("project", "thread_extpanid")
    op.drop_column("project", "thread_channel")
    # ### end Alembic commands ###
