# Owner B story queue

The lead keeps this ledger and writes each story's full prompt only when it is next, so the prompt uses the current code and A's latest contracts. Deadlines and scope come from `docs/FINAL_PRODUCT_PLAN.md` section 8. Stories run in table order.

Status: `queued`, `in round N`, `done (SHA)`, `blocked`, `you` (a person has to do it).

## Due 4 Nov, 18:00 IST

| ID | Feature | Outcome | Depends on | Status |
|---|---|---|---|---|
| B-01 | F13 | Failed SAR, vessel and report lookups read as failures, not as clean results. A rejected sign-off no longer crashes the screen. | none | done (d75ec82); two small follow-ups are in B-17 |
| B-02 | F13 | Run the existing journey on the real stack | none | done 3 Nov by session marine-gurad-70, no commit; results below |
| B-17 | F13 | Sign-off state stays with its report. Today a tick and an error on report #1 carry over to report #2, with **Record sign-off** enabled on a report the officer never opened. Found in the round 1 review; the bug is older than B-01. | none | done (b5bc8c2); one gap moved to B-16 |
| B-15 | F13 | Map layers do not wait for basemap tiles (`OceanMap.jsx:123` adds them on `load`). With slow tiles the map showed no vessels or zones for 30 s under a green "14 vessels". `style.load` fixes it; results below. | none | done (f2a81ca); one test gap moved to round 4 |
| B-03 | F02, F13 | Vessel, evidence and report views label each source as live, historical, cached or synthetic. A missing field reads "Source not reported", never "live". Evidence shows the `source` and `note` the weather API already returns (`Cases.jsx:92` drops them). | Falls back to "not reported" until A's fields exist | done (908cb06); `data_mode` is a placeholder name until H-01 |
| B-04 | F13 | The Shell shows one global data-mode banner, including an offline state. Seeded vessels no longer sit beside real weather under one green pill. | B-03 | done (1cca052); one test gap moved to round 6, one follow-up to B-16 |
| B-05 | F13 | Every evidence time shows its date and a labelled timezone. `timeIST` drops the date, and Reports prints raw ISO strings. Report list rows show a date and status, so repeat snapshots can be told apart. | none | done (5ee3732); two test gaps moved to round 7 |
| B-16a | F13 | Wording fixes. The Spills and Settings placeholders stop promising the 10 Nov prototype. The Alerts intro (`Cases.jsx:17`) is correct. Alerts, Evidence and report factors show display names. Evidence shows "1 gap · 1 encounter", and one duration format for its own encounter rows. A named source beside a missing mode no longer contradicts itself: "Source: Open-Meteo … · Weather data: Source not reported" (found in the round 4 review). Adds the two test gaps from the B-05 review. Durations inside API text, such as "6.4 h so far", stay as they are and go to A. | none | done (aefb751); one test gap moved to B-16b |
| B-16b | F13 | Behaviour fixes. "Draft report" has its own target, not the same one as "Open evidence". A sign-off rejection that arrives after the officer has opened another report does not appear on that report (found in the round 2 review; B-17 covers only a rejection that arrives first). The map pill's dot is not green while the browser is offline: today live data keeps it green under an amber "Offline" banner (found in the round 5 review). Adds a test for a factor `detail` that contains a raw AIS name, on Evidence and on the report (found in the round 7 review). | none | done (fedc063) |
| B-06 | Sprint | Draft the problem statement and video storyboard in `docs/demo/storyboard.md` | none | done (1cdc277) |
| H-01 | Contracts | Agree response examples, enums, units and empty states with A | A's `docs/contracts/` (not in the repo yet) | you |
| H-04 | Contracts | Raise two weather issues with A. (1) The API check says "No marine weather feed is connected yet" directly above a live Open-Meteo reading on Evidence. (2) Snapshots store no weather and the check stays `not_checked`, so a signed report loses what the officer saw. | A | you |

## Due 6 Nov, 18:00 IST

| ID | Feature | Outcome | Depends on | Status |
|---|---|---|---|---|
| B-07 | F08 | The map shows a dated regional environmental value with units and attribution | H-01; fixture first | blocked: needs A's endpoint; done on fixture (c6c510c) |
| B-08 | F07, F08 | The vessel panel and evidence view link to that value without implying a cause | B-07 | blocked: needs A's endpoint; done on fixture (d03d087) |
| B-09 | F03, F09, F13 | Evidence shows the data limitations beside the rule factors. The report view also shows `checks` and the "indicators, not proof of an offence" line, which `Cases.jsx:152-159` omits. | B-03 | done on fixture shape (40ce53d); `limitations` is not in `apps/api`, so it reads "not reported" until A adds it |
| B-10 | Sprint | The journey runs on A's real endpoints instead of fixtures | A's 6 Nov delivery; Docker stack | blocked: needs A's 6 Nov delivery |

## Due 9 Nov, 18:00 IST

| ID | Feature | Outcome | Depends on | Status |
|---|---|---|---|---|
| B-11 | F09 | The report view links each fact to its source and exports sourced JSON | B-10, A's export | blocked: needs A's 6 Nov delivery |
| B-12 | F13 | Tests cover missing sources, real-data replay, and weather that the backend itself reports as `unavailable` | B-10 | done 8 Nov: weather `available`/`unavailable`/`not_checked` and the 404 for no recent positions use payloads copied from `weather.py`; GFW 503 reasons from `gfw.py`; replay checked in the browser (runbook section 5) |
| B-13 | F14 | Record review time and evidence completeness, with sample size and limits | B-10 | blocked: needs A's 6 Nov delivery |
| H-02 | Sprint | Record the climate-centred walkthrough as a draft video on actual screens | B-11 | you |

## Due 10 Nov, 18:00 IST

| ID | Feature | Outcome | Depends on | Status |
|---|---|---|---|---|
| B-14 | F13 | The full journey runs on the prepared setup from a production build, with presentation fixes at 1366×768 and 1920×1080 | all above | blocked: needs A's 6 Nov delivery |
| H-03 | Sprint | Finish the video and evidence pack, and rehearse the judging explanation | B-14 | you |

## B-02 journey results, 3 Nov

Run by session marine-gurad-70 on a disposable compose project with seeded demo data (14 vessels), the Vite dev server, and a Playwright browser at 1440×900. Screenshots are in `C:\Users\app27\.playwright-mcp\journey-*.png`.

- **API tests:** 13 passed, 0 skipped, including the case workflow integration test.
- **Works:** map > vessel panel > alerts > evidence > report snapshot > sign-off. Sign-off stays disabled without both a non-blank name and the tick, and survives a reload. A snapshot tampered with in the database shows "Hash mismatch — sign-off blocked" with the button disabled. No unexpected console errors.
- **Breaks:** moved into B-01, B-03, B-04, B-05, B-09, B-15, B-16 and H-04 above.
- **Not tested:** `/reports?id=999` (B-01 tests it), a production build, 1366×768 and 1920×1080 (B-14), A's real endpoints (B-10), weather that the backend reports as `unavailable` (B-12).

## B-15 spike results, 3 Nov

The lead changed `load` to `style.load` on `OceanMap.jsx:123` in a scratch copy and tested it in a browser with a mocked API, at 1440×900. Nothing from this test is in the repo.

| Tiles | Code | Result |
|---|---|---|
| Held 15 s | current | At 5 s the map is empty and clicking the vessel does nothing (0 vessel requests) |
| Held 15 s, then fail | `style.load` | At 5 s the vessel and zone label are visible. A click opens the panel with track, tags and timeline, and the panel is still there after the tiles fail. |
| Normal (1×1 test tile) | `style.load` | A click opens the panel |
| Fail at once | `style.load` | A click opens the panel |
| Held 15 s, `/map?vessel=` link | `style.load` | The panel opens without a click |

No uncaught page errors in any `style.load` row, using a detail response that includes `generated_at`. A mock without it crashes `TrackTimeline.jsx:20`. The real API always sends it (`vessels.py:61,79`), so copy `seaPearlDetail` from `fixtures.js` when writing B-15's test.

## B-15 review, 3 Nov

The lead tested commit f2a81ca in a clean copy, from a production build, at 1280×800 with a mocked API.

| Tiles | Result |
|---|---|
| Real Esri (70 of 70 tiles loaded) | A click opens the panel with track and tags |
| Held | At about 3 s the vessels, zone and label are visible on a blank basemap. A click opens the panel while the tiles are still held. |
| Fail at once | A click opens the panel. The only console errors are the failed tiles. |
| Held, `/map?vessel=` link | The panel opens without a click |

Tests: 77 passed, build exits 0. The new tests caught 11 of 12 broken versions, including `load` and setup on both events. The one that got through sends an empty track, so round 4 tightens that test.

## B-03 review, 3 Nov

The lead tested commit 908cb06 in a clean copy.

- **Tests:** 92 passed, build exits 0. The new tests caught 24 of 24 broken versions, including a missing mode that reads as live, a dropped weather note and the empty track from B-15.
- **Not checked:** a browser. The change is text only, and the tests check the rendered text.
- **Follow-up:** the API has no mode field, so a line can name a source and still say the source is not reported. B-16 fixes the wording.

## B-04 review, 3 Nov

The lead tested commit 1cca052 in a clean copy, from a production build, with a mocked API and no real basemap tiles.

- **Tests:** 107 passed, build exits 0. The new tests caught 19 of 20 broken versions. The one that got through removes the amber warning style, so round 6 adds that test.
- **Layout at 1366×768 and 1920×1080:** the banner sits above the page in the right column only, the rail is intact, the map fills the area below the banner, and the document does not scroll. Alerts scrolls inside the page and its bottom is reachable.
- **States at 1366×768:** a click on a vessel opens the panel. Offline turns the banner amber and back. A failed refresh shows "Can't reach the API · last sync … · Showing the last data received, not live." with a red dot, and both recover on the next good refresh. The dot is grey with no mode and green for `live`. Reports, Spills and Settings show the banner. No uncaught page errors.
- **Not checked:** a long Evidence page, because the mocked vessel fitted on one screen. It uses the same page wrapper as Alerts. Real Esri tiles, because B-15's review covered them and this change does not touch the map's data.
- **Follow-up:** with live data, the pill's dot stays green under the amber "Offline" banner. The round 5 prompt did not cover this case, so it is the lead's gap, not Antigravity's. It is in B-16.

## B-05 review, 3 Nov

The lead tested commit 5ee3732 in a clean copy, from a production build, with a mocked API and no real basemap tiles.

- **Tests:** 125 passed, build exits 0. The tests caught 26 of 28 broken versions, including the missing warning style from round 5. Two got through, so round 7 adds their tests: `IST IST` on Evidence (the round 6 prompt asked for that check only on the panel, so it is the lead's gap) and an impossible date such as month 13. The code handles both correctly today.
- **Browser at 1366×768 and 1920×1080:** the report list, report, Evidence and panel all show the date and `IST`. A time with no value reads "Time not reported". Timestamps with microseconds and weather times without seconds both parse. List rows wrap to two or three lines with no overflow. No uncaught page errors.
- **Left on purpose:** time-only labels on map tags, the track timeline and the banner. Recheck at B-14.

## B-16a review, 3 Nov

The lead tested commit aefb751 in a clean copy.

- **Tests:** 146 passed, build exits 0. The tests caught 26 of 28 broken versions, including both gaps from the B-05 review. The two that got through remove display names from a factor's `detail`. The code is correct, but no fixture has a raw name in that field, and the round 7 prompt did not ask for it, so it is the lead's gap. B-16b adds the test.
- **Not checked:** a browser. The change is text only, and the tests check the rendered text. B-14 sees these screens at both sizes.
- **To raise with A:** the API writes durations in its own text, such as "6.4 h so far", while the map shows "6 h 22 m" for the same gap. The web app does not rewrite API text, so one format everywhere needs A's change.

## Next round

- Round 8 is B-16b. Read its code again before writing the prompt. `Base commit` is the HEAD at that time.
- Before B-06, add a write rule for `docs/demo/storyboard.md` to `worker-settings.json`.
