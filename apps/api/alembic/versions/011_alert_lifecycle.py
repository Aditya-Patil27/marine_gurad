"""Persist derived alert conditions with an auditable review lifecycle.

Revision ID: 011
Revises: 010

Rows are created only from an explicit analyst-triggered sync of the existing
alert generator. IDs match the deterministic A-003F projection identity so a
stored alert and a live projection of the same condition share a UUID. Nothing
here infers provider provenance; missing mode stays NULL/unknown and no record
is evidence of illegal activity.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None

TRACK_MODES = "source_mode IS NULL OR source_mode IN ('live', 'historical', 'replay', 'synthetic', 'unknown')"


def upgrade() -> None:
    op.create_table(
        "alert_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("mmsi", sa.BigInteger(), nullable=False),
        sa.Column("zone_key", sa.String(200), nullable=False),
        sa.Column("mpa_id", sa.Integer(), nullable=True),
        sa.Column("mpa_name", sa.String(200), nullable=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location_lat", sa.Double(), nullable=True),
        sa.Column("location_lon", sa.Double(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("source", sa.String(120), nullable=True),
        sa.Column("source_mode", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("acknowledged_by", sa.String(50), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(50), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_note", sa.String(500), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("type", "mmsi", "zone_key", name="uq_alert_records_identity"),
        sa.CheckConstraint(
            "severity IN ('HIGH', 'MEDIUM', 'LOW')", name="ck_alert_records_severity"
        ),
        sa.CheckConstraint(
            "status IN ('open', 'acknowledged', 'resolved')",
            name="ck_alert_records_status",
        ),
        sa.CheckConstraint(TRACK_MODES, name="ck_alert_records_source_mode"),
        sa.CheckConstraint("version >= 0", name="ck_alert_records_version"),
        sa.CheckConstraint(
            "last_observed_at >= first_observed_at", name="ck_alert_records_observation_order"
        ),
        sa.CheckConstraint(
            "(location_lat IS NULL) = (location_lon IS NULL)",
            name="ck_alert_records_location_pair",
        ),
        sa.CheckConstraint(
            "location_lat IS NULL OR (location_lat BETWEEN -90 AND 90 AND "
            "location_lon BETWEEN -180 AND 180)",
            name="ck_alert_records_location_bounds",
        ),
        sa.CheckConstraint(
            "(acknowledged_by IS NULL) = (acknowledged_at IS NULL)",
            name="ck_alert_records_ack_pair",
        ),
        sa.CheckConstraint(
            "(resolved_by IS NULL) = (resolved_at IS NULL)",
            name="ck_alert_records_resolve_pair",
        ),
        sa.CheckConstraint(
            "status = 'open' OR "
            "(status = 'acknowledged' AND acknowledged_by IS NOT NULL AND acknowledged_at IS NOT NULL) OR "
            "(status = 'resolved' AND resolved_by IS NOT NULL AND resolved_at IS NOT NULL)",
            name="ck_alert_records_status_fields",
        ),
        sa.CheckConstraint("char_length(type) > 0", name="ck_alert_records_type"),
        sa.CheckConstraint("char_length(title) > 0", name="ck_alert_records_title"),
    )
    op.execute(
        "CREATE INDEX ix_alert_records_status_last_observed "
        "ON alert_records (status, last_observed_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_alert_records_mmsi_last_observed "
        "ON alert_records (mmsi, last_observed_at DESC)"
    )
    op.create_table(
        "alert_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "alert_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("alert_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event", sa.String(20), nullable=False),
        sa.Column("actor", sa.String(50), nullable=False),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "event IN ('created', 'observed', 'acknowledged', 'resolved', 'reopened')",
            name="ck_alert_events_event",
        ),
        sa.CheckConstraint("char_length(actor) > 0", name="ck_alert_events_actor"),
    )
    op.execute(
        "CREATE INDEX ix_alert_events_alert_created ON alert_events (alert_id, created_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX ix_alert_events_alert_created")
    op.drop_table("alert_events")
    op.execute("DROP INDEX ix_alert_records_mmsi_last_observed")
    op.execute("DROP INDEX ix_alert_records_status_last_observed")
    op.drop_table("alert_records")
