# Codex-DR Grep Parity Execution Ladder

Status: active work substrate
Date: 2026-04-23
Applies to: `sandbox/codex-dr/`

## Purpose

This document defines the execution ladder for the Alexandria Codex-DR sandbox.
It exists to prevent the DR mesh from collapsing into scattered local support
work.

The target is a Codex-cli native deep-research mesh at Grep-style functional
parity, under benchmark pressure, with evaluation-fed improvement and
Alexandria custody.

## Open Brain Retrieval Trigger

Before planning, delegation, bead creation, or architect launch for this lane,
search Open Brain for:

- `DR mesh`
- `Grep parity execution ladder`
- `Codex orchestrator spawning Codex workers`

The expected recovered memory is that Alexandria Codex-DR is a Codex-cli native
DR mesh flywheel: a Codex orchestrator runs benchmark-shaped research cases by
spawning scoped Codex worker agents into file-returning boxes, reading
`pointer.md` before `analysis.md`, looping on adequacy and reviewer re-entry,
scoring final answers, then converting evaluation failures into improvement
proposals and regression gates.

## Governing Object

The governing object is the **DR mesh**.

The DR mesh is not a prompt, a report generator, a filesystem demo, or a set of
small harness chores. It is a recursive research run architecture in which:

- the orchestrator owns run state, plan state, task graph state, claim state,
  and stop/continue decisions;
- planner work happens before the task graph is frozen;
- scoped Codex worker agents run in bounded workspaces;
- workers return files, not long authoritative chat payloads;
- the orchestrator reads pointers before deeper analysis;
- adequacy and reviewer pressure can create re-entry work;
- one writer owns final answer cohesion;
- benchmark scoring evaluates the answer after generation;
- evaluation failures feed improvement proposals and regression gates.

## Topology Authority

The three Principal-provided Grep figures are build authority for this lane:

1. Two-layer loop architecture: input, planner, plan file, skills/tools, task
   graph, inner research loop, evaluate/synthesize, writer, outer review loop,
   final report.
2. Inner-loop task dependency graph: parallel branches where possible,
   sequential edges where required, evaluate/synthesize, revision path, and
   review/fact-check before report writing.
3. File-based context economy: sub-agents write `pointer.md`, `analysis.md`,
   and `evidence` files; the orchestrator reads the pointer first and reads
   only needed analysis spans.

These figures are operational constraints. A run that omits the loop, file
returns, pointer-first orchestration, reviewer re-entry, scoring, or improvement
does not close the parity target.

## Pre-Flight Sequence

Every autonomous architect pass in this lane starts with this pre-flight:

1. Recover Open Brain memory using the retrieval trigger above.
2. Read this ladder, then `AGENTS.md`, `docs/BOOTSTRAP_DOCTRINE.md`,
   `docs/ARCHITECT_HANDOFF.md`, `harness-specs/dr_mesh_parity_charter.md`,
   and `harness-specs/grep_parity_contract.md`.
3. State the parity rung being advanced.
4. State the fake success that would look complete while missing that rung.
5. Confirm the allowed-claims boundary before execution.
6. Choose the smallest bead or implementation wave that advances the rung.

If a pass cannot name its rung, proof artifact, and invalid success condition,
it is not ready to start implementation.

## Orchestrator State Machine

The Codex orchestrator operates this state machine:

```text
INTENT
  -> PLAN
  -> TASK_GRAPH
  -> SPAWN_BRANCHES
  -> POINTER_READ
  -> SYNTHESIZE
  -> ADEQUACY_CHECK
  -> REENTER_OR_REVIEW
  -> WRITE_REPORT
  -> SCORE
  -> IMPROVE
  -> NEXT_BEAD
```

Required behavior:

- `PLAN` writes plan, skills/tools, adequacy criteria, and task graph.
- `SPAWN_BRANCHES` launches scoped Codex worker boxes where dependencies allow.
- `POINTER_READ` records which pointer files and analysis spans were admitted.
- `ADEQUACY_CHECK` can create new research tasks before writing.
- `REENTER_OR_REVIEW` compiles reviewer findings into re-entry tasks.
- `WRITE_REPORT` runs after re-entry obligations are resolved.
- `SCORE` reads scorer-only benchmark materials and sealed references.
- `IMPROVE` converts failures into replay fixtures, proposals, and regression
  gates.

## Inner Loop

The inner loop is research until adequacy:

1. Planner gathers context and emits the Plan File.
2. Orchestrator compiles the task graph.
3. Branch agents run in parallel where possible.
4. Branch agents return:
   - `pointer.md`
   - `analysis.md`
   - `evidence.jsonl`
5. Orchestrator reads `pointer.md` first.
6. Orchestrator admits selected analysis spans and evidence.
7. Orchestrator evaluates adequacy criteria.
8. If gaps remain, it spawns targeted follow-up tasks.

## Outer Loop

The outer loop is review, re-entry, and report quality:

1. Orchestrator writes synthesis from admitted evidence.
2. Reviewer checks synthesis against sources, task graph, and adequacy criteria.
3. Reviewer emits structured findings.
4. Required findings compile into re-entry tasks.
5. Re-entry workers return file triplets.
6. Orchestrator updates synthesis, contradictions, and claim ledger.
7. One writer produces the final answer.
8. Final answer is checked against claim custody and allowed claims.

## Benchmark Lifecycle

A benchmark row becomes a case, not a prompt blob.

For each benchmark case:

- the query and allowed metadata enter `case_manifest.json`;
- reference answers stay sealed from planner, branch, reviewer, and writer
  roles;
- rubric material is available only to the scorer path;
- the final report or answer becomes the candidate answer;
- scorer reads candidate answer, rubric, references, evidence, transcripts, and
  run manifests;
- scorer emits `draco_evaluation_output.json` or equivalent benchmark output;
- harness validates `benchmark_score.json`;
- `evaluation_ledger.json` records result status, failure classes, claim impact,
  and recommended improvement actions.

Benchmark claims remain blocked until a claim-review gate explicitly opens
them from scored evidence.

## Improvement Lifecycle

Evaluation failures become system improvement inputs:

1. Scorer or evaluator classifies failures.
2. Harness writes failure taxonomy and replay fixture references.
3. Improvement agent proposes prompt, role, task-graph, validator, or scoring
   changes.
4. Regression gate reruns prior passing fixtures.
5. Passing improvements become eligible for promotion.
6. Failed improvements remain recorded without mutating live prompts or claims.

No improvement proposal may auto-widen benchmark, parity, or product claims.

## Parity Rungs

Rung 1: Authority and memory wiring
- Open Brain trigger is wired into skills and sandbox read order.
- This ladder is in the sandbox read order.
- Future architect prompts must cite the rung they advance.

Rung 2: Orchestrator state machine hardening
- The CLI and validators enforce the state order.
- Illegal ordering fails validation.

Rung 3: Codex worker box harness
- Scoped workspaces, role prompts, file contracts, transcript capture, and
  output validation are durable and reusable.
- Codex CLI model promotion is receipt-backed. A model becomes eligible for
  live mesh default use only after `alexandria-dr model-probe` records an
  `available` receipt for that model.

Rung 4: Inner-loop adequacy recursion
- Adequacy gaps can create follow-up tasks before writing.
- Pointer-first reads and selective analysis admission are recorded.

Rung 5: Outer-loop reviewer re-entry
- Reviewer findings can force re-entry.
- Writer execution is blocked until re-entry decisions are resolved.

Rung 6: Benchmark case lifecycle
- Benchmark rows become sealed, executable case manifests.
- Generator roles cannot see reference answers or scorer-only rubrics.

Rung 7: Scorer-backed scored bundle
- Numeric score artifacts require scorer receipt, transcript references,
  evidence references, and valid evaluation output.
- Score claims remain blocked until claim review.

Rung 8: Claim-review gate
- A separate gate decides whether a scored bundle can widen public benchmark
  claims.
- Grep parity claims require more than one scored smoke.

Rung 9: Improvement flywheel
- Evaluation failures become replay fixtures, improvement proposals, and
  regression gates.

Rung 10: Multi-case parity pressure
- Multiple benchmark cases run through the same mesh.
- Results compare across cases without leaking references into generation.

## Invalid Success Conditions

These outputs may look useful while failing this ladder:

- a polished report without planner context gathering;
- branch prose without `pointer.md`, `analysis.md`, and `evidence.jsonl`;
- synthesis that reads full analysis files without pointer-first receipts;
- review that cannot create re-entry tasks;
- a writer that runs before re-entry obligations are resolved;
- benchmark discussion without executable case manifests and scorer custody;
- numeric scores without receipt, transcript, evidence, and evaluation-output
  validation;
- improvement proposals that skip replay fixtures and regression gates;
- parity claims from a single smoke run;
- product-readiness claims from sandbox-only proof.

## Architect Operating Law

Every architect pass must report:

- parity rung advanced;
- concrete artifacts changed;
- commands, tests, or runs executed;
- proof artifact produced;
- claims now allowed;
- claims still blocked;
- next bead or blocker.

If a pass produces no durable code, test, receipt, validator, bead, or proof
delta, it is not advancing the ladder.

## First Bead Wave

The first wave after this ladder was:

1. Wire memory and ladder authority into skill and sandbox read order.
2. Harden orchestrator state-machine validation around the live/scored mesh.
3. Promote benchmark case lifecycle from prose to manifest validation.
4. Complete scorer-backed scored-bundle claim gate.
5. Build the improvement replay promotion gate.

Each bead must name the parity rung it advances and the proof artifact that
closes it.

## Current Runway

As of 2026-04-24, the next runway is governed by
`AUTONOMOUS_PARITY_RUNWAY.md`.

The live mesh has dependency-aware branch scheduling, context/thread indexing,
adequacy backpressure, sealed DeepResearch Bench case import, official raw
report export with custody, and one validated live DeepResearch Bench case
through the corrected Grep-shaped loop. The corrected loop includes
post-review re-entry synthesis before the writer. It also has an official RACE
bridge that prepares the DeepResearch Bench scorer path and blocks cleanly
without provider authority. The one-case run now has run-owned blocked-score
claim review artifacts with Grep-v5 56.23 recorded as comparison-only. The
one-case run also compiles its scorer, reviewer, adequacy, and claim failures
into non-promoted improvement candidates for evaluator authority, prompt,
file-context, skill, and scheduler surfaces. Those candidates now have isolated
gate results and promotion receipts, with no live surface mutation. The next
proof is full-run packaging and Grep comparison gating. Multi-case pressure is
now present as a two-case DeepResearch Bench subset with raw report export,
blocked RACE receipt, suite claim review, failure taxonomy, and improvement
inputs. Full-run packaging is now present as a readiness package over the
official 100-row query file, with Grep-v5 56.23 recorded as comparison-only and
parity claims blocked until official scorer custody exists.

Before any score-bearing run or claim review, refresh official DeepResearch
Bench sources. The official evaluator lane is changing in 2026, and stale
Grep rank or score assumptions must not drive implementation.
