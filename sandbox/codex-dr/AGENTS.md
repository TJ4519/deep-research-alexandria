# Codex-DR Sandbox AGENTS.md

This file is the local operating map for the Codex-DR sandbox architect.
It narrows the root `AGENTS.md`; it does not replace the root repo rules.

## Mission

Build the Codex-based deep-research sandbox that attempts full Grep-system-and-
performance parity through terminal-agent harnessing, recursive research
coordination, adequacy backpressure, benchmark evaluation, visible tools, and
Alexandria custody receipts.

The sandbox proves the research engine. The product runtime comes later through
separate service-runtime design.

## Start Here

1. `README.md`
2. `CODEX_DR_GREP_PARITY_EXECUTION_LADDER.md`
3. `AUTONOMOUS_PARITY_RUNWAY.md`
4. `AUTONOMOUS_FLYWHEEL_CONTROL_PLANE.md`
5. `docs/BOOTSTRAP_DOCTRINE.md`
6. `docs/ARCHITECT_HANDOFF.md`
7. `harness-specs/dr_mesh_parity_charter.md`
8. `harness-specs/grep_parity_contract.md`
9. `../../docs/references/grep_building_grep_deep_research_2026_03_16.md`
10. `../../ALEXANDRIA_CHARTER.md`
11. `../../PLAN_TO_CREATE_ALEXANDRIA.md`
12. `../../docs/design-docs/codex_dr_sandbox_architect_handoff_2026_04_22.md`
13. `../../docs/design-docs/reimagined_alexandria_authority_ledger_2026_04_21.md`
14. `../../docs/references/claude_in_a_box_grep_agents_sdk_2025_12_11.md`
15. `../../docs/exec-plans/active/codex_dr_sandbox_architect_handoff.md`

Before planning, delegation, bead creation, or architect launch in this lane,
search Open Brain for `DR mesh`, `Grep parity execution ladder`, and `Codex
orchestrator spawning Codex workers`. The retrieval should recover the
Codex-cli native DR mesh flywheel and the lesson that Grep intent must be
compiled into a parity execution ladder before agents fan out.

## Working Invariants

- Historical halt: `docs/codex_exec_halt_2026_04_22.md` records the prior stop
  after uncontrolled `codex exec` token burn. Current authority is receipt
  control. Do not launch ad hoc `codex exec`, `codex-exec`, or
  `/usr/bin/script ... codex exec`. Live DR mesh runs must go through
  `alexandria-dr mesh-execute-live` with an approved run-control receipt.
  Model access checks must go through `alexandria-dr model-probe`, which writes
  a bounded probe receipt and cannot widen benchmark or parity claims.
  Read `docs/codex_mesh_launch_control_2026_04_22.md` first.
- Use `uv` and root repo commands when Python tooling is required.
- Keep generated run outputs under `runs/`, `.agent-workspaces/`, or `tmp/`.
- Do not store secrets, provider transcripts with private data, customer data,
  or raw paid benchmark corpora in git.
- Treat root Program 80 and Program 90 artefacts as historical proof surfaces
  unless a bead explicitly asks for integration.
- Treat old numbered NLSpecs as audit material unless the authority ledger has
  promoted a clause.
- Make every sandbox claim trace to a run bundle, benchmark manifest, receipt,
  or explicit non-claim.
- Keep terminal-agent I/O observable through wrapper scripts, event mirrors, and
  content-addressed artefact manifests.
- Design for a CLI control surface named `alexandria-dr`.
- Complete the bootstrap autonomy gate before unattended live runs.
- Treat benchmark acquisition as target calibration until the provider-off
  bootstrap validator passes.
- Autonomous continuation is required in this lane. Once the agent can name the
  current bead, parity rung, fake success condition, proof artifact, and next
  command or patch, it should execute the next step rather than wait for tacit
  approval. Stop only for a genuine blocker: missing receipt, missing
  credentials or data, destructive action, scope expansion outside this
  workspace, or live/provider execution not covered by run-control.

## Non-Negotiable Target

The target is Grep-system-and-performance parity pressure, not a small demo.

In this sandbox, the Principal's noun for the Grep-style system is **DR mesh**.
The DR mesh is the recursive deep-research agent system shown in the
Principal-provided Grep topology figures and specified in
`harness-specs/dr_mesh_parity_charter.md`. The execution ladder in
`CODEX_DR_GREP_PARITY_EXECUTION_LADDER.md` is the current work substrate that
turns that topology into parity rungs, proof artifacts, invalid success
conditions, and bead-shaping law.

A vertical slice may be used as a stepping stone. It is not the finish line.
The first proof run must exercise planner ratification, recursive branch
research, scoped agents with subagent rights where the harness supports them,
evidence return, synthesis, QA backpressure, reviewer-driven re-entry, report
creation, benchmark scoring, event logs, and custody receipts.

## Bootstrap Autonomy Gate

Before implementation autonomy, complete the gate in
`docs/BOOTSTRAP_DOCTRINE.md`.

The first executable lane is provider-off:

- centre-lock receipt
- run-bundle skeleton
- local fixture case
- fake planner
- fake branch return
- fake reviewer finding
- re-entry compiler fixture
- claim ledger
- compaction receipt fixture
- allowed-claims output
- validator that fails on missing custody or missing re-entry

No unattended model call, repeated benchmark execution, or background
terminal-agent research run is valid until this lane is specified and the
validator plan exists.

## Live Run Control

The Codex-DR sandbox uses run-control receipts for live Codex CLI and
terminal-agent runs.

Use `harness-specs/live_run_control_receipt_template.md`.

Do not treat the old `42,000` token target or token-manifest vocabulary as an
architectural gate. That was runtime-control leakage from earlier Alexandria
work. For this sandbox, the live-run gate is named authorization, exact command
or adapter, foreground supervision or external monitoring, wall-clock bound,
kill path, transcript capture, output boundary, data policy, scorer status, and
claim boundary.

Launch control prevents hidden background burns and uncontrolled retries. It
must not become a substitute for building the planner, orchestrator, branch
adapters, reviewer backpressure, synthesis, benchmark lane, and scorer bridge.

## Required Skill Gates

- Use `center-of-gravity-recovery` before reading broad root implementation or
  Program 90 surfaces.
- Use `teleological-pre-inference` before changing scope, delegation, or
  autonomy.
- Use `teleology-preserving-planning` before writing or revising parity,
  harness, or bootstrap contracts.
- Use `evidence-first-backpressure` before benchmark, provider, SDK, or parity
  claims.
- Use `spec-interface-auditor` before implementation begins from any contract.
- Use `bead-compiler` only after the governing surface and proof gates are
  stable.

## Required First Moves

1. Keep `CODEX_DR_GREP_PARITY_EXECUTION_LADDER.md` authoritative for new
   architect launches and beads.
2. Complete the next ready parity rung from the ladder.
3. Use bootstrap and benchmark-audit artifacts as proof gates, not finish-line
   substitutes.
4. If a bead remains open after an audit, immediately continue into the next
   patch, test, run-control, or validation step. Do not end a turn with
   "ready to proceed" when the next action is already known and within
   authority.

The audit calibrates the target. It does not authorize benchmark execution by
itself.

The audit identifies which Grep-cited benchmark families can be acquired and
run locally, what licenses or data restrictions apply, how cases are selected,
what scores must be reproduced, and which parity claims remain unavailable.

## Autonomous Parity Runway

`AUTONOMOUS_PARITY_RUNWAY.md` is the current authorization and bead-generation
surface for scored DeepResearch Bench work. If `bd --no-daemon ready --json`
has no Codex-DR parity work, read that file and create the next self-starting
bead from its Next Bead Wave.

`AUTONOMOUS_FLYWHEEL_CONTROL_PLANE.md` is the current post-runway control
surface. If the score-readiness runway is complete and the queue is empty, use
the flywheel plan command to select the next experiment from proof artifacts
before creating or executing more work.

Every score-bearing run must refresh official DeepResearch Bench sources first.
As of 2026-04-24, the official repository says the evaluator lane is migrating
away from Gemini-2.5-Pro before June 2026, and the leaderboard lists `grep-v5`
at 56.23 overall. Treat that as a refreshed target snapshot, not permanent
truth.

## Continuation Loop

Durable reference:
`docs/autonomous_continuation_protocol_2026_04_29.md`.

Use this loop whenever work is not complete:

1. Run `bd ready --no-daemon`.
2. Prefer the highest-priority concrete Codex-DR task over its parent epic.
3. Claim or update the bead with `bd --no-daemon`.
4. State the parity rung, fake success condition, proof artifact, and first
   command or file to inspect.
5. Execute until the bead is done or blocked.
6. Record evidence or blocker details in bead comments and, when useful, a
   repo-local artifact.
7. If the bead closes, run `bd ready --no-daemon` again and continue with the
   next unblocked bead.
8. Commit and push only the scoped files touched for the completed bead when
   the change is coherent and the working tree contains unrelated changes.

The default terminal states are `done`, `blocked`, or `continuing`. A bare
proposal is not a terminal state.

## Workspace Boundary

This workspace may own:

- sandbox-specific specs
- benchmark manifests
- test cases
- harness configuration drafts
- terminal-agent wrapper contracts
- run-bundle schemas
- local CLI design
- provider-off fixture cases
- bootstrap validators
- proof-run plans

This workspace may read root docs and app code. It must not change root
runtime code, root authority documents, legacy NLSpecs, product service code,
or Program 90 artefacts unless the bead or ExecPlan explicitly widens scope.

## Completion Shape

The architect's handoff is complete when a future builder can start from this
folder and know:

- what the sandbox is for
- what full parity means as an attempted target
- what the provider-off bootstrap lane must prove first
- what launch-control receipt blocks hidden or unbounded live runs
- which benchmark work starts first
- which files hold authority
- how root `AGENTS.md` interacts with this local `AGENTS.md`
- where generated runs go
- which claims are allowed after each proof gate
