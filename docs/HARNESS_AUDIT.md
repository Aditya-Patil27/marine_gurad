# Shared harness repository audit

Audit date: 4 November 2026. Assignment scope: documentation, instructions, skills and delegation setup only. No new product feature, database migration, provider acquisition, commit or push in this assignment.

## Evidence and preserved baseline

- Branch `ap`, HEAD and locally stored `origin/ap` both `1294148` (`Add product delivery plan and investigation prototype`). Recent commits also include demo-video merge `c93a77b`, README video `be7511d`, compressed video `5aa7d3c` and frontend merge `7322d08`. No remote fetch in this audit; this is not a statement that GitHub has no newer commits.
- Pre-existing modified tracked files: `.gitignore`, `README.md`, `apps/api/.env.example`, `apps/api/app/api/reports.py`, `apps/api/app/config.py`, `apps/api/app/main.py`, `apps/api/app/supabase_client.py`, `apps/api/requirements.txt`, `infra/.env.example`.
- Pre-existing untracked work: `.agents/` (Supabase skills), `.codegraph/`, `skills-lock.json`; API `api/{aisstream,gfw,ocean}.py`; `requirements-copernicus.txt`; scripts `fetch_copernicus_sst.py`, `prepare_copernicus_sst.py`; tests `test_aisstream.py`, `test_copernicus_sst.py`, `test_gfw.py`, `test_ocean.py`, `test_report_ocean_context.py`; `docs/DATA_MANIFEST.md`, `docs/USER_A_PROGRESS.md`, `docs/contracts/USER_A_DATA_API.md`.
- Ignored local Copernicus files exist: NetCDF **36,234 bytes**, prepared JSON **3,994 bytes**. Prior log's 14.08 KB is the provider's estimated subset size, not actual on-disk NetCDF bytes. Do not use it as a measured download/file size.
- A content-hash baseline was captured before harness edits for 169 existing nonignored files. Final review compares it to ensure application code/tests/infra and existing skills survive unchanged. `.codegraph` watcher state can change independently; it is not source implementation.
- Docker read-only `ps` showed backend/frontend/Celery running and PostGIS/Redis healthy. No services restarted or configured here. No live providers queried or old application checks repeated.

## Documents audited and retained

README; product plan including F01–F14, allocation, sprint/full schedule and release gates; PLAN_RESEARCH; LOW_COST_DATA; USER_A_PROGRESS; DATA_MANIFEST; USER_A_DATA_API; design specification and its sample-data status; MIA_V3_GUIDE; services/ML READMEs; existing skill locations and Git changes. Root AGENTS.md and the proposed root harness documents were absent before this task. The user's supplied CodeGraph rules are carried into the new shared AGENTS.md.

The detailed product plan/research, data manifest, API handoff and implementation log remain authoritative for their respective purposes. Root PLAN is a short execution map, not another feature spec. Root PROGRESS is the single current-state pointer; USER_A_PROGRESS retains historical implementation evidence. No separate DATASETS.md was created because it would duplicate DATA_MANIFEST.

## Actual implementation versus older claims

| Finding | Source evidence | Consequence / action |
|---|---|---|
| Legacy alert IDs change on read; two assessment paths | `api/alerts.py` uses UUID and `AlertGenerator`; `services/fleet.py` uses additive risk engine; React Cases reads vessels API | Stable persistence/assessment convergence still required; do not call alert lifecycle complete |
| Report sign-off has no authenticated actor | `api/reports.py` accepts officer string; `main.py` has no auth router/dependency | Local sessions/roles first, then route enforcement and revisions; checksum is not approval identity |
| New real sources are separate from the UI/core case flow | `api/gfw.py`, `ocean.py`, `aisstream.py` registered; frontend `lib/api.js` has no clients for them | Backend slice implemented, B integration and source-linked cases pending |
| Dataset subset exists but not in checkout | Ignored local NetCDF/JSON; `ocean.py` fixed file reader; separate toolbox requirements/scripts | Fresh setup must acquire/prepare it; no automatic refresh; actual size correction recorded |
| SAR importer is a candidate matcher, not trained detection | `api/sar.py`, migrations 004/005 | Real points, provenance, ambiguity and evaluation still missing |
| Model/ML documentation overstates readiness | Missing committed validated weights; MIA guide examples differ from configured chatbot; no hotspot/GNOME pipeline | Mark historical claims; do not infer forecast/AI accuracy from code presence |
| Offline and new-services claims conflict with retained plan | Current Compose has Celery, network adapters/maps/Gemini; old services README proposed BullMQ/C++ | Correct roadmap/README; retain Celery; offline gate remains pending |
| Pollution worker can make fallback geometry | `tasks/celery_app.py` missing-georeferencing branches | Explicit release blocker; no feature fix during harness assignment |
| Tests are not a universal green baseline | Existing integration test requires disposable TEST_DATABASE_URL; prior focused checks only | Record exact scoped evidence; skip is not pass; do not rerun/destructively seed the shared database |
| Shared contract freeze incomplete | Only USER_A_DATA_API prose exists under contracts; no full frozen OpenAPI/examples | New auth/source/case contracts must be authored per task; B handoff explicit |

The current judging slice is a real historical event with independent regional SST and sourced JSON export. It is not yet authenticated, end-to-end in the UI, a climate prediction, a full case lifecycle or full P3/P4. The next logical dependency is **A-001 local auth/session/role foundation**, then route-level permissions, stable provenance/alerts and case/report integration. User B can independently connect the already documented data endpoints in B's workspace.

## Harness validation record

Installed versions and primary-source references are recorded in `AGENT_HARNESS.md`. The harness uses root AGENTS.md, four skills under the platforms' shared `.agents/skills` convention, one current task and a task template/archive. CLI model selector is explicit; no OpenCode/Firecrawl/CodeGraph configuration was changed.

Final checks and CLI dry handoff outcome are recorded in `tasks/H-001.md`. The validation task is read-only and must not start A-001. New skill discovery/brief comprehension is the integration under test, not a repeated test of configured Firecrawl or CodeGraph. The four skills are present in the running OpenCode catalogue. A complete model response remains blocked by provider HTTP 503; the smoke session was interrupted and confirmed inactive. Do not archive H-001 as completed until that remaining check passes.
