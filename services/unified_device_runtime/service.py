from __future__ import annotations

from typing import Any


class UnifiedDeviceRuntime:
    """
    NoorBrain V10.1 unified device control layer.

    Primary registry:
        smart_home_runtime

    Legacy fallback:
        automation device_manager
    """

    def list_devices(self) -> list[dict[str, Any]]:
        from services.smart_home_runtime.store import smart_home_store

        data = smart_home_store.read()

        return [
            {
                **dict(device),
                "runtime": "smart_home_runtime",
            }
            for device in data.get("devices", [])
        ]

    def find_device(
        self,
        query: str,
    ) -> dict[str, Any] | None:

        normalized = query.strip().casefold()

        if not normalized:
            return None

        devices = self.list_devices()

        exact = next(
            (
                device
                for device in devices
                if str(device.get("name", "")).casefold()
                == normalized
            ),
            None,
        )

        if exact:
            return exact

        matches = [
            device
            for device in devices
            if normalized
            in str(device.get("name", "")).casefold()
            or str(device.get("name", "")).casefold()
            in normalized
        ]

        if len(matches) == 1:
            return matches[0]

        return None

    def status(
        self,
        name: str,
    ) -> dict[str, Any]:

        device = self.find_device(name)

        if device is None:
            return {
                "status": "not_found",
                "query": name,
            }

        return {
            "status": "ok",
            "device": device,
        }

    def set_state(
        self,
        name: str,
        state: str,
    ) -> dict[str, Any]:

        requested = state.strip().lower()

        if requested not in {"on", "off"}:
            raise ValueError(
                "State must be on or off."
            )

        device = self.find_device(name)

        if device is None:
            return {
                "status": "not_found",
                "query": name,
            }

        from services.unified_device_runtime.executor import (
            physical_device_executor,
        )

        execution = physical_device_executor.execute(
            device,
            requested,
        )

        # A configured physical transport must succeed
        # before NoorBrain claims the state changed.
        if execution.get("protocol") != "logical":
            if not execution.get("executed"):
                return {
                    "status": "execution_failed",
                    "device": device,
                    "requested_state": requested,
                    "execution": execution,
                }

        device_id = str(device["id"])

        from services.smart_home_runtime.store import (
            smart_home_store,
        )

        data = smart_home_store.read()

        updated = None

        for item in data.get("devices", []):
            if str(item.get("id")) == device_id:
                item["state"] = requested
                updated = dict(item)
                break

        if updated is None:
            return {
                "status": "not_found",
                "query": name,
            }

        smart_home_store.write(data)

        updated["runtime"] = (
            "smart_home_runtime"
        )

        return {
            "status": "ok",
            "device": updated,
            "execution": execution,
        }


unified_device_runtime = UnifiedDeviceRuntime()
