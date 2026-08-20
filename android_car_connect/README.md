# NoorBrain CarConnect — Android-to-RAV4 Bridge

> **Standalone bridge solution for 2019 Toyota RAV4 (Entune 3.0)**
> 
> Enables wireless Android Auto on 2019 RAV4 which only supports **wired** Android Auto natively.

## Overview

The 2019 Toyota RAV4's Entune 3.0 infotainment system supports Android Auto **only over wired USB**.
This project provides an **external bridge device** (Raspberry Pi Zero 2W) that:
1. Accepts a **wireless connection** from your Android phone (Wi-Fi Direct + BLE)
2. Presents itself as an **Android phone** to the RAV4's USB port (USB gadget mode)
3. **Proxies** the Android Auto protocol stream between phone and car

```
┌─────────────┐ WiFi Direct ┌──────────────┐ USB gadget ┌──────────────┐
│  Android    │ ←→ (Wi-Fi Direct) │  Raspberry Pi │ ←→ (USB AOA 2.0) │  2019 RAV4     │
│  Phone      │           │  Zero 2W       │              │  Entune 3.0     │
│ (render +   │           │ (Bridge Dev)   │              │ (Car Display)  │
│  control)   │           │                │              │               │
└─────────────┘           └──────────────┘              └──────────────┘
```

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Bridge device required | 2019 RAV4 does NOT support wireless Android Auto |
| USB for car connection | Car natively supports wired Android Auto |
| Wi-Fi Direct for phone | Most reliable wireless method for AA protocol |
| Raspberry Pi Zero 2W | Small, cheap, supports USB gadget mode |

## What's Included

### 1. Bridge Device Software
- **`rav4_bridge/bridge_server.py`** — Python proxy server (Wi-Fi ↔ USB)
- **`rav4_bridge/setup_usb_gadget.sh`** — Raspberry Pi USB gadget setup script

### 2. Android App (Phase 2 — USB Prototype)
- **`android_car_connect/`** — Complete Android Studio project
- Detects and logs USB connections to any device (for testing/verification)
- Car-friendly UI with dark theme, large buttons

### 3. Documentation
- `docs/rav4-research-phase1.md` — Phase 1 research findings
- `docs/architecture.md` — Full system architecture
- `docs/protocol.md` — USB/Bluetooth/Wi-Fi protocol documentation
- `docs/bridge-device.md` — Bridge device setup guide
- `docs/install-test.md` — Installation and testing procedure
- `docs/feature-status.md` — Working vs Experimental features

## Hardware Requirements

### Bridge Device
| Component | Specification |
|-----------|--------------|
| Board | Raspberry Pi Zero 2W |
| Storage | microSD card (16GB+, Class 10) |
| USB Cable | Micro USB to USB-A OTG adapter |
| Power | USB power supply (2.5A recommended) |

### Phone Side
| Requirement | Details |
|------------|---------|
| Android | 6.0+ (for USB host and Wi-Fi Direct) |
| Cable | USB-C to USB-A (for initial setup/debugging) |
| Wi-Fi | 802.11n/ac (for Wi-Fi Direct) |

### Car Side
- 2019 Toyota RAV4 with Entune 3.0
- USB-A port for the bridge connection

## Setup Instructions

### Step 1: Set Up the Bridge Device
```bash
# Flash Raspberry Pi OS Lite (64-bit) to microSD card
# Boot Pi, login, then run:
cd ~/NoorBrain/android_car_connect/rav4_bridge
chmod +x setup_usb_gadget.sh
sudo ./setup_usb_gadget.sh

# Reboot when prompted
sudo reboot
```

### Step 2: Start the Bridge Service
```bash
# After reboot, start the bridge service
sudo systemctl start carconnect-bridge

# Check status
sudo systemctl status carconnect-bridge

# View logs
journalctl -u carconnect-bridge -f
```

### Step 3: Connect Phone to Bridge
1. On your phone, enable Wi-Fi Direct
2. Scan for devices — look for "RAV4-CarConnect-Bridge" 
3. Connect to the bridge
4. Open Android Auto on your phone
5. The bridge will automatically proxy the connection to the car

## Testing

### Test 1: USB Detection (Phase 2 App)
```bash
# Build and install the Android app
cd android_car_connect
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk

# Plug phone into RAV4 USB port
# Open app — should detect and log the connection
```

### Test 2: Bridge Device
```bash
# With bridge device connected to RAV4 USB port:
# 1. Phone connects via Wi-Fi Direct to bridge
# 2. Bridge logs should show both connections
# 3. Car display should show Android Auto interface
```

## Safety & Limitations

### Safety
- ✅ Does NOT modify vehicle safety systems
- ✅ Does NOT send commands to steering, braking, or airbags
- ✅ Does NOT bypass cryptographic authentication
- ✅ Focuses only on infotainment/projection

### Limitations
- ⚠️ Bridge device is **experimental** — not tested on actual RAV4 hardware
- ⚠️ Requires USB gadget mode support on Pi (Pi Zero 2W confirmed compatible)
- ⚠️ Wi-Fi Direct may have latency (typically 10-30ms)
- ⚠️ Power consumption: Pi Zero 2W draws ~500mA from USB

## Project Structure

```
android_car_connect/
├── app/                    # Android app (Phase 2 USB prototype)
│   ├── src/main/
│   │   ├── java/com/noorbrain/carconnect/
│   │   │   ├── CarConnectApp.kt
│   │   │   ├── MainActivity.kt
│   │   │   ├── LogAdapter.kt
│   │   │   ├── core/
│   │   │   │   ├── ConnectionStateManager.kt
│   │   │   │   ├── ConnectionStateLogger.kt
│   │   │   │   └── ConnectionStateReceiver.kt
│   │   │   ├── usb/
│   │   │   │   ├── UsbReceiver.kt
│   │   │   │   └── UsbCommunicationService.kt
│   │   │   └── wireless/
│   │   │       └── WirelessConnectionManager.kt  # Phase 3
│   │   └── res/
│   ├── build.gradle
│   └── proguard-rules.pro
├── docs/                   # Documentation
│   ├── rav4-research-phase1.md
│   ├── architecture.md
│   ├── protocol.md
│   ├── bridge-device.md
│   ├── install-test.md
│   └── feature-status.md
├── rav4_bridge/            # Bridge device software
│   ├── bridge_server.py    # Python proxy server
│   └── setup_usb_gadget.sh # Pi USB gadget setup
├── build.gradle
├── settings.gradle
├── gradle.properties
└── README.md
```
