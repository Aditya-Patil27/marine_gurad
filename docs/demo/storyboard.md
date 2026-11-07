# SamudraSense: Climate-Centred Demonstration Storyboard

> Historical draft, not the current recording script. Fixture scores, 24-hour windows, typed-reviewer wording and placeholders below must be replaced with observed behavior before recording. Use JUDGING_REPLAY_RUNBOOK.md and ../HACKATHON_JUDGE_REVIEW.md for current constraints.


## 1. Problem Statement

The Gulf of Mannar Biosphere Reserve and Marine National Park comprises 21 islands along the southeastern coast of Tamil Nadu, India, harbouring globally significant marine biodiversity including coral reef ecosystems, extensive seagrass meadows, and vulnerable species such as the dugong (*Dugong dugon*). These critical coastal habitats serve as vital marine carbon sinks and primary fish breeding nurseries.

Coastal monitoring and fisheries surveillance authorities operate under severe constraints: vast maritime surface areas, intermittent communication infrastructure, and disconnected data feeds. Analysts must manually cross-reference AIS vessel streams, environmental readings, and satellite observations across disparate sources. In unmonitored waters, illegal, unreported, and unregulated (IUU) fishing and unauthorised loitering in designated marine park buffers damage benthic habitats, deplete juvenile fish populations, and erode ecosystem stability.

A raw tracking gap also means little on its own. Without receiver health and local marine weather beside it, a gap is easily misread.

SamudraSense addresses this operational challenge through a lightweight, self-contained coastal monitoring workstation. It joins regional ocean observations `[depends on A]`, explainable rule-based alert triage, and hash-checked evidence preparation in a single interface:

- **Truthful Data Provenance:** Vessel, evidence and report views label each source as live, historical, cached or synthetic. Missing data reads as missing, such as "Source not reported", and is never assumed clean.
- **Rule-Based, Explainable Risk Engine:** Vessel risk scores are computed using transparent, additive scoring rules (AIS gaps, protected zone proximity, loitering, and encounters). The screen shows each rule's points and what would clear the alert.
- **Operational Context Without False Causality:** Regional environmental values `[depends on A]` and Open-Meteo marine weather estimates provide operational context for triage. They never modify risk scores and never imply direct causality for vessel manoeuvres.
- **Checkable Evidence and Case Integrity:** Each investigation captures a frozen evidence snapshot with a local SHA-256 hash. The hash detects accidental changes; it is stored alongside the evidence and is not a digital signature. Review and sign-off happen before export.

### Expected Ecological Pathway

This is an expected pathway, not an observed outcome. SamudraSense has not been shown to reduce emissions or fishing pressure.

1. Analysts can review and substantiate suspicious activity in protected zones in `[measure at B-13]` minutes, compared with raw multi-file inspection in `[measure at B-13]` minutes.
2. Weather estimates and receiver coverage checks sit beside each AIS gap, so an officer can weigh other explanations before acting.
3. Each case produces a hash-checked package that an authority can review.

If faster, better-evidenced review leads to more consistent enforcement, that could deter destructive incursions into seagrass and reef nurseries, and so support long-term ecosystem resilience and blue-carbon habitats.

---

## 2. Video Storyboard

| Scene | Screen shown | What is said | Duration |
|---|---|---|---|
| 1. Introduction & Protected Waters | Map overview (`/map`) displaying Gulf of Mannar AOI, protected marine park boundary polygons, vessel symbols, and the top data mode banner. | "Welcome to SamudraSense, a coastal monitoring workstation designed for sensitive marine habitats like the Gulf of Mannar Biosphere Reserve. The console displays vessels against protected park boundaries. The top banner states the data mode, and evidence times carry a date and India Standard Time. In this recording the AIS tracks are synthetic: invented demo vessels from our seed script `[update at B-10 if real AIS is connected]`. Weather values are Open-Meteo model estimates. When the console is offline, the banner says so rather than presenting old data as live." | 25 s |
| 2. Regional Ocean Context | Map with dated regional environmental context card (`/map`) `[depends on A]` | "Sustainable coastal stewardship requires environmental context. Here, the map presents a regional ocean reading `[depends on A: variable, source and whether it is live, historical or cached]`, with its unit, observation date and provider attribution. Environmental values serve strictly as context: they never alter vessel risk scores and never claim to prove or cause vessel actions." | 30 s |
| 3. Alert Triage & Explainable Scoring | Alert triage board (`/alerts`) showing 'Needs review' and 'Watch' lists with vessel cards, scores, and headlines. | "On the alert triage screen, our rule-based risk engine highlights vessels requiring attention over the past 24 hours. The engine adds up fixed rules; no trained model is involved. Sea Pearl II, an invented demo vessel, is under 'Needs review' with a risk score of 0.63, above the alert line of 0.60. As stated on screen, weather does not change these scores. Each card gives a headline, and the rules behind the score are on the next screen." | 30 s |
| 4. Evidence Workspace & Independent Checks | Vessel evidence page (`/vessels/419007431`) displaying rule factors, data limitations, independent checks, weather context, encounters, and candidate SAR detections `[depends on A: the seed script creates no SAR detections]`. | "Evidence for Sea Pearl II lists the signals that were recorded: an AIS gap of 6.4 hours, loitering in protected waters, and a close encounter with Hai Feng 818. We examine independent checks: an AIS receiver outage is ruled out because nine other vessels within 50 kilometres kept reporting. At the gap location, Open-Meteo model estimates give wind and waves as context only; they do not prove why AIS stopped. `[depends on A]` Any candidate SAR detection is labelled with its data source and distance offset, as a candidate match rather than confirmed identity. AIS gaps and encounters are indicators, not proof of an offence." | 45 s |
| 5. Report Snapshot & Evidence Integrity | Report creation and review screen (`/reports?id=<id>`) displaying frozen snapshot, checks, data limitations, SHA-256 integrity hash, reviewer input, and sign-off. | "From the vessel panel or evidence workspace, an analyst creates a report snapshot with a single action. The snapshot freezes the observations, rule factors and checks at this point in time. The console re-checks the SHA-256 hash across the preserved snapshot and blocks sign-off on a mismatch. The hash detects accidental changes and is not a digital signature. An investigating officer reviews the snapshot, enters their name, and records sign-off." | 35 s |
| 6. Sourced Export & Ecological Resilience | Sourced JSON export view (`/reports`) `[depends on A]` | "The reviewed report can be exported as sourced JSON `[depends on A]`, so a reader can trace each fact to its source. `[measure at B-13: review time with raw records and with this interface, with sample size and limits; say nothing about a reduction unless it was measured]` We expect that faster, better-evidenced review could support enforcement that protects seagrass nurseries and marine ecological resilience. That is an expected pathway, not an observed outcome." | 30 s |

## Before recording

- Replace every `[depends on A]` and `[measure at B-13]`. Cut the claim if the screen or measurement does not exist.
- Read 0.63, 6.4 hours and nine vessels off the actual screen. They come from a test fixture, and the seed script's tracks are timed relative to now.
- Add a source for the outside facts in the problem statement: 21 islands, the dugong, carbon sinks and nurseries. The plan does not supply them.
- Settle H-04 first. Evidence currently prints "No marine weather feed is connected yet" directly above a weather reading.
