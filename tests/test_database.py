import pytest
from datetime import datetime, timezone, timedelta

from app.database import WeatherCache


def test_needs_fetch_when_no_fetch_time():
    wc = WeatherCache()
    wc.fetch_1_time = None
    assert wc.needs_fetch() is True


def test_needs_fetch_when_old():
    wc = WeatherCache()
    # Set fetch time to 2 hours ago
    wc.fetch_1_time = datetime.now(timezone.utc) - timedelta(hours=2)
    assert wc.needs_fetch() is True


def test_needs_fetch_when_current_hour():
    wc = WeatherCache()
    # Set fetch time to current rounded hour
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    wc.fetch_1_time = now
    assert wc.needs_fetch() is False

