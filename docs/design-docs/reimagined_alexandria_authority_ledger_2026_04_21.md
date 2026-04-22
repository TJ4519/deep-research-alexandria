# Reimagined Alexandria Authority Ledger

Status: active authority ledger
Date: 2026-04-21
Audience: Principal, future coding agents, commissioned architect

## Why This Exists

Alexandria now has older NLSpecs, Program 80-90 proof receipts, third-party
context packs, a previous ratified charter, a root reimagining plan, and a new
candidate charter. Future agents need a durable rule for what governs which
kind of work.

The ledger prevents authority by inertia.

## Authority Classes

| Class | Meaning | May define goal line? | May drive implementation? |
| --- | --- | --- | --- |
| `RATIFIED_CHARTER` | Principal-ratified immovable commitments | Yes | Through design docs and beads |
| `CHARTER_CANDIDATE` | Draft finish-line proposal awaiting Principal ratification | No | No |
| `ROOT_PLAN` | Principal-facing plan for creating Alexandria | After ratification | Through scoped beads after design gates |
| `BINDING_SPEC` | Retained behavior spec under `canon/` after audit | Yes, within scope | Yes |
| `LEGACY_SPEC_UNAUDITED` | Imported or older spec not yet reconciled with the reimagining | No | No |
| `COMMISSIONING_BRIEF` | Defines deliverable structure and review protocol | No | No |
| `CONTEXT_PACK` | Rationale, divergence flags, and inference gaps | No | No |
| `DONOR_ARTIFACT` | External exemplar or reference | No | No |
| `LOCAL_TRANSLATION` | Repo-local memo, plan, intake, or audit | No | Only through scoped beads |
| `PROOF_RECEIPT` | Generated validation artifact | No | It constrains claims |

## Current Ledger

| Artifact | Path or URL | Class | Status | Governs |
| --- | --- | --- | --- | --- |
| Reimagined Alexandria Charter | `ALEXANDRIA_CHARTER.md` | `CHARTER_CANDIDATE` | Active draft | Reimagining review, amendment, and ratification |
| Alexandria creation plan | `PLAN_TO_CREATE_ALEXANDRIA.md` | `ROOT_PLAN` | Active draft | Reimagining program shape and next moves |
| Alexandria Charter v1.0 | `canon/specs/ALEXANDRIA_CHARTER.md` | `RATIFIED_CHARTER` | Lineage canon until supersession | Existing charter commitments and conflict detection |
| Imported NLSpecs | `canon/specs/` | `LEGACY_SPEC_UNAUDITED` for reimagining | Awaiting audit | Donor material and possible retained specs |
| Commissioning Brief | `docs/references/third_party_reimagining/2026_04_20_alexandria_design_document_commissioning_brief_v1.md` | `COMMISSIONING_BRIEF` | Active | Design Document deliverable and review protocol |
| Context Pack 00-06 | `docs/references/third_party_reimagining/` | `CONTEXT_PACK` | Imported; Pack 07 missing | Rationale, divergence flags, inference gaps |
| Context Pack intake | `docs/design-docs/alexandria_reimagining_context_pack_intake_2026_04_20.md` | `LOCAL_TRANSLATION` | Active | Ordered read ledger and missing Pack 07 warning |
| FrankenEngine plan | `https://github.com/Dicklesworthstone/franken_engine/blob/main/PLAN_TO_CREATE_FRANKEN_ENGINE.md` | `DONOR_ARTIFACT` | Studied for structure | Plan craft only |
| FrankenEngine donor analysis | `docs/design-docs/alexandria_frankenengine_plan_donor_analysis_2026_04_21.md` | `LOCAL_TRANSLATION` | Active | Structural moves translated for Alexandria |
| Grep Claude-in-a-Box article | `docs/references/claude_in_a_box_grep_agents_sdk_2025_12_11.md` | `DONOR_ARTIFACT` | Stored and public URL checked | Grep substrate evidence for isolated SDK boxes, selective skills, MCP scopes, fork/resume, and researcher-to-reporter handoff |
| Claude-in-a-Box implications memo | `docs/design-docs/claude_in_a_box_implications_for_alexandria_agent_py_2026_04_21.md` | `LOCAL_TRANSLATION` | Active | Design pressure for `agent.py`, branch execution, SDK boxes, and custody boundaries |
| Codex-DR sandbox architect handoff | `docs/design-docs/codex_dr_sandbox_architect_handoff_2026_04_22.md` and `sandbox/codex-dr/` | `LOCAL_TRANSLATION` | Active | First architect workspace, memory contract, benchmark-first spine, terminal-agent sandbox boundary, and service-runtime bridge |
| Program 90 receipts | `docs/generated/runtime/latest_program90_parity_proof_suite.json` and siblings | `PROOF_RECEIPT` | Historical proof surface | Claim boundaries and implementation evidence |

## Conflict Rule

If a legacy NLSpec, proof receipt, or design doc conflicts with the root
candidate charter's telos, stop and classify the conflict:

- retain old clause
- supersede old clause
- use old clause as donor material
- rewrite old clause
- escalate to Principal

Do not implement from a conflicted clause until the classification is repo-local.

The Claude-in-a-Box article creates a substrate conflict with the older
Messages-only / no-SDK clause. The candidate charter resolves that conflict by
allowing SDK boxes for branch execution while keeping orchestration and custody
inside Alexandria.

The Codex-DR sandbox handoff creates a workspace-routing rule. Grep-parity
sandbox architect work enters through `sandbox/codex-dr/` and treats Program 90
receipts as historical evidence, not as the new target definition.

## Reimagining Work Rule

For reimagining work, read in this order:

1. `ALEXANDRIA_CHARTER.md`
2. `PLAN_TO_CREATE_ALEXANDRIA.md`
3. this authority ledger
4. `docs/design-docs/alexandria_reimagining_context_pack_intake_2026_04_20.md`
5. the relevant source artifact
6. legacy NLSpecs only after deciding why they are relevant

## Implementation Work Rule

Implementation work is blocked unless the bead cites:

- ratified charter or explicit candidate-charter scope
- ratified root plan or scoped design-entry task
- relevant Design Document section once the Design Document exists
- interface, schema, file format, control-flow, and proof obligations
- acceptance criteria and red/green validation for complex work

## Ratification Path

1. Principal reviews `ALEXANDRIA_CHARTER.md`.
2. Principal reviews `PLAN_TO_CREATE_ALEXANDRIA.md`.
3. Amendments are appended or committed.
4. Ratified charter is promoted into `canon/` through explicit supersession.
5. Old NLSpecs enter audit and classification.
6. The Commission Restatement is produced from the stable authority surface.

## Non-Claims

This ledger does not ratify the candidate charter.

This ledger does not delete or supersede legacy specs by itself.

This ledger does not claim Grep parity, pharma readiness, or Design Document
completion.

This ledger makes the authority state explicit so the next agent does not have
to reconstruct it from chat.
