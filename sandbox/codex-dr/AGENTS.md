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
2. `docs/BOOTSTRAP_DOCTRINE.md`
3. `docs/ARCHITECT_HANDOFF.md`
4. `../../ALEXANDRIA_CHARTER.md`
5. `../../PLAN_TO_CREATE_ALEXANDRIA.md`
6. `../../docs/design-docs/codex_dr_sandbox_architect_handoff_2026_04_22.md`
7. `../../docs/design-docs/reimagined_alexandria_authority_ledger_2026_04_21.md`
8. `../../docs/references/grep_building_grep_deep_research_2026_03_16.md`
9. `../../docs/references/claude_in_a_box_grep_agents_sdk_2025_12_11.md`
10. `../../docs/exec-plans/active/codex_dr_sandbox_architect_handoff.md`

## Working Invariants

- Current halt: do not launch `codex exec`, `codex-exec`,
  `/usr/bin/script ... codex exec`, or any terminal-agent provider-backed smoke
  run from this sandbox until the Principal explicitly reopens a named run.
  Read `docs/codex_exec_halt_2026_04_22.md` first.
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
- Complete the bootstrap autonomy gate before provider-backed runs.
- Treat benchmark acquisition as target calibration until the provider-off
  bootstrap validator passes.

## Non-Negotiable Target

The target is Grep-system-and-performance parity pressure, not a small demo.

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

No paid model call, benchmark execution, or terminal-agent research run is
valid until this lane is specified and the validator plan exists.

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

1. Complete the Bootstrap Autonomy Gate before implementation design hardens.
2. Perform the Benchmark Acquisition Audit before benchmark claims harden.

The audit calibrates the target. It does not authorize benchmark execution by
itself.

The audit identifies which Grep-cited benchmark families can be acquired and
run locally, what licenses or data restrictions apply, how cases are selected,
what scores must be reproduced, and which parity claims remain unavailable.

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
- what token-burn firewall blocks provider-backed runs
- which benchmark work starts first
- which files hold authority
- how root `AGENTS.md` interacts with this local `AGENTS.md`
- where generated runs go
- which claims are allowed after each proof gate
