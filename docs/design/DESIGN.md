# SamudraSense design

Status: **v2 signed off** (17 Sep 2026). v1 was a dark theme and was rejected. Screen 01 (map) is built in `apps/web`; the others are next.

The screens in `screens/` are static HTML mockups with sample data.

## 1. Direction

- **Light and calm.** The UI matches the team deck (`SamudraSense_deck/styles.css`): white, navy, periwinkle, League Spartan and Jost.
- **The map is the product.** App screens use a full-bleed ocean map with a few floating white cards on top, not a grid of boxed panels.
- **Quiet background.** No patterns, grid lines, contour lines or dense status text. Colour is saved for things that need attention.
- **Explainable by design.** Every alert shows why it fired, what was ruled out, and what would clear it (see section 3).

Why the map is styled this way: we borrowed the idea of colour meaning enforcement state from ship chart displays (magenta for protected areas). We borrowed the timeline strip and radar-crop evidence from Global Fishing Watch and Skylight.

## 2. Tokens (`screens/samudra.css`)

| Token | Hex | Use |
|---|---|---|
| `--navy` | `#08337F` | Headings, primary buttons, selected nav, own vessel track |
| `--peri` / `--peri-soft` | `#C1CBFF` / `#E6EAFF` | Selected states, chips, bar backgrounds |
| `--ink` / `--muted` / `--faint` | `#1B1F2A` / `#56607A` / `#8A93A8` | Text levels |
| `--line` / `--canvas` | `#E3E7F0` / `#F5F7FB` | Borders, page background |
| `--red` | `#D64545` | Confirmed signature (ring) |
| `--amber` | `#D98A0B` | Radar hull with no AIS (hollow diamond) |
| `--green` | `#1E9E6A` | Ruled out, verified, sent |
| `--zone` | `#A3339A` | Protected areas (chart magenta) |
| `--storm` | `#7C8AA5` | Weather-downgraded (dashed ring) |

State is never shown by colour alone: every state also has a shape or a dash pattern.

| Role | Font |
|---|---|
| Headings | League Spartan 600–700 |
| Body and UI | Jost 400–500, 14 px in the app, 16 px on the site |
| MMSI, coordinates, times, figures | IBM Plex Mono with tabular numbers |

Cards are white with a 12 px radius and a soft navy-tinted shadow. Buttons have a 9 px radius.

## 3. Explainable AI

| Layer | What the officer sees | How it's produced |
|---|---|---|
| Risk score | "Why it was flagged": each behaviour with its points, which add up to the score | Additive rule-based score, so the explanation is exact |
| Ruled out | Weather, AIS receiver outage | Weather triage and coverage checks |
| What would clear it | "Drops to 0.45 if AIS resumes within 4 h" | Re-scoring with one input changed |
| Radar detection | "Showing what the model saw" heat overlay on the SAR crop | EigenCAM on YOLOv8 |
| Hotspot rank | Share of the rank from each factor (sea temperature, chlorophyll, past effort) | SHAP on the ranker (finale) |
| Report | Every figure highlighted and linked to its record; sign-off blocked while any is unlinked | Figures bound from the database; the LLM writes only the sentences |

Route predictions from the LSTM are labelled as predictions and not "explained".

For the 10 Nov video, the scope is the risk score, ruled-out checks, what would clear it, and report provenance. EigenCAM and SHAP come later.

## 4. Screens

| # | File | Layout |
|---|---|---|
| 00 | `00-landing.html` | Public site: hero, console screenshot, 3 problem stats, Predict/Detect/Act, explainable AI section, roadmap |
| 01 | `01-command-map.html` | Icon rail. Full map with layer chips on top, "Needs attention" card on the left, explained vessel card on the right, 12 h timeline at the bottom |
| 02 | `02-alert-triage.html` | Five lanes: New, Explained by weather (kept, restorable), In review, Awaiting sign-off, Sent. Each card shows its top reason |
| 03 | `03-vessel-evidence.html` | Radar crop with model heat overlay next to the track, speed chart, "How the case was built" timeline with points, encounter graph |
| 04 | `04-incident-report.html` | Report on the left with linked figures; right panel shows figure sources, recipients, history and sign-off |
| 05 | `05-spill-simulator.html` | Full map with 6/12/24 h extents and a dashed possible extent, release inputs, "What it reaches", time scrubber |

The sample story is the same on every screen: *Sea Pearl II* goes dark at 08:20 inside the Gulf of Mannar park buffer, a radar pass at 11:42 finds its hull, and it meets a carrier 410 m away.

Coordinates, park boundaries, habitats and legal wording are **indicative placeholders**. Replace them with WDPA and official data before any real use.

Render PNGs with `sh shots/shoot.sh <screen-name>` (headless Edge, 1600×900).

## 5. Build plan

| Need | Library | License |
|---|---|---|
| Map | MapLibre GL JS with offline tiles (PMTiles) | BSD-3 |
| Map data layers | deck.gl | MIT |
| UI primitives | Radix Primitives styled with these tokens | MIT |
| Charts, timeline | Observable Plot, visx | ISC, MIT |
| Encounter graph | Cytoscape.js | MIT |
| Icons | Lucide | ISC |

The mockups use Leaflet and Esri ocean tiles only for quick screenshots.
