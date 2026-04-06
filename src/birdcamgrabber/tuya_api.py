"""Tuya Cloud API client — shared across polling and event-driven modes."""

import logging

from tuya_connector import TuyaOpenAPI

from .config import TuyaConfig

logger = logging.getLogger(__name__)

TUYA_ENDPOINTS = {
    "us": "https://openapi.tuyaus.com",
    "eu": "https://openapi.tuyaeu.com",
    "cn": "https://openapi.tuyacn.com",
    "in": "https://openapi.tuyain.com",
}


class TuyaClient:
    """Wrapper around TuyaOpenAPI for the operations we need."""

    def __init__(self, config: TuyaConfig) -> None:
        self.config = config
        endpoint = TUYA_ENDPOINTS.get(config.region, TUYA_ENDPOINTS["us"])
        self.api = TuyaOpenAPI(endpoint, config.access_id, config.access_secret)
        resp = self.api.connect()
        if not resp.get("success"):
            raise RuntimeError(f"Tuya API connect failed: {resp}")
        logger.info("Tuya API connected (region=%s)", config.region)

    def allocate_rtsp_url(self) -> str | None:
        """Request a fresh RTSP stream URL for the device."""
        resp = self.api.post(
            f"/v1.0/devices/{self.config.device_id}/stream/actions/allocate",
            body={"type": "rtsp"},
        )
        if not resp.get("success"):
            logger.error("Failed to allocate RTSP stream: %s", resp)
            return None
        url = resp["result"]["url"]
        logger.info("Allocated RTSP stream URL")
        return url

    def get_device_info(self) -> dict | None:
        """Fetch device info (online status, etc.)."""
        resp = self.api.get(f"/v1.0/devices/{self.config.device_id}")
        if not resp.get("success"):
            logger.error("Failed to get device info: %s", resp)
            return None
        return resp["result"]

    def get_event_logs(
        self,
        start_time_ms: int,
        end_time_ms: int,
        event_type: str = "1",
        size: int = 20,
    ) -> list[dict]:
        """Fetch device event logs within a time range.

        Event types observed for Birdfy:
          1 = motion/bird detection (frequent)
          9 = detection-related (frequent)
          2 = rare/other
        """
        resp = self.api.get(
            f"/v1.0/devices/{self.config.device_id}/logs",
            params={
                "start_time": start_time_ms,
                "end_time": end_time_ms,
                "type": event_type,
                "size": size,
            },
        )
        if not resp.get("success"):
            logger.warning("Failed to fetch event logs: %s", resp)
            return []
        return resp.get("result", {}).get("logs", [])
