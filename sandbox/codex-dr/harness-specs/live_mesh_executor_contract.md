# Live Mesh Executor Contract

Status: active no-launch contract for `alexandriacleanroom-91.1.5.11`
Date: 2026-04-23
Workspace: `sandbox/codex-dr/`

## Purpose

This contract defines the no-launch executor boundary that sits after
`mesh-live-plan` and before any future live Codex CLI execution.

The executor preflight consumes a rendered launch plan, validates the
run-control receipt and launch-plan invariants, and prepares per-role execution
metadata without invoking `codex exec`.

## Command Surface

```bash
alexandria-dr mesh-executor-preflight <case_id> --run-control <receipt.json>
```

Current repo-local script form:

```bash
uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir <runs_dir> \
  mesh-executor-preflight <case_id> \
  --run-control <receipt.json>
```

The command must not launch Codex CLI, create transcripts, create provider
metadata, write live branch outputs, execute a benchmark, or score a benchmark.

## Inputs

The command reads:

- `live_adapter/launch_plan.json`;
- the supplied JSON run-control receipt;
- the existing provider-off DR mesh run bundle.

The run-control receipt must remain execution-closed:

- `approval.approved_for_dry_run_planning: true`;
- `approval.approved_for_execution: false`;
- foreground supervision required;
- automatic retry disabled;
- wall-clock bound present;
- kill path present;
- transcript root present.

The launch plan must contain:

- matching `run_id`;
- `launch_mode: dry_run_only`;
- matching `run_control_receipt`;
- at least one `role_launch_plans` entry;
- per-role `cwd` under `sandbox/codex-dr/.agent-workspaces/<run_id>/`;
- per-role `prompt_file`;
- per-role `transcript_path`;
- per-role non-empty relative `output_paths`;
- `will_execute: false`.

## Outputs

The command writes one artifact:

```text
live_executor/execution_preflight.json
```

The artifact uses schema `codex-dr.live_executor_preflight.v1` and records:

- run id;
- run-control receipt path;
- launch-plan path;
- execution status `not_launched_current_halt`;
- workspace root;
- transcript root;
- supervision metadata;
- one preflight record per role;
- blocked side effects;
- non-execution guarantee.

## Fail-Closed Behavior

The command fails before writing `live_executor/` when:

- `live_adapter/launch_plan.json` is missing;
- the run-control receipt is missing or invalid;
- the receipt is approved for execution;
- the receipt run id does not match the requested run id;
- transcript root is missing;
- the launch plan run id does not match the requested run id;
- the launch plan receipt path does not match the supplied receipt;
- any role launch plan lacks workspace path, transcript path, prompt file, or
  output contracts;
- any role launch plan has absolute output contracts;
- any role launch plan sets `will_execute` to anything except `false`.

## Claim Boundary

Permitted claim after this command succeeds:

- the no-launch executor preflight validated launch-plan custody and prepared
  execution metadata for a future supervised live mesh run.

Blocked claims:

- a Codex CLI role ran;
- a provider-backed branch produced research;
- transcripts were captured;
- benchmark scoring happened;
- Grep parity;
- DRACO score;
- product readiness.

## Validation

Required tests:

- missing launch plan fails closed;
- execution-approved receipt fails closed;
- mismatched launch-plan run id fails closed;
- missing workspace path fails closed;
- missing transcript root fails closed;
- missing output contracts fails closed;
- successful preflight creates only `live_executor/execution_preflight.json`;
- no provider metadata, transcripts, or live branch outputs are created.
