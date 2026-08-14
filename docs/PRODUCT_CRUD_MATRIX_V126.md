# NoorBrain V12.6 Product and CRUD Matrix

This matrix records the operations actually implemented by the current backend. A dash means that the backend does not expose that operation; the UI must not imply otherwise. A zero-item list is a valid runtime state.

| Entity | List / view | Add | Edit | Delete | Enable / disable | Run / test | Refresh | Backend route | Mobile V12.6 | Desktop product UI |
|---|---|---|---|---|---|---|---|---|---|---|
| Devices | Yes | Yes | Yes | Yes | Control only when online | Toggle/on/off; honest offline error | Yes | `/api/devices` | Dedicated Devices list and form | Dedicated Devices page |
| Cameras | Yes | Yes | — | Yes | — | Live primary feed remains `/camera_live` | Yes | `/api/mobile-v2/config`, `/api/mobile-v2/cameras` | Camera page keeps live feed and manages configurations | Vision page includes camera manager |
| Zones | Yes | Yes | Yes | Yes | Via edit | — | Yes | `/api/vision-zones/zones` | Existing native V12.6 Zones page, now with bounds CRUD | Dedicated Zones manager |
| Smart automation rules | Yes | Yes | Yes | Yes | Yes | Evaluate/run with persisted run history | Yes | `/api/smart-automation/rules`, `/evaluate`, `/runs` | Full-screen Automation Center | Full-screen Automation Center launched from selected sidebar item |
| Scenes | Yes | Yes | Yes | Yes | Yes | Execute | Yes | `/api/automation/scenes` | Full-screen Automation Center | Full-screen Automation Center |
| Routines | Yes | Yes | Yes | Yes | Yes | Run now | Yes | `/api/automation/routines` | Full-screen Automation Center | Full-screen Automation Center |
| Reminder rules | Yes | Yes | Yes | Yes | Yes | Test | Yes | `/reminder-rules` | Existing mobile Reminder Rules manager | Dedicated Reminder Rules page |
| Smart Islamic rules | Yes | Yes | Yes | Yes | Yes | Evaluate event/zone match | Yes | `/api/islamic-intelligence-v12` | Dedicated Smart Islamic Rules page | Dedicated Smart Islamic Rules page |
| Dua / Azkar | Via media | Via upload | Association metadata | Yes | — | Browser play/preview | Yes | `/api/media` | Dedicated Media page with Islamic association | Dedicated Media Library page |
| Media Library | Yes | Upload | Name/category/association | Yes | — | Browser play/preview; server playback remains available | Yes | `/api/media` | Dedicated Media page | Dedicated Media Library page |
| Notifications | Yes | Backend publish only | Delivery settings | Yes | Mark all read/archive actions | Action routes | Yes | `/api/mobile-notifications` | Dedicated Notifications page | Dedicated Notifications page |
| Prayer configuration | Times/status/events | — | Settings | — | Settings fields | Prayer test | Yes | `/api/prayer-intelligence` | Dedicated Prayer page | Dedicated Prayer page |
| HALO settings | View | — | Preferences | — | Voice/preferences fields | HALO chat and voice diagnostics | Yes | `/api/noor-settings-v11`, `/api/halo-conversation/chat`, `/api/halo-voice` | Settings and HALO pages | HALO and Voice Runtime pages |
| Voice settings | View | — | Preferences | — | Supported preference fields | Transcribe/diagnostics | Yes | `/api/noor-settings-v11`, `/api/halo-voice` | Settings and HALO page | Voice Runtime page |
| Habit Learning | Patterns/suggestions | Import observations | — | — | — | Rebuild patterns/generate suggestions | Yes | `/api/habit-learning` | Dedicated Habit Learning page | Dedicated Habit Learning page |
| Family | Yes | Yes | Yes | Yes | Recognition privacy setting | Presence is event-driven | Yes | `/api/family-intelligence-v11` | Dedicated Family page | Dedicated Family page |
| Plugins | Yes | Install manifest | — | Yes | Yes | — | Yes | `/api/plugin-platform-v13` | Dedicated Plugins page | Dedicated Plugins page |

## Product navigation rule

Normal desktop navigation activates one routed product page at a time. Studio-only global panels are hidden from product navigation. Mobile navigation stays inside the V12.6 shell; Camera, Activity, Zones, Home, HALO, Islamic, Automation, More, and the bottom navigation are not replaced with desktop Studio fallbacks.

## HALO native bridge contract

The installed APK owns the native audio-recorder plugin in its top-level Capacitor page and exchanges `noorbrain-native-record-toggle`, `noorbrain-native-listening`, `noorbrain-native-processing`, `noorbrain-native-transcript`, and `noorbrain-native-error` messages with the remote V12.6 iframe. The web state machine also supports direct Capacitor plugin access when a future wrapper exposes it inside the frame. Both paths have deterministic start, recording, and processing timeouts and lifecycle diagnostics.
