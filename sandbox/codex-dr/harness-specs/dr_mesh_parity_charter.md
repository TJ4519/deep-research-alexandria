# Codex-DR DR Mesh Parity Charter

Status: active parity charter
Date: 2026-04-22
Owner: Principal / Bohr / Codex-DR sandbox architect-builder

## Purpose

This charter names the real build object for Bohr.

The build object is the DR mesh: a Grep-style recursive deep-research agent
system validated through Codex CLI terminal-agent harnessing.

The DR mesh uses Codex CLI boxes because the Principal already subscribes to
Codex and wants to validate the Grep-style agent system without beginning from
SDK or API-per-request product runtime assumptions.

## Governing Sources

- `docs/references/grep_building_grep_deep_research_2026_03_16.md`
- `sandbox/codex-dr/harness-specs/grep_parity_contract.md`
- `sandbox/codex-dr/harness-specs/harness_contracts.md`
- `sandbox/codex-dr/docs/codex_mesh_launch_control_2026_04_22.md`
- Principal-provided Grep topology figures from 2026-04-22:
  - `/Users/singh/Desktop/Screenshot 2026-04-22 at 10.55.20.png`
  - `/Users/singh/Desktop/Screenshot 2026-04-22 at 10.56.39.png`
  - `/Users/singh/Desktop/Screenshot 2026-04-22 at 10.57.13.png`

## Telos

Build and validate a Codex-based DR mesh that performs agentic deep research in
the Grep shape:

1. Take a user question, files/docs, and external context.
2. Run a planner that researches, clarifies, and shapes the expert.
3. Emit a Plan File, selected skills/tools, and a task graph.
4. Execute scoped branch agents as Codex CLI boxes.
5. Have branch agents write pointer, analysis, and evidence files.
6. Have the orchestrator read pointers first, then selected analysis spans.
7. Evaluate and synthesize branch returns against adequacy criteria.
8. Spawn more branch tasks when gaps, contradictions, thin evidence, or reviewer
   findings demand more work.
9. Write the report through one coherent writer pass after synthesis.
10. Run reviewers and fact-checkers against the planning-time checklist.
11. Route failed reviews back into research, synthesis, and rewriting.
12. Produce a final report only when the DR mesh records that the adequacy bar
    is satisfied.

The filesystem is the working memory layer for this system. The event log,
artefact manifest, compaction receipts, claim ledger, and allowed-claims output
make the run inspectable and governable. They serve the DR mesh.

## Figure 1: Two-Layered Loop Architecture

The first figure shows the full Grep loop.

Inputs are files/docs, the user question, and external context. The planner
explores, clarifies, and shapes the expert. Planning emits three execution
surfaces: Plan File, Skills/Tools, and Task Graph.

Execution enters the inner loop. Sub-Agent A performs deep search, Sub-Agent B
performs data analysis, and Sub-Agent C performs verification. These are
example roles, not fixed role names. The required pattern is scoped branch work
with role-specific objectives and rights.

The orchestrator evaluates and synthesizes branch outputs. If coverage,
evidence quality, source support, or contradiction handling is inadequate, it
spawns more sub-agents or deepens existing lines. When the inner loop is
satisfied, a report writer creates the report from the synthesized research
state.

The outer loop then runs reviewers. Reviewers fact-check, validate, and score
the report against the planning-time checklist. If the review needs more
research, the system returns to the research loop. If the review approves, the
system emits the final report.

Build implication for Bohr: implement the state machine, run bundle, and Codex
CLI role adapters that can perform this loop. A single smoke transcript is only
evidence for one run. The deliverable is a reusable DR mesh harness.

## Figure 2: Inner Loop And Task Dependency Graph

The second figure shows how the Plan File becomes concrete work.

The Plan File creates a task dependency graph. Tasks A, B, and C can run in
parallel when their work is independent. Task D depends on A and B and performs
synthesis over those branch results. Source verification can remain a separate
task that feeds review and revision.

The inner loop contains an Evaluate & Synthesize step. That step checks gaps and
decides whether to spawn more tasks. The blue return path means the mesh can add
more tasks before report writing. The red return path means review and
fact-checking can demand revision of a specific task or branch.

Build implication for Bohr: implement task graph semantics. Tasks need IDs,
dependencies, role configuration, input files, expected return files, status,
adequacy checks, and re-entry links. The system must be able to create new tasks
after evaluating evidence, then run those tasks and update synthesis.

## Figure 3: File-Based Context Economy

The third figure shows the required memory economy.

A sub-agent writes files into the filesystem. The minimum return shape is:

- `pointer.md`: summary and section pointers.
- `analysis.md`: full branch analysis.
- `evidence.md` or `evidence.jsonl`: sources, citations, raw notes, and data.

The main researcher reads `pointer.md` first. The pointer tells it which sections
or line ranges matter. The orchestrator then reads only selected spans from the
long analysis and leaves unrelated material outside active context.

Build implication for Bohr: branch agents must return files, not long chat
payloads. The orchestrator must support pointer-first reading, selective span
reads, evidence admission, and synthesis over admitted material. This is the
context economy that makes recursive research practical under Codex CLI.

## Non-Negotiable Build Requirements

- `alexandria-dr` must expose a visible command surface for the DR mesh.
- The planner must produce Plan File, skills/tools selection, task graph,
  adequacy criteria, and review checklist.
- The orchestrator must launch or simulate role-scoped Codex CLI boxes through
  an adapter boundary.
- Branch agents must write pointer / analysis / evidence returns.
- The orchestrator must read pointer files before selective analysis spans.
- The inner loop must evaluate gaps and spawn more branch tasks.
- Synthesis must reconcile evidence, contradictions, unresolveds, and admitted
  claims.
- The writer must generate the report from the synthesized research state.
- Reviewers must write review files with fact-checking, validation, score or
  rubric results, severity, and required action.
- Reviewer findings must compile into re-entry tasks when more research is
  required.
- Benchmark-facing runs must carry case manifests, scorer manifests, run-control
  receipts, transcripts, event logs, artefact manifests, claim ledgers, and
  allowed-claims outputs.

## Invalid Success Conditions

Bohr must not count these as completion:

- documentation that restates the loop without building the control surface;
- provider-off fixture generation with no reusable role adapter;
- a report file without task graph, branch returns, synthesis, review, and
  re-entry evidence;
- branch outputs that lack pointer / analysis / evidence separation;
- review comments that cannot create new research tasks;
- benchmark discussion without an executable case and scorer path;
- launch-control work that delays the DR mesh harness;
- service-runtime design that bypasses Codex CLI mesh validation.

## Immediate Build Center

The next build center is:

1. DR mesh state model.
2. `alexandria-dr` CLI commands for planner, task graph, branch execution,
   synthesis, review, re-entry, writer, validation, and scoring.
3. Provider-off fake role adapters that preserve the exact DR mesh topology.
4. Codex CLI live role adapter behind run-control receipts.
5. Tiny benchmark-facing case lane with DRACO first unless a stronger empirical
   reason appears.
6. Scorer bridge with explicit scorer manifest and custody.

The governing question for every Bohr decision is: does this make the Grep loop
in the three figures executable and inspectable through Codex CLI boxes?
