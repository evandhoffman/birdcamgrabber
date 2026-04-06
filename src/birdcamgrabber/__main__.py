"""Entry point: python -m birdcamgrabber"""

import logging
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .capture import capture_burst
from .config import load_config
from .scheduler import is_daylight
from .tuya_listener import start_listener

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "config.yaml"
POLL_INTERVAL = 60  # seconds between daylight checks when sleeping at night


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    config_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG_PATH
    config = load_config(config_path)

    output_base = Path(config.output.dir)
    output_base.mkdir(parents=True, exist_ok=True)

    shutdown = False

    def _handle_signal(signum, _frame):
        nonlocal shutdown
        logger.info("Received signal %d, shutting down…", signum)
        shutdown = True

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    def on_bird_event(msg: dict) -> None:
        if not is_daylight(config.location):
            logger.info("Ignoring event outside daylight hours")
            return

        now = datetime.now(tz=timezone.utc)
        event_id = uuid4().hex[:8]
        date_dir = now.strftime("%Y-%m-%d")
        burst_dir = now.strftime(f"%H%M%S-{event_id}")
        output_dir = output_base / date_dir / burst_dir

        rtsp_url = config.capture.rtsp_url
        if not rtsp_url:
            logger.error("No RTSP URL configured — skipping capture")
            return

        frames = capture_burst(rtsp_url, output_dir, config.capture)
        logger.info("Captured %d frames → %s", len(frames), output_dir)

    logger.info("Starting birdcamgrabber")

    mq = None
    try:
        while not shutdown:
            if not is_daylight(config.location):
                if mq is not None:
                    logger.info("Sunset — pausing listener")
                    mq.stop()
                    mq = None
                logger.info(
                    "Waiting for daylight (checking every %ds)…", POLL_INTERVAL
                )
                time.sleep(POLL_INTERVAL)
                continue

            if mq is None:
                logger.info("Sunrise — starting listener")
                mq = start_listener(config.tuya, on_bird_event)

            time.sleep(POLL_INTERVAL)
    finally:
        if mq is not None:
            logger.info("Stopping MQTT listener")
            mq.stop()

    logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
