from __future__ import annotations

from typing import Any, Dict, Optional

from backend.app.policies.base import BasePolicy, is_admin, is_authenticated


class PaperPolicy(BasePolicy):
    """论文策略，控制论文的公开操作、提交和内容池访问权限。"""

    resource_name = "paper"

    _PUBLIC_ACTIONS = {
        "list",
        "detail",
        "view",
        "translate",
        "preview",
        "download_session",
        "download",
        "import",
    }

    def allows(
        self,
        user: Optional[Dict[str, Any]],
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """检查用户是否有权执行指定操作：公开操作允许所有人；提交需认证；内容池读取需管理员。"""
        del context

        if action in self._PUBLIC_ACTIONS:
            return self._allow(action, "Public paper action is allowed.")

        if action == "submit":
            if is_authenticated(user):
                return self._allow(action, "Authenticated user may submit papers.")
            return self._deny(action, "Authentication required to submit papers.")

        if action == "content_pool_read":
            if is_admin(user):
                return self._allow(action, "Admin may access content-pool operator views.")
            return self._deny(action, "Admin role required for content-pool operator views.")

        return self._deny(action, "Action not supported by the paper policy.")
