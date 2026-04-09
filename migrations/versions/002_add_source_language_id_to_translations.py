"""add_source_language_id_to_translations

Revision ID: 002
Revises: 001
Create Date: 2026-04-09

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "translations",
        sa.Column(
            "source_language_id",
            sa.Integer(),
            sa.ForeignKey("languages.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_translations_source_language_id", "translations", ["source_language_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_translations_source_language_id", "translations")
    op.drop_column("translations", "source_language_id")
