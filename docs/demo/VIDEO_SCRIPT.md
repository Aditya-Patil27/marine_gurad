# SamudraSense judging video script

Prepared 9 November 2026 for the 10 November judging slice. This replaces the
historical [storyboard](storyboard.md) as the recording script. Claim limits
come from [JUDGING_REPLAY_RUNBOOK.md](JUDGING_REPLAY_RUNBOOK.md) and
[../HACKATHON_JUDGE_REVIEW.md](../HACKATHON_JUDGE_REVIEW.md).

- **Length:** about 4 min 30 s, 1920×1080, 30 fps.
- **Tool:** [HyperFrames](https://github.com/heygen-com/hyperframes)
  (HTML rendered to video). Real screen clips of the app are the footage.
  HyperFrames adds punch-ins, short labels, the voice and click sounds.
- **Voice is the clock:** record the voice first. Each scene lasts as long as
  its line.
- **The lines below were checked against the running app** (seed replay data,
  no Copernicus subset, no PyGNOME) on 9 November 2026. If your stack differs,
  re-check the screen before you read a line.

## Voice script

Read one numbered line per take, at a calm pace of about 130 words a minute.
Leave a one-second pause before and after each take. Save each take as
`vo-<number>.wav`, for example `vo-01.wav` and `vo-04a.wav`.

**01.** A vessel's AIS track goes quiet, just outside a marked protected area
in the Gulf of Mannar. Equipment fault, weather, or something an officer must
see?

**02.** Today that answer is scattered. Positions in one feed, weather in
another, satellite events in a third. Nothing ties them together.

**03.** SamudraSense puts them in one console: the fleet picture, triage,
investigations and operations. Every count comes from the local API. A missing
source stays missing.

**04a.** First, what you are looking at. These tracks are invented replay data
from our seed script, not live AIS. The strip says source not reported,
instead of calling them live.

**04b.** These dots are historical Global Fishing Watch events from January
2024, not vessel positions. The sea temperature subset is not on this machine,
so the card says environmental data not available. Context never changes a
score anyway.

**05.** Alerts ranks vessels for review with fixed, additive rules. No trained
model. Sea Pearl Two scores zero point six three, the only vessel under needs
review.

**06a.** Every point has a reason. More than six hours with AIS off. A close
encounter with Hai Feng 818. Loitering inside the national park. Each rule
shows its threshold.

**06b.** Beside the rules sit the limits and the checks. Nine other vessels
nearby kept reporting, so a receiver outage looks unlikely. Wind and waves are
Open-Meteo model estimates: context, not cause. And no SAR detection is
recorded, so the screen says so instead of guessing.

**06c.** On the map, the track shows where Sea Pearl Two met Hai Feng 818.
Three hundred and seventy one metres apart, for about two and a half hours,
from the same replay positions as the score.

**06d.** A gap or an encounter is a reason for a person to look. It is not
proof of an offence.

**07a.** One click opens an investigation case, and freezes this evidence as
report revision one.

**07b.** Before anyone can sign, the report re-checks its SHA-256 hash. The
hash detects changes to the saved evidence. It is not a digital signature.

**07c.** The approver confirms they reviewed the evidence, and signs as the
signed-in account, not as a typed name. Sign-off sends nothing anywhere.

**08a.** The approved report exports as a PDF and a canonical JSON manifest,
so a reader can trace each fact back to where it came from.

**08b.** You don't have to trust our screen. Hash the downloaded manifest with
any standard tool, and it matches the value the report shows.

**09.** A case can be closed with a note, and reopened later. Every change is
kept in its history, with who made it, and when.

**10.** Ocean is where the dated Copernicus observations belong. That subset
is not loaded here, so the screen says unavailable, and the scan planner stays
switched off instead of ranking on nothing.

**11.** SAR observations go into a register with their source. Today it is
empty, and the screen says so. Protected area boundaries stay marked
unverified until someone checks them.

**12.** Operations shows the state of each source. Configured does not mean
coverage, and the screen keeps the two apart.

**13.** If the connection drops, the strip changes and says when it last
synced. Old data is never passed off as live.

**14.** Spill scenarios need NOAA's PyGNOME engine with real wind and current
data. Until both are installed, submission stays off. We will not draw a
trajectory we cannot back.

**15.** Better-evidenced review could help protect the reefs and seagrass
here. That is our expected pathway, not a measured result. SamudraSense keeps
the source and the limits on every step.

Read at a natural pace, the 22 lines take about 4 min 10 s, plus the pauses.

## Storyline

**"One track, start to finish."** A worked example. One replay vessel,
Sea Pearl II, travels from a quiet AIS track on the map to a signed report
whose hash the viewer can check, then on through the rest of the console. Each
shot ends on the button that opens the next, so the judges follow one thread
rather than a feature tour.

## Before recording

1. Run the pre-flight in
   [JUDGING_REPLAY_RUNBOOK.md §1](JUDGING_REPLAY_RUNBOOK.md#1-pre-flight-5-minutes).
   A `FAIL` stops the recording.
2. Sign in as the local Administrator. Never show a password on screen.
3. Rehearse scene 08b once. Run `Get-FileHash -Algorithm SHA256` on the
   downloaded manifest and compare the result with the SHA-256 on the report.
   If they differ, cut scene 08b. Do not edit or explain the mismatch away.
4. Record scenes 07a–09 (case, sign-off, close and reopen) on a disposable
   database only.
5. Browser at 1920×1080 and 100% zoom, with no other tabs or extensions
   showing.

## Shot list

One row per voice line. The label is the short text that HyperFrames puts on
screen. Never make a label repeat the narration word for word.

| # | Footage (route and clicks) | Label on screen |
|---|---|---|
| 01 | `/map`, zoomed in on Sea Pearl II's AIS-off point beside the protected-area polygon. Slow pull-out to the Gulf of Mannar. | Track goes quiet |
| 02 | Three fast cuts of raw API JSON: `/api/v1/vessels/419007431`, `/api/v1/weather/419007431`, `/api/v1/gfw/events/regional/geojson?start_date=2024-01-01&end_date=2024-02-01`. | Three feeds, no thread |
| 03 | `/overview`. Punch in on the cards as they are named. | SamudraSense |
| 04a | `/map`. Click the AIS-off point; punch in on the panel's synthetic line, then the "Data mode:" strip. | Replay data |
| 04b | `/map`, **Historical fishing events** card: **Load historical events**. Then the "Environmental data not available" chip. | Historical, dated |
| 05 | Left rail **Alerts** → **Needs review**. Click Sea Pearl II. | Fixed rules |
| 06a | Evidence, **Why it was flagged**. Punch in on each factor and its rule threshold. | Every point has a reason |
| 06b | **Data limitations**, the AIS receiver outage check, weather at the AIS gap, SAR none. | Limits beside the rules |
| 06c | **View track on map**. Punch in on the meeting label, then the timeline. | Same positions, same story |
| 06d | Back to the evidence. Hold on the "not proof of an offence" line. | Indicators, not proof |
| 07a | **Create investigation case**. The case opens at `/cases?id=…`, revision 1. | Case opened |
| 07b | The report: **Snapshot hash verified**, the SHA-256 line, the not-a-signature note. | SHA-256 checked |
| 07c | Tick the review checkbox, then **Record sign-off**. Show **Signed by** and "No delivery attempts." | Signed by the session |
| 08a | **Export approved PDF**, then **Download manifest**. | Traceable export |
| 08b | Hold on the report's SHA-256, then a terminal card with `Get-FileHash` on the downloaded manifest. Only if they match. | Check it yourself |
| 09 | Case screen: type a note, **Close case**, then **Reopen case**. Punch in on **History**. | Every change kept |
| 10 | `/ocean`: the unavailable card and the disabled **Prepare plan**. | No data, no plan |
| 11 | `/detections`: the empty register, then the "unverified" boundary references. | Empty means empty |
| 12 | **Operations** (`/settings`): "Configured or not checked does not mean reachable", "Coverage: unknown". | Source state |
| 13 | Set the browser offline. The strip reads "Offline · last sync …". Back online. | Offline stays honest |
| 14 | `/spills`: "not configured", disabled **Run scenario**, "No fallback trajectory". | No forcing, no trajectory |
| 15 | Back to `/overview`, then the end card. | SamudraSense |

## Never say

These come from the runbook. Cut a line rather than bend it:

- live tracking, or live AIS for the replay vessels
- GFW vessel tracks (they are event points)
- detected or confirmed illegal fishing
- identity confirmed from SAR
- a measured review-time saving, enforcement effect or ecological benefit
- weather causing, or explaining, a vessel's behaviour
- a digital signature, or a report delivered or sent
- a satellite tasked or imagery acquired from a scan plan
- a spill forecast, emergency guidance, or any trajectory the Spills screen does
  not show

## Building the video

1. **Voice.** Record the voice script above, one WAV per numbered line.
2. **Footage.** Capture one clip per shot-list row at 1920×1080 against the
   prepared stack. Make each clip about 3 s longer than its voice line, so it
   can be trimmed.
3. **Compose.** `npx hyperframes init docs/demo/video`. One sub-composition per
   row, each with its `data-duration` set to that row's WAV length. Add a click
   sound on each real button press.
4. **Check.**
   - `npx hyperframes check --json`, then `npx hyperframes snapshot --review`.
   - Watch the result once with the sound off: the pictures alone should tell
     the same story.
   - Watch it once against the Never-say list.
5. **Render** when the preview is approved:
   `npx hyperframes render --gpu --browser-gpu`.
