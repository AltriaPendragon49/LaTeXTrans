from __future__ import annotations

from typing import Any, Dict, Optional

from backend.app.policies.base import BasePolicy, is_admin, is_authenticated


class CommunityAgentPolicy(BasePolicy):
    resource_name = "community_conversation"

    def __init__(self, *, resource_name: str = "community_conversation") -> None:
        self.resource_name = resource_name

    def allows(
        self,
        user: Optional[Dict[str, Any]],
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        ctx = context or {}
        owner_user_id = str(ctx.get("owner_user_id") or "").strip() or None

        if not is_authenticated(user):
            return self._deny(action, "Guest access to community conversations is restricted.")

        if is_admin(user):
            return self._allow(action, "Admin may access all community-agent resources.")

        if owner_user_id:
            if str(user.get("id") or "").strip() == owner_user_id:
                return self._allow(action, "Owners may access their own community-agent resources.")
            return self._deny(action, "Only the resource owner or an admin may access this resource.")

        return self._allow(action, "Authenticated users may access community-agent resources.")
