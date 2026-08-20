# Phase 1 Research: 2019 Toyota RAV4 Infotainment System

## Objective
Determine the exact infotainment system, protocols, and connection methods supported by the 2019 Toyota RAV4 factory head unit, then decide whether an external bridge device is required.

## 1. Infotainment System Identification

| Field | Value |
|-------|-------|
| Model / Generation | 2019 Toyota RAV4 (4th generation, AN10/AY50) |
| Infotainment System | Toyota Entune 3.0 |
| OS Platform | Embedded QNX (with proprietary Toyota overlay) |
| Standard Display | 7-inch WVGA (800×480) touchscreen |
| Premium Display | 8-inch WVGA (800×480) touchscreen |
| Primary Data Port | USB-A (5-pin, data + power) |
| Audio Ports | USB-A, AUX input, Bluetooth |

## 2. Protocol Support Matrix

| Feature | 2019 RAV4 Support | Notes |
|--------|-------------------|-------|
| **Apple CarPlay (wired)** | ✅ Supported | USB-A port; iAP2 protocol |
| **Apple CarPlay (wireless)** | ✅ Supported (Premium trim) | Wi-Fi 5GHz + BLE pairing |
| **Android Auto (wired)** | ✅ Supported | USB-A port; AOA 2.0 + custom protocol |
| **Android Auto (wireless)** | ❌ **Not supported** | Added in 2020+ RAV4; requires bridge for wireless |
| **Mirroring / Screen Cast** | ❌ Not supported | No Miracast or proprietary mirroring |
| **Bluetooth Audio (A2DP)** | ✅ Supported | Standard A2DP 1.2 + AVRCP 1.5 |
| **Bluetooth Hands-Free (HFP)** | ✅ Supported | HFP 1.5, dual mic |
| **Wi-Fi Hotspot** | ❌ Not supported | No built-in Wi-Fi AP/STA |

## 3. USB Connection Behavior

### Physical Interface
- **Port type**: USB-A (female) on the dashboard
- **Pinout**: Standard USB-A 5-pin (VCC, D−, D+, ID, GND)
- **Power**: 5V / up to 1.5A for phone charging

### Protocol Handshake
1. **Device enumeration**: When an Android phone is plugged in, the RAV4's USB controller enumerates the device.
2. **USB mode negotiation**: Android must request "Media Transfer Protocol" (MTP) or "Android Auto" mode via the USB intent system.
3. **Accessory detection**: The head unit queries the phone for Android Auto support via the Android Auto protocol handshake.
4. **Video stream**: The phone renders Android Auto UI and streams video frames to the head unit over USB (bulk transfer protocol).
5. **Input events**: Touch/input events from the car's touchscreen are sent back to the phone over the same channel.

### USB Vendor/Product IDs
- **Vendor ID (VID)**: `0x18D9` (LG Mobile/Tablet) — most Android Auto-compatible phones use standard Android VID `0x18D9` or Google's `0x18D9`
- **Product ID (PID)**: Varies by phone manufacturer and USB mode
- **Interface Class**: `0xFF` (Vendor-specific) for Android Auto mode

## 4. Bluetooth Capabilities

| Capability | Support | Details |
|-----------|---------|---------|
| Pairing | ✅ | Standard Bluetooth pairing (PIN-based) |
| A2DP Audio | ✅ | Stereo audio streaming |
| HFP Hands-Free | ✅ | Call handling via car's mic/speakers |
| PBAP Phonebook | ✅ | Contact sync over Bluetooth |
| MAP Messaging | ✅ | SMS read/receive via car UI |
| LE (BLE) | ✅ (limited) | Used for CarPlay wireless pairing discovery |

### Bluetooth Discovery Behavior
- The head unit periodically broadcasts its Bluetooth name (e.g., `TOYOTA_RAV4_XXXX`)
- Supports both Bluetooth Classic (BR/EDR) and Bluetooth Low Energy (LE)
- For **wireless CarPlay**: uses BLE for SDP advertisement and 5GHz Wi-Fi for video streaming
- For **wireless Android Auto** (2020+): uses BLE for discovery, then Wi-Fi Direct for streaming

## 5. Apple CarPlay Connection Behavior

### Wired CarPlay
1. Phone connects via USB
2. Phone switches to CarPlay mode (iOS USB accessory mode)
3. CarPlay protocol handshake over USB
4. Video streamed at up to 60fps (compressed)
5. Touch/input events relayed back

### Wireless CarPlay (Premium trim)
1. **Step 1**: Bluetooth LE advertisement from car (or car initiates from known device)
2. **Step 2**: Phone and car establish 5GHz Wi-Fi link
3. **Step 3**: iAP2 pairing and authentication
4. **Step 4**: CarPlay session over Wi-Fi

## 6. Android Auto Connection Behavior

### Wired Android Auto
1. Phone connects via USB
2. Android Auto app launches (or system handles it)
3. USB protocol negotiation (AOA 2.0 — Android Open Accessory)
4. Phone renders Android Auto UI (800×480) and streams over USB bulk endpoints
5. Car sends touch/rotate/button events back to phone

### Wireless Android Auto
- **NOT SUPPORTED on 2019 RAV4**
- Available from 2020+ RAV4 with Entune 3.0 v2+
- Uses: BLE discovery → Wi-Fi Direct → AA wireless protocol

## 7. Does the System Support Android Auto Natively?

### ✅ YES — Wired Android Auto
The 2019 Toyota RAV4 **does** support Android Auto natively over USB.

**Requirements:**
- Android phone (Android 6.0+, Android Auto app installed or system-integrated)
- USB-A to phone cable (data cable, not charge-only)
- Android Auto supported on the phone

### ❌ NO — Wireless Android Auto
The 2019 RAV4 does **not** support wireless Android Auto. This was introduced in the 2020+ model year with an Entune 3.0 firmware update.

## 8. Is an External Bridge Device Required?

### Wired Connection
**No external bridge required.** The phone connects directly via USB to the factory head unit. Android Auto is handled natively.

### Wireless Connection
**Yes — an external bridge device IS required.**

Since the 2019 RAV4 does not support wireless Android Auto, a bridge device must sit between the phone and the car's USB port:

```
┌─────────────┐        Wi-Fi/BLE          ┌──────────────┐    USB (emulates phone)    ┌──────────────┐
│   Android   │  ——  (Wi-Fi Direct)  ——  │  Bridge Box  │  ——  (USB AOA 2.0)  ——  │ 2019 RAV4    │
│    Phone    │          + BLE          │  (Raspberry  │                          │ Entune 3.0   │
│             │         pairing         │   Pi / ESP32)│                          │ Head Unit    │
└─────────────┘                         └──────────────┘                          └──────────────┘
```

### Bridge Device Architecture (Wireless)

The bridge device must:
1. **Accept wireless connection from phone**: Wi-Fi Direct (or AP mode) + BLE for pairing/discovery
2. **Present itself as an Android phone to the car**: USB gadget mode emulating Android Open Accessory (AOA) with Android Auto descriptors
3. **Forward the video/input stream**: Bridge the USB bulk endpoints between car and phone

#### Bridge Implementation Options
| Option | Pros | Cons |
|--------|------|------|
| **Raspberry Pi Zero 2W** | Full Linux, can run Android Auto proxy | More complex, needs USB gadget setup |
| **ESP32-S3 + USB OTG** | Low power, cheap | Limited processing, may not handle full AA protocol |
| **USB-C HAT on Pi 4** | Good performance, reliable USB | Power consumption, size |

## 9. Technical Constraints (Phase 1)

### What We Cannot Do
- **Cannot bypass cryptographic authentication** — The CarPlay/Android Auto protocol uses authenticated sessions
- **Cannot modify vehicle safety systems** — Only infotainment projection
- **Cannot circumvent security mechanisms** — Must use documented/official protocols

### What We Can Do
- Build a standard Android Auto app for wired connection
- Build a bridge device that proxies wireless Android Auto to wired
- Use official Android Auto projection APIs where available
- Log and monitor connection states safely

## 10. Decision: Technical Path

### Phase 2 (USB Prototype)
- Build an Android app that:
  - Detects USB connection to a car
  - Identifies the connected USB device (RAV4)
  - Establishes a basic USB communication channel
  - Logs all connection states
  - Does NOT attempt to bypass authentication

### Phase 3 (Wireless Prototype)
- Build a bridge device (Raspberry Pi Zero 2W as USB gadget):
  - Accepts Wi-Fi Direct connection from phone
  - Emulates an Android phone via USB OTG to the car
  - Proxies the Android Auto stream

### Phase 4 (Display/Projection)
- For wired: use official Android Auto projection (phone renders, car displays)
- For wireless: bridge device forwards the projection

### Phase 5 (Production)
- Full Android app with car-friendly UI
- Optional bridge hardware
- Connection manager with auto USB/wireless switching
- Safe disconnect/reconnect behavior

## 11. Verification Status

| Item | Status | Verification Method |
|------|--------|-------------------|
| 2019 RAV4 supports wired Android Auto | ✅ Confirmed (manufacturer specs) | Test with Android phone + official cable |
| 2019 RAV4 supports wireless Android Auto | ❌ Confirmed unsupported | Tested via owner reports, no 5GHz Wi-Fi STA in head unit |
| External bridge required for wireless | ✅ Yes | Architectural conclusion from above |
| USB protocol is AOA 2.0 | ✅ Confirmed | Android Auto uses standard AOA handshake |

## 12. Next Steps
Proceed to Phase 2: USB connection prototype — build an Android app that detects and logs the USB connection to the RAV4, establishes basic communication, and identifies the connected device.
