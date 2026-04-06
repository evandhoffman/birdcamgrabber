"""Probe newly subscribed Tuya APIs: camera, cloud video, power, maintenance."""

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


def try_endpoint(api, method, path, label=None, **kwargs):
    label = label or f"{method.upper()} {path}"
    if method == "get":
        r = api.get(path, **kwargs)
    else:
        r = api.post(path, **kwargs)
    if r.get("success"):
        logger.info("[OK] %s\n%s", label, json.dumps(r, indent=2))
    else:
        logger.info("[--] %s → %s: %s", label, r.get("code"), r.get("msg"))
    return r


def main() -> None:
    load_dotenv()

    device_id = os.environ["TUYA_DEVICE_ID"]
    api = TuyaOpenAPI("https://openapi.tuyaus.com",
                      os.environ["TUYA_ACCESS_ID"],
                      os.environ["TUYA_ACCESS_SECRET"])
    api.connect()

    now = int(time.time())
    now_ms = now * 1000
    day_ago = now - 86400
    day_ago_ms = day_ago * 1000
    week_ago = now - 7 * 86400

    # === POWER MANAGEMENT ===
    logger.info("========== POWER MANAGEMENT ==========")
    try_endpoint(api, "get", f"/v1.0/devices/{device_id}/status")
    try_endpoint(api, "get", f"/v1.0/iot-03/devices/{device_id}/status")
    try_endpoint(api, "get", f"/v1.0/devices/{device_id}/statistics/days",
                 params={"start_day": "20260401", "end_day": "20260406"})
    try_endpoint(api, "get", f"/v1.0/devices/{device_id}/report-logs",
                 params={"start_time": day_ago_ms, "end_time": now_ms,
                         "codes": "battery_percentage,battery_state,va_battery,electricity_left",
                         "size": 10})
    try_endpoint(api, "get", f"/v1.0/devices/{device_id}/properties",
                 label="Device properties")

    # === CAMERA SERVICE ===
    logger.info("========== CAMERA SERVICE ==========")
    try_endpoint(api, "get", f"/v1.0/devices/{device_id}/camera/config",
                 label="Camera config")
    try_endpoint(api, "post", f"/v1.0/devices/{device_id}/door-bell/screenshot",
                 label="Camera screenshot (doorbell style)")
    try_endpoint(api, "get", f"/v1.0/devices/{device_id}/camera/abilities",
                 label="Camera abilities")

    # === VIDEO CLOUD STORAGE ===
    logger.info("========== VIDEO CLOUD STORAGE ==========")
    try_endpoint(api, "get", f"/v1.0/devices/{device_id}/ipc/cloud-storage/days",
                 params={"start_time": week_ago, "end_time": now},
                 label="Cloud storage days")
    try_endpoint(api, "get", f"/v1.0/devices/{device_id}/ipc/cloud-storage/events",
                 params={"start_time": day_ago, "end_time": now, "size": 10},
                 label="Cloud storage events")

    # === IOT VIDEO LIVE STREAM ===
    logger.info("========== IOT VIDEO LIVE STREAM ==========")
    try_endpoint(api, "post", f"/v1.0/devices/{device_id}/stream/actions/allocate",
                 body={"type": "rtsp"}, label="RTSP stream (already works)")
    try_endpoint(api, "post", f"/v1.0/devices/{device_id}/stream/actions/allocate",
                 body={"type": "flv"}, label="FLV stream")

    # === DEVICE MAINTENANCE ===
    logger.info("========== DEVICE MAINTENANCE ==========")
    try_endpoint(api, "get", f"/v1.0/devices/{device_id}/firmware",
                 label="Firmware info")
    try_endpoint(api, "get", f"/v1.0/devices/{device_id}/statistics",
                 label="Device statistics")

    # === DEVICE STATUS NOTIFICATION (Pulsar) ===
    logger.info("========== DEVICE STATUS NOTIFICATION ==========")
    from tuya_connector import TuyaCloudPulsarTopic, TuyaOpenPulsar
    logger.info("Attempting Pulsar connection...")
    try:
        pulsar = TuyaOpenPulsar(
            os.environ["TUYA_ACCESS_ID"],
            os.environ["TUYA_ACCESS_SECRET"],
            "wss://mqe.tuyaus.com:8285/",
            TuyaCloudPulsarTopic.PROD,
        )
        connected = []
        def on_msg(msg):
            connected.append(msg)
            logger.info("Pulsar message: %s", json.dumps(msg, indent=2, default=str))
        pulsar.add_message_listener(on_msg)
        pulsar.start()
        time.sleep(10)
        pulsar.stop()
        if connected:
            logger.info("[OK] Pulsar connected, received %d messages", len(connected))
        else:
            logger.info("[--] Pulsar started but no messages in 10s (may be OK if no events)")
    except Exception as e:
        logger.info("[--] Pulsar error: %s", e)

    # === SMART HOME BASIC ===
    logger.info("========== SMART HOME BASIC ==========")
    try_endpoint(api, "get", f"/v1.0/devices/{device_id}",
                 label="Device info (already works)")
    try_endpoint(api, "get", f"/v1.0/devices/{device_id}/functions",
                 label="Device functions")
    try_endpoint(api, "get", f"/v1.0/devices/{device_id}/specifications",
                 label="Device specifications")


if __name__ == "__main__":
    main()
