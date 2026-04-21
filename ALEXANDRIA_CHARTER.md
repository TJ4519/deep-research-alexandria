# ALEXANDRIA CHARTER

Version: 2.0-candidate
Date: 2026-04-21
Author: TJ Singh, Principal Architect and Governor
Status: CANDIDATE FOR PRINCIPAL RATIFICATION
Reads before: `PLAN_TO_CREATE_ALEXANDRIA.md`

## Purpose

This Charter states the governing commitments for the reimagined Alexandria
architecture. Its job is to preserve Alexandria's real point before design
documents, beads, or implementation work harden around a narrower model.

After Principal ratification, this Charter supersedes the prior Charter v1.0
where they conflict. Until then, it is the active draft for the reimagining lane
and the prior Charter remains lineage canon.

## Telos

Alexandria is a recursive deep-research agent system for high-stakes
intelligence work.

Its defining commitment is coordinated research cognition: planner-shaped
decomposition, tool-mediated context gathering, orchestrator-managed recursion,
file-returning sub-agents, evidence retrieval, contradiction reconciliation,
reviewer pressure, research re-entry, and single-voice synthesis.

The filesystem is the working memory of the system whilst research is
happening. The append-only event log is the causal trace of orchestration.
Content-addressed artefacts are the custody objects that make claims,
decisions, and session state durable. These substrates serve the recursive
research system.

## Commercial Wedge

Alexandria's first product is deep-research reports for pharma competitive
intelligence with claim-to-source chain-of-custody as the differentiated
surface.

Buyer tiers, in pursuit order:

1. Specialist pharma CI consultancies.
2. Mid-market biotech competitive-intelligence teams.
3. Big-pharma enterprise after reference-customer accumulation.

Alexandria competes with the analyst layer. It does not compete as a
proprietary pharma data vendor.

## Binding Architectural Invariants

1. Recursive research cognition is the engine. Planning, delegation, evidence
   retrieval, synthesis, review, and re-entry are first-class runtime behavior.
2. Planner-as-researcher. The planner gathers context through tools before it
   emits the Plan File.
3. Inner and outer loops are separate. The inner loop runs research recursion
   until adequacy criteria are met. The outer loop runs report writing,
   review, fact-checking, and potential re-entry.
4. Task graphs express parallel and sequential reasoning. Topology is a product
   of research decomposition, prompt discipline, and orchestration.
5. Sub-agents return through files. Each branch returns a pointer / analysis /
   evidence triplet, and the orchestrator reads the pointer first.
6. Markdown artefacts are working-memory objects. Plan files, task files,
   evidence files, analysis files, contradiction files, reviews, sections, and
   reports are live research state.
7. Contradiction reconciliation is first-class. Conflicting evidence is
   represented, adjudicated where possible, left unresolved where necessary,
   and treated explicitly in the report.
8. One writer owns report voice and cohesion from table of contents through
   thesis scaffold and section expansion.
9. Reviewer findings are research-control inputs. A review can send the system
   back to the inner loop.
10. Event completeness. Every orchestrator I/O hop produces exactly one event
    in the append-only log. No hop is unlogged.
11. Artefact immutability. Every plan, analysis, pointer, evidence file,
    review, report section, and report artefact is content-addressed and
    immutable once written.
12. Decision capture via tool call. Spawn, terminate, re-plan, deepen, and ship
    decisions are emitted through mandatory tool calls carrying prose rationale.
13. Session reconstructibility. The filesystem and event log, together and
    alone, are sufficient to reconstruct any completed session. Runtime state
    and model-provider state are not required.
14. Runtime substrate. Alexandria owns orchestration, custody, decision
    capture, event emission, content addressing, reconciliation, review
    re-entry, and ship decisions. Research branches may run inside Claude
    Agent SDK box harnesses when that is the shortest path to Grep-class
    filesystem skills, MCP tools, isolated contexts, sub-agents, and
    fork/resume behavior. Raw Anthropic Messages API and GPT calls remain
    available behind the provider-agnostic model client for bounded drafting,
    review, synthesis, adversarial pressure, and verification roles.
    LangGraph does not own Alexandria's core state-machine runtime.
15. Provider-agnostic model client. Claude and GPT may serve different roles
    for drafting, review, synthesis, adversarial pressure, and verification.

## Grep Donor Interpretation

Grep is a donor proof-of-concept for recursive deep-research cognition.

Alexandria must preserve the relevant Grep shape: planner-as-researcher,
inner/outer loop separation, file-returning sub-agents, markdown working
memory, single-voice writing, reviewer-driven iteration, and orchestration
loops over adequacy.

Grep's Claude-in-a-Box implementation evidence is relevant donor material for
execution substrate: isolated agent workspaces, selective skill loading,
MCP-scoped tool surfaces, fork/resume sessions, queued worker execution, and
research-to-report handoff are admissible patterns for Alexandria to study and
adopt where they preserve this Charter.

Grep parity is a checkpoint. Alexandria must exceed it through custody, replay,
content-addressed artefacts, decision capture, claim-to-source chain-of-custody,
and pharma CI domain seriousness.

## Non-Goals

1. Alexandria is not a database product. Proprietary pharma data curation
   belongs to incumbents such as Cortellis, Trialtrove, and Evaluate Pharma.
2. Alexandria v1 does not promise cross-session recursive improvement, live
   steering, skill distillation, or meta-research as product features.
3. Alexandria is not a general framework, platform, or developer tool.
4. Alexandria is not a prompt-only report generator.
5. Alexandria is not a filesystem context-economy demo.
6. Alexandria is not a continuation of old numbered NLSpecs by inertia.

## Design Document Quality Bar

The Alexandria Design Document must be specified at a granularity where each
atomic work bead, when handed to a coding agent with no prior Alexandria chat
context, requires no architectural re-derivation to implement correctly.

A bead that forces the coding agent to reinvent an interface, schema,
control-flow shape, file format, authority rule, or proof obligation is
out-of-spec for the Design Document.

## Authority Rule

After ratification, this Charter governs the reimagining. Lower-order design
docs, Linear mirrors, old NLSpecs, code, proof receipts, and chat history may
translate, constrain, or supply evidence. They may not silently narrow this
Charter.

Any conflict between this Charter and older imported NLSpecs must be resolved
through an explicit audit and supersession note before implementation work
depends on the conflicted clause.

## Ratification Test

The Charter is ready for ratification only if the Principal agrees that it
preserves the real point:

Alexandria is a recursive deep-research runtime that reaches and exceeds
Grep-class research coordination, using filesystem working memory, event
logging, content-addressed artefacts, and claim custody as machinery for that
larger system.

*End of Charter.*
