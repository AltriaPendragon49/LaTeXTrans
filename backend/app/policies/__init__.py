from __future__ import annotations

from typing import Any, Dict, Optional

from .admin_policy import AdminPolicy
from .base import AuthorizationResult, BasePolicy
from .community_agent_policy import CommunityAgentPolicy
from .paper_policy import PaperPolicy
from .settings_policy import SettingsPolicy
from .task_policy import TaskPolicy


_POLICY_REGISTRY: dict[str, BasePolicy] = {
    "community_conversation": CommunityAgentPolicy(resource_name="community_conversation"),
    "community_run": CommunityAgentPolicy(resource_name="community_run"),
    "settings": SettingsPolicy(),
    "task": TaskPolicy(),
    "admin_cleanup": AdminPolicy(),
    "paper": PaperPolicy(),
}


def authorize(
    user: Optional[Dict[str, Any]],
    resource: str,
    action: str,
    context: Optional[Dict[str, Any]] = None,
) -> AuthorizationResult:
    policy = _POLICY_REGISTRY.get(resource)
    if policy is None:
        return AuthorizationResult(
            allowed=False,
            reason=f"Unknown resource {resource!r}",
            resource=resource,
            action=action,
        )
    return policy.allows(user, action, context or {})
