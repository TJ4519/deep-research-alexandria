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
- `sandbox/codex-dr/harness-specs/token_manifest_template.md`
- `sandbox/codex-dr/benchmark-manifests/benchmark_acquisition_audit.md`
- `docs/exec-plans/active/codex_dr_sandbox_architect_handoff.md`
- `docs/exec-plans/active/codex_dr_provider_off_bootstrap_implementation.md`
Workspace: `sandbox/codex-dr/`
Last updated: 2026-04-22

## Why This Plan Exists

The first full proof run must exercise the Grep-parity research loop rather
than only proving that provider-off fixtures can write files.

The provider-off bootstrap is now implemented, so the next work can prepare the
full-run surface. Actual provider-backed research, terminal-agent execution,
and benchmark scoring remain blocked until a run-specific token manifest and
explicit approval gate exist.

## Scope

Provider-off scaffolding allowed now:

- keep the `alexandria-dr` control surface visible
- make future provider-backed commands fail closed before approval
- preserve the full run bundle formats already implemented
- add tests that prove blocked commands do not start execution
- record the exact remaining gate for the real proof run

Future full-run scope after approval:

- planner execution
- branch research
- recursive deepening
- synthesis
- review and re-entry
- report creation
- benchmark scoring or placeholder replacement
- allowed-claims output from actual evidence

## Non-Goals

- No provider/model calls in this provider-off scaffolding pass.
- No terminal-agent research execution.
- No benchmark execution.
- No Grep parity, benchmark score, leaderboard, or product-readiness claim.
- No root runtime or product service implementation.

## Preserved Invariants

- Provider-backed commands must fail closed without token-manifest approval.
- Benchmark scoring must remain a placeholder until benchmark gates pass.
- Any generated scaffold output remains under ignored sandbox run/tmp paths.
- The provider-off bootstrap allowed claims remain the current ceiling.

## Pre-Mortem

- A future command stub silently becomes a provider call.
- The proof-run bead closes from provider-off scaffolding alone.
- A benchmark placeholder is treated as a real score.
- The first full run starts without case, scorer, token, and custody manifests.
- Allowed claims widen beyond the actual proof.

## Red/Green TDD Plan

Red:

- invoking future provider-backed commands without approval must fail
- no provider metadata, transcript, token manifest, or benchmark score appears
  as a side effect of a blocked command
- the proof-run bead remains open after provider-off scaffolding

Green:

- provider-backed command stubs fail closed with a clear error
- provider-off bootstrap validation still passes
- `uv run pytest sandbox/codex-dr/tests`, `git diff --check`, and `make check`
  pass

## Proof Posture

Provider-off scaffolding only until Principal approval and a run-specific token
manifest exist.

The current proof ceiling remains: deterministic local fixture generation and
validation.

## Temporary Seams

- The script path remains `sandbox/codex-dr/tools/alexandria_dr.py` until a
  packaging bead promotes it to a console script.
- `benchmark_score.json` remains a placeholder in provider-off runs.
- Real terminal-agent runner selection is still evidence-pending.

## Repo Orientation

Continue from `sandbox/codex-dr/`. Use root commands only for validation and
bead state. Do not touch root runtime, product service code, Program 80/90
generated proof artifacts, env files, or raw/large data.

## Plan Of Attack

1. Add tests that future provider-backed commands fail closed.
2. Add explicit fail-closed command stubs to the local CLI script.
3. Re-run provider-off bootstrap validation and root checks.
4. Leave `alexandriacleanroom-91.1.5` open unless a real full proof run can be
   executed under an approved token manifest without violating gates.

## Progress Log

- 2026-04-22: Created first full proof-run ExecPlan after provider-off
  bootstrap closed. Scoped current work to provider-off command-gate
  scaffolding only.
- 2026-04-22: Added provider-backed command stubs for `run-planner`,
  `run-branch`, `run-review`, `run-reentry`, and `score`; each fails closed
  before token-manifest approval. Added tests proving these commands do not
  create provider metadata or transcript artifacts.

## Decision Log

- 2026-04-22: Do not close `alexandriacleanroom-91.1.5` from provider-off
  scaffolding alone. The bead's acceptance requires a complete proof run, and
  real provider-backed/benchmark execution is still gated.

## Validation

Expected provider-off commands:

```text
uv run pytest sandbox/codex-dr/tests
uv run python sandbox/codex-dr/tools/alexandria_dr.py bootstrap-run local_fixture_001
uv run python sandbox/codex-dr/tools/alexandria_dr.py validate local_fixture_001
git diff --check
make check
```

## Open Questions

- Which terminal-agent runner will be approved for the first real proof run?
- Which benchmark family, if any, will be selected first after token-manifest
  approval?
- What provider budget, stop rules, and transcript policy will the Principal
  approve?

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
