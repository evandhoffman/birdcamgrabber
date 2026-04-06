# CLAUDE.md

Project context for Claude Code working in this repo.

## What this is

A containerized Python service that captures photos from a Birdfy smart bird
feeder camera (Tuya-managed) when motion is detected, and saves burst frames
to local storage. Designed to feed downstream into
[BirdVision](https://github.com/evandhoffman/birdvision) for species ID.

Runs on a home NAS via docker-compose. The user's camera is a Birdfy BF122-C
managed through the Tuya Smart app (not the Birdfy app).

## Architecture

```
src/birdcamgrabber/
├── __main__.py        # Entry point — main loop, daylight gating, event dispatch
├── config.py          # YAML + env var config loading (env wins)
├── tuya_api.py        # TuyaClient: REST wrapper (RTSP allocate, device info, event logs)
├── poller.py          # EventPoller: tracks last-seen event time, polls log API
├── tuya_listener.py   # Pulsar push listener — written but not working (see findings doc)
├── capture.py         # OpenCV burst capture from RTSP URL
└── scheduler.py       # astral-based sunrise/sunset check
```

The main loop:
1. If outside daylight → sleep `polling.daylight_check_interval` (no API calls)
2. Otherwise → poll for new events every `polling.event_interval` (default 120s)
3. For each new event → allocate a fresh RTSP URL → burst-capture frames →
   save to `output.dir/YYYY-MM-DD/HHMMSS-<id>/frame-NNN.jpg`

## Critical constraints

### Tuya free-tier rate limits

- **26,000 API calls/month**, **68,000 messages/month**
- The default 120s poll interval is sized to fit comfortably within this:
  ~12,600 calls/month for polling + ~1,500 for RTSP allocations.
- **Do not lower `polling.event_interval` without recalculating the budget.**
  See README.md for the table.

### What Birdfy doesn't expose through Tuya

The Birdfy is essentially a black box to Tuya — it exposes the live stream
and event log timestamps, and nothing else. **Don't waste time trying to:**

- Get battery / charge state — `status` array is always empty
- Pull cloud-stored snapshots/clips — `/ipc/cloud-storage/...` returns
  "uri path invalid" for this device category (`sp_wnq`)
- Get device functions / specifications — "not support this device"
- Connect Pulsar push — returns 401 even with Device Status Notification
  enabled (likely a free tier limitation)

Full findings: `docs/birdfy-tuya-findings.md`. Update that doc if you discover
anything new about Tuya APIs or Birdfy behavior.

### Session-scoped RTSP URLs

The RTSP URL returned by `POST /v1.0/devices/{id}/stream/actions/allocate`
is **temporary** — each capture must request a fresh URL via
`TuyaClient.allocate_rtsp_url()`. Don't cache it in config.

## Configuration

Two-layer config:

1. `config.yaml` — non-secret settings (lat/lon, capture params, polling
   intervals, output dir). Mounted into the container read-only.
2. `.env` — secrets and runtime overrides (Tuya credentials, optionally
   lat/lon and RTSP URL). Loaded via env_file in docker-compose. **Never
   committed.**

Env vars always override `config.yaml` values. Example files:
`config.yaml.example`, `.env.example`.

## Test scripts

`scripts/` contains exploratory scripts used to understand the Tuya API.
Most can be re-run safely. Useful ones:

- `test_tuya_connection.py` — basic API connect + device info
- `test_grab_frame.py` — single-frame RTSP capture
- `test_full_capture.py` — end-to-end: allocate stream + burst capture
- `test_poll_events.py` — real-time event log polling
- `test_new_apis.py` — probes all subscribed Tuya API services

These are kept for debugging and as a reference for what was tried.

## User preferences (from global CLAUDE.md)

- Python: **uv** for package management; `logging` not `print()`
- Docker: **Chainguard** base images; multi-stage builds; non-root user;
  `stop_grace_period: 30s` in compose
- GitHub username: `evandhoffman`
- Today's date is set in user's global config — don't make up dates
