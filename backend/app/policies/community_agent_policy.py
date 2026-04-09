from __future__ import annotations

from typing import Any, Dict, Optional

from backend.app.policies.base import BasePolicy, is_authenticated


class CommunityAgentPolicy(BasePolicy):
    resource_name = "community_conversation"

    def allows(
        self,
        user: Optional[Dict[str, Any]],
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        if not is_authenticated(user):
            return self._deny(action, "Guest access to community conversations is restricted.")
        return self._allow(action, "Authenticated users control community conversations.")
