# Claude-In-A-Box Implications For Alexandria `agent.py`

Status: active substrate amendment memo
Date: 2026-04-21
Authority class: `LOCAL_TRANSLATION`
Primary donor: `docs/references/claude_in_a_box_grep_agents_sdk_2025_12_11.md`

## Why This Memo Exists

The Grep Claude-in-a-Box article changes the `agent.py` question. The strongest
functional-copy path is now an Alexandria-owned harness around Claude Agent SDK
boxes, because Grep's implementation evidence points to isolated workspaces,
selective skill loading, scoped MCP tool access, fork/resume sessions, queued
worker execution, and a researcher-to-reporter handoff.

The prior Messages-only / no-SDK clause was defensible when Grep was being read
only as topology and file-memory evidence. It is no longer the best default once
the implementation substrate is visible. The corrected question is where
Alexandria must own authority and custody while still using SDK boxes for the
research branches that need Grep-like behavior.

## Core Finding

For a functional Grep copy, the best substrate is:

- Claude Agent SDK boxes for isolated branch execution.
- Alexandria-owned orchestration for planning authority, task graph decisions,
  branch lifecycle, reconciliation, review re-entry, and final synthesis.
- Alexandria-owned event and content-addressed custody over every observable
  runner input, decision, transcript, file artefact, review, and report claim.

This preserves the point of the charter. The SDK box gives each research agent
the computer, selected skills, MCP tools, and context isolation it needs. The
Alexandria layer prevents the system from collapsing into an opaque SDK wrapper.

## Decision Pressure

### Option A: Raw Messages API Custom Loop

This gives maximum control over event emission, model calls, and replay. It also
requires Alexandria to recreate the practical behavior that Claude Code already
provides: filesystem search, skill loading, tool approval, subagents, session
compaction, workspace-local context, and fork/resume ergonomics.

Assessment: good for bounded model roles and custody-sensitive review passes,
weak as the first route to functional Grep parity.

### Option B: Claude Agent SDK Box Harness

This matches the donor implementation shape most closely. It supports selected
skills, `cwd`, allowed and disallowed tools, MCP servers, system prompts,
subagents, and session-oriented execution. The official Claude Agent SDK
materials also frame the loop as gathering context, taking action, verifying
work, and repeating.

Assessment: best default for Grep-parity branch execution, provided Alexandria
owns the outer orchestrator, event mirror, content-addressed store, decision
tool, and claim ledger.

### Option C: LangGraph Core Runtime

LangGraph can represent explicit graphs, retries, state transitions, and
workflow inspection. It does not naturally provide Claude Code's filesystem
workbench, skill system, MCP box ergonomics, or session fork/resume semantics.

Assessment: useful later for visualization or optional workflow composition,
poor default as Alexandria's core state-machine runtime.

### Option D: Celery Or Temporal Around Boxes

Grep uses queued worker execution around boxes. This is infrastructure, not the
research brain. Alexandria can use a queue later to scale branch runs after the
local harness is correct.

Assessment: valuable after the single-machine harness proves the branch,
custody, and replay contracts.

## `agent.py` Target Shape

`agent.py` should become a thin CLI/API entrypoint into an `AgentHarnessRunner`.
It should not contain improvised research policy.

The runner should:

- accept an `AgentHarnessConfig`;
- create an isolated workspace;
- copy only the selected skills;
- configure allowed tools, disallowed tools, and MCP servers;
- run the planner or branch agent with the chosen model and prompt;
- persist the SDK transcript or session file as an immutable artefact;
- mirror observable runner events into Alexandria's append-only event log;
- content-address pointer, analysis, evidence, review, section, and report
  files;
- support fork and resume from explicit session lineage;
- return a pointer-first output contract to the orchestrator.

## Required Design Surfaces Before Code

The Design Document must specify:

- `AgentHarnessConfig` type stub and validation rules.
- Workspace lifecycle and cleanup rules.
- Skill selection and copying rules.
- Tool and MCP allowlist/denylist semantics.
- Session persistence, fork, resume, and lineage conventions.
- Transcript-to-event mirroring rules.
- Transcript-to-CAS storage rules.
- Planner ratification contract.
- Branch pointer / analysis / evidence return format.
- Reconciliation object format.
- Writer and reporter handoff contract.
- Reviewer finding and research re-entry contract.
- Security posture for external MCP tools and filesystem access.

## Bead Implications

The next bead stack should begin with specification beads, not runtime edits:

1. Amend and ratify the substrate clause in the candidate charter.
2. Specify `AgentHarnessConfig`.
3. Specify isolated workspace lifecycle.
4. Specify skill loader behavior.
5. Specify tool/MCP permission policy.
6. Specify session fork/resume persistence.
7. Specify SDK transcript custody.
8. Specify event mirroring.
9. Specify content-addressed artefact admission.
10. Specify planner ratification.
11. Specify branch orchestration and return contract.
12. Specify reconciliation and synthesis loops.
13. Specify reporter handoff.
14. Specify security and eval gates.

Only after those beads pass should `agent.py` be rewritten.

## Non-Claims

This memo does not ratify the candidate charter.

This memo does not claim Alexandria has Grep parity.

This memo does not make the Claude Agent SDK the whole architecture.

This memo says the SDK box harness is the best branch-execution substrate now
visible for a functional Grep copy, and that Alexandria should wrap it with its
own authority, custody, replay, reconciliation, and synthesis machinery.
