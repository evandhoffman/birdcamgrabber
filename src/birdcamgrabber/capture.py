"""Video clip capture from an RTSP stream."""

import logging
import subprocess
from pathlib import Path

from .config import CaptureConfig

logger = logging.getLogger(__name__)


def capture_clip(
    rtsp_url: str,
    output_path: Path,
    config: CaptureConfig,
) -> Path | None:
    """Capture a video clip from an RTSP stream using ffmpeg.

    Saves to ``output_path`` (should end in ``.mp4``).
    Returns the path on success, ``None`` on failure.

    ffmpeg is preferred over OpenCV's VideoWriter because it can copy the
    H.264 stream directly from RTSP without re-encoding, which is faster,
    avoids quality loss, and produces a file BirdVision can play in the
    browser without a codec warning.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-loglevel", "warning",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-t", str(config.duration),
        "-c:v", "copy",        # stream-copy video: no re-encode
        "-an",                 # drop audio (pcm_mulaw not supported in MP4)
        "-movflags", "+faststart",
        "-y",                  # overwrite if exists
        str(output_path),
    ]

    logger.info(
        "Capturing %ds clip from RTSP → %s",
        config.duration,
        output_path,
    )
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=config.duration + 30)
    except FileNotFoundError:
        logger.error("ffmpeg not found — is it installed in the container?")
        return None
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg timed out capturing clip")
        return None

    if result.returncode != 0:
        logger.error("ffmpeg failed (rc=%d): %s", result.returncode, result.stderr.strip())
        return None

    if not output_path.exists() or output_path.stat().st_size == 0:
        logger.error("ffmpeg exited cleanly but output file is missing or empty: %s", output_path)
        return None

    logger.info("Clip saved: %s (%d bytes)", output_path, output_path.stat().st_size)
    return output_path
