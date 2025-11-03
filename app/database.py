from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from datetime import datetime, timezone
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://weather_user:weather_pass@localhost:5432/weather_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class WeatherCache(Base):
    __tablename__ = "weather_cache"

    id = Column(Integer, primary_key=True, index=True)
    city_name = Column(String, index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Current weather data (independent, 15-minute cache)
    current_weather = Column(JSON)
    current_weather_updated_at = Column(DateTime(timezone=True))  # NOT rounded timestamp

    # Hourly forecast (built from last 3 fetches of 3-hour data)
    hourly_forecast = Column(JSON)

    # Daily forecast
    daily_forecast = Column(JSON)

    # Air quality index
    aqi_data = Column(JSON)

    # Timestamps for each data fetch (hourly, rounded to hour)
    fetch_1_data = Column(JSON)
    fetch_1_time = Column(DateTime(timezone=True))

    fetch_2_data = Column(JSON)
    fetch_2_time = Column(DateTime(timezone=True))

    fetch_3_data = Column(JSON)
    fetch_3_time = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (UniqueConstraint('city_name', name='uix_city_name'),)

    def needs_forecast_fetch(self):
        """
        Determines if hourly/daily forecast should be refreshed.
        Aligns to the top of each hour (UTC-based).
        """
        if not self.fetch_1_time:
            return True

        current_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        return self.fetch_1_time < current_hour

    def needs_current_weather_fetch(self):
        """
        Determines if current weather should be refreshed.
        Uses 15-minute cache expiry.
        """
        if not self.current_weather_updated_at:
            return True

        now = datetime.now(timezone.utc)
        time_diff = now - self.current_weather_updated_at
        return time_diff >= timedelta(minutes=15)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)