"""Persist bounded provider-run outcomes and checkpoints.

Revision ID: 009
Revises: 008
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_runs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("position_count", sa.Integer(), nullable=True),
        sa.Column("event_count", sa.Integer(), nullable=True),
        sa.Column("error_category", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("checkpoint", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("triggered_by", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "provider IN ('aisstream', 'gfw')",
            name="ck_source_runs_provider",
        ),
        sa.CheckConstraint(
            "status IN ('succeeded', 'empty', 'unavailable', 'failed', 'rejected')",
            name="ck_source_runs_status",
        ),
        sa.CheckConstraint(
            "error_category IS NULL OR error_category IN "
            "('config', 'auth', 'quota', 'network', 'provider', 'validation', 'timeout', 'unknown')",
            name="ck_source_runs_error_category",
        ),
        sa.CheckConstraint(
            "(provider = 'aisstream' AND operation = 'ais_snapshot' AND mode = 'live') OR "
            "(provider = 'gfw' AND operation = 'gfw_regional_events' AND mode = 'historical')",
            name="ck_source_runs_provider_operation_mode",
        ),
        sa.CheckConstraint(
            "(status IN ('succeeded', 'empty') AND error_category IS NULL AND error_message IS NULL) OR "
            "(status IN ('unavailable', 'failed', 'rejected') AND error_category IS NOT NULL "
            "AND error_message IS NOT NULL)",
            name="ck_source_runs_error_consistency",
        ),
        sa.CheckConstraint("request_count >= 0", name="ck_source_runs_request_count"),
        sa.CheckConstraint(
            "(position_count IS NULL AND event_count IS NOT NULL AND provider = 'gfw') OR "
            "(position_count IS NOT NULL AND event_count IS NULL AND provider = 'aisstream')",
            name="ck_source_runs_count_shape",
        ),
        sa.CheckConstraint(
            "position_count IS NULL OR position_count >= 0",
            name="ck_source_runs_position_count",
        ),
        sa.CheckConstraint(
            "event_count IS NULL OR event_count >= 0",
            name="ck_source_runs_event_count",
        ),
        sa.CheckConstraint("finished_at >= started_at", name="ck_source_runs_time_order"),
        sa.CheckConstraint("length(triggered_by) BETWEEN 1 AND 100", name="ck_source_runs_triggered_by"),
    )
    op.execute(
        "CREATE INDEX ix_source_runs_provider_started_at "
        "ON source_runs (provider, started_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX ix_source_runs_provider_started_at")
    op.drop_table("source_runs")
