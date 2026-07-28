from __future__ import annotations

import importlib.util
import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger("NoorBrain.MQTT")


@dataclass
class MQTTConfig:
    host: str = "127.0.0.1"
    port: int = 1883
    keepalive: int = 60
    client_id: str = "noorbrain"
    username: str | None = None
    password: str | None = None
    base_topic: str = "noorbrain"


class MQTTService:
    def __init__(self, config: MQTTConfig | None = None) -> None:
        self.config = config or MQTTConfig()
        self._client = None
        self._connected = False
        self._started = False
        self._lock = threading.RLock()
        self._subscriptions: dict[str, list[Callable[[str, Any], None]]] = {}
        self._last_error: str | None = None
        self._last_message_at: float | None = None
        self._published = 0
        self._received = 0

    @property
    def available(self) -> bool:
        try:
            return importlib.util.find_spec("paho.mqtt.client") is not None
        except ModuleNotFoundError:
            return False

    @property
    def connected(self) -> bool:
        return self._connected

    def start(self) -> dict[str, Any]:
        with self._lock:
            if self._started:
                return self.status()

            self._started = True

            if not self.available:
                self._last_error = "paho-mqtt is not installed"
                return self.status()

            try:
                import paho.mqtt.client as mqtt

                client = mqtt.Client(
                    mqtt.CallbackAPIVersion.VERSION2,
                    client_id=self.config.client_id,
                )

                if self.config.username:
                    client.username_pw_set(
                        self.config.username,
                        self.config.password,
                    )

                client.on_connect = self._on_connect
                client.on_disconnect = self._on_disconnect
                client.on_message = self._on_message
                client.connect_async(
                    self.config.host,
                    self.config.port,
                    self.config.keepalive,
                )
                client.loop_start()
                self._client = client
                self._last_error = None

            except Exception as exc:
                self._last_error = str(exc)
                logger.exception("MQTT start failed")

            return self.status()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            client = self._client
            self._client = None
            self._connected = False
            self._started = False

            if client is not None:
                try:
                    client.loop_stop()
                    client.disconnect()
                except Exception:
                    logger.exception("MQTT stop failed")

            return self.status()

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        self._connected = int(reason_code) == 0
        if not self._connected:
            self._last_error = f"MQTT connect failed: {reason_code}"
            return

        self._last_error = None

        for topic in self._subscriptions:
            client.subscribe(topic)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        self._connected = False
        if int(reason_code) != 0:
            self._last_error = f"MQTT disconnected: {reason_code}"

    def _on_message(self, client, userdata, message):
        self._received += 1
        self._last_message_at = time.time()

        try:
            raw = message.payload.decode("utf-8")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = raw

            for pattern, callbacks in list(self._subscriptions.items()):
                if pattern == message.topic or pattern.endswith("/#") and message.topic.startswith(pattern[:-1]):
                    for callback in callbacks:
                        try:
                            callback(message.topic, payload)
                        except Exception:
                            logger.exception("MQTT callback failed")
        except Exception as exc:
            self._last_error = str(exc)
            logger.exception("MQTT message handling failed")

    def subscribe(self, topic: str, callback: Callable[[str, Any], None]) -> None:
        with self._lock:
            self._subscriptions.setdefault(topic, []).append(callback)
            if self._client is not None and self._connected:
                self._client.subscribe(topic)

    def publish(
        self,
        topic: str,
        payload: Any,
        *,
        retain: bool = False,
        qos: int = 0,
    ) -> dict[str, Any]:
        if not isinstance(payload, str):
            payload = json.dumps(payload, ensure_ascii=False)

        if self._client is None or not self._connected:
            return {
                "status": "queued",
                "published": False,
                "reason": self._last_error or "MQTT is not connected",
                "topic": topic,
                "payload": payload,
            }

        info = self._client.publish(
            topic,
            payload,
            qos=qos,
            retain=retain,
        )
        self._published += 1

        return {
            "status": "ok",
            "published": True,
            "topic": topic,
            "mid": getattr(info, "mid", None),
        }

    def status(self) -> dict[str, Any]:
        return {
            "status": "connected" if self._connected else "disconnected",
            "available": self.available,
            "started": self._started,
            "connected": self._connected,
            "host": self.config.host,
            "port": self.config.port,
            "base_topic": self.config.base_topic,
            "subscriptions": sorted(self._subscriptions),
            "published": self._published,
            "received": self._received,
            "last_message_at": self._last_message_at,
            "last_error": self._last_error,
        }


mqtt_service = MQTTService()
