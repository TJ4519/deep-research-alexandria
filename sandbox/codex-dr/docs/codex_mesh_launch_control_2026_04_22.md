# Codex Mesh Launch Control

Status: active correction
Date: 2026-04-22
Scope: `sandbox/codex-dr/`

## Correction

The prior `42,000` token target and token-manifest gate were runtime-control
leakage from earlier Alexandria work.

For the Codex-DR sandbox, the primitive is a live run-control receipt. The
receipt names the run, command surface, cwd, output roots, transcript capture,
foreground supervision, wall-clock bound, kill path, data policy, scorer status,
and allowed claims.

It may record token or cost estimates. It does not require a fixed token ceiling
as an architectural invariant.

## Why This Matters

The sandbox is meant to build a working Codex-based deep-research mesh:
planner, branch agents, reviewer pressure, re-entry, synthesis, report writing,
benchmark-facing cases, and scorer bridges.

Launch control exists to prevent hidden background burns and uncontrolled
retries. It must not become a substitute for building the orchestrator, role
adapters, run-bundle validator, benchmark lane, or adequacy loop.

## Current Halt

The halt on new `codex exec` launches remains active until the Principal
explicitly reopens a named run.

The reason for the halt is uncontrolled live-run launch discipline, not the
absence of a mechanical Codex CLI token cap.

## Reopen Conditions

A future live Codex CLI run may be reopened when all of these are true:

- the Principal names the run id or explicitly authorizes a class of runs;
- a run-control receipt exists for the run;
- the exact command or adapter is recorded before launch;
- the run is foreground-supervised or externally monitored;
- the wall-clock bound and kill path are explicit;
- retries are disabled unless separately approved;
- transcript capture and run-bundle output roots are explicit;
- data boundaries block secrets, customer data, env files, and unauthorized
  benchmark corpora;
- the expected claim boundary is written before launch.

## Non-Requirements

The Codex-DR sandbox does not require:

- a `42,000` token ceiling;
- a product-runtime token manifest;
- mechanical token or cost enforcement as a condition for building the mesh;
- service-runtime billing policy before benchmark-facing sandbox work can
  continue.

Those may become product/runtime concerns later. They are not the current
sandbox architecture center.

## Required Next Interpretation

Future architect and builder agents should treat `run-control receipt` as the
live-run gate.

Historical files that mention `token manifest` should be read as lineage from
the pre-correction interpretation unless they have been updated to cite
`live_run_control_receipt_template.md`.
