"""Entry point: python -m birdcamgrabber"""

import logging
import os
import queue
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .birdvision_client import post_clip
from .capture import capture_clip
from .config import load_config
from .poller import EventPoller
from .scheduler import is_daylight, log_schedule
from .tuya_api import TuyaClient
from .tuya_listener import start_listener

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "config.yaml"


def _upload_to_birdvision(clip_path, captured_at, config, event_id):
    """Run in a background thread so the main poll loop isn't blocked."""
    post_clip(
        clip_path,
        captured_at,
        config.birdvision,
        latitude=config.location.lat,
        longitude=config.location.lon,
        source_event_id=event_id,
    )


def main() -> None:
    # Apply timezone before configuring logging so timestamps are in local time.
    # Read directly from env first (fastest path); full config load follows.
    tz = os.environ.get("BIRDCAM_TIMEZONE", "America/New_York")
    os.environ["TZ"] = tz
    time.tzset()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    config_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG_PATH
    config = load_config(config_path)

    # If the config file specifies a different timezone, reapply it.
    if config.location.timezone != tz:
        os.environ["TZ"] = config.location.timezone
        time.tzset()

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
    logger.info(
        "Poll intervals: events=%ds, daylight=%ds",
        config.polling.event_interval,
        config.polling.daylight_check_interval,
    )
    if config.birdvision.enabled:
        logger.info("BirdVision integration enabled: %s", config.birdvision.url)
    else:
        logger.info("BirdVision integration disabled")
    log_schedule(config.location)

    client: TuyaClient | None = None
    poller: EventPoller | None = None
    listener = None
    pulsar_queue: queue.SimpleQueue = queue.SimpleQueue()

    try:
        while not shutdown:
            if not is_daylight(config.location):
                if client is not None:
                    logger.info("Sunset — pausing until dawn")
                    if listener is not None:
                        listener.stop()
                        listener = None
                    client = None
                    poller = None
                    log_schedule(config.location)
                time.sleep(config.polling.daylight_check_interval)
                continue

            # Initialize client on first daylight cycle
            if client is None:
                log_schedule(config.location)
                logger.info("Daylight — connecting to Tuya API")
                client = TuyaClient(config.tuya)
                poller = EventPoller(client, config.polling.event_interval)
                listener = start_listener(
                    config.tuya,
                    lambda msg: pulsar_queue.put(msg),
                )

                info = client.get_device_info()
                if info:
                    logger.info(
                        "Device '%s' online=%s",
                        info.get("name"),
                        info.get("online"),
                    )

            # Drain any Pulsar push messages
            while not pulsar_queue.empty():
                msg = pulsar_queue.get_nowait()
                logger.info("Pulsar message: %s", msg)

            power = client.get_power_stats()
            if power:
                logger.info(
                    "Power stats: battery=%s%% powermode=%s low_threshold=%s%% awake=%s battery_report_cap=%s",
                    power.get("wireless_electricity", "?"),
                    power.get("wireless_powermode", "?"),
                    power.get("wireless_lowpower", "?"),
                    power.get("wireless_awake", "?"),
                    power.get("battery_report_cap", "?"),
                )

            events = poller.check_for_new_events()

            for event in events:
                now = datetime.now(tz=timezone.utc)
                event_id = uuid4().hex[:8]
                date_dir = now.strftime("%Y-%m-%d")
                clip_name = now.strftime(f"%H%M%S-{event_id}.mp4")
                clip_path = output_base / date_dir / clip_name

                # Get a fresh RTSP URL for each capture
                rtsp_url = config.capture.rtsp_url or client.allocate_rtsp_url()
                if not rtsp_url:
                    logger.error("No RTSP URL available — skipping capture")
                    continue

                result = capture_clip(rtsp_url, clip_path, config.capture)
                if result is None:
                    logger.error("Clip capture failed, skipping BirdVision upload")
                    continue

                logger.info("Captured clip → %s", clip_path)

                if config.birdvision.enabled:
                    t = threading.Thread(
                        target=_upload_to_birdvision,
                        args=(clip_path, now, config, event_id),
                        daemon=True,
                        name=f"bv-upload-{event_id}",
                    )
                    t.start()

            time.sleep(config.polling.event_interval)
    finally:
        if listener is not None:
            listener.stop()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
