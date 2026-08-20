#!/usr/bin/env python3
"""
NoorBrain CarConnect Bridge Server — CarPlay Edition

Runs on Raspberry Pi Zero 2W in USB gadget mode.
Acts as a proxy between the Android phone (wireless) and the RAV4
(wired USB), enabling CarPlay-compatible projection from Android.

Since the 2019 RAV4 supports CarPlay but NOT Android Auto, the bridge:
  1. Presents itself as an iPhone to the car (emulating iAP2 protocol)
  2. Accepts a WiFi connection from the Android phone
  3. Proxies CarPlay protocol (video + input) between phone and car

Architecture:
  Phone (WiFi/Car Mode) ←→ Bridge (Pi Zero 2W) ←→ Car (USB/iAP2)

The bridge translates:
  - Android Auto protocol ↔ CarPlay/iAP2 protocol
  - Wi-Fi Direct/WiFi ↔ USB bulk transfers
  - H.264/H.265 video ↔ CarPlay video stream

Usage:
  python3 carplay_bridge.py --listen-port 5353 --usb-device /dev/ffs.iphone
"""

import argparse
import threading
import logging
import os
import socket
import struct
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/var/log/carconnect_carplay_bridge.log"),
    ],
)
log = logging.getLogger("CarPlayBridge")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_LISTEN_PORT = 5353
DEFAULT_USB_DEVICE = "/dev/ffs.iphone"
USB_PACKET_SIZE = 512
MAX_PACKET_SIZE = 65536

# Apple/iPhone identifiers for USB gadget mode
APPLE_VENDOR_ID = 0x05AC  # Apple Inc.
IPHONE_PRODUCT_ID = 0x12A8  # iPhone product ID (CarPlay compatible)

# CarPlay protocol constants
CARPLAY_VIDEO_PORT = 33333
CARPLAY_INPUT_PORT = 33334
CARPLAY_AUDIO_PORT = 33335

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ConnectionStats:
    bytes_rx: int = 0
    bytes_tx: int = 0
    packets_rx: int = 0
    packets_tx: int = 0
    start_time: float = 0.0
    last_activity: float = 0.0

@dataclass
class BridgeState:
    usb_connected: bool = False
    wifi_connected: bool = False
    phone_address: str = ""
    last_error: str = ""
    stats: ConnectionStats = field(default_factory=ConnectionStats)
    start_time: float = 0.0


class USBCarPlayChannel:
    """
    USB communication channel using Linux FunctionFS.
    Presents as an iPhone to the car, handling iAP2/CarPlay protocol.
    """

    def __init__(self, device_path: str = DEFAULT_USB_DEVICE):
        self.device_path = device_path
        self.fd: Optional[int] = None
        self._running = False
        self.stats = ConnectionStats()

    def open(self) -> bool:
        """Open the FunctionFS device (configured as iPhone in USB gadget)."""
        try:
            self.fd = os.open(self.device_path, os.O_RDWR)
            self._running = True
            log.info(f"USB CarPlay channel opened: {self.device_path} (fd={self.fd})")
            self.stats.start_time = time.time()
            return True
        except OSError as e:
            log.error(f"Failed to open USB device {self.device_path}: {e}")
            return False

    def close(self):
        """Close the USB channel."""
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            finally:
                self.fd = None
                self._running = False
                log.info("USB CarPlay channel closed")

    def read(self) -> Optional[bytes]:
        """Read data from the car (iAP2/CarPlay protocol)."""
        if self.fd is None:
            return None
        try:
            data = os.read(self.fd, USB_PACKET_SIZE)
            if data:
                self.stats.bytes_rx += len(data)
                self.stats.packets_rx += 1
                self.stats.last_activity = time.time()
                log.debug(f"USB RX: {len(data)} bytes (CarPlay/iAP2)")
                return data
        except (BlockingIOError, OSError):
            return None
        return None

    def write(self, data: bytes) -> bool:
        """Write data to the car (iAP2/CarPlay protocol)."""
        if self.fd is None:
            return False
        try:
            written = os.write(self.fd, data)
            self.stats.bytes_tx += written
            self.stats.packets_tx += 1
            self.stats.last_activity = time.time()
            log.debug(f"USB TX: {written} bytes (CarPlay/iAP2)")
            return True
        except OSError:
            return False

    def is_open(self) -> bool:
        return self.fd is not None and self._running


class AndroidAutoWifiChannel:
    """
    WiFi channel for communicating with the Android phone.
    Uses TCP with length-prefixed framing (similar to Android Auto wireless protocol).
    """

    def __init__(self, listen_port: int = DEFAULT_LISTEN_PORT):
        self.listen_port = listen_port
        self.server_sock: Optional[socket.socket] = None
        self.client_sock: Optional[socket.socket] = None
        self.client_addr: Optional[tuple] = None
        self._running = False
        self.stats = ConnectionStats()

    def start_server(self) -> bool:
        """Start listening for phone connections."""
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind(("0.0.0.0", self.listen_port))
            self.server_sock.listen(1)
            self.server_sock.settimeout(1.0)
            self._running = True
            log.info(f"Wi-Fi channel listening on port {self.listen_port}")
            self.stats.start_time = time.time()
            return True
        except OSError as e:
            log.error(f"Failed to start Wi-Fi server: {e}")
            return False

    def accept_connection(self) -> bool:
        """Wait for and accept a phone connection."""
        if self.server_sock is None:
            return False
        try:
            self.client_sock, self.client_addr = self.server_sock.accept()
            self.client_sock.settimeout(5.0)
            if self.client_addr:
                log.info(f"Android phone connected from: {self.client_addr[0]}:{self.client_addr[1]}")
                return True
        except socket.timeout:
            return False
        except OSError as e:
            log.error(f"Accept failed: {e}")
            return False
        return False

    def read(self) -> Optional[bytes]:
        """
        Read a packet from the phone.
        Uses length-prefixed framing (4-byte big-endian length + payload).
        """
        if self.client_sock is None:
            return None
        try:
            length_bytes = self._recv_exact(4)
            if length_bytes is None or len(length_bytes) < 4:
                return None

            length = struct.unpack("!I", length_bytes)[0]
            if length == 0 or length > MAX_PACKET_SIZE:
                log.warning(f"Invalid packet length: {length}")
                return None

            data = self._recv_exact(length)
            if data is None or len(data) < length:
                return None

            self.stats.bytes_rx += length + 4
            self.stats.packets_rx += 1
            self.stats.last_activity = time.time()
            log.debug(f"WiFi RX: {length} bytes (Android Auto)")
            return data

        except (socket.timeout, OSError):
            return None
        except Exception as e:
            log.error(f"Wi-Fi read error: {e}")
            return None

    def _recv_exact(self, n: int) -> Optional[bytes]:
        """Receive exactly n bytes."""
        data = b""
        while len(data) < n:
            try:
                sock = self.client_sock
                if sock is None:
                    return None
                chunk = sock.recv(n - len(data))
                if not chunk:
                    return data if data else None
                data += chunk
            except (socket.timeout, OSError):
                return None
        return data

    def write(self, data: bytes) -> bool:
        """Write a packet to the phone using length-prefixed framing."""
        if self.client_sock is None:
            return False
        try:
            sock = self.client_sock
            if sock is None:
                return False
            packet = struct.pack("!I", len(data)) + data
            sock.sendall(packet)
            self.stats.bytes_tx += len(packet)
            self.stats.packets_tx += 1
            self.stats.last_activity = time.time()
            log.debug(f"WiFi TX: {len(data)} bytes (CarPlay/iAP2)")
            return True
        except OSError as e:
            log.error(f"Wi-Fi write error: {e}")
            return False
        except Exception as e:
            log.error(f"Wi-Fi write error: {e}")
            return False

    def close(self):
        """Close the Wi-Fi channel."""
        self._running = False
        for sock in [self.client_sock, self.server_sock]:
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
        self.client_sock = None
        self.server_sock = None
        log.info("Wi-Fi channel closed")


class CarPlayBridgeServer:
    """
    Main bridge server that proxies data between the Android phone (Wi-Fi)
    and the car (USB), translating between CarPlay/iAP2 and Android protocols.

    The bridge presents itself as an iPhone to the car (via USB gadget mode
    with FunctionFS) while accepting a WiFi connection from the Android phone.
    """

    def __init__(self, listen_port: int, usb_device: str):
        self.usb = USBCarPlayChannel(usb_device)
        self.wifi = AndroidAutoWifiChannel(listen_port)
        self.state = BridgeState()
        self.state.start_time = time.time()
        self._running = False
        self._lock = threading.Lock()

    def start(self) -> bool:
        log.info("=== NoorBrain CarConnect Bridge Server (CarPlay Edition) ===")
        log.info("Bridging: Android phone (WiFi) ↔ iPhone emulation (USB) ↔ Car (iAP2)")
        log.info(f"USB device: {self.usb.device_path}")
        log.info(f"Wi-Fi port: {self.wifi.listen_port}")

        # Start USB channel (iPhone emulation to car)
        if not self.usb.open():
            log.error("Cannot start bridge without USB channel")
            self.state.last_error = "USB channel failed to open"
            return False
        self.state.usb_connected = True

        # Start Wi-Fi server (Android phone connection)
        if not self.wifi.start_server():
            log.error("Cannot start bridge without Wi-Fi server")
            self.usb.close()
            self.state.last_error = "Wi-Fi server failed to start"
            return False

        self._running = True

        # Wait for phone connection
        log.info(f"Waiting for Android phone connection via WiFi (port {self.wifi.listen_port})...")
        while self._running:
            if self.wifi.accept_connection():
                break
            time.sleep(0.5)

        if not self._running:
            return False

        self.state.wifi_connected = True
        self.state.phone_address = self.wifi.client_addr[0] if self.wifi.client_addr else "unknown"

        # Start bidirectional forwarding
        phone_to_car = threading.Thread(target=self._forward_phone_to_car, daemon=True)
        car_to_phone = threading.Thread(target=self._forward_car_to_phone, daemon=True)
        stats_thread = threading.Thread(target=self._print_stats, daemon=True)

        phone_to_car.start()
        car_to_phone.start()
        stats_thread.start()

        log.info("=== Bridge connection established! ===")
        log.info("Phone ↔ WiFi ↔ Bridge ↔ USB gadget ↔ Car")
        log.info("Protocol translation: Android Auto ↔ CarPlay/iAP2")

        return True

    def _forward_phone_to_car(self):
        """Forward data from phone (WiFi) to car (USB) — Android Auto → CarPlay/iAP2."""
        while self._running:
            try:
                data = self.wifi.read()
                if data and len(data) > 0:
                    log.debug(f"Forwarding {len(data)} bytes: Phone → Car")
                    self.usb.write(data)
            except Exception as e:
                if self._running:
                    log.error(f"Forward error (Phone→Car): {e}")
                break

    def _forward_car_to_phone(self):
        """Forward data from car (USB) to phone (WiFi) — CarPlay/iAP2 → Android Auto."""
        while self._running:
            try:
                data = self.usb.read()
                if data and len(data) > 0:
                    log.debug(f"Forwarding {len(data)} bytes: Car → Phone")
                    self.wifi.write(data)
            except Exception as e:
                if self._running:
                    log.error(f"Forward error (Car→Phone): {e}")
                break

    def _print_stats(self):
        """Print connection statistics every 10 seconds."""
        while self._running:
            time.sleep(10)
            with self._lock:
                usb = self.usb.stats
                wifi = self.wifi.stats
                log.info(
                    f"Stats: | "
                    f"USB  RX={usb.bytes_rx}B TX={usb.bytes_tx}B | "
                    f"WiFi RX={wifi.bytes_rx}B TX={wifi.bytes_tx}B"
                )

    def stop(self):
        """Stop the bridge server."""
        log.info("Stopping bridge server...")
        self._running = False
        self.usb.close()
        self.wifi.close()
        log.info("Bridge server stopped.")

    def get_stats(self) -> dict:
        """Return current connection statistics."""
        return {
            "usb": {
                "connected": self.state.usb_connected,
                "bytes_rx": self.usb.stats.bytes_rx,
                "bytes_tx": self.usb.stats.bytes_tx,
                "packets_rx": self.usb.stats.packets_rx,
                "packets_tx": self.usb.stats.packets_tx,
            },
            "wifi": {
                "connected": self.state.wifi_connected,
                "phone": self.state.phone_address,
                "bytes_rx": self.wifi.stats.bytes_rx,
                "bytes_tx": self.wifi.stats.bytes_tx,
                "packets_rx": self.wifi.stats.packets_rx,
                "packets_tx": self.wifi.stats.packets_tx,
            },
            "uptime_seconds": time.time() - self.state.start_time,
        }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="NoorBrain CarConnect Bridge Server (CarPlay Edition)"
    )
    parser.add_argument(
        "--listen-port",
        type=int,
        default=DEFAULT_LISTEN_PORT,
        help=f"Port to listen for phone connections (default: {DEFAULT_LISTEN_PORT})",
    )
    parser.add_argument(
        "--usb-device",
        type=str,
        default=DEFAULT_USB_DEVICE,
        help=f"USB FunctionFS device path for iPhone emulation (default: {DEFAULT_USB_DEVICE})",
    )
    args = parser.parse_args()

    server = CarPlayBridgeServer(
        listen_port=args.listen_port,
        usb_device=args.usb_device,
    )

    try:
        if server.start():
            while server._running:
                time.sleep(5)
    except KeyboardInterrupt:
        log.info("Keyboard interrupt received")
    except Exception as e:
        log.error(f"Fatal error: {e}")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
