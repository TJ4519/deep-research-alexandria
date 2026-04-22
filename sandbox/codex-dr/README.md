# Codex-DR Sandbox

This workspace is the launch pad for the Codex-based Alexandria deep-research
sandbox.

The sandbox exists to instantiate a full Grep-style recursive deep-research
agent system using terminal-agent harnessing while preserving Alexandria's
custody discipline: event logs, immutable artefacts, compaction receipts,
claim ledgers, visible QA backpressure, and benchmark-facing proof.

## Why It Lives Here

The first workspace is inside the cleanroom repo because the architect needs
direct access to the charter, root plan, authority ledger, Grep references,
legacy proof receipts, and existing development commands.

A separate repo or worktree becomes appropriate when the sandbox begins
storing substantial generated runs, paid benchmark data, customer material,
secret-bearing configs, or implementation churn that would confuse the root
repo.

## What This Workspace Must Prove

The sandbox must attempt Grep-system-and-performance parity. That means:

- planner ratification of user intent and adequacy criteria
- planner context gathering before the plan is frozen
- task graph decomposition into sequential and parallel research work
- terminal-agent branch execution with scoped tools and skills
- branch agents that return pointer, analysis, and evidence files
- recursive evidence retrieval and branch deepening
- synthesis and contradiction reconciliation
- reviewer and fact-checker files that can push the run back into research
- single-voice report writing from reconciled research state
- benchmark scoring against Grep-cited benchmark families where obtainable
- event and artefact custody for every material orchestration step

## Current Directory Contract

- `AGENTS.md`: local instructions for future architect and builder agents.
- `docs/BOOTSTRAP_DOCTRINE.md`: autonomy, provider-off boot, live-run control,
  root-gravity firewall, and required skill gates.
- `docs/ARCHITECT_HANDOFF.md`: durable handoff memo and plan.
- `benchmark-manifests/`: benchmark acquisition and case-selection manifests.
- `cases/`: small non-private sandbox cases and benchmark wrappers.
- `harness-specs/`: contracts for CLI, terminal-agent boxes, events, artefacts,
  reviews, and run bundles.
- `runs/`: ignored generated run bundles.
- `tmp/`: ignored local scratch.

## Bootstrap Before Tokens

The first executable lane is provider-off.

Before any model-backed terminal-agent run, the sandbox must prove that it can
create and validate a run bundle using local fixtures:

1. centre-lock receipt
2. run-bundle skeleton
3. fake Plan File and task graph
4. fake branch pointer / analysis / evidence return
5. fake reviewer finding
6. re-entry task compiled from the finding
7. synthesis, contradiction state, claim ledger, report, compaction receipt,
   placeholder score, and allowed-claims file
8. validator that fails when custody, review re-entry, compaction, or allowed
   claims are missing

Benchmark acquisition still comes early. It calibrates the target and blocked
claims. Benchmark execution waits until the provider-off bootstrap validator
passes and a live run-control receipt exists.

## Expected CLI Shape

The CLI control surface is expected to be named `alexandria-dr`.

Initial commands should cover:

- `alexandria-dr bootstrap init local_fixture_001`
- `alexandria-dr bootstrap plan local_fixture_001`
- `alexandria-dr bootstrap branch local_fixture_001 branch_a`
- `alexandria-dr bootstrap review local_fixture_001`
- `alexandria-dr bootstrap reentry local_fixture_001 review_001`
- `alexandria-dr bootstrap report local_fixture_001`
- `alexandria-dr benchmark audit`
- `alexandria-dr init-case <case_id>`
- `alexandria-dr run-planner <case_id>`
- `alexandria-dr run-branch <case_id> <branch_id>`
- `alexandria-dr run-review <case_id>`
- `alexandria-dr run-reentry <case_id> <review_id>`
- `alexandria-dr validate <case_id>`
- `alexandria-dr score <case_id>`

The exact implementation may change after the contracts are written. The
control surface must remain visible and scriptable.

Live Codex CLI, terminal-agent, benchmark-generation, scorer, or SDK-backed
commands require a run-control receipt naming purpose, bead id, runner, expected
artefacts, operational bounds, stop conditions, input sources, data policy,
transcript capture path, compaction policy, allowed claims, non-claims,
foreground supervision or monitoring, wall-clock bound, and kill path.

The old `42,000` token target is not a sandbox architecture requirement.

## Proof Run Contract

Every proof run should emit a run bundle with:

- `run_manifest.json`
- `events.jsonl`
- `artefact_manifest.json`
- `plan.md`
- `task_graph.json`
- `adequacy_criteria.json`
- `branches/`
- `evidence/`
- `synthesis.md`
- `contradictions.json`
- `reviews/`
- `compactions/`
- `claim_ledger.json`
- `report.md`
- `benchmark_score.json`
- `allowed_claims.json`

The bundle is the memory. A future agent should be able to inspect it without
chat context.
