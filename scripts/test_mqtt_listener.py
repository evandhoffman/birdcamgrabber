"""Listen to Tuya Pulsar events and log everything that arrives for the device."""

import json
import logging
import os
import signal
import sys

from dotenv import load_dotenv
from tuya_connector import TuyaCloudPulsarTopic, TuyaOpenPulsar

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Tuya Pulsar WebSocket endpoints
PULSAR_ENDPOINTS = {
    "us": "wss://mqe.tuyaus.com:8285/",
    "eu": "wss://mqe.tuyaeu.com:8285/",
    "cn": "wss://mqe.tuyacn.com:8285/",
    "in": "wss://mqe.tuyain.com:8285/",
}


def main() -> None:
    load_dotenv()

    access_id = os.environ.get("TUYA_ACCESS_ID", "")
    access_secret = os.environ.get("TUYA_ACCESS_SECRET", "")
    device_id = os.environ.get("TUYA_DEVICE_ID", "")
    region = os.environ.get("TUYA_REGION", "us")

    ws_endpoint = PULSAR_ENDPOINTS.get(region, PULSAR_ENDPOINTS["us"])

    logger.info("Connecting to Pulsar at %s", ws_endpoint)
    logger.info("Waiting for events from device %s... Ctrl+C to stop.", device_id)

    pulsar = TuyaOpenPulsar(
        access_id,
        access_secret,
        ws_endpoint,
        TuyaCloudPulsarTopic.PROD,
    )

    event_count = 0

    def on_message(msg):
        nonlocal event_count
        event_count += 1
        dev_id = msg.get("devId", "unknown")
        marker = ">>> MATCH" if dev_id == device_id else "    other"
        logger.info(
            "[%s] Event #%d from %s:\n%s",
            marker, event_count, dev_id,
            json.dumps(msg, indent=2, default=str),
        )

    pulsar.add_message_listener(on_message)
    pulsar.start()

    shutdown = False

    def handle_signal(signum, _frame):
        nonlocal shutdown
        shutdown = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    import time
    while not shutdown:
        time.sleep(1)

    logger.info("Stopping Pulsar listener (%d events received)", event_count)
    pulsar.stop()


if __name__ == "__main__":
    main()
