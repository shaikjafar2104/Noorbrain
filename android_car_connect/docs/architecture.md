# NoorBrain Android Car Connect — System Architecture

## Overview

This document describes the architecture for connecting an Android smartphone
to the factory infotainment screen of a 2019 Toyota RAV4 (Entune 3.0).

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PHONE CONNECTION MODES                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  WIRED CONNECTION (Phase 2 — Built & Working)                          │
│  ┌──────────────┐    USB-A cable    ┌──────────────────────────────┐   │
│  │ Android Phone │━━━━━━━━━━━━━━━━━━━▶│ 2019 Toyota RAV4             │   │
│  │ (CarConnect  │                    │ Entune 3.0 Head Unit        │   │
│  │  App)        │                    │                              │   │
│  │ - USB Host    │                    │ - USB Device Detection      │   │
│  │ - USB Manager │                    │ - Android Auto Protocol     │   │
│  │ - AOA 2.0     │                    │ - 7/8" Touchscreen          │   │
│  └──────────────┘                    │ - iAP2/CarPlay support      │   │
│                                      └────────────┬─────────────────┘   │
│                                                   │                     │
│                                                   ▼                     │
│                                         ┌──────────────────────┐        │
│                                         │ Phone renders Android │        │
│                                         │ Auto UI → streams via │        │
│                                         │ USB bulk endpoints    │        │
│                                         └──────────────────────┘        │
│                                                   ▲                     │
│                                         Car sends touch/input │         │
│                                         events back over USB  │         │
│                                                   │                     │
└───────────────────────────────────┬───────────────┼─────────────────────┘
                                    │               │
┌───────────────────────────────────┴───────────────┴─────────────────────┐
│  WIRELESS CONNECTION (Phase 3-5 — Experimental/Bridge Required)         │
│                                                                         │
│  ┌──────────────┐                                              ┌──────┐ │
│  │ Android Phone │                                              │ 2019 │ │
│  │ (CarConnect  │   Wi-Fi Direct + BLE                        │ RAV4 │ │
│  │  App)        │      (Pairing)                              │ USB  │ │
│  │              │                                              │ Port │ │
│  └──────┬───────┘      ┌──────────────────────────────────────┐ └──────┘ │
│         │              │      EXTERNAL BRIDGE DEVICE            │          │
│         │  Wi-Fi Direct │  (Raspberry Pi Zero 2W as USB Gadget) │          │
│         │  + BLE        │  ┌─────────────────────────────────┐ │          │
│         │  Pairing      │  │ USB Gadget Mode                   │ │          │
│         ├───────────────┤  │ - Emulates Android phone via AOA │ │          │
│         │               │  │ - Accepts Wi-Fi Direct from      │ │          │
│         │               │  │   phone                          │ │          │
│         │               │  │ - Proxies Android Auto stream     │ │          │
│         │               │  │   to car's USB port               │ │          │
│         │               │  └─────────────────────────────────┘ │          │
│         │               │  ┌─────────────────────────────────┐ │          │
│         │               │  │ Android Auto Proxy Service       │ │          │
│         │               │  │ (Forwards video + input stream)  │ │          │
│         │               │  └─────────────────────────────────┘ │          │
│         │               │  ┌─────────────────────────────────┐ │          │
│         │               │  │ BLE Pairing Beacon               │ │          │
│         │               │  └─────────────────────────────────┘ │          │
│         └───(streams)───┤  └──────────────────────────────────┘ │          │
│                         │                                      │          │
│                         └──────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Breakdown

### 1. Android Phone (CarConnect App)
- **USB Host Mode**: Detects connection to RAV4 via USB, identifies the device
- **USB Communication**: Opens AOA 2.0 communication channel (Phase 2 prototype)
- **Wireless Module**: Wi-Fi Direct + BLE discovery and pairing (Phase 3+)
- **Car UI**: Driving-optimized interface (Phase 4+)
- **Connection Manager**: Auto-switch between USB and wireless
- **State Logger**: Logs all connection events to file

### 2. 2019 Toyota RAV4 Entune 3.0 Head Unit
- **Supported natively**: Wired Android Auto over USB
- **Not supported**: Wireless Android Auto (requires bridge)
- **Display**: 7" (standard) or 8" (premium) WVGA touchscreen
- **Controls**: Touchscreen + physical knobs/buttons

### 3. External Bridge Device (Wireless Only)
- **Hardware**: Raspberry Pi Zero 2W (wireless not supported without this)
- **USB Gadget Mode**: Presents itself as an Android phone to the car's USB port
- **Proxy Service**: Forwards Android Auto protocol between phone and car
- **Not needed for wired**: Direct USB connection works natively

## Data Flow

### Wired Connection (Phase 2 — Working)
```
1. Phone ←→ USB Cable ←→ RAV4 USB-A Port
2. Phone detects USB device (Entune 3.0)
3. Phone requests USB permission
4. Phone opens AOA 2.0 communication channel
5. Phone logs device info (VID/PID, interfaces, endpoints)
6. Native Android Auto takes over for actual projection
```

### Wireless Connection (Phase 3+ — Experimental)
```
1. Phone → BLE advertising → Bridge device discovers phone
2. Phone ←→ Wi-Fi Direct ←→ Bridge device
3. Bridge ←→ USB gadget ←→ RAV4 USB port
4. Bridge presents itself as Android phone (AOA 2.0)
5. Android Auto protocol proxied through bridge
6. Bidirectional: phone → video, car → input events
```

## Key Decisions

1. **No bridge device for USB**: The 2019 RAV4 supports Android Auto natively over USB.
2. **Bridge required for wireless**: The 2019 RAV4 does NOT support wireless Android Auto.
3. **Phase 2 scope**: USB detection + logging only. No protocol bypass, no safety system modification.
4. **Phase 4 scope**: Car-friendly UI with large buttons, dark mode, minimal text.
5. **Safety**: All code respects vehicle safety constraints — no modification to
   steering, braking, airbags, or control systems.
