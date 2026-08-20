# Installation & Testing Procedure — 2019 Toyota RAV4

## Prerequisites

### For Wired Connection (Phase 2)
- Android phone (Android 6.0+)
- USB-A to USB-C (or micro-USB) data cable
- No additional hardware required

### For Wireless Connection (Phase 3+)
- Same as above, plus:
- Raspberry Pi Zero 2W (bridge device)
- MicroSD card (16GB+)
- USB OTG adapter (micro USB or USB-C to USB-A, depending on Pi model)
- Wi-Fi capable Android phone (Wi-Fi Direct support)

## Installation — Android App

### Option A: Build from Source
```bash
# 1. Install Android Studio (if not already installed)
#    Download from https://developer.android.com/studio

# 2. Open the project
cd android_car_connect/
# In Android Studio: File → Open → select this directory

# 3. Build the APK
# In Android Studio: Build → Generate Signed Bundle/APK → APK → Debug

# Or via command line:
./gradlew assembleDebug
# Output: app/build/outputs/apk/debug/app-debug.apk
```

### Option B: Install via ADB
```bash
# Connect phone via USB, enable Developer Options + USB Debugging
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

### Enable USB Debugging on Phone
1. Settings → About phone → tap "Build number" 7 times
2. Settings → System → Developer options → USB debugging: ON
3. Connect phone to computer via USB
4. Tap "Allow" on the phone when prompted

## Testing Procedure

### Phase 2: USB Connection Test

#### Test 2.1: USB Detection
1. Launch the CarConnect app on the phone
2. Plug the phone into the RAV4's USB-A port using a data cable
3. Observe the app UI:
   - "USB: Connected" should appear
   - Device details (VID/PID) should be displayed
   - Connection mode should show "USB_CONNECTED"
4. Check the log — entries should include:
   - `USB_ATTACHED` with device name and VID/PID
   - `USB_DEVICE_FOUND` with interface count
   - `USB_COMM_OPEN` when channel opens
   - `USB_COMM_CLOSE` when test completes
5. Unplug the cable
6. Verify "USB: Disconnected" appears and log shows `USB_DETACHED`

#### Test 2.2: USB Permission Flow
1. On a fresh app install, plug phone into RAV4 USB port
2. Android should show a USB permission dialog
3. Tap "OK" to grant permission
4. Verify the app logs `USB_PERMISSION_GRANTED`
5. If permission is denied, verify `USB_PERMISSION_DENIED` is logged

#### Test 2.3: Log File Verification
1. Complete Test 2.1
2. Connect phone to computer via ADB
3. Pull the log file:
```bash
adb shell run-as com.noorbrain.carconnect cat files/noorbrain_carconnect_logs/connection_log.txt
```
4. Verify the log contains properly formatted entries with timestamps

#### Test 2.4: No Safety System Interaction
1. Verify the app NEVER sends commands to vehicle control systems
2. Verify the app does NOT bypass any authentication
3. Verify all USB communication is logged and read-only (diagnostic only)

### Phase 3: Wireless Connection Test (Experimental)

> ⚠️ This phase requires the bridge device and is EXPERIMENTAL.
> Not all features are verified on actual 2019 RAV4 hardware.

#### Test 3.1: BLE Discovery
1. Power on the bridge device (Raspberry Pi Zero 2W)
2. Launch CarConnect app
3. Navigate to "Wireless" tab
4. Verify the bridge appears in the device list
5. Tap to initiate BLE pairing

#### Test 3.2: Wi-Fi Direct Connection
1. Complete Test 3.1
2. Verify Wi-Fi Direct connection is established
3. Check IP assignment (phone should get 192.168.49.x)
4. Verify log shows `WIFI_CONNECTED`

#### Test 3.3: Auto-Reconnect
1. Complete Tests 3.1 and 3.2
2. Turn off Wi-Fi on the phone and turn it back on
3. Verify the bridge automatically reconnects
4. Check log shows `CONNECTION_LOST` → `CONNECTION_ESTABLISHED`

### Phase 4: Projection Test

1. After USB or wireless connection is established
2. Verify the car-friendly UI renders on the phone screen
3. Check large buttons are visible and tappable
4. Verify dark mode is active
5. Verify minimal animations

### Phase 5: Production Integration Test

1. Complete all above tests
2. Test USB ↔ wireless auto-switching:
   - Start with USB connection
   - Unplug USB
   - Verify app automatically switches to wireless (if bridge is present)
3. Test safe disconnect:
   - Stop the app
   - Verify USB connection is closed cleanly
   - Verify no leaked resources

## Expected Results

| Phase | Feature | Expected Result |
|-------|---------|----------------|
| Phase 2 | USB detection | ✅ Phone detects RAV4 USB connection |
| Phase 2 | Device identification | ✅ VID/PID logged |
| Phase 2 | Basic communication | ✅ Channel opens and closes cleanly |
| Phase 2 | Logging | ✅ All states logged to file |
| Phase 3 | BLE discovery | ⚠️ Experimental — requires bridge |
| Phase 3 | Wi-Fi Direct | ⚠️ Experimental — requires bridge |
| Phase 3 | Auto-reconnect | ⚠️ Experimental — requires bridge |
| Phase 4 | Car UI | ✅ Phone-side UI ready |
| Phase 4 | Projection | ⚠️ Depends on native Android Auto |
| Phase 5 | Auto-switching | ⚠️ Experimental — requires bridge |

## Safety Verification Checklist

Before using in a vehicle:
- [ ] App does NOT modify vehicle safety systems
- [ ] App does NOT send commands to steering, braking, or airbags
- [ ] App does NOT bypass cryptographic authentication
- [ ] App does NOT circumvent security mechanisms
- [ ] App focuses only on infotainment/projection functionality
- [ ] All USB communication is logged for audit

## Troubleshooting

| Symptom | Possible Cause | Solution |
|---------|---------------|----------|
| "USB: Disconnected" after plugging in | Cable is charge-only | Use a data cable |
| No USB permission dialog | App not in foreground | Open app before plugging in |
| Log file empty | Storage permission denied | Check app permissions |
| Bridge not found (wireless) | Bridge powered off | Power on Raspberry Pi |
| Wi-Fi Direct won't connect | Phone doesn't support Wi-Fi Direct | Use USB connection instead |
