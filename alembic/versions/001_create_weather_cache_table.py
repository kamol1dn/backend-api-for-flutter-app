"""create weather cache table

Revision ID: 001
Revises: 
Create Date: 2023-11-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('weather_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('city_name', sa.String(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('weather_data', sa.JSON(), nullable=True),
        sa.Column('data_type', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_weather_cache_city_name'), 'weather_cache', ['city_name'], unique=False)
    op.create_index(op.f('ix_weather_cache_id'), 'weather_cache', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_weather_cache_id'), table_name='weather_cache')
    op.drop_index(op.f('ix_weather_cache_city_name'), table_name='weather_cache')
    op.drop_table('weather_cache')