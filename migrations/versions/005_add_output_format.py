"""add_output_format_to_translations

Revision ID: 005
Revises: 004
Create Date: 2026-04-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "translations",
        sa.Column(
            "output_format",
            sa.String(20),
            nullable=False,
            server_default="pdf",
        ),
    )
