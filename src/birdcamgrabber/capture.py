"""Burst frame capture from an RTSP stream."""

import logging
import time
from pathlib import Path

import cv2

from .config import CaptureConfig

logger = logging.getLogger(__name__)


def capture_burst(
    rtsp_url: str,
    output_dir: Path,
    config: CaptureConfig,
) -> list[Path]:
    """Connect to an RTSP stream and capture a burst of frames.

    Returns a list of paths to saved JPEG files.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        logger.error("Failed to open RTSP stream: %s", rtsp_url)
        return []

    interval = 1.0 / config.fps
    total_frames = config.fps * config.duration
    saved: list[Path] = []

    logger.info(
        "Starting burst capture: %d frames at %d fps from %s",
        total_frames,
        config.fps,
        rtsp_url,
    )

    try:
        for i in range(total_frames):
            ret, frame = cap.read()
            if not ret:
                logger.warning("Stream read failed at frame %d", i + 1)
                break

            frame_path = output_dir / f"frame-{i + 1:03d}.jpg"
            cv2.imwrite(str(frame_path), frame)
            saved.append(frame_path)
            logger.debug("Saved %s", frame_path)

            if i < total_frames - 1:
                time.sleep(interval)
    finally:
        cap.release()

    logger.info("Burst complete: %d frames saved to %s", len(saved), output_dir)
    return saved
