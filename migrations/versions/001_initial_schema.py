"""initial_schema

Revision ID: 001
Revises:
Create Date: 2026-04-08

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "institutions",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
    )
    op.create_index("ix_institutions_code", "institutions", ["code"])

    op.create_table(
        "languages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(10), unique=True, nullable=False),
        sa.Column("native_name", sa.String(100), nullable=True),
        sa.Column("libretranslate_code", sa.String(10), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
    )
    op.create_index("ix_languages_code", "languages", ["code"])

    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "institution_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("institutions.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "books",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("subject", sa.String(200), nullable=True),
        sa.Column("grade_level", sa.String(50), nullable=True),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column(
            "extraction_status", sa.String(20), server_default="pending", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "institution_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("institutions.id"),
            nullable=True,
        ),
        sa.Column(
            "uploaded_by",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
    )

    op.create_table(
        "translations",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("content_type", sa.String(20), nullable=False),
        sa.Column("content_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("translated_text", sa.Text(), nullable=True),
        sa.Column("translation_engine", sa.String(50), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "language_id", sa.Integer(), sa.ForeignKey("languages.id"), nullable=False
        ),
    )
    op.create_index("ix_translations_content_type", "translations", ["content_type"])
    op.create_index("ix_translations_content_id", "translations", ["content_id"])
    op.create_index("ix_translations_language_id", "translations", ["language_id"])
    op.create_index("ix_translations_status", "translations", ["status"])

    op.create_table(
        "translation_jobs",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "translation_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("translations.id"),
            nullable=False,
        ),
        sa.Column(
            "requested_by",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
    )

    op.create_table(
        "exams",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "institution_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("institutions.id"),
            nullable=True,
        ),
        sa.Column(
            "book_id", sa.UUID(as_uuid=True), sa.ForeignKey("books.id"), nullable=True
        ),
        sa.Column(
            "uploaded_by",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
    )

    op.create_table(
        "answer_keys",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "institution_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("institutions.id"),
            nullable=True,
        ),
        sa.Column(
            "book_id", sa.UUID(as_uuid=True), sa.ForeignKey("books.id"), nullable=True
        ),
        sa.Column(
            "exam_id", sa.UUID(as_uuid=True), sa.ForeignKey("exams.id"), nullable=True
        ),
        sa.Column(
            "uploaded_by",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("answer_keys")
    op.drop_table("exams")
    op.drop_table("translation_jobs")
    op.drop_table("translations")
    op.drop_table("books")
    op.drop_table("users")
    op.drop_table("languages")
    op.drop_table("institutions")
