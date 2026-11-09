# A2 — mounted-route authorization and local administration

Status: COMPLETED — 8 November 2026. Owner: A only.

## Bounded objective

Finish the local API access boundary without changing existing data contracts:
explicitly public root/health/docs/login, authenticated Viewer reads, existing
role-separated mutations and identity-before-CSRF. Complete the existing
hidden-password first-run administrator flow with protected local user
management and persistent one-organisation deployment settings. Secrets never
appear in settings responses. No public-Internet security claim.

## Result

- `app/main.py` applies Viewer authentication to every read-only mounted data
  router. Mixed routers retain endpoint-level dependencies so Analyst or
  Approver remains the first mutation-specific authorization check.
- SAR detections, source health and chat health now explicitly require Viewer.
  Logout now resolves a valid session before CSRF.
- New `/api/v1/admin/users` list/create and
  `/api/v1/admin/users/{id}/active` endpoints require Administrator; mutations
  require CSRF. Disabling an account revokes its sessions, and an administrator
  cannot disable their own current account.
- New `/api/v1/admin/settings` GET/PUT persists validated organisation, WGS84
  AOI bounding box, IANA timezone, threshold, recipients and retention. It
  links source health and has no credential fields.
- Migration `015_deployment_settings` creates one constrained singleton row
  with timezone-aware update metadata and actor reference. No shared database
  was migrated.

Public exceptions are `/`, `/health`, `/docs`, `/redoc`, `/openapi.json` and
`POST /api/v1/auth/login`. The first administrator still comes from
`python scripts/create_local_admin.py`, with hidden password input and no
default credential.

## Changed paths

- `apps/api/app/main.py`
- `apps/api/app/api/auth.py`, `admin.py`, `chat.py`, `sar.py`, `sources.py`
- `apps/api/app/services/auth.py` — records the creating administrator on the
  initial role assignment while preserving first-run/default callers.
- `apps/api/alembic/versions/015_deployment_settings.py`
- `apps/api/tests/test_a2_authorization_admin.py`
- `docs/contracts/AUTH_API.md`, `docs/contracts/USER_A_DATA_API.md`
- this record and `tasks/parallel/A-status.md`

## Verification actually run

- Focused non-DB run during implementation: `test_a2_authorization_admin.py`
  plus `test_auth.py` → **6 passed, 8 skipped** before disposable DB setup.
- A uniquely named database `a2_verify_20261108` on isolated
  `samudrasense_postgres_a` migrated empty → `015`.
- Focused authorization/admin suite:
  `test_a2_authorization_admin.py test_auth.py test_mutation_authorization.py test_report_authorization.py`
  → **28 passed**.
- Migration round trip `015 -> 014 -> 015` succeeded and reported `015 (head)`.
- The disposable database was force-dropped after verification. Shared and B
  databases were not reset, seeded or migrated for A2.

The first disposable run found dependency ordering assumptions and test-row
contamination (**25 passed, 3 failed**). Mixed routers were changed to explicit
read protection so existing mutation identity-first order is preserved; test
cleanup was bounded to its disposable users. The clean rerun passed.

## Limits

No browser/account/settings UI check was run; B owns it. Login throttling
remains bounded and process-local as already documented. This local cookie
session boundary has not received an Internet deployment penetration test.
