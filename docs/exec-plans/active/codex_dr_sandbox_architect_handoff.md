# Codex-DR Sandbox Architect Handoff

Status: active
Owner: Principal / sandbox architect
Bead: `alexandriacleanroom-91.1.1` through `alexandriacleanroom-91.1.6`
Canon refs:
- `ALEXANDRIA_CHARTER.md`
- `PLAN_TO_CREATE_ALEXANDRIA.md`
- `docs/design-docs/reimagined_alexandria_authority_ledger_2026_04_21.md`
Constraining canon refs:
- `docs/design-docs/codex_dr_sandbox_architect_handoff_2026_04_22.md`
- `sandbox/codex-dr/AGENTS.md`
- `sandbox/codex-dr/docs/ARCHITECT_HANDOFF.md`
- `docs/references/grep_building_grep_deep_research_2026_03_16.md`
- `docs/references/claude_in_a_box_grep_agents_sdk_2025_12_11.md`
Workspace: `sandbox/codex-dr/`
Last updated: 2026-04-22

## Why This Plan Exists

The Codex-DR sandbox needs an architect who can build a full Grep-style
recursive deep-research system with benchmark pressure, QA backpressure, and
Alexandria custody. That architect needs a durable footing before delegation or
implementation begins.

This ExecPlan defines the workspace, first empirical audit, architecture
sequence, proof gates, and boundaries.

## Scope

- Establish `sandbox/codex-dr/` as the first architect workspace.
- Keep root repo authority visible while avoiding Program 90 gravity.
- Perform benchmark acquisition audit before parity claims harden.
- Specify the full sandbox contracts before implementation expands.
- Implement the first full proof run once contracts are defined.
- Produce a service-runtime bridge memo after proof-run evidence exists.

## Non-Goals

- Do not create the client-facing product runtime in this lane.
- Do not claim Grep parity from the existence of a harness.
- Do not store secrets, private benchmark data, customer data, or raw paid
  corpora in git.
- Do not mutate root runtime code without a bead that explicitly widens scope.

## Preserved Invariants

- The sandbox target is Grep-system-and-performance parity pressure.
- The first proof run must exercise the full research loop.
- Alexandria custody applies to terminal-agent runs through wrapper events,
  artefact manifests, compaction receipts, claim ledgers, and allowed-claims
  output.
- Benchmark claims require acquired datasets, recorded versions, evaluator
  shape, and reproducible scores.
- Product-runtime claims require a separate service-runtime design lane.

## Pre-Mortem

The main failure is local-demo collapse: a plausible harness proves that files
can be written while leaving recursive research cognition thin.

Other failure modes:

- benchmark public material is incomplete or differs from Grep's private setup
- terminal-agent transcripts cannot support custody without wrapper capture
- root docs overload future agents and reintroduce Program 90 assumptions
- compaction loses provenance
- reviewer findings become editorial suggestions instead of re-entry tasks
- benchmark scoring becomes a hand-written judgment with no manifest
- sandbox success is overstated as product readiness

## Red/Green TDD Plan

Red:

- a future architect cannot locate the sandbox workspace from root docs
- a benchmark claim appears before acquisition audit
- a run produces a report without `events.jsonl`, `artefact_manifest.json`,
  `claim_ledger.json`, and `benchmark_score.json`
- reviewer findings cannot re-enter research
- generated runs are staged for git

Green:

- root and sandbox docs route agents to `sandbox/codex-dr/`
- benchmark acquisition audit exists and names permitted and blocked claims
- contracts exist for CLI, run bundles, terminal-agent boxes, event mirroring,
  compaction receipts, branch returns, review, re-entry, and scoring
- first full proof run emits the required bundle
- allowed-claims output matches the actual proof

## Proof Posture

`TARGET_ONLY` until the benchmark acquisition audit, parity contract, harness
contracts, first full proof run, and allowed-claims artifact exist.

## Temporary Seams

- The sandbox has no implementation yet.
- Benchmark acquisition has not been performed.
- The CLI name `alexandria-dr` is selected, while exact command arguments may
  change through contract work.
- Root charter and root plan remain candidate surfaces until Principal
  ratification.

## Repo Orientation

Start in `sandbox/codex-dr/` for this lane. Read the local `AGENTS.md`,
`README.md`, and `docs/ARCHITECT_HANDOFF.md` before designing or coding.

Use the root repo for shared authority, references, Beads, ExecPlans, commands,
and validation. Treat Program 90 as historical evidence unless a bead says the
scope includes Program 90 integration.

## Plan Of Attack

1. Handoff footing.
   Create local sandbox instructions, root pointers, design memo, and this
   ExecPlan.

2. Benchmark Acquisition Audit.
   Produce `sandbox/codex-dr/benchmark-manifests/benchmark_acquisition_audit.md`
   and any machine-readable manifest needed for case selection.

3. Parity Contract.
   Produce `sandbox/codex-dr/harness-specs/grep_parity_contract.md` defining
   system behaviors, benchmark obligations, proof gates, and non-claims.

4. Harness Contracts.
   Specify the CLI, run bundle, event envelope, CAS manifest, compaction
   receipt, terminal-agent box config, branch return files, review files,
   re-entry compiler, claim ledger, and benchmark score format.

5. Implementation Wave.
   Build the CLI and harness in the narrowest code location that preserves root
   repo hygiene. Implementation may use internal stepping stones, while the
   acceptance target remains the full run.

6. First Full Proof Run.
   Execute one complete run with planner, branches, synthesis, review, re-entry,
   final report, benchmark scoring, and allowed-claims output.

7. Service Runtime Bridge.
   Classify contracts as promotable, hardening-required, sandbox-only, or
   service-runtime replacement.

## Progress Log

- 2026-04-22: Created `sandbox/codex-dr/`, local handoff docs, root pointers,
  design memo, this ExecPlan, and the bead chain for the sandbox lane.

## Decision Log

- 2026-04-22: The first architect workspace lives inside the cleanroom repo at
  `sandbox/codex-dr/` so it can reuse root authority and commands.
- 2026-04-22: A separate repo or worktree is deferred until generated-run
  volume, private data, secrets, or parallel write conflicts justify it.
- 2026-04-22: Benchmark acquisition audit is the first substantive architect
  move because parity claims depend on public benchmark reality.

## Validation

Run during or after handoff-footing changes:

- `bd ready --no-daemon`
- `make check`
- `git status --short`

Implementation waves should add their own tests before writing runtime code.

## Open Questions

- Which benchmark datasets can be obtained and run under acceptable license
  terms?
- Does Parcha publish enough benchmark configuration for strict comparison, or
  must Alexandria record a weaker public-benchmark parity claim?
- Which terminal-agent runner gives the best transcript and tool-call capture
  for custody?
- When does `sandbox/codex-dr/` need to graduate into a separate repo or
  worktree?

## Completion Criteria

This ExecPlan can close when:

- sandbox workspace instructions are present and indexed
- benchmark acquisition audit is complete
- parity contract is complete
- harness contracts are complete
- implementation beads are created with pre-mortem and red/green TDD
- first full proof run has a run bundle and allowed-claims artifact
- service-runtime bridge memo exists
