# DRACO Live Mesh 001 Run Receipt

Status: completed bounded live smoke with validation blocker
Date: 2026-04-23
Bead: `alexandriacleanroom-91.1.5.16`
Run id: `draco_live_mesh_001`

## Authority

The Principal explicitly authorized the live Codex DR mesh smoke for
`alexandriacleanroom-91.1.5.16` in the local coordinator thread on
2026-04-23.

The run used this approved receipt:

`sandbox/codex-dr/harness-specs/draco_live_mesh_001_run_control_receipt_approved_2026_04_23.json`

## Command Sequence

The authorized live run path is:

```bash
uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir sandbox/codex-dr/runs \
  mesh-bootstrap-run draco_live_mesh_001

uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir sandbox/codex-dr/runs \
  mesh-live-plan draco_live_mesh_001 \
  --run-control sandbox/codex-dr/harness-specs/draco_live_mesh_001_run_control_receipt_approved_2026_04_23.json

uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir sandbox/codex-dr/runs \
  mesh-execute-live draco_live_mesh_001 \
  --run-control sandbox/codex-dr/harness-specs/draco_live_mesh_001_run_control_receipt_approved_2026_04_23.json

uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir sandbox/codex-dr/runs \
  validate draco_live_mesh_001
```

During this session, the `mesh-execute-live` process was monitored to
completion under the approved receipt. This specific run id was not retried.
A separate corrected run id, `draco_live_mesh_002`, was later executed after
the dependency-order defect was patched and gated.

## Emitted Custody

The ignored run bundle is:

`sandbox/codex-dr/runs/draco_live_mesh_001/`

The live execution summary is:

`sandbox/codex-dr/runs/draco_live_mesh_001/live_executor/execution_summary.json`

The run completed with:

- `execution_status: succeeded`;
- `role_count: 8`;
- one transcript per role under `transcripts/`;
- one last-message capture per role under `last_messages/`;
- copied live role outputs under `live_executor/role_outputs/`;
- event custody through `events.jsonl`;
- artifact custody through `artefact_manifest.json`;
- validation status `failed` under the current validator because the live role
  execution order placed the writer before its re-entry dependency.

Executed roles:

- `task_plan`;
- `task_deep_search`;
- `task_data_analysis`;
- `task_verification`;
- `task_pointer_first_synthesis`;
- `task_review`;
- `task_final_writer`;
- `task_reentry_followup`.

## Validation

Run-bundle validation was run:

```bash
uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir sandbox/codex-dr/runs \
  validate draco_live_mesh_001
```

`validation_report.json` currently records one failed check:

- `live_execution_custody_present`: `task_final_writer: dependency
  task_reentry_followup executed later`.

The remaining checks passed, including:

- required files present;
- required live event types present;
- event causal chain connected;
- artifact manifest hashes match;
- branch triplets present;
- review re-entry compiled;
- DRACO scorer manifest valid with scoring blocked;
- benchmark placeholder is not a score;
- benchmark evaluation claim gate enforced;
- generated path is ignored.

## Claim Boundary

Allowed from this run:

- A bounded live Codex CLI DR mesh smoke executed eight per-role Codex CLI boxes
  once with transcript and artifact custody for `draco_live_mesh_001`.
- The run used the Codex-DR live adapter path and not an ad hoc monolithic
  `codex exec` command.

These claims are smoke-custody claims only; they do not assert a fully valid
Grep-loop execution because validation found the dependency-order issue below.

Still blocked:

- Grep parity;
- DRACO numeric score;
- leaderboard rank;
- product or service-runtime readiness;
- full benchmark execution;
- scorer custody;
- self-improvement promotion;
- reproducibility against private Grep/Parcha setup.

## Topology Finding

The completed run proves live per-role Codex CLI execution and custody, but it
also exposed a launch-order limitation in the pre-run launch plan: the writer
role was launched before the re-entry follow-up role even though the task graph
dependency points from writer to re-entry.

The command surface has since been patched so `mesh-live-plan` renders future
launch plans in dependency order. This run id was not retried, because the
run-control receipt permits only one live attempt.
