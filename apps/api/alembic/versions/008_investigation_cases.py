"""Add stable investigation cases and immutable report revision links.

Revision ID: 008
Revises: 007
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "investigation_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("mmsi", sa.BigInteger(), nullable=False),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vessel_assessments.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('open', 'closed')", name="ck_case_status"),
        sa.CheckConstraint("version >= 0", name="ck_case_version"),
    )
    op.create_index("ix_investigation_cases_mmsi", "investigation_cases", ["mmsi"])
    op.create_table(
        "investigation_case_revisions",
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investigation_cases.id"), primary_key=True),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("report_id", sa.BigInteger(), sa.ForeignKey("incident_reports.id"), nullable=False),
        sa.Column("report_sha256", sa.String(64), nullable=False),
        sa.Column("created_by", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("case_id", "report_id", name="uq_case_report"),
        sa.CheckConstraint("version > 0", name="ck_case_revision_version"),
    )


def downgrade():
    op.drop_table("investigation_case_revisions")
    op.drop_index("ix_investigation_cases_mmsi", table_name="investigation_cases")
    op.drop_table("investigation_cases")
