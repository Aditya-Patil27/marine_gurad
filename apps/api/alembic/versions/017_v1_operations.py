"""Add bounded v1 investigation and operations records.

Revision ID: 017
Revises: 016

All legacy rows remain valid.  Backfilled labels are deliberately conservative:
existing protected-area rows are demo/unknown provenance until an administrator
loads a licensed version, and existing SAR associations keep their baseline
single-candidate meaning.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vessel_tracks", sa.Column("source_record_id", sa.String(160), nullable=True))
    op.add_column(
        "vessel_tracks",
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.add_column(
        "vessel_tracks",
        sa.Column("quality_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default=sa.text("'[]'::jsonb")),
    )
    op.create_index(
        "uq_vessel_tracks_source_record",
        "vessel_tracks",
        ["source", "source_record_id"],
        unique=True,
        postgresql_where=sa.text("source_record_id IS NOT NULL"),
    )

    op.add_column("alert_records", sa.Column("reviewer_state", sa.String(20), nullable=False,
                                                server_default="new"))
    op.add_column("alert_records", sa.Column("assigned_to", sa.String(50), nullable=True))
    op.add_column("alert_records", sa.Column("resolution_reason", sa.String(500), nullable=True))
    op.add_column(
        "alert_records",
        sa.Column("clear_scenario", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
    )
    op.execute("""UPDATE alert_records SET reviewer_state = CASE status
        WHEN 'resolved' THEN 'closed' WHEN 'acknowledged' THEN 'in_review' ELSE 'new' END""")
    op.create_check_constraint(
        "ck_alert_records_reviewer_state", "alert_records",
        "reviewer_state IN ('new', 'watch', 'in_review', 'closed')",
    )
    op.create_index("ix_alert_records_reviewer_assignee", "alert_records",
                    ["reviewer_state", "assigned_to"])
    op.create_table(
        "alert_notes",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("alert_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author", sa.String(50), nullable=False),
        sa.Column("note", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("char_length(note) > 0", name="ck_alert_notes_note"),
    )
    op.create_index("ix_alert_notes_alert_created", "alert_notes", ["alert_id", "created_at"])

    for name, column in (
        ("publisher", sa.String(200)),
        ("boundary_version", sa.String(100)),
        ("effective_date", sa.Date()),
        ("citation", sa.Text()),
        ("permitted_use", sa.Text()),
        ("restriction_description", sa.Text()),
        ("restriction_activities", postgresql.JSONB(astext_type=sa.Text())),
        ("restriction_seasons", postgresql.JSONB(astext_type=sa.Text())),
        ("restriction_verification_status", sa.String(20)),
        ("data_mode", sa.String(20)),
    ):
        op.add_column("marine_protected_areas", sa.Column(name, column, nullable=True))
    op.execute(
        """UPDATE marine_protected_areas SET
             publisher = COALESCE(publisher, 'SamudraSense demonstration fixture'),
             boundary_version = COALESCE(boundary_version, 'unversioned'),
             permitted_use = COALESCE(permitted_use, 'Local demonstration only; redistribution rights not verified'),
             restriction_verification_status = COALESCE(restriction_verification_status, 'unverified'),
             data_mode = COALESCE(data_mode, 'synthetic')"""
    )
    op.create_check_constraint(
        "ck_mpa_rule_verification", "marine_protected_areas",
        "restriction_verification_status IS NULL OR restriction_verification_status IN ('verified', 'unverified', 'not_applicable')",
    )
    op.create_check_constraint(
        "ck_mpa_data_mode", "marine_protected_areas",
        "data_mode IS NULL OR data_mode IN ('live', 'historical', 'replay', 'synthetic', 'unknown')",
    )

    op.add_column("sar_detections", sa.Column("association_state", sa.String(30), nullable=False,
                                                server_default="insufficient_coverage"))
    op.add_column("sar_detections", sa.Column("publication_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sar_detections", sa.Column("license_reference", sa.String(500), nullable=True))
    op.add_column("sar_detections", sa.Column("provider_match_result", postgresql.JSONB(astext_type=sa.Text()),
                                                nullable=True))
    op.execute("UPDATE sar_detections SET association_state='matched' WHERE matched_mmsi IS NOT NULL")
    op.create_check_constraint(
        "ck_sar_association_state", "sar_detections",
        "association_state IN ('matched', 'ambiguous', 'unmatched', 'insufficient_coverage')",
    )
    op.create_index("ix_sar_scene_detection", "sar_detections", ["source", "scene_id"])
    op.create_table(
        "sar_detection_candidates",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("detection_id", sa.BigInteger(), sa.ForeignKey("sar_detections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mmsi", sa.BigInteger(), nullable=False),
        sa.Column("distance_m", sa.Double(), nullable=False),
        sa.Column("time_difference_seconds", sa.Double(), nullable=False),
        sa.Column("feasible_motion", sa.Boolean(), nullable=False),
        sa.Column("candidate_rank", sa.Integer(), nullable=False),
        sa.Column("input_points", sa.Integer(), nullable=False),
        sa.UniqueConstraint("detection_id", "mmsi", name="uq_sar_candidate_detection_mmsi"),
    )
    op.create_index("ix_sar_candidates_detection_rank", "sar_detection_candidates",
                    ["detection_id", "candidate_rank"])

    op.alter_column("investigation_cases", "mmsi", existing_type=sa.BigInteger(), nullable=True)
    op.add_column(
        "investigation_cases",
        sa.Column("sar_detection_id", sa.BigInteger(),
                  sa.ForeignKey("sar_detections.id", ondelete="RESTRICT"), nullable=True),
    )
    op.create_index("ix_investigation_cases_sar_detection", "investigation_cases", ["sar_detection_id"])

    op.create_table(
        "source_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("checkpoint", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("error", sa.String(300), nullable=True),
        sa.Column("triggered_by", sa.String(50), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("state IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
                           name="ck_source_jobs_state"),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name="ck_source_jobs_progress"),
        sa.CheckConstraint("attempts BETWEEN 0 AND 5", name="ck_source_jobs_attempts"),
    )
    op.create_index("ix_source_jobs_created", "source_jobs", ["created_at"])
    op.create_table(
        "ingest_quarantine",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("source_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("record_index", sa.Integer(), nullable=False),
        sa.Column("source_record_id", sa.String(160), nullable=True),
        sa.Column("reason", sa.String(300), nullable=False),
        sa.Column("record_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ingest_quarantine_job", "ingest_quarantine", ["job_id"])

    op.create_table(
        "report_delivery_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("incident_reports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("report_sha256", sa.String(64), nullable=False),
        sa.Column("recipients", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("idempotency_key", sa.String(120), nullable=False, unique=True),
        sa.Column("state", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(300), nullable=True),
        sa.Column("requested_by", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("state IN ('queued', 'submitted', 'failed', 'cancelled')",
                           name="ck_report_delivery_state"),
        sa.CheckConstraint("attempts BETWEEN 0 AND 3", name="ck_report_delivery_attempts"),
    )
    op.create_index("ix_report_delivery_report_created", "report_delivery_outbox",
                    ["report_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_report_delivery_report_created", table_name="report_delivery_outbox")
    op.drop_table("report_delivery_outbox")
    op.drop_index("ix_ingest_quarantine_job", table_name="ingest_quarantine")
    op.drop_table("ingest_quarantine")
    op.drop_index("ix_source_jobs_created", table_name="source_jobs")
    op.drop_table("source_jobs")
    op.drop_index("ix_investigation_cases_sar_detection", table_name="investigation_cases")
    op.drop_column("investigation_cases", "sar_detection_id")
    # Intentionally refuses while unidentified-object cases exist; inventing an
    # MMSI or deleting them would destroy evidence.
    op.alter_column("investigation_cases", "mmsi", existing_type=sa.BigInteger(), nullable=False)
    op.drop_index("ix_sar_candidates_detection_rank", table_name="sar_detection_candidates")
    op.drop_table("sar_detection_candidates")
    op.drop_index("ix_sar_scene_detection", table_name="sar_detections")
    op.drop_constraint("ck_sar_association_state", "sar_detections", type_="check")
    for name in ("provider_match_result", "license_reference", "publication_at", "association_state"):
        op.drop_column("sar_detections", name)
    op.drop_constraint("ck_mpa_data_mode", "marine_protected_areas", type_="check")
    op.drop_constraint("ck_mpa_rule_verification", "marine_protected_areas", type_="check")
    for name in ("data_mode", "restriction_verification_status", "restriction_seasons",
                 "restriction_activities", "restriction_description", "permitted_use",
                 "citation", "effective_date", "boundary_version", "publisher"):
        op.drop_column("marine_protected_areas", name)
    op.drop_index("ix_alert_notes_alert_created", table_name="alert_notes")
    op.drop_table("alert_notes")
    op.drop_index("ix_alert_records_reviewer_assignee", table_name="alert_records")
    op.drop_constraint("ck_alert_records_reviewer_state", "alert_records", type_="check")
    for name in ("clear_scenario", "resolution_reason", "assigned_to", "reviewer_state"):
        op.drop_column("alert_records", name)
    op.drop_index("uq_vessel_tracks_source_record", table_name="vessel_tracks")
    for name in ("quality_flags", "ingested_at", "source_record_id"):
        op.drop_column("vessel_tracks", name)
