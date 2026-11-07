# Judging replay runbook and demo checklist

Prepared 6 November 2026 for the 10 November judging slice. This reuses
[B's storyboard](storyboard.md); it adds the operator pre-flight, the exact
browser path and the source statements the presenter must say. Read values from
the screen during the recording, not from this document.

The local vessel tracks are **invented replay data** from `scripts/seed_demo.py`.
GFW points are **historical inferred events**, not vessel tracks. Copernicus SST
is a **historical satellite subset**, not a live forecast. None of these prove
illegal activity.

## 1. Pre-flight (5 minutes)

```powershell
# From the repository root. Read-only checks; nothing is reseeded or reset.
docker compose -f infra/docker-compose.yml ps
docker exec -it -w /app samudrasense_backend python scripts/verify_judging_replay.py
```

The script prompts for the local Administrator password with hidden input when
run with `-it`. The password is not printed, logged or stored. For a
non-interactive run, set `SAMUDRA_VERIFY_USERNAME` and
`SAMUDRA_VERIFY_PASSWORD` only in the current process environment; do not paste
them into shared shell history.

Expected result:

- `PASS` for migrations `008`, 14 replay vessels, replay freshness inside 168 h,
  the active `ADMINISTRATOR` account, API health, replay through `/vessels`,
  historical SST and the bounded GFW GeoJSON page.
- `PASS` for administrator sign-in when credentials are supplied. Without them
  the result is `PARTIAL` and never a fabricated pass.
- `FAIL` is a stop condition. Read the failing line; do not proceed to record.

The checker makes one bounded GFW request (`2024-01-01`..`2024-02-01`, 5
features) and performs one login/logout. It does not run migrations, reset
volumes, reseed tracks or change case/report rows; it compares those row counts
before and after.

If replay freshness fails, refresh the demo **deliberately** (this replaces only
the demo MMSIs and sample boundaries):

```powershell
docker exec -w /app samudrasense_backend python scripts/seed_demo.py
```

Do not run that against a database whose cases/reports you have not reviewed.

## 2. Browser journey (about 6 minutes)

1. Open <http://127.0.0.1:5173> (redirects to `/map`).
2. Top strip: click **Sign in to create or review reports**, enter the local
   Administrator account, click **Sign in**. The strip must read
   **Signed in as adishnair (ADMINISTRATOR)**.
3. Map: point at the Gulf of Mannar, the indicative protected-area polygons and
   the vessel markers. Bottom-left card **Regional environmental conditions**
   shows the historical Copernicus SST value, observation date/time in IST and
   the provider attribution.
4. Right card **GFW historical apparent fishing events**: keep
   `2024-01-01` to `2024-02-01`, click **Load historical events**. It should show
   the number shown, the total and **source: Global Fishing Watch**. Select one
   event and click **Download event evidence and historical SST**; the JSON has a
   SHA-256 checksum, not a signature.
5. Left rail **Alerts** → **Alert triage** → **Needs review** / **Watch**.
   Open **Sea Pearl II** (or whichever replay vessel the screen shows).
6. Evidence page: **Why it was flagged**, **Data limitations**, **Checks**,
   **Weather at AIS gap**, **Track and encounters**, **SAR candidates**. SAR is
   expected to be empty; say so rather than implying a detection exists.
7. Click **Create investigation case**. The case screen opens at
   `/cases?id=…` with status `open` and one linked report revision.
8. **Reports** → open the new report. Check **Snapshot hash verified**. Tick
   **I reviewed the evidence and source snapshot**, then **Record sign-off**.
   The reviewer must be the signed-in session identity.
9. Return to **Cases** to show the linked revision, then show the reports list
   marks the report **Signed**.

## 3. Source and mode statements

Say these explicitly; do not let any visual imply more than the data supports.

| What is on screen | Say |
|---|---|
| Local replay vessels (Sea Pearl II, Hai Feng 818, 10 ordinary vessels) | "These tracks are invented local replay data from our seed script. They are dated 31 October–1 November 2026 and shown through a bounded seven-day look-back. They are not live AIS, not GFW tracks and not provider positions." |
| Top data-mode strip | "The strip currently reads **Source not reported** because vessel records do not carry a verified ingestion source. We show the uncertainty rather than labelling them live." |
| GFW event layer | "These are historical inferred apparent-fishing events from Global Fishing Watch for January 2024. Each dot is an event location, not a live vessel position or a reconstructed track." |
| Copernicus SST card | "This is a historical satellite-derived sea-surface temperature for a single grid cell, observed on 20 October 2026. It is context only; it is not a forecast and does not change risk scores." |
| Risk score and factors | "The score is an additive rule-based screening signal. A gap, loitering or encounter is an indicator for human review, not proof of an offence." |
| Report hash and sign-off | "The SHA-256 detects accidental changes when compared with a trusted copy. It is not a digital signature. Sign-off records the local session identity and does not send the report anywhere." |
| Case screen | "A case links a saved assessment to report revisions. Case close/reopen and audit APIs exist; their UI controls and source-linked evidence beyond this local replay remain incomplete." |

Do not say: live tracking, real GFW vessel tracks, detected illegal fishing,
confirmed identity from SAR, measured enforcement impact, or global climate
prediction.

## 4. Failure states to explain

If one of these appears, name it and continue; do not improvise data.

| Screen state | Meaning | Action |
|---|---|---|
| Top strip **Can't reach the API · … Showing the last data received, not live.** | Backend unavailable; the UI keeps the last response visible. | Run the pre-flight checker; restore the backend. Do not call the screen live. |
| **Environmental data not available** (bottom-left map card) | The prepared Copernicus JSON subset is missing or unreadable. | `verify_judging_replay.py` reports `FAIL` for historical SST; restore the local artifact, do not substitute a value. |
| **Historical events unavailable. Check the dates and provider access.** | GFW refused or could not answer (token, quota, network). | The checker reports the HTTP status. Say the external source is unavailable; the rest of the console still works. |
| Alerts/evidence empty or no assessment exists | Replay positions are outside the 168 h look-back or the seed was never loaded. | The checker reports replay freshness/vessels `FAIL`; state that the replay is stale; do not reseed the shared database. A-005B will add fixed historical selection. |
| **Sign-in failed. Check your account and password.** | Wrong credentials or throttled login. | Stop creating reports; do not claim authenticated approval. |
| **No candidate SAR detection recorded for this vessel.** | No permitted point SAR evidence is integrated. | Say point SAR remains unavailable; do not infer a detection from an aggregate layer. |
| Report **Awaiting review** after clicking sign-off | No valid Approver/Administrator session. | Sign in; do not type a reviewer name as a substitute. |

## 5. Known gaps for this run

- Case status UI operations, source-linked real tracks and point SAR remain
  unimplemented or unverified; case creation is a bounded local slice.
- The vessel evidence empty-state text still says "last 24 h" while the API uses
  a seven-day window; trust the actual window and the timestamps on screen.
- Weather is Open-Meteo model context and does not alter risk scores.
- The frontend test runner (`vitest`) was absent in the container at the last
  check; the production build is the verified frontend check.
- No screenshots or provider results are invented by this runbook. Use the
  actual screen during the recording.
