from __future__ import annotations

from typing import Any

from .family_profiles import family_profiles


ROLE_DEFAULTS = {
    "owner": {"*"},
    "admin": {
        "devices.read",
        "devices.write",
        "automation.read",
        "automation.write",
        "reports.read",
        "profiles.read",
        "profiles.write",
    },
    "member": {
        "devices.read",
        "automation.read",
        "reports.read",
    },
    "guest": {
        "devices.read",
    },
}


class PermissionEngine:
    def permissions_for(self, member_id: str) -> set[str]:
        member = family_profiles.get(member_id)
        if member is None:
            raise KeyError(f"Member not found: {member_id}")

        role = str(member.get("role") or "member")
        permissions = set(ROLE_DEFAULTS.get(role, set()))
        permissions.update(str(item) for item in member.get("permissions", []))
        return permissions

    def allowed(self, member_id: str, permission: str) -> bool:
        permissions = self.permissions_for(member_id)
        return "*" in permissions or permission in permissions

    def explain(self, member_id: str, permission: str) -> dict[str, Any]:
        member = family_profiles.get(member_id)
        if member is None:
            raise KeyError(f"Member not found: {member_id}")

        permissions = self.permissions_for(member_id)
        return {
            "member_id": member_id,
            "role": member.get("role"),
            "permission": permission,
            "allowed": "*" in permissions or permission in permissions,
            "effective_permissions": sorted(permissions),
        }


permission_engine = PermissionEngine()
