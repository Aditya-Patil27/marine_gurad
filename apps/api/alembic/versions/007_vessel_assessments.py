"""Persist stable vessel assessments for the alert workflow.

Revision ID: 007
Revises: 006
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vessel_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("mmsi", sa.BigInteger(), nullable=False),
        sa.Column("rule_version", sa.String(50), nullable=False),
        sa.Column("source_mode", sa.String(50), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lookback_hours", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("factors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("checks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("zone", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("headline", sa.Text(), nullable=True),
        sa.Column("vessel_name", sa.String(255), nullable=True),
        sa.Column("vessel_type", sa.String(100), nullable=True),
        sa.Column("length", sa.Float(), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_position", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("mmsi", "rule_version", "source_mode", name="uq_vessel_assessments_mmsi_rule_mode"),
    )
    op.create_index("ix_vessel_assessments_mmsi", "vessel_assessments", ["mmsi"])
    op.create_index("ix_vessel_assessments_level", "vessel_assessments", ["level"])
    op.create_index("ix_vessel_assessments_score", "vessel_assessments", ["score"])
    op.create_index("ix_vessel_assessments_evaluated_at", "vessel_assessments", ["evaluated_at"])


def downgrade() -> None:
    op.drop_index("ix_vessel_assessments_evaluated_at", table_name="vessel_assessments")
    op.drop_index("ix_vessel_assessments_score", table_name="vessel_assessments")
    op.drop_index("ix_vessel_assessments_level", table_name="vessel_assessments")
    op.drop_index("ix_vessel_assessments_mmsi", table_name="vessel_assessments")
    op.drop_table("vessel_assessments")
