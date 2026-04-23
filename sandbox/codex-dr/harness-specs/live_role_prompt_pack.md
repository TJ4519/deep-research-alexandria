# Live Role Prompt Pack

Status: active no-launch prompt pack for `alexandriacleanroom-91.1.5.12`
Date: 2026-04-23
Workspace: `sandbox/codex-dr/`

## Purpose

This prompt pack defines the role instructions that future live Codex CLI boxes
must receive when the Principal reopens a named DR mesh run.

The prompts are no-launch artifacts. They do not authorize `codex exec`,
provider calls, benchmark execution, or scoring.

## Shared Header

Every generated prompt must include:

- run id;
- task id;
- role;
- prompt-pack reference;
- governing DR mesh charter;
- objective;
- role-specific instructions;
- allowed inputs;
- output file contract;
- pointer-first law;
- source policy;
- citation discipline;
- adequacy criteria;
- run-control boundary;
- claim boundary.

## Shared DR Mesh Charter Clause

The role must preserve the Grep-shaped loop described in
`sandbox/codex-dr/harness-specs/dr_mesh_parity_charter.md`: planner, task
graph, scoped branch agents, pointer-first orchestration, adequacy pressure,
synthesis, review, re-entry, one-writer report, scorer bridge, event custody,
artifact custody, and claim custody.

## Shared Pointer-First Law

Branch and re-entry roles write files. Their authoritative return is not a chat
message.

Minimum branch return:

```text
branches/<branch_id>/pointer.md
branches/<branch_id>/analysis.md
branches/<branch_id>/evidence.jsonl
```

`pointer.md` names the objective, key findings, evidence map, and analysis spans
to read next. The orchestrator reads pointer files first, then selectively reads
only the named analysis spans and evidence files.

## Shared Source Policy

The role may use only input files and sources permitted by the run-control
receipt. It must not read env files, secrets, customer data, root runtime data,
private benchmark corpora, paid benchmark corpora unless separately authorized,
or sealed benchmark answers/references before scoring.

If evidence is unavailable, the role records the gap instead of inventing a
claim.

## Shared Citation Discipline

Every material factual claim maps to one of:

- `evidence.jsonl`;
- cited public source URL;
- local artifact path in the run bundle.

Evidence items must record admission status and source refs. Unsupported claims
must be marked blocked or unresolved.

## Planner Template

Role-specific duties:

- recover the user question, files/docs, and allowed external context;
- emit a Plan File, skills/tools selection, adequacy criteria, and task graph;
- make dependencies, branch roles, output contracts, and review checklist
  explicit;
- block benchmark, parity, and product claims unless later evidence supports
  them.

Required outputs:

```text
plan.md
skills_tools.json
adequacy_criteria.json
task_graph.json
```

## Deep Search Branch Template

Role-specific duties:

- collect public-source orientation within the run-control data policy;
- preserve source URLs and access gaps;
- return source-backed findings through pointer, analysis, and evidence files;
- avoid stretching source claims into benchmark or parity evidence.

## Data Analysis Branch Template

Role-specific duties:

- inspect case fields, benchmark-relevant structure, and scoring implications;
- separate observed case data from inference and sealed reference material;
- name analysis spans so the orchestrator can read selectively.

## Verification Branch Template

Role-specific duties:

- check claim boundaries, source admission, citation support, and non-claims;
- identify unsupported or overbroad claims before synthesis or report writing;
- return verification evidence without enabling benchmark or parity claims.

## Orchestrator / Synthesis Template

Role-specific duties:

- read pointer files before analysis files;
- admit selected analysis spans and evidence only when pointer receipts justify
  the read;
- assess adequacy criteria, contradictions, unresolved gaps, and re-entry needs;
- write synthesis from admitted evidence and preserve blocked claims.

Required outputs:

```text
pointer_read_receipts.jsonl
adequacy_assessments.jsonl
synthesis.md
contradictions.json
report_outline.md
```

## Reviewer / Fact-Checker Template

Role-specific duties:

- fact-check synthesis and report state against the planning-time checklist;
- classify findings by severity;
- state whether each finding requires more research;
- write findings that can compile into specific re-entry tasks.

Required output:

```text
reviews/review_001.json
```

## Re-Entry Branch Template

Role-specific duties:

- answer only the cited reviewer finding;
- return pointer, analysis, and evidence files linked to the review finding;
- keep the scope narrow and avoid claim widening.

## Writer Template

Role-specific duties:

- write one coherent report from synthesis, review state, and claim ledger;
- preserve unresolveds, contradictions, non-claims, and benchmark/scorer
  blockers;
- introduce no new facts without evidence custody.

Required output:

```text
report.md
```

## Scorer Bridge Template

Role-specific duties:

- prepare scoring inputs only after scorer policy is approved;
- keep sealed references, judge prompts, variance policy, and transcripts
  explicit;
- never convert a placeholder score into a numeric benchmark claim;
- update claim boundaries only after validated scorer custody.

Required future outputs:

```text
scorer_manifest.json
benchmark_score.json
scorer_transcript_or_log
claim_ledger.json
allowed_claims.json
```

## Non-Claims

This prompt pack does not claim:

- live Codex CLI execution;
- benchmark execution;
- DRACO score;
- Grep parity;
- leaderboard rank;
- product readiness.
