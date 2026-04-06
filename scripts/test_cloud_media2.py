"""Try more Tuya IPC/cloud media endpoints."""

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


def try_endpoint(api, method, path, **kwargs):
    label = f"{method.upper()} {path}"
    logger.info("--- %s ---", label)
    if method == "get":
        r = api.get(path, **kwargs)
    else:
        r = api.post(path, **kwargs)
    if r.get("success"):
        logger.info("SUCCESS: %s", json.dumps(r, indent=2))
    else:
        logger.info("  %s: %s", r.get("code"), r.get("msg"))
    return r


def main() -> None:
    load_dotenv()

    access_id = os.environ["TUYA_ACCESS_ID"]
    access_secret = os.environ["TUYA_ACCESS_SECRET"]
    device_id = os.environ["TUYA_DEVICE_ID"]

    api = TuyaOpenAPI("https://openapi.tuyaus.com", access_id, access_secret)
    api.connect()

    now = int(time.time())
    now_ms = now * 1000
    week_ago = now - (7 * 86400)
    week_ago_ms = week_ago * 1000

    # IPC-related APIs with different path patterns
    try_endpoint(api, "get", f"/v1.0/ipc/devices/{device_id}/cloud-storage-days",
                 params={"start_time": week_ago, "end_time": now})

    try_endpoint(api, "get", f"/v1.0/ipc/devices/{device_id}/detection-media",
                 params={"start_time": week_ago, "end_time": now, "size": 5})

    try_endpoint(api, "get", f"/v1.0/ipc/devices/{device_id}/latest-media")

    try_endpoint(api, "get", f"/v1.0/ipc/{device_id}/alarm-images",
                 params={"start_time": week_ago_ms, "end_time": now_ms, "size": 5})

    # Smart camera specific
    try_endpoint(api, "post", f"/v1.0/smart-camera/devices/{device_id}/screenshot")

    try_endpoint(api, "get", f"/v1.0/smart-camera/devices/{device_id}/screenshots",
                 params={"start_time": week_ago, "end_time": now})

    # Try iot-03 path style
    try_endpoint(api, "get", f"/v1.0/iot-03/devices/{device_id}/ipc/cloud-storage/days",
                 params={"start_time": week_ago, "end_time": now})

    # Check what API services are actually available
    try_endpoint(api, "get", f"/v1.0/devices/{device_id}/camera/config")

    # Device event images via log detail
    try_endpoint(api, "get", f"/v1.0/devices/{device_id}/logs",
                 params={"start_time": week_ago_ms, "end_time": now_ms,
                         "type": "1", "size": 5})

    # Try getting event with more detail (some events include image URLs)
    try_endpoint(api, "get", f"/v1.0/devices/{device_id}/logs",
                 params={"start_time": week_ago_ms, "end_time": now_ms,
                         "type": "9", "size": 5})


if __name__ == "__main__":
    main()
