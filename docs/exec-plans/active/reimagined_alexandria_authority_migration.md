# Reimagined Alexandria Authority Migration

Status: active
Owner: Principal / coding agent
Bead: `alexandriacleanroom-91`
Canon refs:
- `ALEXANDRIA_CHARTER.md`
- `PLAN_TO_CREATE_ALEXANDRIA.md`
- `canon/specs/ALEXANDRIA_CHARTER.md`
Constraining canon refs:
- `docs/references/third_party_reimagining/2026_04_20_alexandria_design_document_commissioning_brief_v1.md`
- `docs/design-docs/alexandria_reimagining_context_pack_intake_2026_04_20.md`
- `docs/design-docs/reimagined_alexandria_authority_ledger_2026_04_21.md`
- `docs/design-docs/alexandria_frankenengine_plan_donor_analysis_2026_04_21.md`
- `docs/references/claude_in_a_box_grep_agents_sdk_2025_12_11.md`
- `docs/design-docs/claude_in_a_box_implications_for_alexandria_agent_py_2026_04_21.md`
Last updated: 2026-04-21

## Why This Plan Exists

The root plan now names Alexandria's reimagined center: Grep-class recursive
deep-research cognition, extended through event-complete custody,
content-addressed artefacts, reconstructibility, and pharma CI
chain-of-custody. The repo still contains older numbered NLSpecs, Program
80-90 proof surfaces, and current runtime code that may contain useful substrate
or inherited drift.

This plan keeps the next work lane recoverable without chat. It owns the
transition from root plan candidate to ratified authority, then from ratified
authority into old-spec audit and commissioned design-document entry.

## Scope

- Refine and ratify `ALEXANDRIA_CHARTER.md`.
- Refine and ratify `PLAN_TO_CREATE_ALEXANDRIA.md`.
- Resolve the missing Context Pack 07 status.
- Update repo authority maps after ratification.
- Audit legacy NLSpecs and current repo assets against the reimagined plan.
- Produce the Commission Restatement Candidate required by the Commissioning
  Brief.
- Open the commissioned Alexandria Design Document program after the restatement
  and audit gates are ready.

## Non-Goals

- Do not implement runtime code in this lane.
- Do not delete legacy specs before audit.
- Do not create Linear tickets.
- Do not claim Grep parity, pharma readiness, or design-doc completion from the
  root plan alone.

## Preserved Invariants

- The root plan governs reimagining only after Principal ratification.
- The current Charter remains lineage unless explicitly superseded.
- Context Pack material is rationale and design pressure, not a silent Charter
  amendment.
- Old NLSpecs are not automatically binding for the reimagined system until
  audited and re-ratified or retained.
- The data pipeline is presumed valuable but must not pull runtime architecture
  away from the reimagined telos.

## Pre-Mortem

False confidence risk: a future agent may treat `ALEXANDRIA_CHARTER.md` or
`PLAN_TO_CREATE_ALEXANDRIA.md` as already ratified because it sits at the root
and has been pushed to GitHub.

Drift risk: a future agent may update `AGENTS.md` too early and leave legacy
NLSpecs in a mixed authority state that is harder to reason about than the
current one.

Flattening risk: a future agent may reduce the plan to filesystem memory and
event logging, losing recursive evidence retrieval, synthesis,
reconciliation, skills, orchestration loops, and reviewer-driven re-entry.

Overreach risk: a future agent may begin the Design Document or implementation
before the Commission Restatement is ratified.

Substrate drift risk: a future agent may treat the old no-Agents-SDK clause as
settled even after the Grep Claude-in-a-Box article showed that Grep's current
implementation substrate uses isolated Claude Agent SDK boxes.

## Red/Green TDD Plan

This lane is documentation and governance work, so the red/green proof is
structural rather than unit-test-first:

- Red: `bd ready --no-daemon` has no recoverable reimagining lane.
- Green: the bead graph exposes the root-plan ratification front door and
  blocked downstream tasks.
- Red: repo entrypoints still imply old NLSpecs are automatically authoritative
  for reimagining work after plan ratification.
- Green: authority maps name the ratified plan and old-spec audit status.
- Red: Pack 07 is missing but design work proceeds as if context is complete.
- Green: Pack 07 is imported or a dated Principal waiver is repo-local.

## Proof Posture

`TARGET_ONLY` until:

- the root plan is ratified or amended;
- Pack 07 is resolved or waived;
- authority maps are updated after ratification;
- legacy material is audited;
- the Commission Restatement Candidate is ready for Principal review.

## Temporary Seams

- `ALEXANDRIA_CHARTER.md` currently has candidate authority only.
- `PLAN_TO_CREATE_ALEXANDRIA.md` currently has candidate authority only.
- Context Pack 07 is unresolved.
- Legacy NLSpecs remain present and discoverable while audit status is pending.
- Only the root plan and `.gitignore` are committed to the public GitHub repo;
  the broader cleanroom codebase remains local and untracked.

## Repo Orientation

Read first:

- `ALEXANDRIA_CHARTER.md`
- `PLAN_TO_CREATE_ALEXANDRIA.md`
- `docs/design-docs/reimagined_alexandria_authority_ledger_2026_04_21.md`
- `AGENTS.md`
- `canon/CANON.md`
- `canon/specs/ALEXANDRIA_CHARTER.md`
- `docs/WORKFLOW.md`
- `docs/PLANS.md`
- `docs/design-docs/alexandria_reimagining_context_pack_intake_2026_04_20.md`
- `docs/design-docs/third_party_reimagining_artifact_registry_2026_04_20.md`

Bead graph:

- `alexandriacleanroom-91`: reimagining authority and design entry epic
- `alexandriacleanroom-91.1`: refine and ratify root plan
- `alexandriacleanroom-91.2`: resolve missing Context Pack 07
- `alexandriacleanroom-91.3`: update authority maps after root plan ratification
- `alexandriacleanroom-91.4`: audit legacy NLSpecs and repo assets
- `alexandriacleanroom-91.5`: produce Commission Restatement Candidate
- `alexandriacleanroom-91.6`: open commissioned Design Document program

## Plan Of Attack

1. Complete `91.1` by refining the root plan with the Principal and committing
   scoped revisions.
2. Complete `91.2` by importing Context Pack 07 or recording a waiver.
3. Complete `91.3` after ratification by updating repo authority maps.
4. Complete `91.4` by producing the legacy NLSpec and repo-surface audit.
5. Complete `91.5` by writing the Commission Restatement Candidate.
6. Complete `91.6` by creating the design-document production plan and blocking
   implementation until the required interfaces and artefact formats are
   specified.

## Progress Log

- 2026-04-21: Created root GitHub repo
  `TJ4519/deep-research-alexandria` and pushed the first commit containing
  `.gitignore` and `PLAN_TO_CREATE_ALEXANDRIA.md`.
- 2026-04-21: Opened beads `alexandriacleanroom-91` through
  `alexandriacleanroom-91.6`.
- 2026-04-21: Created this ExecPlan.
- 2026-04-21: Added root reimagined charter candidate, expanded the root plan,
  added the authority ledger, and recorded the FrankenEngine plan donor
  analysis.
- 2026-04-21: Stored the Grep Claude-in-a-Box article, amended the candidate
  charter and root plan to allow SDK boxes for branch execution, and recorded
  the `agent.py` substrate implications.

## Decision Log

- 2026-04-21: The root plan lives at repository root, not under `canon/`, so it
  is maximally visible during reimagining.
- 2026-04-21: Old NLSpecs are not deleted. They enter audit status.
- 2026-04-21: Root plan revision and scoped GitHub commits are part of
  `91.1`, not a separate perpetual chore.
- 2026-04-21: Grep-functional-copy work should start from an Alexandria-owned
  Agent SDK box harness with event/CAS custody, not from LangGraph as the core
  runtime and not from a raw Messages-only recreation of Claude Code behavior.

## Validation

Run during or after work:

- `bd ready --no-daemon`
- `bd dep tree alexandriacleanroom-91 --no-daemon`
- `make check` after documentation entrypoint changes
- `git status -sb --ignored` before any commit touching public GitHub

## Open Questions

- Does Context Pack 07 exist, or should the Principal waive it?
- What exact wording should mark the root plan as ratified?
- Which old NLSpec sections, if any, are retained binding material after audit?

## Completion Criteria

This plan can be moved to completed when:

- `alexandriacleanroom-91.1` through `91.6` are closed or superseded with clear
  replacements;
- the root plan's authority status is unambiguous;
- old NLSpec authority is no longer ambiguous;
- the Commission Restatement has been produced for Principal review;
- the next design-document work lane is recoverable from repo-local artifacts.
