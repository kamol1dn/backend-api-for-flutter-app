# Weather Caching Backend API

This is a vibecoded backend API for my flutter weather app.
This repo is used deployement to server.
FastAPI-based weather caching backend for Flutter weather app. Intelligently caches OpenWeather API data hourly per city to avoid rate limits.

Idk why, but you can use this repo but why?
I hope i did not hardcode my api key.

## Features

- **Smart Geocoding**: Converts coordinates → city names for consistent caching
- **Hourly Caching**: Fetches data once per hour per city, stores last 3 fetches
- **Comprehensive Data**: Current weather, hourly forecast, daily forecast, and AQI
- **Free Tier Optimized**: Works with OpenWeather's 3-hour forecast data, builds hourly from multiple fetches
- **Docker Ready**: PostgreSQL + FastAPI with health checks

## Quick Start

1. **Set up environment**:
```bash
cp .env.example .env
# Edit .env and add your OpenWeather API key
```

2. **Run with Docker**:
```bash
docker-compose up --build
```

3. **Access the API**:
- API: `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

## API Endpoints

### `POST /api/weather`
Get weather data for a location. Accepts either city name or coordinates.

**Request with coordinates:**
```json
{
  "lat": 51.5074,
  "lon": -0.1278
}
```

**Request with city name:**
```json
{
  "city_name": "London"
}
```

**Response:**
```json
{
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
  "hourly": [
    {
      "dt": 1699012800,
      "time": "2025-11-03T12:00:00+00:00",
      "temp": 16.2,
      "feels_like": 15.1,
      "humidity": 68,
      "description": "few clouds",
      "icon": "02d",
      "wind_speed": 4.1,
      "pop": 0.0
    }
  ],
  "daily": [
    {
      "dt": 1699012800,
      "date": "2025-11-03",
      "temp_min": 12.3,
      "temp_max": 18.7,
      "description": "partly cloudy",
      "icon": "02d",
      "humidity": 65,
      "wind_speed": 3.8
    }
  ],
  "aqi": {
    "aqi": 2,
    "pm2_5": 12.5,
    "pm10": 18.3,
    "co": 230.4,
    "no2": 15.2,
    "o3": 45.8
  },
  "updated_at": "2025-11-03T08:00:00+00:00"
}
```

### `GET /api/health`
Health check endpoint.

### `GET /`
API information and links.

## How It Works

1. **User Request**: Flutter app sends coordinates or city name
2. **Geocoding**: Backend always geocodes to standardized city name (e.g., "London, GB")
3. **Cache Check**: Looks up city in database
4. **Smart Fetching**:
   - If cache is older than 1 hour, fetches new data from OpenWeather
   - Stores last 3 fetches (each has 3-hour step data)
   - Builds hourly forecast by combining the 3 fetches
5. **Response**: Returns cached data with city name, ensuring consistency

**Why geocode coordinates?**
- Users at different coordinates in the same city share the same cache
- Reduces API calls dramatically
- Consistent city naming across all requests

## Architecture

```
Flutter App → FastAPI → PostgreSQL
              ↓
         OpenWeather API (hourly fetches)
```

**Tech Stack:**
- **FastAPI**: Modern async Python web framework
- **PostgreSQL**: Reliable data caching with JSON columns
- **SQLAlchemy**: ORM for database operations
- **Docker**: Containerization with health checks
- **httpx**: Async HTTP client for OpenWeather API

**Database Schema:**
- `city_name`: Unique cache key
- `current_weather`: Latest current weather JSON
- `hourly_forecast`: Built from last 3 fetches
- `daily_forecast`: Aggregated daily data
- `aqi_data`: Air quality index data
- `fetch_1/2/3_data`: Rolling window of last 3 API fetches
- `updated_at`: Timestamp for cache expiration (1 hour)

## Development

**Run locally without Docker:**
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://weather_user:weather_pass@localhost:5432/weather_db"
export OPENWEATHER_API_KEY="your_key"

# Run the server
uvicorn app.main:app --reload
```

**Database migrations:**
```bash
# Create migration
docker-compose exec app alembic revision --autogenerate -m "description"

# Apply migrations
docker-compose exec app alembic upgrade head
```

**View logs:**
```bash
docker-compose logs -f app
```

## Configuration

Environment variables in `.env`:
- `OPENWEATHER_API_KEY`: Your OpenWeather API key (required)
- `DATABASE_URL`: PostgreSQL connection string (auto-configured in Docker)

## License

MIT