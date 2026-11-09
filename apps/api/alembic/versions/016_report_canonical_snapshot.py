"""Preserve canonical report bytes for independently checkable exports.

Revision ID: 016
Revises: 015

Legacy rows intentionally remain NULL: their existing checksum/sign-off stays
unchanged, while reports created after this migration retain their exact UTF-8
canonical JSON bytes.
"""
import sqlalchemy as sa
from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("incident_reports", sa.Column("canonical_snapshot", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("incident_reports", "canonical_snapshot")
