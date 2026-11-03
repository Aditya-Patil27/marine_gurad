"""Index SAR candidates by matched vessel.

Revision ID: 005
Revises: 004
"""
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_sar_detections_matched_mmsi", "sar_detections", ["matched_mmsi"])


def downgrade():
    op.drop_index("ix_sar_detections_matched_mmsi", table_name="sar_detections")
