# Current A/B work

Shared baseline: A-005B/R1 historical replay backend is complete through migration 013. The `ap` branch publishes the backend, contracts and preserved partial B work. Credentials, local data, CodeGraph state and agent transcripts remain local.

## A — start now

Execute [A-004E](A-004E.md): persist and bind one real historical GFW event evidence snapshot, with optional independently dated SST context, into the existing authenticated report/case revision path. A owns `apps/api/**`, migrations, contracts and the data manifest. A must use a fresh backend-only OpenCode session and must not edit `apps/web/**` or resume the interrupted B session.

After A-004E: finish legacy route protection and bounded provider jobs, then advance dependency-ready SAR/triage/environment work from `PLAN.md`. Do not reopen completed replay-window work without a new defect.

## B — continue existing partial work

Continue [B-005](B-005.md) from the partial frontend checkpoint already present on `ap`. B owns `apps/web/**`, relevant frontend tests and demo UI docs. Inspect the existing replay helpers/components before editing; do not reimplement them blindly. Apply migrations through 013 in B's Docker database, complete the map → vessel → assessment → case/report journey, handle 409 re-sync, and record an actual browser journey.

B must not change API, migrations or backend contracts. After B-005, connect existing stored alert/triage and case lifecycle APIs to their screens.

## OpenCode efficiency

OpenCode has Ponytail 5.3.3 installed once in global configuration. `AGENTS.md` also carries the same minimal implementation rules. Every new session must follow both: inspect callers and risks first, reuse existing code, make the smallest complete change, avoid speculative abstractions/dependencies and run only focused meaningful checks.
