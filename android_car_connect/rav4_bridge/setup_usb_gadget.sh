#!/bin/bash
#
# USB Gadget Setup Script for NoorBrain CarConnect Bridge
# Raspberry Pi Zero 2W — configures the Pi as a USB gadget
# that emulates an Android phone to the 2019 RAV4 infotainment system.
#
# This script must be run at boot (add to /etc/rc.local or systemd).
#
# Prerequisites:
#   - Raspberry Pi Zero 2W running Raspberry Pi OS Lite (64-bit)
#   - Kernel with CONFIGFS and g_ffs modules enabled
#   - dtoverlay=dwc2 in /boot/config.txt
#
# ⚠️ EXPERIMENTAL — not tested on actual 2019 RAV4 hardware

set -e

echo "Setting up USB gadget mode for NoorBrain CarConnect Bridge..."

# 1. Load required kernel modules
modprobe libcomposite
modprobe g_ffs  # FunctionFS for Android Auto

# 2. Mount configfs
CONFIGFS_DIR="/sys/kernel/config"
if ! mountpoint -q "$CONFIGFS_DIR"; then
    mount -t configfs none "$CONFIGFS_DIR"
fi

# 3. Create USB gadget directory
GADGET_DIR="$CONFIGFS_DIR/usb_gadget/carconnect"
mkdir -p "$GADGET_DIR"
cd "$GADGET_DIR"

# 4. Configure USB vendor/product IDs
# Using Google VID (0x18D9) and a standard Android Auto PID
echo 0x18D9 > idVendor
echo 0x4025 > idProduct
echo 0x0100 > bcdDevice
echo 0x0200 > bcdUSB

# 5. Set device class (vendor-specific for AOA 2.0)
echo 0x00 > bDeviceClass
echo 0x00 > bDeviceSubClass
echo 0x00 > bDeviceProtocol

# 6. Set strings (manufacturer, product, serial)
mkdir -p strings/0x409
echo "NoorBrain" > strings/0x409/manufacturer
echo "CarConnect-Bridge" > strings/0x409/product
echo "CNB000000001" > strings/0x409/serialnumber

# 7. Create configurations
mkdir -p configs/c.1/strings/0x409
echo "RAV4 Bridge Config" > configs/c.1/strings/0x409/configuration
echo 250 > configs/c.1/MaxPower

# 8. Create FunctionFS function for Android Auto
mkdir -p functions/ffs.usb0

# Bind the function to the configuration
ln -sf functions/ffs.usb0 configs/c.1/

# 9. Enable the gadget (bind to UDC)
# Find the UDC name
ls /sys/class/udc > UDC

echo "USB gadget configured as Android phone (VID=0x18D9, PID=0x4025)"

# 10. Mount FunctionFS for user-space access
mkdir -p /dev/ffs.usb0
mount -t functionfs -o uid=0,gid=0 allow_monotonic=1 \
    ffs.usb0 /dev/ffs.usb0 2>/dev/null || \
    echo "Warning: Could not mount FunctionFS (may already be mounted)"

echo "USB gadget setup complete. The Pi will now appear as an Android phone to the RAV4."

# 11. Start the bridge proxy server
echo "Starting bridge proxy server..."
if [ -f /home/pi/NoorBrain/android_car_connect/rav4_bridge/bridge_server.py ]; then
    python3 /home/pi/NoorBrain/android_car_connect/rav4_bridge/bridge_server.py &
fi

echo "Done. Bridge is ready."
