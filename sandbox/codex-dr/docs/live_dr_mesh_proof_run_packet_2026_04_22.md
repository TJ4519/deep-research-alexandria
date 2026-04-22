# Live DR Mesh Proof-Run Packet

Status: no-launch preflight packet
Date: 2026-04-22
Bead: `alexandriacleanroom-91.1.5.10`
Future run id: `draco_live_mesh_001`

## Completion Object

This packet prepares the first future live DR mesh proof run without launching
Codex CLI, calling providers, or scoring a benchmark.

The prepared object is a Grep-style Codex-DR mesh smoke against a DRACO tiny
case pointer: planner, task graph, scoped branch roles, pointer / analysis /
evidence returns, pointer-first orchestration, evaluate/synthesize,
reviewer-driven re-entry, one-writer report, scorer bridge, event custody,
artifact custody, and claim custody.

## No-Launch Boundary

This bead does not authorize live execution.

Do not run `codex exec` directly from this packet. A future launch must be
reopened by the Principal for the named run and must proceed through the
Codex-DR live adapter path, not an ad hoc shell command.

The current executable no-launch path is dry-run planning only:

```bash
uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir sandbox/codex-dr/runs \
  mesh-live-plan draco_live_mesh_001 \
  --run-control sandbox/codex-dr/harness-specs/draco_live_mesh_001_run_control_receipt_draft.json
```

That command requires an existing provider-off mesh bundle for
`draco_live_mesh_001`; if the bundle does not exist, seed only the local
provider-off skeleton first:

```bash
uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir sandbox/codex-dr/runs \
  mesh-bootstrap-run draco_live_mesh_001
```

The dry-run planner writes prompt and launch-plan artifacts only. It must not
create transcripts, provider metadata, benchmark scores, or live outputs.

## Case Manifest Pointer

Case manifest:
`sandbox/codex-dr/benchmark-manifests/draco_tiny_smoke_case_manifest.md`

Selected benchmark-facing case:

- benchmark family: DRACO;
- dataset id: `perplexity-ai/draco`;
- dataset commit: `ce076749809027649ebd331bcb70f42bf720d387`;
- split/file: `test.jsonl`;
- selected row pointer: row `0`, recorded as `draco_test_row_000`;
- raw data policy: raw/full benchmark data must remain out of git and may be
  fetched only into ignored `sandbox/codex-dr/tmp/` or `sandbox/codex-dr/runs/`
  paths when a run-control receipt allows it.

## Benchmark And Scorer Status

DRACO acquisition is sufficient for a tiny smoke pointer. It is not sufficient
for a numeric score claim by itself.

Scorer status for this packet:

- benchmark execution: not authorized by this bead;
- benchmark scoring: blocked;
- judge/scorer path: evidence-pending until a scorer manifest or accepted
  DRACO evaluation route is written and approved;
- placeholder score policy: allowed only as `scored: false` with `score: null`;
- DRACO leaderboard or comparator claim: blocked.

Prior scored status:
`sandbox/codex-dr/docs/draco_smoke_001_scoring_bridge_2026_04_22.md` records
the earlier smoke score question as blocked, not scored.

## Role Launch Plan References

The future live run must reuse the same topology proven by:

- provider-off proof receipt:
  `sandbox/codex-dr/docs/provider_off_dr_mesh_proof_gate_2026_04_22.md`;
- DR mesh parity charter:
  `sandbox/codex-dr/harness-specs/dr_mesh_parity_charter.md`;
- live adapter dry-run contract:
  `sandbox/codex-dr/harness-specs/live_codex_cli_mesh_adapter_contract.md`;
- run-control receipt template:
  `sandbox/codex-dr/harness-specs/live_run_control_receipt_template.md`.

The launch plan must be rendered from the mesh task graph and role configs:

- `planner`;
- `deep_search`;
- `data_analysis`;
- `verification`;
- `synthesis`;
- `review`;
- `reentry`;
- `writer`;
- `scorer_bridge`.

Each live branch must return files through the pointer-first contract:

- `pointer.md`;
- `analysis.md`;
- `evidence.md` or `evidence.jsonl`.

The orchestrator must read pointer files first, then selectively read cited
analysis spans and evidence files.

## Run-Control Receipt Draft

Draft file:
`sandbox/codex-dr/harness-specs/draco_live_mesh_001_run_control_receipt_draft.json`

This draft is intentionally execution-closed:

- `approval.approved_for_dry_run_planning: true`;
- `approval.approved_for_execution: false`;
- no `codex exec` process may be launched from it;
- it is valid only for rendering dry-run launch plans and prompts.

A future live execution receipt must be created or explicitly amended with a
Principal approval note for `draco_live_mesh_001` before any live launch.

## Supervision And Kill Policy

Future live execution prerequisites:

- foreground supervision required;
- automatic retry disabled;
- maximum cases: `1`;
- maximum live attempts: `1`;
- maximum re-entry rounds: `1`;
- wall-clock bound: `30` minutes unless the Principal approves a different
  bound in the live receipt;
- kill path: manual foreground process termination by the coordinator watching
  the launched Codex CLI process;
- hard stop on secret exposure, root env access, unauthorized raw/private
  benchmark data, missing transcript path, missing run-bundle path, unexpected
  cwd/output root, or retry request.

## Transcript Policy

Future live execution must capture transcripts under:

```text
sandbox/codex-dr/runs/draco_live_mesh_001/transcripts/
```

Transcript capture must be available before launch and must not include
secrets, customer data, raw private benchmark corpora, or root env file
contents. The transcript path must be represented in the run bundle's event and
artifact custody surfaces.

Dry-run launch-plan rendering must not create transcripts.

## Generated Output Paths

All generated live or dry-run outputs must stay under ignored sandbox paths:

```text
sandbox/codex-dr/runs/draco_live_mesh_001/
sandbox/codex-dr/tmp/draco_tiny_smoke_001/
```

Expected run-bundle artifacts for a future authorized run:

- `run_manifest.json`;
- `case_input.json`;
- `plan.md`;
- `task_graph.json`;
- `branches/<task_id>/pointer.md`;
- `branches/<task_id>/analysis.md`;
- `branches/<task_id>/evidence.md` or `evidence.jsonl`;
- `synthesis.md`;
- `reviews/`;
- `reentry_decisions.jsonl`;
- `report.md`;
- `benchmark_score.json`;
- `claim_ledger.json`;
- `allowed_claims.json`;
- `events.jsonl`;
- `artefact_manifest.json`;
- `validation_report.json`.

## Validation Commands

Required after dry-run planning or future authorized live execution:

```bash
uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir sandbox/codex-dr/runs \
  validate draco_live_mesh_001

uv run pytest sandbox/codex-dr/tests -q
git diff --check
make check
```

If a future live execution is authorized, validation must also inspect the
transcript capture and verify that every role output has event and artifact
custody.

## Packet Dry-Run Verification

This packet's no-launch path was verified locally under an ignored tmp path:

```bash
rm -rf sandbox/codex-dr/tmp/proof-run-packet-dry-run
uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir sandbox/codex-dr/tmp/proof-run-packet-dry-run \
  mesh-bootstrap-run draco_live_mesh_001
uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir sandbox/codex-dr/tmp/proof-run-packet-dry-run \
  mesh-live-plan draco_live_mesh_001 \
  --run-control sandbox/codex-dr/harness-specs/draco_live_mesh_001_run_control_receipt_draft.json
uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir sandbox/codex-dr/tmp/proof-run-packet-dry-run \
  validate draco_live_mesh_001
```

Result:

```json
{
  "status": "passed",
  "failed_checks": []
}
```

This was a provider-off skeleton plus dry-run launch-plan render only. It did
not launch Codex CLI, create provider metadata, create transcripts, execute a
benchmark, or score DRACO.

## Allowed Claims

Allowed after this packet only:

- A no-launch preflight packet exists for future run `draco_live_mesh_001`.
- The packet routes future execution through the Codex-DR live adapter path
  instead of ad hoc `codex exec`.
- The packet records case, scorer, supervision, transcript, generated-output,
  validation, and claim-boundary requirements.

Allowed after a successful dry-run launch-plan render:

- The live adapter rendered deterministic role launch plans and prompts from an
  existing provider-off mesh bundle and an execution-closed run-control draft.

Allowed only after a separately approved live run succeeds with custody:

- Codex CLI roles executed for one named DRACO smoke pointer under transcript,
  event, artifact, and claim custody.
- The emitted bundle contains planner, branch, synthesis, review/re-entry,
  writer, and scorer-bridge artifacts for that one run.

## Blocked Claims

These remain blocked by this packet:

- live run happened;
- `codex exec` launch was authorized;
- benchmark execution happened;
- DRACO numeric score;
- Grep parity;
- leaderboard rank;
- product or service-runtime readiness;
- provider-backed quality claim;
- reproducibility against private Grep/Parcha setup;
- reuse rights for private, paid, raw, or unlicensed benchmark data.

## Immediate Next Command

The next safe command after this packet is validation, not launch:

```bash
uv run pytest sandbox/codex-dr/tests -q
git diff --check
make check
```

The next no-launch mesh command for a future agent, once the coordinator wants
the launch plan rendered, is:

```bash
uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir sandbox/codex-dr/runs \
  mesh-bootstrap-run draco_live_mesh_001

uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir sandbox/codex-dr/runs \
  mesh-live-plan draco_live_mesh_001 \
  --run-control sandbox/codex-dr/harness-specs/draco_live_mesh_001_run_control_receipt_draft.json
```

That sequence is provider-off plus dry-run planning only. It is not a live
Codex CLI run and does not authorize benchmark scoring.
