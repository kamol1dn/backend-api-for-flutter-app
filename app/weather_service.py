import os
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from .schemas import WeatherData, HourlyForecast, DailyForecast, AQIData

class WeatherService:
    def __init__(self):
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENWEATHER_API_KEY environment variable is required")
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.geo_url = "https://api.openweathermap.org/geo/1.0"

    async def _make_request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make async HTTP request to OpenWeather API"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            params["appid"] = self.api_key
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def geocode_location(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        city_name: Optional[str] = None
    ) -> Tuple[float, float, str]:
        """
        Geocode location to get standardized city name and coordinates.

        Args:
            lat: Latitude (required if city_name not provided)
            lon: Longitude (required if city_name not provided)
            city_name: City name (alternative to coordinates)

        Returns:
            Tuple of (latitude, longitude, standardized_city_name)
        """
        if not city_name and (lat is None or lon is None):
            raise ValueError("Either city_name or both lat and lon must be provided")

        if city_name:
            # Forward geocoding: city name -> coordinates
            url = f"{self.geo_url}/direct"
            params = {"q": city_name, "limit": 1}
        else:
            # Reverse geocoding: coordinates -> city name
            url = f"{self.geo_url}/reverse"
            params = {"lat": lat, "lon": lon, "limit": 1}

        locations = await self._make_request(url, params)
        if not locations:
            raise ValueError("Location not found")

        location = locations[0]
        standardized_name = f"{location['name']}, {location.get('country', '')}"

        return (
            float(location["lat"]),
            float(location["lon"]),
            standardized_name
        )

    async def fetch_current_weather(self, lat: float, lon: float) -> WeatherData:
        """Fetch current weather data"""
        params = {
            "lat": lat,
            "lon": lon,
            "units": "metric"
        }
        data = await self._make_request(f"{self.base_url}/weather", params)

        return WeatherData(
            temp=data["main"]["temp"],
            feels_like=data["main"]["feels_like"],
            humidity=data["main"]["humidity"],
            pressure=data["main"]["pressure"],
            description=data["weather"][0]["description"],
            icon=data["weather"][0]["icon"],
            wind_speed=data["wind"]["speed"],
            wind_deg=data["wind"]["deg"]
        )

    async def fetch_forecast(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Fetch 5-day/3-hour forecast data from OpenWeather API.
        This is the free tier endpoint that returns data in 3-hour steps.
        """
        params = {
            "lat": lat,
            "lon": lon,
            "units": "metric"
        }
        return await self._make_request(f"{self.base_url}/forecast", params)

    async def fetch_air_pollution(self, lat: float, lon: float) -> AQIData:
        """Fetch air pollution data"""
        params = {
            "lat": lat,
            "lon": lon
        }
        data = await self._make_request(f"{self.base_url}/air_pollution", params)

        components = data["list"][0]["components"]

        return AQIData(
            aqi=data["list"][0]["main"]["aqi"],
            pm2_5=components.get("pm2_5", 0),
            pm10=components.get("pm10", 0),
            co=components.get("co", 0),
            no2=components.get("no2", 0),
            o3=components.get("o3", 0)
        )

    def build_hourly_forecast(self, fetch_data_list: List[Dict[str, Any]]) -> List[HourlyForecast]:
        """
        Build hourly forecast from multiple 3-hour fetches.

        OpenWeather free tier gives 3-hour step data. We fetch every hour and store it.
        By combining the last 3 fetches, we can interpolate or provide more granular data.

        For simplicity, we'll just merge all unique timestamps from the 3 fetches.
        """
        hourly_map = {}

        for fetch_data in fetch_data_list:
            if not fetch_data:
                continue

            for item in fetch_data.get("list", []):
                dt = item["dt"]
                if dt not in hourly_map:
                    hourly_map[dt] = HourlyForecast(
                        dt=dt,
                        time=datetime.fromtimestamp(dt, tz=timezone.utc).isoformat(),
                        temp=item["main"]["temp"],
                        feels_like=item["main"]["feels_like"],
                        humidity=item["main"]["humidity"],
                        description=item["weather"][0]["description"],
                        icon=item["weather"][0]["icon"],
                        wind_speed=item["wind"]["speed"],
                        pop=item.get("pop", 0.0)
                    )

        # Sort by timestamp and return
        return sorted(hourly_map.values(), key=lambda x: x.dt)

    def build_daily_forecast(self, forecast_data: Dict[str, Any]) -> List[DailyForecast]:
        """
        Build daily forecast from 3-hour data.
        Aggregate 3-hour forecasts into daily min/max temperatures.
        """
        daily_map = {}

        for item in forecast_data.get("list", []):
            dt = item["dt"]
            date_obj = datetime.fromtimestamp(dt, tz=timezone.utc).date()
            date_str = date_obj.isoformat()

            temp = item["main"]["temp"]

            if date_str not in daily_map:
                daily_map[date_str] = {
                    "dt": dt,
                    "date": date_str,
                    "temp_min": temp,
                    "temp_max": temp,
                    "description": item["weather"][0]["description"],
                    "icon": item["weather"][0]["icon"],
                    "humidity": item["main"]["humidity"],
                    "wind_speed": item["wind"]["speed"],
                }
            else:
                daily_map[date_str]["temp_min"] = min(daily_map[date_str]["temp_min"], temp)
                daily_map[date_str]["temp_max"] = max(daily_map[date_str]["temp_max"], temp)

        return [
            DailyForecast(**data)
            for data in sorted(daily_map.values(), key=lambda x: x["dt"])
        ]