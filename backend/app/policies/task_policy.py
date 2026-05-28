from __future__ import annotations

from typing import Any, Dict, Optional

from backend.app.policies.base import BasePolicy, is_admin, is_authenticated


class TaskPolicy(BasePolicy):
    """任务策略，控制翻译任务的查看、列表和删除权限。"""

    resource_name = "task"

    def allows(
        self,
        user: Optional[Dict[str, Any]],
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """检查用户是否有权执行指定操作：查看/列表支持所有者和管理员；删除支持所有者和管理员。"""
        ctx = context or {}
        owner_id = ctx.get("owner_user_id")

        if action in {"view", "list"}:
            if self._is_owner(user, owner_id):
                return self._allow(action, "Task owner may access their own tasks.")
            if is_admin(user):
                return self._allow(action, "Admin may access all tasks.")
            if not is_authenticated(user):
                return self._deny(action, "Authentication is required to access tasks.")
            return self._deny(action, "Only the task owner or an admin may access this task.")

        if action == "delete":
            if self._is_owner(user, owner_id):
                return self._allow(action, "Task owner may delete their own task.")
            if is_admin(user):
                return self._allow(action, "Admin may delete tasks.")
            if not is_authenticated(user):
                return self._deny(action, "Authentication is required to delete tasks.")
            return self._deny(action, "Only the task owner or an admin may delete this task.")

        return self._deny(action, "Action not supported by the task policy.")

    def _is_owner(self, user: Optional[Dict[str, Any]], owner_id: Optional[Any]) -> bool:
        """检查用户是否为指定任务的拥有者。"""
        if not owner_id or not user:
            return False
        return str(user.get("id")) == str(owner_id)
