# Auth API contract (A-001, report and mutation protection in A-002A/B)

Implemented 4 November 2026. Prefix `/api/v1`. This is an **offline local**
session/role foundation, not a public-facing security claim. Only the `/auth`
session routes, the report routes in `## Report protection (A-002A)` and the
ingest/SAR/chat mutation routes in `## Mutation protection (A-002B)` use
authentication; every other legacy route remains **unauthenticated** (see the
list at the end).

## Session transport

- `POST /auth/login` sets two first-party cookies:
  - `samudra_session` — opaque session token, `HttpOnly`, `SameSite=Lax`,
    `Path=/`, `Secure` only when `AUTH_COOKIE_SECURE=true`.
  - `samudra_csrf` — readable double-submit token, `SameSite=Lax`, not
    `HttpOnly`.
- Only a SHA-256 digest of the session token is stored (`user_sessions.token_hash`).
  The raw token exists only in the cookie.
- Account passwords are hashed with Argon2id (`argon2-cffi`). Neither hashes nor
  raw tokens are returned by any endpoint or written to logs.
- With the Vite `/api` proxy the cookies are same-origin, so `SameSite=Lax`
  suffices. Cross-site browser origins are not supported.
- Non-browser clients have no API-token mechanism yet; out of scope for A-001.

### CSRF

Unsafe methods (`POST`, `PUT`, `PATCH`, `DELETE`) authenticated by cookie must
echo the `samudra_csrf` cookie value in the `X-CSRF-Token` header
(double-submit). A missing or mismatched value returns `403`. `POST /auth/login`
is exempt because no session exists yet. `POST /auth/logout` enforces the check.
A-002A applies `csrf_protect` to the report create and sign routes; A-002B
applies it to the ingest, SAR and chat mutation routes. Later A-002 slices must
apply it to every other added mutating route.

### Errors

Errors use FastAPI's shape `{"detail": "..."}`. Login failures share one generic
`401` for unknown user, wrong password, disabled, revoked and expired accounts
to avoid account enumeration.

## Endpoints

### `POST /auth/login`

Request:

```json
{"username": "analyst", "password": "..."}
```

`200` response:

```json
{
  "user": {
    "id": "uuid",
    "username": "analyst",
    "email": null,
    "full_name": null,
    "is_active": true,
    "created_at": "2026-11-04T12:00:00",
    "last_login_at": "2026-11-04T12:00:00",
    "roles": ["ANALYST"]
  },
  "expires_at": "2026-11-04T20:00:00",
  "csrf_token": "opaque-token"
}
```

The same CSRF token is also present in the `samudra_csrf` cookie.

Errors: `401` invalid/inactive; `422` missing or malformed fields; `429` too many
failed attempts (`Retry-After` header, bounded process-local counter).

### `POST /auth/logout`

No body. Requires the session cookie and `X-CSRF-Token`. Revokes the current
session and clears both cookies.

`200`: `{"message": "Logged out"}`. `401` when no valid session exists; `403`
when the CSRF header is missing or wrong.

### `GET /auth/me`

Returns the `user` object above for the current cookie session.

`401` when the cookie is missing, revoked, expired, or the account is disabled.

## Roles

| Role | Intended capability (report routes enforced in A-002A) | Implies |
|---|---|---|
| `VIEWER` | Read-only access | `VIEWER` only |
| `ANALYST` | Investigate and draft | `VIEWER` |
| `APPROVER` | Approve reviewed evidence and send | `VIEWER` |
| `ADMINISTRATOR` | Accounts and settings | every role |

Investigation/drafting (`ANALYST`) and approval/sending (`APPROVER`) are
**separate duties**: neither role implies the other. A user who must do both
holds both assignments explicitly (for example `["ANALYST", "APPROVER"]`), and
then passes both `require_analyst` and `require_approver`. Both single roles
inherit read-only `VIEWER` access. **Administrator implies every other role**
(`UserRole.implies`); no separate administrator is created by this revision.

Dependencies exported from `app.api.auth`:

- `get_current_user`
- `require_roles(*roles)`
- `require_viewer`, `require_analyst`, `require_approver`, `require_admin`

They resolve identity only from the session cookie; a user id or name in a
request body is never treated as identity. These dependencies protect only the
routes that explicitly declare them; they are not a route-wide security
guarantee.

## Report protection (A-002A)

The existing report API now uses these dependencies. This first bounded slice
does not prove whole-API authorization and adds no dispatch, digital signature
or complete immutable-revision feature.

| Route | Requires | Unsafe-method CSRF |
|---|---|---|
| `GET /reports/` | `VIEWER` (inherited by Analyst, Approver, Administrator) | n/a |
| `POST /reports/` | `ANALYST` or `ADMINISTRATOR` | `X-CSRF-Token` required |
| `POST /reports/{id}/sign` | `APPROVER` or `ADMINISTRATOR` | `X-CSRF-Token` required |

- Anonymous requests return `401`; authenticated users lacking the role return
  `403`. On unsafe routes the identity/role dependency resolves before
  `csrf_protect`, so anonymous requests are `401` rather than `403`.
- A missing or mismatched CSRF token returns `403`. All dependencies resolve
  before the endpoint body, so denied requests do not read or write report data.
- `POST /reports/` keeps its existing body
  `{mmsi, include_regional_ocean_context?}`, optional regional SST behavior and
  hashed snapshot checksum.
- `POST /reports/{id}/sign` still accepts the legacy `officer` string in the
  request for frontend compatibility, but **ignores it for identity**: the
  persisted `signed_by` is the authenticated session user's `username`.
  `reviewed=true` is still required (`400` otherwise). `404` (not found), `409`
  (failed checksum or already signed), row locking and UTC sign time are
  unchanged. This is an authenticated local approval record, not a digital
  signature or email dispatch.

### Handoff to User B for reports

Existing frontend report calls now require an authenticated cookie session and
the CSRF header. Until B integrates auth:

- send the session and CSRF cookies (`credentials: "include"` when not using
  the Vite proxy);
- send `X-CSRF-Token` on `POST /reports/` and `POST /reports/{id}/sign`;
- treat `401` as signed-out, `403` as missing role or bad CSRF, and display the
  authenticated `signed_by` returned after sign-off rather than the typed
  officer.

The current frontend cannot create or sign reports until B makes that change.
Routes not covered by A-002B below remain unprotected in the meantime.

## Mutation protection (A-002B)

The five remaining mutating prototype routes now require the same identity-first
pattern: `require_analyst` resolves before `csrf_protect`. Administrator implies
Analyst; Viewer and Approver-only cannot mutate. This bounded slice does not
prove whole-API authorization.

| Route | Requires | Unsafe-method CSRF |
|---|---|---|
| `POST /ingest/ais` | `ANALYST` or `ADMINISTRATOR` | `X-CSRF-Token` required |
| `POST /ingest/satellite-image` | `ANALYST` or `ADMINISTRATOR` | `X-CSRF-Token` required |
| `POST /sar/detections` | `ANALYST` or `ADMINISTRATOR` | `X-CSRF-Token` required |
| `POST /chat/message` | `ANALYST` or `ADMINISTRATOR` | `X-CSRF-Token` required |
| `POST /chat/reset` | `ANALYST` or `ADMINISTRATOR` | `X-CSRF-Token` required |

- Anonymous requests return `401`; an authenticated user lacking the role
  returns `403`. A missing or mismatched CSRF token returns `403`.
- All dependencies resolve before the endpoint body, so denied requests do not
  write AIS/pollution/SAR data, rescore the fleet, start a job or call a model
  or provider (including Gemini).
- Payloads, responses and error handling are unchanged. `POST /ingest/ais`
  still rescales the recent fleet after insert; `POST /ingest/satellite-image`
  still returns `503` when its model is not loaded and records only recognised
  pollution classes; `POST /sar/detections` still stores a nearby AIS ping as a
  candidate only and does not treat missing AIS as proof of evasion. The
  pollution worker is not validated by this change and SAR evidence does not
  prove illegal activity.

### Handoff to User B for mutations

Any client calling these five routes must send the session and CSRF cookies
(`credentials: "include"` when not using the Vite proxy) and echo the
`samudra_csrf` value as `X-CSRF-Token`. Treat `401` as signed-out and `403` as
missing role or bad CSRF. No current frontend code calls these mutations, so
this is a forward contract rather than a broken existing call.

## Handoff to User B (frontend)

- Call `POST /api/v1/auth/login` with `{username, password}` and fetch
  credentials `same-origin` (`credentials: "include"` when not using the Vite
  proxy). On `200`, show the returned `user.username` and `user.roles`.
- Treat `401` from `/auth/me` as "not signed in" and show the login screen.
- Read the `samudra_csrf` cookie (not HttpOnly) and send its value as
  `X-CSRF-Token` on every `POST`/`PUT`/`PATCH`/`DELETE`; `POST /auth/logout`
  requires it.
- Do not store the session token in `localStorage`; the HttpOnly cookie is the
  only session transport.
- `403` on a protected route means the role is insufficient or the CSRF token
  is missing/wrong; show the required roles from this table rather than retrying.
- Login `429` includes `Retry-After` seconds.

## Still unauthenticated after A-002B

`/map`, `/analytics`, `/alerts`, `/vessels`, `/weather`, `/ocean`, `/aisstream`,
`/gfw` remain unauthenticated. On the touched routers, reads remain public:
`GET /sar/detections` and `GET /chat/health`. Report routes are protected as
described above and the five mutation routes are protected by A-002B. The API
must not be described as secured or exposed publicly before the remaining
A-002 route slices are applied and tested.

## Limits

- Login throttling is per API process and keyed by normalized username plus the
  direct client IP. Bounded (least-recently-touched keys are evicted), not
  shared across workers, and behind a reverse proxy the peer address may be the
  proxy. It is a workstation defence, not a distributed rate limiter.
- One active session per user; a new login revokes earlier sessions.
- No password reset, MFA, email verification or account self-registration.
