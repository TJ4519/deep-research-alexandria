# DRACO Smoke 001 Scoring Bridge

Status: blocker bridge recorded
Date: 2026-04-22
Run id: `draco_smoke_001`
Bead: `alexandriacleanroom-91.1.5.5`

## Decision

The boxed smoke run produced `benchmark_score.json` as a placeholder with
`score: null`.

No DRACO numeric score may be claimed for `draco_smoke_001`.

## Reason

The authorized run scope did not contain an approved scorer bridge.

Missing scoring requirements:

- scorer manifest;
- judge model or local scorer policy;
- judge prompt version;
- rubric mapping from DRACO criteria to scoring output;
- input/output schema;
- retry and variance policy;
- reference-answer handling rule;
- scoring transcript capture;
- event and artefact custody for scorer execution;
- allowed-claims update after scoring.

The token manifest also stated:

```yaml
scorer_execution_allowed: false_until_scoring_bridge
```

## Required Scorer Manifest Fields

A future DRACO scoring run must provide at least:

```yaml
schema_version: codex-dr.scorer_manifest.v1
run_id: draco_smoke_001
benchmark_family: DRACO
case_manifest: sandbox/codex-dr/benchmark-manifests/draco_tiny_smoke_case_manifest.md
input_report: sandbox/codex-dr/runs/draco_smoke_001/report.md
reference_answer_policy: sealed_until_scoring
judge_or_scorer:
  kind: local_script | model_judge
  implementation_ref: evidence-pending
  version: evidence-pending
  prompt_ref: evidence-pending
  parameters: {}
retry_policy:
  max_attempts: 1
variance_policy: record_unavailable_for_single_smoke
outputs:
  score_file: sandbox/codex-dr/runs/draco_smoke_001/benchmark_score.json
  scorer_transcript: sandbox/codex-dr/runs/draco_smoke_001/transcripts/
claim_policy:
  allow_numeric_score: true_only_after_validated_scoring
  block_grep_parity: true
  block_leaderboard_rank: true
```

## Accepted Completion For This Bead

`alexandriacleanroom-91.1.5.5` is complete as a blocker bridge, because it
identifies the exact missing scorer path and prevents a placeholder report from
becoming a fake benchmark result.

This is not a DRACO score and not a parity claim.
