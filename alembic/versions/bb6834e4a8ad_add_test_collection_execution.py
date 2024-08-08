"""Add test collection execution

Revision ID: bb6834e4a8ad
Revises: e2c185af1226
Create Date: 2024-08-07 20:35:26.786266

"""
from datetime import datetime

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "bb6834e4a8ad"
down_revision = "e2c185af1226"
branch_labels = None
depends_on = None


# TODO: compute test collection execution's state
# TODO: set collection started_at and completed_at by copying from the first and the last suite executions # noqa:E501
# TODO: validate
def upgrade():
    op.alter_column(
        "testcasemetadata",
        "mandatory",
        existing_type=sa.BOOLEAN(),
        existing_server_default=False,
        nullable=False,
    )
    op.alter_column(
        "testsuitemetadata",
        "mandatory",
        existing_type=sa.BOOLEAN(),
        existing_server_default=False,
        nullable=False,
    )

    # Create test collection metadata
    collection_metadata_table = op.create_table(
        "testcollectionmetadata",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("source_hash", sa.VARCHAR(length=64), nullable=False),
        sa.Column("mandatory", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=datetime.now),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_testcollectionmetadata")),
    )
    op.create_index(
        op.f("ix_testcollectionmetadata_id"),
        "testcollectionmetadata",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_testcollectionmetadata_source_hash"),
        "testcollectionmetadata",
        ["source_hash"],
        unique=False,
    )

    # Create test collection execution
    collection_execution_table = op.create_table(
        "testcollectionexecution",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("execution_index", sa.Integer(), nullable=False),
        sa.Column("mandatory", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "state",
            sa.dialects.postgresql.ENUM(name="teststateenum", create_type=False),
            nullable=False,
            default="PENDING",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=datetime.now),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "errors", sa.ARRAY(sa.String(), dimensions=1), nullable=False, default=[]
        ),
        sa.Column("test_collection_metadata_id", sa.Integer(), nullable=True),
        sa.Column("test_run_execution_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["test_collection_metadata_id"],
            ["testcollectionmetadata.id"],
            name=op.f(
                "fk_testcollectionexecution_test_collection_metadata_id_testcollectionmetadata"  # noqa: E501
            ),
        ),
        sa.ForeignKeyConstraint(
            ["test_run_execution_id"],
            ["testrunexecution.id"],
            name=op.f(
                "fk_testcollectionexecution_test_run_execution_id_testrunexecution"
            ),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_testcollectionexecution")),
    )
    op.create_index(
        op.f("ix_testcollectionexecution_id"),
        "testcollectionexecution",
        ["id"],
        unique=False,
    )

    # Add test collection execution reference to test suite execution
    op.add_column(
        "testsuiteexecution",
        sa.Column("test_collection_execution_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        op.f(
            "fk_testsuiteexecution_test_collection_execution_id_testcollectionexecution"
        ),
        "testsuiteexecution",
        "testcollectionexecution",
        ["test_collection_execution_id"],
        ["id"],
    )
    connection = op.get_bind()

    # Get collection info from each existing suite executions
    cursor_result = connection.execute(
        sa.table(
            "testsuiteexecution",
            sa.column("id"),
            sa.column("collection_id"),
            sa.column("mandatory"),
            sa.column("test_run_execution_id"),
            sa.column("execution_index"),
        )
        .select()
        .order_by("test_run_execution_id", "execution_index")
    )
    results = cursor_result.all()

    # Create new test collection metadata and test collection executions
    last_run_id = -1
    last_collection_id = ""
    new_collection_metadata = []
    new_collection_executions = []
    collection_execution_index = 0
    collection_ids = []
    first_execution_indexes = []
    for result in results:
        # result[0]: id
        # result[1]: collection_id
        # result[2]: mandatory
        # result[3]: test_run_execution_id
        # result[4]: execution_index

        if last_run_id != result[3]:
            # First suite execution of the run
            collection_execution_index = 0
            last_run_id = result[3]

        if last_collection_id != result[1]:
            # First suite execution of the collection
            last_collection_id = result[1]

            # Create new collection metadata
            new_collection_metadata.append(
                {
                    "name": result[1],
                    "version": "0.0.1",
                    "path": "undefined",
                    "source_hash": "de7f3c1390cd283f91f74a334aaf0ec3",
                    "mandatory": result[2],
                }
            )

            new_collection_executions.append(
                {
                    "name": result[1],
                    "mandatory": result[2],
                    "test_run_execution_id": result[3],
                    "execution_index": collection_execution_index,
                }
            )
            collection_execution_index += 1

            # Save info about the first suite execution index of a collection
            # The execution index for the first collection doesn't need to be updated
            if result[4] != 0:
                collection_ids.append(result[0])
                first_execution_indexes.append(result[4])

    # Bulk insert new collection metadata
    op.bulk_insert(collection_metadata_table, new_collection_metadata)

    # Bulk insert new collection executions
    op.bulk_insert(collection_execution_table, new_collection_executions)

    # Set test_collection_metadata_id on test collection executions
    op.execute(
        "UPDATE testcollectionexecution \
        SET test_collection_metadata_id = cm.id\
        FROM testcollectionmetadata as cm \
        WHERE testcollectionexecution.name = cm.name"
    )

    # Make test_collection_metadata_id not nullable
    op.alter_column(
        "testcollectionexecution",
        "test_collection_metadata_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # Set test_collection_execution_id on test suite executions
    op.execute(
        "UPDATE testsuiteexecution \
        SET test_collection_execution_id = ce.id\
        FROM testcollectionexecution as ce \
        WHERE testsuiteexecution.test_run_execution_id = ce.test_run_execution_id \
        AND collection_id = ce.name"
    )

    # Make test_collection_execution_id not nullable
    op.alter_column(
        "testsuiteexecution",
        "test_collection_execution_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # TODO: fix this
    # Update execution_index on test suite executions
    connection.execute(
        sa.text(
            f"UPDATE testsuiteexecution \
            SET execution_index=execution_index - bulk_query.first_execution_index \
            FROM ( \
                SELECT * FROM UNNEST( \
                ARRAY{collection_ids}::INT[], \
                ARRAY{first_execution_indexes}::INT[] \
                ) AS t(collection_id, first_execution_index) \
            ) AS bulk_query \
            WHERE testsuiteexecution.test_collection_execution_id=bulk_query.collection_id",  # noqa:501
        )
    )

    # Remove test run execution reference from test suite execution
    op.drop_constraint(
        "fk_testsuiteexecution_test_run_execution_id_testrunexecution",
        "testsuiteexecution",
        type_="foreignkey",
    )
    op.drop_column("testsuiteexecution", "test_run_execution_id")

    # Remove collection_id from test suite execution
    op.drop_column("testsuiteexecution", "collection_id")


# TODO: validate
def downgrade():
    # Restore removed columns from test suite execution as nullable
    op.add_column(
        "testsuiteexecution",
        sa.Column("collection_id", sa.VARCHAR(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "testsuiteexecution",
        sa.Column(
            "test_run_execution_id", sa.INTEGER(), autoincrement=False, nullable=True
        ),
    )
    op.create_foreign_key(
        "fk_testsuiteexecution_test_run_execution_id_testrunexecution",
        "testsuiteexecution",
        "testrunexecution",
        ["test_run_execution_id"],
        ["id"],
    )

    # Set collection_id and test_run_execution_id in test suite execution
    op.execute(
        "UPDATE testsuiteexecution \
        SET collection_id = ce.name, \
            test_run_execution_id = ce.test_run_execution_id  \
        FROM testcollectionexecution AS ce \
        WHERE test_collection_execution_id = ce.id"
    )

    # Make collection_id and test_run_execution_id not nullable
    op.alter_column(
        "testsuiteexecution",
        "collection_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "testsuiteexecution",
        "test_run_execution_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    connection = op.get_bind()

    # Get execution index info
    cursor_result = connection.execute(
        sa.text(
            "SELECT se.id, se.execution_index, se.test_collection_execution_id, \
                    ce.id, ce.execution_index, ce.test_run_execution_id \
            FROM testsuiteexecution AS se \
            JOIN testcollectionexecution AS ce \
            ON se.test_collection_execution_id = ce.id \
            ORDER BY ce.test_run_execution_id, ce.execution_index, se.execution_index"
        )
    )
    results = cursor_result.all()

    # Update execution_index on test suite executions
    last_run_id = -1
    last_collection_execution_index = -1
    run_suite_count = 0
    for result in results:
        # result[0]: se.id
        # result[1]: se.execution_index
        # result[2]: se.test_collection_execution_id
        # result[3]: ce.id
        # result[4]: ce.execution_index
        # result[5]: ce.test_run_execution_id

        if last_run_id != result[5]:
            # First suite execution of the run
            last_run_id = result[5]
            last_collection_execution_index = -1
            run_suite_count = 0

        if last_collection_execution_index != result[4]:
            # First suite execution of the collection
            last_collection_execution_index = result[4]

            # No need to update the indexes for the first collection or the run
            if result[4] != 0:
                op.execute(
                    f"UPDATE testsuiteexecution \
                    SET execution_index = execution_index + {run_suite_count} "  # noqa:E501
                    f"WHERE test_collection_execution_id = {result[3]}"
                )

        run_suite_count += 1

    # Remove test collection execution reference from test suite execution
    op.drop_constraint(
        op.f(
            "fk_testsuiteexecution_test_collection_execution_id_testcollectionexecution"
        ),
        "testsuiteexecution",
        type_="foreignkey",
    )
    op.drop_column("testsuiteexecution", "test_collection_execution_id")

    # Drop test collection execution
    op.drop_index(
        op.f("ix_testcollectionexecution_id"), table_name="testcollectionexecution"
    )
    op.drop_table("testcollectionexecution")

    # Drop test collection metadata
    op.drop_index(
        op.f("ix_testcollectionmetadata_source_hash"),
        table_name="testcollectionmetadata",
    )
    op.drop_index(
        op.f("ix_testcollectionmetadata_id"), table_name="testcollectionmetadata"
    )
    op.drop_table("testcollectionmetadata")

    op.alter_column(
        "testsuitemetadata", "mandatory", existing_type=sa.BOOLEAN(), nullable=True
    )
    op.alter_column(
        "testcasemetadata", "mandatory", existing_type=sa.BOOLEAN(), nullable=True
    )
