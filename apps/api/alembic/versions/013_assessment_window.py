"""Persist the exact observation window used by a vessel assessment.

Revision ID: 013
Revises: 012

The existing ``lookback_hours`` field records only a duration, so a report
cannot prove that an attached assessment was evaluated over the same anchors.
These nullable columns retain the resolved rolling or historical window
without changing the stable ``(mmsi, rule_version, source_mode)`` identity.
Legacy rows stay NULL: their anchors are unknown and must not be inferred.
"""
import sqlalchemy as sa
from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vessel_assessments",
        sa.Column("window_mode", sa.String(20), nullable=True),
    )
    op.add_column(
        "vessel_assessments",
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "vessel_assessments",
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_vessel_assessments_window_mode",
        "vessel_assessments",
        "window_mode IS NULL OR window_mode IN ('rolling', 'historical')",
    )
    op.create_check_constraint(
        "ck_vessel_assessments_window_anchors",
        "vessel_assessments",
        "(window_start IS NULL) = (window_end IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_vessel_assessments_window_anchors",
        "vessel_assessments",
        type_="check",
    )
    op.drop_constraint(
        "ck_vessel_assessments_window_mode",
        "vessel_assessments",
        type_="check",
    )
    op.drop_column("vessel_assessments", "window_end")
    op.drop_column("vessel_assessments", "window_start")
    op.drop_column("vessel_assessments", "window_mode")
