"""End-to-end test: detect event, allocate stream, capture burst."""

import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from birdcamgrabber.tuya_api import TuyaClient
from birdcamgrabber.capture import capture_burst
from birdcamgrabber.config import TuyaConfig, CaptureConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    load_dotenv()

    tuya_config = TuyaConfig(
        access_id=os.environ["TUYA_ACCESS_ID"],
        access_secret=os.environ["TUYA_ACCESS_SECRET"],
        device_id=os.environ["TUYA_DEVICE_ID"],
        region=os.environ.get("TUYA_REGION", "us"),
    )
    capture_config = CaptureConfig(fps=2, duration=5)

    client = TuyaClient(tuya_config)
    output_base = Path("test_captures")

    # Allocate stream and capture immediately
    logger.info("Allocating RTSP stream...")
    rtsp_url = client.allocate_rtsp_url()
    if not rtsp_url:
        logger.error("Failed to get RTSP URL")
        sys.exit(1)

    now = datetime.now(tz=timezone.utc)
    event_id = uuid4().hex[:8]
    output_dir = output_base / now.strftime("%Y-%m-%d") / now.strftime(f"%H%M%S-{event_id}")

    logger.info("Capturing burst to %s", output_dir)
    frames = capture_burst(rtsp_url, output_dir, capture_config)
    logger.info("Done! Captured %d frames", len(frames))
    for f in frames:
        logger.info("  %s", f)


if __name__ == "__main__":
    main()
