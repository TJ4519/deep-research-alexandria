# Third-Party Reimagining Artifact Registry

Status: active intake registry
Date: 2026-04-20
Audience: governor, principal engineer, future coding agents

## Why This Exists

Alexandria is being re-thought with help from third-party artifacts: charters,
context packs, proposed specifications, and architecture memos.

Those artifacts must not live only in chat or persistent assistant memory.
Future agents need a repo-local way to discover:

1. that the artifact exists
2. where the artifact is stored
3. whether it is relevant to the current task
4. what authority class it has
5. whether it has been reconciled with canon and proof receipts

This registry is that durable map.

## Completion Object

Maintain one repo-local registry that keeps third-party reimagining artifacts
discoverable across sessions without relying on assistant memory.

The registry is complete only when every imported third-party CHARTER, context
pack, or proposed spec has:

- a stable repo path
- an authority class
- relevance triggers
- reconciliation status
- supersession status
- an explicit non-substitution rule

## Teleological Ground

The purpose is to let Alexandria benefit from external architectural thinking
without letting external prose silently redefine the system.

Failure still counts as failure if:

1. a future agent must remember from chat that an artifact exists
2. a third-party artifact is treated as canon because it sounds authoritative
3. a proposed spec bypasses `canon/` reconciliation
4. an old artifact remains discoverable but its relevance or supersession state
   is unclear
5. a lower-order context pack collapses the governing finish line

## Authority Ladder

Use this ladder when registering artifacts:

| Class | Meaning | May Define Goal Line? | May Drive Code Directly? |
| --- | --- | --- | --- |
| `BINDING_SPEC` | Governing behavior under `canon/` | Yes | Yes, through bead/plan work |
| `RATIFIED_CHARTER` | Governor-ratified immovable commitments | Yes | Not without design-doc, bead, and plan packaging |
| `COMMISSIONING_BRIEF` | Governs a design/specification deliverable, review protocol, and quality bar | No, unless promoted separately | No |
| `CONTEXT_PACK` | Rationale, divergence flags, inference gaps, and prior-material maps supporting a ratified charter or commission | No | No |
| `CHARTER` | Repo-local governing finish-line artifact | Yes, below binding specs | Not without implementation packaging |
| `CHARTER_CANDIDATE` | Incoming or unratified finish-line proposal | No | No |
| `ROOT_PLAN` | Repo-root creation plan for a ratified or candidate program | After ratification | Through scoped beads and design gates |
| `SPEC_CANDIDATE` | Incoming or unratified behavior/interface proposal | No | No |
| `DONOR_ARTIFACT` | External exemplar studied for structural moves or prior art | No | No |
| `LOCAL_TRANSLATION` | Design doc, plan, memo, or runbook translating canon | No | Only through scoped bead/plan work |
| `CHECKPOINT` | Dated posture or claim-boundary summary | No | No |
| `PROOF_RECEIPT` | Generated validation or harness artifact | No | It constrains claims |
| `EXTERNAL_SNAPSHOT` | Prior art or public/external reference | No | No |

## Current Registered Artifacts

| Artifact id | Path | Class | Status | Relevant when | Non-substitution rule |
| --- | --- | --- | --- | --- | --- |
| `third_party_reimagining_raw_intake` | `docs/references/third_party_reimagining/` | `EXTERNAL_SNAPSHOT` / candidate intake | Active landing zone | A new third-party CHARTER, context pack, or proposed spec is provided | Raw storage does not make an artifact binding |
| `alexandria_reimagined_charter_candidate_2026_04_21` | `ALEXANDRIA_CHARTER.md` | `CHARTER_CANDIDATE` | Active draft for Principal ratification | A task concerns the reimagined telos, Grep interpretation, recursive research cognition, authority repair, or root plan review | Candidate charter guides the reimagining lane but does not supersede Charter v1.0 until ratified and promoted |
| `alexandria_creation_plan_root_2026_04_21` | `PLAN_TO_CREATE_ALEXANDRIA.md` | `ROOT_PLAN` | Active draft for Principal ratification | A task concerns the post-reimagining execution program, design-entry sequencing, authority migration, or bead readiness | Root plan does not authorize implementation work before ratification and design gates |
| `reimagined_alexandria_authority_ledger_2026_04_21` | `docs/design-docs/reimagined_alexandria_authority_ledger_2026_04_21.md` | `LOCAL_TRANSLATION` | Active | A task must decide what governs root plan, candidate charter, legacy NLSpecs, third-party artifacts, or proof receipts | Ledger records authority state; it does not ratify the candidate charter or supersede legacy specs by itself |
| `franken_engine_plan_donor_2026_04_21` | `https://github.com/Dicklesworthstone/franken_engine/blob/main/PLAN_TO_CREATE_FRANKEN_ENGINE.md`; analysis at `docs/design-docs/alexandria_frankenengine_plan_donor_analysis_2026_04_21.md` | `DONOR_ARTIFACT` / `LOCAL_TRANSLATION` | Studied for structure | A task concerns the shape of an excellent root plan, ambition rules, proof floors, impossible-by-default capability lists, evidence contracts, risk registers, or benchmark strategy | FrankenEngine is a plan-structure donor only; it does not define Alexandria architecture |
| `alexandria_charter_v1_2026_04_20` | `canon/specs/ALEXANDRIA_CHARTER.md` | `RATIFIED_CHARTER` | Ratified and promoted to canon; metadata at `docs/references/third_party_reimagining/2026_04_20_alexandria_charter_v1.metadata.md` | Any task concerns Alexandria's telos, runtime substrate, filesystem/event-log architecture, provider strategy, Grep-shape topology, pharma CI wedge, non-goals, or design-doc ticket quality bar | Charter clauses are immovable; downstream specs and tickets may implement but not reinterpret or relitigate them |
| `alexandria_design_document_commissioning_brief_v1_2026_04_20` | `docs/references/third_party_reimagining/2026_04_20_alexandria_design_document_commissioning_brief_v1.md` | `COMMISSIONING_BRIEF` | Active; metadata at `docs/references/third_party_reimagining/2026_04_20_alexandria_design_document_commissioning_brief_v1.metadata.md` | A task concerns the Alexandria Design Document, Commission Restatement, master index, subsystem docs, event schemas, tool specs, artefact formats, control-flow specs, WBS, divergence/gap resolution, out-of-scope sections, Linear delivery, adversarial review, or random-sample ticket test | Governs the design-document deliverable; does not amend the Charter and cannot be fully executed until the Context Pack is imported or explicitly waived |
| `alexandria_context_pack_v1_sections_00_06_2026_04_20` | `docs/references/third_party_reimagining/2026_04_20_context_pack_00_master_index.md` plus sibling files `01` through `06`; compression at `docs/design-docs/alexandria_reimagining_context_pack_intake_2026_04_20.md` | `CONTEXT_PACK` | Sections 00-06 imported from Linear and read in order; Pack 07 is referenced by Pack 00 but missing/not found | A task concerns the Commission Restatement, Design Document rationale, Grep reconstruction, telos evolution, pharma CI wedge, framework/runtime exclusions, divergence flags, or INFERENCE gaps | Context Pack is RATIONALE only; it cannot amend the Charter, and design work cannot claim full Context Pack intake until Pack 07 is obtained or explicitly waived |
| `dream_version_proof_charter` | `canon/specs/dream-version-proof-charter.md` | `CHARTER` | Draft for governor ratification; active finish-line guide | A task concerns dream-version proof, claim ladder, topology, or long-horizon program shape | Does not erase binding NLSpecs or current proof ceilings |
| `grep_deep_research_snapshot_2026_03_16` | `docs/references/grep_building_grep_deep_research_2026_03_16.md` | `EXTERNAL_SNAPSHOT` | Dated public reference snapshot | A task concerns workbench/context economy, planner/task topology, file-backed research artifacts, or Grep comparison | Do not infer Grep private implementation or parity from the public article |
| `runtime_authority_workbench_reconciliation_2026_04_16` | `docs/design-docs/runtime_authority_and_workbench_artifact_reconciliation_2026_04_16.md` | `LOCAL_TRANSLATION` | Active reconciliation proposal | A task concerns authority state versus workbench artifacts | Does not make workbench artifacts authoritative |
| `fresh_session_principal_engineer_bootstrap_2026_04_17` | `docs/runbooks/fresh_session_principal_engineer_bootstrap_2026_04_17.md` | `LOCAL_TRANSLATION` / runbook | Active bootstrap | A fresh agent is asked to establish teleology or audit planning drift | Runbook instructions do not outrank canon |
| `program90_workbench_center_of_gravity_rebuild` | `docs/exec-plans/active/program90_workbench_center_of_gravity_rebuild.md` | `LOCAL_TRANSLATION` / ExecPlan | Active Program 90 owner | A task touches Program 90, workbench-centered cognition, recursive research, selective re-entry, or claim boundaries | Plan sequences work; it does not widen claims by itself |
| `program90_harness_centered_deep_research_rebuild` | `docs/exec-plans/active/program90_harness_centered_deep_research_rebuild.md` | `LOCAL_TRANSLATION` / ExecPlan | Active companion plan | A task needs Program 90 proof packaging, red/green TDD, or bead semantics | Proof obligations remain gated by receipts and allowed claims |
| `program90_allowed_claim_ceiling` | `docs/generated/runtime/latest_allowed_claims_registry.json` | `PROOF_RECEIPT` / claim surface | Active claim ceiling | A task asks what Alexandria may honestly claim now | Claim ceiling blocks broad Grep parity, provider-on parity, and domain maturity claims |

## Pending Imports

The user has stated that a third party has written or is writing one or more
additional specifications.

If these artifacts are provided in chat, by file path, or by external export,
the next agent must store them under `docs/references/third_party_reimagining/`
and add explicit rows to this registry before using them for planning.

The CHARTER has been imported and promoted as
`canon/specs/ALEXANDRIA_CHARTER.md`.

The Alexandria Design Document Commissioning Brief has been imported as
`docs/references/third_party_reimagining/2026_04_20_alexandria_design_document_commissioning_brief_v1.md`.

Context Pack sections 00 through 06 have been imported from Linear under
`docs/references/third_party_reimagining/` and compressed for intake at
`docs/design-docs/alexandria_reimagining_context_pack_intake_2026_04_20.md`.

Context Pack 00 references `07_existing_spec_material.md`; that Pack 07
document remains pending until obtained or explicitly waived by the Principal.

## Relevance Rules

Read this registry when a task mentions:

- third-party charter
- root charter
- root plan
- context pack
- Context Pack 07
- reimagining
- Grep-inspired architecture
- FrankenEngine plan
- Program 90
- workbench/context economy
- active research cognition
- claim ladder or dream-version proof
- proposed specifications outside `canon/`

Read the registered artifact itself only when its relevance trigger matches the
task. Do not bulk-load unrelated artifacts.

## Intake Protocol

When importing a new third-party artifact:

1. Store the artifact under `docs/references/third_party_reimagining/`.
2. Preserve the source text faithfully. Use a sidecar note if metadata would
   disturb the raw artifact.
3. Add or update a row in `Current Registered Artifacts`.
4. Mark the authority class honestly.
5. Add relevance triggers specific enough that future agents know when to read
   it.
6. Add a non-substitution rule.
7. If it proposes behavior, create a reconciliation design doc before code.
8. If it should become binding, promote only through `canon/` with explicit
   ratification.
9. If it creates complex implementation work, create or update beads and an
   ExecPlan.

## Non-Claims

This registry does not claim that any pending third-party artifact has been
read, validated, reconciled, or accepted.

This registry does not make external artifacts binding.

This registry does not widen Alexandria's current allowed claim ceiling.

This registry only makes the artifact trail durable and discoverable.
