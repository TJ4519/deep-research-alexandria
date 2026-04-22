# DRACO Smoke 001 Run Receipt

Status: completed boxed smoke run
Date: 2026-04-22
Run id: `draco_smoke_001`
Beads: `alexandriacleanroom-91.1.5`, `alexandriacleanroom-91.1.5.4`

## Completion Claim

`draco_smoke_001` executed one boxed Codex recursive deep-research smoke run
against the DRACO row-0 pointer under `sandbox/codex-dr/runs/draco_smoke_001/`.

The run emitted the required smoke bundle:

- planner artifacts;
- adequacy criteria;
- task graph;
- terminal-agent box configuration;
- three branch returns;
- synthesis and contradictions;
- reviewer backpressure;
- one re-entry branch;
- report outline and report;
- claim ledger;
- benchmark-score placeholder;
- allowed claims;
- event log;
- artefact manifest;
- transcript capture.

## Local Bundle

The bundle is intentionally ignored by git.

Local entry points:

- `sandbox/codex-dr/runs/draco_smoke_001/execution_summary.md`
- `sandbox/codex-dr/runs/draco_smoke_001/report.md`
- `sandbox/codex-dr/runs/draco_smoke_001/claim_ledger.json`
- `sandbox/codex-dr/runs/draco_smoke_001/allowed_claims.json`
- `sandbox/codex-dr/runs/draco_smoke_001/benchmark_score.json`
- `sandbox/codex-dr/runs/draco_smoke_001/transcripts/codex_exec_smoke.txt`

## Coordinator Validation

After the boxed process exited, the main coordinator re-hashed the transcript
and ran a bundle validation pass.

Validation result:

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

## What The Smoke Proved

The run proved that the current sandbox can launch a real `codex exec` boxed
research run, capture a transcript, perform smoke-depth public web research,
write a recursive research bundle, trigger review-driven re-entry, and narrow
claims from the emitted evidence.

## What Remains Blocked

The run does not prove:

- Grep parity;
- DRACO score;
- leaderboard rank;
- product-runtime readiness;
- systematic AER/QJE/JPE labor-health adoption rates;
- methodological dominance of any estimator in that requested corpus.

## Live-Run Control Finding

The run used more tokens than the historical prompt-level budget target.

Observed terminal output reported:

```text
tokens used
270,716
```

The token manifest target was `max_total_tokens: 42000`. That target is now
classified as runtime-control leakage from earlier Alexandria work, not as a
Codex-DR sandbox architecture requirement.

This smoke proves a narrower operational point: live Codex CLI runs need launch
discipline that prevents hidden background work, uncontrolled retries, unclear
output boundaries, and unobserved transcripts.

Future provider-backed benchmark runs require:

- Principal authorization for a named run or run class;
- run-control receipt;
- foreground supervision or external monitoring;
- wall-clock bound and kill path;
- transcript capture and output boundary;
- no automatic retries unless separately approved;
- data and claim boundaries.

## Completion Boundary

The boxed smoke run is complete.

Benchmark scoring remains blocked by the scoring bridge recorded in
`sandbox/codex-dr/docs/draco_smoke_001_scoring_bridge_2026_04_22.md`.
