from flask import Flask, render_template_string, request, redirect, url_for, flash, session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
import os
import asyncio
import httpx
from functools import wraps

# Import your database models
from .database import DATABASE_URL, WeatherCache, Base

app = Flask(__name__)
app.secret_key = os.getenv("ADMIN_SECRET_KEY", "change-this-secret-key-in-production")

# Admin credentials from environment variables
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # Change this in production!

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# HTML Templates
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Login - Weather Cache</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 400px;
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: #333;
            font-size: 14px;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 6px;
            box-sizing: border-box;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus,
        input[type="password"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            width: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 14px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
        }
        button:active {
            transform: translateY(0);
        }
        .alert {
            padding: 12px;
            margin-bottom: 20px;
            border-radius: 6px;
            font-size: 14px;
        }
        .alert-error {
            background-color: #fee;
            border: 1px solid #fcc;
            color: #c33;
        }
        .icon {
            text-align: center;
            font-size: 48px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="icon">🔐</div>
        <h1>Admin Login</h1>
        <p class="subtitle">Weather Cache Admin Panel</p>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST" action="{{ url_for('login') }}">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required autofocus>
            </div>
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Weather Cache Admin Panel</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
            margin: 0;
        }
        .logout-btn {
            background-color: #f44336;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            font-size: 14px;
        }
        .logout-btn:hover {
            background-color: #da190b;
        }
        .stats {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
        }
        .stat-box {
            text-align: center;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 5px;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #4CAF50;
        }
        .stat-label {
            color: #666;
            margin-top: 5px;
            font-size: 0.9em;
        }
        .add-city-form {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #333;
        }
        input[type="text"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #45a049;
        }
        .btn-danger {
            background-color: #f44336;
        }
        .btn-danger:hover {
            background-color: #da190b;
        }
        table {
            width: 100%;
            background: white;
            border-collapse: collapse;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        th {
            background-color: #4CAF50;
            color: white;
            padding: 12px 10px;
            text-align: left;
            font-size: 0.95em;
        }
        td {
            padding: 10px;
            border-bottom: 1px solid #ddd;
            font-size: 0.9em;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .status {
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 0.85em;
            font-weight: bold;
            display: inline-block;
        }
        .status-ready {
            background-color: #4CAF50;
            color: white;
        }
        .status-partial {
            background-color: #ff9800;
            color: white;
        }
        .status-new {
            background-color: #2196F3;
            color: white;
        }
        .status-fresh {
            background-color: #4CAF50;
            color: white;
        }
        .status-stale {
            background-color: #ff9800;
            color: white;
        }
        .status-expired {
            background-color: #f44336;
            color: white;
        }
        .alert {
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
        .alert-success {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .alert-error {
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        .timestamp {
            font-size: 0.85em;
            color: #666;
        }
        .time-diff {
            font-size: 0.8em;
            color: #999;
            font-style: italic;
        }
        .cache-info {
            display: flex;
            flex-direction: column;
            gap: 3px;
        }
        .legend {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .legend h3 {
            margin-top: 0;
            color: #333;
            font-size: 1.1em;
        }
        .legend-items {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>⛅ Weather Cache Admin Panel</h1>
        <a href="{{ url_for('logout') }}" class="logout-btn">Logout</a>
    </div>
    
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    
    <div class="stats">
        <h2>Statistics</h2>
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-number">{{ stats.total_cities }}</div>
                <div class="stat-label">Total Cities</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{{ stats.ready_cities }}</div>
                <div class="stat-label">Ready (3+ fetches)</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{{ stats.partial_cities }}</div>
                <div class="stat-label">Partial (1-2 fetches)</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{{ stats.new_cities }}</div>
                <div class="stat-label">New (0 fetches)</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{{ stats.fresh_current }}</div>
                <div class="stat-label">Fresh Current (&lt;15m)</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{{ stats.stale_current }}</div>
                <div class="stat-label">Stale Current (&gt;15m)</div>
            </div>
        </div>
    </div>
    
    <div class="legend">
        <h3>📋 Cache Status Legend</h3>
        <div class="legend-items">
            <div class="legend-item">
                <span class="status status-fresh">Fresh</span>
                <span>Current weather &lt; 15 min old</span>
            </div>
            <div class="legend-item">
                <span class="status status-stale">Stale</span>
                <span>Current weather &gt; 15 min old</span>
            </div>
            <div class="legend-item">
                <span class="status status-expired">Expired</span>
                <span>No current weather cached</span>
            </div>
            <div class="legend-item">
                <span class="status status-ready">Ready</span>
                <span>Forecast: 3+ hourly fetches</span>
            </div>
            <div class="legend-item">
                <span class="status status-partial">Partial</span>
                <span>Forecast: 1-2 hourly fetches</span>
            </div>
            <div class="legend-item">
                <span class="status status-new">New</span>
                <span>Forecast: 0 fetches</span>
            </div>
        </div>
    </div>
    
    <div class="add-city-form">
        <h2>Add New City</h2>
        <form method="POST" action="{{ url_for('add_city') }}">
            <div class="form-group">
                <label for="city_name">City Name:</label>
                <input type="text" id="city_name" name="city_name" 
                       placeholder="e.g., London, GB or Tokyo, JP" required>
                <small style="color: #666;">Format: "City Name, Country Code" (e.g., "New York, US")</small>
            </div>
            <button type="submit">Add City</button>
        </form>
    </div>
    
    <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h2>Cached Cities</h2>
        <table>
            <thead>
                <tr>
                    <th>City Name</th>
                    <th>Coordinates</th>
                    <th>Current Weather</th>
                    <th>Forecast Status</th>
                    <th>Forecast Fetches</th>
                    <th>Last Forecast Update</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for city in cities %}
                <tr>
                    <td><strong>{{ city.city_name }}</strong></td>
                    <td>{{ "%.4f"|format(city.latitude) }}, {{ "%.4f"|format(city.longitude) }}</td>
                    <td>
                        <div class="cache-info">
                            <span class="status status-{{ city.current_status_class }}">
                                {{ city.current_status_text }}
                            </span>
                            {% if city.current_weather_updated_at %}
                                <span class="timestamp">{{ city.current_weather_updated_at.strftime('%H:%M:%S UTC') }}</span>
                                <span class="time-diff">{{ city.current_age }}</span>
                            {% else %}
                                <span class="timestamp">Never</span>
                            {% endif %}
                        </div>
                    </td>
                    <td>
                        <span class="status status-{{ city.forecast_status_class }}">
                            {{ city.forecast_status_text }}
                        </span>
                    </td>
                    <td>{{ city.fetch_count }} / 3</td>
                    <td class="timestamp">
                        {% if city.updated_at %}
                            {{ city.updated_at.strftime('%Y-%m-%d %H:%M UTC') }}
                        {% else %}
                            Never
                        {% endif %}
                    </td>
                    <td>
                        <form method="POST" action="{{ url_for('delete_city', city_id=city.id) }}" 
                              style="display: inline;"
                              onsubmit="return confirm('Delete {{ city.city_name }}?');">
                            <button type="submit" class="btn-danger">Delete</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

def get_forecast_status(city):
    """Determine the forecast status based on fetch data"""
    fetch_count = 0
    if city.fetch_1_time:
        fetch_count += 1
    if city.fetch_2_time:
        fetch_count += 1
    if city.fetch_3_time:
        fetch_count += 1

    if fetch_count >= 3:
        status_text = "Ready"
        status_class = "ready"
    elif fetch_count > 0:
        status_text = "Partial"
        status_class = "partial"
    else:
        status_text = "New"
        status_class = "new"

    return {
        'fetch_count': fetch_count,
        'forecast_status_text': status_text,
        'forecast_status_class': status_class
    }

def get_current_weather_status(city):
    """Determine the current weather cache status (15-minute expiry)"""
    if not city.current_weather_updated_at:
        return {
            'current_status_text': 'Expired',
            'current_status_class': 'expired',
            'current_age': 'Never fetched'
        }

    now = datetime.now(timezone.utc)
    time_diff = now - city.current_weather_updated_at
    minutes_old = int(time_diff.total_seconds() / 60)

    if minutes_old < 15:
        status_text = "Fresh"
        status_class = "fresh"
    else:
        status_text = "Stale"
        status_class = "stale"

    # Format age
    if minutes_old < 1:
        age_text = "< 1 min ago"
    elif minutes_old < 60:
        age_text = f"{minutes_old} min ago"
    else:
        hours = minutes_old // 60
        mins = minutes_old % 60
        age_text = f"{hours}h {mins}m ago"

    return {
        'current_status_text': status_text,
        'current_status_class': status_class,
        'current_age': age_text
    }

async def geocode_city(city_name: str):
    """Geocode city name to get coordinates"""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        raise ValueError("OPENWEATHER_API_KEY not set")

    url = "https://api.openweathermap.org/geo/1.0/direct"
    params = {
        "q": city_name,
        "limit": 1,
        "appid": api_key
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        locations = response.json()

        if not locations:
            raise ValueError(f"City '{city_name}' not found")

        location = locations[0]
        standardized_name = f"{location['name']}, {location.get('country', '')}"

        return {
            'name': standardized_name,
            'lat': float(location['lat']),
            'lon': float(location['lon'])
        }

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            flash('Successfully logged in!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')

    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Main admin page"""
    db = SessionLocal()
    try:
        cities = db.query(WeatherCache).order_by(WeatherCache.city_name).all()

        # Add status info to each city
        cities_with_status = []
        for city in cities:
            city_dict = {
                'id': city.id,
                'city_name': city.city_name,
                'latitude': city.latitude,
                'longitude': city.longitude,
                'current_weather_updated_at': city.current_weather_updated_at,
                'updated_at': city.updated_at,
            }
            # Get forecast status
            city_dict.update(get_forecast_status(city))
            # Get current weather status
            city_dict.update(get_current_weather_status(city))
            cities_with_status.append(city_dict)

        # Calculate stats
        total_cities = len(cities)
        ready_cities = sum(1 for c in cities_with_status if c['fetch_count'] >= 3)
        partial_cities = sum(1 for c in cities_with_status if 0 < c['fetch_count'] < 3)
        new_cities = sum(1 for c in cities_with_status if c['fetch_count'] == 0)
        fresh_current = sum(1 for c in cities_with_status if c['current_status_class'] == 'fresh')
        stale_current = sum(1 for c in cities_with_status if c['current_status_class'] in ['stale', 'expired'])

        stats = {
            'total_cities': total_cities,
            'ready_cities': ready_cities,
            'partial_cities': partial_cities,
            'new_cities': new_cities,
            'fresh_current': fresh_current,
            'stale_current': stale_current
        }

        return render_template_string(ADMIN_TEMPLATE, cities=cities_with_status, stats=stats)
    finally:
        db.close()

@app.route('/add', methods=['POST'])
@login_required
def add_city():
    """Add a new city to the cache"""
    city_name = request.form.get('city_name', '').strip()

    if not city_name:
        flash('City name is required', 'error')
        return redirect(url_for('index'))

    db = SessionLocal()
    try:
        # Geocode the city
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        city_info = loop.run_until_complete(geocode_city(city_name))
        loop.close()

        # Check if city already exists
        existing = db.query(WeatherCache).filter(
            WeatherCache.city_name == city_info['name']
        ).first()

        if existing:
            flash(f"City '{city_info['name']}' already exists in the cache", 'error')
            return redirect(url_for('index'))

        # Add new city (empty cache, will be populated on first request or hourly fetch)
        new_city = WeatherCache(
            city_name=city_info['name'],
            latitude=city_info['lat'],
            longitude=city_info['lon'],
            current_weather={},
            aqi_data={}
        )
        db.add(new_city)
        db.commit()

        flash(f"Successfully added '{city_info['name']}'. Current weather will be fetched on first request. Forecast will be updated on the next hourly fetch.", 'success')
        return redirect(url_for('index'))

    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Error adding city: {str(e)}", 'error')
        return redirect(url_for('index'))
    finally:
        db.close()

@app.route('/delete/<int:city_id>', methods=['POST'])
@login_required
def delete_city(city_id):
    """Delete a city from the cache"""
    db = SessionLocal()
    try:
        city = db.query(WeatherCache).filter(WeatherCache.id == city_id).first()
        if city:
            city_name = city.city_name
            db.delete(city)
            db.commit()
            flash(f"Successfully deleted '{city_name}'", 'success')
        else:
            flash('City not found', 'error')
        return redirect(url_for('index'))
    finally:
        db.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)