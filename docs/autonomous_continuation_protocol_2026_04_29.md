# Autonomous Continuation Protocol

Date: 2026-04-29

## Purpose

This protocol tells an Alexandria coding agent what to do after it diagnoses a concrete blocker.

The rule is simple: diagnosis is not a terminal state when the next repair path is known and inside the active authority surface. The agent must convert the blocker into beads, execute the ready bead, and re-check the result.

## Trigger

Use this protocol when all of the following are true:

- a review, benchmark, test, live run, panel, or audit identifies a concrete failure;
- the failure has an observable repair surface;
- the next step does not require destructive action, missing credentials, private data, a paid/provider run without run-control authority, or a scope change outside the active plan;
- the user has not explicitly asked the agent to stop at analysis.

## Required Loop

1. Capture the diagnosis in a repo-local artifact or bead comment.
2. Create or update a repair bead with a teleological preamble, first action, acceptance criteria, and claim boundary.
3. Create or update a rerun bead that proves whether the repair changed behavior.
4. Create or update a re-review bead that compiles the new evidence into the next improvement packet.
5. Run `bd ready --no-daemon`.
6. Claim or update the highest-priority concrete ready bead.
7. Execute until the bead is done or blocked.
8. If done, close it with evidence paths and run `bd ready --no-daemon` again.
9. If blocked, record the blocker as a bead comment or generated artifact, then create the next repair bead if the blocker is actionable.

## Standard Bead Chain

For benchmark or deep-research failures, prefer this three-bead shape:

1. **Repair bead**: changes the harness, prompt, skill, contract, source map, or evaluator boundary that caused the failure.
2. **Rerun bead**: reruns the same case or a bounded case set under the corrected path.
3. **Re-review bead**: scores, audits, or panels the rerun and compiles the next improvement packet.

This chain is intentionally small. It prevents an agent from ending with a diagnosis, while also preventing uncontrolled loops.

## Terminal States

Valid terminal states are:

- `done`: the bead closed with proof artifacts or validation output.
- `blocked`: the next action requires a true blocker such as missing credentials, destructive action, unavailable data, or authority outside the active surface.
- `continuing`: the current bead closed and the agent is moving to the next ready bead.

Invalid terminal states are:

- “I can proceed.”
- “The next step would be...”
- “Ready for approval.”
- “Someone should create a bead.”

Those statements are only valid when paired with a true blocker.

## Claim Boundary

Autonomous continuation may create plans, beads, tests, scripts, prompt changes, run-control receipts, generated reports, and local shadow evaluations. It does not open claims of Grep parity, benchmark score, leaderboard rank, product readiness, official submission, or research quality unless the relevant scorer custody and claim-review gates explicitly open them.

## Current Codex-DR Application

For Codex-DR Grep-parity work, apply this protocol under:

- `sandbox/codex-dr/AGENTS.md`
- `sandbox/codex-dr/AUTONOMOUS_PARITY_RUNWAY.md`
- `sandbox/codex-dr/AUTONOMOUS_FLYWHEEL_CONTROL_PLANE.md`
- `sandbox/codex-dr/CODEX_DR_GREP_PARITY_EXECUTION_LADDER.md`

When a DRB, DRB II, DRACO, or related benchmark probe fails, the agent should not stop at the failure explanation. It should create the repair/rerun/re-review bead chain and execute the first unblocked bead.

## Empirical Operator Check

A human can verify this protocol is working by running:

```bash
bd ready --no-daemon
bd show <ready-bead-id> --no-daemon
git log --oneline -5
```

The ready queue should show concrete next work rather than only a broad parent epic. Recent commits or bead comments should point to proof artifacts, failed checks, rerun outputs, or next blockers.
