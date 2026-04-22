# Codex-DR Bootstrap Doctrine

Status: active doctrine
Date: 2026-04-22
Applies to: `sandbox/codex-dr/`

## Why This Exists

The first sandbox handoff was directionally right and too conceptual for an
autonomous build. It preserved the target, workspace, and benchmark spine, while
leaving the first executable path under-specified.

This doctrine prevents the architect from drifting into root repo gravity,
running hidden live agents, or converting Grep parity into more planning prose.

## Completion Object

The bootstrap object is a local-first, provider-off harness spine that proves
the sandbox can observe and validate its own research loop before any paid or
model-backed run is attempted.

The completed bootstrap state has:

- a centre-lock receipt
- run-bundle skeleton
- local fixture case
- fake planner output
- fake branch outputs
- fake reviewer finding
- re-entry task compilation
- claim ledger
- compaction receipt fixture
- allowed-claims file
- validators that fail when required pieces are missing

## Autonomy Readiness Gate

An architect agent is not ready for autonomous implementation until all of these
are true:

- It has read this doctrine, `AGENTS.md`, `README.md`, and
  `docs/ARCHITECT_HANDOFF.md` from this folder first.
- It has produced a short centre-lock receipt under `runs/` or `tmp/` stating
  the sandbox telos, fake success, root-doc role, and current non-claims.
- It has named which root surfaces are authority, donor material, historical
  proof, or out of scope for the current bead.
- It has a provider-off run-bundle validator plan.
- It has a live run-control receipt template for any later Codex CLI,
  terminal-agent, model-backed, benchmark-facing, or scorer run.

If any item is missing, the architect may write docs or tests for the missing
  gate. It may not start unattended or repeated live research runs.

## Root-Gravity Firewall

For this lane, `sandbox/codex-dr/` is the immediate centre of gravity.

Root documents provide authority, references, commands, and shared repo hygiene.
Existing runtime code, Program 80, Program 90, `one-shot-dr/`, and generated
proof receipts are donor material unless a bead explicitly promotes them into
the sandbox work scope.

The architect must not treat the most complete existing implementation as the
natural target.

## Provider-Off First Boot

The first executable lane is provider-off.

Build this sequence before any model-backed terminal-agent run:

1. `alexandria-dr init-case local_fixture_001`
   Creates a case directory with a fixed local prompt, expected artefacts, and
   no external calls.

2. `alexandria-dr bootstrap-plan local_fixture_001`
   Writes a deterministic fake Plan File, task graph, adequacy criteria, and
   event entries.

3. `alexandria-dr bootstrap-branch local_fixture_001 branch_a`
   Writes pointer, analysis, and evidence fixtures for one branch.

4. `alexandria-dr bootstrap-review local_fixture_001`
   Writes a reviewer finding that must trigger a re-entry task.

5. `alexandria-dr bootstrap-reentry local_fixture_001 review_001`
   Compiles the reviewer finding into a new task and records the decision.

6. `alexandria-dr bootstrap-report local_fixture_001`
   Writes synthesis, contradiction state, claim ledger, report, benchmark score
   placeholder, compaction receipt fixture, and allowed-claims output.

7. `alexandria-dr validate local_fixture_001`
   Fails if any required file, event, causal link, claim custody, review
   re-entry, compaction receipt, or allowed-claims boundary is missing.

Command names may be revised by the harness contract, but the sequence is
binding.

## Live Run Control

Every live Codex CLI, terminal-agent, benchmark-generation, scorer, or SDK-backed
run requires a run-control receipt before it starts.

The receipt must name:

- run purpose
- bead id
- command surface or terminal-agent runner
- expected artefacts
- operational bounds
- stop conditions
- input sources
- data policy
- transcript capture path
- compaction policy
- allowed claims if the run succeeds
- non-claims even if the run succeeds
- foreground supervision or external monitoring
- wall-clock bound
- kill path

The receipt may record token or cost estimates when useful. A fixed token
ceiling is not an architectural invariant for the Codex-mesh sandbox.

Any live run without this receipt is invalid. Benchmark execution is also
invalid until the provider-off bootstrap validator passes.

## Benchmark Role

Benchmark acquisition comes early as target calibration.

The acquisition audit tells the sandbox which benchmark families, datasets,
rubrics, and scoring constraints are real. It does not authorize immediate
benchmark execution.

Benchmark cases may enter the harness only after:

- provider-off bootstrap passes
- harness contracts exist
- live run-control receipt template exists
- benchmark acquisition audit classifies the dataset as usable

## Required Skills

The architect must use these skills at named moments:

- `center-of-gravity-recovery`: before reading broad root implementation or
  Program 90 surfaces.
- `teleological-pre-inference`: before changing scope, delegation, or autonomy.
- `teleology-preserving-planning`: before writing or revising parity, harness,
  or bootstrap contracts.
- `evidence-first-backpressure`: before benchmark, provider, SDK, or parity
  claims.
- `spec-interface-auditor`: before implementation begins from any contract.
- `bead-compiler`: only after the governing surface and proof gates are stable.

If a named skill is unavailable to a future agent, it must follow the equivalent
local protocol and record that fallback in the run or plan notes.

## Stop Rules

Stop and repair the governing surface if:

- the architect cannot state the sandbox telos without referring to Program 90
- a benchmark run is proposed before provider-off bootstrap passes
- a live run lacks a run-control receipt
- a report can be produced without a claim ledger
- a reviewer finding cannot cause re-entry
- compaction has no receipt
- a claim widens beyond the allowed-claims file
- root code begins defining the sandbox target by inertia

## Proof Artifact

The bootstrap proof artifact is a local run bundle under ignored `runs/` plus a
small committed validator or contract note showing what passed, what failed, and
which claims remain blocked.
