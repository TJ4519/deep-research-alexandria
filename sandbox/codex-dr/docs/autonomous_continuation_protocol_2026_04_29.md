# Autonomous Continuation Protocol

Date: 2026-04-29
Scope: `sandbox/codex-dr/`

## Purpose

This protocol prevents the Codex-DR lane from stalling after an agent has
already inferred the correct next action.

The failure mode it blocks is:

```text
agent understands the next bead
  -> says "I can proceed"
  -> waits for another user injection
  -> user becomes the scheduler
```

The desired behavior is:

```text
agent understands the next bead
  -> records the governing reason
  -> executes the next valid step
  -> reports done, blocked, or continuing
```

## Operating Rule

Autonomous continuation is the default once intent and authority are clear.

When an agent can name:

- current bead;
- parity rung;
- fake success condition;
- proof artifact;
- next command, patch, validation, or run-control step;

it should continue without waiting for tacit user authorization.

## Stop Conditions

Stop and ask only when the next step requires one of these:

- destructive filesystem or git action;
- missing credentials, private data, or external account access;
- scope expansion outside the active authority surface;
- live/provider execution without an approved run-control receipt;
- score-bearing benchmark execution without scorer authority;
- committing unrelated dirty work that cannot be separated safely.

If the next action is blocked, record the blocker in the bead and perform the
next safe audit, patch, or validation that does not require the missing input.

## Bead Loop

Use this loop until the queue is empty or blocked:

1. Run `bd ready --no-daemon`.
2. Prefer the highest-priority concrete child task over its parent epic.
3. Claim or update the bead.
4. State the parity rung, fake success condition, proof artifact, and first
   command or file to inspect.
5. Execute until the bead is done or blocked.
6. Record evidence or blocker details in bead comments.
7. Write a repo-local proof or audit artifact when the work changes the runway.
8. Run targeted validation.
9. Commit and push scoped files when the change is coherent.
10. Run `bd ready --no-daemon` again and continue.

## Git Rule

Commit history is part of the proof trail.

When work produces a coherent delta, commit and push the scoped files touched by
that bead. Do not stage unrelated dirty work. If the bead database contains
broad unrelated JSONL changes, record bead progress in comments but avoid
committing the database until it can be separated safely.

## Claim Boundary

This protocol authorizes continuation of repo-local audit, planning,
implementation, tests, validation, run-control preparation, and approved live
runs.

It does not authorize widening benchmark, Grep parity, leaderboard,
product-readiness, scorer-backed, or official-submission claims.
