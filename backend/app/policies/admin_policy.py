from __future__ import annotations

from typing import Any, Dict, Optional

from backend.app.policies.base import BasePolicy, is_admin


class AdminPolicy(BasePolicy):
    resource_name = "admin_cleanup"

    def allows(
        self,
        user: Optional[Dict[str, Any]],
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        if is_admin(user):
            return self._allow(action, "Admin role confirmed for administrative actions.")
        return self._deny(action, "Admin role required to perform administrative cleanup.")
