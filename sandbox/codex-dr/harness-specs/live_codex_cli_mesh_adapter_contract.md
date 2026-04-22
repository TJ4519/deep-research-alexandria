# Live Codex CLI Mesh Adapter Contract

Status: active dry-run contract for `alexandriacleanroom-91.1.5.9`
Date: 2026-04-22
Workspace: `sandbox/codex-dr/`

## Purpose

This contract defines the live Codex CLI mesh adapter boundary without
launching `codex exec`.

The adapter turns a DR mesh task graph and role configuration into per-role
Codex CLI launch plans. It is dry-run-only while the current launch halt
remains active.

## Command Surface

```bash
alexandria-dr mesh-live-plan <case_id> --run-control <receipt.json>
```

Current repo-local script form:

```bash
uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir <runs_dir> \
  mesh-live-plan <case_id> \
  --run-control <receipt.json>
```

The command must not invoke `codex exec`, create transcripts, create provider
metadata, call providers, execute a benchmark, or score a benchmark.

## Inputs

The command reads an existing provider-off DR mesh run bundle:

- `run_manifest.json`
- `task_graph.json`
- `role_configs.json`
- `terminal_agent_boxes.json`

It also reads a JSON run-control receipt. The dry-run planner requires:

- matching `run_id`;
- `runner.kind: codex_exec_box`;
- `runner.cwd`;
- `runner.transcript_root`;
- `operational_bounds.max_wall_clock_minutes`;
- `operational_bounds.foreground_supervision_required: true`;
- `operational_bounds.automatic_retry_allowed: false`;
- `operational_bounds.kill_path`;
- `allowed_claims_if_success`;
- `non_claims_even_if_success`;
- `approval.approved_for_dry_run_planning: true`;
- `approval.approved_for_execution: false`.

Receipts approved for live execution are refused by this dry-run command. Live
execution requires a separate Principal reopening and command path.

## Outputs

The command writes only dry-run planning artifacts under the run bundle:

```text
live_adapter/
  launch_plan.json
  prompts/
    <task_id>.md
```

`launch_plan.json` uses schema `codex-dr.live_adapter_launch_plan.v1` and
contains one role launch plan per task.

Each role launch plan records:

- `task_id`;
- `role`;
- `role_config_id`;
- `box_id`;
- `adapter_kind: codex_cli_box_dry_run`;
- `launch_status: planned_not_launched`;
- `command_plan`;
- `cwd`;
- `prompt_file`;
- `allowed_input_files`;
- `output_paths`;
- `transcript_path`;
- `wall_clock_bound_minutes`;
- `kill_path`;
- `claim_boundary`;
- `scorer_policy`;
- `will_execute: false`.

Prompt files are dry-run artifacts that describe the role objective, allowed
inputs, expected outputs, run-control boundary, and non-claims.

## Fail-Closed Behavior

The command fails before writing `live_adapter/` when:

- the run bundle does not exist;
- the bundle is not a provider-off DR mesh bundle;
- the run-control receipt is missing;
- the receipt is invalid JSON;
- the receipt does not match the run id;
- dry-run planning is not explicitly approved;
- live execution is approved on the receipt;
- required supervision, wall-clock, kill path, transcript root, claim, or
  scorer-policy fields are missing;
- a task references a missing role config or terminal-agent box.

## Claim Boundary

Permitted claim after a successful dry-run:

- the adapter rendered deterministic launch plans and prompt files from the
  mesh task graph and role configs.

Blocked claims:

- a Codex CLI role ran;
- a provider-backed branch produced research;
- benchmark scoring happened;
- Grep parity;
- DRACO score;
- product readiness.

## Validation

Required tests:

- unauthorized or missing receipt fails closed and creates no provider
  artifacts;
- authorized dry-run receipt emits launch plans and prompt files only;
- sandbox test suite passes;
- `git diff --check` passes;
- `make check` passes.
