"""Add AIS dataset fields to vessel_tracks

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update vesseltype enum to include new types
    # First, create a new enum with all values
    op.execute("ALTER TYPE vesseltype ADD VALUE IF NOT EXISTS 'TUG'")
    op.execute("ALTER TYPE vesseltype ADD VALUE IF NOT EXISTS 'PILOT'")
    op.execute("ALTER TYPE vesseltype ADD VALUE IF NOT EXISTS 'SAR'")
    op.execute("ALTER TYPE vesseltype ADD VALUE IF NOT EXISTS 'MILITARY'")
    op.execute("ALTER TYPE vesseltype ADD VALUE IF NOT EXISTS 'SAILING'")
    op.execute("ALTER TYPE vesseltype ADD VALUE IF NOT EXISTS 'PLEASURE'")
    op.execute("ALTER TYPE vesseltype ADD VALUE IF NOT EXISTS 'HIGH_SPEED'")

    # Add new columns to vessel_tracks table
    op.add_column('vessel_tracks', sa.Column('heading', sa.Float(), nullable=True))
    op.add_column('vessel_tracks', sa.Column('vessel_name', sa.String(50), nullable=True))
    op.add_column('vessel_tracks', sa.Column('imo', sa.String(20), nullable=True))
    op.add_column('vessel_tracks', sa.Column('callsign', sa.String(10), nullable=True))
    op.add_column('vessel_tracks', sa.Column('nav_status', sa.Integer(), nullable=True))
    op.add_column('vessel_tracks', sa.Column('length', sa.Float(), nullable=True))
    op.add_column('vessel_tracks', sa.Column('width', sa.Float(), nullable=True))
    op.add_column('vessel_tracks', sa.Column('draft', sa.Float(), nullable=True))
    op.add_column('vessel_tracks', sa.Column('cargo', sa.Integer(), nullable=True))
    op.add_column('vessel_tracks', sa.Column('transceiver_class', sa.String(1), nullable=True))

    # Create indexes for commonly queried fields
    op.create_index('idx_vessel_tracks_imo', 'vessel_tracks', ['imo'])
    op.create_index('idx_vessel_tracks_vessel_name', 'vessel_tracks', ['vessel_name'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_vessel_tracks_vessel_name', table_name='vessel_tracks')
    op.drop_index('idx_vessel_tracks_imo', table_name='vessel_tracks')

    # Drop columns
    op.drop_column('vessel_tracks', 'transceiver_class')
    op.drop_column('vessel_tracks', 'cargo')
    op.drop_column('vessel_tracks', 'draft')
    op.drop_column('vessel_tracks', 'width')
    op.drop_column('vessel_tracks', 'length')
    op.drop_column('vessel_tracks', 'nav_status')
    op.drop_column('vessel_tracks', 'callsign')
    op.drop_column('vessel_tracks', 'imo')
    op.drop_column('vessel_tracks', 'vessel_name')
    op.drop_column('vessel_tracks', 'heading')

    # Note: PostgreSQL doesn't support removing values from ENUMs easily
    # The new enum values will remain in the database
