# External Bridge Device Architecture

## When Is a Bridge Device Required?

| Connection Mode | Native Support on 2019 RAV4 | Bridge Required? |
|-----------------|---------------------------|-----------------|
| USB (Wired) | ✅ Yes — Android Auto native | ❌ No |
| Wireless | ❌ No — wireless AA added in 2020+ | ✅ Yes |

## Bridge Device: Raspberry Pi Zero 2W

The bridge device sits between the Android phone and the RAV4's USB port.
It presents itself as an Android phone to the car, while accepting a wireless
connection from the phone.

### Bridge Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   RASPBERRY PI ZERO 2W                  │
│              (External Bridge Device)                    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Linux (Raspberry Pi OS Lite)                     │   │
│  │                                                  │   │
│  │  ┌────────────┐  ┌───────────────────────────┐  │   │
│  │  │ USB Gadget │  │ Android Auto Proxy        │  │   │
│  │  │ Mode       │  │ (aosp-src / aaw-proxy)    │  │   │
│  │  │            │  │                           │  │   │
│  │  │ - AOA 2.0  │  │ - Accepts Wi-Fi Direct    │  │   │
│  │  │ - Emulates │  │   from phone               │  │   │
│  │  │   Android  │  │ - Proxies USB bulk        │  │   │
│  │  │   phone    │  │   endpoints                │  │   │
│  │  │ - Presents │  │ - Forwards video stream   │  │   │
│  │  │   VID:PID  │  │ - Relays input events    │  │   │
│  │  │   0x18D9:  │  │                           │  │   │
│  │  │   varies   │  │ Bluetooth LE Stack        │  │   │
│  │  └────┬───────┘  │ (bluez + btmon)           │  │   │
│  │       │          └──────────┬────────────────┘  │   │
│  │       │                     │                   │   │
│  │       ▼                     ▼                   │   │
│  │  ┌────────────────────────────────────┐         │   │
│  │  │   USB 3.0 Port (to RAV4)           │         │   │
│  │  │   Micro USB / USB-C OTG            │         │   │
│  │  └────────────────────────────────────┘         │   │
│  │                                                  │   │
│  │  ┌────────────────────────────────────┐         │   │
│  │  │   Wi-Fi Chip (to Phone)            │         │   │
│  │  │   Wi-Fi Direct Group Owner         │         │   │
│  │  └────────────────────────────────────┘         │   │
│  │                                                  │   │
│  │  ┌────────────────────────────────────┐         │   │
│  │  │   Bluetooth LE (Pairing)          │         │   │
│  │  └────────────────────────────────────┘         │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│              ┌───────────────┐   ┌───────────────┐      │
│              │ USB Cable     │   │ Wi-Fi Antenna │      │
│              │ (to RAV4)     │   │ (to Phone)    │      │
│              └──────┬────────┘   └───────┬───────┘      │
└─────────────────────┼─────────────────────┼────────────┘
                      │                     │
                      ▼                     ▲
┌─────────────────────────────────────────────────────────┐
│              2019 Toyota RAV4                           │
│              (USB-A port, Entune 3.0)                   │
└─────────────────────────────────────────────────────────┘
```

## Bridge Software Stack

### Hardware Requirements
| Component | Specification |
|-----------|--------------|
| Board | Raspberry Pi Zero 2W |
| Storage | microSD card (16GB+) |
| USB | Micro USB to USB-A OTG adapter (for connecting to RAV4) |
| Power | USB power supply (2.5A recommended) |

### OS Configuration
```bash
# Base OS: Raspberry Pi OS Lite (64-bit)
# Kernel: 6.x with g_ether and g_ffs modules enabled

# USB Gadget configuration (via configfs):
# 1. Enable USB gadget mode
echo "dtoverlay=dwc2" >> /boot/config.txt

# 2. Configure composite USB gadget
# Creates a multi-function device that appears as an Android phone
# - RNDIS (network) for ADB/debug
# - Mass Storage (optional)
# - FunctionFS for Android Auto protocol
```

### Software Components

1. **Android Auto Proxy** (`aawireless-proxy`)
   - Python/Go service that proxies the AA protocol
   - Accepts TCP connection from phone's Wi-Fi Direct
   - Connects to USB functionFS (/dev/ffs/aa)
   - Bidi-directional stream forwarding

2. **Wi-Fi Direct Manager**
   - Uses `wpa_supplicant` + `hostapd` in P2P mode
   - Phone connects as P2P client, Pi is group owner
   - IP: 192.168.49.1 (Pi), 192.168.49.2 (phone)

3. **BLE Pairing Beacon**
   - Uses `bluez` to advertise a custom service
   - UUID: `0000aade-0000-1000-8000-00805f9b34fb` (AA Wireless UUID)
   - Exchanges pairing token via GATT

4. **USB Gadget Config**
   - Uses Linux `configfs` to create a Composite USB device
   - Vendor ID: `0x18D9` (Google/HTC)
   - Product ID: `0x4025` or similar (must match what car expects)
   - FunctionFS endpoint for AA bulk transfers

## Bridge Setup Steps

### Step 1: Flash Raspberry Pi OS
```bash
# Download Raspberry Pi Imager or use dd
wget https://downloads.raspberrypi.org/raspios_lite_arm64_latest -O raspios.zip
unzip raspios.zip
# Flash to SD card
sudo dd if=raspios.img of=/dev/sdX bs=4M status=progress
```

### Step 2: Initial Configuration
```bash
# Boot Pi, login (default: pi/raspberry), then:
sudo raspi-config
# - Set hostname: rav4-bridge
# - Enable SSH
# - Configure Wi-Fi (for initial setup only)
# - Expand filesystem
```

### Step 3: Install Bridge Software
```bash
# Install dependencies
sudo apt update
sudo apt install -y bluez hostapd dnsmasq python3 python3-pip

# Enable USB gadget mode
echo "dtoverlay=dwc2" | sudo tee -a /boot/config.txt

# Install AA proxy service
git clone https://github.com/niklassenger/aawireless.git
cd aawireless
pip3 install -r requirements.txt
```

### Step 4: USB Gadget Configuration
```bash
#!/bin/bash
# /usr/local/bin/setup-usb-gadget.sh

# Mount configfs
mkdir -p /sys/kernel/config
mount -t configfs none /sys/kernel/config

# Create USB gadget
cd /sys/kernel/config/usb_gadget/
mkdir -p pr_interposer && cd pr_interposer

echo 0x18D9 > idVendor  # Google VID
echo 0x4025 > idProduct # AA PID
echo 0x0100 > bcdDevice
echo 0x0200 > bcdUSB

# Create functionfs function for Android Auto
mkdir -p functions/ff.ffs.0

# Bind to UDC
ls /sys/class/udc > UDC
```

### Step 5: Start Services
```bash
sudo systemctl enable aawireless.service
sudo systemctl enable hostapd.service
sudo systemctl enable dnsmasq.service
```

## Bridge Limitations

1. **Not tested on actual 2019 RAV4** — this is an experimental design
2. **Requires USB gadget mode support** on the Pi
3. **Requires Wi-Fi Direct support** on the phone
4. **AOA 2.0 emulation** is complex and may not be fully compatible
5. **Power consumption** — Pi Zero 2W draws ~500mA from USB

## Alternative: USB-C HAT Approach

Instead of a separate Pi, a USB-C HAT attached to the phone can:
1. Provide USB OTG passthrough to the car
2. Add Wi-Fi/BLE connectivity for wireless AA
3. Act as the bridge entirely on the phone

This avoids the external Pi Zero but requires a compatible USB-C HAT.
