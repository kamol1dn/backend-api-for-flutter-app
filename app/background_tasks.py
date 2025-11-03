import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .database import SessionLocal, WeatherCache
from .weather_service import WeatherService

logger = logging.getLogger(__name__)

class WeatherBackgroundTask:
    def __init__(self):
        self.weather_service = WeatherService()
        self.scheduler = AsyncIOScheduler()

    async def fetch_city_forecast(self, city_name: str, lat: float, lon: float, db: Session):
        """Fetch forecast data for a single city (hourly background task)"""
        try:
            logger.info(f"Background forecast fetch for {city_name} started")

            # Fetch forecast and AQI only (current weather is on-demand)
            forecast_data = await self.weather_service.fetch_forecast(lat, lon)
            aqi_data = await self.weather_service.fetch_air_pollution(lat, lon)

            # Get cache entry
            cache_entry = db.query(WeatherCache).filter(
                WeatherCache.city_name == city_name
            ).first()

            if not cache_entry:
                logger.warning(f"Cache entry not found for {city_name}, skipping")
                return

            now = datetime.now(timezone.utc)
            current_time = now.replace(minute=0, second=0, microsecond=0)

            # Rotate the fetches
            cache_entry.fetch_3_data = cache_entry.fetch_2_data
            cache_entry.fetch_3_time = cache_entry.fetch_2_time
            cache_entry.fetch_2_data = cache_entry.fetch_1_data
            cache_entry.fetch_2_time = cache_entry.fetch_1_time
            cache_entry.fetch_1_data = forecast_data
            cache_entry.fetch_1_time = current_time

            cache_entry.aqi_data = aqi_data.dict()
            cache_entry.updated_at = current_time

            # Build hourly and daily forecasts from the 3 fetches
            fetch_data_list = [
                cache_entry.fetch_1_data,
                cache_entry.fetch_2_data,
                cache_entry.fetch_3_data
            ]
            cache_entry.hourly_forecast = [
                h.dict() for h in self.weather_service.build_hourly_forecast(fetch_data_list)
            ]
            cache_entry.daily_forecast = [
                d.dict() for d in self.weather_service.build_daily_forecast(forecast_data)
            ]

            db.commit()
            logger.info(f"Background forecast fetch for {city_name} completed successfully")

        except Exception as e:
            logger.error(f"Error fetching forecast for {city_name}: {e}", exc_info=True)
            db.rollback()

    async def fetch_all_cities(self):
        """Fetch forecasts for all cities in the database (hourly)"""
        db = SessionLocal()
        try:
            # Get all cities
            cities = db.query(WeatherCache).all()
            logger.info(f"Starting background forecast fetch for {len(cities)} cities")

            # Fetch forecast for each city
            tasks = []
            for city in cities:
                task = self.fetch_city_forecast(
                    city.city_name,
                    city.latitude,
                    city.longitude,
                    db
                )
                tasks.append(task)

            # Run all fetches concurrently (with some rate limiting)
            # Process in batches of 5 to avoid overwhelming the API
            batch_size = 5
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i + batch_size]
                await asyncio.gather(*batch, return_exceptions=True)
                # Small delay between batches
                if i + batch_size < len(tasks):
                    await asyncio.sleep(2)

            logger.info("Background forecast fetch completed for all cities")

        except Exception as e:
            logger.error(f"Error in fetch_all_cities: {e}", exc_info=True)
        finally:
            db.close()

    def start(self):
        """Start the background scheduler"""
        # Run at the start of every hour (e.g., 00:00, 01:00, 02:00)
        self.scheduler.add_job(
            self.fetch_all_cities,
            CronTrigger(minute=0),  # Run at minute 0 of every hour
            id='fetch_forecasts',
            name='Fetch forecasts for all cities',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Background scheduler started - will fetch forecasts hourly")

    def stop(self):
        """Stop the background scheduler"""
        self.scheduler.shutdown()
        logger.info("Background scheduler stopped")

# Global instance
background_task_instance = WeatherBackgroundTask()