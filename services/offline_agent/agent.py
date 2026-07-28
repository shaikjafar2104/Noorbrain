from __future__ import annotations

from typing import Any

from .dialogue import local_dialogue
from .intent_router import intent_router
from .models import AgentResponse, ToolCall
from .tool_registry import tool_registry

from . import tools as _tools  # noqa: F401


class OfflineAgent:
    def process(
        self,
        text: str,
        *,
        session_id: str = "default",
        confirm: bool = False,
    ) -> AgentResponse:
        intent = intent_router.route(text)

        if intent.name == "conversation":
            try:
                return AgentResponse(status="ok", reply=local_dialogue.chat(text))
            except Exception as exc:
                return AgentResponse(
                    status="error",
                    reply=f"HALO local AI is unavailable: {exc}",
                )

        tool_call = ToolCall(name=intent.name, arguments=intent.arguments)

        if tool_registry.requires_confirmation(intent.name) and not confirm:
            return AgentResponse(
                status="needs_confirmation",
                reply=self._confirmation_text(intent.name, intent.arguments),
                tool=tool_call,
            )

        try:
            result = tool_registry.execute(intent.name, intent.arguments)
            return AgentResponse(
                status="ok",
                reply=self._format_result(intent.name, result),
                tool=tool_call,
                result=result,
            )
        except Exception as exc:
            return AgentResponse(
                status="error",
                reply=f"I could not complete that request: {exc}",
                tool=tool_call,
            )

    @staticmethod
    def _confirmation_text(name: str, arguments: dict[str, Any]) -> str:
        if name == "set_device_state":
            return f"Please confirm: turn {arguments.get('name')} {arguments.get('state')}?"
        if name == "run_scene":
            return f"Please confirm: run the {arguments.get('name')} scene?"
        return "Please confirm this action."

    @staticmethod
    def _format_result(name: str, result: dict[str, Any]) -> str:
        status = result.get("status")

        if name == "list_devices":
            devices = result.get("devices", [])
            return (
                "No smart-home devices are registered."
                if not devices
                else "Registered devices: "
                + ", ".join(str(item.get("name")) for item in devices)
                + "."
            )

        if name == "get_device_status":
            if status == "not_found":
                return f"I could not find a registered device named {result.get('query')}."
            device = result["device"]
            online = "online" if device.get("online") else "offline"
            return f"{device.get('name')} is {str(device.get('state')).upper()} and {online}."

        if name == "set_device_state":
            if status == "not_found":
                return f"I could not find a registered device named {result.get('query')}."
            device = result["device"]
            return f"{device.get('name')} is now {str(device.get('state')).upper()}."

        if name == "list_scenes":
            scenes = result.get("scenes", [])
            return (
                "No scenes are configured."
                if not scenes
                else "Configured scenes: "
                + ", ".join(str(item.get("name")) for item in scenes)
                + "."
            )

        if name == "run_scene":
            if status == "not_found":
                return f"I could not find the {result.get('query')} scene."
            return f"Scene completed with {result.get('success_count', 0)} successful actions."

        if name == "list_routines":
            routines = result.get("routines", [])
            return (
                "No routines are configured."
                if not routines
                else "Configured routines: "
                + ", ".join(str(item.get("name")) for item in routines)
                + "."
            )

        if name == "automation_summary":
            counts = result.get("counts", {})
            return (
                f"Automation summary: {counts.get('devices', 0)} devices, "
                f"{counts.get('rules', 0)} rules, "
                f"{counts.get('scenes', 0)} scenes, and "
                f"{counts.get('routines', 0)} routines."
            )

        if name == "camera_status":
            connected = bool(result.get("connected"))
            fps = result.get("fps", 0)
            age = result.get("last_frame")
            if not connected:
                return "The camera is offline."
            detail = f"Camera is online at {fps} FPS"
            if age is not None:
                detail += f", with the last frame {age} seconds ago"
            return detail + "."

        if name == "vision_status":
            running = bool(result.get("running"))
            persons = result.get("persons", 0)
            fps = result.get("fps", 0)
            state = "running" if running else "stopped"
            return f"Vision is {state} at {fps} FPS and currently sees {persons} person(s)."

        if name == "activity_summary":
            active = result.get("active_count", 0)
            events = result.get("event_count", 0)
            if active:
                return f"Activity is running. {active} person(s) are active, with {events} recorded events."
            return f"Activity is running. No one is currently active, with {events} recorded events."

        if name == "reports_summary":
            if status == "unavailable":
                return "Reports are currently unavailable."
            return (
                f"Reports are healthy with {result.get('learning_events', 0)} "
                "learning events available for insights."
            )

        if name == "system_health":
            unavailable = result.get("unavailable", [])
            if not unavailable:
                return "NoorBrain system health is good. Camera, vision, activity, automation, and reports are available."
            return "NoorBrain is running, but these components need attention: " + ", ".join(unavailable) + "."

        if name == "skills_status":
            skills = result.get("skills", [])
            available = [item["name"] for item in skills if item.get("available")]
            return "HALO skills ready: " + ", ".join(available) + "."

        if name == "home_status":
            if status == "unavailable":
                return "I could not read the home status right now."

            camera = result.get("camera", {})
            vision = result.get("vision", {})
            activity = result.get("activity", {})
            devices = result.get("devices", {})
            automation = result.get("automation", {})
            alerts = result.get("alerts", [])

            camera_text = "camera online" if camera.get("connected") else "camera offline"
            vision_text = "vision running" if vision.get("running") else "vision stopped"
            active = activity.get("active_count", 0)
            device_count = devices.get("count", 0)
            counts = automation.get("counts", {})

            reply = (
                f"Home status: {camera_text}, {vision_text}, "
                f"{active} active person(s), {device_count} registered device(s), "
                f"{counts.get('rules', 0)} automation rule(s), and "
                f"{counts.get('routines', 0)} routine(s)."
            )
            if alerts:
                reply += " Needs attention: " + ", ".join(alerts) + "."
            else:
                reply += " No critical alerts."
            return reply

        return "The request completed successfully."


offline_agent = OfflineAgent()
