"""Quick test: connect to Tuya API and query device info."""

import json
import logging
import os
import sys

from dotenv import load_dotenv
from tuya_connector import TuyaOpenAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

ENDPOINTS = {
    "us": "https://openapi.tuyaus.com",
    "eu": "https://openapi.tuyaeu.com",
    "cn": "https://openapi.tuyacn.com",
    "in": "https://openapi.tuyain.com",
}


def main() -> None:
    load_dotenv()

    access_id = os.environ.get("TUYA_ACCESS_ID", "")
    access_secret = os.environ.get("TUYA_ACCESS_SECRET", "")
    device_id = os.environ.get("TUYA_DEVICE_ID", "")
    region = os.environ.get("TUYA_REGION", "us")

    if not all([access_id, access_secret, device_id]):
        logger.error("Missing TUYA_ACCESS_ID, TUYA_ACCESS_SECRET, or TUYA_DEVICE_ID in .env")
        sys.exit(1)

    endpoint = ENDPOINTS.get(region, ENDPOINTS["us"])
    logger.info("Connecting to %s", endpoint)

    api = TuyaOpenAPI(endpoint, access_id, access_secret)
    resp = api.connect()
    logger.info("Connect response: %s", resp)

    if not resp.get("success"):
        logger.error("Failed to connect: %s", resp.get("msg"))
        sys.exit(1)

    # Get device info
    logger.info("Querying device %s", device_id)
    device_info = api.get(f"/v1.0/devices/{device_id}")
    logger.info("Device info:\n%s", json.dumps(device_info, indent=2))

    # Get device status (current data points)
    status = api.get(f"/v1.0/devices/{device_id}/status")
    logger.info("Device status:\n%s", json.dumps(status, indent=2))

    # Get device specifications / functions
    specs = api.get(f"/v1.0/devices/{device_id}/specifications")
    logger.info("Device specifications:\n%s", json.dumps(specs, indent=2))

    # Get device logs (recent events)
    import time
    end_time = int(time.time() * 1000)
    start_time = end_time - (24 * 60 * 60 * 1000)  # last 24 hours
    logs = api.get(
        f"/v1.0/devices/{device_id}/logs",
        params={"start_time": start_time, "end_time": end_time, "type": "7"},
    )
    logger.info("Device logs (last 24h):\n%s", json.dumps(logs, indent=2))


if __name__ == "__main__":
    main()
