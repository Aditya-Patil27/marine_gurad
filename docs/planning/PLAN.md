# SamudraSense plan

Status: **draft for team review** (13 Oct 2026, update 7), written by the planning session. Section 13 lists what changed since the first draft.

This is the only planning file. It holds the current-state baseline, the scope for the 10 Nov 2026 submission, the epics, the first stories, the dependency map, the decision log, the open questions and the split of the work into Frontend, Backend and AI parts. The product description stays in [README.md](../../README.md) and the screen designs stay in [docs/design/DESIGN.md](../design/DESIGN.md); this file does not repeat them.

Sections 4 to 8 are proposals. Nothing in them is approved until section 9 records the decision. Until then the Backend and Frontend sessions inspect and report; they do not build from these stories.

| If you are | Read |
|---|---|
| The team | 1, 4, 8, 10 (fourteen decisions are waiting for you), 13 |
| The owner of the Frontend, Backend or AI part | Your part of [section 12](#12-work-split-frontend-backend-and-ai) first, then the stories it names in 5 and 6, then 7 |
| Audit | 2, 3, and the evidence column in section 7 |

## 1. Target

| | |
|---|---|
| Submission | 10 Nov 2026: a demo video and a complete project (decision D1) |
| Finale | 20–21 Jan 2027 |
| Time left | Four weeks from 13 Oct 2026 |
| Compute | One RTX 3050, plus Kaggle and Colab for training (D3) |
| Models | None trained yet (D2) |

**User.** An enforcement officer at a small coastal agency, or an analyst at an NGO, who has to decide which vessel deserves a patrol and has to justify that decision (README, "The problem" and "Explainable by design").

**Journey.** Predict, Detect, Verify, Act. The part that runs today is narrow: the officer opens the map, sees which vessels are flagged, and reads why. They cannot pick up an alert, see radar evidence, see who the vessel met, or produce a report.

**Scope for 10 Nov**, from `README.md:97`: end-to-end alert flow, SAR + AIS fusion on xView3, hotspot forecasts, evasion state machine and weather triage, encounter graph, explainable alerts. How "complete project" maps onto this list is assumption A1 in section 10.

## 2. Current state

Checked on 13 Oct 2026 against branch `ap`.

**What was run**

| Check | Result |
|---|---|
| `apps/api/tests/test_risk_engine.py` | 10 passed. Run outside Docker on Python 3.12.7 with the pinned numpy 1.26.4 and shapely 2.0.2 (the README asks for 3.11) |
| `npm run build` in `apps/web` | Succeeded |
| `npm test` in `apps/web` | 6 test files, 59 tests passed, on Frontend's uncommitted work. Frontend reports `npm ci`, the build and the tests also pass on a clean copy |
| Running stack, read only, 13:20 UTC | The backend, Postgres and Redis containers were up. The Frontend session had started the existing `samudrasense` containers on their existing volume and run the demo seed at about 12:52 UTC. The Celery worker and frontend containers were not. `GET /vessels/` returned 14 vessels with only Sea Pearl II at alert level. `GET /vessels/419007431` returned 0.63 (AIS gap 0.31, encounter 0.18, loitering 0.14), receiver outage ruled out, weather not checked |

**What was not run or read.** Planning has not opened the console in a browser and has not written to the running stack, so the path from ingest to screen has still not been seen working as a whole. Findings marked Backend, Frontend or Audit were reported by those sessions; planning re-checked the ones it could read without writing. `model_registry.py` and `agent_lightning.py` were not read in full. The demo video, GitHub issues and pull requests were not reviewed.

**Status words.** Implemented and verified; implemented but unverified; partially implemented; broken; planned; unknown. **Proposals for existing code:** KEEP, FIX, SIMPLIFY, REBUILD, FREEZE (no changes until a decision), DELETE (only after approval).

| Capability | Status | Proposal | Evidence |
|---|---|---|---|
| Additive risk score, receiver-outage check, "what would clear it" | Implemented and verified (unit tests only) | KEEP | `apps/api/app/services/risk_engine.py`; 10 of 10 tests |
| Vessel API and protected-area zones | Implemented and verified for reads on seeded data (Frontend, planning and Audit, each on 13 Oct). One bad ingest record makes it return 500 (G11). The end-to-end check (E6-S3) is still open | KEEP | `apps/api/app/api/vessels.py`, `apps/api/app/api/map.py:320`; live responses on 13 Oct |
| Map console (screen 01) | Implemented; checked by Frontend in a browser against the seeded API. Audit verified Frontend's nine fixes by reading the changed files, and ran the tests. The end-to-end check (E6-S3) is still open | KEEP; basemap is online; one layout question (Q12) | Frontend ran the dev server and the production build at 1024, 1280 and 1600 px. Esri tiles at `apps/web/src/features/map/OceanMap.jsx:6` |
| Demo seed (Sea Pearl II story) | Implemented and verified at load time; fades within hours (G10) | KEEP, FIX | `apps/api/scripts/seed_demo.py`; 14 vessels and 678 pings (Backend) |
| AIS ingest (POST route and CSV loader) | Broken on bad input: one record can take the console down (G11, reproduced by Audit). Otherwise unverified | FIX: story E6-S4; no authentication (G6) | `apps/api/app/api/ingest.py:42,95`; `apps/api/scripts/ingest_ais.py` |
| Alerts API | Partially implemented | REBUILD (epic E1) | Gap G2 |
| Background jobs (Celery) | Partially implemented | Decide in E1-S2 | Three tasks are defined, nothing dispatches them, and the worker container is not running |
| Frontend tests | Implemented and verified: 6 files, 59 tests pass | KEEP | `apps/web/tests/`, uncommitted; run by Frontend, planning and Audit on 13 Oct |
| Route prediction (LSTM) | Partially implemented | FREEZE | No weights; falls back to a straight line |
| Pollution detection (YOLOv8) | Partially implemented | FREEZE | No weights; the route returns 503 |
| Chat assistant (Gemini) | Implemented but unverified | FREEZE | No screen calls it; a cloud model against the offline goal. Audit (rated Medium): the route is still reachable, returns errors as HTTP 200 with the exception text, accepts a 200,000-character message and trusts assistant turns sent by the caller |
| Ocean health analytics | Partially implemented | FREEZE | Nothing writes to `ocean_health_metrics` |
| Weather triage | Planned | | The weather check is fixed at "not checked" (`risk_engine.py:360`) |
| Radar fusion, hotspots, evasion states, encounter graph, reports, spill simulator, local LLM, offline tiles, screens 02 to 05, login | Planned | | README stubs; placeholder routes in `apps/web/src/App.jsx` |
| `agent_lightning.py`, `demo_data.py`, `scripts/ingest_sentinel.py` | Dead or mock code | DELETE | No file imports the first two; the third uses example.com URLs |
| `model_registry.py` | Unused by default | SIMPLIFY | Active only when storage is not local |

## 3. Gaps and risks

| ID | Finding | Evidence |
|---|---|---|
| G1 | **Scope against time.** Six items are promised for 10 Nov. Only "explainable alerts" has code behind it, and only in the vessel panel. Two of the six need models that have not been trained. | `README.md:97`; D2 |
| G2 | **The alert list cannot show the headline case.** It only considers vessels that pinged in the last hour, and Sea Pearl II's last seeded ping is 6.2 hours old. Alert IDs are random on every request. There is no alerts table and no status, so the triage lanes and "downgraded, never deleted" have nothing to store. Audit confirmed these on the running stack. It adds that an alert's time is the time of the request, and that the `severity` filter returns nothing for `critical` or for an unknown word. E1 replaces this route. | `alert_generator.py:106`; `seed_demo.py:80`; `alerts.py:43-45,70,78` |
| G3 | **Two scoring paths disagree.** `/vessels` scores live. `/alerts` and `/analytics/statistics` read stored scores, which refresh only when AIS is ingested or the seed runs. The `rescore_fleet` task has no caller, nothing dispatches any task, and Compose runs no scheduler. `GET /map/layers` also reads stored scores, over a one-hour window; the console does not call it, and Audit saw it leave Sea Pearl II out. | `alert_generator.py:116`; `analytics.py:78,88`; `map.py:103,135`; `seed_demo.py:127`; `celery_app.py:157`; `infra/docker-compose.yml` |
| G4 | **"Dark" means different things in the README and the code.** The README says dark status needs a long gap plus a radar hull or a position jump. The code sets it when the gap is open, at least 4 hours long, and a receiver outage is ruled out. It needs neither the radar hull nor the jump. | `README.md:74`; `vessels.py:49`; `fleet.py:80`; `risk_engine.py:170-199` |
| G5 | **Offline goal against the build.** The basemap and the chat assistant both need the internet. This matters at the finale, not on 10 Nov (A4). | `OceanMap.jsx:6`; `README.md:98` |
| G6 | **No authentication on any route.** Audit rates this High, because it lets anyone who can reach the API trigger G11. The satellite-image route would also fetch any URL the caller gives it. Today it stops with 503 before the fetch because no model is loaded, so this opens the day weights are added. Audit's lower-rated notes belong with the same later story: Postgres and Redis are published on every network interface, Redis has no password, the backend container runs as root, and the satellite-image route returns raw error text (`ingest.py:191`). Backend relayed these; planning read only the last. | `ingest.py:42,107,121-123`; `pollution_detector.py:146` (Backend) |
| G7 | **Thin verification.** Only the risk engine has tests. There is no API or database test set-up, no CI, and nothing has been run end to end. | `apps/api/tests/`; no `.github/` |
| G8 | **Scoring cost grows with the square of the fleet.** Every vessel is scored against every ping in the window. On the seed (14 vessels, 678 pings) one fleet score takes about 0.1 s (Backend and Audit, each measured). Audit's scaling runs at the seed's 48 pings per vessel (timings of `risk_engine.explain` over made-up fleets with no database; Audit's own report, not rerun by planning): 0.2 s at 100 vessels and 0.9 s at 200 when the vessels are spread out; 4.4 s at 100, 15.5 s at 200 and 58 s at 400 when every vessel is slow and inside encounter range. The console's request timeout is 30 s. Audit rates this Medium, not a release blocker, and notes that slow vessels clustered in one protected area is the case the product is built for. | `fleet.py:55-64`; `apps/web/src/lib/api.js` |
| G9 | **The existing video shows mockups.** It walks through the designs with sample data, so it is not evidence of a complete project. | `README.md:17` |
| G10 | **The demo story fades within hours, and a vessel that stays dark disappears.** Backend scored the seed at later clock times: Sea Pearl II holds 0.63 for 15 h, drops to 0.45 when the encounter leaves the 24-hour window, and is gone from `/vessels` 17.9 h after seeding. The headline score is 0.03 above the threshold; the mockups show 0.87. From 4 h after seeding, 13 of 14 vessels show "receiver outage: not ruled out", because every seeded vessel stops reporting at seed time. `dark` stays true throughout. | Backend's timed runs of `score_fleet`, reproduced by Audit, which also saw 0.31 at 16 h. Planning saw 0.63 live. The hours come from single runs on the current seed: the fading is the finding, and the exact hours move if the seed changes |
| G11 | **Ingest accepts records that break the console.** Reproduced by Audit, which rates the first case Critical and the second High. First, a NaN latitude or longitude in one AIS record is stored as an empty point. After that `/vessels/` and `/vessels/{mmsi}` return 500 for every vessel, and every later ingest fails when it rescores, until the row is removed by hand. The route needs no login (G6). Second, one over-long field, such as a vessel name over 50 characters, fails at the commit, which sits outside the per-record error handling, so the whole batch is lost with its valid records. Third, a position dated in the future never leaves the scoring window, because the window has no upper bound. Fourth, out-of-range values are stored and served: Audit stored latitude 95, longitude 400 and a negative length, and read them back from `/vessels/{mmsi}`. The record has no range, NaN, length or date check. Audit also lost a valid record sent with an MMSI too large for its column (relayed by Backend). Backend expects a NaN speed to fail as the NaN position does, because both vessel routes return speed and the API cannot write NaN as JSON (`vessels.py:43,89`); it checked the parts and has not run it end to end. Backend measured that a negative speed earns up to 0.32 risk points, because the loitering and encounter rules read it as slow (`risk_engine.py:224,228,277`). | `ingest.py:19-21,54,95`; `models/vessel.py:132`; `fleet.py:30`. Audit ran these inside transactions that were rolled back; planning read the code and did not rerun them |
| G12 | **A real gap is set aside when nobody nearby is reporting.** The receiver-outage check counts an AIS gap only if another vessel within 50 km kept reporting during the silence. If a feed stops for a whole area, every dark vessel there loses its gap points. Audit raised this as a property of the rule, not only of the seed. | `risk_engine.py:46,176-191`; confirmed by Audit, which calls it a trade-off in the rule and not a defect |
| G13 | **Sending the same batch twice doubles the rows.** Ingest does not check for a position it already holds. Audit replayed a batch and the row count went from 2 to 4 (rated Medium). The position-jump factor skips pairs with no time between them, so planning does not expect scoring to fail on duplicates, but has not run it. | `ingest.py:51-95`; `risk_engine.py:205-206`; Audit |
| G14 | **A position with no speed ends a loitering or encounter run.** The engine reads an empty speed as "not slow". Backend measured it in memory: on a 6-hour encounter with positions 10 minutes apart, one empty speed in the middle cuts the encounter to 2.83 h, and an empty speed on every third position removes it (0.18 to 0). A 4-hour loitering run loses its 0.14 the same way. AIS has a "speed not available" value, 102.3 kn. Today it is stored as 102.3 and reads as fast, and under E6-S4 it is stored as empty, so the effect is the same before and after. Planning's reading: a vessel that sends that value keeps these points off its score. The seed has no empty speeds. The fix is in the engine, which is KEEP, so it is a later story and not part of E6-S4. | `risk_engine.py:224,228,277`; Backend's in-memory runs, not rerun by planning |

## 4. Scope for 10 Nov

Priority says whether the item is needed for 10 Nov. Status says what exists today. They are separate on purpose.

| Item | Priority | Status | Depends on | Epic |
|---|---|---|---|---|
| End-to-end alert flow | MVP REQUIRED | Partially implemented (G2) | Nothing | E1 |
| Explainable alerts | MVP REQUIRED | In the vessel panel only | E1 | E1, E5 |
| Evasion state machine | MVP REQUIRED | Planned; the four behaviours exist as score factors, not as states | State definitions (E2) | E2 |
| Weather triage | MVP REQUIRED | Planned | E1; a marine weather feed | E2 |
| SAR + AIS fusion on xView3 | MVP REQUIRED | Planned; no model | Data access, training, Q7, Q14 | E3 |
| Hotspot forecasts | MVP REQUIRED | Planned; no model | Data accounts, Q14 | E4 |
| Encounter graph | MVP REQUIRED | Planned; direct encounters only | Nothing | E5 |
| Vessel evidence screen (03) | MVP REQUIRED | Designed, not built | E1; E3 for the radar crop | E5 |
| API tests, end-to-end check, new video | MVP REQUIRED | Not started | Q1 | E6 |
| Bad AIS records rejected at ingest (G11) | MVP REQUIRED: one bad record takes the map down for every vessel and stops every later ingest (Audit rates it Critical) | Not started; story E6-S4 written | E6-S1 for its tests | E6 |
| Report with linked figures (screen 04) | Blocked on Q2 | Designed, not built | Q2 | |
| Protection on ingest routes | HELPFUL while everything runs locally (A2). Audit rates the gap High, so this becomes MVP REQUIRED if anything is deployed | Not started | Nothing | E6 |
| Scoring that holds for a few hundred vessels close together (G8) | HELPFUL; required if the demo or E3 puts more than about 100 vessels in one area | Not started | E3-S1 | E6 |
| Official protected-area boundaries (WDPA) | HELPFUL | Loader exists (`scripts/load_mpas.py`); sample outlines in use | Data download | E6 |
| CI | HELPFUL | Not started | Test set-up | E6 |
| Local LLM reports, spill simulator, offline build | FUTURE (finale) | Planned | | |
| Login and roles | FUTURE (Q5) | Planned | | |
| Radar heat overlay (EigenCAM), SHAP on hotspots | FUTURE | Planned | E3, E4; `DESIGN.md:53` | |
| Node orchestrator, C++ edge filter | FUTURE (Q9) | README stubs in `services/` | | |
| Chat assistant, route prediction, pollution detection, ocean health | UNNECESSARY for 10 Nov | See section 2 | Q10 | |

## 5. Epics

Six epics, each one outcome. Only E1 has full stories. E3 and E4 start with one fact-finding story each, because they have the longest lead time. Stories for E2 and E5 will be written when E1 is approved and the E3 and E4 findings are in.

| ID | Epic | Outcome | Priority | State of planning |
|---|---|---|---|---|
| E1 | Alert flow and triage | An officer can pick up an alert, work it, and find it again | MVP REQUIRED | Stories ready for approval (section 6) |
| E2 | Evasion states and weather triage | Each vessel has a named state with a reason, and weather explains or escalates alerts | MVP REQUIRED | Outline |
| E3 | Radar detections fused with AIS | A radar hull with no matching AIS becomes a dark-vessel alert | MVP REQUIRED | First story only |
| E4 | Hotspot forecasts | Cells are ranked by where fishing is likely to move, with a measured score | MVP REQUIRED | First story only |
| E5 | Vessel evidence and encounter graph | One screen shows how the case was built and who the vessel met | MVP REQUIRED | Outline |
| E6 | Submission readiness | The project runs from a clean checkout, is tested, and the video shows running software | MVP REQUIRED | Three stories now |

### E2 outline: evasion states and weather triage

- **Problem.** Storms make vessels slow down and loiter, which raises false alarms (README, "Alert fatigue"). Today the score cannot tell sheltering from evasion.
- **Outcome.** The four behaviours in `README.md:49` are tracked as states with a recorded reason for each change. A storm at the vessel's position downgrades the alert into a kept lane; a storm near a protected area escalates it (`README.md:50`).
- **Existing code.** The four behaviours are score factors (`MAX_POINTS` in `risk_engine.py`). `vessels.py:25-30` maps the score level to `flagged`, `watch` or `tracked`; that is not the state machine the README describes. The weather check is fixed at "not checked" (`risk_engine.py:360`).
- **Depends on.** E1 for the alert record and the weather lane. Open-Meteo Marine for weather.
- **Open before stories can be written.** The list of states and what moves a vessel between them. How long a state lasts once positions stop arriving: today a vessel that stays dark leaves the console 24 hours after its last position (G10). The wind and swell values that count as a storm. How "false alerts removed against real alerts wrongly downgraded" will be measured without labelled cases. Whether the factor weights need rebalancing once weather and radar add to the score; the headline case clears the threshold by 0.03 (Q11). G4 and G12 are settled here.

### E3 outline: radar detections fused with AIS

- **Problem.** About 75% of industrial fishing vessels are not publicly tracked (README), so AIS alone misses them.
- **Outcome.** A detector finds hulls in Sentinel-1 scenes, each hull is matched against AIS positions, and an unmatched hull raises an alert. Precision, recall and F1 on held-out xView3 scenes are reported (`README.md:81`).
- **Existing code.** A YOLOv8 pipeline for optical pollution images (`pollution_detector.py`, the `process_satellite_image` task) with no weights and placeholder georeferencing (`ingest.py:107`). Nothing for SAR.
- **Checked by Backend on the team machine.** The GPU is an RTX 3050 Laptop with 6 GB. The API image installs CPU-only PyTorch (`apps/api/Dockerfile:21`), so training needs its own environment. 124 GB of disk is free.
- **Not checked.** The xView3-SAR download size and licence, whether its labels are points or boxes, and whether any scene covers Indian waters (Q7). Backend recalls hundreds of GB, point labels with a vessel length, and European and West African waters. E3-S1 confirms or corrects all three.

**E3-S1 Find out whether xView3 detection fits in four weeks**

- **Owner:** AI (D8): registers for the data, writes the scripts and runs the training. **Priority:** MVP REQUIRED. **Status:** proposed.
- **User value:** the team learns by 26 Oct whether radar fusion can be real on 10 Nov, while there is still time to change the plan.
- **Scope:** data access, one training run on a subset, one measurement on the RTX 3050. **Not in scope:** fusion with AIS, any API or screen.
- **Acceptance criteria:**
  1. Access to xView3-SAR is confirmed, and the licence terms and download size are written down.
  2. A subset is chosen that fits the disk and the Kaggle or Colab limits, with the reason for the choice.
  3. One YOLOv8s training run finishes on that subset. Precision, recall and F1 on held-out scenes are reported with the training time and the hardware used. If the labels are points, the report says how a detection was matched to a label.
  4. Inference time and peak VRAM for one scene are measured on the RTX 3050.
  5. Q7 is answered: which region the demo's radar detections come from.
  6. A written recommendation: go, go with a named reduction, or move to the finale.
- **Required tests:** none; the output is measurements.
- **Evidence:** a model card and the training script under `ml/`, as `ml/README.md` plans. No weights or data committed.

### E4 outline: hotspot forecasts

- **Problem.** Processing every radar tile wastes compute (README, "Wasted compute").
- **Outcome.** Sea temperature and chlorophyll are forecast per grid cell, cells are ranked, and the two README metrics are reported (`README.md:82-83`). The map shows the top cells.
- **Existing code.** None.
- **Not checked.** Whether the team has Copernicus Marine and Global Fishing Watch accounts.

**E4-S1 Get the hotspot data and a baseline number**

- **Owner:** AI (D8), including the accounts. **Priority:** MVP REQUIRED. **Status:** proposed.
- **User value:** the team learns by 26 Oct whether the hotspot data can be had and what a naive forecast scores.
- **Scope:** accounts, one download, one baseline. **Not in scope:** the ranker, any API or map layer.
- **Acceptance criteria:**
  1. Accounts or tokens for Copernicus Marine and Global Fishing Watch exist and are kept out of the repo.
  2. Sea temperature, chlorophyll and fishing effort for a box around the Gulf of Mannar and Gulf of Kutch are downloaded for a stated period.
  3. A grid cell size is proposed with a reason.
  4. A baseline that repeats last month's value is scored with mean absolute error per cell, so later models have a number to beat.
  5. A written recommendation: go, go with a named reduction, or move to the finale.
- **Required tests:** none; the output is measurements.
- **Evidence:** the download and baseline scripts under `ml/`, with the baseline figure.

### E5 outline: vessel evidence and encounter graph

- **Problem.** The vessel panel says why a vessel was flagged, but "Open evidence" leads to a placeholder, and the officer cannot see who else is involved.
- **Outcome.** Screen 03 shows the track, speed, a timeline of how the score was built, and a graph of every vessel the flagged ship met: the Global Fishing Watch rule, then two hops back over 48 hours (`README.md:75`).
- **Existing code.** Direct encounters with the same rule (500 m, 2 kn, 2 h in `risk_engine.py`), returned as `encounters` by `/vessels/{mmsi}`. The mockup is `docs/design/screens/03-vessel-evidence.html`. `/vessels/:mmsi?` is a placeholder route.
- **Depends on.** E1 for the link from an alert. E3 for the radar crop; the screen can ship without the crop. A graph contract (C2) has to be written first.
- **Open before stories can be written.** Whether the 48-hour look-back for the graph changes the 24-hour scoring window (`vessels.py:55` allows up to 72).

### E6 outline: submission readiness

- **Problem.** "Complete project" has to be shown, not claimed (G7, G9).
- **Outcome.** From a clean checkout, the documented commands start the stack, load the demo, pass the tests, and the video is recorded from that running stack.
- **Later stories, not yet written.** Protection on ingest routes (G6); making ingest safe to replay (G13); making a position with no speed neutral in the loitering and encounter rules (G14, proposed by Backend); the clean-up in Q10; correcting `README.md:9` and `apps/web/src/pages/NotBuiltYet.jsx:10`; WDPA boundaries, which need multi-part areas handled first (the boundary column is `POLYGON`, `models/mpa.py:11`, and `zone_relation` reads `poly.exterior`, `risk_engine.py:129`; found by Audit, and it cannot happen on the seed); recording the video, within 4 hours of a fresh seed (G10).

**E6-S1 API tests run against a real database with one command** (Backend, MVP REQUIRED, proposed)

- **User value:** every backend story after this one can prove itself.
- **Context:** the only tests are pure functions in `tests/test_risk_engine.py`. The image holds no test dependencies (`apps/api/Dockerfile:21` installs only `requirements.txt`), so the command at `README.md:205` installs them into the running container each time. There is no pytest configuration and no database fixture.
- **Not in scope:** CI; tests for frozen features.
- **Acceptance criteria:**
  1. One documented command runs the API tests against a PostGIS database that is not the development database.
  2. Tests create their own data and leave none behind.
  3. The ten risk-engine tests still pass under the same command.
  4. A failing test makes the command exit with an error.
- **Required tests:** one test that loads the demo story and asserts `/vessels/` returns Sea Pearl II at or above the alert threshold. The headline case has a margin of 0.03 (G10), so a change to a weight or a seed timing that drops it must fail a test. One test for each C0 route that asserts the fields and values the console reads, so a backend change that drops or renames one fails before it reaches the console. Backend proposed this and has Frontend's list. `position` is on it, because the map stops on a vessel without one (`OceanMap.jsx:59`).

**E6-S2 `npm run build && npm test` passes in `apps/web`** (Frontend, MVP REQUIRED, implemented and verified by Audit on 13 Oct; uncommitted)

- **Context:** the Frontend session's uncommitted work adds Vitest, a `test` script and six test files under `apps/web/tests/`. The README names the command (`README.md:210-211`). On 13 Oct Audit ran `npm ci`, the build and the tests in a copy outside the repository, with no `node_modules` to start from, and all three passed (278 packages installed; 1,979 modules built; 6 files, 59 tests). Frontend had reported the same on its own clean copy, and planning saw the 59 tests pass in the working tree.
- **The lockfile:** before its clean run, Audit ran `npm ci` in the working tree. It failed on a file the running dev server held and removed `node_modules`, so Audit reinstalled with `npm install`, which wrote `apps/web/package-lock.json` at 14:09 UTC. Frontend kept no earlier copy, so it cannot compare the file byte for byte. Its evidence that the content did not change: the file differs from the last commit by the same 1,056 lines its session recorded before the install; `package.json` is untouched; and `npm install --package-lock-only` in a scratch copy left the file byte-identical. Frontend takes it as unchanged and restored nothing. `npm ls --all` exits 0, and Frontend restarted the dev server, because the install had deleted its dependency cache.
- **Acceptance criteria:** the command passes from `apps/web` on a clean install; the README "Tests" section names it.
- **Still needed:** the commit, which is the team's decision.

**E6-S3 End-to-end check on the running stack** (Audit, MVP REQUIRED, waits on Q1)

- **User value:** every "implemented but unverified" row in section 2 becomes verified or broken.
- **Context:** Frontend listed nine fixes to the map console from 13 Oct. Audit has verified all nine against the working tree by reading every changed file under `apps/web/src` and running the 59 tests. Three have no unit test (a double selection on map click, search results opening behind a card, and the timeline width). Audit verified those in the code (`OceanMap.jsx:170-173`, `MapPage.jsx:131`, `TrackTimeline.jsx:47`), and Frontend had seen them in a browser. Audit then ran all three in a browser with Playwright at about 14:00 UTC on 13 Oct, reading only, and each passed. One map click added one history entry, and one Back closed the panel. At 1280×800 the search result was on top of the "Needs attention" card. The timeline was 488, 384 and 704 px wide at 1024, 1280 and 1600 px, clear of the vessel panel each time. Audit notes that the timeline covers 12 hours while scoring covers 24. That matches the signed-off design (`docs/design/DESIGN.md:60`), so planning proposes no change. Audit's backend checks so far ran inside transactions that were rolled back (Q1). The criteria below are still to be met.
- **Acceptance criteria:**
  1. The stack starts with the README command, in a way that does not touch any existing database volume on the machine.
  2. The seed runs, and `/vessels/`, `/vessels/419007431` and `/map/zones` return the story.
  3. The console shows the story on the map with the vessel panel filled in.
  4. Each row in section 2 gets a new status with the observation that supports it.
- **Evidence:** commands, responses and screenshots.

**E6-S4 Bad AIS records are rejected at ingest** (Backend, MVP REQUIRED, proposed)

- **User value:** one malformed record from a feed cannot take the map down, lose the records sent with it or raise a score.
- **Context:** G11, reproduced by Audit. `AISRecord` takes every number as given, and the route builds a point from latitude and longitude unchecked (`ingest.py:17-35,54`). The request is checked as a whole before the route runs, so one record with a wrong type refuses its whole batch with 422 (Backend, checked without a database). The commit sits outside the per-record error handling (`ingest.py:95`), so a row the database refuses fails the whole request. The scoring window has no upper bound on time (`fleet.py:30`). The CSV loader writes rows itself. It drops positions outside the valid range (`scripts/ingest_ais.py:57-58`) and has no length or date check. It commits up to 1,000 rows at a time, outside its per-row error handling (lines 140-142 and 155-157), so one row the database refuses loses the rows committed with it (Backend's reading, not run). The E1-S2 evaluation will read the same rows, so a stored bad position would stop alerts as well (planning's reading of `fleet.py:55-64`, not run). The development database needs no clean-up: Backend counted 678 positions and none of the bad kinds at 13:49 UTC on 13 Oct.
- **Not in scope:** authentication on the route (G6); the satellite-image route; replayed batches (G13); judging positions that are valid but unlikely, which the position-jump factor already does.
- **Acceptance criteria:**
  1. Each record is checked on its own. It is **refused**, with nothing stored, when:
     - `mmsi`, `latitude`, `longitude` or `timestamp` is missing or cannot be read;
     - `mmsi` is not between 1 and 999999999;
     - latitude or longitude is not a finite number, or is outside -90 to 90 or -180 to 180;
     - its time is more than 5 minutes after the server's clock. Exactly 5 minutes is accepted. Times are compared in UTC, and a time with no offset is read as UTC.
  2. A record that passes criterion 1 is **stored with the field left empty** when any other value is unusable: a value of the wrong type, such as a speed of "abc"; a number that is not finite; a speed below 0 or above 102.2 kn; a course below 0, or 360 or above; a heading outside 0 to 359; a negative length, width or draft; a `nav_status` or `cargo` too large for its column; text longer than its column (`models/vessel.py:122-140`).
  3. One refused record does not affect the rest of its batch. The response keeps `status`, `inserted`, `rescored` and `total`, and gains two keys, both always present. `rejected` lists each refused record: its place in the batch, its MMSI where one could be read, and the reason. `blanked` lists each field emptied under criterion 2: the record's place, its MMSI, the field and the reason. `inserted` plus the number of `rejected` entries equals `total`. A batch in which every record is refused answers 200 with `inserted: 0`. 422 is kept for a body that is not `{"records": [...]}`.
  4. The route never answers 500 for bad input.
  5. After a batch holding one of each kind of bad record, `/vessels/` and `/vessels/{mmsi}` answer 200, and a later valid ingest succeeds.
  6. The CSV loader applies the same rules before a row joins a batch.
  7. Scoring ignores positions later than its clock (`fleet.load_pings`), so a future-dated row that arrived another way does not stay in the window.
- **Why criterion 2 keeps the position.** A refused record is a position missing from the track, and silence is what the AIS-gap factor counts (`risk_engine.py:35-36`). A transponder that sends one bad value with every report would never appear on the map. The route already treats a heading of 511 this way (`ingest.py:62-65`). The ranges are those of the AIS position report, in which 102.3 kn, 360 degrees and heading 511 mean "not available" (ITU-R M.1371, as listed by the US Coast Guard Navigation Center), so those values need no rule of their own. Backend and Audit had agreed to refuse these records, and to keep the position only for those three values. Planning proposed criterion 2, and Backend has agreed it after measuring both rules in memory: for a vessel reporting every 150 minutes, one refused record scored 0.26 for an AIS gap and two in a row scored 0.31, while the same records stored with an empty speed scored 0.00. Audit agrees as well.
- **Known limit.** An empty speed ends a loitering or encounter run, so emptying a speed can remove points a vessel had earned (G14). No other emptied field reaches a score: scoring reads only position, time, speed, name and vessel type (Backend, `fleet.py:28,37-38`). The fix is in the engine and is a later story.
- **Required tests:** on the E6-S1 set-up, a batch with one valid record and one of each refused kind stores only the valid one, and `/vessels/` answers 200 afterwards. One test for each rule in criteria 1 and 2. NaN and infinity are sent both bare and as the strings "NaN" and "Infinity", which the request model turns into numbers (Backend). The time rule is tested on a fixed clock, just under 5 minutes, at exactly 5 minutes and just over. Backend uses Audit's seven request bodies: five are refused, and the two with over-long text are stored with the field empty. Audit adds an eighth: a record with a good position and a bad speed, course and length is stored with those three fields empty.
- **Depends on:** E6-S1 for the tests. No open decision.
- **Done when:** the criteria pass, and none of Audit's reproductions (NaN and infinite values, out-of-range values, over-long fields, an MMSI too large for its column, future dates) takes the map down, loses a batch or leaves a bad value stored.

## 6. Epic E1: alert flow and triage

- **User problem.** An officer can see a flagged vessel on the map, but there is no alert to pick up, work on and come back to. The alert list is rebuilt on every request with new IDs, misses any vessel that has been silent for more than an hour, and records nothing the officer does (G2, G3).
- **Outcome, measured by:**
  1. After the demo seed, Sea Pearl II has exactly one alert in New, and its score and top reason equal those from `/vessels/419007431`.
  2. That alert keeps its ID across repeated requests, rescoring and an API restart.
  3. An officer moves it to In review on the Alerts screen; after a reload it is still there, with a history entry.
  4. No alert is ever deleted.
  5. Every alert says when it was last scored (`scored_at`), and its score equals what `/vessels` gave at that time. While the vessel still meets the alert rule, that time is never older than the E1-S2 interval. Alert counts on every screen come from the alerts API.
- **Value.** This is "end-to-end alert flow" in `README.md:97`. The weather lane (E2), radar alerts (E3), the evidence link (E5) and report sign-off (finale) all attach to the alert record.
- **In scope.** A stored alert with a lifecycle and history; alerts raised from the risk engine; alerts kept current without new AIS; the alerts API; the Alerts screen (02); the rail badge.
- **Not in scope.** Weather downgrade, restore and escalation (E2). Radar-only alerts (E3). Reports, and anything that moves an alert to Awaiting sign-off or Sent (finale, Q2). Login (Q5). Search and drag-and-drop on the Alerts screen.
- **Depends on.** Nothing upstream. E6-S1 for its tests.
- **Existing code.** `risk_engine.py` and `fleet.py` (KEEP). `alerts.py` and `alert_generator.py` (REBUILD, Q10). The unused `rescore_fleet` task (`celery_app.py:157`). `Shell.jsx` counts vessels at level `high` for the badge. `AttentionCard.jsx` already links to `/alerts`. `/alerts` renders `NotBuiltYet` (`App.jsx`). Mockup: `docs/design/screens/02-alert-triage.html`.
- **Risks and open questions.** Q3, Q4, Q5, Q11. G10. G8 if the fleet grows. G11: until E6-S4 lands, one bad stored position would stop every evaluation.
- **Done when.** All five stories meet the Definition of Done, E1-S5 passes on the running stack, and the README API table and status line are correct.

### Contract C0: frozen

The console consumes `GET /api/v1/vessels/`, `GET /api/v1/vessels/{mmsi}` and `GET /api/v1/map/zones` (`apps/web/src/lib/api.js`). Their response shapes do not change without an entry in section 9. Adding a field is allowed.

### Contract C1: alerts (draft 3)

Planning proposed this so both sides can start, and Backend owns the final shape. Backend and Frontend agreed draft 2 on 13 Oct, with three later additions (`last_seen`, the wording of `top_reason`, and 422 on the list route). Draft 3 is draft 2 with the two points Backend then decided (D6): `evaluated_at` is added to the list response, and the `zone` filter is left out of E1. Frontend accepts both. Agreeing the contract is not approval to build: the E1 stories still wait on the team. Field names reuse those in `vessels.py:33-50`. `name`, `score` and `zone` show what the seeded stack returned on 13 Oct; the other values are placeholders.

```
GET /api/v1/alerts/?status=<status>
200 {
  "generated_at": "...Z",       the time of this response
  "evaluated_at": "...Z",       the clock of the last completed evaluation run; null before the first run
  "threshold": 0.6,
  "counts": {"new": 1, "weather": 0, "in_review": 0, "awaiting_signoff": 0, "sent": 0, "closed": 0},
  "alerts": [ALERT, ...]
}
422 unknown status

ALERT {
  "id": "...",                  opaque string, stable for the life of the alert
  "status": "new",              new | weather | in_review | awaiting_signoff | sent | closed
  "mmsi": 419007431,
  "name": "SEA PEARL II",       same value as "name" in /vessels (AIS text, upper case)
  "headline": "...",            same value as "headline" in /vessels
  "score": 0.63,
  "top_reason": FACTOR,         the first entry of "factors" in /vessels/{mmsi}, which "headline" also reads
  "zone": {"name": "Gulf of Mannar Marine National Park", "relation": "buffer", "distance_km": 7.2} or null,
  "position": {"lat": 0.0, "lon": 0.0},
  "last_seen": "...Z",          same meaning as "last_seen" in /vessels: the time of the vessel's newest position at scored_at
  "raised_at": "...Z",
  "scored_at": "...Z",          the last evaluation in which the vessel met the alert rule
  "updated_at": "...Z",         the last status change
  "assignee": null              officer name while the alert is in review
}

FACTOR {"key": "ais_gap", "label": "...", "detail": "...", "points": 0.31, "max_points": 0.31, "evidence": ...}
                                the same object as an entry of "factors" in /vessels/{mmsi}

GET /api/v1/alerts/{id}
200 ALERT plus "history": [{"t": "...Z", "from": null, "to": "new", "actor": "system", "note": "..."}]
404 unknown id

POST /api/v1/alerts/{id}/status      body {"status": "in_review", "note": "..."}
                                     "note" is optional, 500 characters at most
200 ALERT plus "history"
404 unknown id    409 move not allowed    422 unknown status, or note too long
```

- **Values.** `score`, `top_reason`, `headline`, `zone`, `position` and `last_seen` come from the evaluation at `scored_at`. While the vessel still meets the alert rule, `scored_at` is never older than the E1-S2 interval. A closed alert, and an alert that stays open after its evidence has aged out (Q3), keep the values from the last evaluation that met the rule.
- **Current or kept.** Each evaluation run takes one clock value. It writes that value as `scored_at` on every alert that met the rule in that run, and as `evaluated_at`. So an alert's values are current when its `scored_at` equals `evaluated_at`, and kept from an earlier run when it is earlier. The console compares the two as times, and treats only "earlier" as kept. `evaluated_at` is on the list response only: E1-S4 does not call `GET /alerts/{id}`, and the console needs no flag on each alert (Frontend).
- **Scoring stopped.** The console treats scoring as stopped when `evaluated_at` is more than 3 minutes before `generated_at`, and as not yet run when it is null (E1-S4 criterion 10). Three minutes is three missed runs at the 60-second interval of E1-S2; Backend suggested it, and it changes if the interval does. Both times are the server's, so the browser's clock does not matter. The run time is stored in the database, so a restart does not clear it. The seed and the ingest route count as runs (E1-S2 criterion 6), so it is null only on a database that has never been seeded or scored.
- **List.** Closed alerts are left out unless `status=closed`. The order is score, highest first, then `raised_at`, newest first. There is no `zone` filter in E1: the console loads every alert and filters by zone in the browser. `counts` cover every alert, whatever `status` is.
- **Moves.** A person may move `new` to `in_review`, which sets `assignee` to the name from Q5, and `in_review` back to `new`, which clears it. A move to the status the alert already has, any move on a closed alert, and any move into `weather`, `awaiting_signoff`, `sent` or `closed` returns 409. Only the system sets `closed` (Q3). `weather`, `awaiting_signoff` and `sent` are reserved for E2 and the finale.
- **One open alert per vessel**, enforced by the database.
- **No authentication** on the status route for 10 Nov (Q5, G6).
### Definition of Done (every story)

1. Each acceptance criterion is met, and the evidence named in section 7 is in the pull request.
2. The required tests are in the repo and pass. Frontend changes pass `npm run build && npm test` in `apps/web`. Backend changes pass the E6-S1 command.
3. No change to C0 or an agreed C1 without an entry in section 9.
4. Anything the change makes wrong in the README or `NotBuiltYet.jsx` is corrected in the same change.
5. The Audit session has checked it. The author does not mark their own story done.
6. No secrets, `.env` files, datasets or model weights are committed.

### Stories

All five are MVP REQUIRED and **proposed**: not started, awaiting approval.

#### E1-S1 Alerts are stored and keep their identity (Backend)

- **User value:** the officer sees the same alert every time, including for a vessel that has gone silent.
- **Context:** `GET /alerts/` rebuilds its list on each request from `AlertGenerator.check_mpa_violations()` (`alerts.py:36-37`), only for vessels that pinged in the last hour (`alert_generator.py:106`), using stored scores (`alert_generator.py:116`). This story adds a stored alert, raised and updated from the same explanation `/vessels` returns (`fleet.score_fleet`, `fleet.py:55`).
- **Not in scope:** routes (S3), the timer (S2), weather status (E2), radar-only alerts (E3).
- **Acceptance criteria:**
  1. When a vessel's explanation meets the alert rule (Q3; until decided, score at or above `ALERT_THRESHOLD`), one alert is stored with status `new`, the time, the score and the top factor.
  2. Evaluating again while the vessel still meets the rule updates the score, top reason and `scored_at` on that alert. It does not create a second alert or change the ID.
  3. A vessel whose last ping is more than an hour old, but inside the scoring window, still gets its alert.
  4. An alert in `new` becomes `closed`, with a history entry, when the vessel has a position newer than the newest one the alert was last scored on (`last_seen`) and scores below the rule. The comparison is between position times; `vessel_tracks` records no arrival time (`models/vessel.py:119-140`). It does not close because evidence aged out of the scoring window, or because the vessel has no position left in the window; it stays open with the values from the last evaluation that met the rule (Q3, G10). Until Q3 is decided, the system leaves an alert in `in_review` alone. No alert row is ever deleted.
  5. Every status change, by the system or a person, adds a history entry: time, old status, new status, actor, note.
  6. The alert rule is defined in one place, so the Q3 decision changes one value.
  7. The schema change is an Alembic migration that upgrades from `002` and downgrades cleanly. It also adds a one-row store for the time of the last completed evaluation run, which E1-S2 writes and E1-S3 returns as `evaluated_at`.
  8. A vessel never has two open alerts, including when two evaluations run at the same moment.
- **Depends on:** E6-S1 for tests. Q3 has a working default, so it does not block a start.
- **Required tests:** unit tests for raise, update, close after the vessel reports again, no close when the evidence ages out with no new position, and a second alert after a close; a database test on the demo story; a test that two evaluations at once leave one open alert.

#### E1-S2 Alerts and scores stay current (Backend)

- **User value:** the Alerts screen matches the map even when no AIS arrives, which is exactly when a vessel is going dark.
- **Context:** stored scores refresh only inside `POST /ingest/ais` (`ingest.py:42`, through `fleet.rescore_all`, `fleet.py:93`) and when the seed runs (`seed_demo.py:127`). An AIS gap grows while nothing arrives, so alerts must also be evaluated on a timer. `rescore_fleet` exists (`celery_app.py:157`) but nothing calls it, Compose starts no scheduler, and the worker container was not running on 13 Oct. Backend saw two ways to run the timer: inside the API process, which needs no new container, or Celery beat, which needs the worker and a beat service. The choice was Backend's, and it chose the first (D7). A background thread started with the API runs one evaluation at start-up and then one every 60 seconds, and a database lock lets only one evaluation run at a time. No Celery, worker container or Compose change is needed. Nothing evaluates while the API process is down. `main.py` has no start-up hook today, so this adds the first.
- **Not in scope:** speeding up `score_fleet` beyond what the demo data needs (G8).
- **Acceptance criteria:**
  1. With the stack running and no ingest calls, a vessel that meets the alert rule through passing time alone gets its alert within a stated interval. Backend proposes 60 seconds; one evaluation of the seed takes about 0.1 s.
  2. When `POST /ingest/ais` returns, alerts reflect the new positions, because the route runs the same evaluation (Backend).
  3. The score on an alert equals the score `GET /vessels/{mmsi}` gave at the alert's `scored_at`. While the vessel still meets the rule, `scored_at` is no older than the interval.
  4. `/analytics/statistics` (`analytics.py:61-88`) either agrees with `/vessels` or is put forward for removal through section 9.
  5. The schedule starts with the documented `docker compose` command, with no manual step. Backend intends one run at start-up, then one every 60 seconds.
  6. Each run takes one clock value and writes it as `scored_at` on every alert that met the rule in that run, and as the time of the last completed run (`evaluated_at` in C1). The timer, the ingest route and the seed call one evaluation function, so each of them is a run. They share one database lock: the timer skips a tick while another evaluation runs, and the route and the seed wait for it.
- **Depends on:** E1-S1; E6-S4 criterion 7.
- **Required tests:** a database test with a fixed clock (`score_fleet` already accepts `now`) showing an alert raised by time alone; a test that statistics and vessels agree. The fixed-clock test relies on E6-S4 criterion 7, which makes scoring leave out positions later than its clock (`fleet.py:25-40`; raised by Audit).

#### E1-S3 Alerts API (Backend)

- **User value:** the console can list alerts, open one and record what the officer did.
- **Context:** the current response model (`alerts.py:12-20`) has a random ID and no status. No frontend code calls `/alerts` (`apps/web/src/lib/api.js`), so replacing the shape breaks nothing in this repo. The status route is the first route that records what a person did, and it has no authentication on 10 Nov if Q5 is answered as recommended.
- **Not in scope:** moves into `weather`, `awaiting_signoff` or `sent`; login.
- **Acceptance criteria:**
  1. The three routes in C1 return the agreed shapes, including `counts` and `evaluated_at`, in the agreed order.
  2. The `status` filter works. `counts` cover every alert, whatever `status` is. Closed alerts appear only with `status=closed`.
  3. Allowed moves succeed, set or clear `assignee`, and add a history entry. Each 409, 422 and 404 case in C1 returns that code.
  4. Times are UTC with a `Z`, as in `vessels.py:14-22`.
  5. The actor on a person's move follows the Q5 decision.
  6. The README API table describes the new routes.
- **Depends on:** E1-S1; C1 agreed.
- **Required tests:** an API test for each route, the filter and each error.

#### E1-S4 Alerts screen (Frontend)

- **User value:** the officer sees every open alert in lanes with its top reason, and takes one into review.
- **Context:** `/alerts` renders `NotBuiltYet`. The signed-off design is `docs/design/screens/02-alert-triage.html`, with tokens in `samudra.css`. `Shell.jsx` shows a badge counting vessels at level `high`. Frontend's approach: one unfiltered `GET /alerts/`, polled in `Shell.jsx` because the rail is on every page, feeds the badge, the zone chips and the lanes; the screen filters by zone in the browser.
- **Scope:** the lanes Q4 settles; the header line with counts; zone chips; a card with headline, top-reason detail, score and "Top reason: label +points"; the assignee on In review cards; actions to take an alert into review and put it back. Clicking a card opens the vessel on the map at `/map?vessel=<mmsi>`, the parameter `MapPage.jsx` already reads, until screen 03 exists.
- **Not in scope:** search; Restore and Escalated (E2); Review report and Fix source (finale); radar-only cards (E3); drag-and-drop.
- **Acceptance criteria:**
  1. With the demo seed loaded, Sea Pearl II is in New. Its score, and its top reason's key and points, equal those in the vessel panel. The wording is not compared: the alert's text is from `scored_at`, and the panel's is live ("6.9 h so far" keeps growing).
  2. Taking it into review moves the card, shows who took it, and survives a reload.
  3. With All zones chosen, the header and lane counts equal `counts` from the API. With a zone chosen, they equal the cards shown.
  4. Choosing a zone chip shows only that zone's alerts. All zones shows everything, including alerts with no zone. The chips are the zones that have open alerts, named in full as the API gives them; the mockup's short names are not in the API.
  5. If the API cannot be reached, the screen keeps the last good data and shows that it is not live, as the map does (`usePolling.js`; `AttentionCard.jsx`; the status pill at `MapPage.jsx:154`).
  6. State is never shown by colour alone (`DESIGN.md`, section 2).
  7. An empty lane shows a short message, not a blank column.
  8. The rail badge shows the number of alerts in New across all zones, on every page, from the alerts API. It replaces the count of vessels at level `high`. Its accessible name, today "Alerts, N high risk" (`Shell.jsx:21`), is reworded to match.
  9. If Q3 is answered as recommended, an alert can outlive its vessel's place in `/vessels` (G10). Its card still shows, with the date and time the vessel was last seen (`last_seen`), and opening it tells the officer the vessel has no recent positions. `GET /vessels/{mmsi}` returns 404 for such a vessel (`vessels.py:76`).
  10. The Alerts screen says when what it shows is not current (C1). There are three cases:
      - A card whose `scored_at` is earlier than `evaluated_at` shows that its values are from that earlier time. Frontend asked for this.
      - When `evaluated_at` is more than 3 minutes before `generated_at`, scoring has stopped. The screen gets the treatment of criterion 5 with its own sentence, which says that scoring has stopped and when the last evaluation was. It does not say the API cannot be reached, because the API is answering.
      - When `evaluated_at` is null, the screen says scoring has not run yet.

      Times are in IST, with the date when it is not today, as in criterion 9. When the API cannot be reached, only the criterion 5 state shows, because nothing newer is known. The rail badge keeps its count with no mark, and the map is not affected, because `/vessels` scores on each request. The second and third cases are planning's answer to Frontend's question, with the limit Backend suggested: this is the first screen that depends on a background timer, and a timer can stop while the API still answers.
- **Depends on:** C1 agreed (work can start against a fixture straight away); E1-S3 for live data; Q3 for criterion 9; Q4; Q5.
- **Required tests:** component tests under `apps/web/tests/`: lanes from a fixture, a status change that calls the API and moves the card, the not-live state, the badge count, a card whose vessel returns 404, a card with kept values, the scoring-stopped state, the not-yet-run state. The scoring-stopped and cannot-reach states are told apart by their text.

#### E1-S5 The demo story produces its alert, checked end to end (Backend for the seed, Audit for the check)

- **User value:** the video can be recorded from a clean start with one seed command.
- **Context:** `scripts/seed_demo.py` clears and reloads the story vessels, loads the sample protected areas and rescores (lines 112-127). Timestamps are relative to the moment it runs, so the story fades as the 24-hour window moves on; the README says to re-run it (`README.md:161`). Backend measured the fade: the headline score holds for 15 hours, and the vessel leaves `/vessels` after 17.9 (G10). The seed's scoring is a run (E1-S2 criterion 6), so the alert exists as soon as the seed command ends, even with the API stopped. The seed rewrites the positions of its own 14 vessels and knows nothing about alerts today (`seed_demo.py:113`), so criterion 2 is a change to the seed. Backend's plan for it: the seed holds the evaluation lock from before it replaces the positions until its own evaluation ends, so a timer run cannot score a half-replaced fleet. Each second seed adds closed alerts, so `counts.closed` grows with every seed.
- **Not in scope:** new story vessels; scores chosen to match the mockups (Q11).
- **Acceptance criteria:**
  1. After the seed command alone, Sea Pearl II has one alert in New. Every other story vessel has an alert if and only if `/vessels` shows it at alert level.
  2. Running the seed again closes the open alerts of the vessels it replaces, each with a history entry whose actor is `seed`, before new ones are raised. Afterwards there is exactly one open alert per flagged vessel, and no alert row has been deleted.
  3. Audit runs seed, list, take into review, restart the API, list again on the Docker stack and records what it saw.
  4. Audit confirms outcomes 1 to 5 of the epic, and that its findings on today's alerts route (G2) no longer reproduce.
- **Depends on:** E1-S1 to S4; Q1.
- **Required tests:** the database test from E1-S1 covers criterion 1; criteria 3 and 4 are Audit's record.

## 7. Dependencies and parallel work

| Story | Must happen first | Can Frontend and Backend work apart? | Contract | Conflicts | Evidence for done |
|---|---|---|---|---|---|
| E6-S1 | Nothing | Yes | None | None | Command output, including a deliberate failure |
| E6-S2 | Nothing | Yes | None | Frontend's uncommitted work in `apps/web` | Command output on a clean install |
| E6-S3 | Q1 | Yes | C0 | Uses ports 5432, 6379, 8000 and 5173. The other Postgres container on the team machine listens on 55532, so there is no clash | Commands, responses, screenshots |
| E6-S4 | E6-S1; before E1-S2 | Yes | None; the ingest response gains `rejected` and `blanked` | `ingest.py`, `scripts/ingest_ais.py`, `services/fleet.py`; Backend only | Test output; Audit's reproductions no longer succeed |
| E1-S1 | E6-S1 | Yes | Status values in C1 | Adds a migration; Backend only | Test output; one alert per flagged vessel after the seed |
| E1-S2 | E1-S1, E6-S4 | Yes | None | `app/main.py` and one new module under `app/services/` (D7); Backend only | Test output; an alert appearing with no ingest call |
| E1-S3 | E1-S1, C1 agreed | Yes, once C1 is agreed | C1 | Replaces `alerts.py`; `README.md` API table | API test output |
| E1-S4 | C1 agreed | Yes, against a fixture; live data needs E1-S3 | C1 | `App.jsx`, `Shell.jsx` | Test output; screenshot against the seeded stack |
| E1-S5 | E1-S1 to S4, Q1 | No, this is the joint check | C0, C1 | `scripts/seed_demo.py` | Audit's record |
| E3-S1, E4-S1 | Nothing; Q8 is answered by D8 | Yes; the AI part touches neither `apps/api` nor `apps/web` | None | None | Model card or baseline figure under `ml/` |

**Who owns shared files**

| Path | Owner |
|---|---|
| `apps/api/**`, `infra/docker-compose.yml` | Backend |
| `infra/.env.example` | Backend, except the block headed "Frontend", which is Frontend's |
| `apps/web/**` | Frontend |
| `ml/**` | AI (D8) |
| `docs/planning/PLAN.md` | Planning; other sessions send findings instead of editing |
| `README.md` | Whoever's change makes a line wrong corrects that line |
| `docs/design/**` | Signed off on 17 Sep 2026; changes need a team decision |

`docs/design/screens/00-landing.html` has an uncommitted change that did not come from the planning session. Its owner should commit or discard it.

On 13 Oct Frontend removed three unused `VITE_MAP_*` lines and their comment from `infra/.env.example`, by agreement with Backend. Nothing under `apps/web` or in the Compose file read them (planning's search). The change is uncommitted.

A check that installs or builds runs in a copy outside the working tree. On 13 Oct an install run by Audit in `apps/web` removed `node_modules` under Frontend's running dev server, and the reinstall wrote the lockfile (E6-S2).

No session restores a modified file from git (`git checkout` or `git restore` on a path). Every file that `git status` lists as modified holds uncommitted work, and the command would discard it. For `apps/web/package-lock.json` it would bring back the committed lockfile, which lacks the four test dependencies.

## 8. Proposed sequence

A proposal for the team, not a commitment.

| By | What should be true |
|---|---|
| Mon 19 Oct | Q1 to Q8 answered. C1 agreed. E6-S1, E6-S2 and E6-S4 done. E1-S1 in review. Data access for E3 and E4 confirmed or refused. |
| Mon 26 Oct | E1 done and checked. E3-S1 and E4-S1 report. **Go or no-go on E3 and E4.** Stories for E2 and E5 approved. |
| Mon 2 Nov | E2 and E5 done. E3 and E4 integrated, or a scope change recorded in section 9. |
| Thu 5 Nov | No new features after this day. |
| Fri 6 to Mon 9 Nov | Audit pass on a clean checkout, README corrected, video recorded from the running stack within 4 hours of a fresh seed (G10). |
| Tue 10 Nov | Submit. |

**Order of protection, if time runs short.** E1, then E2, then E5, then E3, then E4. The first three need no training and build on code that has tests. E3 and E4 carry the data and training risk (G1). If the 26 Oct check fails for either, planning brings the options to the team in writing. Nothing is cut quietly.

## 9. Decision log

| ID | Date | Decision | Source |
|---|---|---|---|
| D0 | 17 Sep 2026 | Design v2 is signed off | `docs/design/DESIGN.md:3` |
| D1 | 13 Oct 2026 | The 10 Nov submission is a demo video and a complete project | Team |
| D2 | 13 Oct 2026 | Recorded fact: no model training has been done | Team |
| D3 | 13 Oct 2026 | Training may use the team's RTX 3050, Kaggle and Colab | Team |
| D4 | 13 Oct 2026 | The leaked Gemini and Supabase keys have been rotated; `README.md:233` can say so | Team |
| D5 | 13 Oct 2026 | Planning lives in this one file | Team |
| D6 | 13 Oct 2026 | C1 changes after it was agreed: `evaluated_at` is added to the list response, and the `zone` filter is left out of E1 | Backend, which owns C1; accepted by Frontend. Agreed between sessions, not a team decision |
| D7 | 13 Oct 2026 | The E1-S2 timer runs inside the API process: one evaluation at start-up, then one every 60 seconds, one at a time under a database lock. No Celery, worker container or Compose change | Backend, whose choice it was (E1-S2). Not a team decision |
| D8 | 13 Oct 2026 | The plan is divided into three parts, Frontend, Backend and AI, so that three team members can work at the same time (section 12). The AI part owns `ml/**`, E3-S1 and E4-S1 | Team. That each part has one owner, and that the AI owner holds the data accounts, is planning's reading |

## 10. Decisions needed and assumptions

**Decisions needed.** Each has a recommendation so the team can answer with a yes or a correction.

| ID | Question | Recommendation | Blocks |
|---|---|---|---|
| Q1 | Overtaken in part. On 13 Oct the Frontend session started the existing `samudrasense` containers on their existing volume and ran the demo seed. Backend and Audit have read from that stack. Audit installed pytest into the running backend container at about 12:55 UTC, with the README's test command (`README.md:205-206`), to run the ten existing unit tests. That changed the container's installed packages and is lost when the container is recreated; it changed neither the image nor any project file. Audit's own reproductions ran in that container against that database, each inside a transaction that was rolled back, and the row count was 678 before and after. At 13:40 UTC planning saw `/vessels/` answer 200 with 14 vessels, as before. Is that acceptable, and may Audit run the full end-to-end check there, including ingest and status changes? | Yes to both. Test writes go to a separate Compose project or a test database, so the demo data stays clean | E6-S3, E1-S5, the remaining "unverified" rows |
| Q2 | Is the report with linked figures in the 10 Nov scope? `DESIGN.md:53` says yes; `README.md:98` puts reports at the finale. | Finale. Correct `DESIGN.md:53`. | Screen 04, Q4 |
| Q3 | What raises an alert, and what closes one? The first draft's rule (close when the score falls below the threshold) would close Sea Pearl II's alert 15.5 hours after seeding, about 21.7 hours after its last position and while it is still dark, because the encounter leaves the 24-hour window (G10). | Raised when the score reaches `ALERT_THRESHOLD` (0.60), the value "what would clear it" already uses. Closed by the system only when the vessel has a position newer than the one the alert was last scored on and scores below the threshold. Not closed because evidence aged out or the vessel stayed silent; the alert then keeps its last qualifying score and the time of it. The system does not close an alert an officer has taken into review; the officer puts it back to New first. A crossing after a close is a new alert. No manual dismissal for 10 Nov. What this means in practice is listed under this table. | E1-S1 criterion 4, E1-S4 criterion 9 (working default in place) |
| Q4 | Which lanes does the Alerts screen show on 10 Nov? The design has five; two need reports. | Show New, Explained by weather and In review. Add Awaiting sign-off and Sent with reports. This changes a signed-off design, so it needs a yes. | E1-S4 |
| Q5 | Is login needed for 10 Nov? | No. One officer name set in configuration is recorded as the actor. Login at the finale. This means anyone who can reach the API can change an alert's status, as with every other route today (G6); acceptable while the project runs locally (A2). | E1-S3, E1-S4 |
| Q6 | Is assumption A1 the right reading of "complete project"? | Yes | Everything |
| Q7 | xView3 may not cover Indian waters (not checked). Where do the demo's radar detections come from? | Decide after E3-S1: score the model on xView3, and show it on one Sentinel-1 scene of the Gulf of Mannar if the story stays there | E3 after its first story |
| Q8 | Answered by D8: the owner of the AI part runs the training. Planning reads that as including the registrations for xView3-SAR, Copernicus Marine and Global Fishing Watch. Is that right, and does that person have time on the machine with the RTX 3050? | Yes to both. If someone else holds an account or the GPU, say who | Nothing, unless the reading is wrong |
| Q9 | Are the Node orchestrator and C++ edge filter needed for 10 Nov? | No. Nothing in the 10 Nov scope needs them: no background job is dispatched today, and the one timer runs inside the API process (D7). Decide again for the finale. | Nothing now |
| Q10 | Approve the proposals in section 2? | FREEZE chat, route prediction, pollution detection and ocean health as they are. DELETE `agent_lightning.py`, `demo_data.py`, `scripts/ingest_sentinel.py` and `apps/api/docs/MIA_V3_GUIDE.md` (it describes an API that `chatbot.py` does not have). Replace `alert_generator.py` through E1. SIMPLIFY `model_registry.py` later. | E1-S3, clean-up |
| Q11 | The headline case scores 0.63, which is 0.03 above the threshold; the mockups show 0.87. It also fades 15 hours after seeding (G10). Change the seed or the weights so the story is stronger, or leave them? | Leave both for E1. A test guards the 0.63 (E6-S1), and the video is recorded within 4 hours of a fresh seed. Look at the weights again in E2, when weather and radar join the score. | Nothing now; the video |
| Q12 | At about 1024 px wide, the selected vessel sits under the detail card on the map (Frontend, seen in a browser). Only about 128 px of map is open between the two cards, so moving the map cannot fix it. The design states no minimum width. Options: (a) state 1280 px as the minimum and record at that width or wider, with no code; (b) below 1280 px, collapse "Needs attention" to its header while a vessel is selected, which changes the signed-off layout at small widths and has not been prototyped. | (a) for 10 Nov. | Nothing now |
| Q13 | Audit found the Gemini key, the Supabase keys and the Supabase database password in this repository's history, at commits b903704 and 84e88ac. Planning confirmed the database line in those commits and that the repository is public; nobody has tested any value. The example files in the working tree hold placeholders only. D4 records that the Gemini and Supabase keys were rotated. Was the database password reset as well? | Reset it in Supabase, or confirm that project is deleted. Rewriting the history is optional once every value is dead. | The security note at `README.md:233` |
| Q14 | Where does the AI part end and the Backend part begin? Three lines are not drawn yet. (a) Who matches radar hulls against AIS positions and raises the alert. (b) Whether a model runs inside the API on 10 Nov. (c) Who builds the evasion state machine and the weather rules; `README.md:123` lists the state machine under AI / ML, and the code it changes is `risk_engine.py`. | (a) Backend: matching needs the AIS positions in the database and the alert record from E1. (b) No: the AI part runs its models itself and hands over result files in a written format (C3 for detections, C4 for hotspot cells), and Backend loads them. The API image has CPU-only PyTorch and no weights. (c) Backend, because both are rules with no training. | The E3 and E4 stories after the first two; the E2 stories. Not E3-S1 or E4-S1 |

**What the Q3 recommendation means in practice.** These follow from the rule; they are not defects.

- A vessel that never reports again keeps its alert open.
- A vessel that stays dark for more than 24 hours and then reports again has its alert closed at the next evaluation. Its positions from before the gap are outside the 24-hour window, so the engine no longer sees the gap. Backend read this from the code and has not run it. If a returning dark vessel should stay flagged, that is a rule for E2 to add.
- When an officer puts an alert back to New and the vessel has since reported and scores below the threshold, the system closes it at the next evaluation, so the card leaves the screen within one interval.
- The demo seed closes the open alerts of the vessels it replaces, including alerts in review (E1-S5). That is the only case where something other than the officer ends a review.
- Open alerts only accumulate, and C1 has no paging. That is fine at demo size.

**Assumptions.** Each one is planning's reading, not a team decision.

| ID | Assumption |
|---|---|
| A1 | "Complete project" means the six items in `README.md:97` run as software on 10 Nov, and the video is recorded from that software. The finale row (`README.md:98`) stays at the finale. |
| A2 | The submission runs locally on Docker Compose with seeded data. Nothing is deployed publicly. |
| A3 | The Sea Pearl II story in the Gulf of Mannar stays the demo case (`DESIGN.md:66`). |
| A4 | Online services are acceptable on 10 Nov (the Esri basemap, Open-Meteo). Offline is a finale goal. |

## 11. Existing documents

| Document | Keep or correct |
|---|---|
| `README.md` | Keep as the product description and roadmap. Correct the status line (line 9) and the security note (line 233) once E1 lands. |
| `docs/design/DESIGN.md` | Keep. Line 53 conflicts with the README (Q2). Line 9 points to `SamudraSense_deck/styles.css`, which is not in the repo. |
| `docs/design/screens/02` to `05` | Keep as the screen specifications. |
| `apps/web/src/pages/NotBuiltYet.jsx:10` | Correct after Q2: it says every unbuilt screen is planned for 10 Nov, including reports and spills. |
| `apps/api/docs/MIA_V3_GUIDE.md` | Delete or rewrite (Q10). |
| `ml/README.md`, `services/README.md` | Keep as stubs. `services/` waits on Q9. |

## 12. Work split: Frontend, Backend and AI

The team asked on 13 Oct for the plan to be divided into three parts so that three people can work at the same time (D8). This section is that division. It adds no scope. Every item is a story or an outline from sections 5 and 6, and the detail stays there. Each part says what its owner owns, what to do in order, what to wait for and what to hand over.

Dividing the plan does not approve the stories. They stay **proposed** until section 9 records the team's go-ahead. The "Waits on" column shows what else each story needs.

### 12.1 Frontend part

**Owns:** `apps/web/**`, and the block headed "Frontend" in `infra/.env.example`.

| Order | Story | What it is | State | Waits on |
|---|---|---|---|---|
| 1 | E6-S2 | The build and the tests pass in `apps/web` | Implemented and verified by Audit; uncommitted | The commit |
| 2 | E1-S4 | The Alerts screen (02) and the rail badge | Proposed. It can be built against a fixture of C1 draft 3 before the API exists | Q4 (which lanes) and Q5 (the officer's name). Live data needs E1-S3 from Backend |
| 3 | E1-S5 | The joint check of the alert flow on the running stack. Audit runs it; Frontend's part is that the screen passes it | Proposed | E1-S1 to S4; Q1 |

**After E1, stories not yet written.** They are written when E1 is approved and the AI part has reported (26 Oct).

- E2: the "Explained by weather" lane with Restore and Escalated, and the vessel's state on the map and in the panel.
- E5: the vessel evidence screen (03) and the encounter graph. It needs contract C2 from Backend first.
- E3 and E4: radar-only alert cards, the radar crop on screen 03, and the hotspot cells on the map. Backend serves these, and the API shapes are written with the stories.
- E6: `NotBuiltYet.jsx:10` corrected after Q2.

**Decisions this part waits on:** Q4, Q5, Q12 (minimum width) and Q2 (whether screen 04 is in scope).

### 12.2 Backend part

**Owns:** `apps/api/**`, `infra/docker-compose.yml`, and the rest of `infra/.env.example`.

| Order | Story | What it is | State | Waits on |
|---|---|---|---|---|
| 1 | E6-S1 | API tests run against a real database with one command | Proposed | Nothing |
| 2 | E6-S4 | Bad AIS records are rejected at ingest | Proposed; criteria agreed with Audit | E6-S1 |
| 3 | E1-S1 | Alerts are stored and keep their identity | Proposed | E6-S1. Q3 has a working default |
| 4 | E1-S2 | Alerts and scores stay current on a timer (D7) | Proposed | E1-S1; E6-S4 |
| 5 | E1-S3 | The alerts API. Frontend's screen waits on this story for live data | Proposed | E1-S1; Q5 for the actor's name; Q10 for replacing `alerts.py` |
| 6 | E1-S5 | The seed closes the alerts it replaces and raises the new ones | Proposed | E1-S1 to S4 |

**After E1, stories not yet written.**

- E2: the evasion states, and the weather check with Open-Meteo Marine. The open points are in the E2 outline (section 5).
- E5: the encounter graph over two hops, and contract C2 for it.
- E3 and E4: loading the AI part's result files, matching radar hulls against AIS, raising radar alerts and serving the hotspot cells. All of this depends on Q14.
- E6, later stories: protection on the ingest routes (G6), replayed batches (G13), a position with no speed (G14), the clean-up in Q10, and the official protected-area boundaries.

**Decisions this part waits on:** Q3, Q5, Q10, and Q14 before any E3 or E4 work.

### 12.3 AI part

**Owns:** `ml/**`: training code, dataset preparation and model cards (`ml/README.md`). The directory holds only that README today. This part has no code to inherit: the YOLOv8 pipeline in the API is for optical pollution images and is frozen (section 2).

| Order | Story | What it is | State | Waits on |
|---|---|---|---|---|
| 1 | E3-S1 criterion 1, E4-S1 criterion 1 | Register for xView3-SAR, Copernicus Marine and Global Fishing Watch. Nothing else in this part can start without the data, so this is the first day's work | Proposed | Nothing |
| 2 | E3-S1 | Find out whether xView3 detection fits in four weeks: one YOLOv8s training run on a subset, with precision, recall and F1, and the inference time and memory on the RTX 3050 | Proposed | The data |
| 3 | E4-S1 | Get the hotspot data and a baseline number: one download for the two gulfs and a "repeat last month" baseline. The download and the baseline can run while the E3 training runs | Proposed | The accounts |
| 4 | The E3 and E4 stories that follow | The detector and the hotspot forecast themselves, with the README's metrics (`README.md:81-83`) | Not written. Planning writes them from the two reports | The go or no-go on 26 Oct; Q7; Q14 |

**Before the first download.**

- Add ignore rules for datasets and weights under `ml/`. `.gitignore:27` covers only `models/*.pt` at the top of the repository; planning checked on 13 Oct that a file under `ml/` or `apps/api/models/` is not ignored. The repository is public, and the Definition of Done forbids committing data, weights or tokens.
- Set up a training environment of its own. The API image installs CPU-only PyTorch (`apps/api/Dockerfile:21`).
- Hardware: one RTX 3050 Laptop with 6 GB, and 124 GB of free disk on that machine (Backend's check), plus Kaggle and Colab (D3). If the AI owner works on another machine, E3-S1 criterion 4 needs time on that one (Q8).

**What each report must end with.** A written recommendation: go, go with a named reduction, or move to the finale. Both are due by 26 Oct, while there is still time to change the plan (G1).

**Hand-over.** Under planning's recommendation for Q14, this part gives Backend result files, not a running service: radar detections (C3) and ranked hotspot cells (C4). Neither format is written yet. Planning proposes that the AI and Backend owners agree both by 26 Oct on a small hand-made sample file each, so Backend can build its loader while training is still running.

**Not in this part for 10 Nov:** route prediction, pollution detection and the chat assistant (frozen, section 2); the local LLM, the radar heat overlay and SHAP (finale, section 4).

**Decisions this part waits on:** Q8 (confirm), Q7 (after E3-S1) and Q14.

### 12.4 Where the parts meet

Each hand-over has a written contract, so that neither side has to guess the other's format.

| Hand-over | From | To | Contract | State |
|---|---|---|---|---|
| Vessels and protected areas | Backend | Frontend | C0 | Frozen |
| Alerts | Backend | Frontend | C1 draft 3 | Agreed between the sessions (D6) |
| Encounter graph | Backend | Frontend | C2 | Not written; needed before the E5 stories |
| Radar detections | AI | Backend | C3 | Not written; proposed by 26 Oct, with a sample file (Q14) |
| Hotspot cells | AI | Backend | C4 | Not written; proposed by 26 Oct, with a sample file (Q14) |

The AI and Frontend parts do not meet directly. What a model produces reaches a screen through the API.

### 12.5 The dates, by part

The dates are those of section 8.

| By | Frontend | Backend | AI |
|---|---|---|---|
| Mon 19 Oct | E6-S2 committed. E1-S4 under way against the fixture | E6-S1 and E6-S4 done. E1-S1 in review | Data access confirmed or refused for all three sources |
| Mon 26 Oct | E1-S4 done on live data | E1-S1, S2, S3 and S5 done | E3-S1 and E4-S1 report. C3 and C4 agreed with Backend |
| Mon 2 Nov | The E2 and E5 screens done | E2 and E5 done. The AI results loaded and served, or a scope change recorded in section 9 | Result files handed over with their measured scores, early enough for Backend to load them by this date |
| Thu 5 Nov | No new features after this day | The same | The same |

### 12.6 Outside the three parts

- **Checking.** The Audit session checks every story before it is called done (Definition of Done, item 5), and runs E6-S3 and the check in E1-S5.
- **The plan.** Planning keeps this file. Each owner sends findings and proposed changes to planning; they do not edit the file.
- **Shared files.** The ownership table in section 7 holds, with `ml/**` now the AI part's. `README.md` and `.gitignore` are shared: whoever's change makes a line wrong, or needs a new ignore rule, edits that line only.
- **No owner yet.** Recording the video (6 to 9 Nov), the last README pass and the submission itself. The team should name one person by 2 Nov.
- **Load.** Backend carries the most stories, and everything the AI part produces passes through it before it reaches a screen. Planning proposes no move of work now. The time to look again is 26 Oct, when the go or no-go on E3 and E4 shows how much of the AI owner's time is free.

## 13. Changes since the first draft

**Update 1, 13 Oct 2026.** Source: findings from the Backend session and, through it, the Audit session, and a report from the Frontend session. Planning re-read the code and the running API where it could; anything it could not check is marked as relayed. No story had been approved or started, so no finished work is affected.

| Change | Why |
|---|---|
| Q3 recommendation and E1-S1 criterion 4: an alert no longer closes because its evidence aged out | Backend and Audit each measured Sea Pearl II falling below 0.60 at 15.5 hours after seeding (about 21.7 hours after its last position), while it is still dark. The first draft would have closed the alert at that point (G10) |
| C1 is now draft 2 | Backend's proposals from the code: `scored_at`, the whole factor as `top_reason`, the zone shape, list order and filters, the allowed moves, one open alert per vessel |
| E1 outcome 5 and E1-S2 criterion 3 use `scored_at` | "For the same moment" could not be tested: a stored alert is always up to one interval behind `/vessels` |
| E1-S5 criterion 2: the seed closes the alerts it replaces | "Exactly one alert after a re-seed" conflicted with "no alert is ever deleted" |
| E1-S4 criterion 9 | With the new Q3 rule an alert can outlive its vessel's place in `/vessels` |
| New gaps G10, G11, G12 and decision Q11 | The demo story fades and has a 0.03 margin; ingest accepts positions that break `/vessels/`; the outage rule sets aside real gaps when a whole area goes quiet |
| G3, G4, G6, Q9 and the port note in section 7 corrected | First-draft errors Backend found: the seed also refreshes stored scores; `dark` also needs the outage ruled out; the URL fetch sits behind a 503 today; no job is dispatched to Celery; the other Postgres container is on port 55532 |
| G8 carries measured figures | Backend's and Audit's timings. An earlier worst-case set was withdrawn by Audit and is not used |
| Section 2 and Q1 | Frontend started and seeded the stack, so vessel reads on seeded data are verified, and Frontend ran the map console in a browser |
| E6-S2, E1-S4 criteria 5 and 8, Q12 | Frontend's report: 59 frontend tests pass (planning ran them too); the "not live" code and the badge label moved; one layout question at 1024 px is open |
| E3 outline, E6-S1 | Hardware facts from the team machine; the image holds no test dependencies |

**Who is affected.** Backend: E1-S1, S2, S3, S5 and E6-S1. Frontend: C1 draft 2 and E1-S4 criteria 4, 8 and 9. Audit: G8, G10, G11 and G12 rest partly on its findings as relayed, so its own report should come to planning; Frontend's nine map-console fixes are waiting for its check (E6-S3).

**Update 2, 13 Oct 2026.** Source: Backend's review of update 1. Backend confirms C1 draft 2 states its proposals correctly. Frontend has still to agree it.

| Change | Why |
|---|---|
| Q3 and the first row above said the score falls "15.5 hours after it goes dark" | Planning's error. It is 15.5 hours after seeding, about 21.7 hours after the vessel's last position (`seed_demo.py:80`) |
| The closing rule in Q3 and E1-S1 criterion 4 compares position times | "Reported again since `scored_at`" compared a position time with a server clock, and `vessel_tracks` records no arrival time, so a late-arriving position could be missed |
| C1: `last_seen` added to an alert | It is the value the closing rule compares against, and the time a card shows once its vessel has left `/vessels` (E1-S4 criterion 9) |
| C1: `top_reason` is the first entry of `factors` | The engine sorts factors once and `headline` reads the same first entry (`risk_engine.py:353,384`), so card, headline and panel cannot disagree on a tie |
| C1: the list route returns 422 for an unknown `status` | Consistent with the status route. Today's route returns an empty list for an unknown filter value, which Audit has since confirmed (G2) |
| Section 10: "What the Q3 recommendation means in practice" | Four consequences written down so nobody reads them as defects, including a vessel that returns after more than 24 hours dark |

**Update 3, 13 Oct 2026.** Source: Frontend's review of C1 draft 2 and E1-S4. Frontend agreed draft 2 as written after checking it against the live `/vessels` responses. It later confirmed the three additions from update 2 and the E1-S4 wording below, and has no objection to leaving the `zone` filter out of E1. `last_seen` is now worded as a time, at its request.

| Change | Why |
|---|---|
| C1 is marked agreed by both sides, with two open points for Backend | Frontend's agreement; its request for a way to spot kept values; nothing will call the `zone` filter |
| E1-S4 criteria 3, 4 and 8, and its context | Frontend will load all alerts once and filter by zone in the browser, so the badge and the screen share one source. Chips use the API's full zone names |
| E1-S4 criterion 1 compares score, key and points, not text | The alert's text is fixed at `scored_at`; the panel's is live |
| Q12 carries two options | Frontend tried map padding at 1024 px and it cannot work; the choice is a stated minimum width or a layout change |

**Update 4, 13 Oct 2026.** Source: the Audit session's own report. It confirms G8, G10, G11 and G12 as reproduced, so they no longer rest on a relay. Planning read the code behind G11 and behind the three frontend fixes that have no unit test. It did not rerun Audit's reproductions.

| Change | Why |
|---|---|
| G11 rewritten and no longer provisional; new story E6-S4, with rows in sections 2, 4, 7 and 8 | Audit reproduced it and rates it Critical. One NaN position makes `/vessels/` fail for every vessel and every later ingest fail. One over-long field loses a whole batch. A future-dated position never leaves the window |
| E1 risks name G11 | The E1-S2 evaluation will read the same rows that a bad record breaks |
| Q1 corrected | It said Audit had installed pytest in the container. Audit reports that it installed nothing and ran every check inside a transaction that was rolled back |
| G8, G10 and G12 wording | Confirmed first-hand. G10's hours come from single runs on the current seed. Audit calls G12 a trade-off, not a defect |
| Section 2, E6-S2 and E6-S3 | Audit verified Frontend's nine fixes in the code and ran the 59 tests. The 12-hour timeline against 24-hour scoring matches the signed-off design, so no change is proposed |

Audit also agrees with the Q3 recommendation. That is still the team's decision.

**Who is affected.** Backend: E6-S4 is new and should land before E1-S2. Audit: E6-S4 is done only when its three reproductions no longer succeed. Frontend: nothing changes.

**Update 5, 13 Oct 2026.** Source: Audit's answers to planning's three questions. Most of it confirms what the plan already had. Planning read the code behind each new item and did not rerun Audit's tests.

| Change | Why |
|---|---|
| New decision Q13 | Audit lists a database password among the secrets in the public history. D4 covers the Gemini and Supabase keys only |
| G11; E6-S4 criterion 1 and "done when" | Audit also stored latitude 95, longitude 400 and a negative length, and read them back |
| New gap G13, listed as a later E6 story | Replaying a batch doubles the rows. HELPFUL: nothing in the demo sends a batch twice |
| E6 outline: WDPA boundaries need multi-part areas handled first | `zone_relation` would fail on one, and the column cannot store one. It cannot happen on the seed |
| G2, G3, G6, the chat row in section 2, one row in section 4 | Audit's confirmations and ratings for findings already listed. `/map/layers` shares the old one-hour window and nothing calls it. Protection on ingest routes stays HELPFUL only while everything runs locally |
| Vessel API row in section 2; E1-S5 criterion 4 | Audit verified the three read routes on the seed at 13:47 UTC. Its findings on today's alerts route are closed by E1 and checked again in E1-S5 |

**Who is affected.** The team: Q13. Backend: E6-S4 criterion 1 has one more case. Frontend: nothing changes.

**Update 6, 13 Oct 2026.** Sources: Backend's answers on C1 and E6-S4, Audit's correction on pytest, and Frontend's report of what it settled with Backend and Audit. Frontend and Backend each report that the team told them to communicate with each other directly. So what the sessions agree on technical points is recorded here and in section 9, and is not put to the team as a question. None of it approves a story.

| Change | Why |
|---|---|
| C1 is draft 3 (D6): `evaluated_at` added, `zone` filter removed. E1-S1 criterion 7, E1-S2 criterion 6, E1-S3 criteria 1 and 2 follow | Backend decided the two open points and Frontend accepts both. The run time needs one stored value, because it cannot be worked out when no vessel meets the rule |
| E1-S4 criterion 10, and the "Scoring stopped" rule in C1 | Frontend asked whether the screen should say when scoring has stopped, and would not choose the limit itself. Planning's answer is yes. The limit, 3 minutes, is Backend's suggestion. Frontend then read the criterion and asked for four clarifications, all taken: null means "not yet run", the stopped state has its own sentence, times carry the date when it is not today, and only the Alerts screen is marked |
| E6-S2 context and "still needed"; E6-S3 context; one rule under the ownership table | Audit's build and 59 tests pass, but its `npm ci` failed on a file the dev server held, and its reinstall wrote the lockfile in the working tree. Audit then ran the full command in a copy outside the repository and it passed, so both criteria are checked. Frontend finds no sign that the lockfile's content changed (E6-S2), so what remains is the commit. A second rule follows from this: no session restores a modified file from git. Audit sent its own record of the three browser-only checks, and each passes |
| E6-S4 rewritten: seven criteria, and two kinds of bad record | Backend found four gaps: whole numbers too large for a column, non-finite numbers other than the position, one wrong-typed record refusing a whole batch, and no guard where scoring reads. It also measured a negative speed earning risk points. Planning proposes that a bad value outside the position, time and MMSI empties that field and keeps the position |
| Backend and Audit agreed E6-S4 criterion 2, with three changes from Backend and one more test from Audit; new G14 | Backend measured that refusing a record can raise a score and that emptying a field cannot. It also measured the cost, an empty speed ending a loitering or encounter run, which is G14 and a later story. At its request the user value says "raise a score", a side field of the wrong type is emptied and not refused, and the response gains `blanked` |
| D7; E1-S2 context and its section 7 row; Q9 | Backend chose how the timer runs: inside the API process |
| The upper time bound moves from E1-S2's tests to E6-S4 criterion 7 | One line in `load_pings` serves both (Backend) |
| E6-S1 gains a test of the C0 fields the console reads | Proposed by Backend, with Frontend's list |
| Q1 corrected again | Update 4 removed the note that Audit installed pytest in the container. Audit has since found the command in its own transcript. Backend's reading of the container agrees |
| G6 and G11 | Audit's lower-rated notes, its over-large MMSI case, and Backend's measurements |
| Owner of `infra/.env.example` | Frontend asked. It removed three unused lines from its block |

Not changed: Frontend asked what the console should show for a vessel with no position. Nothing new. `position` stays required in C0, the E6-S1 test guards it, and E6-S4 keeps out the only known way to store a record without one. Backend also noted that an encounter label takes the other vessel's name from the start of the encounter, while the vessel list takes it from the newest position. The two are equal on the seed, Frontend calls a mismatch cosmetic, and no story is proposed.

Also not changed: Backend proposed that a second seed delete the alerts and history of the vessels it re-seeds, so the story starts from a new alert. E1-S5 criterion 2 already covers a second seed by closing those alerts with the actor `seed`, and it stays, because the product never deletes an alert (G2). Backend checked that closing works with the lock and the one-open-alert rule, and withdrew the proposal. Backend's answer that the seed and the ingest route count as evaluation runs is taken into E1-S2 criteria 2 and 6 and C1.

**Who is affected.** Backend: E6-S4 criterion 2 is new, agreed by Backend and Audit; the read-side guard is criterion 7; E1-S1 criterion 7 and E1-S2 criterion 6. Frontend: E1-S4 criterion 10. Audit: under E6-S4 criterion 2, a negative length or an over-long text field no longer refuses the record.

**Update 7, 13 Oct 2026.** Source: the team, which asked for the plan to be divided into a Frontend, a Backend and an AI part so that three people can work. No story's scope or criteria changed. The change log moved from section 12 to section 13.

| Change | Why |
|---|---|
| New section 12, and D8 | The division the team asked for. Each part lists its files, its stories in order, what it waits on and what it hands over. The stories themselves stay in sections 5 and 6 |
| E3-S1 and E4-S1 are owned by the AI part; `ml/**` in the ownership table; their row in section 7 | They were Backend's "until Q8 names someone". D8 names the AI part |
| Q8 reworded as a confirmation | D8 answers who runs the training. Whether that person also holds the data accounts and has time on the RTX 3050 is planning's reading |
| New decision Q14, and contracts C3 and C4 named but not written | With a separate AI owner, the line between AI and Backend has to be drawn once: who matches hulls to AIS, whether a model runs inside the API, and who builds the evasion states. `README.md:123` lists the state machine under AI / ML, and the code is Backend's |
| Section 12.3: ignore rules before the first download | `.gitignore:27` covers only `models/*.pt` at the top of the repository. Planning checked that files under `ml/` and `apps/api/models/` are not ignored |
| Section 12.6: the video, the last README pass and the submission have no owner | None of the three parts covers them |

**Who is affected.** Backend: E3-S1, E4-S1 and `ml/**` are no longer its work; loading the AI part's results joins its later work, under Q14. Frontend and Audit: nothing changes. The AI owner: section 12.3 is the starting point, and no AI session exists yet to receive this.
