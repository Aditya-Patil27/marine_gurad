"""Persist reviewed incident snapshots.

Revision ID: 003
Revises: 002
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "incident_reports",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("mmsi", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("snapshot", JSONB, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True)),
        sa.Column("signed_by", sa.String(120)),
    )
    op.create_index("ix_incident_reports_mmsi", "incident_reports", ["mmsi"])


def downgrade():
    op.drop_index("ix_incident_reports_mmsi", table_name="incident_reports")
    op.drop_table("incident_reports")
