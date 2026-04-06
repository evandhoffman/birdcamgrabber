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
from .poller import EventPoller
from .scheduler import is_daylight
from .tuya_api import TuyaClient

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "config.yaml"
DAYLIGHT_CHECK_INTERVAL = 60  # seconds between checks when waiting for dawn
EVENT_POLL_INTERVAL = 30  # seconds between event log polls during daylight


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

    logger.info("Starting birdcamgrabber")

    client: TuyaClient | None = None
    poller: EventPoller | None = None

    try:
        while not shutdown:
            if not is_daylight(config.location):
                if client is not None:
                    logger.info("Sunset — pausing until dawn")
                    client = None
                    poller = None
                time.sleep(DAYLIGHT_CHECK_INTERVAL)
                continue

            # Initialize client on first daylight cycle
            if client is None:
                logger.info("Daylight — connecting to Tuya API")
                client = TuyaClient(config.tuya)
                poller = EventPoller(client, EVENT_POLL_INTERVAL)

                info = client.get_device_info()
                if info:
                    logger.info(
                        "Device '%s' online=%s",
                        info.get("name"),
                        info.get("online"),
                    )

            events = poller.check_for_new_events()

            for event in events:
                now = datetime.now(tz=timezone.utc)
                event_id = uuid4().hex[:8]
                date_dir = now.strftime("%Y-%m-%d")
                burst_dir = now.strftime(f"%H%M%S-{event_id}")
                output_dir = output_base / date_dir / burst_dir

                # Get a fresh RTSP URL for each burst
                rtsp_url = config.capture.rtsp_url or client.allocate_rtsp_url()
                if not rtsp_url:
                    logger.error("No RTSP URL available — skipping capture")
                    continue

                frames = capture_burst(rtsp_url, output_dir, config.capture)
                logger.info("Captured %d frames → %s", len(frames), output_dir)

            time.sleep(EVENT_POLL_INTERVAL)
    finally:
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
