# birdcamgrabber

Captures bird photos from a Tuya/Birdfy smart feeder camera when bird-detection
events fire, and saves burst frames to local storage.

## How it works

1. **Event polling** — polls the Tuya Cloud API for new bird-detection events
   from the camera (Pulsar push events planned once auth is resolved)
2. **Burst capture** — on event, allocates a fresh RTSP stream URL from Tuya
   and grabs frames at ~2 fps for a configurable duration
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

## Tuya free-tier rate limits

The Tuya IoT Platform free trial plan has these limits:

| Resource                    | Limit       |
|-----------------------------|-------------|
| Data centers                | 1           |
| Max devices                 | 50          |
| Max controllable devices    | 10          |
| API calls / month           | **26,000**  |
| Messages / month            | **68,000**  |

### How this app stays within limits

The default polling interval of **120 seconds** during daylight (~14h) yields:

| Activity                | Calls/day | Calls/month |
|-------------------------|-----------|-------------|
| Event log polls         | ~420      | ~12,600     |
| RTSP stream allocations | ~10–50    | ~300–1,500  |
| Device info (1×/day)    | 1         | 30          |
| **Total (typical)**     | **~470**  | **~14,100** |

This leaves comfortable headroom under the 26,000/month cap. If you need
faster polling, reduce `polling.event_interval` — but watch the budget:

| Interval | Polls/month | Remaining for captures |
|----------|-------------|------------------------|
| 60s      | ~25,200     | ~800                   |
| 90s      | ~16,800     | ~9,200                 |
| **120s** | **~12,600** | **~13,400**            |
| 180s     | ~8,400      | ~17,600                |

Switching to Tuya Pulsar push notifications (planned) would eliminate polling
entirely and use only the message quota instead.

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

polling:
  event_interval: 120           # seconds between event log polls (daylight)
  daylight_check_interval: 300  # seconds between dawn/dusk checks (night)
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
- **tuya-connector-python** for cloud API + event polling
- **opencv-python-headless** for RTSP frame capture
- **astral** for sunrise/sunset calculation
