"""Third attempt at battery info — probe newer Tuya endpoints and known DP IDs.

Findings from external research (April 2026):

* Birdfy / sp_wnq cameras expose battery via these data points:
    - DP 145  battery_percentage     Integer 0-100
    - DP 146  power_supply_mode      Enum     "0"=battery / "1"=AC
    - DP 147  low_battery_alarm      Integer  10-30 threshold
    - DP 149  device_state           Bool     dormant / waking
    - DP 126  battery_report_capacity (sometimes used)

* Older /v1.0/devices/{id}/status returned an empty array for us. This is
  almost always because the IoT project is in "Standard Instruction" mode
  rather than "DP Instruction" mode. In Standard Instruction mode the cloud
  only returns DPs that match a published standard schema; Birdfy's vendor
  DPs are hidden. Switching the device type in the project settings to
  "DP Instruction" exposes all raw DPs.

* The newer Smart Home Device Management Service exposes DPs as
  "properties" via /v2.0/cloud/thing/{device_id}/shadow/properties, which
  appears to bypass the Standard/DP-Instruction toggle for some devices.

This script probes both old and new endpoints and reports anything that
looks like a battery value, so we can confirm which combination works for
this account before wiring it into the main service.
"""

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


# DP codes to look for in any response
BATTERY_CODES = {
    "battery_percentage",
    "battery_state",
    "battery_value",
    "residual_electricity",
    "wireless_electricity",
    "wireless_battery",
    "wireless_lowpower",
    "electricity_left",
    "va_battery",
    "power_supply_mode",
    "low_battery_alarm",
    "battery_report_capacity",
}
BATTERY_DP_IDS = {126, 145, 146, 147, 149}


def dump(label: str, resp: dict) -> None:
    logger.info("--- %s ---", label)
    logger.info("%s", json.dumps(resp, indent=2)[:4000])


def main() -> None:
    load_dotenv()

    access_id = os.environ.get("TUYA_ACCESS_ID", "")
    access_secret = os.environ.get("TUYA_ACCESS_SECRET", "")
    device_id = os.environ.get("TUYA_DEVICE_ID", "")
    if not (access_id and access_secret and device_id):
        logger.error("Missing TUYA_ACCESS_ID / TUYA_ACCESS_SECRET / TUYA_DEVICE_ID")
        sys.exit(1)

    api = TuyaOpenAPI("https://openapi.tuyaus.com", access_id, access_secret)
    if not api.connect().get("success"):
        logger.error("Tuya connect failed")
        sys.exit(1)

    # 1. Smart Home Device Management Service — properties shadow.
    #    This is the newer "things" API. Returns latest reported value of
    #    every property/DP the cloud knows about, including custom DPs.
    dump(
        "v2.0 cloud/thing shadow properties (all)",
        api.get(f"/v2.0/cloud/thing/{device_id}/shadow/properties"),
    )

    # 2. Same endpoint, but filtered by codes — saves bandwidth and
    #    sometimes returns DPs the unfiltered call hides.
    dump(
        "v2.0 cloud/thing shadow properties (filtered)",
        api.get(
            f"/v2.0/cloud/thing/{device_id}/shadow/properties",
            params={"codes": ",".join(sorted(BATTERY_CODES))},
        ),
    )

    # 3. Data model — tells us what properties this device *should* expose,
    #    even if their current value is hidden.
    dump(
        "v2.0 cloud/thing model",
        api.get(f"/v2.0/cloud/thing/{device_id}/model"),
    )

    # 4. Device details (newer endpoint).
    dump(
        "v2.0 cloud/thing detail",
        api.get(f"/v2.0/cloud/thing/{device_id}"),
    )

    # 5. Power Management Service — Query Remaining Battery Capacity.
    #    Documented for /v1.0/iot-03/power-devices/{device_id}/balance-charge.
    #    Almost certainly meant for energy meters, not cameras, but worth
    #    a probe since the Power Management API service IS subscribed.
    dump(
        "Power Management balance-charge",
        api.get(f"/v1.0/iot-03/power-devices/{device_id}/balance-charge"),
    )

    # 6. Re-try the legacy status endpoints in case "DP Instruction" mode
    #    has been toggled on the device type since the last attempt.
    dump(
        "v1.0 devices status (after possible DP-Instruction toggle)",
        api.get(f"/v1.0/devices/{device_id}/status"),
    )
    dump(
        "v1.0 iot-03 devices status",
        api.get(f"/v1.0/iot-03/devices/{device_id}/status"),
    )

    # 7. Specifications — lists every DP id/code/type the cloud has on file.
    dump(
        "v1.0 iot-03 devices specification",
        api.get(f"/v1.0/iot-03/devices/{device_id}/specification"),
    )

    # 8. Hunt for the known battery DP ids in everything we collected. We
    #    re-issue the shadow query and walk the response so the operator
    #    sees a clear PASS/FAIL line at the bottom of the run.
    shadow = api.get(f"/v2.0/cloud/thing/{device_id}/shadow/properties")
    found = []
    for prop in (shadow.get("result") or {}).get("properties", []) or []:
        if (
            prop.get("dp_id") in BATTERY_DP_IDS
            or prop.get("code") in BATTERY_CODES
        ):
            found.append(prop)

    if found:
        logger.info("BATTERY DATA FOUND: %s", json.dumps(found, indent=2))
    else:
        logger.info(
            "No battery DPs found. If the Tuya app shows a battery percentage, "
            "open iot.tuya.com -> Cloud -> your project -> Devices, edit the "
            "device type for this product, enable 'DP Instruction', save, and "
            "re-run this script after a few minutes."
        )


if __name__ == "__main__":
    main()
