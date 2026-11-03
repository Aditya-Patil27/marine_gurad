"""Store externally produced, geolocated SAR detections.

Revision ID: 004
Revises: 003
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("sar_detections",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("scene_id", sa.String(300), nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("matched_mmsi", sa.Integer()),
        sa.Column("match_distance_m", sa.Float()),
        sa.Column("match_time_seconds", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_sar_detections_observed_at", "sar_detections", ["observed_at"])


def downgrade():
    op.drop_index("ix_sar_detections_observed_at", table_name="sar_detections")
    op.drop_table("sar_detections")
