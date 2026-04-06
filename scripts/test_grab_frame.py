"""Grab a single frame from the camera's RTSP stream."""

import json
import logging
import os
import sys

import cv2
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

    # Allocate RTSP stream
    stream = api.post(
        f"/v1.0/devices/{device_id}/stream/actions/allocate",
        body={"type": "rtsp"},
    )
    if not stream.get("success"):
        logger.error("Failed to allocate stream: %s", stream)
        sys.exit(1)

    rtsp_url = stream["result"]["url"]
    logger.info("RTSP URL: %s", rtsp_url)

    # Grab a frame
    logger.info("Opening RTSP stream...")
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        logger.error("Failed to open RTSP stream")
        sys.exit(1)

    ret, frame = cap.read()
    cap.release()

    if not ret:
        logger.error("Failed to read frame from stream")
        sys.exit(1)

    output_path = "test_frame.jpg"
    cv2.imwrite(output_path, frame)
    h, w = frame.shape[:2]
    logger.info("Saved %dx%d frame to %s", w, h, output_path)


if __name__ == "__main__":
    main()
