"""phase 4 memory

Revision ID: 0d50f7c45dc6
Revises: 0ab4f35d61a7
Create Date: 2026-09-26 22:02:37.089197

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0d50f7c45dc6"
down_revision: Union[str, Sequence[str], None] = "0ab4f35d61a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("memory_facts", sa.Column("key", sa.String(), nullable=True))
    op.add_column("memory_facts", sa.Column("value", sa.Text(), nullable=True))
    op.add_column("memory_facts", sa.Column("normalized_value", sa.Text(), nullable=True))
    op.add_column("memory_facts", sa.Column("trust_level", sa.String(), nullable=True))
    op.add_column(
        "memory_facts", sa.Column("version", sa.Integer(), server_default="1", nullable=False)
    )
    op.add_column(
        "memory_facts", sa.Column("is_current", sa.Boolean(), server_default="true", nullable=False)
    )
    op.add_column(
        "memory_facts", sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "memory_facts", sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "memory_facts", sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "memory_facts",
        sa.Column("needs_reconfirmation", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column("memory_facts", sa.Column("embedding_model", sa.String(), nullable=True))
    op.add_column("memory_facts", sa.Column("embedding_dimension", sa.Integer(), nullable=True))

    op.execute(
        "UPDATE memory_facts SET value = content, key = category, trust_level = 'SYSTEM_DERIVED', last_verified_at = last_confirmed_at"  # noqa: E501
    )

    op.alter_column("memory_facts", "key", nullable=False)
    op.alter_column("memory_facts", "value", nullable=False)
    op.alter_column("memory_facts", "trust_level", nullable=False)

    op.drop_column("memory_facts", "content")
    op.drop_column("memory_facts", "last_confirmed_at")

    op.create_unique_constraint(
        "uix_memory_fact_version", "memory_facts", ["user_id", "key", "version"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("memory_facts", sa.Column("content", sa.Text(), nullable=True))
    op.add_column(
        "memory_facts", sa.Column("last_confirmed_at", sa.DateTime(timezone=True), nullable=True)
    )

    op.execute("UPDATE memory_facts SET content = value, last_confirmed_at = last_verified_at")

    op.alter_column("memory_facts", "content", nullable=False)

    op.drop_constraint("uix_memory_fact_version", "memory_facts", type_="unique")

    op.drop_column("memory_facts", "embedding_dimension")
    op.drop_column("memory_facts", "embedding_model")
    op.drop_column("memory_facts", "needs_reconfirmation")
    op.drop_column("memory_facts", "last_verified_at")
    op.drop_column("memory_facts", "valid_until")
    op.drop_column("memory_facts", "valid_from")
    op.drop_column("memory_facts", "is_current")
    op.drop_column("memory_facts", "version")
    op.drop_column("memory_facts", "trust_level")
    op.drop_column("memory_facts", "normalized_value")
    op.drop_column("memory_facts", "value")
    op.drop_column("memory_facts", "key")
