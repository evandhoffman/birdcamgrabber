"""Client for posting captured clips to BirdVision."""

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from .config import BirdVisionConfig

logger = logging.getLogger(__name__)

_RETRY_DELAYS = (10, 20, 30)  # seconds between attempts


def post_clip(
    clip_path: Path,
    captured_at: datetime,
    config: BirdVisionConfig,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
    source_event_id: str | None = None,
) -> bool:
    """POST a video clip to BirdVision's /api/v1/videos endpoint.

    Retries on transient failures with delays of 10 s, 20 s, 30 s before
    giving up.  Returns True if accepted (202), False after all retries
    are exhausted.
    """
    if not config.enabled:
        logger.debug("BirdVision integration disabled, skipping upload")
        return False

    url = config.url.rstrip("/") + "/api/v1/videos"
    headers = {"X-API-Token": config.api_token}
    ts = captured_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    data: dict[str, str] = {
        "captured_at": ts,
        "source": "birdcamgrabber",
    }
    if latitude is not None:
        data["latitude"] = str(latitude)
    if longitude is not None:
        data["longitude"] = str(longitude)
    if source_event_id:
        data["source_event_id"] = source_event_id

    for attempt, delay in enumerate((*_RETRY_DELAYS, None), start=1):
        try:
            with clip_path.open("rb") as fh:
                resp = requests.post(
                    url,
                    headers=headers,
                    files={"file": (clip_path.name, fh, "video/mp4")},
                    data=data,
                    timeout=60,
                )
            if resp.status_code == 202:
                body = resp.json()
                logger.info(
                    "BirdVision accepted clip: job_id=%s url=%s",
                    body.get("job_id"),
                    config.url.rstrip("/") + body.get("url", ""),
                )
                return True
            logger.warning(
                "BirdVision returned %d (attempt %d): %s",
                resp.status_code,
                attempt,
                resp.text[:200],
            )
        except requests.RequestException as exc:
            logger.warning("BirdVision request failed (attempt %d): %s", attempt, exc)

        if delay is None:
            break
        logger.info("Retrying BirdVision upload in %ds…", delay)
        time.sleep(delay)

    logger.error("BirdVision upload failed after %d attempts, giving up", len(_RETRY_DELAYS) + 1)
    return False
