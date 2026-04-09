from __future__ import annotations

from typing import Any, Dict, Optional

from backend.app.policies import authorize


def _user(roles: Optional[list[str]] = None, user_id: str = "user-123") -> Dict[str, Any]:
    return {"id": user_id, "roles": roles or []}


def test_guest_cannot_access_community_conversation():
    result = authorize(user=None, resource="community_conversation", action="read")
    assert not result.allowed
    assert "guest" in result.reason.lower()


def test_authenticated_user_can_view_their_task_but_not_delete():
    user = _user()
    view = authorize(
        user=user,
        resource="task",
        action="view",
        context={"owner_user_id": "user-123"},
    )
    assert view.allowed
    assert view.resource == "task"

    delete_attempt = authorize(
        user=user,
        resource="task",
        action="delete",
        context={"owner_user_id": "user-123"},
    )
    assert not delete_attempt.allowed
    assert "admin" in delete_attempt.reason.lower()


def test_settings_endpoint_requires_authenticated_user():
    guest = authorize(user=None, resource="settings", action="read")
    assert not guest.allowed
    assert "authentication" in guest.reason.lower()

    user = authorize(user=_user(), resource="settings", action="read")
    assert user.allowed
    assert user.action == "read"


def test_admin_cleanup_requires_admin_role():
    non_admin = authorize(user=_user(), resource="admin_cleanup", action="execute")
    assert not non_admin.allowed
    assert "admin" in non_admin.reason.lower()

    admin = authorize(user=_user(roles=["admin"]), resource="admin_cleanup", action="execute")
    assert admin.allowed


def test_unknown_resource_is_denied():
    result = authorize(user=None, resource="missing", action="noop")
    assert not result.allowed
    assert "unknown resource" in result.reason.lower()
