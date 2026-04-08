"""Dawn/dusk scheduling — determines whether capture should be active."""

import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from astral import LocationInfo
from astral.sun import sun

from .config import LocationConfig

logger = logging.getLogger(__name__)


def get_schedule(location: LocationConfig) -> dict:
    """Return today's sunrise/sunset and active window, all in the configured tz."""
    tz = ZoneInfo(location.timezone)
    loc = LocationInfo(
        name="camera",
        region="",
        timezone="UTC",
        latitude=location.lat,
        longitude=location.lon,
    )
    now_utc = datetime.now(tz=timezone.utc)
    s = sun(loc.observer, date=now_utc.astimezone(tz).date())
    return {
        "sunrise": s["sunrise"].astimezone(tz),
        "sunset": s["sunset"].astimezone(tz),
        "wake": (s["sunrise"] - timedelta(hours=1)).astimezone(tz),
        "sleep": (s["sunset"] + timedelta(hours=1)).astimezone(tz),
    }


def log_schedule(location: LocationConfig) -> None:
    """Log today's sunrise, sunset, and active window in the configured timezone."""
    sched = get_schedule(location)
    fmt = f"%H:%M:%S {location.timezone}"
    logger.info(
        "Today's schedule: sunrise=%s sunset=%s | active %s – %s",
        sched["sunrise"].strftime(fmt),
        sched["sunset"].strftime(fmt),
        sched["wake"].strftime(fmt),
        sched["sleep"].strftime(fmt),
    )


def is_daylight(location: LocationConfig) -> bool:
    """Return True if the current time is within the active window."""
    sched = get_schedule(location)
    now = datetime.now(tz=sched["wake"].tzinfo)
    return sched["wake"] <= now <= sched["sleep"]
