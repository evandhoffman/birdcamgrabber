"""Tuya Cloud Pulsar listener for bird-detection events."""

import logging
from collections.abc import Callable

from tuya_connector import TuyaCloudPulsarTopic, TuyaOpenPulsar

from .config import TuyaConfig

logger = logging.getLogger(__name__)

PULSAR_ENDPOINTS = {
    "us": "wss://mqe.tuyaus.com:8285/",
    "eu": "wss://mqe.tuyaeu.com:8285/",
    "cn": "wss://mqe.tuyacn.com:8285/",
    "in": "wss://mqe.tuyain.com:8285/",
}


def start_listener(
    config: TuyaConfig,
    on_event: Callable[[dict], None],
) -> TuyaOpenPulsar:
    """Connect to Tuya Cloud Pulsar and subscribe to device events.

    Calls `on_event(message)` whenever a message arrives for the
    configured device.
    """
    ws_endpoint = PULSAR_ENDPOINTS.get(config.region, PULSAR_ENDPOINTS["us"])

    pulsar = TuyaOpenPulsar(
        config.access_id,
        config.access_secret,
        ws_endpoint,
        TuyaCloudPulsarTopic.PROD,
    )

    def _on_message(msg):
        device_id = msg.get("devId", "")
        if device_id != config.device_id:
            return
        logger.info("Pulsar event for device %s: %s", device_id, msg)
        on_event(msg)

    pulsar.add_message_listener(_on_message)
    pulsar.start()
    logger.info("Pulsar listener started for device %s", config.device_id)
    return pulsar
