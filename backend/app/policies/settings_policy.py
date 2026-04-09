from __future__ import annotations

from typing import Any, Dict, Optional

from backend.app.policies.base import BasePolicy, is_authenticated


class SettingsPolicy(BasePolicy):
    resource_name = "settings"

    def allows(
        self,
        user: Optional[Dict[str, Any]],
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        if not is_authenticated(user):
            return self._deny(action, "Authentication is required to access settings.")
        return self._allow(action, "Authenticated users may manage settings.")
