# Codex-DR First Full Proof Run

Status: active
Owner: Codex-DR sandbox architect-builder
Bead: `alexandriacleanroom-91.1.5`
Canon refs:
- `PLAN_TO_CREATE_ALEXANDRIA.md`
- `sandbox/codex-dr/harness-specs/grep_parity_contract.md`
- `sandbox/codex-dr/harness-specs/harness_contracts.md`
Constraining canon refs:
- `sandbox/codex-dr/AGENTS.md`
- `sandbox/codex-dr/docs/BOOTSTRAP_DOCTRINE.md`
- `sandbox/codex-dr/docs/ARCHITECT_HANDOFF.md`
- `sandbox/codex-dr/harness-specs/live_run_control_receipt_template.md`
- `sandbox/codex-dr/docs/codex_mesh_launch_control_2026_04_22.md`
- `sandbox/codex-dr/benchmark-manifests/benchmark_acquisition_audit.md`
- `docs/exec-plans/active/codex_dr_sandbox_architect_handoff.md`
- `docs/exec-plans/active/codex_dr_provider_off_bootstrap_implementation.md`
Workspace: `sandbox/codex-dr/`
Last updated: 2026-04-22

## Why This Plan Exists

The first full proof run must exercise the Grep-parity research loop rather
than only proving that provider-off fixtures can write files.

The provider-off bootstrap is now implemented. It is containment and evidence
infrastructure, not the system telos.

The next executable lane is boxed Codex recursive DRACO smoke: prove whether
this sandbox can launch a Codex/terminal-agent box with transcript capture,
select a tiny DRACO benchmark-facing case without committing raw data, prepare
a run-control receipt, run the smallest allowed recursive research
loop, and bridge to scoring or record the exact scorer blocker.

## Scope

Corrected next lane:

- boxed Codex runner capability probe;
- DRACO tiny smoke case manifest;
- run-control receipt;
- boxed recursive research smoke run;
- benchmark scoring bridge.

The smoke run must exercise planner context gathering, branch work,
pointer/analysis/evidence returns, synthesis, reviewer or fact-checker
pressure, re-entry, report creation, and benchmark-facing evaluation. A score
placeholder is acceptable only when the scoring bridge records the exact
external blocker.

## Non-Goals

- No fake benchmark execution.
- No unattended provider/model call before run-control receipt, operational
  bounds, stop rules, transcript policy, and kill path exist.
- No benchmark scoring before case manifest and scorer/judge policy exist.
- No Grep parity, benchmark score, leaderboard, or product-readiness claim.
- No root runtime or product service implementation.
- No additional provider-off guardrail work unless it directly enables the
  boxed smoke run.

## Preserved Invariants

- Provider-off bootstrap is containment/evidence infrastructure only.
- Live commands must fail closed without run-control approval.
- Benchmark scoring remains a placeholder unless the scoring bridge executes
  under an approved run-control/scorer policy.
- Public Grep/Parcha score claims must be classified by the orchestrator as
  target calibration only until Alexandria emits its own approved run evidence.
- Any generated scaffold output remains under ignored sandbox run/tmp paths.
- The provider-off bootstrap allowed claims remain the current ceiling.

## Pre-Mortem

- A future command stub silently becomes a provider call.
- The proof-run bead closes from provider-off scaffolding alone.
- A benchmark placeholder is treated as a real score.
- A public Grep/Parcha score is treated as Alexandria evidence instead of
  target calibration.
- A local CLI help/version probe is mistaken for a boxed recursive research
  run.
- A DRACO case is copied into git instead of referenced through a tiny manifest.
- The first full run starts without case, scorer, run-control, and custody
  manifests.
- Allowed claims widen beyond the actual proof.

## Red/Green TDD Plan

Red:

- boxed Codex runner capability is unknown;
- DRACO smoke case manifest is absent;
- no run-control receipt exists;
- no boxed recursive research smoke run bundle exists;
- no benchmark scoring bridge exists;
- proof-run bead remains open until a real allowed run executes.

Green:

- capability probe records whether Codex/terminal-agent box launch and
  transcript capture are available from this sandbox;
- DRACO tiny smoke case manifest records source pointer without committing raw
  or large data;
- run-control receipt records operational bounds, stop rules, transcript policy,
  provider/tool policy, supervision, kill path, allowed claims, and non-claims;
- smoke run emits planner, branch, synthesis, review/re-entry, report, event,
  artifact, claim, and allowed-claims custody;
- scoring bridge records exact scorer/judge path or exact blocker;
- `uv run pytest sandbox/codex-dr/tests`, `git diff --check`, and `make check`
  pass

## Proof Posture

Provider-off scaffolding is complete enough to stop being the active center.
The active proof posture is boxed Codex DRACO smoke, gated by runner
capability, case manifest, run-control receipt, and scorer policy.

The current proof ceiling remains deterministic provider-off fixture generation
until a real boxed smoke run emits a custody bundle.

## Temporary Seams

- The script path remains `sandbox/codex-dr/tools/alexandria_dr.py` until a
  packaging bead promotes it to a console script.
- `benchmark_score.json` remains a placeholder unless the scoring bridge
  executes under approved run-control/scorer policy.
- Real terminal-agent runner selection is still evidence-pending.

## Repo Orientation

Continue from `sandbox/codex-dr/`. Use root commands only for validation and
bead state. Do not touch root runtime, product service code, Program 80/90
generated proof artifacts, env files, or raw/large data.

## Plan Of Attack

1. Create `alexandriacleanroom-91.1.5.1` for boxed Codex runner capability
   probe.
2. Create `alexandriacleanroom-91.1.5.2` for DRACO tiny smoke case manifest.
3. Create `alexandriacleanroom-91.1.5.3` for run-control receipt.
4. Create `alexandriacleanroom-91.1.5.4` for boxed recursive research smoke
   run.
5. Create `alexandriacleanroom-91.1.5.5` for benchmark scoring bridge.
6. Execute the next unblocked safe bead immediately: the capability probe.
7. Continue to DRACO case manifest only after the probe result is repo-local.

## Progress Log

- 2026-04-22: Created first full proof-run ExecPlan after provider-off
  bootstrap closed. Scoped current work to provider-off command-gate
  scaffolding only.
- 2026-04-22: Added provider-backed command stubs for `run-planner`,
  `run-branch`, `run-review`, `run-reentry`, and `score`; each fails closed
  before run-control approval. Added tests proving these commands do not
  create provider metadata or transcript artifacts.
- 2026-04-22: Principal/main coordinator corrected trajectory. The active
  center is now boxed Codex recursive DRACO smoke. Provider-off runtime
  guardrails are not progress unless they directly enable that boxed run.
- 2026-04-22: Created `91.1.5.1` through `91.1.5.5` for runner probe, DRACO
  tiny smoke manifest, run-control receipt, boxed recursive smoke run,
  and scoring bridge. Completed `91.1.5.1`, `91.1.5.2`, and `91.1.5.3`.
  `91.1.5.4` was initially blocked before provider spend because the lane
  incorrectly treated a fixed token cap as a hard architectural gate.
- 2026-04-22: Principal explicitly authorized one smoke run. Ran
  `draco_smoke_001` through `codex exec --full-auto` with transcript capture.
  The run emitted the required smoke bundle under ignored
  `sandbox/codex-dr/runs/draco_smoke_001/`, including three branch returns,
  review-triggered re-entry, report, claim ledger, placeholder benchmark score,
  allowed claims, event log, and artefact manifest. Coordinator validation
  found no missing files, JSON/JSONL envelope failures, missing event outputs,
  missing required event types, or hash mismatches after the transcript closed.
- 2026-04-22: Recorded tracked receipts:
  `sandbox/codex-dr/docs/draco_smoke_001_run_receipt_2026_04_22.md` and
  `sandbox/codex-dr/docs/draco_smoke_001_scoring_bridge_2026_04_22.md`.
  The scoring bridge closes the score question as blocked, not scored.
- 2026-04-22: Principal correction accepted. The `42,000` token target and
  token-manifest gate were runtime-control leakage. Future live Codex-mesh work
  uses run-control receipts, foreground supervision or monitoring, wall-clock
  bounds, kill paths, transcript capture, output boundaries, and claim
  boundaries. Fixed token ceilings are optional operational estimates.

## Decision Log

- 2026-04-22: Do not close `alexandriacleanroom-91.1.5` from provider-off
  scaffolding alone. The bead's acceptance requires a complete proof run, and
  real provider-backed/benchmark execution is still gated.
- 2026-04-22: Standalone child beads under `91.1.5.*` own the corrected runway.
  Do not hide runner probe, DRACO manifest, run-control receipt, smoke run, or
  scoring bridge work inside generic notes.
- 2026-04-22: Superseded. The earlier decision to block `draco_smoke_001` until
  a Codex CLI budget/cost-cap mechanism existed is no longer the governing
  interpretation for Codex-DR. Reopened live runs require run-control approval,
  supervision or monitoring, timeout and kill path, and claim discipline.
- 2026-04-22: Treat `draco_smoke_001` as a completed boxed smoke run with a
  blocked score. The run may support only the claims in its
  `allowed_claims.json`; it does not support Grep parity, DRACO scoring,
  leaderboard rank, product readiness, systematic adoption rates, or
  methodological dominance in the requested AER/QJE/JPE corpus.
- 2026-04-22: Treat the observed `270,716` token use as a live-run control
  finding. Future provider-backed benchmark runs need named authorization,
  run-control receipt, foreground supervision or monitoring, wall-clock bound,
  kill path, and no automatic retries.

## Validation

Expected provider-off commands:

```text
bd --no-daemon show alexandriacleanroom-91.1.5.1
uv run pytest sandbox/codex-dr/tests
uv run python sandbox/codex-dr/tools/alexandria_dr.py bootstrap-run local_fixture_001
uv run python sandbox/codex-dr/tools/alexandria_dr.py validate local_fixture_001
git diff --check
make check
```

Observed boxed-smoke validation:

```json
{
  "missing": [],
  "json_bad": [],
  "jsonl_bad": [],
  "missing_event_outputs": [],
  "missing_event_types": [],
  "hash_bad": [],
  "branch_count": 3,
  "benchmark_score": null,
  "benchmark_scored": false,
  "tokens_used_observed": "270,716"
}
```

## Open Questions

- Which terminal-agent runner will be approved for the first real proof run?
- Which benchmark family, if any, will be selected first after run-control
  approval?
- What run-control, stop rules, transcript policy, and scorer bridge will the
  Principal approve?

## Completion Criteria

This bead can close only when:

- a complete proof run emits the required bundle from actual allowed execution
- validators fail on missing custody, review re-entry, benchmark score, and
  report claims without custody
- `allowed_claims.json` matches the actual proof
- `make check` passes
- no claim exceeds the emitted proof

## Non-Claims

- Provider-off command scaffolding is not a full proof run.
- No benchmark or provider-backed performance claim is available yet.
- No product service readiness claim is available.
