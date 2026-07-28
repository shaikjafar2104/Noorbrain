# NoorBrain v2 Phase 1 Audit

## Confirmed root cause: Activity 404

The existing `dashboard/js/activity.js` declares two different constants:

```javascript
const API = "/api/activity";
(() => {
  const API = window.location.origin;
```

The inner constant shadows the correct API prefix. The browser therefore requests:

```text
/activities?limit=100
```

instead of:

```text
/api/activity/activities?limit=100
```

The Phase 1A replacement removes this shadowing and supports both old and new response field names.

## NoorBrain findings

- `main.py` contains router registrations in two distant blocks.
- 19 backup/temporary source files are inside the working tree.
- Dashboard loads both `/dashboard-static/...` and `/dashboard/...` assets.
- HALO has overlapping implementations: `halo_bridge`, `offline_agent`, `ai_assistant`, and multiple dashboard fix scripts.
- Devices dashboard is injected through separate asset routes instead of the main static mount.
- The existing project should be stabilized incrementally, not rewritten.

## NoorCameraNode findings

- Camera Node is much cleaner than NoorBrain.
- One FastAPI application owns startup, health, diagnostics, stats, and MJPEG streaming.
- Camera Node does not need a rewrite.
- Recommended future cleanup: split the large `stream.py` into routes and lifecycle modules, while preserving existing endpoints.

## Phase 1A behavior

- Non-destructive installation.
- Full dashboard backup before replacement.
- Fixes Activity API path.
- Supports ISO and Unix timestamps.
- Supports `active_people`/`active_count` and `recorded_events`/`event_count`.
- Changes Activity polling from 2 seconds to 5 seconds.
- Does not delete any old files.
