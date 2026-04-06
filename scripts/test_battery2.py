"""Second attempt at battery info — try different API paths and log codes."""

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

    access_id = os.environ.get("TUYA_ACCESS_ID", "")
    access_secret = os.environ.get("TUYA_ACCESS_SECRET", "")
    device_id = os.environ.get("TUYA_DEVICE_ID", "")

    api = TuyaOpenAPI("https://openapi.tuyaus.com", access_id, access_secret)
    api.connect()

    end_time = int(time.time() * 1000)
    start_time = end_time - (7 * 24 * 60 * 60 * 1000)

    # Get more detail from logs — try with codes param
    logger.info("--- Logs with codes param ---")
    for codes in ["battery_percentage", "battery_state", "charge_state",
                  "va_battery", "residual_electricity", "wireless_electricity",
                  "electricity_left", "battery_value", "power"]:
        r = api.get(
            f"/v1.0/devices/{device_id}/logs",
            params={"start_time": start_time, "end_time": end_time,
                    "type": "7", "codes": codes, "size": 5},
        )
        logs = r.get("result", {}).get("logs", [])
        if logs:
            logger.info("Code %s: %s", codes, json.dumps(logs, indent=2))

    # Try type 7 with larger size to see what codes exist
    logger.info("--- Log type 7 (DP reports), last 50 ---")
    r = api.get(
        f"/v1.0/devices/{device_id}/logs",
        params={"start_time": start_time, "end_time": end_time,
                "type": "7", "size": 50},
    )
    logs = r.get("result", {}).get("logs", [])
    if logs:
        logger.info("%s", json.dumps(logs, indent=2))
    else:
        logger.info("No type-7 logs")

    # Try getting all DP codes via report logs (type 4)
    for t in ["4", "5", "6", "8"]:
        r = api.get(
            f"/v1.0/devices/{device_id}/logs",
            params={"start_time": start_time, "end_time": end_time,
                    "type": t, "size": 10},
        )
        logs = r.get("result", {}).get("logs", [])
        if logs:
            logger.info("Log type %s: %s", t, json.dumps(logs, indent=2))

    # Try the v1.0 smart home scene API to see device capabilities
    logger.info("--- Device DP list via iot-03 ---")
    r = api.get(f"/v1.0/iot-03/devices/{device_id}")
    logger.info("%s", json.dumps(r, indent=2))

    # Try sending a DP query command to wake up reporting
    logger.info("--- Send DP query ---")
    r = api.post(
        f"/v1.0/devices/{device_id}/commands",
        body={"commands": [{"code": "battery_percentage", "value": None}]},
    )
    logger.info("battery_percentage query: %s", json.dumps(r, indent=2))

    # Try the device info endpoint which returned lat/lon — check all fields
    logger.info("--- Full device info ---")
    r = api.get(f"/v1.0/devices/{device_id}")
    logger.info("%s", json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
