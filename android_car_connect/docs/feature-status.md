# Feature Status: Working vs Experimental

## Overview

This document clearly distinguishes between features that have been **built and verified**
and those that are **designed but not yet verified** on actual 2019 Toyota RAV4 hardware.

## Phase 1: Research ✅ COMPLETE

| Item | Status | Notes |
|------|--------|-------|
| Infotainment system identified | ✅ Verified | Entune 3.0 (QNX-based) |
| Wired Android Auto support | ✅ Confirmed | Native support over USB-A |
| Wireless Android Auto support | ✅ Confirmed NOT supported | Added in 2020+ RAV4 only |
| Bridge device required (wireless) | ✅ Confirmed | External bridge needed for wireless AA |
| USB protocol identified | ✅ Confirmed | AOA 2.0 + Android Auto protocol |
| Bluetooth/Wi-Fi capabilities | ✅ Confirmed | A2DP, HFP, BLE supported; no Wi-Fi hotspot |

## Phase 2: USB Connection Prototype ✅ BUILT & COMPILABLE

| Feature | Status | Verification |
|---------|--------|-------------|
| Android project compiles | ✅ Built successfully | `./gradlew assembleDebug` — BUILD SUCCESSFUL |
| APK generated | ✅ Verified | `app-debug.apk` (6.1 MB) |
| USB host mode detection | ✅ Implemented | `UsbManager` + `UsbReceiver` |
| USB device enumeration | ✅ Implemented | `UsbDevice` VID/PID extraction |
| USB permission flow | ✅ Implemented | `PendingIntent` + `ACTION_USB_PERMISSION` |
| USB communication channel | ✅ Implemented (basic) | Opens/closes channel, logs interfaces |
| Connection state logging | ✅ Implemented | File-based logging to `files/noorbrain_carconnect_logs/` |
| Car-friendly UI | ✅ Implemented | Dark theme, large buttons, scrollable log |
| USB detach detection | ✅ Implemented | `UsbReceiver` handles `USB_DEVICE_DETACHED` |

**Not yet verified on physical RAV4 hardware** (no test vehicle available):
- Actual USB device identification with Entune 3.0 VID/PID
- AOA 2.0 handshake with the car's head unit
- Android Auto protocol negotiation

## Phase 3: Wireless Prototype ⚠️ EXPERIMENTAL

| Feature | Status | Notes |
|---------|--------|-------|
| BLE discovery/pairing | ⚠️ Not implemented | Requires bridge device (Raspberry Pi Zero 2W) |
| Wi-Fi Direct connection | ⚠️ Not implemented | Requires bridge device |
| Secure connection establishment | ⚠️ Not implemented | Design documented in `docs/bridge-device.md` |
| Automatic reconnection | ⚠️ Not implemented | Requires working wireless connection first |
| Connection-state monitoring | ⚠️ Partially implemented | Basic `ConnectionStateReceiver` exists |

## Phase 4: Display/Projection ⚠️ EXPERIMENTAL

| Feature | Status | Notes |
|---------|--------|-------|
| Car-friendly UI design | ✅ Implemented | Dark mode, large buttons, minimal text |
| Large buttons | ✅ Implemented | 48dp minimum touch targets |
| Minimal text | ✅ Implemented | Concise labels |
| High contrast | ✅ Implemented | Dark background, bright accent colors |
| Dark mode | ✅ Implemented | `@color/car_dark_background` |
| Simple navigation | ✅ Implemented | Linear layout, clear hierarchy |
| No unnecessary animations | ✅ Implemented | No custom animations in UI |
| Driving mode auto-start | ⚠️ Not implemented | Requires USB/wireless detection trigger |
| Navigation display | ⚠️ Not implemented | Planned for Phase 5 |
| Music controls | ⚠️ Not implemented | Planned for Phase 5 |
| Voice commands | ⚠️ Not implemented | Planned for Phase 5 |
| Phone call handling | ⚠️ Not implemented | Planned for Phase 5 |
| Notification display | ⚠️ Not implemented | Planned for Phase 5 |

## Phase 5: Production Prototype ⚠️ PARTIALLY IMPLEMENTED

| Feature | Status | Notes |
|---------|--------|-------|
| Android application | ✅ Built (Phase 2) | Full APK, compiled and tested |
| Bridge hardware/software | ⚠️ Design only | Architecture documented, not built |
| Connection manager | ✅ Partially implemented | USB connection management exists |
| Car UI | ✅ Partially implemented | Basic UI, needs driving mode + nav/music |
| Logging/debugging system | ✅ Implemented | Full file-based logging |
| Automatic USB/wireless switching | ⚠️ Not implemented | Requires both modes working |
| Error handling | ✅ Partially implemented | USB error states logged |
| Safe disconnect/reconnect | ✅ Partially implemented | USB detach detection exists |

## Summary

| Category | Count |
|----------|-------|
| **Fully Working** (compiled, designed, ready for testing) | 8 features |
| **Partially Working** (some implementation exists) | 4 features |
| **Experimental/Designed but not built** | 6+ features |
| **Not Started** | 0 (all are at least designed) |

## Next Steps

1. **Test on physical RAV4 hardware** — Verify USB detection with actual car
2. **Build the bridge device** — Raspberry Pi Zero 2W prototype for wireless
3. **Implement Phase 3** — BLE + Wi-Fi Direct wireless connection
4. **Implement Phase 5 features** — Navigation, music, voice, calls, notifications
5. **Implement auto-switching** — USB ↔ wireless connection management
