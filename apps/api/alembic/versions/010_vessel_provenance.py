"""Add truthful source provenance to vessel tracks and assessments.

Revision ID: 010
Revises: 009

Existing rows are backfilled to ``unknown``; nothing is relabelled as a real or
provider-derived source. The defaults keep future implicit writes conservative.
"""
import sqlalchemy as sa
from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None

TRACK_MODES = "source_mode IN ('live', 'historical', 'replay', 'synthetic', 'unknown')"
ASSESSMENT_MODES = (
    "source_mode IN ('live', 'historical', 'replay', 'synthetic', 'unknown', 'mixed')"
)


def upgrade() -> None:
    op.add_column(
        "vessel_tracks",
        sa.Column("source", sa.String(120), nullable=False, server_default=sa.text("'unknown'")),
    )
    op.add_column(
        "vessel_tracks",
        sa.Column("source_mode", sa.String(20), nullable=False, server_default=sa.text("'unknown'")),
    )
    op.create_check_constraint("ck_vessel_tracks_source_mode", "vessel_tracks", TRACK_MODES)
    op.create_check_constraint(
        "ck_vessel_assessments_source_mode", "vessel_assessments", ASSESSMENT_MODES
    )


def downgrade() -> None:
    op.drop_constraint("ck_vessel_assessments_source_mode", "vessel_assessments", type_="check")
    op.drop_constraint("ck_vessel_tracks_source_mode", "vessel_tracks", type_="check")
    op.drop_column("vessel_tracks", "source_mode")
    op.drop_column("vessel_tracks", "source")
