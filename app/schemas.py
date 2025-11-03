from typing import Optional, List, Dict, Any
from pydantic import BaseModel, validator
from datetime import datetime
from pydantic import BaseModel, root_validator

class LocationRequest(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    city_name: Optional[str] = None

    @root_validator
    def check_location(cls, values):
        lat, lon, city_name = values.get("lat"), values.get("lon"), values.get("city_name")

        # Require at least city_name or both coordinates
        if not city_name and (lat is None or lon is None):
            raise ValueError("Provide either city_name or both lat and lon.")

        # If lat is given, lon must also be given
        if lat is not None and lon is None:
            raise ValueError("lon is required when lat is provided")

        return values


class WeatherData(BaseModel):
    temp: float
    feels_like: float
    humidity: int
    pressure: int
    description: str
    icon: str
    wind_speed: float
    wind_deg: int

class HourlyForecast(BaseModel):
    dt: int  # Unix timestamp
    time: str  # ISO format time
    temp: float
    feels_like: float
    humidity: int
    description: str
    icon: str
    wind_speed: float
    pop: float  # Probability of precipitation

class DailyForecast(BaseModel):
    dt: int
    date: str
    temp_min: float
    temp_max: float
    description: str
    icon: str
    humidity: int
    wind_speed: float

class AQIData(BaseModel):
    aqi: int
    pm2_5: float
    pm10: float
    co: float
    no2: float
    o3: float

class CityInfo(BaseModel):
    city_name: str
    latitude: float
    longitude: float
    last_updated: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "city_name": "London, GB",
                "latitude": 51.5074,
                "longitude": -0.1278,
                "last_updated": "2025-11-03T08:00:00Z"
            }
        }

class WeatherResponse(BaseModel):
    city_name: str
    latitude: float
    longitude: float
    current: WeatherData
    hourly: List[HourlyForecast]
    daily: List[DailyForecast]
    aqi: AQIData
    current_weather_updated_at: datetime  # NOT rounded - exact fetch time for current weather
    updated_at: datetime  # For forecast data

    class Config:
        json_schema_extra = {
            "example": {
                "city_name": "London, GB",
                "latitude": 51.5074,
                "longitude": -0.1278,
                "current": {
                    "temp": 15.5,
                    "feels_like": 14.2,
                    "humidity": 72,
                    "pressure": 1013,
                    "description": "clear sky",
                    "icon": "01d",
                    "wind_speed": 3.5,
                    "wind_deg": 180
                },
                "hourly": [],
                "daily": [],
                "aqi": {
                    "aqi": 2,
                    "pm2_5": 12.5,
                    "pm10": 18.3,
                    "co": 230.4,
                    "no2": 15.2,
                    "o3": 45.8
                },
                "current_weather_updated_at": "2025-11-03T08:23:45Z",
                "updated_at": "2025-11-03T08:00:00Z"
            }
        }