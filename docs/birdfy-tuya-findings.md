# Birdfy + Tuya Cloud API: what works and what doesn't

This document records what we learned about integrating a Birdfy smart bird
feeder camera (Tuya-managed) with the Tuya Cloud API. The goal was to find
the simplest path to capturing photos when the camera detects activity.

## Device

| Field | Value |
|-------|-------|
| Brand | Birdfy |
| Model | BF122-C |
| Tuya category | `sp_wnq` (Smart Bird Feeder Camera) |
| Tuya product ID | `snqsbpfrgrqizqny` |
| App used | Tuya Smart (migrated from Birdfy app) |

## Tuya project setup

- **Project type**: Smart Home, free trial plan (US data center)
- **Account linking**: Tuya Smart app account linked to the developer project
- **Subscribed API services**:
  - IoT Core
  - Smart Home Basic Service
  - Video Cloud Storage
  - IoT Video Live Stream
  - Device Maintenance
  - Device Status Notification
  - Power Management
  - Camera Service

## What works

| Capability | API | Notes |
|-----------|-----|-------|
| Device info | `GET /v1.0/devices/{id}` | Returns name, model, online status, IP, lat/lon (camera-reported) |
| Live RTSP stream | `POST /v1.0/devices/{id}/stream/actions/allocate` body `{type: rtsp}` | Returns a temporary RTSPS URL — must allocate fresh per session |
| Live FLV stream | Same endpoint, `{type: flv}` | Alternative to RTSP |
| Live HLS stream | Same endpoint, `{type: hls}` | Alternative to RTSP |
| Event log polling | `GET /v1.0/devices/{id}/logs?type=1` | Returns motion/detection events with timestamps |

The RTSP URL is **session-scoped** — every capture cycle should request a
fresh URL via `allocate_rtsp_url()` rather than storing one in config.

## What doesn't work

| Capability | Why |
|-----------|-----|
| Pulsar push notifications (`wss://mqe.tuyaus.com:8285/`) | 401 Unauthorized — even after enabling Device Status Notification. Likely not available on free tier or for this device category. |
| Standard device status (`/v1.0/devices/{id}/status`) | Returns "function not support". `iot-03/.../status` returns empty array. |
| Device functions / specifications | "not support this device" — Birdfy doesn't expose standard Tuya data points (DPs). |
| Battery / charge state | See [Battery: revisited](#battery-revisited) below — the data **is** in Tuya cloud, our project just can't see it yet. |
| Cloud-stored snapshots and clips (the images the Tuya app shows in alerts) | All `/ipc/cloud-storage/...` endpoints return "uri path invalid" — Birdfy stores media in its proprietary cloud, not Tuya's IPC cloud storage. |
| Camera Service endpoints (`/camera/config`, `/door-bell/screenshot`, etc.) | "uri path invalid" — Birdfy doesn't behave like a standard Tuya IPC. |
| Device statistics / report-logs | Either "uri path invalid" or "API not subscribed" (requires paid Industry Project Data tier). |
| Firmware info | "uri path invalid". |

## Event log details

Polling `/v1.0/devices/{id}/logs?type=N` returns events. Observed types:

| Type | Frequency | Meaning (best guess) |
|------|-----------|----------------------|
| 1 | Frequent, in pairs | Motion detected (start/end?) |
| 9 | Frequent | Detection-related (possibly AI bird detection) |
| 2 | Rare | Other |

Event payloads contain only `event_id`, `event_time`, `status`, `event_from`
— no associated image URL, no detection class, no bounding box. To get the
actual photo we have to grab our own RTSP frames.

A motion alert sent to the Tuya app (with snapshot) corresponds to type-1
events appearing in the log API within a few seconds.

## Free-tier rate limits

| Resource | Limit |
|----------|-------|
| API calls / month | 26,000 |
| Messages / month | 68,000 |
| Max devices | 50 |
| Max controllable devices | 10 |
| Data centers | 1 |

At a 120-second poll interval over ~14h of daylight: ~12,600 API calls/month,
leaving comfortable headroom for RTSP allocations and device info checks.
See README.md for the full budget table.

## Architecture implications

Given these constraints, the working approach is:

1. **Poll** the event log API every ~120s during daylight for new type-1 events
2. **Allocate** a fresh RTSP URL on each detected event
3. **Capture** a burst of frames via OpenCV from that RTSP stream
4. **Save** locally for downstream processing (e.g. BirdVision species ID)

We do not depend on:
- Push notifications (Pulsar) — unreliable on free tier
- Tuya cloud storage — not exposed for this device
- Battery telemetry — not available

If Birdfy ever publishes a public API for their own cloud, we could
optionally fetch their motion-triggered snapshots and AI-detected species
data, but that's out of scope here.

## Battery: revisited

The original investigation concluded that battery state was simply not
available. After observing that the Tuya Smart app shows
**Battery Powered 20%** plus a **Low Battery Alert Threshold** setting on
the Power Management Settings screen, we know the data definitely lives in
Tuya cloud — we just weren't asking for it the right way.

### Known Birdfy / `sp_wnq` battery DPs

Reverse-engineered by the
[`make-all/tuya-local`](https://github.com/make-all/tuya-local/issues/698)
project from a real BF122-style feeder:

| DP id | Code (best guess) | Type | Notes |
|-------|-------------------|------|-------|
| 145 | `battery_percentage` | Integer 0-100 | The 20% the app shows |
| 146 | `power_supply_mode` | Enum `"0"`/`"1"` | `0`=battery, `1`=AC |
| 147 | `low_battery_alarm` | Integer 10-30 | The threshold slider |
| 149 | `device_state` | Bool | dormant / waking |
| 126 | `battery_report_capacity` | Integer | Sometimes used instead of 145 |

These are **vendor DPs**, not part of any Tuya standard schema. That is the
root cause of every empty `status` response we saw earlier.

### Why our earlier probes returned empty

Tuya IoT projects have a per-device-type setting called **Control
Instruction Mode** with two values:

- **Standard Instruction** (default): the cloud only surfaces DPs that
  match a published standard schema. Vendor DPs are silently filtered out
  of `/v1.0/devices/{id}/status` and friends. This is what we have now.
- **DP Instruction**: the cloud surfaces every raw DP the device reports.

To switch it: `iot.tuya.com` → Cloud → Development → *project* → Devices
tab → pencil-edit the device type → tick **DP Instruction** → save. There
is no global toggle; it has to be done per device type, and it can take
several minutes to propagate.

After flipping the toggle, `GET /v1.0/devices/{device_id}/status` should
start returning entries with codes like `battery_percentage`,
`power_supply_mode`, `low_battery_alarm`, etc.

### Endpoints worth probing

Even without flipping DP Instruction mode, two newer endpoints sometimes
expose vendor DPs that the legacy `/v1.0/.../status` route hides:

- `GET /v2.0/cloud/thing/{device_id}/shadow/properties`
  Smart Home Device Management Service "Query Properties". Returns the
  latest reported value of every property the cloud has cached for the
  thing, including custom DPs. Accepts an optional `codes=a,b,c` filter.
- `GET /v2.0/cloud/thing/{device_id}/model`
  Returns the data model — useful for confirming which property *codes*
  this specific device declares before we go hunting for values.

The Power Management API service (which we already have subscribed) also
documents `GET /v1.0/iot-03/power-devices/{device_id}/balance-charge`
("Query Remaining Battery Capacity"), but that endpoint is intended for
energy meters/sub-meters, not IPC cameras — worth a probe but unlikely.

### How to verify locally

`scripts/test_battery3.py` walks all of the above and prints anything that
looks like battery data. Run it once with the project still in Standard
Instruction mode to confirm whether the `/v2.0/cloud/thing/.../shadow/...`
route exposes the DPs without any project changes; if it doesn't, flip the
device type to DP Instruction mode and re-run.

### Plan once we confirm an endpoint works

1. Add a `TuyaClient.get_battery_state()` method that returns
   `{percentage: int, power_source: "battery"|"ac", low: bool}`.
2. Read it from the main loop on a long interval (say once per hour, well
   inside the rate-limit budget — that's only ~720 calls/month) and log
   it. Optionally surface it via a future health endpoint.
3. Update this doc to reflect what actually worked.

We should not bake any of this into the production loop until the probe
script confirms which endpoint+mode combination this account can use.
