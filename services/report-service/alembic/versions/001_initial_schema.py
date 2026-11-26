"""Initial report_db schema (report_snapshots)

Revision ID: 001_initial_report
Revises:
Create Date: 2026-11-26
"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial_report"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_type", sa.String(100), nullable=False),
        sa.Column("requested_by", sa.Integer(), nullable=False),
        sa.Column("requested_role", sa.String(50), nullable=False),
        sa.Column("filter_context", sa.String(255), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_report_snapshots_report_type", "report_snapshots", ["report_type"])


def downgrade() -> None:
    op.drop_table("report_snapshots")
