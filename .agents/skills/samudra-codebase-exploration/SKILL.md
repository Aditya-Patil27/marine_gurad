---
name: samudra-codebase-exploration
description: Locate and trace SamudraSense modules or change impact with focused CodeGraph queries without repeating a repository-wide audit.
---

Use `ARCHITECTURE.md` and the task's named paths to frame one structural question. Read code to determine completion; mockups, docstrings and plans alone are insufficient evidence.

1. Call `codegraph_context` for the feature/task, or `codegraph_search` for an exact symbol lookup. Use `codegraph_files` for directory structure.
2. If needed, make one capped `codegraph_explore` for related symbol source. Use callers/callees/impact for the specific dependency question; include file paths to distinguish similarly named functions.
3. Trust indexed structure rather than re-grepping definitions. Use `rg`/direct reads for literal strings, configs/docs, or a concrete detail the graph does not expose. Do not delegate another exploration of the same area.
4. Trace input → validation → service → storage/output → actual caller. Report missing links, alternative legacy paths, provider/network dependencies and affected contracts. Distinguish a defined route from one the UI consumes.
5. Return only the relevant module paths, source evidence, reuse points and unresolved question. Do not edit files, rerun provider tests or inspect secrets during a read-only lookup. Investigate index/tool setup only on a concrete failure; preserve the existing configuration.
