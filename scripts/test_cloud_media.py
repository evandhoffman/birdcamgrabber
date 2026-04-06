"""Probe Tuya APIs for cloud-stored images and video clips."""

import json
import logging
import os
import sys
import time

from dotenv import load_dotenv
from tuya_connector import TuyaOpenAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    load_dotenv()

    access_id = os.environ["TUYA_ACCESS_ID"]
    access_secret = os.environ["TUYA_ACCESS_SECRET"]
    device_id = os.environ["TUYA_DEVICE_ID"]

    api = TuyaOpenAPI("https://openapi.tuyaus.com", access_id, access_secret)
    api.connect()

    end_time = int(time.time())
    start_time = end_time - (7 * 24 * 60 * 60)  # last 7 days

    # 1. IPC cloud storage — list recorded days
    logger.info("--- Cloud storage: recorded days ---")
    r = api.get(f"/v1.0/devices/{device_id}/ipc/cloud-storage/days",
                params={"start_time": start_time, "end_time": end_time})
    logger.info("%s", json.dumps(r, indent=2))

    # 2. Cloud storage events/clips
    logger.info("--- Cloud storage: events ---")
    r = api.get(f"/v1.0/devices/{device_id}/ipc/cloud-storage/events",
                params={"start_time": start_time, "end_time": end_time, "size": 10})
    logger.info("%s", json.dumps(r, indent=2))

    # 3. Cloud storage — get playback URL
    logger.info("--- Cloud storage: playback URL ---")
    r = api.get(f"/v1.0/devices/{device_id}/ipc/cloud-storage/playback-url",
                params={"start_time": start_time, "end_time": end_time, "type": "hls"})
    logger.info("%s", json.dumps(r, indent=2))

    # 4. Detection media list
    logger.info("--- Detection media list ---")
    r = api.get(f"/v1.0/devices/{device_id}/ipc/media/latest",
                params={"size": 10})
    logger.info("%s", json.dumps(r, indent=2))

    # 5. Try v1.1 media
    logger.info("--- v1.0 media events ---")
    r = api.get(f"/v1.0/devices/{device_id}/media-events",
                params={"start_time": start_time * 1000, "end_time": end_time * 1000, "size": 10})
    logger.info("%s", json.dumps(r, indent=2))

    # 6. Smart camera detection list
    logger.info("--- IPC detection list ---")
    r = api.post(f"/v1.0/devices/{device_id}/ipc/detection/list",
                 body={"start_time": start_time, "end_time": end_time, "size": 10})
    logger.info("%s", json.dumps(r, indent=2))

    # 7. Local storage days
    logger.info("--- Local storage: days ---")
    r = api.get(f"/v1.0/devices/{device_id}/ipc/local-storage/days",
                params={"start_time": start_time, "end_time": end_time})
    logger.info("%s", json.dumps(r, indent=2))

    # 8. AI detection images
    logger.info("--- AI detection images ---")
    r = api.get(f"/v1.0/devices/{device_id}/ipc/ai-detect",
                params={"start_time": start_time, "end_time": end_time, "size": 10})
    logger.info("%s", json.dumps(r, indent=2))

    # 9. Try alarm images
    logger.info("--- Alarm images ---")
    r = api.get(f"/v1.0/devices/{device_id}/alarm-images",
                params={"start_time": start_time * 1000, "end_time": end_time * 1000, "size": 10})
    logger.info("%s", json.dumps(r, indent=2))

    # 10. IPC capabilities
    logger.info("--- IPC capabilities ---")
    r = api.get(f"/v1.0/devices/{device_id}/ipc/capabilities")
    logger.info("%s", json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
