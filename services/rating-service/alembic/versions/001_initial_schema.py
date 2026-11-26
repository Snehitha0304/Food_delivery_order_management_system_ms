"""Initial rating_db schema (ratings)

Revision ID: 001_initial_rating
Revises:
Create Date: 2026-11-26
"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial_rating"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ratings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=True),
        sa.Column("restaurant_rating", sa.Integer(), nullable=False),
        sa.Column("agent_rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("restaurant_rating >= 1 AND restaurant_rating <= 5", name="check_restaurant_rating_range"),
        sa.CheckConstraint("agent_rating >= 1 AND agent_rating <= 5", name="check_agent_rating_range"),
    )
    op.create_index("ix_ratings_order_id", "ratings", ["order_id"], unique=True)
    op.create_index("ix_ratings_restaurant_id", "ratings", ["restaurant_id"])
    op.create_index("ix_ratings_agent_id", "ratings", ["agent_id"])


def downgrade() -> None:
    op.drop_table("ratings")
