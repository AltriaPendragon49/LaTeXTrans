from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional


@dataclass(frozen=True)
class AuthorizationResult:
    allowed: bool
    reason: str
    policy: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None


class BasePolicy(ABC):
    resource_name: str

    @abstractmethod
    def allows(
        self,
        user: Optional[Dict[str, Any]],
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AuthorizationResult:
        ...

    def _build(self, allowed: bool, action: str, reason: str) -> AuthorizationResult:
        return AuthorizationResult(
            allowed=allowed,
            reason=reason,
            policy=self.__class__.__name__,
            resource=self.resource_name,
            action=action,
        )

    def _allow(self, action: str, reason: str = "Allowed") -> AuthorizationResult:
        return self._build(True, action, reason)

    def _deny(self, action: str, reason: str = "Denied") -> AuthorizationResult:
        return self._build(False, action, reason)


def _normalize_roles(user: Optional[Dict[str, Any]]) -> Iterable[str]:
    if not user:
        return ()
    roles = user.get("roles", ())
    if isinstance(roles, str):
        roles = [part.strip() for part in roles.split(",") if part.strip()]
    return {str(role).strip().lower() for role in roles}


def is_admin(user: Optional[dict[str, Any]]) -> bool:
    return "admin" in _normalize_roles(user)


def is_authenticated(user: Optional[Dict[str, Any]]) -> bool:
    return bool(user and user.get("id"))
