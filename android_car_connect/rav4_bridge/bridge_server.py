#!/usr/bin/env python3
"""
NoorBrain CarConnect — Bridge Device Proxy Server

This is the bridge software that runs on a Raspberry Pi Zero 2W (or similar).
It acts as a USB gadget to the car's USB port and as a Wi-Fi Direct client
to the phone.

The bridge's job:
  1. Accept a wireless (Wi-Fi Direct) connection from the Android phone
  2. Present itself to the car's USB port as an Android phone (AOA 2.0)
  3. Proxy the Android Auto protocol stream between phone and car

This is EXPERIMENTAL and has NOT been tested on actual 2019 RAV4 hardware.

Usage:
  python3 bridge_server.py --listen-port 5353 --usb-device /dev/ffs.aa

Phase 3 — Wireless prototype
"""

import argparse
import logging
import socket
import struct
import sys
import threading
import time
from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Logging setup (matches the Android app's log format)
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/var/log/carconnect_bridge.log"),
    ],
)

logger = logging.getLogger("CarConnectBridge")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Android Auto protocol uses port 5353 for wireless connections
DEFAULT_LISTEN_PORT = 5353

# USB FunctionFS for Android Auto (set up via configfs on Raspberry Pi)
DEFAULT_USB_DEVICE = "/dev/ffs.aa"

# Maximum packet size for USB bulk transfers
USB_PACKET_SIZE = 512

# Timeout for USB reads (milliseconds)
USB_READ_TIMEOUT_MS = 100


@dataclass
class ConnectionStats:
    """Tracks connection statistics for monitoring."""
    bytes_rx: int = 0
    bytes_tx: int = 0
    packets_rx: int = 0
    packets_tx: int = 0
    start_time: float = 0.0
    last_activity: float = 0.0


class UsbChannel:
    """
    Represents the USB communication channel to the car.
    Uses Linux FunctionFS to communicate with the car's USB host.
    """

    def __init__(self, device_path: str = DEFAULT_USB_DEVICE):
        self.device_path = device_path
        self.fd: Optional[int] = None
        self.stats = ConnectionStats()
        self._running = False

    def open(self) -> bool:
        """Open the USB FunctionFS device."""
        try:
            import os
            self.fd = os.open(self.device_path, os.O_RDWR)
            self._running = True
            logger.info(f"USB channel opened: {self.device_path} (fd={self.fd})")
            return True
        except Exception as e:
            logger.error(f"Failed to open USB device {self.device_path}: {e}")
            return False

    def close(self):
        """Close the USB channel."""
        if self.fd is not None:
            try:
                import os
                os.close(self.fd)
                logger.info(f"USB channel closed: {self.device_path}")
            except Exception as e:
                logger.error(f"Error closing USB device: {e}")
            finally:
                self.fd = None
                self._running = False

    def read_packet(self) -> Optional[bytes]:
        """Read a packet from the car (USB bulk OUT endpoint)."""
        if self.fd is None:
            return None
        try:
            import os
            data = os.read(self.fd, USB_PACKET_SIZE)
            if data:
                self.stats.bytes_rx += len(data)
                self.stats.packets_rx += 1
                self.stats.last_activity = time.time()
                return data
        except BlockingIOError:
            return None
        except Exception as e:
            logger.error(f"USB read error: {e}")
        return None

    def write_packet(self, data: bytes) -> bool:
        """Write a packet to the car (USB bulk IN endpoint)."""
        if self.fd is None:
            return False
        try:
            import os
            written = os.write(self.fd, data)
            self.stats.bytes_tx += written
            self.stats.packets_tx += 1
            self.stats.last_activity = time.time()
            return written == len(data)
        except Exception as e:
            logger.error(f"USB write error: {e}")
            return False

    def is_running(self) -> bool:
        return self._running


class WifiDirectChannel:
    """
    Represents the Wi-Fi Direct connection from the phone.
    The bridge acts as the group owner (access point) in Wi-Fi Direct.
    """

    def __init__(self, listen_port: int = DEFAULT_LISTEN_PORT):
        self.listen_port = listen_port
        self.sock: Optional[socket.socket] = None
        self.client_sock: Optional[socket.socket] = None
        self.stats = ConnectionStats()
        self._running = False

    def start_server(self) -> bool:
        """Start listening for phone connections."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("0.0.0.0", self.listen_port))
            self.sock.listen(1)
            self.sock.settimeout(1.0)
            self._running = True
            logger.info(f"Wi-Fi Direct server listening on port {self.listen_port}")
            return True
        except Exception as e:
            logger.error(f"Failed to start Wi-Fi server: {e}")
            return False

    def accept_connection(self) -> bool:
        """Wait for and accept a phone connection."""
        if self.sock is None:
            return False
        try:
            self.client_sock, addr = self.sock.accept()
            logger.info(f"Phone connected from: {addr[0]}:{addr[1]}")
            self.stats.start_time = time.time()
            return True
        except socket.timeout:
            return False
        except Exception as e:
            logger.error(f"Accept failed: {e}")
            return False

    def read_packet(self) -> Optional[bytes]:
        """Read data from the phone."""
        if self.client_sock is None:
            return None
        try:
            # First 4 bytes = packet length (big-endian uint32)
            length_bytes = self.client_sock.recv(4)
            if len(length_bytes) < 4:
                return None
            length = struct.unpack("!I", length_bytes)[0]
            # Then the payload
            data = b""
            while len(data) < length:
                chunk = self.client_sock.recv(length - len(data))
                if not chunk:
                    break
                data += chunk
            if len(data) == length:
                self.stats.bytes_rx += length + 4
                self.stats.packets_rx += 1
                self.stats.last_activity = time.time()
                return data
        except Exception as e:
            logger.error(f"Wi-Fi read error: {e}")
        return None

    def write_packet(self, data: bytes) -> bool:
        """Write data to the phone."""
        if self.client_sock is None:
            return False
        try:
            # Send 4-byte length prefix + payload
            packet = struct.pack("!I", len(data)) + data
            self.client_sock.sendall(packet)
            self.stats.bytes_tx += len(packet)
            self.stats.packets_tx += 1
            self.stats.last_activity = time.time()
            return True
        except Exception as e:
            logger.error(f"Wi-Fi write error: {e}")
            return False

    def close(self):
        """Close the Wi-Fi Direct channel."""
        self._running = False
        for sock in [self.client_sock, self.sock]:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
        logger.info("Wi-Fi Direct channel closed")


class BridgeServer:
    """
    Main bridge server that proxies data between the phone (Wi-Fi Direct)
    and the car (USB gadget).

    Data flow:
      Phone → Wi-Fi Direct → BridgeServer → USB FunctionFS → Car
      Car → USB FunctionFS → BridgeServer → Wi-Fi Direct → Phone
    """

    def __init__(self, listen_port: int, usb_device: str):
        self.usb = UsbChannel(usb_device)
        self.wifi = WifiDirectChannel(listen_port)
        self._running = False
        self._forward_thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        """Start the bridge server."""
        logger.info("Starting NoorBrain CarConnect Bridge Server...")
        logger.info("Phase 3: Wireless prototype (experimental)")

        # Start USB channel
        if not self.usb.open():
            logger.error("Cannot start bridge without USB channel")
            return False

        # Start Wi-Fi Direct server
        if not self.wifi.start_server():
            logger.error("Cannot start bridge without Wi-Fi server")
            self.usb.close()
            return False

        self._running = True

        # Wait for phone connection
        logger.info("Waiting for phone to connect via Wi-Fi Direct...")
        while self._running:
            if self.wifi.accept_connection():
                break
            time.sleep(0.5)

        if not self._running:
            return False

        # Start bidirectional forwarding
        self._forward_thread = threading.Thread(
            target=self._forward_loop, daemon=True
        )
        self._forward_thread.start()

        logger.info("Bridge connection established! Proxying traffic...")
        return True

    def _forward_loop(self):
        """
        Bidirectional forwarding loop.
        Uses threads to read from both channels simultaneously.
        """
        def forward(src_name: str, src_read, dst_write, dst_name: str):
            while self._running:
                try:
                    data = src_read()
                    if data and len(data) > 0:
                        logger.debug(
                            f"Forwarding {len(data)} bytes: {src_name} → {dst_name}"
                        )
                        dst_write(data)
                except Exception as e:
                    logger.error(f"Forward error ({src_name} → {dst_name}): {e}")
                    break
                time.sleep(0.001)  # Small delay to prevent CPU spin

        # Forward phone → car (Wi-Fi → USB)
        phone_to_car = threading.Thread(
            target=forward,
            args=("phone", self.wifi.read_packet, self.usb.write_packet, "car"),
            daemon=True,
        )
        phone_to_car.start()

        # Forward car → phone (USB → Wi-Fi)
        car_to_phone = threading.Thread(
            target=forward,
            args=("car", self.usb.read_packet, self.wifi.write_packet, "phone"),
            daemon=True,
        )
        car_to_phone.start()

        phone_to_car.join()
        car_to_phone.join()

    def stop(self):
        """Stop the bridge server."""
        logger.info("Stopping bridge server...")
        self._running = False
        self.usb.close()
        self.wifi.close()
        logger.info("Bridge server stopped.")

    def get_stats(self) -> dict:
        """Return current connection statistics."""
        return {
            "usb": {
                "bytes_rx": self.usb.stats.bytes_rx,
                "bytes_tx": self.usb.stats.bytes_tx,
                "packets_rx": self.usb.stats.packets_rx,
                "packets_tx": self.usb.stats.packets_tx,
            },
            "wifi": {
                "bytes_rx": self.wifi.stats.bytes_rx,
                "bytes_tx": self.wifi.stats.bytes_tx,
                "packets_rx": self.wifi.stats.packets_rx,
                "packets_tx": self.wifi.stats.packets_tx,
            },
            "running": self._running,
        }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="NoorBrain CarConnect Bridge Server (Phase 3)"
    )
    parser.add_argument(
        "--listen-port",
        type=int,
        default=DEFAULT_LISTEN_PORT,
        help=f"Port to listen for Wi-Fi Direct connections (default: {DEFAULT_LISTEN_PORT})",
    )
    parser.add_argument(
        "--usb-device",
        type=str,
        default=DEFAULT_USB_DEVICE,
        help=f"USB FunctionFS device path (default: {DEFAULT_USB_DEVICE})",
    )
    args = parser.parse_args()

    server = BridgeServer(
        listen_port=args.listen_port,
        usb_device=args.usb_device,
    )

    try:
        if server.start():
            # Print stats every 5 seconds
            while server._running:
                time.sleep(5)
                stats = server.get_stats()
                logger.info(f"Stats: USB RX={stats['usb']['bytes_rx']}B TX={stats['usb']['bytes_tx']}B | "
                           f"WiFi RX={stats['wifi']['bytes_rx']}B TX={stats['wifi']['bytes_tx']}B")
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
