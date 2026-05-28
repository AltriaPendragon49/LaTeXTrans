from __future__ import annotations

from typing import Any, Dict, Optional

from backend.app.policies.base import BasePolicy, is_admin, is_authenticated


class CommunityAgentPolicy(BasePolicy):
    """社区Agent策略，控制社区对话资源的访问权限。"""

    resource_name = "community_conversation"

    def __init__(self, *, resource_name: str = "community_conversation") -> None:
        """初始化策略，可自定义资源名称。"""
        self.resource_name = resource_name

    def allows(
        self,
        user: Optional[Dict[str, Any]],
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """检查用户权限：管理员可访问所有资源；所有者可访问自己的资源；已认证用户可访问社区资源；访客禁止。"""
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
