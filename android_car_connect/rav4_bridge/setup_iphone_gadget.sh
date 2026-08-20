#!/bin/bash
#
# NoorBrain CarConnect Bridge — USB Gadget Setup for iPhone Emulation
# Raspberry Pi Zero 2W configuration
#
# Configures the Pi as a USB gadget that appears as an iPhone to the
# 2019 Toyota RAV4's USB port, enabling CarPlay.
#
# Since your car supports CarPlay but NOT Android Auto, the bridge
# presents itself as an iPhone to the car's head unit.

set -e

echo "=== NoorBrain CarConnect Bridge Setup (iPhone Emulation) ==="

# Step 1: Enable USB gadget mode in config.txt
echo ""
echo "[1/5] Configuring /boot/config.txt..."
if ! grep -q "dtoverlay=dwc2" /boot/config.txt; then
    echo "dtoverlay=dwc2" >> /boot/config.txt
fi
if ! grep -q "otg_mode=1" /boot/config.txt; then
    echo "otg_mode=1" >> /boot/config.txt
fi

# Step 2: Configure USB gadget with Apple/iPhone identifiers
echo ""
echo "[2/5] Configuring USB gadget (iPhone emulation)..."

# Mount configfs
CONFIGFS_DIR="/sys/kernel/config"
if ! mountpoint -q "$CONFIGFS_DIR"; then
    mount -t configfs none "$CONFIGFS_DIR"
fi

# Create gadget directory
GADGET=$CONFIGFS_DIR/usb_gadget/carplay
mkdir -p $GADGET
cd $GADGET

# Apple Inc. Vendor ID
echo 0x05AC > idVendor
# iPhone Product ID (CarPlay compatible)
echo 0x12A8 > idProduct
echo 0x0111 > bcdDevice
echo 0x0200 > bcdUSB

# Device class settings for iPhone/CarPlay
echo 0xEF > bDeviceClass
echo 0x02 > bDeviceSubClass
echo 0x01 > bDeviceProtocol

# Strings (appear as Apple/iPhone to the car)
mkdir -p strings/0x409
echo "Apple Inc." > strings/0x409/manufacturer
echo "CarPlay Bridge" > strings/0x409/product
echo "CNB000000001" > strings/0x409/serialnumber

# Create configuration
mkdir -p configs/c.1/strings/0x409
echo "Config 1: CarPlay Bridge" > configs/c.1/strings/0x409/configuration
echo 250 > configs/c.1/MaxPower

# FunctionFS for iPhone/CarPlay protocol
mkdir -p functions/ffs.iphone

# Bind to configuration
ln -sf functions/ffs.iphone configs/c.1/

# Bind to UDC (USB Device Controller)
echo "Binding to UDC..."
ls /sys/class/udc > UDC

echo "USB gadget configured as iPhone (VID=0x05AC, PID=0x12A8)"

# Step 3: Mount FunctionFS for user-space access
echo ""
echo "[3/5] Mounting FunctionFS..."
mkdir -p /dev/ffs.iphone
mount -t functionfs iphone /dev/ffs.iphone 2>/dev/null || {
    echo "Warning: Could not mount FunctionFS — may already be mounted"
}

# Step 4: Install Python dependencies
echo ""
echo "[4/5] Installing Python dependencies..."
pip3 install pyserial

# Step 5: Create systemd service for the bridge
echo ""
echo "[5/5] Creating bridge service..."

sudo tee /etc/systemd/system/carconnect-carplay-bridge.service > /dev/null << 'EOF'
[Unit]
Description=NoorBrain CarConnect Bridge Server (CarPlay Edition)
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/pi/NoorBrain/android_car_connect/rav4_bridge/carplay_bridge.py --listen-port 5353 --usb-device /dev/ffs.iphone
Restart=always
RestartSec=5
User=pi

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable carconnect-carplay-bridge.service

echo ""
echo "=== Setup Complete ==="
echo "The Pi Zero W will now appear as an iPhone to the car."
echo ""
echo "Next steps:"
echo "1. Connect Pi to car's USB-A port (with OTG adapter)"
echo "2. Connect phone to Pi's WiFi (SSID: CarConnect-Bridge)"
echo "3. Start the bridge: sudo systemctl start carconnect-carplay-bridge"
echo "4. Open NoorBrain CarConnect app on your phone"
echo "5. Enable CarPlay mode in the app"
echo ""
echo "IMPORTANT: Use a powered USB hub if the car's USB doesn't provide enough power."
