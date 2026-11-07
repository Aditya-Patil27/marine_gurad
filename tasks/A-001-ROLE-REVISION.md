# A-001 revision — keep approval separate from analysis

> Historical role-correction brief; A-001 is complete. See completed/A-001.md and current.md.


Status: COMPLETED after Codex review. OpenCode corrected the three scoped files and its focused role unit test passed. Codex ran the full auth suite against a newly created isolated database migrated to 006: 12 passed, including the corrected negative and dual-role API checks. The temporary database was removed. Existing routes remain unauthenticated until A-002.

The A-001 implementation incorrectly makes `ANALYST` imply `APPROVER` in `apps/api/app/models/user.py`; its tests assert this escalation. The product plan F01 assigns investigation/drafting to Analyst and approval/sending to Approver. Users may hold both explicitly. Correct this before A-001 can be accepted.

Scope: `apps/api/app/models/user.py`, `apps/api/tests/test_auth.py`, and `docs/contracts/AUTH_API.md` only. Preserve all other work. No schema, migration, database, provider or frontend changes. Do not create an administrator. Keep the existing Viewer inheritance for Analyst and Approver, and Administrator implication of every role.

1. Remove `APPROVER` from Analyst's implied roles. Approver must not imply Analyst. Explicitly holding both grants both.
2. Fix meaningful unit and dependency integration assertions: an Analyst-only user gets 403 from `require_approver`; an Approver-only user gets 403 from `require_analyst`; both assigned roles and Administrator each grant the appropriate permissions. Preserve anonymous/Viewer negatives. Add a test for explicit multiple roles if practical without changing the existing schema.
3. Update the role matrix/description in `docs/contracts/AUTH_API.md` to state the separation and hierarchy. Do not claim route-wide security.
4. Run the focused no-database role unit test in the backend container. Integration tests need a migrated disposable `TEST_DATABASE_URL`; if unavailable, report them skipped, never target the running application DB. Return files changed, actual results and remaining blockers. Do not mark A-001 COMPLETED.
