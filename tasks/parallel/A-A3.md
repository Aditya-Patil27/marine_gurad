# A3 — report and export guarantees

Status: COMPLETED — 9 November 2026. Owner: A only.

## Implemented slice

- Migration `016_report_canonical_snapshot` preserves exact canonical UTF-8 JSON bytes for new reports; legacy rows remain compatible with their existing checksums.
- Reports now have authenticated single-report retrieval, a verified manifest and an approved-only deterministic PDF export. The manifest identifies canonical bytes, checksum scope and source references without presenting the checksum as a signature.
- Approval accepts an optional `expected_sha256` guard and validates stored source references before signing; tampered, missing or mismatched assessment/GFW evidence returns 409.
- Focused tests cover decimal-scale canonical bytes (`59.0`), deterministic PDF content, tamper/missing-reference rejection and stale approval rejection. Authorization coverage adds the new read routes.

## Changed A-owned paths

- `apps/api/app/api/reports.py`
- `apps/api/alembic/versions/016_report_canonical_snapshot.py`
- `apps/api/tests/test_report_exports.py`
- `apps/api/tests/test_report_authorization.py`
- `docs/contracts/USER_A_DATA_API.md`

## Verification

- Isolated A backend migration: `alembic upgrade head && alembic current` → `016 (head)`.
- Focused container suite (without disposable DB URL): **12 passed, 5 skipped**.
- Unique disposable database `a3_verify_20261109`, migrated from empty through `016`:
  `PYTHONPATH=/app TEST_DATABASE_URL=$DATABASE_URL python -m pytest tests/test_report_exports.py tests/test_report_authorization.py -q` → **17 passed**.
- The disposable database was dropped after the run. The shared stack/database was not migrated, reset or seeded.

## Limits

No browser PDF-download journey was run; that is a B-owned integration check. The checksum remains explicitly documented as an integrity checksum, not a digital signature or proof of source authenticity.
