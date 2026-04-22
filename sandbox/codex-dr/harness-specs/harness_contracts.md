# Codex-DR Harness Contracts

Status: active contract for `alexandriacleanroom-91.1.4`
Date: 2026-04-22
Workspace: `sandbox/codex-dr/`

## Purpose

This file specifies the provider-off and future provider-backed harness
contracts for the Codex-DR sandbox.

The implementation bead may build against this file without inventing file
formats, command semantics, validation hooks, or failure behavior.

## Authority Inputs

- `sandbox/codex-dr/docs/BOOTSTRAP_DOCTRINE.md`
- `sandbox/codex-dr/docs/ARCHITECT_HANDOFF.md`
- `sandbox/codex-dr/harness-specs/grep_parity_contract.md`
- `sandbox/codex-dr/harness-specs/live_run_control_receipt_template.md`
- `sandbox/codex-dr/benchmark-manifests/benchmark_acquisition_audit.md`
- `../../docs/exec-plans/active/codex_dr_sandbox_architect_handoff.md`

## Contract Principles

- Provider-off first. Bootstrap commands must not call models, providers,
  terminal agents, benchmarks, network search, or paid services.
- Bundle as memory. A future reviewer must be able to inspect a completed run
  bundle without chat context.
- Event before claim. Every material artifact and decision must have causal
  event linkage before it can support a claim.
- Pointer before analysis. Branch returns must include pointer, analysis, and
  evidence files; orchestration reads pointer first.
- Reviews can change research. A qualifying review finding must compile into a
  re-entry task or an explicit no-reentry decision with rationale.
- Fail closed. Missing custody, missing linkage, missing re-entry, missing
  compaction, fake benchmark scores, or widened claims fail validation.

## CLI Contract

The stable control surface is named `alexandria-dr`.

During early implementation, the command may be exposed as a repo-local Python
script if no package entrypoint exists. The observable command behavior must
match this contract.

### Provider-Off Bootstrap Commands

| Command | Required effect | Valid when |
| --- | --- | --- |
| `alexandria-dr init-case <case_id>` | Create a run bundle skeleton for `<case_id>` under `sandbox/codex-dr/runs/<case_id>/`. | Case directory does not already contain a completed run unless `--force` is explicitly supplied. |
| `alexandria-dr bootstrap-plan <case_id>` | Write deterministic fake plan, adequacy criteria, task graph, terminal-agent box placeholders, and events. | Run exists and has no provider-backed marker. |
| `alexandria-dr bootstrap-branch <case_id> <branch_id>` | Write branch manifest, pointer, analysis, evidence, artifact manifest entries, and events for one branch. | Branch id exists in task graph or is added as a deterministic bootstrap branch. |
| `alexandria-dr bootstrap-review <case_id>` | Write a reviewer file containing at least one finding that requires re-entry. | Report draft or synthesis placeholder exists. |
| `alexandria-dr bootstrap-reentry <case_id> <review_id>` | Compile the reviewer finding into a research task and record the decision. | Review finding has `requires_reentry: true`. |
| `alexandria-dr bootstrap-report <case_id>` | Write synthesis, contradictions, report outline, report, claim ledger, compaction receipt, benchmark-score placeholder, allowed claims, and events. | Plan, at least one branch, review, and re-entry decision exist. |
| `alexandria-dr bootstrap-run <case_id>` | Execute all provider-off bootstrap steps in deterministic order. | Used by tests and future operators for one-command fixture creation. |
| `alexandria-dr validate <case_id>` | Validate the run bundle and write `validation_report.json`. | Never mutates substantive run artifacts except the validation report. |

### Future Provider-Backed Commands

These are reserved and blocked until provider-off validation passes and a
run-control receipt exists:

- `alexandria-dr run-planner <case_id> --run-control <path>`
- `alexandria-dr run-branch <case_id> <branch_id> --run-control <path>`
- `alexandria-dr run-review <case_id> --run-control <path>`
- `alexandria-dr run-reentry <case_id> <review_id> --run-control <path>`
- `alexandria-dr score <case_id> --run-control <path>`

If invoked before gates pass, these commands must fail closed and emit no
provider calls.

## Run Bundle Contract

All generated run outputs live under ignored paths:

```text
sandbox/codex-dr/runs/<case_id>/
```

Required run bundle tree:

```text
run_manifest.json
events.jsonl
artefact_manifest.json
plan.md
adequacy_criteria.json
task_graph.json
terminal_agent_boxes.json
branches/
  <branch_id>/
    branch_manifest.json
    pointer.md
    analysis.md
    evidence.jsonl
evidence/
adequacy_assessments.jsonl
synthesis.md
contradictions.json
report_outline.md
reviews/
  <review_id>.json
reentry_decisions.jsonl
claim_ledger.json
compactions/
  <compaction_id>.json
report.md
benchmark_score.json
allowed_claims.json
validation_report.json
```

Provider-backed or benchmark runs add:

```text
run_control_receipt.yaml
case_manifest.json
scorer_manifest.json
provider_metadata.json
transcripts/
```

## Common JSON Rules

- Every JSON object uses `schema_version`.
- Every generated artifact uses `run_id`.
- Every event-linked object uses `produced_by_event`.
- Arrays are ordered when order carries causal meaning.
- IDs are stable ASCII strings matching `[a-z0-9][a-z0-9_-]*`.
- Timestamps are ISO-8601 UTC strings. Provider-off bootstrap may use
  deterministic fixture timestamps.
- Paths are relative to the run bundle root unless explicitly absolute.
- Unknown fields are permitted only under `extensions`.

## Run Manifest

File: `run_manifest.json`

```json
{
  "schema_version": "codex-dr.run_manifest.v1",
  "run_id": "local_fixture_001",
  "case_id": "local_fixture_001",
  "mode": "provider_off_bootstrap",
  "created_at": "2026-04-22T00:00:00Z",
  "authority": {
    "bootstrap_doctrine": "sandbox/codex-dr/docs/BOOTSTRAP_DOCTRINE.md",
    "parity_contract": "sandbox/codex-dr/harness-specs/grep_parity_contract.md",
    "harness_contracts": "sandbox/codex-dr/harness-specs/harness_contracts.md"
  },
  "provider_calls_allowed": false,
  "benchmark_execution_allowed": false,
  "generated_under_ignored_path": true,
  "status": "initialized"
}
```

Semantics:

- `mode=provider_off_bootstrap` means provider calls and benchmark execution
  are invalid.
- `status` is one of `initialized`, `planned`, `branched`, `reviewed`,
  `reentered`, `reported`, `validated`, or `failed_validation`.

Failure modes:

- Missing manifest: fail closed.
- `provider_calls_allowed=true` in bootstrap: fail closed.
- Run path outside ignored sandbox run/tmp paths: fail closed.

## Event Mirror And Envelope

File: `events.jsonl`

Each line is one JSON event:

```json
{
  "schema_version": "codex-dr.event.v1",
  "event_id": "evt_0001_init_case",
  "run_id": "local_fixture_001",
  "timestamp": "2026-04-22T00:00:00Z",
  "actor": "bootstrap_harness",
  "event_type": "case.initialized",
  "causally_after": [],
  "inputs": [],
  "outputs": ["run_manifest.json"],
  "decision": null,
  "summary": "Initialized provider-off run bundle."
}
```

Required event types for provider-off bootstrap:

```text
case.initialized
plan.written
task_graph.written
agent_box.placeholder_written
branch.spawn_declared
branch.return_written
adequacy.assessed
review.written
reentry.compiled
synthesis.written
compaction.receipt_written
claim_ledger.written
allowed_claims.written
report.written
benchmark.placeholder_written
```

Decision events set:

```json
"decision": {
  "decision_id": "dec_0001_deepen",
  "decision_type": "spawn_branch|deepen|reenter|ship|no_reentry",
  "rationale": "Review finding requires one targeted follow-up task.",
  "status": "accepted"
}
```

Failure modes:

- Required event type absent: fail closed.
- Event references missing output path: fail closed.
- Decision event missing rationale: fail closed.
- Causal chain disconnected from `case.initialized`: fail closed.

## Artefact Manifest And CAS Contract

File: `artefact_manifest.json`

```json
{
  "schema_version": "codex-dr.artefact_manifest.v1",
  "run_id": "local_fixture_001",
  "hash_algorithm": "sha256",
  "artifacts": [
    {
      "artifact_id": "art_plan",
      "path": "plan.md",
      "role": "plan",
      "content_type": "text/markdown",
      "sha256": "<hex>",
      "bytes": 1234,
      "produced_by_event": "evt_0002_plan_written",
      "source_event_ids": ["evt_0001_init_case"],
      "claim_support_allowed": true
    }
  ]
}
```

Semantics:

- Every required artifact except `artefact_manifest.json` and
  `validation_report.json` must appear in the manifest before validation
  completes.
- `sha256` is the hash of current file bytes.
- `claim_support_allowed=false` for placeholders that cannot support material
  claims.

Failure modes:

- Required artifact absent from manifest: fail closed.
- Hash mismatch: fail closed.
- Claim ledger cites artifact with `claim_support_allowed=false`: fail closed
  unless the cited claim is explicitly a placeholder/non-claim.

## Terminal-Agent Box Config

File: `terminal_agent_boxes.json`

```json
{
  "schema_version": "codex-dr.terminal_agent_boxes.v1",
  "run_id": "local_fixture_001",
  "boxes": [
    {
      "box_id": "planner_box",
      "role": "planner",
      "mode": "provider_off_placeholder",
      "cwd": "branches/planner_box",
      "skills": [],
      "allowed_tools": [],
      "disallowed_tools": ["provider_calls", "network", "benchmark_execution"],
      "mcp_servers": [],
      "model": null,
      "session_lineage": null,
      "cleanup_policy": "preserve_for_bootstrap",
      "output_contract": ["plan.md", "adequacy_criteria.json", "task_graph.json"],
      "produced_by_event": "evt_0004_agent_box_placeholder"
    }
  ]
}
```

Semantics:

- Provider-off boxes are placeholders, not terminal-agent executions.
- Provider-backed boxes require run-control receipt linkage and transcript
  capture.

Failure modes:

- Provider-off box with model/provider configured: fail closed.
- Missing output contract for active box: fail closed.

## Plan File

File: `plan.md`

Required headings:

```text
# Plan
## Objective
## Assumptions
## Adequacy Criteria
## Source Policy
## Task Graph Summary
## Review Checklist
## Non-Claims
```

Failure modes:

- Missing adequacy criteria or review checklist: fail closed.
- Plan claims benchmark/provider execution in bootstrap: fail closed.

## Adequacy Criteria

File: `adequacy_criteria.json`

```json
{
  "schema_version": "codex-dr.adequacy_criteria.v1",
  "run_id": "local_fixture_001",
  "criteria": [
    {
      "criterion_id": "adequacy_evidence_triplet",
      "description": "Each branch must return pointer, analysis, and evidence files.",
      "required": true,
      "validator": "branch_triplet_present"
    }
  ],
  "produced_by_event": "evt_0002_plan_written"
}
```

Failure modes:

- No required criteria: fail closed.
- Criterion has no validator mapping: fail closed.

## Task Graph

File: `task_graph.json`

```json
{
  "schema_version": "codex-dr.task_graph.v1",
  "run_id": "local_fixture_001",
  "tasks": [
    {
      "task_id": "task_branch_a",
      "kind": "branch_research",
      "objective": "Produce deterministic bootstrap evidence triplet.",
      "depends_on": ["task_plan"],
      "status": "pending",
      "assigned_box_id": "branch_box_a",
      "expected_outputs": [
        "branches/branch_a/pointer.md",
        "branches/branch_a/analysis.md",
        "branches/branch_a/evidence.jsonl"
      ],
      "source_review_finding_id": null
    }
  ],
  "produced_by_event": "evt_0003_task_graph_written"
}
```

Task `kind` values:

- `planning`
- `branch_research`
- `adequacy_assessment`
- `review`
- `reentry_research`
- `synthesis`
- `report`
- `validation`

Failure modes:

- Dependency references missing task: fail closed.
- Required expected output missing: fail closed.
- Re-entry task missing source review finding: fail closed.

## Branch Return Contract

Files:

```text
branches/<branch_id>/branch_manifest.json
branches/<branch_id>/pointer.md
branches/<branch_id>/analysis.md
branches/<branch_id>/evidence.jsonl
```

`branch_manifest.json`:

```json
{
  "schema_version": "codex-dr.branch_manifest.v1",
  "run_id": "local_fixture_001",
  "branch_id": "branch_a",
  "task_id": "task_branch_a",
  "objective": "Produce deterministic bootstrap evidence triplet.",
  "mode": "provider_off_fixture",
  "outputs": {
    "pointer": "branches/branch_a/pointer.md",
    "analysis": "branches/branch_a/analysis.md",
    "evidence": "branches/branch_a/evidence.jsonl"
  },
  "produced_by_event": "evt_0006_branch_return_written"
}
```

`pointer.md` required headings:

```text
# Branch Pointer
## Objective
## Key Findings
## Evidence Map
## Read Next
```

`evidence.jsonl` line shape:

```json
{
  "schema_version": "codex-dr.evidence_item.v1",
  "evidence_id": "ev_branch_a_001",
  "run_id": "local_fixture_001",
  "branch_id": "branch_a",
  "source_type": "local_fixture",
  "source_ref": "provider-off deterministic fixture",
  "supports": ["claim_bootstrap_bundle_has_branch_return"],
  "quote_or_summary": "The branch return contains pointer, analysis, and evidence files.",
  "admission_status": "admitted",
  "produced_by_event": "evt_0006_branch_return_written"
}
```

Failure modes:

- Any triplet member missing: fail closed.
- Evidence item missing admission status: fail closed.
- Pointer lacks `Read Next`: fail closed.

## Adequacy Assessment

File: `adequacy_assessments.jsonl`

```json
{
  "schema_version": "codex-dr.adequacy_assessment.v1",
  "run_id": "local_fixture_001",
  "assessment_id": "adequacy_001",
  "criteria_checked": ["adequacy_evidence_triplet"],
  "branch_ids": ["branch_a"],
  "status": "needs_review",
  "gaps": [],
  "decision_event_id": "evt_0007_adequacy_assessed",
  "produced_by_event": "evt_0007_adequacy_assessed"
}
```

Status values:

- `satisfied`
- `needs_deepening`
- `needs_review`
- `blocked`

Failure modes:

- Assessment omits required criterion: fail closed.
- `needs_deepening` without task graph update: fail closed.

## Review File

File: `reviews/<review_id>.json`

```json
{
  "schema_version": "codex-dr.review.v1",
  "run_id": "local_fixture_001",
  "review_id": "review_001",
  "reviewer_role": "bootstrap_reviewer",
  "target_artifacts": ["synthesis.md", "claim_ledger.json"],
  "findings": [
    {
      "finding_id": "finding_reentry_001",
      "severity": "major",
      "finding_type": "thin_evidence|unsupported_claim|contradiction|missing_perspective",
      "summary": "Bootstrap requires one reviewer-driven re-entry task.",
      "evidence_refs": ["branches/branch_a/evidence.jsonl#ev_branch_a_001"],
      "requires_reentry": true,
      "recommended_task": "Add deterministic follow-up task for review pressure."
    }
  ],
  "produced_by_event": "evt_0008_review_written"
}
```

Failure modes:

- Review has no findings: fail closed.
- `requires_reentry=true` without recommended task: fail closed.
- Finding evidence ref missing: fail closed.

## Re-Entry Compiler

File: `reentry_decisions.jsonl`

```json
{
  "schema_version": "codex-dr.reentry_decision.v1",
  "run_id": "local_fixture_001",
  "decision_id": "reentry_001",
  "review_id": "review_001",
  "finding_id": "finding_reentry_001",
  "decision": "create_task",
  "rationale": "Major finding requires research-state change, not prose patching.",
  "created_task_id": "task_reentry_001",
  "task_graph_path": "task_graph.json",
  "produced_by_event": "evt_0009_reentry_compiled"
}
```

Decision values:

- `create_task`
- `no_reentry`
- `blocked`

Failure modes:

- Required re-entry finding has no decision: fail closed.
- `create_task` decision missing task in `task_graph.json`: fail closed.
- `no_reentry` decision without rationale: fail closed.

## Synthesis And Contradictions

Files:

```text
synthesis.md
contradictions.json
report_outline.md
```

`synthesis.md` required headings:

```text
# Synthesis
## Admitted Evidence
## Contradictions
## Unresolveds
## Claims Ready For Ledger
## Review Impact
```

`contradictions.json`:

```json
{
  "schema_version": "codex-dr.contradictions.v1",
  "run_id": "local_fixture_001",
  "contradictions": [
    {
      "contradiction_id": "contradiction_none_001",
      "issue": "No real contradiction in provider-off fixture.",
      "positions": [],
      "adjudication_status": "not_applicable",
      "unresolved": false,
      "report_treatment": "State that provider-off fixture carries no real-world contradiction claim."
    }
  ],
  "produced_by_event": "evt_0010_synthesis_written"
}
```

Failure modes:

- Synthesis lacks review impact: fail closed.
- Real contradiction lacks report treatment: fail closed.

## Compaction Receipt

File: `compactions/<compaction_id>.json`

```json
{
  "schema_version": "codex-dr.compaction_receipt.v1",
  "run_id": "local_fixture_001",
  "compaction_id": "compaction_001",
  "mode": "provider_off_fixture",
  "input_artifacts": ["plan.md", "branches/branch_a/pointer.md", "synthesis.md"],
  "output_artifact": "compactions/compaction_001.json",
  "scope": "bootstrap state summary",
  "claim_impact": "no claim widening",
  "produced_by_event": "evt_0011_compaction_receipt_written"
}
```

Failure modes:

- Compaction receipt missing for reported run: fail closed.
- Claim impact absent: fail closed.

## Claim Ledger

File: `claim_ledger.json`

```json
{
  "schema_version": "codex-dr.claim_ledger.v1",
  "run_id": "local_fixture_001",
  "claims": [
    {
      "claim_id": "claim_bootstrap_bundle_has_branch_return",
      "text": "The provider-off fixture includes a branch return triplet.",
      "materiality": "bootstrap",
      "status": "admitted",
      "source_artifact_refs": ["branches/branch_a/evidence.jsonl#ev_branch_a_001"],
      "intermediate_artifact_refs": ["branches/branch_a/pointer.md", "synthesis.md"],
      "blocked_from_public_claims": false
    }
  ],
  "produced_by_event": "evt_0012_claim_ledger_written"
}
```

Claim status values:

- `admitted`
- `blocked`
- `evidence_pending`
- `non_claim`

Failure modes:

- Report material claim absent from ledger: fail closed.
- Admitted claim lacks source and intermediate refs: fail closed.
- Claim text asserts benchmark/provider/Grep parity in bootstrap: fail closed.

## Benchmark Score

File: `benchmark_score.json`

Provider-off placeholder shape:

```json
{
  "schema_version": "codex-dr.benchmark_score.v1",
  "run_id": "local_fixture_001",
  "mode": "provider_off_placeholder",
  "benchmark_family": null,
  "case_manifest": null,
  "scorer_manifest": null,
  "score": null,
  "claims_enabled": false,
  "reason": "Benchmark execution is blocked until provider-off bootstrap, case manifest, scorer manifest, and run-control gates pass.",
  "produced_by_event": "evt_0013_benchmark_placeholder_written"
}
```

Failure modes:

- Numeric score in provider-off placeholder: fail closed.
- `claims_enabled=true` without completed benchmark run: fail closed.

## Allowed Claims

File: `allowed_claims.json`

```json
{
  "schema_version": "codex-dr.allowed_claims.v1",
  "run_id": "local_fixture_001",
  "allowed_claims": [
    {
      "claim": "The provider-off bootstrap harness emitted and validated a deterministic local fixture run bundle.",
      "scope": "local_fixture_only",
      "supporting_artifacts": ["validation_report.json", "claim_ledger.json"]
    }
  ],
  "blocked_claims": [
    "Grep parity",
    "benchmark score",
    "provider-backed execution",
    "product service readiness"
  ],
  "produced_by_event": "evt_0014_allowed_claims_written"
}
```

Failure modes:

- Allowed claim not supported by ledger or validation report: fail closed.
- Missing blocked claims list: fail closed.
- Claim widens beyond run mode: fail closed.

## Report

File: `report.md`

Required headings:

```text
# Provider-Off Bootstrap Report
## Scope
## What Ran
## Evidence
## Review Re-Entry
## Claim Boundary
## Non-Claims
```

Failure modes:

- Report claims benchmark/provider execution in bootstrap: fail closed.
- Report omits non-claims: fail closed.

## Validation Report

File: `validation_report.json`

```json
{
  "schema_version": "codex-dr.validation_report.v1",
  "run_id": "local_fixture_001",
  "status": "passed",
  "validated_at": "2026-04-22T00:00:00Z",
  "checks": [
    {
      "check_id": "events_required_types_present",
      "status": "passed",
      "details": "All required provider-off event types are present."
    }
  ],
  "failed_checks": [],
  "produced_by_event": null
}
```

Status values:

- `passed`
- `failed`

Validator must check at least:

- run path is under ignored sandbox `runs/` or `tmp/`
- required files exist
- required event types exist
- causal event chain is connected
- artefact manifest hashes match current files
- branch triplets exist
- adequacy criteria map to checks
- required review re-entry decision exists
- compaction receipt exists
- benchmark score is placeholder in provider-off mode
- report claims are in claim ledger
- allowed claims do not include blocked claims
- generated provider-off bundle has no provider metadata, run-control receipt,
  transcripts, or benchmark numeric score unless explicitly marked as blocked

The validation report is an external report over the run bundle. It is the
only file the `validate` command writes and does not require an event-log entry;
otherwise validation would mutate the causal log whose hashes it is checking.

## Failure Mode Matrix

| Failure | Detection hook | Required result |
| --- | --- | --- |
| Missing required file | `required_files_present` | Validation fails. |
| Missing required event type | `events_required_types_present` | Validation fails. |
| Disconnected event chain | `events_causal_chain_connected` | Validation fails. |
| Missing artefact hash or mismatch | `artefact_manifest_hashes_match` | Validation fails. |
| Missing branch pointer/analysis/evidence | `branch_triplets_present` | Validation fails. |
| Review finding requires re-entry but none exists | `review_reentry_compiled` | Validation fails. |
| Compaction receipt missing | `compaction_receipt_present` | Validation fails. |
| Benchmark placeholder has numeric score | `benchmark_placeholder_not_score` | Validation fails. |
| Claim wider than allowed scope | `allowed_claims_scope_enforced` | Validation fails. |
| Provider-backed artifact appears in provider-off run | `provider_off_no_provider_artifacts` | Validation fails. |
| Generated bundle path is not ignored | `generated_path_is_ignored` | Validation fails. |

## Contract Report

Upstream interfaces satisfied:

- Parity contract behaviors are mapped to concrete artifacts and validators.
- Bootstrap doctrine command sequence is represented by scriptable commands.
- Live run-control receipt remains the gate for provider-backed commands.
- Benchmark acquisition audit remains target calibration only.

Downstream obligations created:

- `alexandriacleanroom-91.1.4.1` must implement provider-off generation and
  validation against these file formats.
- Future provider-backed beads must add run-control, case, scorer, provider
  metadata, and transcript validation without weakening provider-off rules.

Round-trip contracts closed:

- CLI command writes artifacts, events, and manifest entries.
- Branch returns are consumed by adequacy and synthesis artifacts.
- Review findings are consumed by re-entry decisions and task graph updates.
- Report claims are consumed by claim ledger and allowed-claims validation.
- Validation reads the full bundle and emits one validation report.

Policy defaults:

- All missing required artifacts fail closed.
- Provider-backed commands are blocked before run-control receipt and bootstrap
  validation.
- Benchmark scores are placeholders until explicit benchmark execution gates
  pass.

Remaining contradictions:

- Exact future provider-backed terminal-agent runner remains undecided.
  Governing rule: runner choice may vary, but transcript-to-event,
  transcript-to-CAS, run-control, and claim-boundary semantics may not vary.
