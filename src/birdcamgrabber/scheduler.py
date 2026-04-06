"""Dawn/dusk scheduling — determines whether capture should be active."""

import logging
from datetime import datetime

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
    daylight = s["sunrise"] <= now <= s["sunset"]
    if not daylight:
        logger.debug(
            "Outside daylight hours (sunrise=%s, sunset=%s)",
            s["sunrise"].isoformat(),
            s["sunset"].isoformat(),
        )
    return daylight
