"""Load and validate configuration from YAML."""

import logging
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
    lat: float = 40.75
    lon: float = -73.50


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


def load_config(path: str | Path) -> AppConfig:
    """Load configuration from a YAML file."""
    path = Path(path)
    if not path.exists():
        logger.warning("Config file %s not found, using defaults", path)
        return AppConfig()

    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    cfg = AppConfig(
        tuya=TuyaConfig(**raw.get("tuya", {})),
        location=LocationConfig(**raw.get("location", {})),
        capture=CaptureConfig(**raw.get("capture", {})),
        output=OutputConfig(**raw.get("output", {})),
    )
    logger.info("Loaded config from %s", path)
    return cfg
