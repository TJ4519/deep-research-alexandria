# Codex-DR Token Manifest Template

Status: superseded lineage template
Applies to: future provider-backed, model-backed, benchmark, SDK, or
terminal-agent runs under `sandbox/codex-dr/`

## Supersession Note

This template is retained as lineage from the pre-correction interpretation.

For the Codex-DR sandbox, new live Codex CLI or terminal-agent runs use:

```text
sandbox/codex-dr/harness-specs/live_run_control_receipt_template.md
```

The corrected rule is recorded in:

```text
sandbox/codex-dr/docs/codex_mesh_launch_control_2026_04_22.md
```

The `42,000` token target used for `draco_smoke_001` is not an architectural
invariant. Fixed token ceilings are optional operational estimates, not the
center of the Codex-mesh build.

## Historical Rule

Under the superseded interpretation, any provider-backed run without a
completed token manifest was invalid.

This template does not authorize execution. New live runs should use a
run-control receipt instead.

## Manifest

```yaml
manifest_id: "token_manifest_<run_id>"
created_at: "YYYY-MM-DDTHH:MM:SSZ"
bead_id: ""
run_id: ""
run_purpose: ""

runner:
  kind: "" # e.g. terminal-agent, provider-api, benchmark-scorer
  provider: ""
  model_or_agent: ""
  provider_sdk_or_cli_version: "evidence-pending"
  cwd: "sandbox/codex-dr/"

authority:
  governing_docs:
    - "sandbox/codex-dr/AGENTS.md"
    - "sandbox/codex-dr/docs/BOOTSTRAP_DOCTRINE.md"
  benchmark_audit: "sandbox/codex-dr/benchmark-manifests/benchmark_acquisition_audit.md"
  parity_contract: "required-before-benchmark-execution"

inputs:
  allowed_sources: []
  forbidden_sources:
    - "secrets"
    - "customer data"
    - "raw private benchmark corpora"
    - "paid benchmark corpora unless separately authorized"
  benchmark_case_manifest: "required-for-benchmark-runs"
  data_policy: ""

budget:
  max_input_tokens: null
  max_output_tokens: null
  max_total_tokens: null
  max_wall_clock_minutes: null
  max_provider_cost_usd: null
  max_attempts: null

stop_conditions:
  hard_stop:
    - "budget exhausted"
    - "missing required custody artifact"
    - "unexpected secret or private data exposure"
    - "benchmark/license/access condition not satisfied"
  soft_stop:
    - "judge variance exceeds manifest tolerance"
    - "case manifest mismatch"
    - "scorer schema mismatch"

expected_artifacts:
  run_bundle: "sandbox/codex-dr/runs/<run_id>/"
  event_log: "events.jsonl"
  artefact_manifest: "artefact_manifest.json"
  transcript_capture: "transcripts/"
  claim_ledger: "claim_ledger.json"
  allowed_claims: "allowed_claims.json"
  benchmark_score: "benchmark_score.json"
  compaction_receipts: "compactions/"

scoring:
  benchmark_family: ""
  dataset_source_url: ""
  dataset_version_or_sha: ""
  scorer_code_version: ""
  judge_model: ""
  judge_prompt_version: ""
  parameters: {}
  retry_policy: ""
  variance_policy: ""

compaction:
  policy: ""
  receipt_required: true
  input_manifest_required: true
  output_manifest_required: true

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

- `bead_id`, `run_id`, `run_purpose`, `runner`, `budget`,
  `stop_conditions`, `expected_artifacts`, `allowed_claims_if_success`, and
  `non_claims_even_if_success` are required.
- Benchmark runs require `benchmark_case_manifest`, `scoring`, and a citation
  to `benchmark_acquisition_audit.md`.
- Provider-backed runs require positive finite budgets and transcript capture.
- Runs that can produce claims require a claim ledger and allowed-claims file.
- Any manifest with `approved_for_execution: false` must fail closed.
- Any manifest that permits raw private, paid, or large benchmark data in git
  must fail closed.
