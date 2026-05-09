## 1. Specification
- [x] 1.1 Update the retained community-agent accessibility requirement to allow admin-only product access while keeping public entry points hidden
- [x] 1.2 Add web UI requirements for the admin-only sidebar entry, admin route guard, and refined conversation workspace presentation

## 2. Frontend implementation
- [x] 2.1 Add an admin-only `Paper Copilot` sidebar navigation item beneath `Paper Tool`
- [x] 2.2 Gate `/agent` routes so guests go to `/login` and authenticated non-admin users are redirected to `/tools`
- [x] 2.3 Apply a moderate visual refresh to the conversation rail, header, message area, and composer without changing the existing workspace structure

## 3. Verification
- [x] 3.1 Add or update tests for sidebar visibility, protected route behavior, and conversation page rendering
- [x] 3.2 Run targeted frontend tests for the touched areas
