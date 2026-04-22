# Codex-DR Grep Parity Contract

Status: active contract for `alexandriacleanroom-91.1.3`
Date: 2026-04-22
Workspace: `sandbox/codex-dr/`

## Purpose

This contract defines what the Codex-DR sandbox means by
Grep-system-and-performance parity pressure.

It does not claim parity. It defines the required behaviors, benchmark
obligations, proof artifacts, allowed claims, blocked claims, fake success
conditions, and the boundary between benchmark-facing sandbox proof and later
product service readiness.

## Authority Inputs

- `sandbox/codex-dr/AGENTS.md`
- `sandbox/codex-dr/docs/BOOTSTRAP_DOCTRINE.md`
- `sandbox/codex-dr/docs/ARCHITECT_HANDOFF.md`
- `sandbox/codex-dr/benchmark-manifests/benchmark_acquisition_audit.md`
- `../../PLAN_TO_CREATE_ALEXANDRIA.md`
- `../../docs/exec-plans/active/codex_dr_sandbox_architect_handoff.md`
- `../../docs/references/grep_building_grep_deep_research_2026_03_16.md`
- `../../docs/references/claude_in_a_box_grep_agents_sdk_2025_12_11.md`

## Evidence-First Gate

Gate decision:

- PROCEED for defining target behaviors and contract obligations.
- PROCEED for provider-off bootstrap implementation after harness contracts
  exist.
- PROVE FIRST for benchmark execution, provider-backed terminal-agent runs,
  SDK behavior claims, performance claims, leaderboard claims, and Grep parity
  claims.

Settled basis:

- The benchmark acquisition audit settles source/license/access metadata only
  for the checked public scope.
- No Alexandria run bundle currently settles system parity or performance
  parity.

## Parity Definition

Codex-DR parity has two layers:

1. System parity pressure.
   The sandbox must exercise the same class of recursive deep-research
   cognition described by the Grep donor material: planner-as-researcher,
   task graphing, branch execution, pointer-first file returns, inner-loop
   adequacy assessment, synthesis, reviewer/fact-checker pressure, re-entry,
   single-voice report writing, and custody over the resulting run.

2. Performance parity pressure.
   The sandbox must be able to run against public benchmark families in a
   reproducible, claim-bounded way: DRACO, DeepSearchQA, DeepResearch Bench,
   and any Parcha-published material that has acceptable access and use
   conditions. Performance parity is not available until benchmark cases,
   scorers, model/provider settings, run bundles, and allowed-claim outputs are
   all present and validated.

Parity is a proof target, not a default property of the harness.

## Required Cognitive Behaviors

The first full proof run must exercise every behavior below. A provider-off
bootstrap run may use deterministic fake artifacts, but it must preserve the
same file and event semantics.

| Behavior | Required contract | Evidence artifact |
| --- | --- | --- |
| Intent ratification | The planner records the user objective, assumptions, adequacy criteria, source policy, and known unknowns before tasking. | `plan.md`, `adequacy_criteria.json`, `events.jsonl` |
| Planner-as-researcher | For provider-backed runs, planning may gather context before freezing the plan. Provider-off bootstrap records the planned context-gathering slot without external calls. | `plan.md`, `events.jsonl`, future transcript artifacts |
| Expert shaping | The plan names selected skills, tools, allowed/disallowed capabilities, and branch role constraints. | `plan.md`, `terminal_agent_boxes.json` |
| Task graphing | Sequential and parallel work are represented as explicit tasks with dependencies. | `task_graph.json` |
| Branch spawning | Each branch has a scoped objective, tool/skill rights, workspace path, and expected return files. | `branches/<branch_id>/branch_manifest.json` |
| Pointer-first return | Branches return pointer, analysis, and evidence files; orchestrator reads pointer before deeper analysis. | `branches/<branch_id>/pointer.md`, `analysis.md`, `evidence.jsonl` |
| Inner-loop adequacy | The orchestrator compares branch returns against adequacy criteria and records deepen/continue/stop decisions. | `adequacy_assessments.jsonl`, `events.jsonl` |
| Recursive deepening | Thin or contradictory evidence can create follow-up branch tasks before reporting. | `reentry_tasks.jsonl` or `task_graph.json` updates |
| Synthesis | The orchestrator integrates evidence, contradictions, and unresolveds into a single research state. | `synthesis.md`, `contradictions.json` |
| Single-voice report writing | The final report is generated from reconciled synthesis state, not stitched branch prose. | `report.md`, `report_outline.md` |
| Review and fact-checking | Reviewers write findings to files with severity, evidence basis, and required action. | `reviews/<review_id>.json` |
| Reviewer-driven re-entry | A qualifying reviewer finding compiles into a new research task or an explicit no-reentry decision. | `reentry_decisions.jsonl`, `task_graph.json` |
| Claim custody | Every material report claim links to sources and intermediate work. | `claim_ledger.json` |
| Compaction custody | Any compaction records inputs, outputs, scope, and claim impact. | `compactions/<compaction_id>.json` |
| Benchmark placeholder/scoring | Provider-off bootstrap emits a placeholder; benchmark runs emit real score manifests only after gates pass. | `benchmark_score.json` |
| Allowed claims | The run ends by narrowing what may be claimed from the actual evidence. | `allowed_claims.json` |

## Benchmark Obligations

The acquisition audit is binding for benchmark scope.

| Benchmark family | Acquisition status | Execution gate | Claim boundary |
| --- | --- | --- | --- |
| DRACO | Public HF dataset metadata, MIT, 100 rows, rubric axes known. | Requires provider-off bootstrap pass, case manifest, scorer manifest, run-control receipt, judge configuration, and run bundle. | No Alexandria DRACO score until executed and validated. |
| DeepSearchQA | Public HF metadata, Apache-2.0, 900 rows; 896-case Grep/Parcha subset evidence-pending. | Requires scorer prompt/code provenance, `gemini-2.5-flash` or declared replacement, case/subset rule, run-control receipt, and run bundle. | No pass@1, FC, F1, or Grep comparison until executed and validated. |
| DeepResearch Bench | Public repo/HF surfaces, Apache-2.0, 100 tasks, RACE/FACT shape. | Requires official scripts, provider keys, raw generated report handling policy, scorer manifest, repeated-run policy, run-control receipt, and run bundle. | No RACE/FACT or leaderboard claim until executed and validated; current rank must be checked at claim time. |
| Parcha-published material | Public external score/result repo, no explicit license observed. | Requires license/permission decision before reuse of artifacts; may be cited as external target pressure only. | Public Grep/Parcha claims are donor evidence, not Alexandria proof. |

Benchmark execution is blocked until:

1. `alexandriacleanroom-91.1.4.1` provider-off bootstrap passes.
2. Harness contracts are implemented enough to emit required custody artifacts.
3. A case manifest exists for selected benchmark cases.
4. A scorer manifest exists for the benchmark family.
5. A run-control receipt exists and is approved for the specific run.
6. Raw private, paid, or large benchmark data remains outside git.

## Required Proof Artifacts

Every full proof run must emit a run bundle with at least:

```text
run_manifest.json
events.jsonl
artefact_manifest.json
plan.md
adequacy_criteria.json
task_graph.json
terminal_agent_boxes.json
branches/
evidence/
adequacy_assessments.jsonl
synthesis.md
contradictions.json
report_outline.md
reviews/
reentry_decisions.jsonl
claim_ledger.json
compactions/
report.md
benchmark_score.json
allowed_claims.json
validation_report.json
```

Provider-backed runs additionally require:

```text
run_control_receipt.yaml
transcripts/
scorer_manifest.json
case_manifest.json
provider_metadata.json
```

The provider-off bootstrap may replace provider artifacts with explicit
placeholders that validate as placeholders and do not widen claims.

## Allowed Claims

Before any run:

- The sandbox has target-calibration and contract artifacts only.
- The sandbox is not benchmark-executed and not parity-proven.

After provider-off bootstrap passes:

- The sandbox can create and validate a deterministic local fixture run bundle.
- The sandbox can enforce custody, causal linkage, review re-entry,
  compaction, benchmark-placeholder, claim-ledger, and allowed-claims gates for
  provider-off fixtures.
- The sandbox still has no provider-backed or benchmark score claim.

After a provider-backed non-benchmark proof run passes with run-control receipt:

- The sandbox may claim the specific behaviors demonstrated by that run bundle.
- Benchmark and Grep-performance claims remain blocked.

After benchmark execution passes:

- The sandbox may claim only the specific benchmark family, case set, scorer
  configuration, date, and run bundle that passed validation.
- Grep parity may be claimed only if the parity contract's system behaviors and
  performance comparators are both satisfied by evidence, and the
  allowed-claims file says so.

## Blocked Claims

The following claims remain blocked unless a future proof artifact explicitly
unblocks them:

- Codex-DR has achieved Grep parity.
- Codex-DR has reproduced any Grep/Parcha public score.
- Codex-DR has a stable leaderboard rank.
- Codex-DR benchmark execution is authorized without provider-off bootstrap.
- A tidy report proves recursive research cognition.
- A run-control receipt alone authorizes benchmark execution.
- Terminal-agent transcript capture alone is sufficient custody.
- Sandbox success proves product service readiness.
- Public Grep/Parcha benchmark artifacts may be reused in git despite missing
  or evidence-pending license/permission.

## Fake Success

Fake success is any result that looks like progress while avoiding the actual
parity target:

- a local fixture that writes files but has no causal event chain
- branch outputs that are prose without pointer/analysis/evidence separation
- reviewer comments that do not compile into re-entry decisions
- a report that contains claims not present in `claim_ledger.json`
- a benchmark score without case, scorer, and run-control manifests
- a run that cannot be reconstructed from bundle artifacts
- a claim boundary that widens because the result sounds impressive
- a sandbox run presented as product runtime readiness

## Sandbox Parity Proof Vs Product Service Readiness

Sandbox parity proof concerns the research engine:

- recursive planning and branch work
- event and artefact custody
- review-driven re-entry
- claim ledger and allowed-claims output
- benchmark-facing reproducibility

Product service readiness is a separate lane and requires at least:

- API boundaries and client-facing contracts
- tenant isolation and access control
- secrets and provider-billing policy
- job queues, durable workers, retries, and cancellation
- customer data policy and audit export
- UI/report delivery surfaces
- operations, observability, deployment, and support posture

A sandbox proof may inform the service runtime. It does not become the product
runtime by assertion.

## Harness Contract Obligations

The next harness-contract bead must specify file formats and validators for:

- CLI commands
- run bundle
- event envelope and event types
- artefact manifest and content-addressing
- terminal-agent box config
- branch return files
- adequacy assessment
- review files
- re-entry decisions
- compaction receipts
- claim ledger
- benchmark score
- allowed claims
- validation report
- failure modes

The implementation bead may not invent missing semantics. If a format is
unclear, the harness contract must be amended before code relies on it.

## Contract Report

Upstream interfaces satisfied:

- Bootstrap doctrine: preserves provider-off first boot and live-run control.
- Benchmark acquisition audit: imports benchmark access/licensing/evaluator
  boundaries without widening claims.
- Root plan: keeps recursive research cognition as the telos and custody as
  native machinery.
- ExecPlan: supplies the parity contract required before harness contracts.

Downstream obligations created:

- `alexandriacleanroom-91.1.4` must specify concrete schemas and validators
  for every proof artifact named here.
- `alexandriacleanroom-91.1.4.1` must implement provider-off bootstrap against
  those schemas before any provider-backed or benchmark run.
- Future benchmark beads must carry case, scorer, run-control, custody, score, and
  allowed-claim manifests.

Round-trip contracts:

- Branches send pointer/analysis/evidence files; the orchestrator validates
  all three and records adequacy decisions.
- Reviewers send findings; the re-entry compiler returns research tasks or
  explicit no-reentry decisions.
- Reports send claims; the claim ledger and allowed-claims validator return
  pass/fail on custody and claim scope.

Policy defaults:

- Missing required artifact: fail closed.
- Missing causal event linkage: fail closed.
- Missing review re-entry for qualifying findings: fail closed.
- Missing compaction receipt: fail closed.
- Benchmark placeholder presented as score: fail closed.
- Claim wider than evidence: fail closed.

Remaining contradictions:

- Exact Grep/Parcha private setup remains evidence-pending. Governing rule:
  public benchmarks can calibrate targets, but only Alexandria-owned run
  bundles can authorize Alexandria claims.
