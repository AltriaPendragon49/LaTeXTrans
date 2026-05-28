from __future__ import annotations

from typing import Any, Dict, Optional

from backend.app.policies.base import BasePolicy, is_admin


class AdminPolicy(BasePolicy):
    """管理员策略，仅允许管理员执行管理相关的清理操作。"""

    resource_name = "admin_cleanup"

    def allows(
        self,
        user: Optional[Dict[str, Any]],
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """检查用户是否为管理员，是则允许，否则拒绝。"""
        if is_admin(user):
            return self._allow(action, "Admin role confirmed for administrative actions.")
        return self._deny(action, "Admin role required to perform administrative cleanup.")
