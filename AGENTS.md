# AGENTS.md

This file is a map, not an encyclopedia.

## Mission

Build the reimagined Alexandria deep-research runtime from repo-local authority,
using a cleanroom repo that is optimized for future coding-agent legibility.

## Start Here

1. `ALEXANDRIA_CHARTER.md`
2. `PLAN_TO_CREATE_ALEXANDRIA.md`
3. `docs/design-docs/reimagined_alexandria_authority_ledger_2026_04_21.md`
4. `README.md`
5. `canon/CANON.md`
6. `data/SOURCES.md`
7. `ARCHITECTURE.md`
8. `docs/SYSTEM_MAP.md`
9. `docs/KNOWLEDGE_MAP.md`
10. `docs/README.md`

## Working Invariants

- Use `uv` for Python versioning, dependency management, and command execution.
- Do not use `pip install`, `python -m venv`, or Node bootstrap tools here.
- Keep backend runtime, ingestion, and dev-hygiene concerns separate.
- Treat the repo as the source of truth; chat and external trackers are secondary.
- For reimagining work, read the root candidate charter and root plan before
  legacy NLSpecs. Old numbered NLSpecs are audit material until retained,
  superseded, rewritten, or promoted by an explicit authority note.
- For implementation work, do not build from a conflicted or unaudited legacy
  clause. Cite the ratified charter/plan surface, relevant design-document
  section when available, and the bead/ExecPlan acceptance contract.
- Use beads for work tracking and dependencies.
- Use an ExecPlan for any bead that is complex, risky, or likely to span sessions.
- Prefer boring, inspectable machinery over clever hidden state.

## Commands

- `uv sync --group dev`
- `make check`
- `make lint`
- `make test`
- `bd ready`

## Knowledge Map

- `ALEXANDRIA_CHARTER.md`: candidate reimagined charter naming recursive deep-research cognition as the governing telos
- `PLAN_TO_CREATE_ALEXANDRIA.md`: root plan for creating Alexandria after the reimagining
- `docs/design-docs/reimagined_alexandria_authority_ledger_2026_04_21.md`: current authority ledger for root plan, candidate charter, legacy NLSpecs, context packs, donor artifacts, and proof receipts
- `docs/design-docs/alexandria_frankenengine_plan_donor_analysis_2026_04_21.md`: donor-structure analysis of the FrankenEngine plan and its Alexandria translation
- `canon/CANON.md`: what is binding, what is legacy/audit material, and how to read imported specs
- `canon/specs/ALEXANDRIA_CHARTER.md`: prior ratified Charter v1.0, retained as lineage canon until explicit supersession
- `data/SOURCES.md`: what data exists and how it may be used
- `docs/SYSTEM_MAP.md`: concrete bridge from Alexandria concepts to code, tests, and proof artifacts
- `docs/KNOWLEDGE_MAP.md`: plain-language map of folders, commands, work tracking, and harness families
- `docs/README.md`: progressive-disclosure index for workflow, plans, quality, and debt
- `docs/GOLDEN_RULES.md`: anti-drift rules and enforcement posture
- `docs/design-docs/third_party_reimagining_artifact_registry_2026_04_20.md`: durable authority and relevance registry for third-party CHARTER, context-pack, and proposed-spec artifacts
- `docs/design-docs/alexandria_reimagining_context_pack_intake_2026_04_20.md`: ordered Linear read ledger and teleological compression for the Charter, Commissioning Brief, and Context Pack 00-06; records Pack 07 as missing until obtained or waived
- `docs/exec-plans/active/`: living plans for complex beads
- `app/README.md`: backend layer model and package layout

## Current Checkpoint

- Active Program 90 owner:
  `docs/exec-plans/active/program90_harness_centered_deep_research_rebuild.md`
- Reimagined root charter:
  `ALEXANDRIA_CHARTER.md`
- Reimagined root plan:
  `PLAN_TO_CREATE_ALEXANDRIA.md`
- Reimagined authority ledger:
  `docs/design-docs/reimagined_alexandria_authority_ledger_2026_04_21.md`
- Program 90 proof suite:
  `docs/generated/runtime/latest_program90_parity_proof_suite.json`
- Program 90 final selective re-entry gate:
  `docs/generated/runtime/latest_program90_selective_reentry_closure.json`
- Program 90 workbench plan:
  `docs/exec-plans/active/program90_workbench_center_of_gravity_rebuild.md`
- Controlled parity lane:
  `docs/exec-plans/active/program90_controlled_parity_experiment_lane.md`
- Prior ratified Alexandria Charter v1.0:
  `canon/specs/ALEXANDRIA_CHARTER.md`
- Third-party reimagining artifact registry:
  `docs/design-docs/third_party_reimagining_artifact_registry_2026_04_20.md`
- Third-party reimagining context-pack intake:
  `docs/design-docs/alexandria_reimagining_context_pack_intake_2026_04_20.md`
- Required root-cause note before interpreting parity baseline:
  `docs/design-docs/program90_controlled_parity_root_cause_and_corrected_interpretation_2026_04_18.md`
- Current honesty surfaces:
  `docs/generated/runtime/latest_allowed_claims_registry.json`,
  `docs/generated/runtime/latest_release_gate_validation.json`,
  `docs/generated/runtime/latest_product_surface_drift_monitor.json`
- Historical context lives in `docs/exec-plans/completed/` and `docs/design-docs/`.

## Work Tracking

- Use `bd ready --no-daemon` to see the current unblocked queue.
- Claim, close, and update beads with `bd --no-daemon` so the runtime lane stays deterministic.
- Keep complex or session-spanning work in an ExecPlan under `docs/exec-plans/active/`.
- Read the relevant active ExecPlan before touching Program `90`, report,
  topology, or claim-boundary work.
- Do not overclaim from proof receipts; start with
  `docs/generated/runtime/latest_allowed_claims_registry.json`.
