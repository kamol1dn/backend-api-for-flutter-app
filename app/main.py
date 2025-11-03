from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional, List
import logging
from datetime import datetime, timezone

from .database import SessionLocal, WeatherCache, init_db
from .schemas import LocationRequest, WeatherResponse, CityInfo
from .weather_service import WeatherService
from .background_tasks import background_task_instance

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Weather Caching API",
    description="Backend API for caching weather data from OpenWeather API",
    version="1.0.0"
)

# CORS middleware for Flutter app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this to your Flutter app's domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")

    # Start background task scheduler
    logger.info("Starting background weather fetch scheduler...")
    background_task_instance.start()
    logger.info("Background scheduler started")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down background scheduler...")
    background_task_instance.stop()
    logger.info("Background scheduler stopped")

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize weather service
weather_service = WeatherService()

@app.get("/api/cities", response_model=List[CityInfo])
async def get_saved_cities(db: Session = Depends(get_db)):
    """
    Get list of all saved cities in the database.

    Returns a list of cities with their basic information:
    - city_name: Standardized city name
    - latitude: City latitude
    - longitude: City longitude
    - last_updated: Last time the city data was updated
    """
    try:
        cities = db.query(WeatherCache).all()

        return [
            CityInfo(
                city_name=city.city_name,
                latitude=city.latitude,
                longitude=city.longitude,
                last_updated=city.updated_at or city.created_at
            )
            for city in cities
        ]
    except Exception as e:
        logger.error(f"Error fetching cities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching cities: {str(e)}")

@app.post("/api/weather", response_model=WeatherResponse)
async def get_weather(
        request: LocationRequest,
        db: Session = Depends(get_db)
):
    """
    Get weather data for a location (by city name or coordinates).

    - **city_name**: City name (e.g., "London" or "London, GB")
    - **lat**: Latitude (alternative to city_name)
    - **lon**: Longitude (required if lat is provided)

    Returns current weather, hourly forecast, daily forecast, and AQI data.
    - Current weather: cached for 15 minutes (on-demand)
    - Forecasts: cached hourly (background task)
    """
    try:
        # Step 1: Try to find existing cache entry first to avoid geocoding
        cache_entry = None
        lat, lon, city_name = None, None, None

        if request.city_name:
            # Try exact match first
            cache_entry = db.query(WeatherCache).filter(
                WeatherCache.city_name == request.city_name
            ).first()

            if cache_entry:
                # Found in cache, use stored coordinates
                lat = cache_entry.latitude
                lon = cache_entry.longitude
                city_name = cache_entry.city_name
                logger.info(f"Found cached coordinates for {city_name}: ({lat}, {lon})")
            else:
                # Not in cache, need to geocode
                logger.info(f"Cache miss, geocoding city: {request.city_name}")
                lat, lon, city_name = await weather_service.geocode_location(
                    city_name=request.city_name
                )
                logger.info(f"Geocoded to: {city_name} ({lat}, {lon})")
        else:
            # Coordinates provided, do reverse geocoding
            logger.info(f"Reverse geocoding coordinates: ({request.lat}, {request.lon})")
            lat, lon, city_name = await weather_service.geocode_location(
                lat=request.lat,
                lon=request.lon
            )
            logger.info(f"Reverse geocoded to: {city_name} ({lat}, {lon})")

            # Check if this city is already cached
            cache_entry = db.query(WeatherCache).filter(
                WeatherCache.city_name == city_name
            ).first()

        now = datetime.now(timezone.utc)
        current_hour = now.replace(minute=0, second=0, microsecond=0)

        # Step 2: Handle new cache entry or existing cache entry
        if not cache_entry:
            logger.info(f"No cache entry for {city_name}, creating new entry...")

            # Fetch all data for new city
            current_weather = await weather_service.fetch_current_weather(lat, lon)
            forecast_data = await weather_service.fetch_forecast(lat, lon)
            aqi_data = await weather_service.fetch_air_pollution(lat, lon)

            cache_entry = WeatherCache(
                city_name=city_name,
                latitude=lat,
                longitude=lon,
                current_weather=current_weather.dict(),
                current_weather_updated_at=now,  # NOT rounded
                aqi_data=aqi_data.dict(),
                fetch_1_data=forecast_data,
                fetch_1_time=current_hour,  # Rounded to hour
            )
            db.add(cache_entry)

            # Build forecasts
            fetch_data_list = [cache_entry.fetch_1_data, None, None]
            cache_entry.hourly_forecast = [
                h.dict() for h in weather_service.build_hourly_forecast(fetch_data_list)
            ]
            cache_entry.daily_forecast = [
                d.dict() for d in weather_service.build_daily_forecast(forecast_data)
            ]

            db.commit()
            db.refresh(cache_entry)
            logger.info(f"Created new cache entry for {city_name}")

        else:
            # Step 3: Check if current weather needs update (15-minute cache)
            needs_current_update = cache_entry.needs_current_weather_fetch()

            if needs_current_update:
                logger.info(f"Current weather expired for {city_name} (>15 min), fetching new data...")
                current_weather = await weather_service.fetch_current_weather(lat, lon)
                cache_entry.current_weather = current_weather.dict()
                cache_entry.current_weather_updated_at = now  # NOT rounded
                db.commit()
                db.refresh(cache_entry)
                logger.info(f"Updated current weather for {city_name}")
            else:
                logger.info(f"Current weather cache hit for {city_name} (fresh within 15 min)")

            # Step 4: Check if forecast needs update (hourly, handled by background task mostly)
            needs_forecast_update = cache_entry.needs_forecast_fetch()

            if needs_forecast_update:
                logger.info(f"Forecast expired for {city_name}, fetching new data...")
                forecast_data = await weather_service.fetch_forecast(lat, lon)
                aqi_data = await weather_service.fetch_air_pollution(lat, lon)

                # Rotate fetches
                cache_entry.fetch_3_data = cache_entry.fetch_2_data
                cache_entry.fetch_3_time = cache_entry.fetch_2_time
                cache_entry.fetch_2_data = cache_entry.fetch_1_data
                cache_entry.fetch_2_time = cache_entry.fetch_1_time
                cache_entry.fetch_1_data = forecast_data
                cache_entry.fetch_1_time = current_hour

                cache_entry.aqi_data = aqi_data.dict()

                # Rebuild forecasts
                fetch_data_list = [
                    cache_entry.fetch_1_data,
                    cache_entry.fetch_2_data,
                    cache_entry.fetch_3_data
                ]
                cache_entry.hourly_forecast = [
                    h.dict() for h in weather_service.build_hourly_forecast(fetch_data_list)
                ]
                cache_entry.daily_forecast = [
                    d.dict() for d in weather_service.build_daily_forecast(forecast_data)
                ]

                db.commit()
                db.refresh(cache_entry)
                logger.info(f"Updated forecast for {city_name}")

        # Step 5: Build response from cache
        return WeatherResponse(
            city_name=cache_entry.city_name,
            latitude=cache_entry.latitude,
            longitude=cache_entry.longitude,
            current=cache_entry.current_weather,
            hourly=[h for h in cache_entry.hourly_forecast] if cache_entry.hourly_forecast else [],
            daily=[d for d in cache_entry.daily_forecast] if cache_entry.daily_forecast else [],
            aqi=cache_entry.aqi_data,
            current_weather_updated_at=cache_entry.current_weather_updated_at,  # NOT rounded timestamp
            updated_at=cache_entry.updated_at or current_hour
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "Weather Caching API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }