"""Allow investigation cases based on one verified event-only report.

Revision ID: 014
Revises: 013

Existing assessment-backed rows keep their value and foreign key. A case with a
NULL ``assessment_id`` carries its source-bound GFW event evidence through its
report revisions; it does not invent an AIS observation or assessment.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "investigation_cases",
        "assessment_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    # Fails while event-only cases exist; they cannot be represented as NOT NULL.
    # Remove or re-base those cases deliberately before downgrading.
    op.alter_column(
        "investigation_cases",
        "assessment_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
