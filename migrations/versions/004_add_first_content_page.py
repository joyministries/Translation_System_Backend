"""add_first_content_page_to_books

Revision ID: 004
Revises: 003
Create Date: 2026-04-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "books",
        sa.Column(
            "first_content_page",
            sa.Integer(),
            nullable=True,
            server_default="1",
        ),
    )
