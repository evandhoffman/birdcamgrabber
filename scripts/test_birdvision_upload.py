"""
Force a single capture + BirdVision upload, bypassing the daylight gate.

Usage:
    uv run scripts/test_birdvision_upload.py [config.yaml]
"""
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("test_birdvision_upload")

from birdcamgrabber.config import load_config
from birdcamgrabber.tuya_api import TuyaClient
from birdcamgrabber.capture import capture_clip
from birdcamgrabber.birdvision_client import post_clip

config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
config = load_config(config_path)

logger.info("Allocating RTSP URL…")
client = TuyaClient(config.tuya)
rtsp_url = config.capture.rtsp_url or client.allocate_rtsp_url()
if not rtsp_url:
    logger.error("Could not get RTSP URL — check Tuya credentials")
    sys.exit(1)
logger.info("RTSP URL: %s", rtsp_url[:60] + "…")

now = datetime.now(tz=timezone.utc)
event_id = uuid4().hex[:8]
clip_path = Path(config.output.dir) / now.strftime("%Y-%m-%d") / now.strftime(f"%H%M%S-{event_id}-test.mp4")

result = capture_clip(rtsp_url, clip_path, config.capture)
if result is None:
    logger.error("Capture failed")
    sys.exit(1)

if not config.birdvision.enabled:
    logger.warning("BirdVision not configured (set BIRDVISION_API_TOKEN + BIRDVISION_URL), skipping upload")
    logger.info("Clip saved to %s", clip_path)
    sys.exit(0)

logger.info("Uploading to BirdVision…")
ok = post_clip(
    clip_path,
    now,
    config.birdvision,
    latitude=config.location.lat,
    longitude=config.location.lon,
    source_event_id=f"test-{event_id}",
)
sys.exit(0 if ok else 1)
