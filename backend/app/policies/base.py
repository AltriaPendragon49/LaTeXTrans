from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional


@dataclass(frozen=True)
class AuthorizationResult:
    """授权结果数据类，包含是否允许、原因、策略名称、资源名称和操作名称。"""
    allowed: bool
    reason: str
    policy: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None


class BasePolicy(ABC):
    """策略基类，定义授权检查的抽象接口和通用方法。"""

    resource_name: str

    @abstractmethod
    def allows(
        self,
        user: Optional[Dict[str, Any]],
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AuthorizationResult:
        """检查用户是否被允许执行指定操作。子类必须实现此方法。"""
        ...

    def _build(self, allowed: bool, action: str, reason: str) -> AuthorizationResult:
        """构建授权结果对象。"""
        return AuthorizationResult(
            allowed=allowed,
            reason=reason,
            policy=self.__class__.__name__,
            resource=self.resource_name,
            action=action,
        )

    def _allow(self, action: str, reason: str = "Allowed") -> AuthorizationResult:
        """构建允许操作的授权结果。"""
        return self._build(True, action, reason)

    def _deny(self, action: str, reason: str = "Denied") -> AuthorizationResult:
        """构建拒绝操作的授权结果。"""
        return self._build(False, action, reason)


def _normalize_roles(user: Optional[Dict[str, Any]]) -> Iterable[str]:
    """标准化用户角色列表，处理字符串、列表等多种格式。"""
    if not user:
        return ()
    roles = user.get("roles", ())
    if isinstance(roles, str):
        roles = [part.strip() for part in roles.split(",") if part.strip()]
    return {str(role).strip().lower() for role in roles}


def is_admin(user: Optional[dict[str, Any]]) -> bool:
    """检查用户是否拥有管理员角色。"""
    return "admin" in _normalize_roles(user)


def is_authenticated(user: Optional[Dict[str, Any]]) -> bool:
    """检查用户是否已认证（用户对象存在且包含ID）。"""
    return bool(user and user.get("id"))
