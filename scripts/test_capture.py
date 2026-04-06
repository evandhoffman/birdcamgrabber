"""Test: try to grab a frame from the camera via Tuya APIs."""

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

    endpoint = ENDPOINTS.get(region, ENDPOINTS["us"])
    api = TuyaOpenAPI(endpoint, access_id, access_secret)
    resp = api.connect()
    if not resp.get("success"):
        logger.error("Connect failed: %s", resp)
        sys.exit(1)
    logger.info("Connected to Tuya API")

    # 1. Try IPC snapshot command
    logger.info("--- Attempt 1: IPC visual capability (snapshot) ---")
    snap = api.post(
        f"/v1.0/devices/{device_id}/commands",
        body={"commands": [{"code": "snapshot", "value": True}]},
    )
    logger.info("Snapshot command: %s", json.dumps(snap, indent=2))

    # 2. Try to get RTSP stream URL
    logger.info("--- Attempt 2: Stream URL via /v1.0/devices/.../stream/actions/allocate ---")
    stream = api.post(
        f"/v1.0/devices/{device_id}/stream/actions/allocate",
        body={"type": "rtsp"},
    )
    logger.info("Stream allocate (rtsp): %s", json.dumps(stream, indent=2))

    # 3. Try HLS stream
    logger.info("--- Attempt 3: Stream URL via HLS ---")
    stream_hls = api.post(
        f"/v1.0/devices/{device_id}/stream/actions/allocate",
        body={"type": "hls"},
    )
    logger.info("Stream allocate (hls): %s", json.dumps(stream_hls, indent=2))

    # 4. Try v2.0 stream API
    logger.info("--- Attempt 4: v2.0 stream API ---")
    stream_v2 = api.post(
        f"/v2.0/devices/{device_id}/stream/actions/allocate",
        body={"type": "rtsp"},
    )
    logger.info("Stream allocate v2 (rtsp): %s", json.dumps(stream_v2, indent=2))

    # 5. Try to get camera abilities
    logger.info("--- Attempt 5: Device functions ---")
    funcs = api.get(f"/v1.0/devices/{device_id}/functions")
    logger.info("Device functions: %s", json.dumps(funcs, indent=2))

    # 6. Try category-level info for sp_wnq
    logger.info("--- Attempt 6: Category functions for sp_wnq ---")
    cat_funcs = api.get(f"/v1.0/functions/snqsbpfrgrqizqny")
    logger.info("Product functions: %s", json.dumps(cat_funcs, indent=2))


if __name__ == "__main__":
    main()
