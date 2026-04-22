# Alexandria Cleanroom

Alexandria Cleanroom is the cleanroom repo for the reimagined Alexandria
deep-research runtime: a recursive research system with filesystem working
memory, event-complete orchestration, content-addressed artefacts, replay, and
pharma CI claim-to-source custody.

It is optimized for coding agents first:
- a small stable entry point
- progressive disclosure through indexes and plans
- mechanical rules for architecture and repo hygiene
- local-first development with pluggable infrastructure choices

## What This Repo Is For

- rebuilding the backend runtime from explicit repo-local authority
- validating the charter and plan through specification, implementation, and proof
- using local example corpora now while preserving a path to real deployment later
- hosting the first Codex-DR sandbox workspace for Grep-parity research-engine
  proof work under `sandbox/codex-dr/`

It is not:
- a wrapper around the historical repo
- a frontend project
- a place where architecture is inferred from chat history
- a place where old numbered NLSpecs govern the reimagining by inertia

Auxiliary tooling that is not part of the backend runtime may live under
`tools/` when it is explicitly documented and mechanically contained.

## Start Here

1. `ALEXANDRIA_CHARTER.md`
2. `PLAN_TO_CREATE_ALEXANDRIA.md`
3. `docs/design-docs/reimagined_alexandria_authority_ledger_2026_04_21.md`
4. `AGENTS.md`
5. `canon/CANON.md`
6. `data/SOURCES.md`
7. `ARCHITECTURE.md`
8. `docs/SYSTEM_MAP.md`
9. `docs/KNOWLEDGE_MAP.md`
10. `docs/README.md`

## Codex-DR Sandbox

The Codex-DR sandbox lives at `sandbox/codex-dr/`.

Use it for the architect lane that attempts full Grep-system-and-performance
parity through terminal-agent harnessing, recursive research coordination,
benchmark acquisition, adequacy backpressure, event/CAS custody, compaction
receipts, and allowed-claims proof.

Start there with:

1. `sandbox/codex-dr/AGENTS.md`
2. `sandbox/codex-dr/README.md`
3. `sandbox/codex-dr/docs/ARCHITECT_HANDOFF.md`

## Local Setup

```bash
uv python install 3.12
uv sync --group dev
make check
make lint
make test
```
