# Communication Protocol Documentation

## 1. USB Protocol (Wired Connection)

### Physical Layer
- **Connector**: USB-A (female) on the RAV4 dashboard
- **Cable**: USB-A to phone (USB-C or micro-USB depending on phone)
- **Power**: 5V / up to 1.5A (powers and charges the phone)
- **Data Rate**: Full-Speed (12 Mbps) or High-Speed (480 Mbps)

### USB Detection Sequence (Phase 2)

```
1. Phone is connected to RAV4 USB-A port
2. USB controller on phone detects VBUS (host mode)
3. Phone sends USB reset signal
4. Phone enumerates the connected device:
   a. Sends GET_DESCRIPTOR request
   b. Reads device descriptor (VID, PID, class, etc.)
   c. Reads configuration descriptors
5. Android broadcasts USB_DEVICE_ATTACHED intent
6. UsbReceiver catches the intent
7. ConnectionStateManager records device info
8. ConnectionStateLogger writes to log file
9. UsbCommunicationService requests permission
10. If granted, opens a basic communication channel
```

### Android Auto USB Protocol

When the phone switches to Android Auto mode:

```
1. Phone enters "Android Auto" USB mode (vendor-specific)
2. Car's head unit detects the phone is in AA mode
3. AOA 2.0 (Android Open Accessory) handshake:
   a. Car sends AOA handshake via USB control transfers
   b. Phone responds with AA protocol version
   c. Car sends feature request
   d. Phone sends features and returns to accessory mode
4. Data transfer:
   - Video frames: USB bulk IN endpoints (phone → car)
   - Input events: USB bulk OUT endpoints (car → phone)
   - Control: USB control transfers (bidirectional)
5. Video resolution: 800×480 (matches RAV4 screen)
6. Frame rate: Up to 60 fps (typically 30 fps for AA)
```

### USB Vendor/Product IDs for RAV4 Detection

| Component | Vendor ID | Product ID | Description |
|-----------|-----------|------------|-------------|
| Generic Android Auto | 0x18D9 | Varies | Standard AA VID |
| Toyota Entune 3.0 (car side) | Unknown | Unknown | Car presents as generic USB device |
| iPhone (CarPlay) | 0x05AC | Varies | Apple VID (for reference) |

**Note**: The RAV4 head unit acts as the USB host. The phone is the device.

### USB Interface Classes

| Class | Description | Used by |
|-------|-------------|---------|
| 0x02 | Communications | Serial/debug |
| 0x03 | HID | Input devices |
| 0xFF | Vendor-specific | Android Auto, CarPlay |
| 0x00 | Per-interface | Defined in interface descriptors |

## 2. Wireless Protocol (Bridge Required)

### Bluetooth LE Discovery Phase

```
1. Bridge device advertises as "RAV4-CarConnect-Bridge" (BLE)
2. Phone scans for BLE devices with "CarConnect" prefix
3. BLE connection established (encrypted)
4. GATT service discovery:
   Service UUID: 0x1800 (Generic Access)
   Characteristic: Device Name
   Characteristic: Appearance
5. Phone sends pairing code (displayed on both devices)
6. Pairing complete
```

### Wi-Fi Direct Connection Phase

```
1. Phone initiates Wi-Fi Direct connection to bridge
2. Wi-Fi P2P connection established (5GHz preferred)
3. IP address assigned (bridge acts as group owner)
4. TCP connection on port 5353 (Android Auto wireless port)
5. Authentication handshake:
   a. Phone sends connection request
   b. Bridge verifies pairing (from BLE phase)
   c. Secure TLS channel established
6. Audio/video stream over TCP/UDP
```

### Android Auto Wireless Protocol

```
1. Phone renders AA UI at 800×480
2. Video encoded (H.264) and sent over Wi-Fi
3. Car sends touch/input events back over Wi-Fi
4. Audio (if not using Bluetooth A2DP) sent over the same channel
5. Voice commands via the phone's microphone (phone handles ASR)
```

## 3. Protocol State Machine

```
DISCONNECTED
    │
    ├── USB_CABLE_INSERTED ──┐
    │                        ▼
    │                   USB_DETECTED
    │                        │
    │                        ▼
    │                   USB_PERMISSIONS_REQUESTED
    │                        │
    │              ┌────────┴────────┐
    │              │                 │
    │   PERMISSION_GRANTED     PERMISSION_DENIED
    │              │                 │
    │              ▼                 ▼
    │        USB_CHANNEL_OPEN    ERROR
    │              │
    │   ┌──────────┴──────────┐
    │   │                     │
    │ NATIVE_AA_HANDOFF   COMMUNICATION_ERROR
    │   │                     │
    │   ▼                     ▼
    │ PROJECTION_ACTIVE      RECOVER
    │   │
    │   ▼
    │ DRIVE_MODE_ACTIVE
    │   │
    │   ┼── USB_DETACHED ──▶ DISCONNECTED
    │   │
    │   ▼
    └── BRIDGE_REQUESTED (wireless)
         │
         ▼
       BT_DISCOVERY
         │
         ▼
       BT_PAIRING
         │
         ▼
       WIFI_DIRECT_CONNECT
         │
         ▼
       BRIDGE_ACTIVE (proxy to USB)
         │
         ▼
       PROJECTION_ACTIVE
         │
         ▼
       DRIVE_MODE_ACTIVE
```

## 4. Log Format

All connection events are logged in the format:

```
YYYY-MM-DD HH:MM:SS.mmm | STATE_ENUM | message
```

Example:
```
2026-08-19 23:03:45.123 | USB_ATTACHED | Device attached: /dev/bus/usb/001, VID=0x18D9, PID=0x4025
2026-08-19 23:03:45.234 | USB_PERMISSION_GRANTED | Permission granted for: /dev/bus/usb/001
2026-08-19 23:03:45.345 | USB_COMM_OPEN | USB device opened: /dev/bus/usb/001
2026-08-19 23:03:45.456 | USB_COMM_OPEN | Interface 0: ID=0, Class=255, Name=android-auto, Endpoints=2
2026-08-19 23:03:45.567 | USB_COMM_CLOSE | USB test channel closed: /dev/bus/usb/001
```

## 5. Safety and Constraints

### What This Protocol Does
- Detects USB connection to vehicle
- Logs device identification information
- Opens and closes a standard USB communication channel
- Does NOT send commands to vehicle control systems
- Does NOT bypass authentication

### What This Protocol Does NOT Do
- Does NOT modify steering/braking/airbag systems
- Does NOT bypass cryptographic authentication
- Does NOT circumvent security mechanisms
- Does NOT interfere with vehicle safety systems
