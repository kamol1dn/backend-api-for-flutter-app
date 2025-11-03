"""update weather cache schema

Revision ID: 002
Revises: 001
Create Date: 2025-11-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Drop old columns that are no longer used
    op.drop_column('weather_cache', 'weather_data')
    op.drop_column('weather_cache', 'data_type')

    # Add new columns for current weather (15-minute cache)
    op.add_column('weather_cache', sa.Column('current_weather', sa.JSON(), nullable=True))
    op.add_column('weather_cache', sa.Column('current_weather_updated_at', sa.DateTime(timezone=True), nullable=True))

    # Add columns for hourly and daily forecasts
    op.add_column('weather_cache', sa.Column('hourly_forecast', sa.JSON(), nullable=True))
    op.add_column('weather_cache', sa.Column('daily_forecast', sa.JSON(), nullable=True))

    # Add column for air quality data
    op.add_column('weather_cache', sa.Column('aqi_data', sa.JSON(), nullable=True))

    # Add columns for the 3 rotating forecast fetches
    op.add_column('weather_cache', sa.Column('fetch_1_data', sa.JSON(), nullable=True))
    op.add_column('weather_cache', sa.Column('fetch_1_time', sa.DateTime(timezone=True), nullable=True))

    op.add_column('weather_cache', sa.Column('fetch_2_data', sa.JSON(), nullable=True))
    op.add_column('weather_cache', sa.Column('fetch_2_time', sa.DateTime(timezone=True), nullable=True))

    op.add_column('weather_cache', sa.Column('fetch_3_data', sa.JSON(), nullable=True))
    op.add_column('weather_cache', sa.Column('fetch_3_time', sa.DateTime(timezone=True), nullable=True))

    # Make latitude and longitude non-nullable
    op.alter_column('weather_cache', 'latitude', nullable=False)
    op.alter_column('weather_cache', 'longitude', nullable=False)
    op.alter_column('weather_cache', 'city_name', nullable=False)

    # Add unique constraint on city_name
    op.create_unique_constraint('uix_city_name', 'weather_cache', ['city_name'])


def downgrade():
    # Drop the unique constraint
    op.drop_constraint('uix_city_name', 'weather_cache', type_='unique')

    # Drop new columns
    op.drop_column('weather_cache', 'fetch_3_time')
    op.drop_column('weather_cache', 'fetch_3_data')
    op.drop_column('weather_cache', 'fetch_2_time')
    op.drop_column('weather_cache', 'fetch_2_data')
    op.drop_column('weather_cache', 'fetch_1_time')
    op.drop_column('weather_cache', 'fetch_1_data')
    op.drop_column('weather_cache', 'aqi_data')
    op.drop_column('weather_cache', 'daily_forecast')
    op.drop_column('weather_cache', 'hourly_forecast')
    op.drop_column('weather_cache', 'current_weather_updated_at')
    op.drop_column('weather_cache', 'current_weather')

    # Add back old columns
    op.add_column('weather_cache', sa.Column('data_type', sa.String(), nullable=True))
    op.add_column('weather_cache', sa.Column('weather_data', sa.JSON(), nullable=True))

    # Make columns nullable again
    op.alter_column('weather_cache', 'city_name', nullable=True)
    op.alter_column('weather_cache', 'longitude', nullable=True)
    op.alter_column('weather_cache', 'latitude', nullable=True)