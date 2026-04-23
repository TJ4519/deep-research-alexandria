# DR Mesh Parity Gap Audit

Status: active forensic audit
Date: 2026-04-23
Scope: Codex-DR sandbox against the Grep topology figures

## Completion Object

This audit answers whether the Codex-DR sandbox currently implements the Grep
deep-research topology shown in the three Principal-provided figures, whether
real benchmarks are available, what prompts exist, what is missing, and what
must be built next.

## Intended Object

The intended object is the DR mesh: a Codex-based recursive deep-research
system that can run a planner, create a task graph, execute scoped branch
agents, read pointer files before selected analysis spans, synthesize evidence,
apply reviewer backpressure, re-enter research, write a final report, score
benchmark outputs, and feed evaluation results into an improvement loop.

## Current Finding

The current sandbox is functional as a provider-off deterministic topology
harness. It is not functional parity with Grep.

It can generate a mesh-shaped run bundle with planner, task graph, branch
returns, pointer-first receipts, synthesis, review, re-entry, report, claim
ledger, allowed claims, events, artifact custody, and a benchmark placeholder.

It cannot yet run reusable live multi-agent Codex CLI boxes through that mesh.
It cannot yet score DRACO or another deep-research benchmark. It cannot yet
use evaluation failure to improve prompts, skills, role configs, or regression
fixtures.

## Diagram 1: Two-Layer Loop

Implemented provider-off:

- inputs, case manifest, plan file, skills/tools, task graph;
- deep-search, data-analysis, verification branch roles;
- evaluate and synthesize step;
- reviewer step;
- reviewer-triggered re-entry;
- writer report;
- final allowed-claims boundary.

Missing or blocked:

- live planner that gathers context and clarifies the task with a model;
- live Codex CLI branch boxes launched from the task graph;
- dynamic recursive branch spawning beyond a fixed provider-off re-entry path;
- benchmark-backed approval of a final report;
- reusable outer loop that can iterate until a reviewer approves.

## Diagram 2: Task Dependency Graph

Implemented provider-off:

- task ids, dependency edges, expected outputs, role config ids, and assigned
  box ids;
- independent branch tasks and dependent synthesis;
- re-entry task compiled from review finding;
- validators for missing dependencies and missing expected outputs.

Missing or blocked:

- live scheduler that can execute independent Codex boxes and then resume
  dependent tasks;
- live process supervision, transcript capture, retries policy, and kill path;
- task revision against a specific failed branch in a live run;
- benchmark or evaluator signal feeding back into the task graph.

## Diagram 3: File-Based Context Economy

Implemented provider-off:

- branch `pointer.md`, `analysis.md`, and `evidence.jsonl`;
- pointer-first read receipts;
- selected analysis spans represented in custody receipts;
- evidence admission and claim ledger boundaries.

Missing or blocked:

- a live context-window manager that actually reads only selected spans during
  model execution;
- live branch agents writing file returns under their own Codex workspaces;
- robust line-range or section-range addressing over long analysis files;
- evaluator-driven evidence re-entry after a failed benchmark or review score.

## Benchmark Reality

Real benchmarks exist.

- DRACO is public on Hugging Face as `perplexity-ai/draco`, with 100 test rows,
  task-specific rubrics, and a documented weighted scoring method.
- DeepSearchQA is public as a 900-prompt benchmark for multi-step search tasks.
- DeepResearch Bench is public, with 100 PhD-level tasks and RACE/FACT
  evaluation code and data surfaces.
- Parcha/Grep have published benchmark result material, including
  DeepResearch Bench artifacts, but those external claims are target
  calibration for Alexandria, not Alexandria evidence.

Local Alexandria benchmark state:

- `sandbox/codex-dr/benchmark-manifests/draco_tiny_smoke_case_manifest.md`
  records a DRACO row-0 pointer.
- `sandbox/codex-dr/benchmark-manifests/benchmark_acquisition_audit.md`
  records benchmark access and claim boundaries.
- `benchmark_score.json` remains `score: null` and `claims_enabled: false`.
- No scorer manifest, judge prompt, judge model policy, rubric mapping,
  sealed-reference policy, variance policy, scorer transcript, or score
  validator exists yet.

## Prompt Reality

Prompt-like surfaces exist, but they are not yet a full live role-prompt pack.

Current surfaces:

- the historical monolithic smoke prompt under
  `sandbox/codex-dr/runs/draco_smoke_001/prompts/`;
- deterministic provider-off templates embedded in
  `sandbox/codex-dr/tools/alexandria_dr.py`;
- dry-run live adapter prompts generated under `live_adapter/prompts/`;
- role objectives and return contracts in `role_configs.json`.

Missing:

- hardened planner prompt;
- branch prompts for deep search, data analysis, verification, and re-entry;
- orchestrator/evaluate/synthesize prompt;
- reviewer/fact-check prompt;
- writer prompt;
- scorer/judge prompt;
- role-specific source policy, citation discipline, pointer-first output law,
  and benchmark-rubric awareness.

## Root Cause

The previous trajectory favored safe, buildable support surfaces under a
no-launch halt: provider-off fixtures, manifests, validators, launch-control
receipts, dry-run command plans, and claim gates.

Those surfaces are useful because they prevent false claims and make custody
inspectable. They also created a false sense of completion because the bundle
looked like the Grep topology while no reusable live multi-agent mesh had run
and no benchmark scorer existed.

The strongest artifact-grounded cause is this: the executable command surface
currently stops at provider-off simulation and dry-run launch planning. The
commands that would perform provider-backed work still fail closed. The scorer
is a placeholder. The self-improvement loop is absent.

## Evidence-First Gate State

- Provider-off topology: PROCEED. It is locally validated.
- Live Codex multi-agent mesh: PROVE FIRST. No reusable live execution exists.
- DRACO benchmark scoring: PROVE FIRST. Dataset exists; scorer path does not.
- Grep parity: PROVE FIRST. No Alexandria benchmark score exists.
- Self-improvement loop: PROVE FIRST. No evaluator-to-improvement path exists.

## Next Build Queue

1. Build no-launch live mesh executor contract.
2. Harden live role prompt pack.
3. Add DRACO scorer manifest and local schema.
4. Add benchmark evaluation ledger and claim gate.
5. Add provider-off self-improvement replay loop.
6. Open the authorized live mesh smoke run only after the Principal approves a
   named run-control receipt.

## Non-Claims

This audit does not claim:

- Grep parity;
- DRACO score;
- benchmark execution;
- reusable live multi-agent execution;
- product readiness;
- service-runtime maturity.
