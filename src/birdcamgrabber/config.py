"""Load and validate configuration from YAML + environment variables."""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class TuyaConfig:
    access_id: str = ""
    access_secret: str = ""
    device_id: str = ""
    region: str = "us"


@dataclass
class LocationConfig:
    lat: float = 40.770998606849155
    lon: float = -73.97321317729947


@dataclass
class CaptureConfig:
    fps: int = 2
    duration: int = 5
    rtsp_url: str = ""


@dataclass
class OutputConfig:
    dir: str = "/data/images"


@dataclass
class AppConfig:
    tuya: TuyaConfig = field(default_factory=TuyaConfig)
    location: LocationConfig = field(default_factory=LocationConfig)
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


def _apply_env_overrides(cfg: AppConfig) -> None:
    """Override config values with environment variables when set."""
    if v := os.environ.get("TUYA_ACCESS_ID"):
        cfg.tuya.access_id = v
    if v := os.environ.get("TUYA_ACCESS_SECRET"):
        cfg.tuya.access_secret = v
    if v := os.environ.get("TUYA_DEVICE_ID"):
        cfg.tuya.device_id = v
    if v := os.environ.get("TUYA_REGION"):
        cfg.tuya.region = v
    if v := os.environ.get("BIRDCAM_LAT"):
        cfg.location.lat = float(v)
    if v := os.environ.get("BIRDCAM_LON"):
        cfg.location.lon = float(v)
    if v := os.environ.get("BIRDCAM_RTSP_URL"):
        cfg.capture.rtsp_url = v


def load_config(path: str | Path) -> AppConfig:
    """Load configuration from a YAML file, then apply env var overrides."""
    path = Path(path)
    if not path.exists():
        logger.warning("Config file %s not found, using defaults", path)
        cfg = AppConfig()
    else:
        with open(path) as f:
            raw = yaml.safe_load(f) or {}

        cfg = AppConfig(
            tuya=TuyaConfig(**raw.get("tuya", {})),
            location=LocationConfig(**raw.get("location", {})),
            capture=CaptureConfig(**raw.get("capture", {})),
            output=OutputConfig(**raw.get("output", {})),
        )
        logger.info("Loaded config from %s", path)

    _apply_env_overrides(cfg)
    return cfg
