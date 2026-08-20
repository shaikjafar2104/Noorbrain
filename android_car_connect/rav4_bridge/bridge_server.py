#!/usr/bin/env python3
"""
NoorBrain CarConnect Bridge Server

Runs on Raspberry Pi Zero 2W in USB gadget mode.
Acts as a proxy between the Android phone (wireless) and the RAV4
(wired USB), enabling wireless Android Auto on cars that only support
wired (like the 2019 RAV4).

Architecture:
  Phone (Wi-Fi Direct) ←→ Bridge (Pi Zero 2W) ←→ Car (USB gadget)

The bridge:
  1. Presents itself as an Android phone to the car via USB FunctionFS
  2. Accepts a Wi-Fi Direct connection from the phone
  3. Proxies the Android Auto protocol between both sides

Usage:
  python3 bridge_server.py --listen-port 5353 --usb-device /dev/ffs.android
"""

import argparse
import asyncio
import logging
import os
import socket
import ssl
import struct
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Logging — matches Android app format for consistency
# --------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/var/log/carconnect_bridge.log"),
    ],
)
log = logging.getLogger("CarConnectBridge")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_LISTEN_PORT = 5353
DEFAULT_USB_DEVICE = "/dev/ffs.android"
USB_PACKET_SIZE = 512
USB_READ_TIMEOUT_MS = 100
WIFI_READ_TIMEOUT_S = 5.0
MAX_PACKET_SIZE = 65536

# Android Auto protocol constants
AOA_PROTOCOL_VERSION = 1
AOA_FEATURE_0 = 0  # Default feature set

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


class USBChannel:
    """
    USB communication channel using Linux FunctionFS.
    Communicates with the car's USB host via bulk endpoints.
    """

    def __init__(self, device_path: str = DEFAULT_USB_DEVICE):
        self.device_path = device_path
        self.fd: Optional[int] = None
        self.ep_in: Optional[int] = None  # Phone → Car (IN to car)
        self.ep_out: Optional[int] = None  # Car → Phone (OUT from car)
        self._running = False
        self.stats = ConnectionStats()

    def open(self) -> bool:
        """Open the FunctionFS device."""
        try:
            self.fd = os.open(self.device_path, os.O_RDWR)
            self._running = True
            log.info(f"USB channel opened: {self.device_path} (fd={self.fd})")
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
                log.info("USB channel closed")

    def read(self) -> Optional[bytes]:
        """
        Read data from the car (bulk OUT endpoint).
        Returns bytes received from the car, or None on timeout/error.
        """
        if self.fd is None:
            return None
        try:
            data = os.read(self.fd, USB_PACKET_SIZE)
            if data:
                self.stats.bytes_rx += len(data)
                self.stats.packets_rx += 1
                self.stats.last_activity = time.time()
                log.debug(f"USB RX: {len(data)} bytes")
                return data
        except (BlockingIOError, OSError):
            return None
        except Exception as e:
            log.error(f"USB read error: {e}")
        return None

    def write(self, data: bytes) -> bool:
        """
        Write data to the car (bulk IN endpoint).
        """
        if self.fd is None:
            return False
        try:
            written = os.write(self.fd, data)
            self.stats.bytes_tx += written
            self.stats.packets_tx += 1
            self.stats.last_activity = time.time()
            log.debug(f"USB TX: {written} bytes")
            return written == len(data)
        except OSError as e:
            log.error(f"USB write error: {e}")
            return False
        except Exception as e:
            log.error(f"USB write error: {e}")
            return False

    def is_open(self) -> bool:
        return self.fd is not None and self._running


class WifiChannel:
    """
    Wi-Fi Direct communication channel between the bridge and the phone.
    The bridge acts as the Wi-Fi Direct group owner (access point).
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
            self.client_sock.settimeout(WIFI_READ_TIMEOUT_S)
            addr = self.client_addr
            if addr is not None:
                log.info(f"Phone connected from: {addr[0]}:{addr[1]}")
            return True
        except socket.timeout:
            return False
        except OSError as e:
            log.error(f"Accept failed: {e}")
            return False

    def read(self) -> Optional[bytes]:
        """
        Read a packet from the phone.
        Uses length-prefixed framing (4-byte big-endian length + payload).
        """
        if self.client_sock is None:
            return None
        try:
            # Read 4-byte length prefix
            length_bytes = self._recv_exact(4)
            if length_bytes is None or len(length_bytes) < 4:
                return None

            length = struct.unpack("!I", length_bytes)[0]
            if length == 0 or length > MAX_PACKET_SIZE:
                log.warning(f"Invalid packet length: {length}")
                return None

            # Read payload
            data = self._recv_exact(length)
            if data is None or len(data) < length:
                return None

            self.stats.bytes_rx += length + 4
            self.stats.packets_rx += 1
            self.stats.last_activity = time.time()
            log.debug(f"WiFi RX: {length} bytes")
            return data

        except socket.timeout:
            return None
        except OSError as e:
            log.error(f"Wi-Fi read error: {e}")
            return None
        except Exception as e:
            log.error(f"Wi-Fi read error: {e}")
            return None

    def _recv_exact(self, n: int) -> Optional[bytes]:
        """Receive exactly n bytes, or None on connection close/error."""
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
            except socket.timeout:
                return None
            except OSError:
                return None
        return data

    def write(self, data: bytes) -> bool:
        """
        Write a packet to the phone.
        Uses length-prefixed framing.
        """
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
            log.debug(f"WiFi TX: {len(data)} bytes")
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


class BridgeServer:
    """
    Main bridge server that proxies data between the phone (Wi-Fi)
    and the car (USB).

    The bridge presents itself as an Android phone to the car (via USB gadget
    mode with FunctionFS) while accepting a wireless connection from the phone.
    """

    def __init__(self, listen_port: int, usb_device: str):
        self.usb = USBChannel(usb_device)
        self.wifi = WifiChannel(listen_port)
        self.state = BridgeState()
        self.state.start_time = time.time()
        self._running = False
        self._lock = threading.Lock()

    def start(self) -> bool:
        """Start the bridge server."""
        log.info("=== NoorBrain CarConnect Bridge Server ===")
        log.info("Phase 3: Wireless prototype (experimental)")
        log.info(f"USB device: {self.usb.device_path}")
        log.info(f"Wi-Fi port: {self.wifi.listen_port}")

        # Start USB channel
        if not self.usb.open():
            log.error("Cannot start bridge without USB channel")
            self.state.last_error = "USB channel failed to open"
            return False

        self.state.usb_connected = True

        # Start Wi-Fi Direct server
        if not self.wifi.start_server():
            log.error("Cannot start bridge without Wi-Fi server")
            self.usb.close()
            self.state.last_error = "Wi-Fi server failed to start"
            return False

        self._running = True

        # Wait for phone connection
        log.info("Waiting for phone connection via Wi-Fi Direct (port %d)..." % self.wifi.listen_port)

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

        log.info("=== Bridge connection established! Proxying traffic... ===")
        log.info("Phone ←→ Wi-Fi Direct ←→ Bridge ←→ USB gadget ←→ Car")

        return True

    def _forward_phone_to_car(self):
        """Forward data from phone (Wi-Fi) to car (USB)."""
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
        """Forward data from car (USB) to phone (Wi-Fi)."""
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
        description="NoorBrain CarConnect Bridge Server"
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
        help=f"USB FunctionFS device path (default: {DEFAULT_USB_DEVICE})",
    )
    args = parser.parse_args()

    server = BridgeServer(
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
