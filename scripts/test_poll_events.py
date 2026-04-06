"""Poll for events in real-time to verify detection works."""

import json
import logging
import os
import signal
import time

from dotenv import load_dotenv

# Add parent to path so we can import the package
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from birdcamgrabber.tuya_api import TuyaClient
from birdcamgrabber.config import TuyaConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 30  # poll every 30s for this test


def main() -> None:
    load_dotenv()

    config = TuyaConfig(
        access_id=os.environ["TUYA_ACCESS_ID"],
        access_secret=os.environ["TUYA_ACCESS_SECRET"],
        device_id=os.environ["TUYA_DEVICE_ID"],
        region=os.environ.get("TUYA_REGION", "us"),
    )

    client = TuyaClient(config)

    info = client.get_device_info()
    if info:
        logger.info("Device: %s, online: %s", info.get("name"), info.get("online"))

    last_event_time = int(time.time() * 1000)
    total_events = 0

    shutdown = False
    def _sig(s, f):
        nonlocal shutdown
        shutdown = True
    signal.signal(signal.SIGINT, _sig)

    logger.info("Polling for new events every %ds... Ctrl+C to stop.", POLL_INTERVAL)
    logger.info("Trigger motion or wait for a bird to test detection.")

    while not shutdown:
        now_ms = int(time.time() * 1000)
        for event_type in ["1", "9"]:
            events = client.get_event_logs(
                start_time_ms=last_event_time + 1,
                end_time_ms=now_ms,
                event_type=event_type,
                size=10,
            )
            if events:
                for e in events:
                    total_events += 1
                    ts = time.strftime(
                        "%H:%M:%S",
                        time.localtime(e["event_time"] / 1000),
                    )
                    logger.info(
                        "NEW EVENT #%d — type=%s time=%s details=%s",
                        total_events, event_type, ts,
                        json.dumps(e, default=str),
                    )
                newest = max(e["event_time"] for e in events)
                if newest > last_event_time:
                    last_event_time = newest

        time.sleep(POLL_INTERVAL)

    logger.info("Done. %d events detected.", total_events)


if __name__ == "__main__":
    main()
