# Codex-DR Live Run Control Receipt Template

Status: active launch-control template
Applies to: live Codex CLI, terminal-agent, benchmark-generation, scorer, or
SDK-backed runs under `sandbox/codex-dr/`

## Rule

Live runs require an approved run-control receipt before launch.

This is an operational control for the Codex-mesh sandbox. It is not a product
runtime token manifest, and it must not become a blocker to building the
orchestrator, role adapters, benchmark lane, or adequacy backpressure.

The receipt records how a run is launched, observed, bounded, stopped, and
interpreted. Token or cost estimates may be recorded when useful, but no fixed
token ceiling is an architectural invariant for the Codex CLI mesh.

## Receipt

```yaml
receipt_id: "run_control_<run_id>"
created_at: "YYYY-MM-DDTHH:MM:SSZ"
bead_id: ""
run_id: ""
run_purpose: ""

runner:
  kind: "" # codex_exec_box | local_fake_adapter | scorer | provider_api | sdk_adapter
  command_surface: ""
  cli_or_sdk_version: "evidence-pending"
  cwd: "sandbox/codex-dr/"
  sandbox_mode: ""
  approval_policy: ""
  transcript_wrapper: ""
  transcript_root: "sandbox/codex-dr/runs/<run_id>/transcripts/"
  output_last_message: ""

authority:
  governing_docs:
    - "sandbox/codex-dr/AGENTS.md"
    - "sandbox/codex-dr/docs/BOOTSTRAP_DOCTRINE.md"
    - "sandbox/codex-dr/docs/codex_mesh_launch_control_2026_04_22.md"
  benchmark_audit: "sandbox/codex-dr/benchmark-manifests/benchmark_acquisition_audit.md"
  case_manifest: "required-for-benchmark-facing-runs"
  scorer_manifest: "required-for-scoring-runs"

inputs:
  allowed_sources: []
  forbidden_sources:
    - "secrets"
    - "customer data"
    - "raw private benchmark corpora"
    - "paid benchmark corpora unless separately authorized"
    - "root env files"
  data_policy: ""

operational_bounds:
  max_cases: 1
  max_live_attempts: 1
  max_reentry_rounds: 1
  max_wall_clock_minutes: null
  foreground_supervision_required: true
  automatic_retry_allowed: false
  external_monitoring: ""
  kill_path: ""
  notes: ""

stop_conditions:
  hard_stop:
    - "run leaves approved cwd or output roots"
    - "unexpected secret or private data exposure"
    - "benchmark/license/access condition not satisfied"
    - "automatic retry requested without explicit approval"
    - "required transcript or run-bundle path unavailable"
  soft_stop:
    - "branch evidence is too thin for score claims"
    - "reviewer requests more re-entry rounds than this receipt allows"
    - "scorer bridge is unavailable"

expected_artifacts:
  run_bundle: "sandbox/codex-dr/runs/<run_id>/"
  transcript_capture: "sandbox/codex-dr/runs/<run_id>/transcripts/"
  event_log: "events.jsonl"
  artefact_manifest: "artefact_manifest.json"
  case_payload_cache: "sandbox/codex-dr/tmp/<case_id>/"
  plan: "plan.md"
  task_graph: "task_graph.json"
  branch_returns: "branches/"
  synthesis: "synthesis.md"
  review: "reviews/"
  reentry: "reentry_decisions.jsonl"
  report: "report.md"
  claim_ledger: "claim_ledger.json"
  allowed_claims: "allowed_claims.json"
  benchmark_score: "benchmark_score.json"

scoring:
  benchmark_family: ""
  scorer_status: "blocked | approved"
  judge_or_scorer: "evidence-pending"
  prompt_or_code_version: "evidence-pending"
  retry_policy: ""
  variance_policy: ""

allowed_claims_if_success:
  - ""

non_claims_even_if_success:
  - "Grep parity unless separately proven by the parity contract"
  - "product-runtime readiness"
  - "leaderboard rank unless accepted by the benchmark owner or reproduced under a declared public comparator"
  - "reuse rights for private or unlicensed artifacts"

approval:
  prepared_by: ""
  reviewed_by: ""
  approved_for_execution: false
  approval_note: ""
```

## Minimal Validation Rules

- `bead_id`, `run_id`, `run_purpose`, `runner`, `operational_bounds`,
  `stop_conditions`, `expected_artifacts`, `allowed_claims_if_success`, and
  `non_claims_even_if_success` are required.
- Live Codex CLI runs require transcript capture, foreground supervision,
  a wall-clock bound, and a kill path.
- Benchmark-facing runs require a case manifest and the benchmark acquisition
  audit.
- Scoring runs require a scorer manifest and scoring transcript or scorer log.
- Runs that can produce claims require a claim ledger and allowed-claims file.
- Any receipt with `approved_for_execution: false` must fail closed.
- Any receipt that permits raw private, paid, or large benchmark data in git
  must fail closed.
