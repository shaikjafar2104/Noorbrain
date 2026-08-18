# Human Activity Intelligence V12.6 — Specification

## Purpose

Human Activity Intelligence (HAI) consumes person-track, zone, and object
data from the existing camera vision pipeline and emits higher-level activity
observations into the existing event/rule pipeline. It extends the existing
NoorBrain architecture — no second engine is created.

## Architecture

```
Camera Vision → observe() → HumanActivityIntelligence → ActivityStore
                                          ↓
                           Pattern Learner (statistical)
                                          ↓
                           Rule Suggestions (neutral action)
                                          ↓
                            ReminderRulesEngine → PlaybackRouter → Pi
```

- **Prayer Intelligence** remains the authoritative prayer-time source.
- **Playback Router** remains the authoritative audio output.
- **ReminderRulesEngine** remains the authoritative rule evaluation engine.
- No new duplicate engines or services are introduced.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `LONG_SITTING_THRESHOLD_SECONDS` | `1800` | Dwell time to emit `long_sitting` |
| `INACTIVITY_THRESHOLD_SECONDS` | `600` | Dwell time to emit `inactivity` |
| `PHONE_USE_DWELL` | `60` | Dwell time after which phone object → `possible_phone_use` |
| `STATIONARY_MOTION_THRESHOLD` | `3.0` | Motion delta below which a person is stationary |
| `HIGH_MOTION_THRESHOLD` | `25.0` | Motion delta above which a person is `moving` |
| `TV_CONTEXT_ZONES` | `set()` | Configurable TV context zones (injectable per instance) |
| `TV_EVENING_START` | `16` | Earliest hour for TV context (4 PM) |
| `TV_EVENING_END` | `21` | Latest hour for TV context (9 PM) |

## Observable Activities

### Posture Classification
- **standing** — box height/width ratio ≥ 1.4
- **sitting** — box height/width ratio < 1.4

Posture and motion are **orthogonal** signals:
- A person can be **standing + stationary** or **sitting + stationary**
- High motion emits **moving**
- Both posture and motion events may be emitted for the same observation

### Event Types
| Event | Trigger | Confidence |
|-------|---------|------------|
| `activity_started` | First observation of a person/track | 0.30 |
| `activity_ended` | Person track disappears / stale timeout | 1.0 |
| `standing` | Standing posture | ramps 0.3 → 0.9 |
| `sitting` | Sitting posture | ramps 0.3 → 0.9 |
| `moving` | Motion delta ≥ HIGH_MOTION_THRESHOLD | 0.85 |
| `stationary` | Motion delta < STATIONARY_MOTION_THRESHOLD | 0.75 |
| `long_sitting` | Sitting ≥ LONG_SITTING_THRESHOLD_SECONDS | 0.9 |
| `inactivity` | Stationary ≥ INACTIVITY_THRESHOLD_SECONDS | 0.8 |
| `moved_zone` | Person moves to a different zone | 0.95 |
| `possible_phone_use` | Sitting + stationary + phone object + PHONE_USE_DWELL (LIMITED_CAPABILITY) | 0.55 |
| `possible_tv_context` | Stationary/sitting + TV zone + evening hours (PROBABILISTIC_ONLY) | 0.45 |

## Privacy Limits

- Snapshots are **disabled by default** (`snapshot_enabled` is None)
- Snapshots contain no camera/vision data — only session metadata
- No face recognition or identity inference

## Phone-Use Evidence Requirement

`observed_objects` passed to `observe()` represents objects **already associated
with the tracked person**. Phone use is ONLY emitted when:

1. The person has been sitting+stationary for ≥ `PHONE_USE_DWELL`
2. `observed_objects` contains a phone label (e.g. `"cell phone"`)

An unrelated phone elsewhere in the frame must NOT appear in the person's
`observed_objects`. `observed_objects=[]` produces no phone-use event.

`PHONE_USE_CAPABILITY = "LIMITED_CAPABILITY"` — never elevated to certain.

## TV Context

TV context is **PROBABILISTIC_ONLY** (`TV_CONTEXT_CAPABILITY = "PROBABILISTIC_ONLY"`).

- `tv_context_zones` is configurable per engine instance (e.g. `{"Hall"}`)
- TV context is eligible when zone ∈ tv_context_zones AND (sitting OR stationary)
- Time window: 4 PM–9 PM (configurable via `TV_EVENING_START`/`TV_EVENING_END`)
- `deterministic=False` — never displayed as a fact

## Patterns

Pattern learning is statistical, using `pattern_learner.py` with `store=`
injection. Patterns are built from recurring activity events in the same
person/zone/activity + compatible time window + usual days.

## Rule Suggestions

Human Activity learned suggestions remain **suggestions only**:

- Never auto-enabled
- Default action: `notification` (never Dua/Azkar automatically)
- User must explicitly approve/configure an action

## API Endpoints

```
GET  /api/human-activity-intelligence/health
GET  /api/human-activity-intelligence/settings
POST /api/human-activity-intelligence/settings
POST /api/human-activity-intelligence/observe
POST /api/human-activity-intelligence/observe-batch
GET  /api/human-activity-intelligence/events
GET  /api/human-activity-intelligence/events/recent
GET  /api/human-activity-intelligence/events/count
GET  /api/human-activity-intelligence/sessions
GET  /api/human-activity-intelligence/sessions/active
GET  /api/human-activity-intelligence/sessions/{session_id}
GET  /api/human-activity-intelligence/patterns
GET  /api/human-activity-intelligence/patterns/count
POST /api/human-activity-intelligence/patterns/rebuild
GET  /api/human-activity-intelligence/suggestions
GET  /api/human-activity-intelligence/suggestions/count
GET  /api/human-activity-intelligence/suggestions/{suggestion_id}
POST /api/human-activity-intelligence/suggestions/{suggestion_id}/dismiss
POST /api/human-activity-intelligence/suggestions/{suggestion_id}/snooze
POST /api/human-activity-intelligence/suggestions/{suggestion_id}/never-suggest
POST /api/human-activity-intelligence/suggestions/{suggestion_id}/approve
GET  /api/human-activity-intelligence/snapshots
GET  /api/human-activity-intelligence/snapshots/count
POST /api/human-activity-intelligence/snapshots
```

### Prayer / Adhan Integration

Prayer Intelligence produces prayer events (kind=`adhan`, `pre_prayer`).
The Adhan integration layer (`PrayerIntelligenceService.check_adhan_due`)
polls for due prayers and routes playback through the authoritative
Playback Router.

```
GET  /api/prayer-intelligence/health         — prayer status
GET  /api/prayer-intelligence/settings       — prayer settings
PATCH /api/prayer-intelligence/settings     — update settings
GET  /api/prayer-intelligence/times          — prayer times for a day
GET  /api/prayer-intelligence/status         — current prayer status
GET  /api/prayer-intelligence/due            — due events (adhan/pre_prayer)
POST /api/prayer-intelligence/test           — test prayer audio
POST /api/prayer-intelligence/acknowledge    — acknowledge prayer
GET  /api/prayer-intelligence/events         — prayer event history
GET  /api/prayer-intelligence/adhan/settings — Adhan config
PATCH /api/prayer-intelligence/adhan/settings — update Adhan config
POST /api/prayer-intelligence/adhan/check   — poll for due adhan
```

#### Adhan Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `adhan_enabled` | `true` | Global Adhan toggle |
| `adhan_target_node` | `existing-pi-audio` | Target Pi speaker node |
| `adhan_lead_minutes` | `0` | Minutes before prayer to trigger |
| `adhan_media_id` | `null` | Explicit verified Adhan media ID |

If no verified Adhan media is configured or found in the catalog, the
system returns truthful state `ADHAN_MEDIA_REQUIRED` — never silently
substitutes TTS or fabricated audio.

## Playback Router Contract

- Playback Router is the **sole** audio output path
- `laptop_fallback` is **always False**
- Playback failures are truthful: `status="failed"`, `laptop_fallback=False`
- All test calls mock/patch the authoritative `playback_router.play`

## Test Status

```
python3 -m py_compile services/human_activity_intelligence/*.py services/islamic_learning/*.py main.py
pytest tests/test_human_activity_islamic_ai_v126.py
```

49 tests, 0 failures, 0 errors.

Test command (environment-aware):
```
PYTHONPATH="" venv/bin/python -m pytest tests/test_human_activity_islamic_ai_v126.py
```
