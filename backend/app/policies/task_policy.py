from __future__ import annotations

from typing import Any, Dict, Optional

from backend.app.policies.base import BasePolicy, is_admin, is_authenticated


class TaskPolicy(BasePolicy):
    resource_name = "task"

    def allows(
        self,
        user: Optional[Dict[str, Any]],
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ):
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
        if not owner_id or not user:
            return False
        return str(user.get("id")) == str(owner_id)
