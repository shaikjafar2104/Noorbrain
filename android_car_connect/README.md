# NoorBrain Android Car Connect — Phase 2 USB Prototype

## Project Overview

This Android application enables a smartphone to connect to the factory infotainment
system of a 2019 Toyota RAV4. Phase 2 implements the **USB connection prototype**:

- Detects USB connection to the RAV4
- Identifies the connected USB device
- Establishes a basic communication channel
- Logs all relevant connection states

### Phase 1 Decision: External Bridge NOT Required for USB

> See `../../../docs/rav4-research-phase1.md` for the full research report.
>
> **Key finding:** The 2019 Toyota RAV4 (Entune 3.0) supports Android Auto natively over USB.
> No external bridge device is needed for wired connection.
>
> For **wireless** connection (Phase 3+), a bridge device IS required because
> the 2019 RAV4 does not support wireless Android Auto (introduced in 2020+ models).

## Build Instructions

```bash
cd android_car_connect
./gradlew assembleDebug
```

### Prerequisites
- Android SDK with platform 35 and build-tools 35.0.0
- Java 17+
- Network access (for first-time Gradle dependency resolution)

### ADB Install
```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

## Phase 2 Features
1. USB host mode detection
2. Device enumeration and identification
3. Connection state logging
4. Basic serial communication test
5. UI for monitoring connection status
