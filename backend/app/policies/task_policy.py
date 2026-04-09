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

        if action == "view":
            if self._is_owner(user, owner_id):
                return self._allow(action, "Task owner may view their own task.")
            if is_admin(user):
                return self._allow(action, "Admin may view all tasks.")
            if not is_authenticated(user):
                return self._deny(action, "Authentication is required to view tasks.")
            return self._deny(action, "Only the task owner or an admin may view this task.")

        if action == "delete":
            if is_admin(user):
                return self._allow(action, "Admin may delete tasks.")
            return self._deny(action, "Admin role required to delete tasks.")

        return self._deny(action, "Action not supported by the task policy.")

    def _is_owner(self, user: Optional[Dict[str, Any]], owner_id: Optional[Any]) -> bool:
        if not owner_id or not user:
            return False
        return str(user.get("id")) == str(owner_id)
