# Codex-DR Harness Boundary Audit

Date: 2026-04-29
Bead: `alexandriacleanroom-99.22`
Status: A1 preflight complete; targeted proof slice passed

## Question

Where does OpenAI/Codex runtime authority end, and where does Alexandria
Codex-DR harness authority begin?

This audit exists because `alexandriacleanroom-99.22` asks for a fresh
status-derived adequacy live proof. That proof is only meaningful if the live
run demonstrates Alexandria-owned custody over Codex CLI role execution rather
than relying on uncontrolled Codex session state.

## Short Answer

The two harnesses are layered, not mutually exclusive.

OpenAI/Codex provides the role execution substrate. Alexandria provides the
mesh coordinator, file custody, run-control receipts, canonical artifacts,
validators, event log, gate decisions, and claim boundaries.

The conflict risk is uncontrolled launch. A live role run is valid only when it
goes through the Alexandria command surface and produces inspectable run-bundle
artifacts.

## Boundary Map

| Layer | Owner | What It Does | What It Must Not Own |
| --- | --- | --- | --- |
| Codex runtime / CLI | OpenAI Codex | Executes a role prompt inside a workspace and returns transcript/output files. | Canonical run state, benchmark claims, writer gate truth, claim widening. |
| Alexandria live adapter | `mesh-live-plan` | Converts task graph and role configs into per-role Codex CLI launch plans and prompts. | It must not launch Codex during planning. |
| Alexandria live executor | `mesh-execute-live` | Validates live receipt, batches dependency-ready roles, creates workspaces, copies scoped inputs, runs Codex CLI, captures transcripts, copies declared outputs, and writes execution events. | It must not run without an approved execution receipt or accept undeclared outputs as canonical truth. |
| Alexandria validators | `validate_run` checks | Decide whether the run bundle satisfies custody, topology, adequacy, scoring, and claim rules. | They must not treat prompt compliance as empirical proof. |
| Alexandria claim gates | allowed-claims and claim-review artifacts | Decide what may be claimed from the proof bundle. | They must not widen Grep parity, score, leaderboard, or product-readiness claims without scorer custody and claim review. |

## Evidence From Repo

### Launch Planning

`mesh_live_plan(...)` reads the existing run bundle, task graph, role configs,
terminal-agent box definitions, and run-control receipt. It writes
`live_adapter/launch_plan.json` and per-role prompts.

Relevant implementation:

- `sandbox/codex-dr/tools/alexandria_dr.py::mesh_live_plan`
- The command plan is rendered as `codex exec --json ... --cd <workspace>
  --add-dir <run_bundle> --output-last-message <path> -`.
- The launch plan records `will_execute` from the receipt approval state.

Authority interpretation:

- The adapter decides what roles Codex may run as.
- The adapter decides which files each role may read.
- The adapter decides which outputs count.
- Codex has not run yet at this stage.

### Live Execution

`mesh_execute_live(...)` is the intended controlled path for live Codex role
execution. It requires a live execution receipt, validates the launch plan,
builds dependency batches, and runs each role through `execute_live_role(...)`.

Relevant implementation:

- `sandbox/codex-dr/tools/alexandria_dr.py::mesh_execute_live`
- `sandbox/codex-dr/tools/alexandria_dr.py::run_live_execution_batch`
- `sandbox/codex-dr/tools/alexandria_dr.py::execute_live_role`
- `sandbox/codex-dr/tools/alexandria_dr.py::run_codex_cli_role`

Authority interpretation:

- Alexandria owns the live execution sequence.
- Codex owns the cognition inside each role execution.
- Alexandria copies only declared outputs back into the run bundle.
- Alexandria records transcripts, last messages, copied inputs, copied
  outputs, role events, and scheduler state.

### Workspace and File Custody

`execute_live_role(...)` creates a role workspace under
`sandbox/codex-dr/.agent-workspaces/<run_id>/...`, copies only allowed input
files into that workspace, writes a `LIVE_PROMPT.md`, runs Codex, then copies
declared outputs to:

- `live_executor/role_outputs/<task_id>/...`
- canonical run-bundle paths, unless the output is listed as a control-only
  output.

Authority interpretation:

- Role workspaces are disposable execution boxes.
- The run bundle is the durable evidence surface.
- Canonical outputs come from declared contracts, not arbitrary Codex prose.

### Backpressure and Writer Gate

`mesh_execute_live(...)` checks `writer_blocked_by_adequacy_backpressure(...)`
before running a final writer batch. If open adequacy pressure remains, it may
attempt recursive re-entry up to the run-control limit. If pressure remains
after re-entry capacity is exhausted, the writer batch is blocked.

Authority interpretation:

- Reviewer and adequacy roles can produce semantic pressure.
- The harness compiles pressure into canonical queue/gate artifacts.
- The harness decides whether the writer can run.
- The writer must not decide that it is allowed to ignore open pressure.

## Current Risk For `99.22`

The next live proof must specifically prove status-derived adequacy pressure
affects execution.

The fake success condition is a live run that completes and writes a plausible
final report while adequacy pressure should have forced recursive re-entry or
lawful writer blockage.

The proof run therefore needs evidence for one of two valid outcomes:

1. Recursive re-entry is triggered from status-derived adequacy pressure, re-entry
   outputs are produced, synthesis is refreshed, and the writer is allowed only
   after pressure clears.
2. Recursive re-entry cannot clear the pressure within the receipt bounds, and
   the final writer is lawfully blocked before a weak report is exported.

## Next-Bead Selection Rule

I will not wait for chat permission after each bead. The next bead is selected
by this rule:

1. Run `bd ready --no-daemon`.
2. Prefer the highest-priority ready concrete task over its parent epic.
3. Read the bead, the local `sandbox/codex-dr/AGENTS.md`, and the active
   execution ladder.
4. State the parity rung, fake success condition, proof artifact, and first
   command or file to inspect.
5. Execute until the bead is done or blocked.
6. If done, record evidence in the bead and move to the next ready bead.
7. If blocked, record the blocker, the exact unblocking condition, and the
   next safe audit or patch that does not require the missing input.

For the current queue, this selects:

- `alexandriacleanroom-99.22`
- parity rung: inner-loop adequacy recursion / outer-loop writer gate
- fake success: live completion without re-entry or lawful writer blockage
- proof artifact: new run bundle with validation, backpressure, gate, and
  execution summary artifacts refreshed

## Immediate Next Action

Run a command-surface audit for `99.22` before executing the live proof:

1. Identify the latest relevant run-control receipt for status-derived adequacy
   live proof.
2. Identify the command that creates the fresh run id.
3. Confirm the run-control receipt permits exactly the intended live execution.
4. Confirm validation checks include:
   - live execution custody;
   - status-derived adequacy queue/gate behavior;
   - writer blockage or recursive re-entry;
   - score and parity claim blockage.

If any of those are missing, patch tests/validators before running the live
proof.

## Command-Surface Audit Result

Existing `99.22` surface:

- root:
  `sandbox/codex-dr/tmp/deepresearch_bench_status_gap_live_99_22/`
- case 001:
  `sandbox/codex-dr/tmp/deepresearch_bench_status_gap_live_99_22/runs/deepresearch_bench_status_gap_live_suite_99_22_case_001/`
- run controls summary:
  `sandbox/codex-dr/tmp/deepresearch_bench_status_gap_live_99_22/run_controls/run_controls_summary.json`

The existing case 001 run did execute live Codex CLI roles and reached:

```text
execution_status: blocked_by_adequacy_backpressure
blocked_task_ids: ["task_final_writer"]
recursive_reentry_rounds_used: 1
```

Current-code validation command:

```bash
uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir sandbox/codex-dr/tmp/deepresearch_bench_status_gap_live_99_22/runs \
  validate deepresearch_bench_status_gap_live_suite_99_22_case_001
```

Current-code validation result:

```text
failed
failed_checks:
- prompt_contract_drift_guard
- evidence_quality_handoffs_valid
- adequacy_backpressure_queue_present
- backpressure_gate_receipt_valid
- writer_gate_preflight_valid
- allowed_claims_scope_enforced
```

Interpretation:

The prior `99.22` run is directionally relevant but stale. It proves that a
live role sequence once reached lawful adequacy blockage, but it does not prove
the post-repair harness. Current validation rejects it because the run predates
newer prompt-contract, evidence-handoff, canonical queue v2, gate receipt,
writer preflight, and allowed-claims requirements.

Therefore `alexandriacleanroom-99.22` remains open. The next valid action is
not to interpret the old run as closure. The next valid action is to generate
or identify a fresh post-repair run id and live run-control receipt, render a
new launch plan with current prompts, execute through `mesh-execute-live`, and
validate the new run under current code.

## Validation Run During A1

Command:

```bash
uv run pytest sandbox/codex-dr/tests/test_provider_off_bootstrap.py -q \
  -k 'remaining_gap_status or writer_gate_preflight or lawfully_blocks_writer_on_open_backpressure or runs_recursive_reentry_before_writer'
```

Result:

```text
4 passed
```

Interpretation:

- status-derived `remaining_gap` adequacy pressure is compiled into open
  writer-blocking backpressure in the targeted fixture;
- missing or contradictory gate receipts block writer preflight;
- an open live backpressure queue lawfully blocks the final writer after one
  re-entry attempt;
- recursive re-entry can clear the pressure before writer execution in the
  targeted fixture.

This is not yet the fresh DeepResearch Bench live run required by
`alexandriacleanroom-99.22`. It is the local proof slice that says the next
fresh run has the right harness machinery to test.

## Claims

This audit proves the harness boundary is legible enough to proceed to the
next `99.22` preflight.

It does not prove:

- a fresh live proof has been run;
- status-derived adequacy pressure currently triggers re-entry;
- writer blocking is correct in all live paths;
- DeepResearch Bench scoring has occurred;
- Grep parity;
- product readiness.
