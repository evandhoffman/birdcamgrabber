# birdcamgrabber

Captures bird photos from a Tuya/Birdfy smart feeder camera when bird-detection
events fire, and saves burst frames to local storage.

## How it works

1. **Event subscription** — connects to Tuya Cloud MQTT and listens for
   bird-detection events from the camera
2. **Burst capture** — on event, connects to the camera's RTSP stream and grabs
   frames at ~2 fps for a configurable duration
3. **Storage** — saves frames to local filesystem:
   `YYYY-MM-DD/HHMMSS-<event-id>/frame-001.jpg`
4. **Dawn/dusk scheduling** — only active between sunrise and sunset, computed
   from configured lat/lon (shifts automatically with the seasons)
5. **Future: species ID** — POST captured frames to
   [BirdVision](https://github.com/evandhoffman/birdvision) for classification

## Prerequisites

1. A Tuya-compatible smart bird feeder camera (e.g. Birdfy)
2. [Tuya IoT Platform](https://iot.tuya.com) developer account (free tier)
3. Link your Tuya Smart / Smart Life app account to the developer project
4. Subscribe to the **Smart Home** API group (free)
5. Note your **Access ID**, **Access Secret**, and **Device ID**

## Configuration

Non-secret settings live in `config.yaml` (mounted into the container).
Secrets and location are loaded from environment variables (`.env` file),
which override anything in `config.yaml`.

Copy the example files to get started:

```bash
cp config.yaml.example config.yaml
cp .env.example .env
# edit .env with your Tuya credentials and real coordinates
```

### `.env` (secrets — not checked in)

```
TUYA_ACCESS_ID=your-access-id
TUYA_ACCESS_SECRET=your-access-secret
TUYA_DEVICE_ID=your-device-id
TUYA_REGION=us
BIRDCAM_LAT=40.770998606849155
BIRDCAM_LON=-73.97321317729947
BIRDCAM_RTSP_URL=rtsp://...
```

### `config.yaml` (non-secret defaults)

```yaml
location:
  lat: 40.770998606849155
  lon: -73.97321317729947

capture:
  fps: 2                        # frames per second during burst
  duration: 5                   # burst duration in seconds
  rtsp_url: ""                  # leave blank to auto-discover via Tuya API

output:
  dir: "/data/images"           # container path; bind-mount to host
```

Environment variables always take precedence over `config.yaml` values.

## Running

```bash
docker compose up -d
```

Images are written to the bind-mounted volume at `./images/` on the host.

## Development

```bash
uv sync
uv run python -m birdcamgrabber
```

## Architecture

- **Python 3.12+**, managed with [uv](https://github.com/astral-sh/uv)
- **Docker** with Chainguard base image (`cgr.dev/chainguard/python:latest-dev`)
- **tuya-connector-python** for cloud API + MQTT event subscription
- **opencv-python** (or ffmpeg) for RTSP frame capture
- **astral** for sunrise/sunset calculation
