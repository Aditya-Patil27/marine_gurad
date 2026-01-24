"""Initial schema with PostGIS support

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2
from sqlalchemy.dialects.postgresql import UUID, ENUM
import uuid

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Enable PostGIS extension
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    
    # Create custom ENUM types
    pollution_type_enum = ENUM('OIL', 'PLASTIC', 'ALGAE', name='pollutiontype', create_type=True)
    vessel_type_enum = ENUM('FISHING', 'CARGO', 'TANKER', 'PASSENGER', 'OTHER', name='vesseltype', create_type=True)
    
    # VesselTrack table
    op.create_table(
        'vessel_tracks',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('mmsi', sa.Integer(), nullable=False, index=True),
        sa.Column('vessel_type', vessel_type_enum, nullable=True),
        sa.Column('flag', sa.String(3), nullable=True),
        sa.Column('location', geoalchemy2.Geometry('POINT', srid=4326), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('is_dark', sa.Boolean(), default=False),
        sa.Column('risk_score', sa.Float(), default=0.0),
        sa.Column('speed', sa.Float(), nullable=True),
        sa.Column('course', sa.Float(), nullable=True),
    )
    op.create_index('idx_vessel_tracks_location', 'vessel_tracks', ['location'], postgresql_using='gist')
    
    # PollutionEvent table
    op.create_table(
        'pollution_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('type', pollution_type_enum, nullable=False),
        sa.Column('severity', sa.Float(), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('zone', geoalchemy2.Geometry('POLYGON', srid=4326), nullable=False),
        sa.Column('image_source', sa.String(500), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
    )
    op.create_index('idx_pollution_events_zone', 'pollution_events', ['zone'], postgresql_using='gist')
    
    # MarineProtectedArea table
    op.create_table(
        'marine_protected_areas',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('designation', sa.String(100), nullable=True),
        sa.Column('boundary', geoalchemy2.Geometry('POLYGON', srid=4326), nullable=False),
        sa.Column('iucn_category', sa.String(10), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
    )
    op.create_index('idx_mpa_boundary', 'marine_protected_areas', ['boundary'], postgresql_using='gist')
    
    # OceanHealthMetric table
    op.create_table(
        'ocean_health_metrics',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('region_id', sa.Integer(), nullable=False, index=True),
        sa.Column('date', sa.Date(), nullable=False, index=True),
        sa.Column('ohi_score', sa.Float(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('ph', sa.Float(), nullable=True),
        sa.Column('salinity', sa.Float(), nullable=True),
        sa.Column('forecasted_score', sa.Float(), nullable=True),
    )
    op.create_index('idx_health_region_date', 'ocean_health_metrics', ['region_id', 'date'])

def downgrade() -> None:
    op.drop_table('ocean_health_metrics')
    op.drop_table('marine_protected_areas')
    op.drop_table('pollution_events')
    op.drop_table('vessel_tracks')
    op.execute('DROP TYPE IF EXISTS vesseltype')
    op.execute('DROP TYPE IF EXISTS pollutiontype')
