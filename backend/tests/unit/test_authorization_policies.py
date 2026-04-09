from __future__ import annotations

from typing import Any, Dict, Optional

from backend.app.policies import authorize


def _user(roles: Optional[list[str]] = None, user_id: str = "user-123") -> Dict[str, Any]:
    return {"id": user_id, "roles": roles or []}


def test_guest_cannot_access_community_conversation():
    result = authorize(user=None, resource="community_conversation", action="read")
    assert not result.allowed
    assert "guest" in result.reason.lower()


def test_authenticated_user_can_view_and_delete_their_own_task():
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
    assert delete_attempt.allowed


def test_non_owner_cannot_delete_task():
    delete_attempt = authorize(
        user=_user(),
        resource="task",
        action="delete",
        context={"owner_user_id": "other-user"},
    )
    assert not delete_attempt.allowed
    assert "owner" in delete_attempt.reason.lower()


def test_community_run_policy_requires_owner_or_admin():
    guest = authorize(user=None, resource="community_run", action="read", context={"owner_user_id": "user-123"})
    assert not guest.allowed
    assert "authentication" in guest.reason.lower() or "guest" in guest.reason.lower()

    owner = authorize(
        user=_user(user_id="user-123"),
        resource="community_run",
        action="read",
        context={"owner_user_id": "user-123"},
    )
    assert owner.allowed

    outsider = authorize(
        user=_user(user_id="user-999"),
        resource="community_run",
        action="read",
        context={"owner_user_id": "user-123"},
    )
    assert not outsider.allowed
    assert "owner" in outsider.reason.lower()

    admin = authorize(
        user=_user(roles=["admin"], user_id="admin-1"),
        resource="community_run",
        action="read",
        context={"owner_user_id": "user-123"},
    )
    assert admin.allowed


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


def test_paper_policy_allows_public_read_paths():
    for action in (
        "list",
        "detail",
        "view",
        "translate",
        "preview",
        "download_session",
        "download",
        "import",
    ):
        decision = authorize(user=None, resource="paper", action=action)
        assert decision.allowed


def test_paper_policy_requires_authenticated_user_for_submit():
    guest = authorize(user=None, resource="paper", action="submit")
    assert not guest.allowed
    assert "authentication" in guest.reason.lower()

    member = authorize(user=_user(), resource="paper", action="submit")
    assert member.allowed


def test_paper_policy_restricts_content_pool_to_admin():
    member = authorize(user=_user(), resource="paper", action="content_pool_read")
    assert not member.allowed
    assert "admin" in member.reason.lower()

    admin = authorize(user=_user(roles=["admin"]), resource="paper", action="content_pool_read")
    assert admin.allowed
