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
        from services.automation.manager import device_manager

        data = smart_home_store.read()
        devices = [
            {
                **dict(device),
                "runtime": "smart_home_runtime",
            }
            for device in data.get("devices", [])
        ]

        known_ids = {str(device.get("id")) for device in devices}
        known_names = {
            str(device.get("name") or "").casefold()
            for device in devices
        }

        for registered in device_manager.list_devices():
            item = registered.model_dump(mode="json")

            if (
                str(item.get("id")) in known_ids
                or str(item.get("name") or "").casefold() in known_names
            ):
                continue

            item["type"] = item.get("device_type", "other")
            item["runtime"] = "automation_devices"
            devices.append(item)

        return devices

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

    def find_device_by_id(
        self,
        device_id: str,
    ) -> dict[str, Any] | None:
        normalized = str(device_id).strip()
        return next(
            (
                device
                for device in self.list_devices()
                if str(device.get("id")) == normalized
            ),
            None,
        )

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

        return self._set_device_state(
            device,
            requested,
        )

    def set_state_by_id(
        self,
        device_id: str,
        state: str,
    ) -> dict[str, Any]:
        requested = state.strip().lower()

        if requested not in {"on", "off"}:
            raise ValueError("State must be on or off.")

        device = self.find_device_by_id(device_id)

        if device is None:
            return {
                "status": "not_found",
                "query": device_id,
            }

        return self._set_device_state(device, requested)

    @staticmethod
    def _set_device_state(
        device: dict[str, Any],
        requested: str,
    ) -> dict[str, Any]:
        if device.get("online") is not True:
            return {
                "status": "execution_failed",
                "device": device,
                "requested_state": requested,
                "execution": {
                    "status": "offline",
                    "executed": False,
                    "reason": "Device is offline.",
                },
            }

        from services.unified_device_runtime.executor import (
            physical_device_executor,
        )

        execution = physical_device_executor.execute(
            device,
            requested,
        )

        if not execution.get("executed"):
            return {
                "status": "execution_failed",
                "device": device,
                "requested_state": requested,
                "execution": execution,
            }

        device_id = str(device["id"])

        if device.get("runtime") == "automation_devices":
            from services.automation.manager import device_manager

            updated_device = device_manager.update_device(
                device_id,
                {"state": requested},
            )
            updated = updated_device.model_dump(mode="json")
            updated["type"] = updated.get("device_type", "other")
            updated["runtime"] = "automation_devices"

            return {
                "status": "ok",
                "device": updated,
                "execution": execution,
            }

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
                "query": device_id,
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
