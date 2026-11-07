# SamudraSense: final product delivery plan

Plan updated: 3 November 2026. All deadlines are 18:00 India Standard Time (IST).

Harness audit, 4 November 2026: this remains the canonical F01–F14 specification, ownership allocation and deadline schedule. Start execution with [PLAN.md](../PLAN.md), [PROGRESS.md](../PROGRESS.md) and [the current task](../tasks/current.md); they map this plan to actual implementation. Section 2 is a dated starting-point snapshot, not current completion evidence. P1 and the judging gate have not passed. Shared operating instructions are now in [AGENTS.md](../AGENTS.md).

Owner: Team Code4Seas. Team size: two people; an optional third person has a separate work area.

The judging demo is due 10 November. The team will pull a real-data slice of phases 3 and 4 into that demo using the accelerated schedule in section 8. The complete phase 3 and 4 requirements remain due 20 November and 2 December respectively; tested v1 is due 11 December 2026. A pilot review is due 8 January 2027, ahead of the README's 20–21 January finale.

This is a proposed execution schedule, not a claim that work is complete. It assumes two people each have six focused hours per weekday for six weeks: 360 person-hours. Plan 300 hours of work and keep 60 hours for integration and defects. If that capacity is unavailable, reduce the release scope explicitly; do not silently move the deadlines or call unfinished features complete.

## 1. Product definition and release boundary

SamudraSense helps a coastal analyst decide which vessel activity needs investigation, understand the evidence, prepare a reviewed case, and explore environmental risk. Its main journey is:

**Select waters → inspect activity and data coverage → review an alert → examine evidence → approve a report → export or dispatch it.**

The first complete release serves one organisation in the Gulf of Mannar. Its area of interest (AOI) is configurable. Gulf of Kutch is the second test area after the first works. It must support live data when available, recorded data for replay, and cached data when offline. Those modes must always be visible.

The environmental feature forecasts ocean conditions and ranks likely fishing activity. It does not prove illegal fishing or forecast global climate change. Protected-area presence, AIS gaps, rendezvous and unmatched satellite detections are investigation signals. Conclusions need source context and human review.

### What counts as the full v1

All required feature outcomes F01–F14 below work end to end. The app has no placeholder pages in its release navigation. Data access, tests, performance measurements, setup instructions and an offline demonstration are included. The release supports a supervised pilot; it does not claim legal certification, global satellite coverage, or production accuracy without field evidence.

Some outcomes have two implementation options. For example, SAR evidence can come from an external detector or our own validated detector; report text can come from a template or an optional local language model. The required outcome must work even if an optional model is absent. A fallback must be labelled and tested.

Not part of this six-week release: training a large SAR model from scratch; the full xView3 download; a buoy; global AIS coverage; automatic enforcement decisions; ownership/sanctions intelligence; native mobile apps; multiple customer organisations in one database; a new C++ filter; a Node/BullMQ replacement for Celery. These can be separate projects after v1. Existing pollution AI, LSTM and chatbot code must not appear as validated product features just because an endpoint exists.

## 2. Verified starting point

Checked on 2 November using CodeGraph, local documentation, Docker Compose and the running API schema. The frontend returned HTTP 200. These checks establish presence and reachability, not full correctness.

| Area | Present now | Work still required |
|---|---|---|
| Runtime | API, frontend, Celery, Redis and PostGIS running in Docker; database and Redis healthy | Production configuration, health checks for all services, scheduler, resource limits, backup/restore and offline packaging |
| Tracking | AIS import, vessel map, history and explainable rule scores | Live source adapter, deduplication, bounded ingestion, source health and coverage |
| Alerts | Vessel-based alert screen; a separate legacy alert endpoint | One consistent, stored alert model; stable IDs, lifecycle, assignments and audit history |
| Evidence | Vessel factors, encounters, weather request and SAR import/matching | Complete event timeline, ambiguous matches, graph, source drill-down and persistent source records |
| SAR | External coordinates accepted; nearest AIS ping within 2 km and 15 minutes becomes a candidate | Real provider adapter, scene provenance, unmatched detection investigation, accuracy evaluation |
| Reports | Snapshot JSON, SHA-256, typed reviewer name and review checkbox | Authenticated approval, source binding, immutable revisions, audit trail, export and delivery tracking |
| Weather | Open-Meteo model context at an AIS gap; no score change | Cache, availability handling, coverage checks and evaluated triage recommendations |
| Hotspots | Product idea in README | Regional data pipeline, baseline, forecast evaluation, map and scan prioritisation |
| Spills/settings | Routes show placeholders | Scenario engine, results, permissions, data sources and settings screens |
| ML/offline | Model-loading code and planned offline design | Validated weights, measured resource use, local basemap and cached workflows |

Important code locations: apps/api/app/services/risk_engine.py and fleet.py; apps/api/app/api/{vessels,alerts,sar,reports,weather}.py; apps/api/app/tasks/celery_app.py; apps/web/src/pages/Cases.jsx; apps/web/src/App.jsx; infra/docker-compose.yml. Existing migrations run through 005; check the actual Alembic head before adding more.

The legacy alerts route creates fresh random IDs on reads and uses a separate prediction path. Resolve this early so the map, alert board and reports cannot disagree. Current report approval is not identity verification. The existing satellite pollution worker can produce fallback geometry when georeferencing is missing; reject missing georeferencing before exposing that path in the release.

The worktree already contains implementation changes and user configuration changes. Preserve them. The preceding repository check found local ap equal to origin/ap; that was checked on 1 November, not revalidated by this plan. Phase 1 must check again before implementation.

## 3. Competitive gap and the claim we should make

The detailed source review is in [PLAN_RESEARCH.md](PLAN_RESEARCH.md). Treat vendor descriptions as advertised capabilities, not independent performance tests.

| Existing capability | Consequence for SamudraSense |
|---|---|
| Global Fishing Watch provides vessel activity, encounters and SAR-derived information | Tracking, encounter detection and SAR/AIS matching alone are not a new invention |
| Skylight combines maritime surveillance sources and suspicious-activity events | Do not claim that dark-vessel detection is unique to us |
| OceanMind supports fisheries monitoring and compliance analysis | A risk label alone does not close the operational gap |
| Windward markets broader maritime risk and vessel intelligence | Do not spend this schedule recreating global commercial intelligence |

Our proposed advantage is a small, affordable workstation deployment that joins regional ocean conditions, cautious triage and traceable case preparation in one interface. This is a hypothesis to demonstrate, not an established market lead.

Show the following evidence before using an advantage in a presentation:

1. **Less analyst work:** compare time to complete the same case with raw files versus the app. Run at least five cases with two reviewers. Report the median and mistakes, not just the fastest run.
2. **Useful triage:** measure how often weather/coverage recommendations help and how often suspicious cases are wrongly set aside. Retain every original alert and reason.
3. **Useful environmental prioritisation:** compare the same scan budget against recent-activity ranking and uniform selection on time-separated data. Count activity captured and detections missed. Fishing activity is a proxy, not a label for illegality.
4. **Lower resource use:** measure wall time, RAM, optional VRAM, downloaded bytes and local storage on the named machine. Report energy only if actually measured.
5. **Evidence continuity:** a reviewer can follow every report fact to a record, inspect its version and verify an exported snapshot offline.

## 4. Final feature specifications

### F01. Accounts, roles and deployment settings — required

- Local sign-in must work offline. Use maintained password/session libraries, hashed passwords, expiry, revocation, login rate limits and a first-run administrator flow. Do not build cryptography.
- Roles: Viewer reads; Analyst investigates and drafts; Approver approves and authorises sending; Administrator manages users, sources and settings. A person can hold more than one role in a small team. Record the actor for each action.
- Enforce permissions in the API, including ingest, jobs, exports, reports, settings and any legacy chat tools. Hiding a button is insufficient.
- One deployment serves one organisation. Use an explicit source/data-mode boundary so demo evidence cannot enter a real case silently.
- Settings cover AOI, timezone display, thresholds, recipients, retention and source status. API keys stay server-side and are never returned to the browser.
- Done: tests cover allowed and forbidden actions for every role, session expiry and disabled accounts; an unauthenticated caller cannot change data.

### F02. Vessel tracking and data quality — required

- Ingest geographic-filtered AISStream positions and supported CSV/JSON files. Keep the source identifier, vessel identifier, observation time, ingestion time and quality flags.
- Validate coordinates, timezones, speed and AIS unknown-value codes. Quarantine invalid records with a reason. Handle late and out-of-order records without inventing motion.
- Deduplicate replays and reconnect deliveries. Bound queues and batches. Retry with backoff; resume from a recorded checkpoint where the provider supports one.
- Map search supports MMSI/name, time window, AOI and risk filters. Vessel detail shows metadata, track, latest observation age and source.
- Show feed availability separately from estimated receiver coverage. An absence of AIS observations does not establish deliberate silence.
- Done: replaying the same input twice does not double records or alerts; connection loss is visible; a source recovery does not create a flood of duplicate alerts.

### F03. One explainable alert engine and lifecycle — required

- Reuse the additive risk engine. Unify map, alerts and reports around the same score, evidence and rule version. Preserve existing behaviour unless a documented test justifies a change.
- Evaluate AIS gaps, position jumps, prolonged slow movement, close encounters and activity inside/near protected areas. Thresholds depend on vessel class and data quality where known; record unknown class explicitly.
- Add an event history for observed → gap detected → corroboration available → in review → resolved. This represents evidence state, not a determination of guilt. Late data can add a revised assessment without overwriting history.
- Store stable alert IDs and a deduplication key. Track New, Watch, In review and Closed separately from report approval/delivery status. Add assignee, notes, reopen and resolution reason.
- Every alert shows score contributions, source references, checks not completed and a computed “what would clear it” scenario. Do not hard-code a counterfactual score in the UI.
- Done: reloads keep the same ID; the map and board show identical scores; an analyst can reopen a watched/closed alert with a recorded reason.

### F04. Protected areas and restrictions — required

- Replace sample polygons in real mode with licensed boundaries and verified local sources. Keep publisher, version, date, citation and permitted uses.
- Model presence, buffer proximity and applicable restrictions separately. A buffer used for review is not automatically a legal boundary. Protected status does not automatically ban every type of vessel or activity.
- Store restriction description, activity/season applicability and verification status. Until checked, label “activity in protected area; restrictions unverified”.
- Support boundary version history and a UI source panel. Treat invalid geometry, coastal edges and missing rules explicitly.
- Done: demo polygons are visibly labelled; real alerts link to the exact boundary/rule version; restricted data is not included in distributable bundles without permission.

### F05. SAR evidence and AIS association — required; own inference optional

- Add a GFW adapter for the dataset and detail level actually available to the account. Discover dataset IDs and schema; do not assume a heatmap API returns individual detections. If point access is unavailable, use a permitted point export or another verified source. Aggregates may be an overlay but cannot become fabricated point evidence.
- Keep acquisition time distinct from publication and ingestion time. Store scene/detection IDs, geometry, confidence meaning, provider match result, licence reference and image/crop location if accessible.
- Support matched, unmatched, ambiguous and insufficient-coverage states. Evaluate multiple AIS candidates using time difference, distance, feasible motion and uncertainty. Preserve the current 2 km/15-minute rule as a baseline to evaluate, not a universal final threshold.
- An unmatched detection gets its own detail page and case. Do not require an MMSI for every alert or report.
- Display the real crop if licensed and available. Otherwise show footprint/location and “image unavailable”. Never substitute a decorative image for evidence.
- Optional local inference: isolated adapter for Ai2's pretrained SAR model. Honour its preprocessing, licence and hardware requirements. Do not load its weights into the existing generic YOLO pipeline.
- Check the published model's training split before choosing evaluation scenes. Ai2's README says its training used xView3 validation scenes, so the dataset's “validation” name does not make a scene unseen by those weights. When overlap is unknown, report an integration smoke test and runtime; do not claim independent detection accuracy.
- Done: real, permitted samples pass import and provenance checks; tests cover ambiguous matches, missing AIS, duplicate scenes and invalid geography; evaluation reports association errors and unknowns.

### F06. Weather and coverage triage — required

- Fetch wind/waves for the event's time and location; cache by source, grid and time. Preserve model/forecast issue time where provided. A current forecast cannot stand in for an unavailable historical value.
- Show conditions, source age, feed health and nearby observation availability beside the alert. Mark missing information “unknown”. Nearby silence alone is not proof of a receiver outage.
- Suggest “weather may explain this behaviour” only through a versioned, tested rule. Keep behavioural score and operational review priority separate.
- Start with analyst-confirmed Watch decisions. No weather-only automatic closure. Preserve the original evidence and allow restoration. Protected-area activity remains visible; a storm is not evidence of wrongdoing by itself.
- Done: offline/missing weather never lowers priority automatically; reviewer actions are logged; the evaluation includes suspicious activity during storms and sparse AIS coverage.

### F07. Encounters and evidence workspace — required

- Show a time-aligned map, speed/position plot, SAR observation, weather, alert events and source list. A click on an event selects the corresponding time and location.
- Build a graph of observed vessel encounters over a selectable window, default 48 hours. Support up to two hops and cap nodes/edges to keep the UI usable.
- Each edge shows distance, duration, time overlap and input coverage. A close encounter does not establish cargo transfer, shared ownership or illegal activity.
- Keep observations, model estimates and analyst notes visually distinct. Store notes as authored records with timestamps.
- Done: every displayed connection can be traced to input records; sparse tracks cannot satisfy a long encounter duration by interpolating through large gaps.

### F08. Ocean conditions, activity hotspots and scan planning — required

- For the first AOI, ingest subsetted sea-surface temperature (SST), chlorophyll and fishing-effort history. Keep units, quality masks, resolution, product version and observation/availability times.
- Start with a configurable 0.1-degree grid, adjusting to the coarsest useful input. Do not imply finer resolution than the source. Fetch a small regional time window before any longer history.
- Forecast next-day conditions using persistence and available provider forecasts. Add a simple seasonal/lagged baseline for seven-day activity ranking. Chlorophyll gaps must carry a missing-data flag; do not fill clouds with invented measurements.
- Rank cells by recent activity and environmental features. Show environmental anomalies separately from the activity score. Explain the actual factors used. Historical fishing effort is not illegal-fishing ground truth.
- Use a rolling temporal split: train/tune only on earlier data, then evaluate on a later blocked period. Align inputs to what was available at prediction time. If enough labelled history is unavailable, show a descriptive layer and mark the forecast evaluation blocked.
- Recommend which existing/available satellite scenes or tiles to process within a daily budget. This does not task a satellite or change its orbit. Reserve 20% of the evaluation scan budget for non-hotspot coverage to measure blind spots.
- Done: export a reproducible backtest against persistence, recent-effort ranking and a uniform scan baseline. Promote an advanced ranker only when held-out results support it; keep the baseline if not.

### F09. Reports, approval, integrity and delivery — required

- Cases may refer to vessels, unidentified SAR detections, spills or several events. Capture an immutable evidence snapshot when creating each report revision.
- Generate a deterministic report containing event times, coordinates, sources, score explanation, uncertainty, analyst findings and attachments. Every factual field links to an evidence reference. Missing references block approval.
- An optional local language model may suggest wording from the approved structured facts. It cannot invent values, run arbitrary SQL, change evidence or send messages. Template generation is always available offline. Treat imported text as data, not instructions.
- Approval requires the logged-in approver, report version and reviewed state. Editing an approved report creates a new draft revision requiring new approval. Use concurrency checks so two reviewers cannot overwrite each other.
- Preserve canonical hashes and an append-only application audit history. Export a hash manifest to independently held storage. State the threat model: a hash stored beside mutable data does not protect against a privileged database administrator rewriting both. Do not call the current typed-name feature a digital signature.
- Export a human-readable PDF and machine-readable evidence manifest. Bundle only assets allowed by their licences. Include instructions to check hashes and source references offline.
- Implement optional SMTP delivery to an administrator-approved recipient list. Require explicit approval of the exact report version and recipients. Use an outbox, idempotency key, retry limit and delivery state. Provider acceptance means submitted, not received/read. Never send merely because a job retried.
- Done: unreferenced/tampered/stale revisions cannot be approved; export re-verifies; rejection and revision work; failed delivery remains visible and does not create duplicate sends. Test with a local mail sink before any real recipient.

### F10. Spill scenarios and pollution observations — required

- Allow an analyst to enter or import a georeferenced pollution observation. Automated oil detection is optional and remains disabled without validated weights and labels.
- Run a bounded NOAA PyGNOME scenario from location, release time, duration, substance parameters, wind and current fields. Record all inputs, defaults, engine version and random seed.
- Show 6/12/24-hour trajectories or footprints, uncertainty ensemble, coastline contact and potentially affected protected areas. Label this a planning scenario; a deterministic path is not a calibrated probability contour.
- Use a job with queued/running/failed/complete/cancelled status. Limit area, particle count, run duration and output size. A missing current field must not silently become zero flow.
- Offline mode can use cached forcing for its valid period. Synthetic forcing is allowed only in a clearly labelled training scenario. A reference notebook is not a finished app feature.
- Done: constant-flow and no-flow checks pass; a reference scenario is reproducible; real-data availability is visible; the UI can run and inspect a scenario without a developer's terminal.

### F11. Offline operation and economical processing — required

- Ship a licensed regional PMTiles/vector basemap with local style, glyphs, sprites and fonts. Verify all browser assets load without internet. Retain map attribution.
- Support browsing cached tracks, investigating existing cases, writing notes, drafting/approving reports and exporting them offline. Clearly show last sync and the validity window of cached environmental data.
- Pause remote fetches when offline. Resume idempotently after reconnect. Live AIS and newly acquired satellite data require a connection; cached data must not appear live.
- Use AOI/time filters, conditional downloads, content hashes, bounded caches and serial heavy jobs. CPU-only operation is the default supported profile; GPU use is optional and measured.
- Done: a prepared installation completes the case workflow with networking disabled. A fresh machine still needs the installation pack and permitted data pack supplied beforehand.

### F12. Source management, job control and operations — required

- Settings show connection state, latest observation, last successful import, data latency, quota use when available, licence status, errors and retry action. Never show API keys.
- One scheduler launches incremental jobs. Give jobs stable identifiers, retries, cancellation, timeouts and progress. Monitor queue depth, disk space and worker liveness.
- Add bounded logs and request/job IDs. Provide daily backups, a documented restore procedure and a tested upgrade/rollback path. Restore into a separate database first.
- Done: stop/restart a worker during an import without duplicated evidence; restore a backup and verify sample cases; source failure appears in the UI.

### F13. Release interface and accessibility — required

- Preserve the signed-off light/navy/periwinkle design in docs/design/DESIGN.md. Do not restart the visual design or convert the whole app to another framework.
- Main navigation: Map, Alerts, Cases/Reports, Ocean conditions, Spill scenarios, Settings. Vessel/unknown-detection detail opens from map or alerts. Landing material must describe implemented capabilities accurately.
- Map: layer controls, AOI/time selector, coverage/freshness strip, attention list, selected-object panel and working time scrubber. Changing time must affect actual queries/layers.
- Alerts: New, Watch, In review, Closed with filters and bulk assignment only where supported. Show report approval and delivery as separate badges. Avoid calling weather “explained” when it is only a hypothesis.
- Evidence: linked timeline, map, plots, sources and encounter graph. Reports: draft preview, source validation, version history, approval and delivery controls.
- Ocean page: historical versus forecast dates, units, product age and baseline evaluation. Spill page: input panel, job state, time steps and affected-area list.
- Cover loading, empty, error, offline, stale, no-permission and partial-data states on every page. Support keyboard navigation, visible focus, readable contrast and state labels in addition to colour. Replace “confirmed signature” colours with terms that do not imply confirmed illegality.
- Done: test at 1366×768 and 1920×1080; tablet layout remains usable; no essential operation relies solely on colour, hover or a tiny map marker.

### F14. Evaluation and reproducibility — required

- Version fixtures, input manifests, source permissions, model/rule versions and expected outputs. Keep synthetic tests separate from real-data evaluation.
- Provide one repeatable demo script: suspicious track → corroborating observation → weather/coverage review → encounter evidence → report → authenticated approval → export. Use a second story for harmless weather/sparse coverage and a third for a spill.
- Include a model/data card for each forecast or detector actually exposed. Record where it fails and its evaluation region.
- Done: another teammate can recreate the demonstration and evaluation from the documentation without undocumented manual database edits.

## 5. APIs, datasets and libraries

Free hosted access, open data and open-source software are different things. Record each resource's terms and permitted redistribution. Do not put paid access on the critical path. Detailed checks and source links are in [PLAN_RESEARCH.md](PLAN_RESEARCH.md); access can change.

| Resource | Use | Access, limits and fallback | Phase owner |
|---|---|---|---|
| [AISStream](https://aisstream.io/) | Live AIS within AOI | Account/key; server-side WebSocket; test actual Indian coverage. Use permitted replay/import if sparse; label it recorded | A, P1–P2 |
| [GFW APIs](https://globalfishingwatch.org/our-apis/documentation/) | Activity, vessel/encounter context, permitted SAR detections | Token; documented non-commercial use. Verify dataset IDs, resolution, latency and export rights. No assumption of point-level/live access | A, P1–P3 |
| [Copernicus Data Space Sentinel-1](https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-1) | Scene discovery, metadata and bounded SAR samples | Free/open mission data with service registration/quotas. Query AOI/date/size first; imagery is optional when external detections suffice | A/C, P3 |
| [Ai2 SAR detector](https://github.com/allenai/sar_vessel_detect) | Optional local pretrained inference | Separate environment and preprocessing; pin code/weights/checksum and verify both licences. Not compatible with arbitrary YOLO weights | A/C, P3 |
| [xView3](https://iuu.xview.us/) | Optional labelled SAR benchmark | Registration; user-reported training ~1.3 TB, validation ~123.1 GB and 2 TB recommended space. Do not download either full split. Check scene size, labels AND overlap with the pretrained model's training data | A/C, P3 |
| [Open-Meteo Marine](https://open-meteo.com/en/docs/marine-weather-api) and weather API | Wind/wave context | Free hosted endpoint is non-commercial and quota-limited; cache. Verify historical coverage for each event. Use cached valid data or unknown, never fabricated calm weather | A, P2–P3 |
| [Copernicus Marine](https://data.marine.copernicus.eu/products) | SST, chlorophyll and currents | Register as needed; choose products covering Indian waters and required dates. Record exact dataset/version/variables/units. Regional subsets only | A/C, P1/P3–P4 |
| [GFW activity datasets](https://globalfishingwatch.org/datasets-and-code/) | Historical fishing-effort proxy | Match spatial/time resolution and publication delay. Effort is not a crime label. If access is blocked, forecast evaluation stays blocked | A/C, P3–P4 |
| [Protected Planet](https://www.protectedplanet.net/en/legal) plus official Indian sources | Boundary context and restriction verification | Public terms restrict commercial use and redistribution. Verify permissions and exact local restrictions before real deployment. Ship demo polygons only when real-data packaging rights are missing | A, P1/P3 |
| [NOAA GNOME/PyGNOME](https://response.restoration.noaa.gov/oil-and-chemical-spills/oil-spills/response-tools/gnome-suite-oil-spill-modeling.html) | Spill trajectories | Open modelling tools; pin engine and dependencies in an isolated worker image. Needs compatible wind/current/coastline inputs; integration spike early | A/C, P1/P4 |
| [MapLibre](https://maplibre.org/) + [PMTiles](https://docs.protomaps.com/pmtiles/) + licensed regional OSM-derived tiles | Online/local map | Library licence does not grant basemap redistribution rights. Preserve attribution and verify tile source; do not bulk-download public OSM tile servers | B, P4 |
| PostgreSQL/PostGIS, FastAPI, Celery, Redis, React/Vite | Main application stack | Keep current working stack, lock versions and review licences. No new graph/vector database needed; encounters fit the existing database | A/B, all |
| scikit-learn and xarray | Simple ranker and regional ocean-data processing | Pin only needed dependencies. Use interpretable baselines before complex models; keep data transforms reusable | A/C, P3–P4 |
| Cytoscape.js; existing SVG/chart tooling | Encounter graph and plots | B chooses one graph library and one small plotting approach; avoid adding several chart systems | B, P3 |
| Optional local model runtime, e.g. Ollama | Wording suggestions | Select exact model and runtime after hardware/licence check; benchmark memory and output. Template reports remain the required default | A, P4 |
| Optional SMTP relay; local test mail sink | Explicitly approved report delivery | Credentials and recipient allowlist required; no assumed free provider or external send during tests | A/B, P4–P5 |

### Data access checklist due 4 November

Create docs/DATA_MANIFEST.md with one entry per selected dataset: provider URL, exact product/dataset ID, version, licence, account owner, secret variable name (no value), allowed uses, export restrictions, AOI, date range, variables, units, resolution, expected delay, requested byte limit, retention and fallback. Store one permitted response fixture for each required adapter. If a provider is inaccessible, record the blocker and affected acceptance criterion that day.

### Storage and spending limits

- C: had approximately 104 GB free on 1 November; recheck before downloads. Reserve at least 40 GB free on the host. Check Docker's available storage separately.
- Initial total project data budget: 20 GB across database, scenes, tiles, models, caches and exports. Allocate at most 5 GB to raw SAR samples and 5 GB to ocean/effort history initially. These are plan limits, not source-size estimates.
- Inspect compressed AND expected extracted size before obtaining a scene. Stream/subset where supported. If the smallest useful scene exceeds the budget, use external detections and record local-model evaluation as blocked.
- Keep active-case evidence and backups out of automatic cache eviction. Evict only regenerable cache objects according to a documented policy; never delete unknown user files or database volumes to make space.
- Target zero paid API subscriptions for the non-commercial pilot. Budget target for an optional remote demo host: at most INR 3,000/month, subject to an actual quote and team choice. This is a spending cap, not verified hosting pricing. Start locally; do not purchase services as part of this plan.
- Public/commercial launch requires a separate provider-rights and hosting decision. Free-tier terms may not allow that use. Use licences to determine what can be exported, shared or retained.

## 6. Architecture and shared contracts

Keep one React app, one FastAPI app and one PostGIS database. Use Redis/Celery for background work and one scheduler. The data flow is:

**Provider/import → validated source records → normalised observations → evidence/risk jobs → stable alerts → cases → immutable report revisions → approved export/delivery.**

Heavy optional SAR or GNOME dependencies may use dedicated worker images on the same job queue. Avoid loading every model into the API process. Do not introduce a second orchestrator, graph database, vector database or separate microservice for each feature.

### Logical records to define before coding

These are design requirements, not a ready-to-run database migration. A owns actual schema design and migrations. Reuse existing records where safe.

| Record group | Required purpose |
|---|---|
| Users, roles and sessions | Identity, permissions and revocation |
| Sources, ingestion runs and source records | Provenance, checkpoints, rights, status and deduplication |
| AIS observations, zones/rules and version references | Time-based evidence and verified spatial context |
| SAR detections and candidate associations | Multiple candidates, match method/version, ambiguity and unknown identity |
| Alerts and alert events | Stable identity, score version, evidence references, assignments and lifecycle |
| Cases, notes and evidence links | Vessel and non-vessel investigation; preserve authored history |
| Report revisions, approvals, audit events and delivery outbox | Immutable snapshots, independent approval, integrity and idempotent delivery |
| Environmental samples, forecast runs and evaluations | Time/availability-aware inputs, baselines and reproducible metrics |
| Spill jobs and outputs | Scenario inputs, engine version, forcing references and output manifests |

Use UTC-aware timestamps and WGS84 coordinates at API boundaries; display IST or a selected timezone with a label. Keep observation, publication and ingestion times separate. Use metres for distance, knots for vessel speed and explicit units for environmental values. GeoJSON uses longitude then latitude.

For new local relational records, prefer identity keys and explicit foreign keys. Plan indexes from actual time, vessel and spatial queries. Keep migrations ordered with one owner. Use a limited application database role; migrations use a separate role. Preserve report-linked evidence during retention. No TimescaleDB or partitioning is required until measurements justify it. The Postgres skill's guidance informs these constraints; developers must review its relevant rules before writing migrations.

### Contract freeze due 4 November

A writes docs/contracts/openapi-v1.json from the agreed API design and docs/contracts/examples/ with small synthetic responses. B builds against those examples. Existing endpoints remain compatible until both callers and tests migrate. Label every new route below **planned** until implemented.

| API group | Existing starting point | Contract to add/fix |
|---|---|---|
| Authentication | None | Login/logout/current-user, roles, session expiry and consistent 401/403 |
| Tracking | /api/v1/vessels/ and /ingest/ais | AOI/time/pagination, source/freshness, idempotent ingestion and errors |
| Alerts | /api/v1/alerts/ | Stable IDs, one engine, lifecycle updates, assignments and event history |
| Evidence | /vessels/{mmsi}, /sar/detections, /weather/{mmsi} | Detection detail without MMSI, source lookup, association candidates and encounter graph |
| Cases/reports | /reports/ and /reports/{id}/sign | Case identity, revisions, source validation, authenticated approval, export and delivery |
| Environment | None for real hotspots | Layer queries, forecast runs, evaluation summaries and scan recommendations |
| Spills | Placeholder UI | Create job, status, cancel and bounded GeoJSON results |
| Operations | /health | Readiness, source health, jobs and permission-protected settings |

All list APIs need bounded pagination and a consistent empty response. All jobs return an ID and explicit state. Mutations that may be retried need idempotency or version checks. Source errors use a consistent code, safe message, retryability flag and request ID. Distinguish unknown from false and missing from zero.

## 7. Two-person split with minimal overlap

Assign names to A and B on 2 November. The optional C owns evaluation/data preparation only. No task has two implementation owners.

| Owner | Exclusive write areas | Responsibility |
|---|---|---|
| A: backend/data/integration | apps/api/**, infra/**, docs/contracts/**, docs/DATA_MANIFEST.md | APIs, authentication, migrations, provider adapters, workers, deployment, final integration |
| B: interface/workflows | apps/web/**, docs/design/**, browser tests under apps/web, docs/demo/** | Screens, state handling, charts/maps, browser workflow tests, recorded demo and user guide |
| C, optional: evaluation | ml/**, docs/evaluation/**, data-preparation scripts inside ml | Pure transforms, reference scenarios, labelled benchmarks and metric reports; no API/database/frontend changes |
| Shared documentation, one editor | This plan and README.md | A integrates agreed updates; B/C submit text in their task notes |

With two people, A owns C's small baseline/adapter tasks and B runs recorded-case evaluation using existing screens. With three, transfer those exact tasks to C; keep deadlines and scope unchanged. C hands A a versioned input/output file or pure function, never an unreviewed schema change.

Working rules:

1. Start from the same reviewed base commit. Inspect the dirty worktree and preserve user work; record the baseline before splitting. Do not reset files to make branches clean.
2. Use separate local worktrees/clones and branches for A/B/C. Each has its own test database and ports. Do not share the running development database for destructive tests.
3. Keep one owner for main.py, config.py, requirements, Compose, migrations and API contracts: A. B alone edits App.jsx, api.js, package files and frontend lockfiles.
4. By 4 November, agree payload examples, enums, units, errors and empty states. B can finish screens against mock responses while A builds the endpoints.
5. Contract changes are additive within a phase. A writes the changed example first; B acknowledges before the old field is removed. Use a small adapter for a legacy field rather than an unrelated refactor.
6. Integrate working vertical slices by 17:00 each workday; run the relevant checks after merge. Spend at most 15 minutes on a blocker/contract review. A controls the integration branch; use the team's existing review process for remote merges.
7. Never add a shared dependency or rename a common folder from two branches. Record the owning task and ask the file owner to make the edit.

## 8. Strict phase schedule

### Accelerated judging sprint: 3–10 November

**This section supersedes the original P1/P2 task allocation and their 10 November gate below.** It pulls the smallest useful real-data portions of P3 and P4 forward. The detailed P3/P4 lists remain the definition of their complete phases; do not count a demonstration slice as completion of those lists. Keep a task ledger and subtract any work completed during this sprint from the later tasks.

Capacity from 3 through 10 November is six weekdays, or 36 focused hours per person at six hours per day: **72 person-hours for two people**. That assumes work starts on 3 November and neither person has other commitments; reduce the hours and scope if that is not true. A third person adds up to 36 hours only if actually available. The full original P1–P4 workload is 230 planned person-hours, so completing all of it by 10 November would require at least 39 hours per day across six weekdays, before contingency. Do not promise full phase completion on this schedule. The 10 November outcome is a narrower, working demonstration; the full v1 feature and validation gates are unchanged.

**The minimum real-data story:** show a selected Gulf of Mannar area, a permitted real marine environmental observation and a real vessel track or event, then review an explainable risk signal and export a sourced evidence record. The environmental data and vessel event need not be simultaneous, but show their dates and avoid implying a causal relationship. Historical, recorded or cached real data is acceptable and must be labelled. A protected-area overlay is useful only with verified provenance and permission; presence alone is not proof of an offence. Explain how better monitoring could support marine ecosystem resilience; do not claim measured emissions reductions or prevented fishing without evidence.

| Deadline | A: backend, data and integration (36 h total) | B: interface and judging evidence (36 h total) |
|---|---|---|
| **4 Nov, 18:00** | **9 h:** check repository/dirty state and runtime; confirm available AIS or permitted historical track, one regional SST/chlorophyll product and licence; obtain a small real subset with dates, units, bounds and attribution. Test access to point-level SAR and GNOME without a large download. Record blockers and size. | **9 h:** test existing end-to-end journey; agree response examples with A; show data mode, timestamps, provenance and unavailable states; draft the problem statement and video storyboard. |
| **6 Nov, 18:00** | **12 h:** connect the real vessel record and environmental subset through a bounded import or adapter; deduplicate and preserve provenance; reuse the existing risk engine and report flow. Make alert identity and scores consistent for the chosen story. Cache weather if available. | **12 h:** display the real environmental layer or a dated regional value on the map and link it to the selected vessel/evidence view. Show rule factors and data limitations. Connect to the real API and exercise the journey. |
| **9 Nov, 18:00** | **10 h:** deliver the best available additional real capability in priority order: permitted point-level SAR association, then a simple environmental/activity baseline, then a bounded GNOME scenario with valid forcing. Only expose a capability that runs with real inputs and passes a reference check. Support a source-linked export and basic access controls appropriate to the demonstration. | **10 h:** complete the climate-centred walkthrough and source-linked report/export UI; test missing sources and real-data replay. Measure review time and evidence completeness on available cases, recording sample size and limits. Record a draft video using actual screens. |
| **10 Nov, 18:00** | **5 h:** integrate, rerun the prepared dataset and basic API checks, record data provenance, resource use and outstanding blockers. | **5 h:** run the full journey on the prepared setup, fix presentation issues, finalise video and evidence pack, and rehearse the judging explanation. |

If a third person is available, C exclusively owns bounded data preparation and evaluation under `ml/**` and `docs/evaluation/**`: obtain and document permitted SAR points or ocean subsets, run the GNOME reference spike, and hand A a versioned file or pure function. C must not edit API, database or frontend files. C's availability does not remove the access, reference-check or evidence requirements.

**Decision points and fallback:**

1. By 4 November, record an actual accessible source, sample, licence and download size for the vessel and ocean datasets. If a source is blocked, switch to a permitted historical export or a different permitted regional product. A real cached observation is preferable to a simulated live feed. If no permitted real source is obtainable by 6 November, explicitly mark that part unavailable; synthetic data may be used only if labelled and the team chooses to include it.
2. By 6 November, freeze the main story and contracts. Prioritise the complete vessel → evidence → environmental context → export journey. Defer advanced lifecycle controls, PDF if sourced JSON export works, optional model training, extra regions and visual polish before dropping data provenance or truthful labels.
3. By 9 November, stop adding integrations. SAR requires genuine point detections with permission and acquisition time; gridded cells are not vessel points. A hotspot requires a real input and a clearly described baseline; a descriptive ocean layer is not a prediction. GNOME requires a working engine, appropriate forcing and a reference check. If any is blocked, show it as planned or unavailable, not as a working capability.
4. On 10 November, submit an honest video even if an integration fails. State whether each source is live, historical, cached or synthetic; identify the rule-based risk engine as such, and describe any trained AI model only if actually used. Report measured review time and feasibility with sample size, and describe climate impact as an expected pathway rather than an observed outcome. No full xView3 download is needed.

**Judging gate, 10 November:** a fresh prepared setup reproduces the real-data story, shows source dates/attribution and missing-data states, and exports a traceable record. The video explains the climate problem, the actual analytical method, implementation, expected impact, feasibility and evidence. Record which optional SAR, baseline and spill slices actually ran. If a required real source or the end-to-end journey is unavailable, report the limitation and submit the best accurately labelled demonstration; do not claim the gate passed.

### Full product schedule

The table below retains the full-product target dates. Original P1/P2 hours describe the earlier plan and are replaced by the accelerated allocation above. P3/P4 hours are original estimates before subtracting work delivered in the sprint; re-estimate remaining tasks on 11 November. The six-week 360-hour figure is the original capacity assumption from 2 November, not extra capacity on top of the 72 hours above. Estimates assume reused components and small baselines; external access and model performance are not guaranteed.

| Phase | Dates | Deadline | Planned A / B hours | Required delivered chunk |
|---|---|---|---:|---|
| P1 Foundation and access | 3–4 Nov | 4 Nov, 18:00 | See sprint | Source access, contracts and real-data story selected |
| P2 Judging demonstration | 5–10 Nov | 10 Nov, 18:00 | See sprint | Real vessel and ocean context → explainable evidence → sourced export |
| P3 Real evidence and triage | 11–20 Nov | 20 Nov, 18:00 | 40 / 40 | Provider pipeline, SAR association, weather/coverage triage, encounter graph, environmental input pipeline |
| P4 Complete remaining product | 23 Nov–2 Dec | 2 Dec, 18:00 | 40 / 40 | Hotspots/scan budget, spills, offline operation, delivery and source settings |
| P5 Release and handover | 3–11 Dec | 11 Dec, 18:00 | 35 / 35 | Validated, documented, reproducible and packaged v1 |

Weekends are not assumed working days. Internal tasks finish before their phase gate. If a required gate fails, record the failed requirement and recovery owner. Keep the date as the review date; do not relabel a limited demonstration “full v1”. Use reserve time and remove optional work first.

### P1 — foundation, access and contracts

The following original tasks are the full foundation backlog. For 3–10 November, use the accelerated allocation above; unfinished tasks carry forward and must be completed before the relevant full-v1 gate.

Dependencies: current repository and Docker available.

**A tasks, 15 hours:**

- P1-A1 (3 h): inspect git status/remotes; fetch remote metadata and compare current branch with its upstream; review divergence before merging. Record baseline commit and dirty files. Run existing tests/build against disposable data. Check disk/RAM/GPU availability. Audit exposed ports and known leaked-key references; create a rotation checklist without printing secrets.
- P1-A2 (4 h): verify AIS/GFW access, one ocean product subset and boundary rights; create the data manifest. Run a bounded GNOME install/reference smoke test early. Record exact blockers and size estimates. Do not spend the whole phase waiting for credentials.
- P1-A3 (5 h): define contracts and role matrix; implement local session/role foundation and lock down mutation routes. Use a maintained auth approach with tests. Add data-mode/source fields to the contract.
- P1-A4 (3 h): define the shared alert/case/evidence model, migration order and fixture boundary; record how the legacy alert route will converge on the risk engine.

**B tasks, 15 hours:**

- P1-B1 (3 h): compare current screens with signed-off mockups; inventory missing interactions and split Cases.jsx into owned page/components as needed without changing API semantics.
- P1-B2 (5 h): add login/session UI, role-aware navigation, global live/replay/offline banner and consistent loading/error/empty components.
- P1-B3 (5 h): build mock-backed alert board, case shell and planned detail routes, including unmatched SAR objects. Agree component states from contract examples.
- P1-B4 (2 h): establish browser smoke tests and viewport checks; update the screen checklist.

**Gate:** contracts and owners assigned; authenticated read/write permissions demonstrated; source access/unknowns documented; one permitted fixture per available source; no paid subscription or large download required. Missing credentials remain explicit blockers for real-data gates, even when mocks unblock UI work.

### P2 — complete the core 10 November demonstration

The following original tasks are retained as the full core-workflow backlog. The accelerated judging gate above replaces this section's original gate and hours; authenticated approval and immutable revisions remain required for full v1 even if they cannot be completed for the demo.

Dependencies: P1 contracts and auth. Prioritise the full journey over cosmetic completeness.

**A tasks, 20 hours:**

- P2-A1 (6 h): make imports idempotent and persist stable alerts from the existing risk engine; route map/board/report data through one assessment. Add event/source references and server-side lifecycle checks.
- P2-A2 (7 h): bind report facts to snapshots; add authenticated approval, immutable revisions and basic PDF/JSON export. Test missing facts, tamper detection, permissions and concurrent revision rejection.
- P2-A3 (5 h): wire one available AIS feed or explicit recorded import, weather caching and permitted SAR fixture import. Include source age and unknown coverage in outputs.
- P2-A4 (2 h): prepare repeatable, isolated demo setup and fix integrated API issues. No silent replacement of live records by the seed script.

**B tasks, 20 hours:**

- P2-B1 (6 h): connect map/search/time filters and stable alert board; add assignment and Watch/reopen controls allowed by the API.
- P2-B2 (7 h): complete linked evidence view and report preview/source validation/approval/export journey.
- P2-B3 (4 h): add visible source/time/mode labels and missing-SAR/weather states; test the entire journey with the real API.
- P2-B4 (3 h): record an honest demonstration and retain the script and evidence manifest. Mark synthetic story elements and features still planned.

**Full core-workflow gate:** a fresh prepared setup completes the journey from observation to approved export. Report sign-off uses a logged-in user. Map and alert scores match. Track any gap against this gate after the judging demo.

### P3 — trustworthy data and investigation

Dependencies: P2 evidence IDs and lifecycle; provider access from P1. B uses fixtures until each endpoint lands.

**A tasks, 40 hours:**

- P3-A1 (9 h): productionise AIS/GFW adapters: schema validation, AOI filters, pagination, retries, rate limits, checkpoints, deduplication and source/job status. Record observed provider latency and coverage.
- P3-A2 (8 h): import permitted real SAR detections, preserve provider provenance and implement candidate/ambiguous/unmatched associations. Evaluate against known matches; do not turn aggregate data into points.
- P3-A3 (8 h): add versioned weather/coverage recommendations, event-state history and encounter graph query. Test storms, outages, sparse tracks and late corrections.
- P3-A4 (8 h): load permitted boundaries/rules and a small ocean/effort dataset. Implement pure time-aligned transforms and baseline evaluation inputs. Verify no future-data leakage.
- P3-A5 (7 h): add job tests and source health; run a tightly bounded optional local SAR feasibility benchmark only if required tasks are on schedule. If absent, use this time to complete evaluation and provider integration.

**B tasks, 40 hours:**

- P3-B1 (10 h): evidence timeline and encounter graph, with edge inspection and source drill-down.
- P3-B2 (8 h): SAR layer/detail, unknown-vessel cases, ambiguity display and crop/footprint fallback.
- P3-B3 (8 h): triage recommendations, coverage/freshness indicators and full alert lifecycle controls.
- P3-B4 (8 h): source status/settings and ocean-layer screens against frozen examples.
- P3-B5 (6 h): reviewer scenarios, keyboard testing and integrated bug fixes.

**Gate:** permitted real records can be traced through import → alert → report. Unmatched SAR can be investigated without a vessel identity. Provider errors and missing data stay visible. Evaluation data is separated from synthetic demo fixtures. Ocean inputs and reference spill environment are ready for P4.

### P4 — forecasting, scenarios, offline use and delivery

Dependencies: P3 source pipelines, provenance, auth and job infrastructure. Freeze new feature scope after this phase.

**A tasks, 40 hours:**

- P4-A1 (10 h): implement environmental/activity baselines, rolling backtest and budgeted scene recommendations; return factors, uncertainty/availability and comparison metrics. Add a learned ranker only if baseline/evaluation work is complete.
- P4-A2 (12 h): integrate GNOME worker, bounded scenario contracts, forcing preparation, reference checks and 6/12/24-hour outputs. If the P1 GNOME spike failed, prioritise fixing that documented blocker; a toy polygon is not the substitute for this feature.
- P4-A3 (9 h): finish evidence manifest verification, append-only application history, retention safeguards and optional delivery outbox; keep tests pointed at a local mail sink.
- P4-A4 (9 h): add scheduler/checkpoints, production/offline Compose profiles, cached-data loading and reconnect handling. Evaluate optional local wording suggestions only after required workflows pass.

**B tasks, 40 hours:**

- P4-B1 (10 h): finish ocean-condition/hotspot page, forecast-vs-observation labels, factors and scan-budget controls.
- P4-B2 (12 h): finish spill scenario input, job status/cancellation, scrubber, extents and affected-area display.
- P4-B3 (10 h): regional offline basemap/assets and offline state behaviour; ensure cached queries and report work survive network loss.
- P4-B4 (8 h): finish recipient/delivery settings, source configuration and workflow polish. Remove or hide all unimplemented legacy features from release navigation.

**Gate:** F01–F14 outcomes are implemented and reachable; all remaining work is verification/defects/documentation. A prepared offline system completes a case. A spill scenario runs through the UI. A hotspot backtest and baseline comparison exist. Failed empirical claims remain labelled experimental; a missing required workflow prevents feature-complete status.

### P5 — release validation and handover

Dependencies: P4 candidate. Use reserve for defects; no new modelling framework or provider.

**A tasks, 35 hours:**

- P5-A1 (10 h): isolated integration suite for permissions, imports, retries, report integrity/versioning, outbox and jobs. Close exposure of default credentials, development reload, permissive CORS and unnecessary host ports in the release profile. Confirm owner-managed rotation of previously leaked credentials.
- P5-A2 (10 h): run load/resource benchmarks, database query review, worker failure/recovery and backup/restore drill. Keep evidence manifests with results.
- P5-A3 (9 h): pin runtime images/dependencies/models, write installation/upgrade/rollback guide and package regional/offline assets with licence notices. Build from a clean checkout plus approved configuration.
- P5-A4 (6 h): final review, release notes and handover of remaining limitations; prepare version/tag/merge artefacts using the team's approval process.

**B tasks, 35 hours:**

- P5-B1 (12 h): browser tests covering real and replay modes, failures, permissions, offline use, all screen sizes and keyboard navigation.
- P5-B2 (8 h): two-reviewer usability evaluation, timing/mistake report and fixes.
- P5-B3 (9 h): user guide, source/provenance walkthrough, honest demo video and comparison/evaluation presentation.
- P5-B4 (6 h): verify clean install with A's guide, remove stale screenshots/promises and conduct the final acceptance checklist.

**Gate:** release checklist below is signed by both people. Any missing required feature is listed as an incomplete v1 requirement; only a limited demo may be delivered in that case. Optional model failures do not block v1 if the required tested baseline works.

### Pilot and finale dates

- **8 January 2027, 18:00:** review pilot feedback and recorded measurements, recheck expiring accounts/data permissions, and close release-critical findings. Reserve two person-days within 4–8 January for this review; this is additional maintenance, not extra feature scope hidden inside the 360-hour build.
- **15 January 2027, 18:00:** freeze the presentation/data pack and run an offline dress rehearsal. Reserve one person-day; after this, only release-blocking fixes.
- **20–21 January 2027:** finale dates from README; verify event arrangements independently. Keep a local installation pack, cached demonstration and video available.

## 9. Verification targets and release checklist

These are acceptance targets to test, not results already achieved. Record actual hardware, fixtures, commands, output and failures in docs/evaluation/RELEASE_RESULTS.md. Do not create a passing metric by changing the test data after seeing the result.

| Test area | Required evidence / pass rule |
|---|---|
| Core workflow | Tracking/import → alert → evidence → draft → authenticated approval → export succeeds from documented setup; unknown SAR and spill cases also supported |
| Permissions | Negative tests on every mutation role boundary; expired/revoked sessions rejected; reviewer identity comes from session |
| Imports/jobs | Same batch/scene twice creates no duplicates; out-of-order data handled; interrupted work resumes; rate limits/failures do not crash API |
| Alert consistency | Stable IDs across refresh; identical assessment version on map, board and report; all contributions reconcile to displayed score |
| Evidence/report | Every factual report field has a source or explicit analyst attribution; missing/tampered sources block approval; approved revision cannot be silently edited |
| Weather/coverage | Test at least 30 reviewed scenarios spanning storms, sparse coverage and suspicious behaviour; no automatic closure based only on weather; report reviewer disagreements and false downgrades |
| SAR association | Test at least 30 reviewed detection/candidate cases if permitted data allows, including ambiguous/unmatched cases; report false matches and sample uncertainty; insufficient sample remains an evaluation limitation |
| Own SAR model, if enabled | Scenes unseen during model training and tuning, not random chips or a split merely named validation; precision/recall/F1, tolerance definition, near-shore errors, runtime and hardware; unknown training overlap means smoke test only; no operational accuracy claim from a tiny benchmark |
| Hotspots | Time-separated backtest with availability-aware inputs; report condition MAE and activity captured at a fixed scan/area budget; compare recent-activity, persistence and uniform baselines; keep baseline when no useful gain |
| Spill modelling | Reproducible reference scenario; constant/no-flow sanity checks; valid forcing times and units; engine output integration verified. Matching GNOME when using GNOME is an integration check, not independent physical validation |
| Performance | Target on the documented 16 GB-class workstation: 1 million stored AIS observations and 1,000 displayed latest vessels; p95 cached list/detail API under 2 s for 10 concurrent read clients; interactive map under 3 s after assets load. Record actual dataset/queries and adjust capacity claims to results |
| Ingestion capacity | Target sustained 100 AIS messages/s for 30 min with bounded queues and documented resource use; accepted observations visible within 60 s locally. Provider delivery latency is reported separately |
| Resources | CPU-only core workflow works; normal services target ≤10 GB combined RAM; one heavy job at a time, no OOM; stay within data/free-space limits. Record actual GPU use separately |
| Offline | After provisioning, disable external networking and complete browse → investigate → approve → export using cached data; no hidden CDN/fonts/tiles; reconnect causes no duplicate writes |
| Recovery | Stop worker during job, restart safely; restore backup into separate database and verify cases/hashes. Target daily backup, ≤24 h data loss and ≤60 min restore for the benchmark data volume; measure, do not promise without a drill |
| Delivery | Local mail sink receives only explicitly approved version/recipients, once per delivery key; retry/failure states accurate; external send only when separately authorised by a user |
| UI | All empty/loading/error/stale/offline/forbidden states covered; keyboard and viewport checks pass; no placeholder navigation or unlabelled synthetic evidence |
| Licence/security | No committed secrets or forbidden data bundles; owner confirms leaked-key rotation; auth and host exposure checked; source attributions and limitations included |

Required release artefacts:

- [ ] Working source with reproducible build instructions and reviewed dependency locks.
- [ ] Production and offline Docker profiles; services/volumes explained.
- [ ] Data/source manifest with licences, exact product IDs and configuration names.
- [ ] API contract and representative success/error fixtures.
- [ ] Isolated test setup; unit, integration and browser workflow results.
- [ ] Evaluation report with limitations, baseline comparisons and named hardware.
- [ ] Model/data cards for enabled forecasts/detectors and checksum manifest.
- [ ] Export verifier, backup/restore record and installation/rollback guide.
- [ ] User guide and demo script/video that match the actual release.
- [ ] Known-issues list; no unresolved critical permissions, data-loss or report-integrity defects.

## 10. Blockers and deadline protection

| Trigger | Immediate action | Effect on completion |
|---|---|---|
| API credentials absent by 4 Nov | Build adapter against permitted fixture; owner obtains access while UI work continues | Real-source acceptance remains blocked; fixtures do not count as live integration |
| AIS coverage poor in Gulf of Mannar | Show coverage unknown; use licensed regional replay; evaluate alternate receiver/partner access | Do not claim comprehensive live monitoring or intentional silence |
| GFW only provides aggregate access | Use aggregate layer honestly; obtain permitted point export/provider for SAR cases | Individual SAR feature blocked until actual points exist |
| Boundary/rule rights unclear | Demo-only geometry; add verified source references; obtain permissions | Operational restriction alerts remain unverified |
| GNOME spike fails by 4 Nov | Use isolated supported runtime and reference scenario; escalate within A's P3 work | P4 spill feature remains required; scenario mockups do not satisfy it |
| SAR sample exceeds disk budget | Skip local inference benchmark; retain provider detection workflow | Optional own-model claim deferred; no full xView3 download |
| Weather unavailable at event time | Display unknown and preserve priority | Feature remains functional with tested partial-data handling |
| Hotspot model has no held-out gain | Ship transparent baseline and descriptive environment layer with evaluation | Required ranking workflow can pass; advanced prediction/novelty claim cannot |
| LLM too slow or invents facts | Disable suggestions; use source-bound template | Report feature remains complete |
| Phase workload exceeds capacity | Spend reserve, remove optional own SAR/LLM/learned ranker/extra AOI first | Never cut auth, provenance, uncertainty labels or tests to make a date |
| Required capability cannot finish by 11 Dec | Deliver clearly named limited demo and list missed gates with owners | Full v1 is not complete; team must explicitly re-scope or fund a follow-up |

## 11. Instructions for a developer or coding model

Use this procedure for every task. Do not treat the whole plan as permission to rewrite the repository.

1. Read AGENTS.md and this plan. Identify your task ID, feature IDs, owner, deadline and write paths. Check git status and preserve existing changes.
2. Use CodeGraph context for structural questions, then a focused explore call if needed. Read literal configs/docs directly. Do not infer implementation from a mockup or roadmap.
3. Read the agreed API contract and example payload before editing. If a required dependency is missing, implement against the frozen fixture in your own area and record the integration blocker.
4. State the small outcome and acceptance check. Make only the owned changes. Use maintained packages already present where possible; avoid unrelated refactors or framework migrations.
5. Keep all secrets out of code, logs, screenshots and examples. Put configuration names with placeholders in .env.example. Distinguish real, recorded and synthetic data in every new path.
6. A alone adds/changes database migrations. Before database work, read the Postgres skill and relevant rules. Test upgrades on a disposable database and preserve current data; never use a volume reset as the upgrade procedure.
7. Add meaningful tests for changed behaviour: success, invalid input, missing data and relevant permissions. Provider tests use deterministic fixtures; optional live checks must not be required for every test run.
8. Run the existing backend tests and frontend build when relevant. New database tests must use a migrated disposable TEST_DATABASE_URL; a skipped integration test is not a pass. Add browser workflow commands to the guide when their framework is introduced.
9. Record changed files, checks/results, limitations and contract changes. Mark a task complete only when its API/UI path and acceptance check work together. A screenshot alone is not a functional test.
10. Request owner review for shared files/contracts. Do not send external reports, purchase services, bulk-download datasets, publish a deployment or merge remote branches merely because it appears in this planning document.

Suggested task handoff format:

~~~text
Task: P3-B2 / F05
Owner: B
Write paths: apps/web/src/features/sar/** and B-owned route/API client files
Depends on: frozen SAR detail and association contract from A
Outcome: inspect matched, ambiguous and unmatched SAR evidence in the UI
Inputs: docs/contracts/examples/sar-*.json
Steps: add layer; add detail view; connect source panel; wire real endpoint
Must handle: no crop, unknown identity, stale source, failed request, no permission
Done when: each fixture and real integration path passes the UI acceptance checks
Report: changed files, checks run, screenshots if useful, remaining blocker
~~~

Baseline verification commands from the repository root (PowerShell):

~~~powershell
git status --short
docker compose -f infra/docker-compose.yml ps
docker exec -w /app samudrasense_backend python -m pytest tests
docker exec -w /app samudrasense_frontend npm run build
git diff --check
~~~

These commands assume the containers have the declared development/test dependencies installed. Install missing dependencies from the repository's requirement/lock files in the development or test environment, not an operational deployment. The current database integration test skips when TEST_DATABASE_URL is unset. P1-A1 must document a disposable migrated test database with the required synthetic seed and set that variable for the integration run. Do not point it at the live development database. P1-B4 must add the exact browser-test command after choosing the test runner. Save exit codes and skipped-test counts with the task record.

## 12. Documents to reconcile during implementation

This plan defines delivery scope when it conflicts with older roadmap proposals. Preserve the product's Predict/Detect/Act intent while correcting unsupported implementation claims.

- README.md: separate working features, experimental measurements and future ideas; replace automatic storm/illegality claims with the tested review policy; update actual dates and deployment instructions. Replace the old database-reset advice with a tested migration/backup path.
- docs/design/DESIGN.md: keep visual tokens; update lifecycle labels, evidence uncertainty, source states and completed screens.
- docs/LOW_COST_DATA.md: retain as background; link verified resource decisions to DATA_MANIFEST.md and the research appendix.
- services/README.md: mark the BullMQ/C++ rewrite deferred; explain current Celery workers/scheduler.
- ml/README.md: describe the exact baseline/model artefacts used, dataset limits and evaluation commands.
- apps/api/docs/MIA_V3_GUIDE.md: audit claims against actual supported code; remove unverified model/version, latency and “reasoning trace” promises. Prefer factual source citations and brief explanations. Do not make chatbot upgrades part of the critical path.

The plan is complete as a work specification. Implementation progress starts with the verified baseline above; all new phase tasks are pending until their acceptance evidence is recorded.
