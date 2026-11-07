# Local authentication setup (A-001)

This guide creates a local user and session so an analyst can log in without
internet access or marine provider credentials. Reports, cases and selected
mutations require roles and CSRF; some legacy reads remain public.

## Prerequisites

- The Compose stack from `infra/docker-compose.yml` is running, or a local
  PostgreSQL/PostGIS instance is configured in `apps/api/.env`.
- `DATABASE_URL` points at the target database. Never reuse the shared
  development database for destructive testing.

## 1. Apply the migration

```bash
cd apps/api
alembic upgrade head
```

Migration `006_auth_tables` only adds `users`, `user_role_assignments` and
`user_sessions`; existing evidence tables are untouched.

## 2. Create the first administrator

No default credentials exist. Run the interactive script; the password is read
with hidden input and is never accepted as a command-line argument:

```bash
cd apps/api
python scripts/create_local_admin.py
```

For the running Docker stack, run `docker exec -it -w /app samudrasense_backend python scripts/create_local_admin.py` in your terminal. Enter the password interactively; do not paste it into chat. The application has a sign-in control in the top bar.

The script refuses to overwrite an existing username. The created account has
the `ADMINISTRATOR` role, which implies all other roles.

## 3. Configuration

Relevant variables (see `apps/api/.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `AUTH_SESSION_COOKIE_NAME` | `samudra_session` | HttpOnly session cookie |
| `AUTH_CSRF_COOKIE_NAME` | `samudra_csrf` | Readable double-submit cookie |
| `AUTH_SESSION_TTL_MINUTES` | `480` | Session lifetime |
| `AUTH_COOKIE_SECURE` | `false` | Set `true` when served over HTTPS |
| `AUTH_LOGIN_MAX_ATTEMPTS` | `5` | Failed logins per window/key |
| `AUTH_LOGIN_WINDOW_SECONDS` | `300` | Throttle window |

The defaults are development values, not production security. Plain HTTP keeps
`AUTH_COOKIE_SECURE=false`; any HTTPS deployment must set it to `true`.

## 4. Verify

```bash
curl -i -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"<admin>","password":"<password>"}'
```

Use the returned cookies for `GET /api/v1/auth/me`; send the `samudra_csrf`
cookie value in `X-CSRF-Token` for `POST /api/v1/auth/logout`.

Focused tests:

```bash
# Unit-only checks run without a database (DB tests are skipped)
pytest apps/api/tests/test_auth.py -q

# Full auth tests against a disposable migrated database
TEST_DATABASE_URL=postgresql://.../samudrasense_auth_test pytest apps/api/tests/test_auth.py -v
```

Database tests are skipped when `TEST_DATABASE_URL` is unset; a skip is not a
pass. Prepare an isolated database, run `alembic upgrade head` against it, and
point `TEST_DATABASE_URL` at it. Tests roll back their own transaction and do
not seed or reset the shared database.

## 5. Deployment caveats

- Some legacy routes remain public; do not expose the API publicly without a complete security review.
- The admin bootstrap is intentionally interactive and must be run by an
  authorised operator; there is no HTTP bootstrap endpoint.
- Login throttling is process-local; multiple workers do not share counters.
- Password reset, MFA and email verification are not implemented.
