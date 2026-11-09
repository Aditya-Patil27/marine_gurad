# A0 — stable baseline for simultaneous work (brief and result)

Status: COMPLETED — 8 November 2026. Owner: A only.

## Outcome

Publish a stable, source-frozen backend snapshot for B's browser checks, a separate A development/test stack, and non-secret start/migration/health/schema/account instructions. The shared `samudrasense` stack is untouched.

## Baseline captured

- HEAD `dde0c119e7551667883f3c4a8f1a807d0918f2bc` (includes B's `dde0c11` frontend work).
- Working tree keeps A-004F (`app/api/reports.py`, `app/api/cases.py`, `alembic/versions/014_event_only_case.py`, contract, tests) uncommitted as found.
- Baseline hashes: `.agent-runs/parallel-A-20261108-221250/` (`head.txt`, `status-before.txt`, `a-004f-baseline.txt`).

## Runtime

Snapshot image `samudrasense-api:014-a004f` (`sha256:ea6e2688…`), built from the current `apps/api` working tree on the project's existing dependency layer. No source mount, no `.env` baked into the image (`**/.env` is in `.dockerignore`), no reload.

| Item | Value |
|---|---|
| Schema | Alembic `014 (head)` (`014_event_only_case`) |
| Contract | A-004F event-only report/case in `docs/contracts/USER_A_DATA_API.md` |
| B backend | `http://localhost:8002`, container `samudrasense_backend_b` |
| B database | `samudrasense_b` on `localhost:5433` (volume `postgres_b_data`) |
| B redis | `localhost:6380` |
| A backend | `http://localhost:8001`, container `samudrasense_backend_a` (live source mount) |
| A database | `samudrasense_a` on `localhost:5434` (volume `postgres_a_data`) |
| A redis | `localhost:6381` |

## B start / migration / health

```powershell
docker compose -f infra/docker-compose.parallel-b.yml up -d
# schema (the container runs `alembic upgrade head` on start):
docker exec samudrasense_backend_b sh -lc "cd /app && alembic current"
# non-secret health check:
Invoke-RestMethod http://localhost:8002/health
```

`infra/docker-compose.parallel-b.yml` deliberately uses `environment:` overrides, so the shared `apps/api/.env` (env_file) cannot redirect B to the shared database; values in `environment` win.

Approved local account (interactive, hidden password, no default credentials):

```powershell
docker exec -it samudrasense_backend_b python scripts/create_local_admin.py
```

The frontend may call the backend at `http://localhost:8002` from origin `http://localhost:5174`; both allowed CORS origins are configured in the B compose file.

## Verification actually run

- `docker compose -f infra/docker-compose.parallel-a.yml up -d` → A stack healthy.
- A snapshot container: `GET http://localhost:8001/health` → `{"status":"healthy"}`; `alembic current` → `014 (head)`.
- Disposable B-snapshot proof: same image started on port `18002` against a fresh `samudrasense_a0_verify` database with no source mount → health `{"status":"healthy"}`, migrations applied, `alembic current` → `014 (head)`; container removed and database dropped (`WITH (FORCE)`).
- `python -c "import argon2, app.main"` → `SamudraSense 1.0.0` (the pre-existing base image lacked the `argon2-cffi` already in `requirements.txt`; the snapshot layer installs the pinned package).
- Container logs contain no credentials; no secret value was printed in this record.

## Notes / limits

- The shared stack (`samudrasense_backend:8000`, postgres `:5432`, redis `:6379`) was not restarted, migrated or seeded.
- B's session had already started its own container `samudrasense_b_backend` on `127.0.0.1:8002` from image `samudrasense-backend-b0` before this phase finished; A did not stop or reuse it. The A recipe above is the documented alternative when that container is stopped; the port and schema are identical.
- No live provider call was made. The image is a local artifact, not a released build; a clean full rebuild was not completed (the full pip build exceeded the local build window, so the verified image reuses the project's existing dependency layer plus the one missing pinned package).
