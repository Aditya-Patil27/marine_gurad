# B-005 handoff to A (8 November 2026)

From B (frontend). Branch `b/judging-slice`, pushed to `origin/b/judging-slice`. Full record: [tasks/B-005.md](../../tasks/B-005.md).

## What is done

| Item | State | Evidence |
|---|---|---|
| Historical replay, fleet → assessment → case → report | Done in a real browser, synthetic seed in a throwaway DB | `tasks/B-005.md` Status 1 |
| GFW event → vessel page → report request (A-004E contract) | Done in code and focused test; event list and attach link verified with live GFW | Status 2 |
| GFW report without the SST file | Frontend sends `include_gfw_ocean_context` / `include_regional_ocean_context` = `true` only when `GET /environment/regional` loads | commit `2cbc337` |
| Real event-to-case journey | **Blocked on data** (see below) | Status 3 |

Commits: `0836e04` (B-005 replay), `2cbc337` (SST optional). No backend file was changed.

## What B needs from A

1. **Real AIS for a GFW event vessel, inside a replay window.** This is the only thing blocking the real journey.
   - The GFW public API gives events and identity, not AIS position history.
   - AISStream does not cover the area. On 8 Nov B ran the existing `_run_aisstream` path with `AISSTREAM_PERSIST_ENABLED=true` against a separate B-only database, then a 3-minute listen over `aisstream.BOX`, and got **0 positions** both times. A 20-second worldwide listen with the same key got 873 positions, only 1 of them in 0–25N, 65–95E. The key works; there are no receivers near the Gulf of Mannar. Recording forward for days would not help.
   - Options, A's decision:
     - a historical AIS export for the region (satellite AIS provider, or a dataset A already has), loaded with source provenance and not relabelled;
     - accept a GFW-event-only journey, where a report can carry event evidence for a vessel with no AIS in the window (needs a backend contract change: today the vessel page returns 404 and no case is offered);
     - move the demo to a region that AISStream covers.
   - Once AIS exists, tell B the dates. B changes the replay preset (`apps/web/src/lib/replayWindow.jsx`) to match.
2. **The Copernicus SST subset** `apps/api/data/copernicus/gulf_mannar_sst_20261018_20.json`. It is gitignored and missing from both checkouts. It is now optional for reports, but `/environment/regional` and SST in evidence need it. Reproduction steps are in `docs/DATA_MANIFEST.md`.
3. **Credentials in `apps/api/.env.example`, lines 64–66.** This tracked file holds a JWT-shaped GFW token (issued 2026-11-04, expiry 2036-11-01; different from the one in `.env`) and Copernicus values. The repo is public. Please confirm whether these are placeholders or real; if real, rotate them and replace with empty values.
4. **"Data mode" header label.** The shell header said "Source not reported" while the report for the same data said "Synthetic data". The header reads a separate status endpoint; please check what it should return for seeded data.
5. **Migration 013 on B's shared database.** The `samudrasense_postgres_data` volume is at alembic 002 (678 rows dated 13 Oct). B did not migrate it. Either migrate it, or confirm that B should keep using throwaway databases.
6. **Stored alerts and replay data.** `POST /alerts/sync` calls `check_mpa_violations()`, which only reads `vessel_tracks` from the last hour (`alert_generator.py:110`). For a replay window, sync finds 0 alerts; B got 2 only after reseeding the throwaway DB at the current time. The titles say "MPA Violation Detected". Please decide whether sync should follow the selected window, and whether "Violation" is the wording you want for a screening record.
7. **Report hash and JSON numbers.** The hash covers Python's text, where `course` is `59.0`. Any client that parses the JSON and writes it again gets `59`, so the hash no longer matches. B's export now saves the server text unchanged (verified: hash recomputed outside the app matches). A single-report `GET /reports/{id}` would let B stop extracting the report from the list text.

## Known, not caused by B-005

- 14 frontend tests that were failing before this work are fixed: they expected the removed "Officer name" field and the pre-replay call signatures. The full frontend suite now passes.
- The compose `samudrasense_backend` mounts the main `b/sprint` checkout, which has no migration 013 and no sources code. B ran its own backend container from this worktree instead.

## Local state left behind

- Stopped containers `b_ais_recorder` and `b_ais_rec_pg`, network `b_ais_rec`, and volume `b_ais_recording_data`. They hold 0 positions and can be deleted. Nothing shared was modified.

Not claimed: the full judging gate, production readiness, real-time tracking, or illegal-activity detection.
