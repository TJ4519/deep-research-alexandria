# Codex-DR Sandbox Architect Handoff

Status: active handoff
Date: 2026-04-22
Owner: Principal / sandbox architect
Workspace: `sandbox/codex-dr/`
Related ExecPlan: `../../docs/exec-plans/active/codex_dr_sandbox_architect_handoff.md`

## Completion Object

The object being created is a bounded repo-local workspace and execution plan
for the architect who will build the Codex-DR sandbox.

The completed state is a future architect agent launched in this folder knowing
the target, authority order, benchmark-first spine, generated-output boundary,
and root-doc interaction model before it writes design or code.

## Assumptions

- The sandbox uses terminal agents as worker intelligence.
- The sandbox target is a full attempt at Grep-system-and-performance parity.
- Benchmark acquisition and reproduction are the first empirical spine.
- Pharma product phasing remains important, while the first sandbox target is
  benchmark-facing Grep parity.
- The root cleanroom repo is still the right starting workspace because it holds
  the authority surfaces and historical proof material.
- A separate repo can be promoted later if data scale, secrets, customer data,
  or execution churn require stronger isolation.

## Teleological Ground

The sandbox exists to prove whether Alexandria can instantiate the recursive
deep-research engine that the Grep articles describe: intent ratification,
planner research, task graphing, scoped branch agents, recursive evidence work,
synthesis, reconciliation, reviewer-driven re-entry, report writing, and
benchmark-facing evaluation.

Filesystem working memory, event logs, compaction manifests, content-addressed
artefacts, and claim ledgers serve that engine by making runs inspectable,
replayable, and promotable into a later service runtime.

Fake success would be a tidy local harness that demonstrates file logging while
leaving planner adequacy, recursive retrieval, branch coordination, QA
backpressure, benchmark scoring, and report synthesis thin.

## Binding Constraints

- Launch future architect work with cwd `sandbox/codex-dr/` when possible.
- Read this folder's `AGENTS.md` before root implementation surfaces.
- Keep root `AGENTS.md` global invariants active.
- Do not let Program 90 historical receipts define the new target.
- Do not let legacy NLSpecs govern implementation without authority-ledger
  promotion.
- Do not treat a minimal vertical slice as the program endpoint.
- Do not build product service runtime surfaces inside this sandbox without an
  explicit bridge bead.
- Do not commit generated run bundles, secrets, customer data, or raw private
  benchmark corpora.

## Definition Of Done

The footing is adequate when:

- `sandbox/codex-dr/AGENTS.md` exists and names the sandbox mission, read order,
  boundary, and first move.
- `sandbox/codex-dr/README.md` explains the workspace in plain language.
- The root plan and root `AGENTS.md` point future agents to this workspace.
- A repo-local design memo records the mental model and workspace decision.
- An ExecPlan states how the architect should proceed.
- Beads expose the work as durable queue entries.
- `make check` still passes after documentation changes.
- `docs/BOOTSTRAP_DOCTRINE.md` blocks provider-backed runs until the
  provider-off bootstrap lane and token manifest rules exist.

## Literal-Following Check

If a future architect simply reads the root repo and starts implementing from
Program 90, it may look productive while missing the new target. The local
handoff exists to prevent that failure. The architect should enter through this
workspace, recover the target, perform benchmark acquisition audit, then design
the full parity sandbox.

The hindsight correction is that benchmark acquisition alone is not a safe
first execution lane. It calibrates the target. The first execution lane is the
provider-off bootstrap described in `docs/BOOTSTRAP_DOCTRINE.md`.

## What The Architect Must Remember

The architect is responsible for building the full sandbox, not an illustrative
demo.

The first empirical question is benchmark reality: which Grep-cited benchmarks
are online, obtainable, licensable, runnable, and comparable enough to support
or block a parity claim.

The second architectural question is harness shape: how terminal-agent boxes,
skills, tool scopes, files, events, compactions, CAS manifests, claim ledgers,
reviews, and re-entry decisions become one inspectable run bundle.

The third product question is bridge discipline: how the sandbox remains useful
for the later service runtime without pretending that a terminal-agent harness
is already a client-deployable SaaS or VPS product.

## Plan

0. Bootstrap autonomy gate.
   Complete `docs/BOOTSTRAP_DOCTRINE.md`: centre-lock receipt, root-gravity
   firewall, provider-off run-bundle spine, token-burn firewall, local fixture
   validators, and required skill gates.

1. Benchmark acquisition audit.
   Identify DRACO, DeepSearchQA, DeepResearch Bench, and any Parcha-published
   benchmark material. Record source URLs, license constraints, dataset access,
   case counts, evaluator shape, scoring gaps, and local reproduction burden.
   Treat this as target calibration until the provider-off bootstrap validator
   passes.

2. Parity definition.
   Convert the benchmark audit and Grep articles into a named parity contract:
   system topology, cognitive behaviors, artefacts, metrics, non-claims, and
   proof gates.

3. Harness contract design.
   Specify terminal-agent boxes, workspace lifecycle, skills, tool scopes,
   branch/subagent permissions, transcript capture, event mirroring,
   compaction receipts, CAS manifests, and run-bundle schemas.

4. CLI design.
   Specify `alexandria-dr` commands, arguments, generated files, validation
   behavior, failure modes, and red/green tests.

5. Full proof-run implementation.
   Implement through the first complete run that includes planning, branch
   work, recursive deepening, synthesis, review, re-entry, final report,
   scoring, and allowed-claims output.

6. Service-runtime bridge memo.
   Write the boundary document that states which sandbox contracts can graduate
   to the product runtime, which must be replaced, and which remain
   experimental.

## Pre-Mortem

- Bootstrap gap: the architect may understand the target and still lack a
  concrete first boot path from zero to a validated local run.
- Benchmark drift: the cited benchmark papers and datasets may be public while
  the exact Grep/Parcha evaluation configuration is unavailable.
- Token burn: the architect may spend model calls before the harness can record
  events, artefacts, compaction, review re-entry, and allowed claims.
- Terminal-agent opacity: provider or CLI transcripts may hide details needed
  for strong provenance unless wrapper capture is explicit.
- Compaction provenance: model compaction may lose source lineage unless the
  sandbox stores compaction inputs, outputs, manifests, and decision context.
- Context overload: loading every skill and document may reduce agent accuracy.
- Root gravity: existing Program 90 and one-shot demos may pull the architect
  toward local closure.
- Product confusion: a successful sandbox run may be mistaken for a deployable
  service runtime.

## Red TDD

- A provider-backed run starts before a provider-off bootstrap validator exists.
- A model-backed run has no token manifest.
- A benchmark execution is attempted before the bootstrap validator passes.
- A launch from this folder cannot identify the full parity target.
- A benchmark claim is made before acquisition and scoring conditions are
  known.
- A run emits prose without a run bundle.
- A reviewer finding cannot create re-entry work.
- A claim appears in the report without source and intermediate-work custody.
- A compaction occurs without a receipt.
- A generated run lands in git.

## Green TDD

- The architect can name the target, boundary, first move, and proof artifacts
  after reading this folder.
- The bootstrap doctrine names the provider-off first boot sequence, token
  firewall, root-gravity firewall, and skill gates.
- A local fixture run can be validated before model calls are introduced.
- The benchmark acquisition audit blocks or permits claims explicitly.
- A full proof run emits the required bundle files.
- The event log and artefact manifest cover planner, branch, synthesis, review,
  re-entry, and report steps.
- The allowed-claims artifact narrows public claims to what the run proves.
- Root `AGENTS.md` points here without making this workspace compete with
  Program 90.
