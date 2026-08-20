#!/bin/bash
#
# NoorBrain CarConnect Bridge — USB Gadget Setup
# Raspberry Pi Zero 2W configuration
#
# This script configures the Pi as a USB gadget that emulates
# an Android phone to the 2019 Toyota RAV4's USB port.
#
# The bridge accepts a wireless connection from your phone (Wi-Fi Direct)
# and forwards it to the car as if the phone were directly connected via USB.

set -e

echo "=== NoorBrain CarConnect Bridge Setup ==="

# Step 1: Enable USB gadget mode in config.txt
echo ""
echo "[1/5] Configuring /boot/config.txt..."
if ! grep -q "dtoverlay=dwc2" /boot/config.txt; then
    echo "dtoverlay=dwc2" >> /boot/config.txt
fi
# Also increase USB current limit
if ! grep -q "max_usb_current=1" /boot/config.txt; then
    echo "max_usb_current=1" >> /boot/config.txt
fi

# Step 2: Enable SSH and configure networking
echo ""
echo "[2/5] Configuring network..."
# The bridge needs to act as a Wi-Fi Direct group owner
# Install hostapd and dnsmasq for Wi-Fi hotspot fallback
sudo apt-get update -qq
sudo apt-get install -y -qq hostapd dnsmasq dnsmasq-base

# Configure dnsmasq for DHCP (used in fallback AP mode)
sudo tee /etc/dnsmasq.d/carconnect.conf > /dev/null << 'EOF'
interface=wlan0
dhcp-range=192.168.49.100,192.168.49.200,12h
dhcp-option=3,192.168.49.1
dhcp-option=6,8.8.8.8
EOF

# Step 3: Create USB gadget using configfs
echo ""
echo "[3/5] Configuring USB gadget..."

# Mount configfs
sudo mkdir -p /sys/kernel/config
sudo mount -t configfs none /sys/kernel/config 2>/dev/null || true

# Create gadget
GADGET=/sys/kernel/config/usb_gadget/carconnect
sudo mkdir -p $GADGET
cd $GADGET

# Use Google VID (same as Android phones)
echo 0x18D9 | sudo tee idVendor
# Product ID for Android Auto / AOA 2.0
echo 0x4025 | sudo tee idProduct
echo 0x0100 | sudo tee bcdDevice
echo 0x0200 | sudo tee bcdUSB

# Device class (set to 0 for per-interface)
echo 0x00 | sudo tee bDeviceClass
echo 0x00 | sudo tee bDeviceSubClass
echo 0x00 | sudo tee bDeviceProtocol

# Strings
sudo mkdir -p strings/0x409
echo "NoorBrain" | sudo tee strings/0x409/manufacturer
echo "CarConnect-Bridge" | sudo tee strings/0x409/product
echo "CNB000000001" | sudo tee strings/0x409/serialnumber

# Configuration
sudo mkdir -p configs/c.1/strings/0x409
echo "RAV4 Bridge Config" | sudo tee configs/c.1/strings/0x409/configuration
echo 250 | sudo tee configs/c.1/MaxPower

# FunctionFS for Android Auto protocol
sudo mkdir -p functions/ffs.android
sudo ln -sf functions/ffs.android configs/c.1/

# Bind to UDC (USB Device Controller)
echo "Binding to UDC..."
ls /sys/class/udc/ | head -1 | sudo tee UDC

# Step 4: Mount FunctionFS for user-space access
echo ""
echo "[4/5] Mounting FunctionFS..."
sudo mkdir -p /dev/ffs.android
sudo mount -t functionfs android /dev/ffs.android 2>/dev/null || {
    # Try alternate approach
    sudo mount -t functionfs -o uid=0,gid=0 /dev/ffs.android
}

echo "USB gadget configured!"
echo "The Pi will appear as an Android phone to the RAV4."

# Step 5: Create systemd service for the bridge
echo ""
echo "[5/5] Creating bridge service..."
sudo tee /etc/systemd/system/carconnect-bridge.service > /dev/null << 'EOF'
[Unit]
Description=NoorBrain CarConnect Bridge Server
After=multi-user.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/pi/NoorBrain/android_car_connect/rav4_bridge/bridge_server.py --listen-port 5353 --usb-device /dev/ffs.android
Restart=always
RestartSec=5
User=pi

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable carconnect-bridge.service

echo ""
echo "=== Setup Complete ==="
echo "To start the bridge: sudo systemctl start carconnect-bridge"
echo "To check status: sudo systemctl status carconnect-bridge"
echo "To view logs: journalctl -u carconnect-bridge -f"
echo ""
echo "IMPORTANT: Connect the Pi to the RAV4's USB-A port using a USB OTG adapter."
echo "The Pi Zero 2W's micro USB port serves as the device port."
