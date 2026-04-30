---
name: autonomous-continuation-release
description: Use when the user says the agent has stopped, asks to release the brakes, grants autonomy, asks the agent to keep working, or asks how to continue without babysitting. Converts known next work into immediate execution, or recovers telos, creates durable beads, and executes the first unblocked bead when the next action is not yet known.
---

# Autonomous Continuation Release

Use this skill when the agent is at risk of ending a turn with latent work still
available.

The purpose is to turn "I know what comes next" into repo-visible execution.
It is not a permission bypass, and it is not a license to overclaim.

## Trigger

Use this skill when the user says or implies:

- "release the brakes"
- "keep working"
- "why have you stopped?"
- "do not make me babysit this"
- "you are authorized"
- "continue autonomously"
- "make beads and do the work"
- "if you do not know what to do, ground the telos and figure it out"

Also use it after a diagnosis, benchmark result, audit, or failed run when the
next repair path is inside the active authority surface.

## Core Rule

Do not stop at a procedural statement if a valid next action is available.

Invalid terminal responses:

- "I can proceed."
- "The next step is..."
- "Ready for approval."
- "Someone should create a bead."

Valid terminal states:

- `done`: work completed with evidence paths or validation output.
- `blocked`: a true blocker is recorded with the exact missing authority,
  credential, data, destructive action, or scope decision.
- `continuing`: the current unit closed and the agent is moving to the next
  concrete work item.

## Hard Stops

Stop and ask only when the next action requires:

- destructive action or irreversible data loss;
- credentials, private data, or unavailable external access;
- a paid or live provider run without the repo's required run-control receipt;
- a scope change outside the active authority surface;
- a charter or claim change the user has not ratified;
- modifying user-owned unrelated changes.

When blocked, write the blocker into the bead, ExecPlan, or repo-local artifact
when possible.

## Protocol

### 1. Establish Current Work State

Recover the active workspace and authority surface.

For `alexandria_cleanroom`, read the relevant `AGENTS.md`, then prefer:

- `docs/autonomous_continuation_protocol_2026_04_29.md`
- active ExecPlan under `docs/exec-plans/active/`
- `sandbox/codex-dr/AGENTS.md` for Codex-DR work
- `sandbox/codex-dr/AUTONOMOUS_PARITY_RUNWAY.md` for Grep-parity work
- `docs/generated/runtime/latest_allowed_claims_registry.json` before claims

Run the queue command used by the repo, such as:

```bash
bd ready --no-daemon
```

### 2. If The Next Bead Is Clear

Claim or update the highest-priority concrete ready bead and execute it.

For Beads:

```bash
bd show <bead-id> --no-daemon
bd update <bead-id> --claim --no-daemon
```

Then perform the implementation, run validation, update or close the bead with
evidence paths, and re-run the ready queue.

### 3. If The Next Action Is Clear But No Bead Exists

Create the smallest durable bead that lets a future agent recover:

- purpose;
- scope and non-goals;
- read-first files;
- first action;
- acceptance criteria;
- validation or proof artifacts;
- claim boundary.

If the work is complex, risky, or likely to span sessions, create or update an
ExecPlan before implementation.

Then claim and execute the bead.

### 4. If The Next Action Is Not Clear

Do not stall.

Run the smallest applicable recovery route:

1. Use `teleological-pre-inference` to recover the completion object, hidden
   assumptions, governing telos, constraints, definition of done, and literal
   following risk.
2. Use `center-of-gravity-recovery` if existing code, historical docs, or local
   artifacts may be pulling the work toward the wrong object.
3. Use `teleology-preserving-planning` if the plan may have missed the point or
   collapsed ambition into support machinery.
4. Use a research-plan loop when a factual or benchmark unknown controls the
   next move: identify the unknown, inspect local sources first, browse only
   when the information is current or missing, record the answer in a durable
   artifact, then create the next bead.
5. Use `bead-compiler` once the work is shaped enough to queue.

After recovery, create/update beads and execute the first unblocked bead.

### 5. Diagnosis To Execution Loop

When a test, review, benchmark, or audit finds a concrete failure:

1. Record the diagnosis.
2. Create or update a repair bead.
3. Create or update a rerun bead.
4. Create or update a re-review bead.
5. Execute the first unblocked bead.

For benchmark-facing work, preserve the claim boundary: local shadow scores,
official scores, parity claims, product readiness, and research quality are
separate claims.

### 6. End-Of-Turn Check

Before ending a response, ask:

- Is a ready bead available and inside scope?
- Did a failure produce an actionable repair?
- Did I just say "can proceed" while knowing the next command or patch?
- Is the only reason for stopping a true blocker?

If a valid next action exists, do it.

## Output Shape

Keep user updates short while working.

For final responses, include:

- what was executed;
- what evidence or validation exists;
- what bead or artifact moved;
- whether the state is `done`, `blocked`, or `continuing`;
- the next bead only if you are actually moving into it or a true blocker stops
  execution.

## Alexandria Adapter

In `/Users/singh/Desktop/alexandria_cleanroom`, this skill means:

- repo-local authority outranks chat memory;
- use `bd --no-daemon`;
- start from allowed-claims surfaces before benchmark or parity language;
- generated Codex-DR runs belong under ignored `sandbox/codex-dr/tmp/`,
  `sandbox/codex-dr/runs/`, or `sandbox/codex-dr/.agent-workspaces/`;
- Codex-DR Grep-parity work should advance by repair/rerun/re-review beads,
  not isolated conceptual notes;
- after closing a bead, run `bd ready --no-daemon` and continue unless blocked.

## Standard

This skill succeeds only when it changes behavior from passive readiness to
observable execution, or when it records a true blocker in a durable surface.
