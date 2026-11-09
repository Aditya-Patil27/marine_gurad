# B0 brief — finish B-005F and the reviewed event journey

Outcome: an analyst on a selected historical GFW event with a 404 vessel lookup can create an explicit
event-only report and case, open the stored evidence and export it without a fabricated score.

Allowed writes: `apps/web/**`, `tasks/B-005F.md` result, this brief, `tasks/parallel/B-status.md`.

Dependency/contract: A-004F (present in working tree; migration 014 reported applied).
`POST /reports/` body `{mmsi, event_only: true, gfw_event_id, gfw_start_date, gfw_end_date, gfw_offset,
gfw_limit, include_gfw_ocean_context}`; cannot carry assessment/window/weather. Then
`POST /cases/ {report_id, title}` creates revision 1 atomically.

Callers touched: `reportsApi.create*`, `casesApi.create*`, `EvidencePage`, `ReportsPage`,
`GfwEventEvidence`, `B005Journey` fixture path.

Acceptance checks:
1. Focused test: vessel 404 + selected event → one `Create event-only review`; exact report body; then
   `{report_id, title}`; no assessment sync and no `/cases/{id}/revisions`; double click sends one write;
   navigation to the case; report page shows unavailable AIS/assessment + event limitations, no score.
2. Focused test: no event-only action on generic API failure or absent event; case failure keeps the report
   ID and a retry calls only `/cases/`; existing assessment-backed B-005 test still passes.
3. Production build.
4. Actual browser: real historical GFW event with missing AIS → report → case revision 1 → stored evidence and
   export, verified hash outside the UI. Record if the stable runtime/credentials are unavailable.

Skips: no backend edits, no dependency additions, no live AIS/fishing/illegality claim.
