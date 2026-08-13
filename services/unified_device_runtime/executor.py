from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class PhysicalDeviceExecutor:

    @staticmethod
    def _protocol(device: dict[str, Any]) -> str:
        return str(
            device.get("protocol")
            or device.get("transport")
            or "logical"
        ).strip().lower()

    def execute(
        self,
        device: dict[str, Any],
        state: str,
    ) -> dict[str, Any]:

        state = str(state).strip().lower()

        if state not in {"on", "off"}:
            raise ValueError("State must be on or off.")

        protocol = self._protocol(device)

        if protocol in {"logical", "virtual", "local", ""}:
            return {
                "status": "logical_only",
                "executed": False,
                "protocol": "logical",
                "reason": "No physical transport configured.",
            }

        if protocol == "mqtt":
            return self._mqtt(device, state)

        if protocol in {"http", "https", "esp32"}:
            return self._http(device, state)

        return {
            "status": "unsupported",
            "executed": False,
            "protocol": protocol,
            "reason": f"Unsupported protocol: {protocol}",
        }

    def _mqtt(
        self,
        device: dict[str, Any],
        state: str,
    ) -> dict[str, Any]:

        from services.automation.mqtt_service import mqtt_service

        metadata = dict(device.get("metadata") or {})

        topic = str(
            device.get("command_topic")
            or metadata.get("command_topic")
            or ""
        ).strip()

        if not topic:
            return {
                "status": "configuration_required",
                "executed": False,
                "protocol": "mqtt",
                "reason": "MQTT command_topic is missing.",
            }

        payload_map = (
            device.get("payloads")
            or metadata.get("payloads")
            or {}
        )

        payload = payload_map.get(state, state)

        if not mqtt_service.status().get("started"):
            mqtt_service.start()

        result = mqtt_service.publish(
            topic,
            payload,
            qos=int(
                device.get("qos")
                or metadata.get("qos")
                or 0
            ),
            retain=bool(
                device.get("retain")
                or metadata.get("retain")
                or False
            ),
        )

        published = bool(result.get("published"))

        return {
            "status": "ok" if published else result.get("status", "error"),
            "executed": published,
            "protocol": "mqtt",
            "topic": topic,
            "result": result,
        }

    def _http(
        self,
        device: dict[str, Any],
        state: str,
    ) -> dict[str, Any]:

        metadata = dict(device.get("metadata") or {})

        base_url = str(
            device.get("base_url")
            or device.get("url")
            or metadata.get("base_url")
            or metadata.get("url")
            or ""
        ).strip().rstrip("/")

        endpoints = (
            device.get("endpoints")
            or metadata.get("endpoints")
            or {}
        )

        endpoint = str(
            endpoints.get(state)
            or metadata.get(f"{state}_endpoint")
            or device.get(f"{state}_endpoint")
            or ""
        ).strip()

        if not base_url:
            ip_address = str(
                device.get("ip_address")
                or metadata.get("ip_address")
                or ""
            ).strip()

            if ip_address:
                base_url = f"http://{ip_address}"

        if not base_url:
            return {
                "status": "configuration_required",
                "executed": False,
                "protocol": "http",
                "reason": "HTTP base_url/ip_address is missing.",
            }

        if not endpoint:
            endpoint = f"/{state}"

        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            url = endpoint
        else:
            url = base_url + "/" + endpoint.lstrip("/")

        method = str(
            device.get("method")
            or metadata.get("method")
            or "POST"
        ).upper()

        headers = {
            "Accept": "application/json",
        }

        token = str(
            device.get("token")
            or metadata.get("token")
            or ""
        ).strip()

        if token:
            headers["Authorization"] = f"Bearer {token}"

        body = None

        if method in {"POST", "PUT", "PATCH"}:
            headers["Content-Type"] = "application/json"

            body = json.dumps({
                "state": state,
                "device_id": device.get("id"),
            }).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=4,
            ) as response:
                response.read()

                return {
                    "status": "ok",
                    "executed": True,
                    "protocol": "http",
                    "url": url,
                    "http_status": response.status,
                }

        except urllib.error.HTTPError as exc:
            return {
                "status": "error",
                "executed": False,
                "protocol": "http",
                "url": url,
                "reason": f"HTTP {exc.code}",
            }

        except Exception as exc:
            return {
                "status": "error",
                "executed": False,
                "protocol": "http",
                "url": url,
                "reason": f"{type(exc).__name__}: {exc}",
            }


physical_device_executor = PhysicalDeviceExecutor()
