"""Probe various Tuya APIs for battery/charge status."""

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


def main() -> None:
    load_dotenv()

    access_id = os.environ.get("TUYA_ACCESS_ID", "")
    access_secret = os.environ.get("TUYA_ACCESS_SECRET", "")
    device_id = os.environ.get("TUYA_DEVICE_ID", "")

    api = TuyaOpenAPI("https://openapi.tuyaus.com", access_id, access_secret)
    resp = api.connect()
    if not resp.get("success"):
        logger.error("Connect failed: %s", resp)
        sys.exit(1)

    # Try v1.1 device status (sometimes works when v1.0 doesn't)
    logger.info("--- v1.1 device status ---")
    r = api.get(f"/v1.1/devices/{device_id}/status")
    logger.info("%s", json.dumps(r, indent=2))

    # Try v2.0 device detail
    logger.info("--- v2.0 device detail ---")
    r = api.get(f"/v2.0/devices/{device_id}")
    logger.info("%s", json.dumps(r, indent=2))

    # Try device properties (DP)
    logger.info("--- Device properties report ---")
    r = api.get(f"/v2.0/devices/{device_id}/properties")
    logger.info("%s", json.dumps(r, indent=2))

    # Try specific DP codes commonly used for battery
    logger.info("--- Get DP values via commands ---")
    for code in ["battery_percentage", "battery_state", "charge_state", "electricity_left",
                 "va_battery", "residual_electricity", "battery_value"]:
        r = api.get(f"/v1.0/devices/{device_id}/status", params={"code": code})
        if r.get("success") and r.get("result"):
            logger.info("DP %s: %s", code, json.dumps(r["result"], indent=2))

    # Try device sub-devices (in case battery is a sub-component)
    logger.info("--- Sub-devices ---")
    r = api.get(f"/v1.0/devices/{device_id}/sub-devices")
    logger.info("%s", json.dumps(r, indent=2))

    # Try device logs for type 1-10 (broader search)
    import time
    end_time = int(time.time() * 1000)
    start_time = end_time - (7 * 24 * 60 * 60 * 1000)  # last 7 days
    for log_type in range(1, 11):
        r = api.get(
            f"/v1.0/devices/{device_id}/logs",
            params={"start_time": start_time, "end_time": end_time, "type": str(log_type), "size": 10},
        )
        logs = r.get("result", {}).get("logs", [])
        if logs:
            logger.info("Log type %d: %s", log_type, json.dumps(logs, indent=2))

    # Try v1.0 iot-03 device status (industry API)
    logger.info("--- iot-03 device status ---")
    r = api.get(f"/v1.0/iot-03/devices/{device_id}/status")
    logger.info("%s", json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
