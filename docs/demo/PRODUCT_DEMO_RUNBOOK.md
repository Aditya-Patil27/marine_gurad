# SamudraSense product demo runbook

Target: 3–4 minutes. This is a review-support product demo, not a claim of
live regional coverage, illegal-activity detection or operational spill
forecasting.

## Before recording

1. Start the frontend with the intended isolated API target.
2. Sign in with an existing local Analyst account. Use an Approver only when
   showing a prepared draft's sign-off; do not re-approve an already approved
   report.
3. Confirm the banner's data mode before narrating a result. If a source is
   unavailable, show its state rather than retrying during the recording.

## Narration and clicks

### 0:00–0:30 — Overview

Open `/overview`. Say: “SamudraSense turns regional activity into an
explainable investigation, a human-reviewed case and a traceable export.”
Point to the four stages: Detect, Investigate, Act and Prepare. Explain that
the counts are loaded from the local API and unavailable sources are not
silently shown as zero.

### 0:30–1:15 — Detect and investigate

Select **Map**, then a vessel or one of the historical GFW event entries.
State the displayed mode aloud. For a GFW event, say: “This is a historical,
inferred event point—not a live vessel track and not proof of fishing or
illegality.” Move to **Alerts** and then the evidence view. Point out score
factors, the selected observation window, coverage limitations and the
separate ocean/weather context if available.

### 1:15–2:05 — Act: case, review and export

Open **Cases**, choose the prepared case, then **Reports**. Select a report.
Show the evidence basis, source references, limitations, review state and
SHA-256 integrity checksum. Say: “The checksum detects stored-snapshot change;
it is not a digital signature.”

For a draft, switch to the Approver account and select the review checkbox,
then record sign-off. For an approved report, show **Export approved PDF** and
**Download manifest**. Do not claim a delivery or external dispatch.

### 2:05–2:40 — Prepare: operations

Open **Operations**. Show the source-health cards and say that configured or
not-checked is not coverage or guaranteed availability. If signed in as an
Administrator, show deployment settings and local account roles; do not type
or display a password during the video. If not an Administrator, show the
truthful permission explanation.

### 2:40–3:25 — Spill readiness

Open **Spills**. Show the engine and wind/current forcing capability first. If
available, submit a bounded scenario job and inspect its reported status; if
unavailable, show that submission is disabled. Explain: “The product will not
invent a trajectory without a configured engine and compatible forcing.” Do
not claim GNOME output, a calibrated forecast or emergency guidance unless the
capability screen actually reports those prerequisites available.

### 3:25–3:45 — Close

Return to **Overview**. Say: “The product keeps source mode and limitations
attached to the analyst workflow, so uncertain data remains reviewable rather
than becoming an automated conclusion.”

## Fallbacks

- No GFW event: use a prepared vessel replay and say it is replay data.
- No report available: show the Reports empty state, then use the prepared
  event-only/case workflow only if a disposable demo database has been set up.
- Source failure: stay on Operations and show the source-specific unavailable
  status; do not claim live coverage.
- Spill engine unavailable: show the capability state. Do not use a client-side
  substitute trajectory.

## Recording limits

The current demo does not claim a spill forecast unless the configured engine
and forcing are available. It also does not claim calibrated probabilities,
emergency response advice, actual spill detection, external delivery, or full
offline capability.
