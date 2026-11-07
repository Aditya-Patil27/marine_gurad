# Current A/B work

Shared baseline: A-005B/R1 historical replay backend is complete through migration 013. GitHub branches `ap` and `handoff/b-005` publish the backend, contracts and preserved partial B work. B's existing `b/sprint` branch was left untouched. Credentials, local data, CodeGraph state and agent transcripts remain local.

## A — completed handoff

[A-004E](completed/A-004E.md) is complete: one selected historical GFW event can be re-fetched from its bounded page and bound, with optional independently dated SST context, into the authenticated hashed report/case revision path. No migration or parallel evidence system was added. A must not reopen this slice without a concrete defect.

The next independent A work is remaining legacy route protection and bounded provider jobs. It must use a separate backend-only brief and must not edit `apps/web/**` or resume B's frontend session.

## B — continue existing partial work

Continue [B-005](B-005.md) from the partial frontend checkpoint already present on `ap`. B owns `apps/web/**`, relevant frontend tests and demo UI docs. Inspect the existing replay helpers/components before editing; do not reimplement them blindly. Apply migrations through 013 in B's Docker database, complete the map → vessel → assessment → case/report journey, handle 409 re-sync, and record an actual browser journey.

B should fetch `origin/handoff/b-005` and continue from that branch in a separate checkout/worktree, or integrate it into B's own branch using the team's normal Git workflow. Do not force-update `b/sprint` or discard B-local work.

B must not change API, migrations or backend contracts. The completed A-004E contract is available for the next browser caller integration; preserve its exact GFW page bounds and truthful historical-event limitations. After B-005, connect existing stored alert/triage and case lifecycle APIs to their screens.

## OpenCode efficiency

OpenCode has Ponytail 5.3.3 installed once in global configuration. `AGENTS.md` also carries the same minimal implementation rules. Every new session must follow both: inspect callers and risks first, reuse existing code, make the smallest complete change, avoid speculative abstractions/dependencies and run only focused meaningful checks.
