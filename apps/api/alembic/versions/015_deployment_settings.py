"""Persist the single-organisation deployment settings.

Revision ID: 015
Revises: 014
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deployment_settings",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("organization", sa.Text(), nullable=False),
        sa.Column("aoi_name", sa.Text(), nullable=False),
        sa.Column("aoi_bbox", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("display_timezone", sa.Text(), nullable=False),
        sa.Column("alert_threshold", sa.Numeric(4, 3), nullable=False),
        sa.Column("report_recipients", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.CheckConstraint("id = 1", name="deployment_settings_singleton"),
        sa.CheckConstraint("alert_threshold >= 0 AND alert_threshold <= 1", name="deployment_settings_threshold_range"),
        sa.CheckConstraint("retention_days >= 1 AND retention_days <= 3650", name="deployment_settings_retention_range"),
    )
    op.execute(sa.text("""
        INSERT INTO deployment_settings
            (id, organization, aoi_name, aoi_bbox, display_timezone,
             alert_threshold, report_recipients, retention_days)
        VALUES
            (1, 'SamudraSense local deployment', 'Gulf of Mannar',
             '[[77.5, 8.0], [79.5, 10.0]]'::jsonb, 'Asia/Kolkata',
             0.500, '[]'::jsonb, 365)
    """))


def downgrade() -> None:
    op.drop_table("deployment_settings")
