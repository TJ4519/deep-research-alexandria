# DRACO Live Mesh 002 Run Receipt

Status: completed bounded live smoke with validation pass
Date: 2026-04-23
Bead: `alexandriacleanroom-91.1.5.16`
Run id: `draco_live_mesh_002`

## Authority

The Principal explicitly authorized live Codex DR mesh execution in the local
coordinator thread on 2026-04-23. This second named run was a corrective smoke
after `draco_live_mesh_001` exposed a writer-before-reentry launch-order defect.

The run used this approved receipt:

`sandbox/codex-dr/harness-specs/draco_live_mesh_002_run_control_receipt_approved_2026_04_23.json`

## Command Sequence

```bash
uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir sandbox/codex-dr/runs \
  mesh-bootstrap-run draco_live_mesh_002

uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir sandbox/codex-dr/runs \
  mesh-live-plan draco_live_mesh_002 \
  --run-control sandbox/codex-dr/harness-specs/draco_live_mesh_002_run_control_receipt_approved_2026_04_23.json

uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir sandbox/codex-dr/runs \
  mesh-execute-live draco_live_mesh_002 \
  --run-control sandbox/codex-dr/harness-specs/draco_live_mesh_002_run_control_receipt_approved_2026_04_23.json

uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir sandbox/codex-dr/runs \
  validate draco_live_mesh_002
```

The launch plan executed in dependency order:

1. `task_plan`
2. `task_deep_search`
3. `task_data_analysis`
4. `task_verification`
5. `task_pointer_first_synthesis`
6. `task_review`
7. `task_reentry_followup`
8. `task_final_writer`

## Emitted Custody

The ignored run bundle is:

`sandbox/codex-dr/runs/draco_live_mesh_002/`

The live execution summary is:

`sandbox/codex-dr/runs/draco_live_mesh_002/live_executor/execution_summary.json`

The run completed with:

- `execution_status: succeeded`;
- `role_count: 8`;
- one transcript per role under `transcripts/`;
- one last-message capture per role under `last_messages/`;
- copied live role outputs under `live_executor/role_outputs/`;
- event custody through `events.jsonl`;
- artifact custody through `artefact_manifest.json`;
- validation status `passed`.

## Validation

Validation passed with no failed checks:

```bash
uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir sandbox/codex-dr/runs \
  validate draco_live_mesh_002
```

The validation includes live execution custody, dependency order, per-role
transcript capture, per-role output capture, event custody, artifact custody,
claim-boundary enforcement, and generated-path isolation.

## Claim Boundary

Allowed from this run:

- A bounded live Codex CLI DR mesh smoke executed eight per-role Codex CLI boxes
  once with transcript and artifact custody for `draco_live_mesh_002`.
- The corrected live launch plan executed reviewer-driven re-entry before the
  final writer.

Still blocked:

- Grep parity;
- DRACO numeric score;
- leaderboard rank;
- product or service-runtime readiness;
- full benchmark execution;
- scorer custody;
- self-improvement promotion;
- reproducibility against private Grep/Parcha setup.
