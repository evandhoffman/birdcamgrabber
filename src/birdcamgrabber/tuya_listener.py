"""Tuya Cloud MQTT listener for bird-detection events."""

import logging
from collections.abc import Callable

from tuya_connector import TuyaOpenAPI, TuyaOpenMQ

from .config import TuyaConfig

logger = logging.getLogger(__name__)

TUYA_ENDPOINTS = {
    "us": "https://openapi.tuyaus.com",
    "eu": "https://openapi.tuyaeu.com",
    "cn": "https://openapi.tuyacn.com",
    "in": "https://openapi.tuyain.com",
}


def start_listener(
    config: TuyaConfig,
    on_event: Callable[[dict], None],
) -> TuyaOpenMQ:
    """Connect to Tuya Cloud and subscribe to device events.

    Calls `on_event(message)` whenever a message arrives for the
    configured device.
    """
    endpoint = TUYA_ENDPOINTS.get(config.region, TUYA_ENDPOINTS["us"])
    api = TuyaOpenAPI(endpoint, config.access_id, config.access_secret)
    resp = api.connect()
    logger.info("Tuya API connect: %s", resp)

    mq = TuyaOpenMQ(api)
    mq.start()

    def _on_message(msg):
        device_id = msg.get("devId", "")
        if device_id != config.device_id:
            return
        logger.info("Event received for device %s: %s", device_id, msg)
        on_event(msg)

    mq.add_message_listener(_on_message)
    logger.info("Listening for events on device %s", config.device_id)
    return mq
