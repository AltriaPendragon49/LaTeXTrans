## Centralized Authorization Design

### Context
- `backend/app/core/auth.py` currently exposes helper dependencies like `require_current_user`, `require_admin_request`, and `optional_current_user`, but individual routes still scatter ownership/admin checks, which makes future switches to a shared policy harder and leaves no single source of truth for allow/deny reasoning.
- The new `authorization` slice has to provide one entry point (`authorize(user, resource, action, context=None)`) plus clear results so callers, tests, and future engineering can understand why something failed.

### Goals
1. Keep the API surface framework-agnostic (plain Python call that can be imported into FastAPI dependencies or services).
2. Offer an `AuthorizationResult` container with at least `allowed: bool` plus a reason/description of the rule that fired.
3. Support the existing set of chance-of-change resources: `community_conversation`, `settings`, `task`, and `admin_cleanup`, covering guest/user/admin role permutations.
4. Drive the behavior from tests (TDD).

### Architecture
1. Introduce a `BasePolicy` protocol/abstract class that accepts a user dict (or `None` for guests), the action name, and a context dict and returns an `AuthorizationResult`.
2. Each resource gets a thin subclass:
   * `CommunityAgentPolicy`: guests are denied for every action, authenticated users are allowed for common actions (`list`, `create`, `get`, `update`, `delete`), admins reuse the user path.
   * `SettingsPolicy`: only authenticated users or admins may `read` or `write`; we treat admin as having the same privileges as a regular user.
   * `TaskPolicy`: `view` is allowed for the record owner (stringified `user["id"]`), `delete` is reserved for admins, and other actions default to deny so we can add future cases without forgetting.
   * `AdminPolicy`: only admin users are allowed to run `execute` (e.g., `admin_cleanup`).
3. The shared `authorize` function looks at a registry mapping resource names to policies, falls back to a deny result when the resource is unknown, and surfaces the explanation from the policy.
4. Add helper functions for checking if a user is authenticated (`is_user`) and if they carry the admin role (checking `roles` values case-insensitively).

### Testing Approach
- Create `backend/tests/unit/test_authorization_policies.py` that drives TDD:
  * Fail first by invoking `authorize` for guest/user/admin combinations on each resource/action and asserting the expected allow/deny plus risk reason text.
  * Cover `task:view` vs `task:delete` to ensure owner vs admin difference is codified.
  * Include a negative test for an unknown resource to prove defaults work.

### Next Steps
1. Write the tests (this will fail initially).
2. Implement the policy classes and entrypoint as described.
3. Run the focused test file to confirm the behavior.
4. Later iterations will plug this entrypoint into real routes/services once the policy slice is mature.

### Review
Spec written and ready for your review. Please confirm or suggest adjustments here before I continue with the implementation plan.
