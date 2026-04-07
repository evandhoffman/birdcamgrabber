"""Dawn/dusk scheduling — determines whether capture should be active."""

import logging
from datetime import datetime, timedelta

from astral import LocationInfo
from astral.sun import sun

from .config import LocationConfig

logger = logging.getLogger(__name__)


def is_daylight(location: LocationConfig) -> bool:
    """Return True if the current local time is between sunrise and sunset."""
    loc = LocationInfo(
        name="camera",
        region="",
        timezone="UTC",
        latitude=location.lat,
        longitude=location.lon,
    )
    s = sun(loc.observer, date=datetime.utcnow().date())
    now = datetime.utcnow().replace(tzinfo=s["sunrise"].tzinfo)
    window_start = s["sunrise"] - timedelta(hours=1)
    window_end = s["sunset"] + timedelta(hours=1)
    active = window_start <= now <= window_end
    if not active:
        logger.debug(
            "Outside active hours (start=%s, end=%s)",
            window_start.isoformat(),
            window_end.isoformat(),
        )
    return active
