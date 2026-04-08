"""Dawn/dusk scheduling — determines whether capture should be active."""

import logging
from datetime import datetime, timedelta

from astral import LocationInfo
from astral.sun import sun

from .config import LocationConfig

logger = logging.getLogger(__name__)

_FMT = "%H:%M:%S UTC"


def get_schedule(location: LocationConfig) -> dict:
    """Return today's sunrise/sunset and active window times."""
    loc = LocationInfo(
        name="camera",
        region="",
        timezone="UTC",
        latitude=location.lat,
        longitude=location.lon,
    )
    s = sun(loc.observer, date=datetime.utcnow().date())
    return {
        "sunrise": s["sunrise"],
        "sunset": s["sunset"],
        "wake": s["sunrise"] - timedelta(hours=1),
        "sleep": s["sunset"] + timedelta(hours=1),
    }


def log_schedule(location: LocationConfig) -> None:
    """Log today's sunrise, sunset, and active window."""
    sched = get_schedule(location)
    logger.info(
        "Today's schedule: sunrise=%s sunset=%s | active %s – %s",
        sched["sunrise"].strftime(_FMT),
        sched["sunset"].strftime(_FMT),
        sched["wake"].strftime(_FMT),
        sched["sleep"].strftime(_FMT),
    )


def is_daylight(location: LocationConfig) -> bool:
    """Return True if the current time is within the active window."""
    sched = get_schedule(location)
    now = datetime.utcnow().replace(tzinfo=sched["wake"].tzinfo)
    return sched["wake"] <= now <= sched["sleep"]
