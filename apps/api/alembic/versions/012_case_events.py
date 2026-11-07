"""Add append-only case status events.

Revision ID: 012
Revises: 011
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "case_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigation_cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event", sa.String(20), nullable=False),
        sa.Column("actor", sa.String(50), nullable=False),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "event IN ('opened', 'closed', 'reopened')", name="ck_case_events_event"
        ),
        sa.CheckConstraint("char_length(actor) > 0", name="ck_case_events_actor"),
    )
    op.create_index("ix_case_events_case_created", "case_events", ["case_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_case_events_case_created", table_name="case_events")
    op.drop_table("case_events")
