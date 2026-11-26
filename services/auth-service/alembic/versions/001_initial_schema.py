"""Initial auth_db schema (auth_credentials, login_audit_logs)

Revision ID: 001_initial_auth
Revises:
Create Date: 2026-11-26
"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial_auth"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("ADMIN", "RESTAURANT_OWNER", "CUSTOMER", "DELIVERY_AGENT", name="userrole"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_auth_credentials_id", "auth_credentials", ["id"])
    op.create_index("ix_auth_credentials_email", "auth_credentials", ["email"], unique=True)

    op.create_table(
        "login_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_login_audit_logs_user_id", "login_audit_logs", ["user_id"])
    op.create_index("ix_login_audit_logs_email", "login_audit_logs", ["email"])


def downgrade() -> None:
    op.drop_table("login_audit_logs")
    op.drop_table("auth_credentials")
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
