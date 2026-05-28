from __future__ import annotations

from typing import Any, Dict, Optional

from backend.app.policies.base import BasePolicy, is_authenticated


class SettingsPolicy(BasePolicy):
    """设置策略，仅允许已认证用户管理个人设置。"""

    resource_name = "settings"

    def allows(
        self,
        user: Optional[Dict[str, Any]],
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """检查用户是否已认证，认证通过则允许管理设置，否则拒绝。"""
        if not is_authenticated(user):
            return self._deny(action, "Authentication is required to access settings.")
        return self._allow(action, "Authenticated users may manage settings.")
