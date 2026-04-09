# Centralized Authorization Implementation Plan

I'm using the writing-plans skill to create the implementation plan.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a centralized `authorize(user, resource, action, context=None)` slice with clear result objects so downstream routes can stop copying ownership/admin checks.

**Architecture:** Run a TDD loop focused on a single test file before implementing the policy registry plus resource-specific policy subclasses that share an `AuthorizationResult` contract.

**Tech Stack:** Python 3.11, pytest, dataclasses, typing, the existing `backend/app` package structure.

---

### Task 1: Create focused authorization tests

**Files:**
- Create: `backend/tests/unit/test_authorization_policies.py`

- [ ] **Step 1: Write the failing tests**

```python
from backend.app.policies import authorize


def _user(roles=None, user_id="user-123"):
    return {"id": user_id, "roles": roles or []}


def test_guest_cannot_access_community_conversations():
    result = authorize(user=None, resource="community_conversation", action="read")
    assert not result.allowed
    assert "guest" in result.reason.lower()


def test_user_can_read_and_delete_task_they_own():
    result = authorize(
        user=_user(),
        resource="task",
        action="view",
        context={"owner_user_id": "user-123"},
    )
    assert result.allowed

    delete_result = authorize(
        user=_user(),
        resource="task",
        action="delete",
        context={"owner_user_id": "user-123"},
    )
    assert not delete_result.allowed
    assert "admin" in delete_result.reason.lower()


def test_settings_require_authenticated_user():
    assert not authorize(user=None, resource="settings", action="read").allowed
    assert authorize(user=_user(), resource="settings", action="read").allowed


def test_admin_cleanup_requires_admin_role():
    non_admin = authorize(user=_user(), resource="admin_cleanup", action="execute")
    assert not non_admin.allowed
    admin = authorize(user=_user(roles=["admin"]), resource="admin_cleanup", action="execute")
    assert admin.allowed


def test_unknown_resource_is_denied_with_reason():
    result = authorize(user=None, resource="unknown", action="foo")
    assert not result.allowed
    assert "unknown resource" in result.reason.lower()
```

- [ ] **Step 2: Run the test suite to see it fail**

```bash
pytest backend/tests/unit/test_authorization_policies.py
```

Expected: `ModuleNotFoundError` / `ImportError` or AttributeError because `backend.app.policies` is not fleshed out yet. The command should exit with status 1.

- [ ] **Step 3: (Optional) Add placeholder imports to keep the test file clean while waiting for implementation**

Add a `# pylint: disable=unused-import` comment if necessary and import the `AuthorizationResult` dataclass paths, keeping the file ready for step 4.

- [ ] **Step 4: Commit the tests**

```bash
git add backend/tests/unit/test_authorization_policies.py
git commit -m "test: add authorization policy coverage"
```

### Task 2: Implement the policy slice

**Files:**
- Create: `backend/app/policies/__init__.py`
- Create: `backend/app/policies/base.py`
- Create: `backend/app/policies/community_agent_policy.py`
- Create: `backend/app/policies/settings_policy.py`
- Create: `backend/app/policies/task_policy.py`
- Create: `backend/app/policies/admin_policy.py`

- [ ] **Step 1: Define the base result and policy contract**

```python
from dataclasses import dataclass
from typing import Any, Optional, Protocol


@dataclass(frozen=True)
class AuthorizationResult:
    allowed: bool
    reason: str
    policy: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None


class BasePolicy(Protocol):
    def allows(self, user: Optional[dict[str, Any]], action: str, context: Optional[dict[str, Any]]) -> AuthorizationResult:
        ...

def is_admin(user: Optional[dict[str, Any]]) -> bool:
    if not user:
        return False
    roles = {str(role).strip().lower() for role in user.get("roles") or []}
    return "admin" in roles

def is_authenticated(user: Optional[dict[str, Any]]) -> bool:
    return bool(user and user.get("id"))
```

- [ ] **Step 2: Implement resource policies**

Add classes that inherit from this contract and return `AuthorizationResult` with resource/action tags and clear deny reasons, e.g. `CommunityAgentPolicy`, `SettingsPolicy`, `TaskPolicy`, `AdminPolicy`. Each one should check `is_authenticated`/`is_admin` and the provided context when needed (`owner_user_id` for tasks).

- [ ] **Step 3: Implement `authorize` entrypoint**

```python
POLICY_REGISTRY = {
    "community_conversation": CommunityAgentPolicy(),
    "settings": SettingsPolicy(),
    "task": TaskPolicy(),
    "admin_cleanup": AdminPolicy(),
}


def authorize(user, resource, action, context=None):
    policy = POLICY_REGISTRY.get(resource)
    if not policy:
        return AuthorizationResult(
            allowed=False,
            reason=f"Unknown resource {resource!r}",
            resource=resource,
            action=action,
        )
    return policy.allows(user, action, context or {})
```

- [ ] **Step 4: Run the tests and expect them to pass**

```bash
pytest backend/tests/unit/test_authorization_policies.py
```

Expected: The new test file should pass (exit code 0) once the policies return the described result objects.

- [ ] **Step 5: Commit the implementation**

```bash
git add backend/app/policies backend/tests/unit/test_authorization_policies.py
git commit -m "feat: add centralized authorization policies"
```
