# NoorBrain v2 Phase 1B — HALO Cleanup

## Confirmed current architecture

The uploaded project contains four overlapping HALO-related layers:

- Legacy dashboard handler in `dashboard/js/app.js` using `POST /halo`
- `services/halo_bridge` using `POST /api/halo/chat`
- `services/offline_agent` using `POST /api/offline-agent/chat`
- Old dashboard repair scripts:
  - `dashboard/js/halo_fix.js`
  - `dashboard/js/halo_studio_fix.js`

The current dashboard only loads `app.js`, so it still uses the legacy `/halo` endpoint even though the verified offline agent is installed.

## Phase 1B decision

The dashboard now has one owner for HALO UI behavior:

```text
dashboard/js/halo.js
```

It uses:

```text
POST /api/offline-agent/chat
```

This gives deterministic skill routing, verified device status, automation tools, local Ollama conversation, caching, and action confirmation.

## Safety

- Full dashboard and `main.py` backup is created before installation.
- Legacy fix scripts are moved to `dashboard/legacy/halo/`.
- The old HALO submit binding in `app.js` is disabled, not broadly rewritten.
- Backend HALO routes remain available for compatibility.
