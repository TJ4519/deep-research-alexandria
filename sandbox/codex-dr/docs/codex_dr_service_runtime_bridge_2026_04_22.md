# Codex-DR Service Runtime Bridge

Status: boundary memo for `alexandriacleanroom-91.1.6`
Date: 2026-04-22
Workspace: `sandbox/codex-dr/`

## Purpose

This memo separates the benchmark-facing Codex-DR sandbox from any later
client-deployable service runtime.

The sandbox build target remains the DR mesh: a Grep-style recursive
deep-research agent system validated through Codex CLI terminal-agent
harnessing. The service runtime is a later product lane. A sandbox proof can
inform that lane, but it does not make the sandbox production-ready.

## Source Basis

- `sandbox/codex-dr/AGENTS.md`
- `sandbox/codex-dr/harness-specs/dr_mesh_parity_charter.md`
- `sandbox/codex-dr/harness-specs/grep_parity_contract.md`
- `sandbox/codex-dr/harness-specs/harness_contracts.md`
- `sandbox/codex-dr/docs/codex_mesh_launch_control_2026_04_22.md`
- `sandbox/codex-dr/docs/draco_smoke_001_run_receipt_2026_04_22.md`
- `sandbox/codex-dr/docs/draco_smoke_001_scoring_bridge_2026_04_22.md`
- `docs/design-docs/codex_dr_sandbox_architect_handoff_2026_04_22.md`

## Current Proof Ceiling

The strongest sandbox evidence is:

- `draco_smoke_001`, a boxed Codex smoke run with transcript capture and a
  recursive research bundle.
- The provider-off DR mesh harness added after the live-run halt, including
  staged mesh commands and deterministic validators.

The current proof does not establish:

- Grep parity;
- a DRACO benchmark score;
- leaderboard rank;
- product-runtime readiness;
- safe unattended provider spending;
- tenant-safe client operation.

## Contract Classification

| Sandbox contract or artifact | Classification | Service-runtime implication |
| --- | --- | --- |
| DR mesh topology charter | Promotable after hardening | Keep the planner, task graph, branch roles, pointer-first returns, synthesis, review, re-entry, writer, and scorer concepts as the product research-engine spine. Product design must add APIs, tenants, durable execution, and operational policy around it. |
| Grep parity contract | Promotable after hardening | Reuse as an evaluation and claim-boundary contract. It is not an SLA, product capability sheet, or marketing claim until service evidence exists. |
| Harness contracts | Promotable after hardening | File schemas, event envelopes, artifact manifests, branch returns, reviews, re-entry decisions, compaction receipts, claim ledgers, allowed claims, and validation reports should inform product internal contracts. They need versioning, migration rules, storage backends, and compatibility tests. |
| `alexandria-dr` command surface | Hardening-required | Useful as operator and worker control vocabulary. A service runtime needs API/job equivalents, idempotency, cancellation, authorization, and queue semantics rather than only local CLI commands. |
| Provider-off fake role adapters | Sandbox-only | Keep for deterministic tests and offline regressions. Do not present fake adapters as product research capability. |
| Codex CLI live role adapter | Hardening-required | Useful for proving Codex-in-a-box DR mesh behavior. A product lane must decide whether Codex CLI remains a supported worker substrate or is replaced by service-managed model/tool workers. |
| Run bundle tree | Promotable after hardening | Keep as the audit/export shape. Product runtime needs durable object storage, retention policy, redaction, per-tenant access, and export packaging. |
| Event mirror and causal chain | Promotable after hardening | Product runtime should retain event-first custody. It needs durable append-only storage, replay semantics, event schema migration, and tamper/audit controls. |
| Artefact manifest and SHA-256 custody | Promotable after hardening | Product runtime should preserve content-addressed artifacts. It needs CAS storage, garbage collection, encryption, and tenant-scoped references. |
| Branch return shape: `pointer.md`, `analysis.md`, `evidence.jsonl` | Promotable as written for research memory; hardening-required for product storage | This is core context economy. Product runtime needs structured span indexes, citation policies, redaction hooks, and UI affordances for pointer-first inspection. |
| Pointer-first read receipts | Promotable after hardening | Keep as context-economy proof and reviewability. Product runtime needs automated enforcement, span identifiers, and human audit display. |
| Adequacy assessments | Promotable after hardening | Keep as inner-loop backpressure. Product runtime needs policy-configured adequacy bars, reviewer overrides, and customer-visible confidence boundaries. |
| Review files and fact-checker findings | Promotable after hardening | Keep as outer-loop pressure. Product runtime needs role permissions, reviewer assignment, escalation, and audit trails for review decisions. |
| Re-entry decisions and task graph updates | Promotable after hardening | Keep as the mechanism that prevents prose-only repair. Product runtime needs durable work queues, dependency scheduling, retries, cancellation, and idempotent task creation. |
| Compaction receipts | Promotable after hardening | Keep to preserve context compression provenance. Product runtime needs automated compaction policy, quality checks, and traceable claim impact. |
| Claim ledger | Promotable after hardening | Keep as the claim-custody backbone. Product runtime needs claim extraction policy, customer-facing claim display, source redaction, and export controls. |
| Allowed-claims output | Promotable after hardening | Keep as release/response gate. Product runtime needs policy packs by customer/domain, approval workflow, and marketing/legal separation. |
| Benchmark score placeholder | Sandbox-only | Placeholder is useful for fail-closed tests only. Product or benchmark service needs real scorer manifests, judge policies, sealed-reference handling, and scorer custody. |
| DRACO smoke run bundle | Sandbox-only evidence; promotable lessons | Use as a smoke proof and operational lesson. It is not a reusable customer artifact, score, or production reliability proof. |
| `draco_smoke_001` transcript | Sandbox-only unless redacted and policy-cleared | Product runtime needs transcript retention, redaction, PII policy, customer access rules, and deletion controls. |
| Run-control receipts and launch-control halt | Hardening-required | Keep the named-run authorization, supervision, timeout, kill path, transcript, and claim-boundary ideas. Product runtime needs billing limits, spend metering, automated cancellation, and customer-visible quotas. |
| Benchmark acquisition audit | Promotable after hardening | Keep as target calibration. Product runtime needs benchmark licensing review, data handling policy, scorer procurement, and reproducible evaluation environments. |
| Tests and validators | Promotable after hardening | Keep negative controls and fail-closed posture. Product runtime needs broader integration, load, security, multi-tenant, and regression tests. |

## Product Runtime Surfaces Still Missing

The sandbox does not yet specify or implement these product requirements:

- API boundaries and client-facing contracts.
- Authentication, authorization, and tenant isolation.
- Customer data classification, retention, deletion, redaction, and export.
- Secret management for providers, search tools, connectors, and customer keys.
- Provider billing policy, spend metering, quotas, and budget enforcement.
- Durable job queues, workers, retries, cancellation, leases, and recovery.
- Source connector policy, provenance requirements, and connector-level access
  controls.
- Persistent storage model for run bundles, artifacts, transcripts, CAS hashes,
  and event streams.
- Observability for production health, cost, latency, quality, and audit.
- Admin/operator controls for run approval, pause, kill, replay, and incident
  response.
- Client report surfaces, review workflow, export format, and claim-boundary UI.
- Benchmark/scorer execution service with scorer manifests, judge prompts,
  sealed-reference policy, variance policy, and validation custody.
- Deployment, support, abuse prevention, rate limits, and compliance posture.

## Promotion Rules

1. Promote DR mesh semantics before implementation convenience.
2. Promote custody artifacts only with storage, access, retention, and redaction
   policy.
3. Promote Codex CLI adapters only if the service lane explicitly accepts CLI
   workers as a managed substrate.
4. Replace provider-off fake adapters with real worker adapters in product
   execution paths.
5. Keep benchmark placeholders out of product claims.
6. Keep allowed-claims generation in the response path; do not turn it into
   after-the-fact documentation.

## Claim Boundary

Permitted now:

- The sandbox has a DR mesh-oriented harness and proof artifacts that can inform
  later product design.
- Some contracts are suitable starting points for service-runtime internal
  interfaces after hardening.

Blocked now:

- The sandbox is product-ready.
- The boxed smoke run is a benchmark score.
- The provider-off mesh fixture is a real research result.
- Codex CLI transcript capture is sufficient production audit.
- Benchmark acquisition or public Grep/Parcha claims prove Alexandria parity.

## Recommended Next Beads

If the Principal wants to advance the service lane, create separate beads for:

- service API/job contract;
- tenant and data policy;
- durable worker and queue design;
- provider billing and spend controls;
- artifact storage and audit export;
- scorer service design.

Those beads should depend on this memo, but they should not replace the DR mesh
benchmark-facing sandbox lane.

## Completion

`alexandriacleanroom-91.1.6` can close when this memo is accepted as the
boundary artifact. It classifies the major sandbox contracts, names product
runtime gaps, preserves benchmark and proof-run lessons, and keeps service
readiness blocked until a separate product lane proves it.
