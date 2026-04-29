# Codex-DR Autonomous Flywheel Control Plane

Status: active instruction surface
Date: 2026-04-24
Workspace: `sandbox/codex-dr/`

## Purpose

This document names the missing center after the DeepResearch Bench parity
runway closed as score-claim-blocked.

The sandbox now has enough proof machinery to create an attractive failure
mode: it can package benchmark readiness, blocked scorer receipts, and candidate
gates while leaving the next experiment implicit. This control plane makes the
next loop explicit.

The center is the flywheel:

```text
RUN
  -> SCORE_OR_BLOCK
  -> CLAIM_REVIEW
  -> FAILURE_TAXONOMY
  -> CANDIDATE_GATE
  -> SELECT_NEXT_EXPERIMENT
  -> RERUN_PRESSURE
```

## Current Control Packet

The latest validated packet is:

- plan:
  `sandbox/codex-dr/tmp/deepresearch_bench_flywheel_2026_04_24/flywheel_next_action_plan.json`
- validation:
  `sandbox/codex-dr/tmp/deepresearch_bench_flywheel_2026_04_24/flywheel_next_action_validation.json`
- architect packet:
  `sandbox/codex-dr/tmp/deepresearch_bench_flywheel_2026_04_24/architect_work_packet.md`

The selected next experiment is:

- `cand_drb_numeric_appendix_prompt_001`

The current isolated overlay artifact is:

- `sandbox/codex-dr/tmp/deepresearch_bench_overlay_2026_04_24/prompt_overlay.json`

It is validated and has not changed the base prompt pack.

The selected experiment exists because the last live DeepResearch Bench run
surfaced a reviewability problem: material numeric claims need a local support
appendix so reviewer and synthesis roles can inspect quantities without reading
full transcripts or relying on opaque handles.

## Command

Regenerate the packet with:

```bash
uv run python sandbox/codex-dr/tools/alexandria_dr.py \
  --runs-dir sandbox/codex-dr/tmp/deepresearch_bench_live_2026_04_24/runs \
  deepresearch-bench-flywheel-plan deepresearch_bench_flywheel_2026_04_24 \
  --case-id deepresearch_bench_live_patched_suite_case_001 \
  --subset-summary sandbox/codex-dr/tmp/deepresearch_bench_subset_2026_04_24/runs/deepresearch_bench_subset_pressure_suite/deepresearch_bench_subset_pressure_summary.json \
  --full-run-package sandbox/codex-dr/tmp/deepresearch_bench_full_run_2026_04_24/full_run_readiness_package/full_run_package.json \
  --output-dir sandbox/codex-dr/tmp/deepresearch_bench_flywheel_2026_04_24
```

## Center-Of-Gravity Recovery

Completion object:
The Codex-DR sandbox must become a self-driving experimental lane for a
Grep-style deep-research mesh.

Intended system:
A Codex orchestrator plans, spawns scoped Codex workers, reads pointer-first
returns, synthesizes, checks adequacy, routes reviewer re-entry, writes a
single report, scores or blocks with custody, compiles failures, gates
improvements, and reruns pressure.

Kernel invariants:

- sealed benchmark references stay out of generator roles;
- pointer-first file economy stays visible and validated;
- reviewer and adequacy pressure can block the writer;
- numeric score claims require scorer custody and claim review;
- prompt, skill, scheduler, and file-economy changes need source failures,
  replay fixtures, regression gates, and promotion receipts;
- generated run data stays out of git.

Current center to demote:
Score-readiness packages and blocked claim receipts are evidence. They are not
the operating center.

Missing center added:
The next-action planner reads the latest scorer, subset, full-run, and
candidate-gate artifacts and emits the next flywheel work packet.

## Next Work

The immediate next wave is:

1. Apply the selected numeric-appendix prompt candidate as an isolated overlay.
2. Run one live DeepResearch Bench mesh case against the overlay.
3. Export the raw report and run the RACE bridge in blocked or scored mode,
   depending on authority.
4. Run claim review.
5. Run a larger subset pressure suite after the overlay.
6. Compile the next improvement packet from failures.

The full 100-case run remains blocked until scorer authority, explicit
provider-run approval, and run-control budget exist.

## Autonomous Continuation Rule

The flywheel should not wait for the Principal after every inference pass.
When the next valid action is known and lies inside the current authority
surface, continue into it.

Operationally:

1. Select work from `bd ready --no-daemon`.
2. Prefer concrete child tasks over parent epics.
3. If analysis reveals the current run or artifact is stale, record that in the
   bead and proceed to the next repair, fresh run-control, validation, or test
   step.
4. Stop only when the next action requires missing data, credentials, a
   destructive operation, a scope expansion, scorer/provider authority not
   already granted by receipt, or live execution without an approved
   run-control receipt.
5. Preserve git history by committing scoped, coherent deltas without staging
   unrelated dirty work.

## Invalid Success Conditions

These are not enough:

- another readiness memo without a selected experiment;
- a prompt edit with no source failure and no replay gate;
- a subset rerun that hides failed cases;
- a score-bearing run without official scorer custody;
- a Grep parity claim before suite-level claim review opens it.

## Claim Boundary

The current control packet opens no score, Grep parity, leaderboard,
product-readiness, or official-submission claim.
