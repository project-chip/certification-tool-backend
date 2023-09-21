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
"""rename selected test cases

Revision ID: 136e7b39e9e8
Revises: 72989eaa90f6
Create Date: 2021-02-11 00:07:45.540498

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "136e7b39e9e8"
down_revision = "72989eaa90f6"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "testrunconfig", "selected_test_cases", new_column_name="selected_tests"
    )
    pass


def downgrade():
    op.alter_column(
        "testrunconfig", "selected_tests", new_column_name="selected_test_cases"
    )
    pass
