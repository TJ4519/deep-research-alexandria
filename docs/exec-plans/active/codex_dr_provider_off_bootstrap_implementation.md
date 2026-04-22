# Codex-DR Provider-Off Bootstrap Implementation

Status: active
Owner: Codex-DR sandbox architect-builder
Bead: `alexandriacleanroom-91.1.4.1`
Canon refs:
- `PLAN_TO_CREATE_ALEXANDRIA.md`
- `sandbox/codex-dr/docs/BOOTSTRAP_DOCTRINE.md`
- `sandbox/codex-dr/harness-specs/grep_parity_contract.md`
- `sandbox/codex-dr/harness-specs/harness_contracts.md`
Constraining canon refs:
- `sandbox/codex-dr/AGENTS.md`
- `sandbox/codex-dr/docs/ARCHITECT_HANDOFF.md`
- `sandbox/codex-dr/harness-specs/token_manifest_template.md`
- `sandbox/codex-dr/benchmark-manifests/benchmark_acquisition_audit.md`
- `docs/exec-plans/active/codex_dr_sandbox_architect_handoff.md`
Workspace: `sandbox/codex-dr/`
Last updated: 2026-04-22

## Why This Plan Exists

The Codex-DR sandbox must prove it can observe and validate its own research
loop before any provider-backed terminal-agent run, model call, or benchmark
execution.

This plan implements the provider-off bootstrap harness required by
`BOOTSTRAP_DOCTRINE.md`: a deterministic local run bundle with custody, causal
linkage, review re-entry, compaction receipt, claim ledger, benchmark-score
placeholder, and allowed-claims boundaries.

## Scope

Owned implementation paths:

- `sandbox/codex-dr/tools/`
- `sandbox/codex-dr/tests/`
- ignored generated outputs under `sandbox/codex-dr/runs/` and
  `sandbox/codex-dr/tmp/`

Allowed root writes:

- this ExecPlan
- bead updates through `bd --no-daemon`

## Non-Goals

- No root runtime code changes.
- No Program 80/90 artifact changes.
- No product service runtime implementation.
- No provider-backed/model-backed calls.
- No terminal-agent research runs.
- No benchmark execution.
- No secrets, customer data, private corpora, or large/raw benchmark data.

## Preserved Invariants

- Provider-off bootstrap comes before provider-backed execution.
- Generated run outputs stay under ignored sandbox paths.
- Benchmark score is a placeholder until benchmark gates pass.
- Allowed claims narrow to exactly what the local fixture proves.
- Review findings that require re-entry must alter the research state.

## Pre-Mortem

- The fixture writes the right filenames but omits causal event links.
- The validator checks only file presence and misses semantic drift.
- Reviewer findings become decorative and do not compile into re-entry tasks.
- `benchmark_score.json` accidentally looks like a real score.
- `allowed_claims.json` permits a wider claim than the provider-off run proves.
- Generated run output is created under a tracked path.
- Future provider-backed commands become reachable before token-manifest gates.

## Red/Green TDD Plan

Red checks must demonstrate failure for:

- missing `events.jsonl`
- missing required event type
- disconnected causal event chain
- missing branch pointer/analysis/evidence triplet
- missing review re-entry decision
- missing compaction receipt
- numeric benchmark score in provider-off placeholder
- allowed claim containing a blocked benchmark/parity/provider/product claim

Green checks pass when:

- `bootstrap-run local_fixture_001` creates the full run bundle under
  `sandbox/codex-dr/runs/local_fixture_001/`
- `validate local_fixture_001` writes `validation_report.json` with
  `status=passed`
- the validator reports the named checks from
  `harness-specs/harness_contracts.md`
- negative tests mutate copied fixture bundles and fail for the expected reason
- `git diff --check`, `make check`, and the bootstrap validation command pass

## Proof Posture

Provider-off fixture proof only.

This implementation can support the claim that the sandbox emits and validates
a deterministic local fixture run bundle. It cannot support Grep parity,
benchmark performance, provider-backed behavior, or product readiness.

## Temporary Seams

- The stable CLI name is `alexandria-dr`, while this slice may expose it as
  `uv run python sandbox/codex-dr/tools/alexandria_dr.py`.
- Provider-backed commands remain reserved and blocked.
- The fixture uses deterministic local evidence rather than real research.

## Repo Orientation

Work starts in `sandbox/codex-dr/`.

Use root commands for validation. Do not touch root runtime, app code,
Program 80/90 generated proofs, legacy NLSpecs, env files, provider secrets, or
large/raw data.

## Plan Of Attack

1. Add failing validator tests under `sandbox/codex-dr/tests/` against invalid
   bundle mutations.
2. Implement a provider-off CLI script under `sandbox/codex-dr/tools/` using
   only the Python standard library.
3. Generate deterministic fixture artifacts matching
   `harness-specs/harness_contracts.md`.
4. Implement validation checks for required files, event chain, artifact
   hashes, branch triplets, review re-entry, compaction, benchmark placeholder,
   claim ledger, allowed claims, and generated-path safety.
5. Run red/green tests and a real provider-off fixture validation.
6. Keep generated fixture output under ignored `sandbox/codex-dr/runs/`.
7. Close `alexandriacleanroom-91.1.4.1` only if acceptance criteria pass.

## Progress Log

- 2026-04-22: Created implementation ExecPlan before code changes.
- 2026-04-22: Added red/green provider-off validator tests under
  `sandbox/codex-dr/tests/`, implemented the deterministic bootstrap harness
  under `sandbox/codex-dr/tools/alexandria_dr.py`, and verified
  `bootstrap-run local_fixture_001` plus `validate local_fixture_001` passes
  without provider/model calls or benchmark execution.

## Decision Log

- 2026-04-22: Implemented the first CLI surface as a repo-local Python script
  rather than a package entrypoint so the provider-off proof can land without
  root packaging changes.
- 2026-04-22: Treated validation as an external report over the run bundle
  rather than an event-log mutation, so the validator can check event-log hashes
  without changing them.

## Validation

Expected commands:

```text
uv run pytest sandbox/codex-dr/tests
uv run python sandbox/codex-dr/tools/alexandria_dr.py bootstrap-run local_fixture_001
uv run python sandbox/codex-dr/tools/alexandria_dr.py validate local_fixture_001
uv run ruff check sandbox/codex-dr/tools sandbox/codex-dr/tests
git diff --check
make check
```

## Open Questions

- Should a later packaging bead expose `alexandria-dr` as a console script?
- Which provider-backed runner will later satisfy transcript-to-event and
  transcript-to-CAS custody without weakening the provider-off semantics?

## Completion Criteria

- Provider-off local fixture run can be created without model/provider calls.
- Run emits the bootstrap bundle required by `BOOTSTRAP_DOCTRINE.md`.
- Validators fail on missing events, missing event type, disconnected causal
  chain, missing branch triplet, missing review re-entry, missing compaction
  receipt, numeric benchmark placeholder, or widened claims.
- Generated run outputs remain under ignored sandbox paths.
- `uv run pytest sandbox/codex-dr/tests`, bootstrap validation command,
  `git diff --check`, and `make check` pass.

## Non-Claims

- This implementation does not run a provider, model, terminal agent, or
  benchmark.
- This implementation does not claim Grep parity or benchmark performance.
- This implementation does not establish product service readiness.
