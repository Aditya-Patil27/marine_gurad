# SamudraSense

**Climate-aware AI for ocean protection.** *Samudra* is Sanskrit for ocean.

SamudraSense predicts which waters are at risk, catches vessels that hide from tracking, and turns the evidence into reports that an officer signs off. It is designed to run offline on a single workstation.

Built by **Team Code4Seas** (Adish Nair, Aditya Patil, Aditya Saraf) for **Indradhanu IGC 2026**, track *AI for Climate Change: Ocean & Marine Protection*. It grows out of our earlier platform, BlueGuard.

> **Status (Sep 2026):** the BlueGuard v1 backend and dashboard in this repo work end to end. The screens for SamudraSense are designed and signed off in [docs/design](docs/design/DESIGN.md). The features listed under [The idea](#the-idea) are what we are building for the prototype (10 Nov 2026) and the finale (20–21 Jan 2027). They are not in the code yet.

---

## The problem

Oceans absorb about 90% of the extra heat from global warming (IPCC AR6). As seas warm, fish stocks move into new waters, and illegal fleets follow them. Up to 26 Mt of fish a year may be caught illegally, worth up to US$23 billion (FAO, upper estimate), and about 75% of industrial fishing vessels are not publicly tracked (*Nature*, 2024).

Today's monitoring tools have four gaps:

- **Alert fatigue.** Storms make ships slow down and loiter, which sets off false alarms.
- **Wasted compute.** AI scans every satellite tile instead of the ones that matter.
- **No follow-up.** Detections rarely become evidence that an authority can act on.
- **Cloud cost.** Satellite AI is out of reach for NGOs and small coastal agencies.

## The idea

Three verbs: **Predict, Detect, Act.**

1. **Predict.** Forecast sea temperature and chlorophyll per grid cell, rank the cells where illegal fishing is likely to move next, and pull radar tiles only for those cells.
2. **Detect.** A radar hull with no matching AIS signal is a dark vessel. A finite state machine checks for evasion.
3. **Verify.** If there was a storm, the alert goes on a watch list. If the sea was calm, we find who the vessel met.
4. **Act.** The evidence is hashed, a local LLM drafts the report, and an officer approves it. Nothing is sent without that approval.

| # | Innovation | What it does |
|---|---|---|
| 01 | Climate hotspots | Sea-temperature shifts predict where illegal fishing moves |
| 02 | SAR + AIS fusion | Sentinel-1 radar hulls with no AIS become dark-vessel alerts |
| 03 | Evasion state machine | Tracks AIS switch-off, loitering, rendezvous and position jumps as explainable states |
| 04 | Weather-aware triage | Storm sheltering is downgraded and logged, never deleted. A storm near a protected area escalates instead |
| 05 | Ghost-fleet graph | Maps every vessel a dark ship met in the last 48 hours |
| 06 | Legal dispatch | A local LLM drafts incident reports for officer approval |
| 07 | Spill simulator | Drop a pin to see where oil drifts in 6, 12 and 24 hours |
| 08 | Green edge AI | Runs offline on one RTX 3050 and scans only hotspot tiles |

### Explainable by design

An officer can't board a boat because a model said 0.87. Every alert in SamudraSense shows:

- **Why it was flagged.** The risk score is additive: each behaviour adds points, so the breakdown *is* the score.
- **What was ruled out.** For example bad weather or an AIS receiver outage.
- **What would clear it.** For example "drops to 0.45 if AIS resumes within 4 h".
- **Where every figure comes from.** Each number in a report links to its database record, and sign-off is blocked while any number is unlinked. The LLM writes only the sentences.

Later we add a heat overlay showing what the radar model saw (EigenCAM on YOLOv8) and SHAP values for the hotspot ranking. Route predictions from the LSTM are labelled as predictions, not explained.

### Honest limits

| Question | Our answer |
|---|---|
| Satellites pass every few days. Is this real time? | AIS is live, and radar adds a confirming snapshot. Hotspots decide which passes to process first. |
| Won't storm suppression hide real crimes? | Alerts are downgraded, never deleted, and a storm near a protected area escalates. |
| Can a local LLM invent facts in a report? | It writes only the wording. Every figure comes from the database, and an officer approves each report. |
| Does every AIS gap mean a vessel went dark? | No. Dark status needs a long gap plus a radar hull or a position jump. |
| How do you find transshipment partners? | Global Fishing Watch's encounter rule: within 500 m for 2+ hours under 2 knots, then 2 hops back over 48 hours. |

### How we will measure it

| Open dataset | Used for | Metric |
|---|---|---|
| xView3-SAR (Sentinel-1) | Dark-vessel detection | Precision, recall and F1 on held-out scenes |
| Global Fishing Watch AIS + fishing effort | Hotspot labels, encounters | Share of next month's fishing effort inside our top-ranked cells |
| Copernicus Marine SST + chlorophyll | Hotspot forecasts | Mean absolute error per grid cell |
| Open-Meteo Marine | Alert triage | False alerts removed vs. real alerts wrongly downgraded |
| NOAA GNOME runs | Spill simulator | Overlap between our impact zones and GNOME's |

We start with India's coasts, including the Gulf of Mannar and Gulf of Kutch protected areas. The work supports **SDG 14** (Life Below Water) and **SDG 13** (Climate Action).

---

## Roadmap

| When | Milestone | Scope |
|---|---|---|
| Done | BlueGuard v1 (this repo) | AIS tracking and risk scores, LSTM route prediction, pollution detection pipeline, alerts for 4 Indian protected areas, React dashboard, Gemini chat assistant |
| Sep 2026 | Revival and design | Repo fixed and restructured; SamudraSense screens designed ([docs/design](docs/design/DESIGN.md)) |
| 10 Nov 2026 | Prototype video | End-to-end alert flow, SAR + AIS fusion on xView3, hotspot forecasts, evasion state machine and weather triage, encounter graph, explainable alerts |
| 20–21 Jan 2027 | Grand finale | Local LLM reports, spill simulator, offline build on an RTX 3050. Stretch goal: 3D smart buoy |

---

## Tech stack

### In the code today

| Layer | Technology |
|---|---|
| Frontend (`apps/web`) | React 18, Vite 7, Tailwind CSS 3, Leaflet + React-Leaflet, Recharts, Radix UI, Lucide, Axios |
| API (`apps/api`) | Python 3.11, FastAPI, SQLModel, Pydantic 2, Alembic, Uvicorn |
| Data | PostgreSQL 15 + PostGIS 3.3, GeoAlchemy2, Shapely, Fiona, PyProj |
| Jobs | Celery on Redis 7 |
| AI / ML | PyTorch 2.2 (LSTM route model), Ultralytics YOLOv8 (detector, no trained weights yet), Google Gemini via `google-genai` for the chat assistant |
| Infra | Docker Compose; Supabase Postgres as an optional hosted database |

### Planned for SamudraSense

| Layer | Technology | Replaces |
|---|---|---|
| Maps | MapLibre GL JS with offline PMTiles, deck.gl data layers | Leaflet with online tiles |
| UI | Radix Primitives with our design tokens, Observable Plot / visx, Cytoscape.js for the encounter graph | Current dashboard components |
| Orchestration | Node.js + BullMQ on Redis (`services/orchestrator`) | Celery for the scan pipeline |
| Edge filter | C++17 spatial grid index and geofencing that drops routine AIS early (`services/edge-filter`) | — |
| AI / ML | YOLOv8s on Sentinel-1 SAR, Prophet + scikit-learn hotspot ranker, evasion state machine, EigenCAM, SHAP | Pollution-only detector |
| LLM | Local 3–4B model via Ollama, 4-bit | Gemini |
| Data sources | Copernicus Marine, Global Fishing Watch, Open-Meteo Marine, OSM | — |

**Edge budget** (planning estimates; measured figures will come with the prototype): YOLOv8s at FP16 takes about 1 GB of VRAM and the LLM about 3 GB, so they take turns on the GPU. The CPU-side models need about 2 GB of RAM, the database and Redis about 3 GB, and the filter and orchestrator about 1 GB, all within a 16 GB workstation. Internet is used only to download satellite data.

---

## Repository layout

```
marine_gurad/
├── apps/
│   ├── api/          FastAPI backend: routes, models, services, Alembic migrations, scripts
│   └── web/          React + Vite dashboard
├── services/         Orchestrator and C++ edge filter (planned)
├── ml/               Training code, datasets and model cards (planned)
├── infra/            docker-compose.yml and its .env.example
└── docs/
    └── design/       DESIGN.md, HTML screen mockups and rendered screenshots
```

---

## Running it

### With Docker (recommended)

```bash
git clone https://github.com/Aditya-Patil27/marine_gurad.git
cd marine_gurad
cp apps/api/.env.example apps/api/.env   # set GEMINI_API_KEY for the chat assistant
docker compose -f infra/docker-compose.yml up --build
```

- Dashboard: http://127.0.0.1:5173
- API docs: http://127.0.0.1:8000/docs

Compose starts PostGIS, Redis, the API, a Celery worker and the frontend, and runs the database migrations on start. To use Supabase instead of the local database, set `DATABASE_URL` in `infra/.env`.

If you ran an older version of this stack, reset the database volume once, because the default database name and user changed: `docker compose -f infra/docker-compose.yml down -v`.

### Without Docker

You need Python 3.11 (PyTorch 2.2 has no wheels for newer versions), Node.js 20.19+, PostgreSQL 15 with PostGIS, and Redis.

```bash
# API
cd apps/api
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt
createdb samudrasense_db && psql samudrasense_db -c "CREATE EXTENSION postgis;"
alembic upgrade head
python scripts/load_mpas.py          # optional: sample protected areas
uvicorn app.main:app --reload --port 8000

# Web (second terminal)
cd apps/web
npm ci
npm run dev                          # proxies /api to http://127.0.0.1:8000
```

### Loading data

```bash
cd apps/api
python scripts/ingest_ais.py path/to/AIS.csv   # MarineCadastre-style CSV: MMSI, LAT, LON, BaseDateTime, SOG, COG, ...
python scripts/ingest_sentinel.py              # satellite pollution detections (needs trained weights)
```

Trained model weights are not committed. The API looks for them in `apps/api/models/` (`pollution_yolo.pt`, `route_lstm.pt`). Without them, route prediction falls back to linear extrapolation and satellite detection returns 503.

---

## API

All routes are under `/api/v1`. Full reference at `/docs` when the API is running.

| Method | Route | Purpose |
|---|---|---|
| GET | `/map/layers?layer_type=vessels\|pollution\|mpas&bbox=minLon,minLat,maxLon,maxLat` | GeoJSON map layers |
| GET | `/alerts/?severity=HIGH&limit=20` | Alerts sorted by severity and risk score |
| GET | `/analytics/statistics` | Headline counts for the dashboard |
| GET | `/analytics/ohi?days=180` | Ocean Health Index time series |
| POST | `/ingest/ais` | Ingest AIS positions |
| POST | `/ingest/satellite-image` | Run detection on a satellite image URL |
| POST | `/chat/message` | Ask the assistant (Gemini with database tools) |

---

## Security notes

- Never commit `.env` files. Use the `.env.example` files as templates.
- Ingest routes have no authentication yet. Don't expose the API publicly.
- Early commits in this repo contained a Gemini API key and a Supabase service-role key. Both must be treated as leaked and rotated.

---

## Data and acknowledgements

Global Fishing Watch, Copernicus / Sentinel, xView3-SAR, MarineCadastre AIS, Protected Planet (WDPA), Open-Meteo, NOAA GNOME and OpenStreetMap.

Protected-area boundaries and sample data in this repo are indicative placeholders. Replace them with official WDPA data before any real use.
