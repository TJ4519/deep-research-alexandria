#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

SANDBOX_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS_DIR = SANDBOX_ROOT / "runs"
DEFAULT_DEEPRESEARCH_BENCH_OFFICIAL_REPO = (
    SANDBOX_ROOT / "tmp" / "deepresearch_bench_official"
)
DEEPRESEARCH_BENCH_RACE_SCORER_MANIFEST_SCHEMA = (
    "harness-specs/deepresearch_bench_race_scorer_manifest.schema.json"
)
DEEPRESEARCH_BENCH_RACE_EVALUATION_OUTPUT_SCHEMA = (
    "harness-specs/deepresearch_bench_race_evaluation_output.schema.json"
)
SELF_IMPROVEMENT_TAXONOMY_PATH = (
    SANDBOX_ROOT / "harness-specs" / "self_improvement_failure_taxonomy.json"
)
SELF_IMPROVEMENT_CORPUS_PATH = (
    SANDBOX_ROOT / "harness-specs" / "provider_off_self_improvement_replay_corpus.json"
)
DEFAULT_DRACO_DATASET_SOURCE = {
    "benchmark_family": "DRACO",
    "dataset_id": "perplexity-ai/draco",
    "dataset_commit": "ce076749809027649ebd331bcb70f42bf720d387",
    "split": "test",
    "source_file": "test.jsonl",
    "license_observed": "mit",
    "access_observed": "public_ungated",
    "manifest_ref": (
        "sandbox/codex-dr/benchmark-manifests/draco_tiny_smoke_case_manifest.md"
    ),
}
BENCHMARK_FAMILY_DRACO = "DRACO"
BENCHMARK_FAMILY_DEEPRESEARCH_BENCH = "DEEPRESEARCH_BENCH"
SUPPORTED_CASE_MANIFEST_FAMILIES = {
    BENCHMARK_FAMILY_DRACO,
    BENCHMARK_FAMILY_DEEPRESEARCH_BENCH,
}
CASE_SOURCE_REQUIRED_FIELDS = [
    "dataset_id",
    "dataset_commit",
    "split",
    "source_file",
    "row_indices",
    "license_observed",
    "access_observed",
    "manifest_ref",
]
SATISFIED_ADEQUACY_STATUSES = {
    "satisfied",
    "satisfied_for_provider_off_topology",
    "passed",
    "clear",
}
SCORER_BLOCKING_ADEQUACY_STATUSES = {
    "not_satisfied",
    "partially_satisfied",
    "failed",
    "blocked",
    "open",
}
SELF_LIMITING_REPORT_PATTERNS = [
    "not benchmark-grade",
    "not adequately demonstrated",
    "directional thesis",
    "benchmark-grade closure is still blocked",
    "not yet adequately demonstrated",
]
COMPARATIVE_PROMPT_MARKERS = [
    "compare",
    "comparison",
    "rank",
    "ranking",
    "shortlist",
    "which",
    "比较",
    "横向",
    "评估",
    "排名",
    "哪一个",
]
FIXTURE_TIMESTAMP = "2026-04-22T00:00:00Z"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
DEFAULT_CODEX_EXEC_MODEL = "gpt-5.4"
DEFAULT_CODEX_EXEC_REASONING = "medium"
MODEL_PROBE_PROMPT = "Write exactly: codex-dr model probe ok"
MODEL_PROBE_EXPECTED_MESSAGE = "codex-dr model probe ok"
EVENT_WRITE_LOCK = threading.RLock()

REQUIRED_EVENT_TYPES = [
    "case.initialized",
    "plan.written",
    "task_graph.written",
    "agent_box.placeholder_written",
    "branch.spawn_declared",
    "branch.return_written",
    "adequacy.assessed",
    "review.written",
    "reentry.compiled",
    "synthesis.written",
    "compaction.receipt_written",
    "claim_ledger.written",
    "allowed_claims.written",
    "report.written",
    "benchmark.placeholder_written",
]

REQUIRED_FILES = [
    "run_manifest.json",
    "events.jsonl",
    "artefact_manifest.json",
    "plan.md",
    "adequacy_criteria.json",
    "task_graph.json",
    "terminal_agent_boxes.json",
    "branches/branch_a/branch_manifest.json",
    "branches/branch_a/pointer.md",
    "branches/branch_a/analysis.md",
    "branches/branch_a/evidence.jsonl",
    "adequacy_assessments.jsonl",
    "synthesis.md",
    "contradictions.json",
    "report_outline.md",
    "reviews/review_001.json",
    "reentry_decisions.jsonl",
    "claim_ledger.json",
    "compactions/compaction_001.json",
    "report.md",
    "benchmark_score.json",
    "allowed_claims.json",
]

MESH_BRANCH_ROLES = {
    "deep_search": {
        "task_id": "task_deep_search",
        "box_id": "box_deep_search",
        "role": "deep_search",
        "objective": "Collect public-source orientation for the tiny DRACO-shaped smoke case.",
        "analysis_section": "Public-Source Orientation",
        "evidence_id": "ev_deep_search_001",
    },
    "data_analysis": {
        "task_id": "task_data_analysis",
        "box_id": "box_data_analysis",
        "role": "data_analysis",
        "objective": "Inspect the local case fields and identify scoring-relevant structure.",
        "analysis_section": "Local Case Structure",
        "evidence_id": "ev_data_analysis_001",
    },
    "verification": {
        "task_id": "task_verification",
        "box_id": "box_verification",
        "role": "verification",
        "objective": "Verify claim boundaries, source admission, and non-execution constraints.",
        "analysis_section": "Verification Notes",
        "evidence_id": "ev_verification_001",
    },
    "reentry_followup": {
        "task_id": "task_reentry_followup",
        "box_id": "box_reentry_followup",
        "role": "verification",
        "objective": "Answer the reviewer-requested follow-up without widening claims.",
        "analysis_section": "Reviewer Re-Entry Follow-Up",
        "evidence_id": "ev_reentry_followup_001",
    },
}

MESH_INITIAL_BRANCH_IDS = ["deep_search", "data_analysis", "verification"]
MESH_ALL_BRANCH_IDS = [*MESH_INITIAL_BRANCH_IDS, "reentry_followup"]
LIVE_ROLE_PROMPT_PACK_REF = "sandbox/codex-dr/harness-specs/live_role_prompt_pack.md"
LIVE_CONTROL_OUTPUTS = {
    "task_plan": {"plan.md", "skills_tools.json", "adequacy_criteria.json", "task_graph.json"},
}
LIVE_CUMULATIVE_JSONL_OUTPUTS = {
    "pointer_read_receipts.jsonl",
    "reentry_decisions.jsonl",
}
EVIDENCE_ADMITTED_STATUSES = {
    "admitted",
    "admitted_local_artifact",
    "admitted_process_fact",
    "limited_admission",
    "derived_from_admitted_inputs",
    "inference_from_admitted_artifacts",
}
EVIDENCE_GAP_STATUSES = {
    "gap",
    "blocked",
    "blocked_by_input",
    "explicit_gap",
    "missing_required_packet",
    "missing_reentry_task_packet",
    "needs_synthesis",
    "unsupported",
    "not_admitted",
    "unadmitted",
    "not_admitted_for_claim",
    "not_admitted_for_claim_support",
}
EVIDENCE_RESULT_STATUSES = {
    "bounded_result",
}
BACKPRESSURE_CLOSED_STATUSES = {"closed", "superseded", "lawful_partial"}
BACKPRESSURE_WRITER_BLOCKING_STATUSES = {
    "open",
    "assigned",
    "repair_returned",
    "review_pending",
    "narrowed",
    "blocked_by_input",
    "blocked_by_tooling",
}
BACKPRESSURE_QUEUE_SCHEMA_VERSION = "codex-dr.adequacy_backpressure_queue.v2"
BACKPRESSURE_QUEUE_LEGACY_SCHEMA_VERSION = "codex-dr.adequacy_backpressure_queue.v1"
BACKPRESSURE_GATE_RECEIPT_SCHEMA_VERSION = "codex-dr.backpressure_gate_receipt.v1"
WRITER_GATE_PREFLIGHT_SCHEMA_VERSION = "codex-dr.writer_gate_preflight.v1"
REENTRY_TASK_PACKET_SCHEMA_VERSION = "codex_dr_reentry_task_packet_v0.3"
REENTRY_ADEQUACY_DELTA_SCHEMA_VERSION = "codex_dr_reentry_adequacy_delta.v1"
CITATION_SUPPORT_MAP_SCHEMA_VERSION = "codex_dr_citation_support_map.v1"
REENTRY_BASE_OUTPUTS = [
    "pointer.md",
    "analysis.md",
    "evidence.jsonl",
    "reentry_result.json",
]
REENTRY_BLOCKED_COMPILER_STATUSES = {
    "blocked_by_assignment_ambiguity",
    "blocked_no_eligible_item",
    "blocked_malformed_queue_item",
    "blocked_by_missing_input",
    "blocked_by_missing_authority",
}
REENTRY_MUST_NOT_CLAIM = [
    "final_answer_success",
    "grep_parity",
    "benchmark_score",
    "leaderboard_rank",
    "product_readiness",
    "official_submission",
    "scorer_backed_evaluation",
]
REENTRY_RESULT_STATUSES = {
    "closed_candidate",
    "narrowed",
    "narrowed_review_pending",
    "open",
    "blocked_by_input",
    "blocked_by_tooling",
    "contradicted",
    "lawful_partial_candidate",
}
CITATION_SUPPORT_MAP_LEGACY_SCHEMA_VERSIONS = {
    "codex_dr_citation_support_map_v0.1",
}
CITATION_SUPPORT_STATUSES = {
    "supported",
    "directly_supported",
    "partially_supported",
    "indirectly_supported",
    "unsupported",
    "contradicted",
    "source_missing",
    "too_broad_for_evidence",
    "not_material",
    "downgraded",
    "removed",
    "lawful_partial_candidate",
}
CITATION_WRITER_BLOCKING_STATUSES = {
    "unsupported",
    "contradicted",
    "source_missing",
    "too_broad_for_evidence",
}
REVIEWER_FORBIDDEN_OUTPUTS = {
    "backpressure/adequacy_backpressure_queue.json",
    "backpressure/backpressure_gate_receipt.json",
    "final_report.md",
    "report.md",
    "allowed_claims.json",
    "benchmark_score.json",
}
REENTRY_FORBIDDEN_OUTPUTS = {
    "backpressure/adequacy_backpressure_queue.json",
    "backpressure/backpressure_gate_receipt.json",
    "reviews/review_001.json",
    "final_report.md",
    "report.md",
    "allowed_claims.json",
    "benchmark_score.json",
}


def mesh_branch_objective(branch_id: str, benchmark_family: str) -> str:
    if benchmark_family == BENCHMARK_FAMILY_DEEPRESEARCH_BENCH:
        objectives = {
            "deep_search": (
                "Collect public-source evidence for the DeepResearch Bench prompt."
            ),
            "data_analysis": (
                "Analyze population, consumption, market-size, and forecast structure "
                "needed by the DeepResearch Bench prompt."
            ),
            "verification": (
                "Verify source admission, citation support, sealed-scorer boundaries, "
                "and non-claims for the DeepResearch Bench run."
            ),
            "reentry_followup": (
                "Answer the reviewer-requested DeepResearch Bench follow-up without "
                "reading scorer-only material or widening claims."
            ),
        }
        return objectives[branch_id]
    return MESH_BRANCH_ROLES[branch_id]["objective"]


ROLE_PROMPT_PROFILES = {
    "planner": {
        "title": "Researcher-Planner",
        "instructions": [
            "Read case_manifest.json first when present, then any ratification, governor-instruction, or run-control files included in the allowed inputs.",
            "Recover the research ground before branch design: surface request, recovered objective, candidate answer object, scope boundaries, topology-changing ambiguities, proposed defaults, and fake-success modes.",
            "Use planning status `mesh_plan_ready`, `awaiting_ratification`, or `blocked_by_input` consistently across plan.md, skills_tools.json, adequacy_criteria.json, and task_graph.json.",
            "Ask clarification only for topology-changing ambiguity; ask no more than five questions, and state what would change in the mesh plan.",
            "If ratification is pending or input authority is missing, write blocked planning packets and do not compile executable branch tasks.",
            "You may propose defaults, but default authorization must come from the user, governor, ratification receipt, or run-control context.",
            "Compile a mesh plan only when the answer object is fixed or ratification/default authorization is supplied by the run context.",
            "Plan by epistemic function, with explicit branch dependencies, pointer-first output contracts, adequacy checks, re-entry triggers, writer gate, and claim boundaries.",
        ],
    },
    "deep_search": {
        "title": "Deep Search Branch",
        "instructions": [
            "Collect source candidates and source-backed observations only within the run-control data policy.",
            "Preserve source URLs, local paths, retrieval method, access timestamp when available, and access gaps.",
            "Classify evidence rows as source discovery, direct evidence, contradiction candidate, provenance note, or gap.",
            "State what each source supports, what it does not support, and what still needs verification.",
            "Do not treat source discovery as source validation or benchmark/parity evidence.",
        ],
    },
    "data_analysis": {
        "title": "Data Analysis Branch",
        "instructions": [
            "Inspect case fields, benchmark-relevant structure, and scoring implications.",
            "Separate observed data from inference and blocked reference-answer material.",
            "Record claim ids, quantities/comparisons, derivations, source paths, evidence ids, confidence, and unresolved gaps for numerical or comparative claims.",
            "Do not rank, compare, forecast, or normalize unless the metrics, time horizon, geography/jurisdiction, entity class, and evidence standard are explicit.",
            "Mark unresolved comparability as non_comparable_inputs or scope_ambiguity rather than forcing a conclusion.",
        ],
    },
    "verification": {
        "title": "Verification Branch",
        "instructions": [
            "Check claim boundaries, source admission, citation support, and non-claims.",
            "Consume assigned claims, source rows, pointer receipts, or branch evidence; do not perform broad new search unless explicitly permitted.",
            "Identify unsupported or overbroad claims before synthesis or report writing.",
            "Classify each checked claim as directly_supported, partially_supported, indirectly_supported, unsupported, contradicted, source_missing, or too_broad_for_evidence.",
            "Distinguish source existence from statement-to-source support.",
            "Return verification evidence without enabling benchmark or parity claims.",
        ],
    },
    "orchestrator": {
        "title": "Evaluate And Synthesize Orchestrator",
        "instructions": [
            "Read pointer files before analysis files and admit only named analysis spans.",
            "Assess adequacy criteria, contradictions, unresolved gaps, and re-entry needs.",
            "Write adequacy_assessments.jsonl for unresolved adequacy; the harness owns canonical backpressure queue compilation.",
            "When running re-entry synthesis, integrate bounded repair artifacts without closing blockers or authorizing the writer.",
            "Write synthesis from admitted evidence and preserve blocked claims.",
        ],
    },
    "reviewer": {
        "title": "Reviewer And Fact-Checker",
        "instructions": [
            "Adjudicate admitted synthesis against the recovered answer object and planning-time adequacy criteria.",
            "Do not answer the research question, write the final report, run broad new research, score benchmarks, or promote claims.",
            "Review plan.md, adequacy_criteria.json, task_graph.json, pointer-read receipts, adequacy assessments, synthesis, contradictions, report outline, branch artifacts, and any existing backpressure queue.",
            "Distinguish supported claims, unsupported claims, hypotheses, contradictions, provenance gaps, non-comparable inputs, citation gaps, and claim-boundary failures.",
            "Write actionable semantic blockers under proposed_backpressure_items in the review artifact for bounded re-entry, citation verification, methodology repair, or adequacy pressure.",
            "Adjudicate semantic adequacy only; the harness owns canonical queue compilation and derived transition gate receipts.",
            "Do not write backpressure/adequacy_backpressure_queue.json or backpressure/backpressure_gate_receipt.json.",
        ],
    },
    "reentry": {
        "title": "Reviewer-Driven Re-Entry Branch",
        "instructions": [
            "Consume exactly one branch-local reentry_task_packet.json when present.",
            "Execute only the bounded repair objective named by the task packet; do not reopen the whole research question.",
            "For ready packets, return pointer.md, analysis.md, evidence.jsonl, reentry_result.json, and any packet-required closure artifacts.",
            "For missing, malformed, or non-ready packets, return blocked fallback outputs with a blocker evidence row.",
            "Propose local repair status only; do not close queue items, write gate receipts, write reviews, authorize the writer, or promote claims.",
        ],
    },
    "writer": {
        "title": "One Writer Report",
        "instructions": [
            "Write one coherent report voice from admitted synthesis, report outline, latest review, claim ledger, and gate state.",
            "Read writer_gate_preflight.json when provided, otherwise read any gate receipt and canonical backpressure queue.",
            "If gate inputs still show open writer-blocking adequacy, write report.md as a blocked-state output rather than a final answer.",
            "Preserve unresolveds, non-claims, and benchmark/scorer blockers.",
            "Do not introduce new facts that lack evidence custody.",
            "Do not claim final-answer success, Grep parity, benchmark score, leaderboard rank, product readiness, official submission readiness, or scorer-backed evaluation unless claim review and scorer receipts permit it.",
        ],
    },
    "scorer_bridge": {
        "title": "Scorer Bridge / Claim Reviewer",
        "instructions": [
            "Prepare scoring inputs and schema only after scorer policy is approved.",
            "Keep sealed references, judge prompts, variance policy, and transcripts explicit.",
            "Never convert a placeholder score into a numeric benchmark claim.",
            "For claim review, inspect receipts and artifacts only; do not infer readiness from validation success.",
            "Distinguish live role custody, structural validation, answer adequacy, writer success, scorer custody, benchmark score, Grep parity, and product readiness.",
        ],
    },
}

PROMPT_AUTHORITY_CLAUSES = {
    "task_plan": [
        {
            "clause_id": "default_authorization_external",
            "text": "default authorization must come from",
        },
        {
            "clause_id": "ratification_blocks_executable_graph",
            "text": "awaiting_ratification",
        },
        {
            "clause_id": "world_knowledge_prior_only",
            "text": "world knowledge as planning prior",
        },
    ],
    "task_deep_search": [
        {
            "clause_id": "source_discovery_not_validation",
            "text": "source discovery as source validation",
        },
        {
            "clause_id": "source_support_limits",
            "text": "what each source supports, what it does not support",
        },
    ],
    "task_data_analysis": [
        {
            "clause_id": "comparability_required_before_ranking",
            "text": "do not rank, compare, forecast, or normalize",
        },
        {
            "clause_id": "non_comparable_inputs_status",
            "text": "non_comparable_inputs",
        },
    ],
    "task_verification": [
        {
            "clause_id": "statement_to_source_support",
            "text": "statement-to-source support",
        },
        {
            "clause_id": "too_broad_for_evidence_status",
            "text": "too_broad_for_evidence",
        },
    ],
    "task_pointer_first_synthesis": [
        {
            "clause_id": "synthesis_not_queue_owner",
            "text": "canonical backpressure queue",
        },
        {
            "clause_id": "adequacy_assessments_surface",
            "text": "adequacy_assessments.jsonl",
        },
    ],
    "task_review": [
        {
            "clause_id": "reviewer_proposes_backpressure",
            "text": "proposed_backpressure_items",
        },
        {
            "clause_id": "reviewer_not_queue_owner",
            "text": "backpressure/adequacy_backpressure_queue.json",
        },
        {
            "clause_id": "reviewer_not_gate_owner",
            "text": "backpressure/backpressure_gate_receipt.json",
        },
    ],
    "task_reentry_followup": [
        {
            "clause_id": "single_task_packet_scope",
            "text": "reentry_task_packet.json",
        },
        {
            "clause_id": "reviewer_adjudicates_closure",
            "text": "reviewer adjudicates closure",
        },
        {
            "clause_id": "citation_support_closure_artifact",
            "text": "citation_support_map.json",
        },
    ],
    "task_reentry_synthesis": [
        {
            "clause_id": "adequacy_delta_output",
            "text": "adequacy_delta.json",
        },
        {
            "clause_id": "narrowed_not_closed",
            "text": "repair_returned`, `narrowed`, and",
        },
        {
            "clause_id": "no_writer_authorization",
            "text": "authorize the writer",
        },
    ],
    "task_final_writer": [
        {
            "clause_id": "writer_gate_preflight",
            "text": "writer_gate_preflight.json",
        },
        {
            "clause_id": "blocked_state_output",
            "text": "blocked-state output rather than a final answer",
        },
        {
            "clause_id": "no_final_success_or_parity_claim",
            "text": "do not claim final-answer success, grep parity",
        },
    ],
}

MESH_REQUIRED_FILES = [
    "run_manifest.json",
    "events.jsonl",
    "artefact_manifest.json",
    "case_manifest.json",
    "plan.md",
    "skills_tools.json",
    "adequacy_criteria.json",
    "task_graph.json",
    "role_configs.json",
    "terminal_agent_boxes.json",
    "pointer_read_receipts.jsonl",
    "adequacy_assessments.jsonl",
    "synthesis.md",
    "contradictions.json",
    "report_outline.md",
    "reviews/review_001.json",
    "reentry_decisions.jsonl",
    "compactions/compaction_001.json",
    "claim_ledger.json",
    "report.md",
    "scorer_manifest.json",
    "benchmark_score.json",
    "evaluation_ledger.json",
    "self_improvement/replay_corpus.json",
    "self_improvement/failure_taxonomy.json",
    "self_improvement/improvement_proposal.json",
    "self_improvement/regression_gate.json",
    "allowed_claims.json",
]

for mesh_branch_id in MESH_ALL_BRANCH_IDS:
    MESH_REQUIRED_FILES.extend(
        [
            f"branches/{mesh_branch_id}/branch_manifest.json",
            f"branches/{mesh_branch_id}/pointer.md",
            f"branches/{mesh_branch_id}/analysis.md",
            f"branches/{mesh_branch_id}/evidence.jsonl",
        ]
    )

MESH_REQUIRED_EVENT_TYPES = [
    *REQUIRED_EVENT_TYPES,
    "role_configs.written",
    "pointer_reads.recorded",
    "scorer_bridge.written",
    "evaluation_ledger.written",
    "self_improvement.replay_written",
    "self_improvement.proposal_written",
    "self_improvement.regression_gate_written",
]

LIVE_MESH_REQUIRED_FILES = [
    "live_executor/run_control_receipt.json",
    "live_executor/execution_summary.json",
    "live_executor/context_thread_index.json",
]

LIVE_MESH_REQUIRED_EVENT_TYPES = [
    "live_executor.run_control_receipt_copied",
    "live_executor.execution_started",
    "live_executor.dependency_batch_started",
    "live_executor.dependency_batch_completed",
    "live_executor.role_completed",
    "live_executor.context_thread_index_written",
    "live_executor.execution_completed",
]

VALIDATOR_NAMES = {
    "branch_triplet_present",
    "mesh_branch_triplets_present",
    "events_required_types_present",
    "orchestrator_state_machine_order_valid",
    "benchmark_case_manifest_sealed",
    "review_reentry_compiled",
    "compaction_receipt_present",
    "benchmark_placeholder_not_score",
    "allowed_claims_scope_enforced",
    "task_graph_dependencies_valid",
    "pointer_first_receipts_present",
}

BLOCKED_ALLOWED_CLAIM_PHRASES = [
    "grep parity",
    "benchmark score",
    "draco score",
    "deepresearch bench score",
    "provider-backed",
    "provider backed",
    "product service readiness",
    "product readiness",
    "leaderboard",
    "official submission",
    "official benchmark submission",
    "scorer-backed evaluation",
    "scorer backed evaluation",
]
REQUIRED_BLOCKED_CLAIMS = [
    "Grep parity",
    "benchmark score",
    "DeepResearch Bench score",
    "DRACO score",
    "leaderboard rank",
    "provider-backed execution",
    "product service readiness",
    "product readiness",
    "official benchmark submission",
    "scorer-backed evaluation",
]


class HarnessError(RuntimeError):
    pass


def run_path(case_id: str, runs_dir: Path | str | None = None) -> Path:
    validate_id(case_id, "case_id")
    return Path(runs_dir or DEFAULT_RUNS_DIR) / case_id


def validate_id(value: str, label: str) -> None:
    if not ID_RE.match(value):
        raise HarnessError(f"{label} must match {ID_RE.pattern}: {value!r}")


def validate_model_name(value: str) -> None:
    if not MODEL_RE.match(value):
        raise HarnessError(f"model must match {MODEL_RE.pattern}: {value!r}")


def safe_model_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._:-]+", "_", value).strip("_").replace(":", "_")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def topologically_order_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {task["task_id"]: task for task in tasks}
    ordered: list[dict[str, Any]] = []
    completed: set[str] = set()
    pending = [task["task_id"] for task in tasks]
    while pending:
        progressed = False
        for task_id in list(pending):
            task = by_id[task_id]
            dependencies = task.get("depends_on", [])
            missing = [dependency for dependency in dependencies if dependency not in by_id]
            if missing:
                raise HarnessError(
                    f"{task_id} depends on missing task(s): {', '.join(missing)}"
                )
            if all(dependency in completed for dependency in dependencies):
                ordered.append(task)
                completed.add(task_id)
                pending.remove(task_id)
                progressed = True
        if not progressed:
            raise HarnessError(
                "task graph contains a dependency cycle or unsatisfied dependency among: "
                + ", ".join(pending)
            )
    return ordered


def path_is_within(path: Path, root: Path) -> bool:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    return resolved_path == resolved_root or resolved_root in resolved_path.parents


def resolve_run_relative_path(run_dir: Path, relative_path: str, label: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute():
        raise HarnessError(f"{label} must be relative to the run bundle: {relative_path}")
    resolved = (run_dir / path).resolve()
    if not path_is_within(resolved, run_dir):
        raise HarnessError(f"{label} escapes the run bundle: {relative_path}")
    return resolved


def is_web_ref(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def reference_exists(run_dir: Path, ref: str) -> bool:
    ref_path = ref.split("#", 1)[0]
    if not ref_path:
        return False
    if is_web_ref(ref_path):
        return True
    try:
        resolved = resolve_run_relative_path(run_dir, ref_path, "reference")
    except HarnessError:
        return False
    return resolved.exists()


def run_mode(run_dir: Path) -> str:
    try:
        return str(read_json(run_dir / "run_manifest.json").get("mode", "provider_off_bootstrap"))
    except (FileNotFoundError, json.JSONDecodeError):
        return "unknown"


def is_mesh_run(run_dir: Path) -> bool:
    return run_mode(run_dir) in {"provider_off_dr_mesh", "live_dr_mesh_smoke"}


def is_live_mesh_run(run_dir: Path) -> bool:
    return (run_dir / "live_executor" / "execution_summary.json").exists()


def live_execution_status(run_dir: Path) -> str | None:
    if not is_live_mesh_run(run_dir):
        return None
    try:
        summary = read_json(run_dir / "live_executor" / "execution_summary.json")
        return str(summary.get("execution_status"))
    except (FileNotFoundError, json.JSONDecodeError):
        return "unknown"


def is_live_mesh_blocked_by_adequacy(run_dir: Path) -> bool:
    return live_execution_status(run_dir) == "blocked_by_adequacy_backpressure"


def required_files_for_run(run_dir: Path) -> list[str]:
    if is_mesh_run(run_dir):
        required = [*MESH_REQUIRED_FILES]
        if is_live_mesh_run(run_dir):
            required.extend(LIVE_MESH_REQUIRED_FILES)
        return required
    return REQUIRED_FILES


def required_event_types_for_run(run_dir: Path) -> list[str]:
    if is_mesh_run(run_dir):
        required = [*MESH_REQUIRED_EVENT_TYPES]
        if is_live_mesh_run(run_dir):
            if is_live_mesh_blocked_by_adequacy(run_dir):
                required.extend(
                    event_type
                    for event_type in LIVE_MESH_REQUIRED_EVENT_TYPES
                    if event_type != "live_executor.execution_completed"
                )
                required.append("live_executor.dependency_batch_blocked")
            else:
                required.extend(LIVE_MESH_REQUIRED_EVENT_TYPES)
        return required
    return REQUIRED_EVENT_TYPES


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(SANDBOX_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def event_outputs(run_dir: Path) -> dict[str, dict[str, Any]]:
    output_map: dict[str, dict[str, Any]] = {}
    for event in read_jsonl(run_dir / "events.jsonl"):
        for output in event.get("outputs", []):
            output_map[output] = event
    return output_map


def append_event(
    run_dir: Path,
    *,
    event_id: str,
    event_type: str,
    outputs: list[str],
    inputs: list[str] | None = None,
    causally_after: list[str] | None = None,
    decision: dict[str, Any] | None = None,
    summary: str,
    replace_existing: bool = False,
) -> None:
    with EVENT_WRITE_LOCK:
        events_path = run_dir / "events.jsonl"
        events = read_jsonl(events_path)
        existing_index = next(
            (index for index, event in enumerate(events) if event["event_id"] == event_id),
            None,
        )
        if existing_index is not None and not replace_existing:
            return
        if causally_after is None:
            if existing_index is not None:
                causally_after = events[existing_index].get("causally_after", [])
            else:
                causally_after = [events[-1]["event_id"]] if events else []
        event = {
            "schema_version": "codex-dr.event.v1",
            "event_id": event_id,
            "run_id": run_dir.name,
            "timestamp": FIXTURE_TIMESTAMP,
            "actor": "bootstrap_harness",
            "event_type": event_type,
            "causally_after": causally_after,
            "inputs": inputs or [],
            "outputs": outputs,
            "decision": decision,
            "summary": summary,
        }
        if existing_index is None:
            events.append(event)
        else:
            events[existing_index] = event
        write_jsonl(events_path, events)


def update_manifest_status(run_dir: Path, status: str) -> None:
    manifest_path = run_dir / "run_manifest.json"
    manifest = read_json(manifest_path)
    manifest["status"] = status
    write_json(manifest_path, manifest)


def artifact_role(path: str) -> str:
    if path.startswith("branches/"):
        return "branch_return"
    if path.startswith("reviews/"):
        return "review"
    if path.startswith("compactions/"):
        return "compaction_receipt"
    return Path(path).stem


def artifact_id(path: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", path).strip("_").lower()
    return f"art_{safe}"


def refresh_artifact_manifest(run_dir: Path) -> None:
    outputs = event_outputs(run_dir)
    events = read_jsonl(run_dir / "events.jsonl")
    last_event = events[-1] if events else None
    artifacts = []
    for path in sorted(p for p in run_dir.rglob("*") if p.is_file()):
        relative = rel(path, run_dir)
        if relative in {"artefact_manifest.json", "validation_report.json"}:
            continue
        event = outputs.get(relative)
        produced_by_event = event["event_id"] if event else None
        source_event_ids = event.get("causally_after", []) if event else []
        if relative == "events.jsonl" and last_event:
            produced_by_event = last_event["event_id"]
            source_event_ids = [event_row["event_id"] for event_row in events[:-1]]
        artifacts.append(
            {
                "artifact_id": artifact_id(relative),
                "path": relative,
                "role": artifact_role(relative),
                "content_type": content_type(relative),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "produced_by_event": produced_by_event,
                "source_event_ids": source_event_ids,
                "claim_support_allowed": relative != "benchmark_score.json",
            }
        )
    write_json(
        run_dir / "artefact_manifest.json",
        {
            "schema_version": "codex-dr.artefact_manifest.v1",
            "run_id": run_dir.name,
            "hash_algorithm": "sha256",
            "artifacts": artifacts,
        },
    )


def content_type(path: str) -> str:
    if path.endswith(".md"):
        return "text/markdown"
    if path.endswith(".json"):
        return "application/json"
    if path.endswith(".jsonl"):
        return "application/jsonl"
    return "application/octet-stream"


def init_case(case_id: str, *, runs_dir: Path | str | None = None, force: bool = False) -> Path:
    run_dir = run_path(case_id, runs_dir)
    if run_dir.exists() and force:
        shutil.rmtree(run_dir)
    if run_dir.exists() and any(run_dir.iterdir()):
        raise HarnessError(f"run already exists: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        run_dir / "run_manifest.json",
        {
            "schema_version": "codex-dr.run_manifest.v1",
            "run_id": case_id,
            "case_id": case_id,
            "mode": "provider_off_bootstrap",
            "created_at": FIXTURE_TIMESTAMP,
            "authority": {
                "bootstrap_doctrine": "sandbox/codex-dr/docs/BOOTSTRAP_DOCTRINE.md",
                "parity_contract": "sandbox/codex-dr/harness-specs/grep_parity_contract.md",
                "harness_contracts": "sandbox/codex-dr/harness-specs/harness_contracts.md",
            },
            "provider_calls_allowed": False,
            "benchmark_execution_allowed": False,
            "generated_under_ignored_path": True,
            "status": "initialized",
        },
    )
    append_event(
        run_dir,
        event_id="evt_0001_init_case",
        event_type="case.initialized",
        outputs=["run_manifest.json"],
        causally_after=[],
        summary="Initialized provider-off run bundle.",
    )
    refresh_artifact_manifest(run_dir)
    return run_dir


def bootstrap_plan(case_id: str, *, runs_dir: Path | str | None = None) -> Path:
    run_dir = run_path(case_id, runs_dir)
    plan = """# Plan

## Objective
Create a deterministic provider-off fixture that proves the harness can emit and validate
custody artifacts before any provider-backed run.

## Assumptions
- No model, provider, terminal-agent, network, or benchmark execution is allowed.
- The fixture exercises the same artifact semantics that future runs must preserve.

## Adequacy Criteria
- The run emits a branch pointer / analysis / evidence triplet.
- A reviewer finding compiles into a re-entry task.
- The final report has claim-ledger support and explicit non-claims.

## Source Policy
Only local deterministic fixture material is admissible.

## Task Graph Summary
Plan, branch, review, re-entry, synthesize, report, and validate.

## Review Checklist
- Does a finding require research re-entry?
- Are material claims present in the claim ledger?
- Does the benchmark score remain a placeholder?

## Non-Claims
No benchmark score, Grep parity, provider-backed execution, or product service readiness.
"""
    write_text(run_dir / "plan.md", plan)
    write_json(
        run_dir / "adequacy_criteria.json",
        {
            "schema_version": "codex-dr.adequacy_criteria.v1",
            "run_id": case_id,
            "criteria": [
                {
                    "criterion_id": "adequacy_evidence_triplet",
                    "description": "Each branch must return pointer, analysis, and evidence files.",
                    "required": True,
                    "validator": "branch_triplet_present",
                },
                {
                    "criterion_id": "adequacy_review_reentry",
                    "description": "A qualifying review finding must compile into a re-entry task.",
                    "required": True,
                    "validator": "review_reentry_compiled",
                },
            ],
            "produced_by_event": "evt_0002_plan_written",
        },
    )
    task_graph = {
        "schema_version": "codex-dr.task_graph.v1",
        "run_id": case_id,
        "tasks": [
            {
                "task_id": "task_plan",
                "kind": "planning",
                "objective": "Write deterministic provider-off plan artifacts.",
                "depends_on": [],
                "status": "completed",
                "assigned_box_id": "planner_box",
                "expected_outputs": [
                    "plan.md",
                    "adequacy_criteria.json",
                    "task_graph.json",
                ],
                "source_review_finding_id": None,
            },
            {
                "task_id": "task_branch_a",
                "kind": "branch_research",
                "objective": "Produce deterministic bootstrap evidence triplet.",
                "depends_on": ["task_plan"],
                "status": "pending",
                "assigned_box_id": "branch_box_a",
                "expected_outputs": [
                    "branches/branch_a/pointer.md",
                    "branches/branch_a/analysis.md",
                    "branches/branch_a/evidence.jsonl",
                ],
                "source_review_finding_id": None,
            },
        ],
        "produced_by_event": "evt_0003_task_graph_written",
    }
    write_json(run_dir / "task_graph.json", task_graph)
    write_json(
        run_dir / "terminal_agent_boxes.json",
        {
            "schema_version": "codex-dr.terminal_agent_boxes.v1",
            "run_id": case_id,
            "boxes": [
                {
                    "box_id": "planner_box",
                    "role": "planner",
                    "mode": "provider_off_placeholder",
                    "cwd": "branches/planner_box",
                    "skills": [],
                    "allowed_tools": [],
                    "disallowed_tools": ["provider_calls", "network", "benchmark_execution"],
                    "mcp_servers": [],
                    "model": None,
                    "session_lineage": None,
                    "cleanup_policy": "preserve_for_bootstrap",
                    "output_contract": ["plan.md", "adequacy_criteria.json", "task_graph.json"],
                    "produced_by_event": "evt_0004_agent_box_placeholder",
                },
                {
                    "box_id": "branch_box_a",
                    "role": "branch_researcher",
                    "mode": "provider_off_placeholder",
                    "cwd": "branches/branch_a",
                    "skills": [],
                    "allowed_tools": [],
                    "disallowed_tools": ["provider_calls", "network", "benchmark_execution"],
                    "mcp_servers": [],
                    "model": None,
                    "session_lineage": None,
                    "cleanup_policy": "preserve_for_bootstrap",
                    "output_contract": [
                        "branches/branch_a/pointer.md",
                        "branches/branch_a/analysis.md",
                        "branches/branch_a/evidence.jsonl",
                    ],
                    "produced_by_event": "evt_0004_agent_box_placeholder",
                },
            ],
        },
    )
    append_event(
        run_dir,
        event_id="evt_0002_plan_written",
        event_type="plan.written",
        outputs=["plan.md", "adequacy_criteria.json"],
        summary="Wrote provider-off plan and adequacy criteria.",
    )
    append_event(
        run_dir,
        event_id="evt_0003_task_graph_written",
        event_type="task_graph.written",
        outputs=["task_graph.json"],
        summary="Wrote deterministic task graph.",
    )
    append_event(
        run_dir,
        event_id="evt_0004_agent_box_placeholder",
        event_type="agent_box.placeholder_written",
        outputs=["terminal_agent_boxes.json"],
        summary="Wrote provider-off terminal-agent box placeholders.",
    )
    update_manifest_status(run_dir, "planned")
    refresh_artifact_manifest(run_dir)
    return run_dir


def bootstrap_branch(
    case_id: str,
    branch_id: str = "branch_a",
    *,
    runs_dir: Path | str | None = None,
) -> Path:
    validate_id(branch_id, "branch_id")
    run_dir = run_path(case_id, runs_dir)
    branch_dir = run_dir / "branches" / branch_id
    write_json(
        branch_dir / "branch_manifest.json",
        {
            "schema_version": "codex-dr.branch_manifest.v1",
            "run_id": case_id,
            "branch_id": branch_id,
            "task_id": f"task_{branch_id}",
            "objective": "Produce deterministic bootstrap evidence triplet.",
            "mode": "provider_off_fixture",
            "outputs": {
                "pointer": f"branches/{branch_id}/pointer.md",
                "analysis": f"branches/{branch_id}/analysis.md",
                "evidence": f"branches/{branch_id}/evidence.jsonl",
            },
            "produced_by_event": "evt_0006_branch_return_written",
        },
    )
    write_text(
        branch_dir / "pointer.md",
        """# Branch Pointer

## Objective
Produce deterministic bootstrap evidence for the provider-off harness.

## Key Findings
- The fixture branch writes pointer, analysis, and evidence files.
- The branch carries no real-world benchmark or provider claim.

## Evidence Map
- `ev_branch_a_001` supports the branch-return custody claim.

## Read Next
Read `analysis.md` only after this pointer.
""",
    )
    write_text(
        branch_dir / "analysis.md",
        """# Branch Analysis

This provider-off analysis is deterministic fixture material. It proves only that the
harness can preserve branch-return shape before provider-backed research exists.
""",
    )
    write_jsonl(
        branch_dir / "evidence.jsonl",
        [
            {
                "schema_version": "codex-dr.evidence_item.v1",
                "evidence_id": "ev_branch_a_001",
                "run_id": case_id,
                "branch_id": branch_id,
                "source_type": "local_fixture",
                "source_ref": "provider-off deterministic fixture",
                "supports": ["claim_bootstrap_bundle_has_branch_return"],
                "quote_or_summary": (
                    "The branch return contains pointer, analysis, and evidence files."
                ),
                "admission_status": "admitted",
                "produced_by_event": "evt_0006_branch_return_written",
            }
        ],
    )
    append_event(
        run_dir,
        event_id="evt_0005_branch_spawn_declared",
        event_type="branch.spawn_declared",
        outputs=[f"branches/{branch_id}/branch_manifest.json"],
        decision={
            "decision_id": "dec_0001_spawn_branch",
            "decision_type": "spawn_branch",
            "rationale": "Bootstrap requires one deterministic branch return.",
            "status": "accepted",
        },
        summary="Declared provider-off branch spawn.",
    )
    append_event(
        run_dir,
        event_id="evt_0006_branch_return_written",
        event_type="branch.return_written",
        outputs=[
            f"branches/{branch_id}/pointer.md",
            f"branches/{branch_id}/analysis.md",
            f"branches/{branch_id}/evidence.jsonl",
        ],
        summary="Wrote provider-off branch return triplet.",
    )
    write_jsonl(
        run_dir / "adequacy_assessments.jsonl",
        [
            {
                "schema_version": "codex-dr.adequacy_assessment.v1",
                "run_id": case_id,
                "assessment_id": "adequacy_001",
                "criteria_checked": ["adequacy_evidence_triplet"],
                "branch_ids": [branch_id],
                "status": "needs_review",
                "gaps": [],
                "decision_event_id": "evt_0007_adequacy_assessed",
                "produced_by_event": "evt_0007_adequacy_assessed",
            }
        ],
    )
    append_event(
        run_dir,
        event_id="evt_0007_adequacy_assessed",
        event_type="adequacy.assessed",
        outputs=["adequacy_assessments.jsonl"],
        decision={
            "decision_id": "dec_0002_assess_adequacy",
            "decision_type": "deepen",
            "rationale": "Bootstrap should continue to review and re-entry validation.",
            "status": "accepted",
        },
        summary="Assessed branch adequacy for bootstrap.",
    )
    mark_task(run_dir, f"task_{branch_id}", "completed")
    update_manifest_status(run_dir, "branched")
    refresh_artifact_manifest(run_dir)
    return run_dir


def bootstrap_review(case_id: str, *, runs_dir: Path | str | None = None) -> Path:
    run_dir = run_path(case_id, runs_dir)
    write_json(
        run_dir / "reviews" / "review_001.json",
        {
            "schema_version": "codex-dr.review.v1",
            "run_id": case_id,
            "review_id": "review_001",
            "reviewer_role": "bootstrap_reviewer",
            "target_artifacts": ["branches/branch_a/pointer.md", "adequacy_assessments.jsonl"],
            "findings": [
                {
                    "finding_id": "finding_reentry_001",
                    "severity": "major",
                    "finding_type": "thin_evidence",
                    "summary": "Bootstrap requires one reviewer-driven re-entry task.",
                    "evidence_refs": ["branches/branch_a/evidence.jsonl#ev_branch_a_001"],
                    "requires_reentry": True,
                    "recommended_task": "Add deterministic follow-up task for review pressure.",
                }
            ],
            "produced_by_event": "evt_0008_review_written",
        },
    )
    append_event(
        run_dir,
        event_id="evt_0008_review_written",
        event_type="review.written",
        outputs=["reviews/review_001.json"],
        summary="Wrote provider-off review finding that requires re-entry.",
    )
    update_manifest_status(run_dir, "reviewed")
    refresh_artifact_manifest(run_dir)
    return run_dir


def bootstrap_reentry(
    case_id: str,
    review_id: str = "review_001",
    *,
    runs_dir: Path | str | None = None,
) -> Path:
    run_dir = run_path(case_id, runs_dir)
    review = read_json(run_dir / "reviews" / f"{review_id}.json")
    finding = next(f for f in review["findings"] if f["requires_reentry"])
    task = {
        "task_id": "task_reentry_001",
        "kind": "reentry_research",
        "objective": finding["recommended_task"],
        "depends_on": ["task_branch_a"],
        "status": "completed",
        "assigned_box_id": "branch_box_a",
        "expected_outputs": ["reentry_decisions.jsonl"],
        "source_review_finding_id": finding["finding_id"],
    }
    graph_path = run_dir / "task_graph.json"
    graph = read_json(graph_path)
    if not any(existing["task_id"] == task["task_id"] for existing in graph["tasks"]):
        graph["tasks"].append(task)
    write_json(graph_path, graph)
    write_jsonl(
        run_dir / "reentry_decisions.jsonl",
        [
            {
                "schema_version": "codex-dr.reentry_decision.v1",
                "run_id": case_id,
                "decision_id": "reentry_001",
                "review_id": review_id,
                "finding_id": finding["finding_id"],
                "decision": "create_task",
                "rationale": "Major finding requires research-state change, not prose patching.",
                "created_task_id": "task_reentry_001",
                "task_graph_path": "task_graph.json",
                "produced_by_event": "evt_0009_reentry_compiled",
            }
        ],
    )
    append_event(
        run_dir,
        event_id="evt_0009_reentry_compiled",
        event_type="reentry.compiled",
        inputs=[f"reviews/{review_id}.json"],
        outputs=["reentry_decisions.jsonl", "task_graph.json"],
        decision={
            "decision_id": "dec_0003_reenter",
            "decision_type": "reenter",
            "rationale": "Review finding requires one targeted follow-up task.",
            "status": "accepted",
        },
        summary="Compiled review finding into deterministic re-entry task.",
    )
    update_manifest_status(run_dir, "reentered")
    refresh_artifact_manifest(run_dir)
    return run_dir


def bootstrap_report(case_id: str, *, runs_dir: Path | str | None = None) -> Path:
    run_dir = run_path(case_id, runs_dir)
    write_text(
        run_dir / "synthesis.md",
        """# Synthesis

## Admitted Evidence
- `ev_branch_a_001` supports that the fixture contains a branch return triplet.

## Contradictions
No real-world contradiction is asserted by this provider-off fixture.

## Unresolveds
Provider-backed and benchmark claims remain blocked.

## Claims Ready For Ledger
- The provider-off fixture includes a branch return triplet.

## Review Impact
The review finding compiled into `task_reentry_001`.
""",
    )
    write_json(
        run_dir / "contradictions.json",
        {
            "schema_version": "codex-dr.contradictions.v1",
            "run_id": case_id,
            "contradictions": [
                {
                    "contradiction_id": "contradiction_none_001",
                    "issue": "No real contradiction in provider-off fixture.",
                    "positions": [],
                    "adjudication_status": "not_applicable",
                    "unresolved": False,
                    "report_treatment": (
                        "State that provider-off fixture carries no real-world contradiction claim."
                    ),
                }
            ],
            "produced_by_event": "evt_0010_synthesis_written",
        },
    )
    write_text(
        run_dir / "report_outline.md",
        """# Report Outline

1. Scope
2. What ran
3. Evidence
4. Review re-entry
5. Claim boundary
6. Non-claims
""",
    )
    append_event(
        run_dir,
        event_id="evt_0010_synthesis_written",
        event_type="synthesis.written",
        outputs=["synthesis.md", "contradictions.json", "report_outline.md"],
        summary="Wrote provider-off synthesis, contradictions, and report outline.",
    )
    write_json(
        run_dir / "compactions" / "compaction_001.json",
        {
            "schema_version": "codex-dr.compaction_receipt.v1",
            "run_id": case_id,
            "compaction_id": "compaction_001",
            "mode": "provider_off_fixture",
            "input_artifacts": ["plan.md", "branches/branch_a/pointer.md", "synthesis.md"],
            "output_artifact": "compactions/compaction_001.json",
            "scope": "bootstrap state summary",
            "claim_impact": "no claim widening",
            "produced_by_event": "evt_0011_compaction_receipt_written",
        },
    )
    append_event(
        run_dir,
        event_id="evt_0011_compaction_receipt_written",
        event_type="compaction.receipt_written",
        outputs=["compactions/compaction_001.json"],
        summary="Wrote provider-off compaction receipt.",
    )
    write_json(
        run_dir / "claim_ledger.json",
        {
            "schema_version": "codex-dr.claim_ledger.v1",
            "run_id": case_id,
            "claims": [
                {
                    "claim_id": "claim_bootstrap_bundle_has_branch_return",
                    "text": "The provider-off fixture includes a branch return triplet.",
                    "materiality": "bootstrap",
                    "status": "admitted",
                    "source_artifact_refs": ["branches/branch_a/evidence.jsonl#ev_branch_a_001"],
                    "intermediate_artifact_refs": [
                        "branches/branch_a/pointer.md",
                        "synthesis.md",
                    ],
                    "blocked_from_public_claims": False,
                }
            ],
            "produced_by_event": "evt_0012_claim_ledger_written",
        },
    )
    append_event(
        run_dir,
        event_id="evt_0012_claim_ledger_written",
        event_type="claim_ledger.written",
        outputs=["claim_ledger.json"],
        summary="Wrote provider-off claim ledger.",
    )
    write_json(
        run_dir / "allowed_claims.json",
        {
            "schema_version": "codex-dr.allowed_claims.v1",
            "run_id": case_id,
            "allowed_claims": [
                {
                    "claim": (
                        "The provider-off bootstrap harness emitted and validated a "
                        "deterministic local fixture run bundle."
                    ),
                    "scope": "local_fixture_only",
                    "supporting_artifacts": ["validation_report.json", "claim_ledger.json"],
                }
            ],
            "blocked_claims": REQUIRED_BLOCKED_CLAIMS,
            "produced_by_event": "evt_0013_allowed_claims_written",
        },
    )
    append_event(
        run_dir,
        event_id="evt_0013_allowed_claims_written",
        event_type="allowed_claims.written",
        outputs=["allowed_claims.json"],
        summary="Wrote provider-off allowed claims.",
    )
    write_text(
        run_dir / "report.md",
        """# Provider-Off Bootstrap Report

## Scope
This deterministic local fixture exercises provider-off custody and validation only.

## What Ran
The bootstrap wrote plan, task graph, branch return, review, re-entry, synthesis,
claim ledger, compaction receipt, benchmark placeholder, and allowed-claims artifacts.

## Evidence
The provider-off fixture includes a branch return triplet.

## Review Re-Entry
The review finding compiled into `task_reentry_001`.

## Claim Boundary
The run supports only provider-off fixture validation claims.

## Non-Claims
- No benchmark score.
- No Grep parity.
- No provider-backed execution.
- No product service readiness.
""",
    )
    append_event(
        run_dir,
        event_id="evt_0014_report_written",
        event_type="report.written",
        outputs=["report.md"],
        summary="Wrote provider-off report.",
    )
    write_json(
        run_dir / "benchmark_score.json",
        {
            "schema_version": "codex-dr.benchmark_score.v1",
            "run_id": case_id,
            "mode": "provider_off_placeholder",
            "benchmark_family": None,
            "case_manifest": None,
            "scorer_manifest": None,
            "score": None,
            "claims_enabled": False,
            "reason": (
                "Benchmark execution is blocked until provider-off bootstrap, case "
                "manifest, scorer manifest, and run-control gates pass."
            ),
            "produced_by_event": "evt_0015_benchmark_placeholder_written",
        },
    )
    append_event(
        run_dir,
        event_id="evt_0015_benchmark_placeholder_written",
        event_type="benchmark.placeholder_written",
        outputs=["benchmark_score.json"],
        summary="Wrote provider-off benchmark placeholder.",
    )
    update_manifest_status(run_dir, "reported")
    refresh_artifact_manifest(run_dir)
    return run_dir


def mark_task(run_dir: Path, task_id: str, status: str) -> None:
    graph_path = run_dir / "task_graph.json"
    if not graph_path.exists():
        return
    graph = read_json(graph_path)
    for task in graph["tasks"]:
        if task["task_id"] == task_id:
            task["status"] = status
    write_json(graph_path, graph)


def bootstrap_run(case_id: str, *, runs_dir: Path | str | None = None) -> Path:
    run_dir = init_case(case_id, runs_dir=runs_dir, force=True)
    bootstrap_plan(case_id, runs_dir=runs_dir)
    bootstrap_branch(case_id, "branch_a", runs_dir=runs_dir)
    bootstrap_review(case_id, runs_dir=runs_dir)
    bootstrap_reentry(case_id, "review_001", runs_dir=runs_dir)
    bootstrap_report(case_id, runs_dir=runs_dir)
    return run_dir


def mesh_init_case(
    case_id: str, *, runs_dir: Path | str | None = None, force: bool = False
) -> Path:
    run_dir = run_path(case_id, runs_dir)
    if run_dir.exists() and force:
        shutil.rmtree(run_dir)
    if run_dir.exists() and any(run_dir.iterdir()):
        raise HarnessError(f"run already exists: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        run_dir / "run_manifest.json",
        {
            "schema_version": "codex-dr.run_manifest.v1",
            "run_id": case_id,
            "case_id": case_id,
            "mode": "provider_off_dr_mesh",
            "created_at": FIXTURE_TIMESTAMP,
            "authority": {
                "dr_mesh_parity_charter": (
                    "sandbox/codex-dr/harness-specs/dr_mesh_parity_charter.md"
                ),
                "run_control_halt": "sandbox/codex-dr/docs/codex_exec_halt_2026_04_22.md",
            },
            "provider_calls_allowed": False,
            "codex_exec_allowed": False,
            "benchmark_execution_allowed": False,
            "generated_under_ignored_path": True,
            "status": "initialized",
        },
    )
    append_event(
        run_dir,
        event_id="evt_0001_init_case",
        event_type="case.initialized",
        outputs=["run_manifest.json"],
        causally_after=[],
        summary="Initialized provider-off DR mesh run bundle.",
    )
    refresh_artifact_manifest(run_dir)
    return run_dir


def build_case_manifest_payload(
    *,
    run_id: str,
    case_index: int,
    case_spec: dict[str, Any] | None = None,
    manifest_source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    case_spec = case_spec or {}
    source = {**DEFAULT_DRACO_DATASET_SOURCE, **(manifest_source or {})}
    source.update(case_spec.get("source", {}))
    benchmark_family = (
        case_spec.get("benchmark_family")
        or source.get("benchmark_family")
        or BENCHMARK_FAMILY_DRACO
    )
    if benchmark_family not in SUPPORTED_CASE_MANIFEST_FAMILIES:
        raise HarnessError(f"unsupported benchmark_family: {benchmark_family}")
    source["benchmark_family"] = benchmark_family
    row_indices = case_spec.get("row_indices", source.get("row_indices", [case_index]))
    if not isinstance(row_indices, list) or not row_indices:
        raise HarnessError("case row_indices must be a non-empty list")
    if not all(isinstance(index, int) and index >= 0 for index in row_indices):
        raise HarnessError("case row_indices must contain non-negative integers")
    source["row_indices"] = row_indices
    missing_source = [field for field in CASE_SOURCE_REQUIRED_FIELDS if not source.get(field)]
    if missing_source:
        raise HarnessError(f"case source missing fields: {', '.join(missing_source)}")
    default_case_prefix = (
        "draco_test_row"
        if benchmark_family == BENCHMARK_FAMILY_DRACO
        else "deepresearch_bench_query"
    )
    case_id = case_spec.get("case_id") or f"{default_case_prefix}_{case_index:03d}"
    validate_id(case_id, "case_spec.case_id")
    default_question = (
        "What evidence is needed to answer the tiny DRACO-shaped smoke case?"
        if benchmark_family == BENCHMARK_FAMILY_DRACO
        else "What research report should be generated for this DeepResearch Bench task?"
    )
    default_pointer = (
        f"DRACO test row {row_indices[0]} pointer only; raw row not committed."
        if benchmark_family == BENCHMARK_FAMILY_DRACO
        else (
            f"DeepResearch Bench query row {row_indices[0]} pointer only; "
            "scorer references are sealed."
        )
    )
    default_source_policy = (
        "Use only deterministic local fixture facts; no benchmark execution."
        if benchmark_family == BENCHMARK_FAMILY_DRACO
        else (
            "Use the benchmark prompt and permitted public sources; do not read "
            "reference articles, criteria, scorer rubrics, or judge-only files."
        )
    )
    generator_visible = {
        "question": default_question,
        "case_pointer": default_pointer,
        "allowed_context": [
            "case source metadata",
            "local run-bundle artifacts",
            "public sources allowed by run control",
        ],
        "source_policy": default_source_policy,
    }
    generator_visible.update(case_spec.get("generator_visible", {}))
    sealed_scorer_only = {
        "reference_answer": {
            "visibility": "scorer_only",
            "payload_status": "not_materialized_in_git",
            "generator_visible": False,
        },
        "rubric": {
            "visibility": "scorer_only",
            "payload_status": "not_materialized_in_git",
            "generator_visible": False,
            "rubric_axes": [
                *(
                    [
                        "factual_accuracy",
                        "breadth_depth",
                        "presentation_quality",
                        "citation_quality",
                    ]
                    if benchmark_family == BENCHMARK_FAMILY_DRACO
                    else [
                        "comprehensiveness",
                        "insight_depth",
                        "instruction_following",
                        "readability",
                    ]
                ),
            ],
        },
    }
    sealed_scorer_only.update(case_spec.get("sealed_scorer_only", {}))
    return {
        "schema_version": "codex-dr.case_manifest.v1",
        "run_id": run_id,
        "benchmark_family": benchmark_family,
        "case_id": case_id,
        "case_count": 1,
        "raw_data_in_git": False,
        "execution_mode": "provider_off_fixture",
        "source": source,
        "generator_visible": generator_visible,
        "sealed_scorer_only": sealed_scorer_only,
        "leakage_policy": {
            "reference_answers_visible_to_generator": False,
            "rubric_payload_visible_to_generator": False,
            "fail_closed_on_generator_leak": True,
        },
        "question": (
            generator_visible.get("question")
            or f"What evidence is needed to answer benchmark case {case_id}?"
        ),
        "source_policy": generator_visible.get(
            "source_policy",
            default_source_policy,
        ),
        "produced_by_event": "evt_0002_plan_written",
    }


def read_case_spec_manifest(manifest_path: Path) -> dict[str, Any]:
    try:
        manifest = read_json(manifest_path)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        raise HarnessError(f"case spec manifest unavailable: {error}") from error
    if manifest.get("schema_version") != "codex-dr.case_spec_manifest.v1":
        raise HarnessError("case spec manifest schema_version is invalid")
    benchmark_family = manifest.get("benchmark_family")
    if benchmark_family not in SUPPORTED_CASE_MANIFEST_FAMILIES:
        raise HarnessError(
            "case spec manifest benchmark_family must be one of: "
            + ", ".join(sorted(SUPPORTED_CASE_MANIFEST_FAMILIES))
        )
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise HarnessError("case spec manifest must contain at least one case")
    source = manifest.get("source", {})
    missing_source = [
        field
        for field in CASE_SOURCE_REQUIRED_FIELDS
        if field != "row_indices" and not source.get(field)
    ]
    if missing_source:
        raise HarnessError(f"case spec source missing fields: {', '.join(missing_source)}")
    case_ids: set[str] = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise HarnessError(f"case spec at index {index} must be an object")
        case_id = case.get("case_id")
        if case_id:
            validate_id(case_id, f"cases[{index}].case_id")
            if case_id in case_ids:
                raise HarnessError(f"duplicate case_id in case spec manifest: {case_id}")
            case_ids.add(case_id)
        row_indices = case.get("row_indices")
        if not isinstance(row_indices, list) or not row_indices:
            raise HarnessError(f"cases[{index}].row_indices must be a non-empty list")
        if not all(isinstance(row, int) and row >= 0 for row in row_indices):
            raise HarnessError(f"cases[{index}].row_indices must be non-negative integers")
    return manifest


def parse_row_indices(value: str | None, *, row_count: int) -> list[int]:
    if value is None or value.strip() == "":
        return list(range(row_count))
    row_indices = []
    for raw_item in value.split(","):
        item = raw_item.strip()
        if not item:
            continue
        try:
            row_index = int(item)
        except ValueError as error:
            raise HarnessError(f"row index is not an integer: {item}") from error
        if row_index < 0:
            raise HarnessError("row indices must be non-negative")
        row_indices.append(row_index)
    if not row_indices:
        raise HarnessError("at least one row index is required")
    return row_indices


def deepresearch_bench_case_manifest(
    *,
    query_jsonl: Path,
    source_refresh: Path,
    output: Path,
    row_indices: str | None = None,
    limit: int | None = None,
) -> Path:
    refresh = read_json(source_refresh)
    repo = refresh.get("official_repository", {})
    dataset = refresh.get("official_dataset", {})
    query_rows = read_jsonl(query_jsonl)
    selected_indices = parse_row_indices(row_indices, row_count=len(query_rows))
    if limit is not None:
        if limit < 1:
            raise HarnessError("--limit must be positive")
        selected_indices = selected_indices[:limit]
    if not selected_indices:
        raise HarnessError("DeepResearch Bench manifest selection is empty")
    if max(selected_indices) >= len(query_rows):
        raise HarnessError("row index exceeds query file length")

    cases = []
    for row_index in selected_indices:
        row = query_rows[row_index]
        prompt = row.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise HarnessError(f"row {row_index} is missing prompt")
        prompt_id = row.get("id", row_index + 1)
        try:
            prompt_id_int = int(prompt_id)
        except (TypeError, ValueError) as error:
            raise HarnessError(f"row {row_index} has invalid id: {prompt_id}") from error
        case_id = f"deepresearch_bench_query_{prompt_id_int:03d}"
        cases.append(
            {
                "case_id": case_id,
                "benchmark_family": BENCHMARK_FAMILY_DEEPRESEARCH_BENCH,
                "row_indices": [row_index],
                "generator_visible": {
                    "question": prompt,
                    "benchmark_prompt_id": prompt_id_int,
                    "topic": row.get("topic"),
                    "language": row.get("language"),
                    "case_pointer": (
                        "DeepResearch Bench prompt row "
                        f"{row_index}; reference article and criteria are scorer-only."
                    ),
                    "allowed_context": [
                        "benchmark prompt",
                        "case source metadata",
                        "local run-bundle artifacts",
                        "public sources allowed by run control",
                    ],
                    "source_policy": (
                        "Use the benchmark prompt and permitted public sources. "
                        "Do not read reference articles, criteria, scorer rubrics, "
                        "or judge-only files."
                    ),
                },
                "sealed_scorer_only": {
                    "reference_answer": {
                        "visibility": "scorer_only",
                        "payload_status": "not_materialized_in_git",
                        "generator_visible": False,
                        "source_file": "data/test_data/raw_data/reference.jsonl",
                        "row_index": row_index,
                    },
                    "rubric": {
                        "visibility": "scorer_only",
                        "payload_status": "not_materialized_in_git",
                        "generator_visible": False,
                        "source_file": "data/criteria_data/criteria.jsonl",
                        "row_index": row_index,
                        "rubric_axes": [
                            "comprehensiveness",
                            "insight_depth",
                            "instruction_following",
                            "readability",
                        ],
                    },
                },
            }
        )

    manifest = {
        "schema_version": "codex-dr.case_spec_manifest.v1",
        "benchmark_family": BENCHMARK_FAMILY_DEEPRESEARCH_BENCH,
        "source": {
            "benchmark_family": BENCHMARK_FAMILY_DEEPRESEARCH_BENCH,
            "dataset_id": repo.get("full_name", "Ayanami0730/deep_research_bench"),
            "dataset_commit": repo.get("commit_sha"),
            "split": "prompt_data",
            "source_file": "data/prompt_data/query.jsonl",
            "license_observed": repo.get("license_observed") or dataset.get("license_observed"),
            "access_observed": "public_ungated",
            "manifest_ref": source_refresh.as_posix(),
            "official_repository_commit": repo.get("commit_sha"),
            "official_dataset_revision": dataset.get("revision_sha"),
            "evaluator_lane_policy": refresh.get("evaluator_lane", {}),
        },
        "selection": {
            "method": "explicit_row_indices" if row_indices else "first_n_rows",
            "row_indices": selected_indices,
            "raw_data_in_git": False,
            "reference_and_rubric_visibility": "scorer_only",
        },
        "cases": cases,
        "claim_boundary": {
            "allowed_claims_if_valid": [
                "DeepResearch Bench cases were imported as sealed generator/scorer manifests."
            ],
            "blocked_claims": [
                "DeepResearch Bench score",
                "Grep parity",
                "leaderboard rank",
                "product readiness",
            ],
        },
    }
    if not manifest["source"].get("dataset_commit"):
        raise HarnessError("source refresh receipt is missing official_repository.commit_sha")
    if not manifest["source"].get("license_observed"):
        raise HarnessError("source refresh receipt is missing license information")
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, manifest)
    read_case_spec_manifest(output)
    return output


def default_report_export_custody_path(output: Path) -> Path:
    if output.suffix == ".jsonl":
        return output.with_name(f"{output.stem}_custody.json")
    return output.with_suffix(f"{output.suffix}.custody.json")


def effective_report_path(run_dir: Path) -> Path:
    live_writer_report = (
        run_dir
        / "live_executor"
        / "role_outputs"
        / "task_final_writer"
        / "report.md"
    )
    if live_writer_report.exists():
        return live_writer_report
    return run_dir / "report.md"


def blocked_adequacy_export_article(run_dir: Path) -> str:
    queue = read_json(run_dir / "backpressure" / "adequacy_backpressure_queue.json")
    gaps = [
        f"- {item.get('gap')}"
        for item in queue.get("items", [])
        if item.get("gap")
    ]
    gap_text = "\n".join(gaps) if gaps else "- Unspecified adequacy gap."
    return (
        "# Blocked By Adequacy Backpressure\n\n"
        "This case did not produce a final writer report. The live Codex-DR mesh "
        "stopped before `task_final_writer` because the active adequacy queue "
        "remained open.\n\n"
        "## Required Follow-Up\n"
        f"{gap_text}\n\n"
        "## Claim Boundary\n"
        "No DeepResearch Bench score, Grep parity, leaderboard, product-readiness, "
        "or official-submission claim is opened by this blocked export."
    )


def planned_not_executed_export_article(run_dir: Path) -> str:
    return (
        "# Planned Live Mesh Case Not Executed\n\n"
        "This case did not produce a live Codex-DR final writer report. A live "
        "launch plan exists, but `mesh-execute-live` has not completed for this "
        "case in the current subset lane.\n\n"
        "## Claim Boundary\n"
        "No DeepResearch Bench score, Grep parity, leaderboard, product-readiness, "
        "or official-submission claim is opened by this planned-case export."
    )


def deepresearch_bench_report_export(
    case_ids: list[str],
    *,
    output: Path,
    custody_output: Path | None = None,
    runs_dir: Path | str | None = None,
    allow_invalid: bool = False,
) -> Path:
    if not case_ids:
        raise HarnessError("at least one case_id is required")
    runs_root = Path(runs_dir or DEFAULT_RUNS_DIR)
    custody_path = custody_output or default_report_export_custody_path(output)
    rows: list[dict[str, Any]] = []
    custody_cases: list[dict[str, Any]] = []
    seen_ids: set[Any] = set()
    for case_id in case_ids:
        run_dir = run_path(case_id, runs_root)
        report = validate_run(case_id, runs_dir=runs_root)
        if report["status"] != "passed":
            if not allow_invalid:
                raise HarnessError(
                    f"{case_id} failed validation before report export: "
                    + ", ".join(report["failed_checks"])
                )
        case_manifest = read_json(run_dir / "case_manifest.json")
        if case_manifest.get("benchmark_family") != BENCHMARK_FAMILY_DEEPRESEARCH_BENCH:
            raise HarnessError(
                f"{case_id} is not a DeepResearch Bench run: "
                f"{case_manifest.get('benchmark_family')}"
            )
        prompt_id = case_manifest.get("generator_visible", {}).get(
            "benchmark_prompt_id",
            case_manifest.get("case_id"),
        )
        if prompt_id in seen_ids:
            raise HarnessError(f"duplicate exported id: {prompt_id}")
        seen_ids.add(prompt_id)
        prompt = case_manifest.get("generator_visible", {}).get("question")
        if not prompt:
            raise HarnessError(f"{case_id} case manifest has no generator-visible question")
        blocked_by_adequacy = is_live_mesh_blocked_by_adequacy(run_dir)
        planned_not_executed = (
            (run_dir / "live_adapter" / "launch_plan.json").exists()
            and not is_live_mesh_run(run_dir)
        )
        if blocked_by_adequacy and not allow_invalid:
            raise HarnessError(
                f"{case_id} stopped on adequacy backpressure before final writer"
            )
        if planned_not_executed and not allow_invalid:
            raise HarnessError(f"{case_id} has a live plan but no live execution")
        if blocked_by_adequacy:
            report_path = run_dir / "backpressure" / "adequacy_backpressure_queue.json"
            article = blocked_adequacy_export_article(run_dir)
        elif planned_not_executed:
            report_path = run_dir / "live_adapter" / "launch_plan.json"
            article = planned_not_executed_export_article(run_dir)
        else:
            report_path = effective_report_path(run_dir)
            article = report_path.read_text(encoding="utf-8").strip()
        if not article:
            raise HarnessError(f"{case_id} report is empty")
        claim_ledger = read_json(run_dir / "claim_ledger.json")
        allowed_claims = read_json(run_dir / "allowed_claims.json")
        artifact_manifest = read_json(run_dir / "artefact_manifest.json")
        rows.append({"id": prompt_id, "prompt": prompt, "article": article})
        custody_cases.append(
            {
                "run_id": case_id,
                "case_id": case_manifest.get("case_id"),
                "benchmark_prompt_id": prompt_id,
                "benchmark_family": BENCHMARK_FAMILY_DEEPRESEARCH_BENCH,
                "row_indices": case_manifest.get("source", {}).get("row_indices", []),
                "source_refresh": case_manifest.get("source", {}).get("manifest_ref"),
                "evaluator_lane_policy": case_manifest.get("source", {}).get(
                    "evaluator_lane_policy",
                    {},
                ),
                "inputs": {
                    "run_manifest": display_path(run_dir / "run_manifest.json"),
                    "case_manifest": display_path(run_dir / "case_manifest.json"),
                    "report": display_path(report_path),
                    "canonical_report": display_path(run_dir / "report.md"),
                    "claim_ledger": display_path(run_dir / "claim_ledger.json"),
                    "allowed_claims": display_path(run_dir / "allowed_claims.json"),
                    "validation_report": display_path(run_dir / "validation_report.json"),
                    "artefact_manifest": display_path(run_dir / "artefact_manifest.json"),
                },
                "hashes": {
                    "report_sha256": sha256_file(report_path),
                    "case_manifest_sha256": sha256_file(run_dir / "case_manifest.json"),
                    "claim_ledger_sha256": sha256_file(run_dir / "claim_ledger.json"),
                    "allowed_claims_sha256": sha256_file(run_dir / "allowed_claims.json"),
                },
                "claim_boundary": {
                    "claim_ledger_status": claim_ledger.get("ledger_status"),
                    "allowed_claim_count": len(allowed_claims.get("allowed_claims", [])),
                    "blocked_claims": allowed_claims.get("blocked_claims", []),
                },
                "artifact_count": len(artifact_manifest.get("artifacts", [])),
                "validation": {
                    "status": report.get("status"),
                    "failed_checks": report.get("failed_checks", []),
                    "exported_despite_validation_failure": report.get("status")
                    != "passed",
                    "exported_blocked_partial": blocked_by_adequacy,
                    "exported_planned_not_executed": planned_not_executed,
                },
            }
        )
    write_jsonl(output, rows)
    custody = {
        "schema_version": "codex-dr.deepresearch_bench_raw_report_export.v1",
        "export_id": output.stem,
        "benchmark_family": BENCHMARK_FAMILY_DEEPRESEARCH_BENCH,
        "official_raw_report_format": {
            "format": "jsonl",
            "required_fields": ["id", "prompt", "article"],
            "source": "DeepResearch Bench raw generated reports",
        },
        "produced_at": FIXTURE_TIMESTAMP,
        "raw_report_jsonl": display_path(output),
        "raw_report_jsonl_sha256": sha256_file(output),
        "case_count": len(rows),
        "contains_validation_failures": any(
            case.get("validation", {}).get("status") != "passed"
            for case in custody_cases
        ),
        "cases": custody_cases,
        "claim_boundary": {
            "may_claim_score": False,
            "may_claim_grep_parity": False,
            "requires_next_bead": "alexandriacleanroom-98.3",
            "blocked_claims": [
                "DeepResearch Bench score",
                "Grep parity",
                "leaderboard rank",
                "product readiness",
            ],
        },
    }
    write_json(custody_path, custody)
    return output


def git_commit_or_unknown(path: Path) -> str:
    if not (path / ".git").exists():
        return "unknown"
    try:
        result = subprocess.run(
            ["git", "-C", path.as_posix(), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def validate_deepresearch_bench_raw_report_rows(raw_reports: Path) -> list[dict[str, Any]]:
    rows = read_jsonl(raw_reports)
    if not rows:
        raise HarnessError("raw report JSONL is empty")
    seen_ids: set[Any] = set()
    for index, row in enumerate(rows, start=1):
        missing = [field for field in ["id", "prompt", "article"] if field not in row]
        if missing:
            raise HarnessError(f"raw report row {index} missing fields: {', '.join(missing)}")
        extra = set(row) - {"id", "prompt", "article"}
        if extra:
            raise HarnessError(
                f"raw report row {index} has non-official fields: {', '.join(sorted(extra))}"
            )
        if row["id"] in seen_ids:
            raise HarnessError(f"duplicate raw report id: {row['id']}")
        seen_ids.add(row["id"])
        if not str(row["prompt"]).strip():
            raise HarnessError(f"raw report row {index} has an empty prompt")
        if not str(row["article"]).strip():
            raise HarnessError(f"raw report row {index} has an empty article")
    return rows


def resolve_sandbox_display_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    parts = path.parts
    if len(parts) >= 2 and parts[0] == "sandbox" and parts[1] == "codex-dr":
        return SANDBOX_ROOT.parent.parent / path
    return SANDBOX_ROOT / path


def cjk_count(text: str) -> int:
    return sum(1 for char in text if "\u4e00" <= char <= "\u9fff")


def prompt_expects_cjk_answer(prompt: str) -> bool:
    return cjk_count(prompt) >= 4


def report_has_substantial_cjk(report: str) -> bool:
    stripped = "".join(char for char in report if not char.isspace())
    if not stripped:
        return False
    return cjk_count(stripped) / len(stripped) >= 0.05


def report_has_markdown_table(report: str) -> bool:
    lines = [line.strip() for line in report.splitlines()]
    return any(line.startswith("|") and line.endswith("|") for line in lines)


def prompt_asks_comparison(prompt: str) -> bool:
    lowered = prompt.lower()
    return any(marker in lowered or marker in prompt for marker in COMPARATIVE_PROMPT_MARKERS)


def adequacy_status_value(row: dict[str, Any]) -> str:
    return str(row.get("status") or row.get("assessment_status") or "").strip()


def adequacy_label_value(row: dict[str, Any]) -> str:
    return str(
        row.get("criterion")
        or row.get("criterion_id")
        or row.get("adequacy_id")
        or row.get("assessment_id")
        or "unknown"
    )


def review_finding_requires_reentry(finding: dict[str, Any]) -> bool:
    return bool(finding.get("requires_reentry") is True)


def review_finding_severity(finding: dict[str, Any]) -> str:
    return str(finding.get("severity") or "").lower()


def severity_is_material(value: str) -> bool:
    return value in {"high", "major", "critical", "blocking"}


def deepresearch_bench_pre_scorer_quality_gate(
    suite_id: str,
    *,
    output_dir: Path | None = None,
    runs_dir: Path | str | None = None,
) -> Path:
    validate_id(suite_id, "suite_id")
    runs_root = Path(runs_dir or DEFAULT_RUNS_DIR)
    suite_dir = run_path(suite_id, runs_root)
    custody_path = suite_dir / "deepresearch_bench_subset_raw_reports_custody.json"
    if not custody_path.exists():
        raise HarnessError(
            f"{suite_id} has no raw report custody file; run subset pressure first"
        )
    custody = read_json(custody_path)
    if custody.get("benchmark_family") != BENCHMARK_FAMILY_DEEPRESEARCH_BENCH:
        raise HarnessError("pre-scorer quality gate requires a DeepResearch Bench suite")
    output = output_dir or suite_dir / "pre_scorer_quality_gate"
    output.mkdir(parents=True, exist_ok=True)

    cases: list[dict[str, Any]] = []
    failure_taxonomy: dict[str, dict[str, Any]] = {}

    def add_failure(
        *,
        failure_class: str,
        severity: str,
        run_id: str,
        summary: str,
    ) -> None:
        entry = failure_taxonomy.setdefault(
            failure_class,
            {
                "failure_class": failure_class,
                "severity": severity,
                "affected_cases": [],
                "summary": summary,
            },
        )
        if run_id not in entry["affected_cases"]:
            entry["affected_cases"].append(run_id)
        if severity == "blocking":
            entry["severity"] = "blocking"

    for case in custody.get("cases", []):
        run_id = case.get("run_id")
        if not run_id:
            raise HarnessError("raw report custody case is missing run_id")
        run_dir = run_path(run_id, runs_root)
        manifest = read_json(run_dir / "case_manifest.json")
        prompt = str(manifest.get("generator_visible", {}).get("question") or "")
        report_path = resolve_sandbox_display_path(case.get("inputs", {}).get("report", ""))
        report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
        adequacy_rows = read_jsonl(run_dir / "adequacy_assessments.jsonl")
        review = read_json(run_dir / "reviews" / "review_001.json")
        review_findings = [
            finding
            for finding in review.get("findings", [])
            if isinstance(finding, dict)
            and review_finding_requires_reentry(finding)
            and severity_is_material(review_finding_severity(finding))
        ]
        issues: list[dict[str, Any]] = []

        for row in adequacy_rows:
            status = adequacy_status_value(row)
            if status in SCORER_BLOCKING_ADEQUACY_STATUSES:
                issues.append(
                    {
                        "issue_id": "unresolved_adequacy_status",
                        "severity": "blocking",
                        "criterion": adequacy_label_value(row),
                        "status": status,
                        "follow_up_task": row.get("follow_up_task"),
                    }
                )
                add_failure(
                    failure_class="answer_adequacy_pre_scorer_risk",
                    severity="blocking",
                    run_id=run_id,
                    summary=(
                        "Root adequacy assessments preserve unsatisfied or partial "
                        "answer adequacy before scorer execution."
                    ),
                )

        if review_findings and any(
            issue["issue_id"] == "unresolved_adequacy_status" for issue in issues
        ):
            issues.append(
                {
                    "issue_id": "material_review_reentry_still_live",
                    "severity": "blocking",
                    "finding_count": len(review_findings),
                    "finding_ids": [
                        str(finding.get("finding_id") or finding.get("title"))
                        for finding in review_findings
                    ],
                }
            )
            add_failure(
                failure_class="material_review_reentry_still_live",
                severity="blocking",
                run_id=run_id,
                summary=(
                    "Material review findings still require re-entry while adequacy "
                    "status remains unresolved."
                ),
            )

        if "local_artifact" in report_text:
            issues.append(
                {
                    "issue_id": "local_artifact_source_in_final_report",
                    "severity": "warning",
                    "detail": (
                        "Final report uses local_artifact as a source URL for at "
                        "least one material support row."
                    ),
                }
            )
            add_failure(
                failure_class="final_public_citation_map_weak",
                severity="warning",
                run_id=run_id,
                summary=(
                    "Final report uses local custody surfaces where public source "
                    "support should be visible."
                ),
            )

        lowered_report = report_text.lower()
        matched_self_limiting = [
            pattern for pattern in SELF_LIMITING_REPORT_PATTERNS if pattern in lowered_report
        ]
        if matched_self_limiting:
            issues.append(
                {
                    "issue_id": "scorer_facing_self_limitation",
                    "severity": "warning",
                    "matched_patterns": matched_self_limiting,
                }
            )
            add_failure(
                failure_class="scorer_facing_self_limitation",
                severity="warning",
                run_id=run_id,
                summary=(
                    "Final report carries internal adequacy caveats into the scorer-facing answer."
                ),
            )

        if prompt_expects_cjk_answer(prompt) and not report_has_substantial_cjk(report_text):
            issues.append(
                {
                    "issue_id": "user_language_mismatch",
                    "severity": "warning",
                    "detail": (
                        "Generator-visible prompt is Chinese, but the final report "
                        "is not substantially Chinese."
                    ),
                }
            )
            add_failure(
                failure_class="user_language_fit_inconsistent",
                severity="warning",
                run_id=run_id,
                summary=(
                    "Final report language does not consistently follow the prompt language."
                ),
            )

        if prompt_asks_comparison(prompt) and not report_has_markdown_table(report_text):
            issues.append(
                {
                    "issue_id": "comparative_prompt_without_table",
                    "severity": "warning",
                    "detail": (
                        "Prompt asks for comparison or ranking, but final report has "
                        "no Markdown comparison table."
                    ),
                }
            )
            add_failure(
                failure_class="comparative_answer_structure_weak",
                severity="warning",
                run_id=run_id,
                summary=(
                    "Comparative prompt lacks a visible same-basis table in the final answer."
                ),
            )

        case_status = (
            "blocked"
            if any(issue.get("severity") == "blocking" for issue in issues)
            else "warning"
            if issues
            else "passed"
        )
        cases.append(
            {
                "run_id": run_id,
                "case_id": case.get("case_id"),
                "benchmark_prompt_id": case.get("benchmark_prompt_id"),
                "status": case_status,
                "word_count": len(report_text.split()),
                "prompt_expects_cjk_answer": prompt_expects_cjk_answer(prompt),
                "report_has_substantial_cjk": report_has_substantial_cjk(report_text),
                "root_adequacy_statuses": [
                    {
                        "criterion": adequacy_label_value(row),
                        "status": adequacy_status_value(row),
                    }
                    for row in adequacy_rows
                ],
                "issues": issues,
                "inputs": {
                    "report": display_path(report_path),
                    "review": display_path(run_dir / "reviews" / "review_001.json"),
                    "adequacy": display_path(run_dir / "adequacy_assessments.jsonl"),
                },
            }
        )

    has_blockers = any(case["status"] == "blocked" for case in cases)
    has_warnings = any(case["status"] == "warning" for case in cases)
    status = "blocked" if has_blockers else "passed_with_warnings" if has_warnings else "passed"
    if any(
        issue.get("issue_id") == "unresolved_adequacy_status"
        for case in cases
        for issue in case.get("issues", [])
    ):
        selected_candidate = {
            "candidate_id": "cand_drb_recursive_reentry_from_adequacy_status_001",
            "target_surface": "sandbox/codex-dr/tools/alexandria_dr.py::mesh_execute_live",
            "purpose": (
                "Trigger recursive re-entry or block scorer export when root "
                "adequacy status remains not_satisfied or partially_satisfied."
            ),
        }
    elif any(
        issue.get("issue_id") == "user_language_mismatch"
        for case in cases
        for issue in case.get("issues", [])
    ):
        selected_candidate = {
            "candidate_id": "cand_drb_user_language_writer_lock_001",
            "target_surface": "sandbox/codex-dr/harness-specs/live_role_prompt_pack.md",
            "purpose": "Require final answers to follow the generator-visible prompt language.",
        }
    else:
        selected_candidate = {
            "candidate_id": "cand_drb_final_public_citation_map_001",
            "target_surface": "sandbox/codex-dr/harness-specs/live_role_prompt_pack.md",
            "purpose": "Make public source support visible in final benchmark reports.",
        }

    gate = {
        "schema_version": "codex-dr.deepresearch_bench_pre_scorer_quality_gate.v1",
        "suite_id": suite_id,
        "status": status,
        "produced_at": FIXTURE_TIMESTAMP,
        "source_custody": display_path(custody_path),
        "case_count": len(cases),
        "cases": cases,
        "failure_taxonomy": sorted(
            failure_taxonomy.values(), key=lambda item: item["failure_class"]
        ),
        "selected_candidate": selected_candidate,
        "scorer_spend_decision": {
            "official_scorer_should_run_for_quality_smoke": status == "passed",
            "official_scorer_may_run_for_baseline_measurement": True,
            "reason": (
                "Quality smoke should wait for this gate to pass; baseline measurement "
                "can still run if scorer authority and budget are explicitly approved."
            ),
        },
        "claim_boundary": {
            "may_claim_deepresearch_bench_score": False,
            "may_claim_grep_parity": False,
            "may_claim_leaderboard_rank": False,
            "may_claim_product_readiness": False,
            "blocked_claims": [
                "DeepResearch Bench score",
                "Grep parity",
                "leaderboard rank",
                "product readiness",
                "official benchmark submission",
                "scorer-backed evaluation",
            ],
        },
    }
    gate_path = output / "pre_scorer_quality_gate.json"
    write_json(gate_path, gate)
    markdown_lines = [
        "# DeepResearch Bench Pre-Scorer Quality Gate",
        "",
        f"Suite: `{suite_id}`",
        f"Status: `{status}`",
        "",
        "## Cases",
        "",
        "| Case | Status | Issues |",
        "| --- | --- | --- |",
    ]
    for case in cases:
        issue_names = ", ".join(issue["issue_id"] for issue in case["issues"]) or "none"
        markdown_lines.append(
            f"| `{case['run_id']}` | `{case['status']}` | {issue_names} |"
        )
    markdown_lines.extend(
        [
            "",
            "## Selected Candidate",
            "",
            f"`{selected_candidate['candidate_id']}`",
            "",
            "## Claim Boundary",
            "",
            "Score, Grep parity, leaderboard rank, product readiness, official submission, "
            "and scorer-backed evaluation claims remain blocked.",
            "",
        ]
    )
    write_text(output / "pre_scorer_quality_gate.md", "\n".join(markdown_lines))
    return output


def probe_deepresearch_bench_official_race_repo(official_repo: Path) -> dict[str, Any]:
    required_paths = [
        "README.md",
        "deepresearch_bench_race.py",
        "run_benchmark.sh",
        "utils/api.py",
        "data/prompt_data/query.jsonl",
        "data/criteria_data/criteria.jsonl",
        "data/test_data/cleaned_data/reference.jsonl",
    ]
    missing = [relative for relative in required_paths if not (official_repo / relative).exists()]
    if missing:
        raise HarnessError(
            "official DeepResearch Bench RACE path is incomplete: "
            + ", ".join(missing)
        )
    return {
        "repository": display_path(official_repo),
        "commit": git_commit_or_unknown(official_repo),
        "required_paths": required_paths,
        "script": "deepresearch_bench_race.py",
        "reference_file": "data/test_data/cleaned_data/reference.jsonl",
        "criteria_file": "data/criteria_data/criteria.jsonl",
        "query_file": "data/prompt_data/query.jsonl",
    }


def parse_race_result_file(path: Path) -> dict[str, float]:
    metrics = {}
    if not path.exists():
        return metrics
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized_key = key.strip().lower().replace(" ", "_")
        try:
            metrics[normalized_key] = float(value.strip())
        except ValueError:
            continue
    return metrics


def deepresearch_bench_race_bridge(
    *,
    raw_reports: Path,
    source_refresh: Path,
    official_repo: Path = DEFAULT_DEEPRESEARCH_BENCH_OFFICIAL_REPO,
    output_dir: Path,
    model_name: str = "alexandria-codex-dr",
    allow_provider_run: bool = False,
    limit: int | None = None,
    max_workers: int = 1,
    timeout_seconds: int = 1800,
) -> Path:
    rows = validate_deepresearch_bench_raw_report_rows(raw_reports)
    source = read_json(source_refresh)
    if source.get("schema_version") != "codex-dr.deepresearch_bench_source_refresh.v1":
        raise HarnessError("source refresh is not a DeepResearch Bench source refresh receipt")
    repo_probe = probe_deepresearch_bench_official_race_repo(official_repo)
    safe_model = safe_model_filename(model_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_input_dir = output_dir / "official_inputs" / "raw_data"
    cleaned_input_dir = output_dir / "official_inputs" / "cleaned_data"
    official_results_dir = output_dir / "official_results" / "race" / safe_model
    raw_input_dir.mkdir(parents=True, exist_ok=True)
    cleaned_input_dir.mkdir(parents=True, exist_ok=True)
    official_results_dir.mkdir(parents=True, exist_ok=True)
    official_input_copy = raw_input_dir / f"{safe_model}.jsonl"
    shutil.copyfile(raw_reports, official_input_copy)
    evaluator_lane = {
        "name": "RACE",
        "judge_model": "gemini-2.5-pro-preview-06-05",
        "lane_status": "accepted_before_new_evaluator_announcement",
        "source_refresh_policy": source.get("evaluator_lane", {}),
    }
    command_plan = [
        sys.executable,
        "-u",
        "deepresearch_bench_race.py",
        safe_model,
        "--raw_data_dir",
        raw_input_dir.resolve().as_posix(),
        "--cleaned_data_dir",
        cleaned_input_dir.resolve().as_posix(),
        "--max_workers",
        str(max_workers),
        "--query_file",
        "data/prompt_data/query.jsonl",
        "--output_dir",
        official_results_dir.resolve().as_posix(),
        "--force",
    ]
    if limit is not None:
        command_plan.extend(["--limit", str(limit)])
    gemini_key_present = bool(os.environ.get("GEMINI_API_KEY"))
    missing_requirements = []
    if not gemini_key_present:
        missing_requirements.append("GEMINI_API_KEY")
    if not allow_provider_run:
        missing_requirements.append("explicit --allow-provider-run")
    execution_allowed = not missing_requirements
    transcript_path = output_dir / "race_command_transcript.json"
    result_file = official_results_dir / "race_result.txt"
    raw_results_file = official_results_dir / "raw_results.jsonl"
    bridge_receipt_path = output_dir / "race_bridge_receipt.json"
    scorer_manifest_path = output_dir / "scorer_manifest.json"
    evaluation_output_path = output_dir / "race_evaluation_output.json"
    execution = {
        "ran": False,
        "return_code": None,
        "transcript": display_path(transcript_path),
        "reason": "blocked_before_provider_execution",
    }
    status = "blocked"
    metrics: dict[str, float] = {}
    if execution_allowed:
        completed = subprocess.run(
            command_plan,
            cwd=official_repo,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        write_json(
            transcript_path,
            {
                "schema_version": "codex-dr.deepresearch_bench_race_transcript.v1",
                "command": command_plan,
                "cwd": display_path(official_repo),
                "return_code": completed.returncode,
                "stdout_tail": completed.stdout[-4000:],
                "stderr_tail": completed.stderr[-4000:],
            },
        )
        execution = {
            "ran": True,
            "return_code": completed.returncode,
            "transcript": display_path(transcript_path),
            "reason": "official_race_script_invoked",
        }
        if completed.returncode == 0:
            metrics = parse_race_result_file(result_file)
            status = "scored_claims_blocked" if metrics else "failed"
        else:
            status = "failed"
    raw_report_metadata = {
        "source": display_path(raw_reports),
        "official_input_copy": display_path(official_input_copy),
        "sha256": sha256_file(raw_reports),
        "case_count": len(rows),
    }
    scorer_status = (
        "executed"
        if status == "scored_claims_blocked"
        else "failed"
        if status == "failed"
        else "blocked"
    )
    manifest = {
        "schema_version": "codex-dr.deepresearch_bench_race_scorer_manifest.v1",
        "benchmark_family": BENCHMARK_FAMILY_DEEPRESEARCH_BENCH,
        "model_name": safe_model,
        "source_refresh": display_path(source_refresh),
        "evaluator_lane": evaluator_lane,
        "scorer_status": scorer_status,
        "execution_allowed": execution_allowed,
        "official_scorer": {
            **repo_probe,
            "command_plan": command_plan,
            "command_cwd": display_path(official_repo),
        },
        "raw_reports": raw_report_metadata,
        "provider_requirements": {
            "required_env": [
                {
                    "name": "GEMINI_API_KEY",
                    "purpose": "Gemini evaluator access for official RACE scoring.",
                    "present": gemini_key_present,
                }
            ],
            "missing_requirements": missing_requirements,
            "secrets_recorded": False,
        },
        "output_paths": {
            "evaluation_output": display_path(evaluation_output_path),
            "bridge_receipt": display_path(bridge_receipt_path),
            "official_results_dir": display_path(official_results_dir),
            "race_result": display_path(result_file),
            "raw_results": display_path(raw_results_file),
            "transcript": display_path(transcript_path),
        },
        "execution": execution,
        "claim_boundary": {
            "numeric_score_allowed": False,
            "blocked_claims": [
                "DeepResearch Bench score",
                "Grep parity",
                "leaderboard rank",
                "product readiness",
            ],
        },
        "manifest_schema": DEEPRESEARCH_BENCH_RACE_SCORER_MANIFEST_SCHEMA,
        "evaluation_output_schema": DEEPRESEARCH_BENCH_RACE_EVALUATION_OUTPUT_SCHEMA,
        "produced_at": FIXTURE_TIMESTAMP,
    }
    write_json(scorer_manifest_path, manifest)
    score = metrics.get("overall_score") if status == "scored_claims_blocked" else None
    dimensions = (
        {
            "comprehensiveness": metrics.get("comprehensiveness"),
            "insight": metrics.get("insight"),
            "instruction_following": metrics.get("instruction_following"),
            "readability": metrics.get("readability"),
        }
        if status == "scored_claims_blocked"
        else None
    )
    evaluation_output = {
        "schema_version": "codex-dr.deepresearch_bench_race_evaluation_output.v1",
        "benchmark_family": BENCHMARK_FAMILY_DEEPRESEARCH_BENCH,
        "evaluator_lane": evaluator_lane,
        "status": status,
        "raw_reports": {
            "source": display_path(raw_reports),
            "case_count": len(rows),
            "sha256": sha256_file(raw_reports),
        },
        "score": score,
        "dimensions": dimensions,
        "official_result_files": {
            "race_result": display_path(result_file),
            "raw_results": display_path(raw_results_file),
        },
        "missing_requirements": missing_requirements,
        "execution": execution,
        "claim_boundary": {
            "may_claim_score": False,
            "blocked_claims": [
                "DeepResearch Bench score",
                "Grep parity",
                "leaderboard rank",
                "product readiness",
            ],
        },
    }
    write_json(evaluation_output_path, evaluation_output)
    write_json(
        bridge_receipt_path,
        {
            "schema_version": "codex-dr.deepresearch_bench_race_bridge_receipt.v1",
            "status": status,
            "benchmark_family": BENCHMARK_FAMILY_DEEPRESEARCH_BENCH,
            "evaluator_lane": evaluator_lane,
            "official_scorer": {
                "repository": repo_probe["repository"],
                "commit": repo_probe["commit"],
                "script": repo_probe["script"],
                "command_plan": command_plan,
            },
            "provider_requirements": manifest["provider_requirements"],
            "raw_reports": raw_report_metadata,
            "outputs": manifest["output_paths"],
            "execution": execution,
            "claim_boundary": manifest["claim_boundary"],
            "produced_at": FIXTURE_TIMESTAMP,
        },
    )
    return scorer_manifest_path


def deepresearch_bench_claim_review(
    case_id: str,
    *,
    race_bridge_receipt: Path,
    source_refresh: Path,
    runs_dir: Path | str | None = None,
) -> Path:
    run_dir = run_path(case_id, runs_dir)
    if not run_dir.exists():
        raise HarnessError(f"run does not exist: {run_dir}")
    if not is_live_mesh_run(run_dir):
        raise HarnessError("DeepResearch Bench claim review requires a live mesh run")
    receipt = read_json(race_bridge_receipt)
    if receipt.get("schema_version") != "codex-dr.deepresearch_bench_race_bridge_receipt.v1":
        raise HarnessError("race bridge receipt schema is invalid")
    if receipt.get("benchmark_family") != BENCHMARK_FAMILY_DEEPRESEARCH_BENCH:
        raise HarnessError("race bridge receipt is not for DeepResearch Bench")
    source = read_json(source_refresh)
    if source.get("schema_version") != "codex-dr.deepresearch_bench_source_refresh.v1":
        raise HarnessError("source refresh is not a DeepResearch Bench receipt")
    bridge_dir = race_bridge_receipt.parent
    bridge_manifest = bridge_dir / "scorer_manifest.json"
    bridge_evaluation = bridge_dir / "race_evaluation_output.json"
    if not bridge_manifest.exists() or not bridge_evaluation.exists():
        raise HarnessError("race bridge manifest or evaluation output is missing")

    scoring_dir = run_dir / "scoring" / "deepresearch_bench_race"
    scoring_dir.mkdir(parents=True, exist_ok=True)
    copied_receipt = scoring_dir / "race_bridge_receipt.json"
    copied_manifest = scoring_dir / "race_scorer_manifest.original.json"
    copied_evaluation = scoring_dir / "race_evaluation_output.json"
    shutil.copy2(race_bridge_receipt, copied_receipt)
    shutil.copy2(bridge_manifest, copied_manifest)
    shutil.copy2(bridge_evaluation, copied_evaluation)

    scorer_manifest = read_json(bridge_manifest)
    evaluation = read_json(bridge_evaluation)
    status = evaluation.get("status") or receipt.get("status")
    score = evaluation.get("score")
    score_supported = status == "scored_claims_blocked" and score is not None
    missing_requirements = (
        receipt.get("provider_requirements", {}).get("missing_requirements", [])
        or evaluation.get("missing_requirements", [])
    )
    scorer_manifest.update(
        {
            "run_id": case_id,
            "case_manifest": "case_manifest.json",
            "source_refresh": display_path(source_refresh),
            "scorer_status": "executed" if score_supported else status or "blocked",
            "output_paths": {
                **scorer_manifest.get("output_paths", {}),
                "bridge_receipt": rel(copied_receipt, run_dir),
                "evaluation_output": rel(copied_evaluation, run_dir),
                "original_scorer_manifest": rel(copied_manifest, run_dir),
            },
            "claim_boundary": {
                "numeric_score_allowed": False,
                "blocked_claims": REQUIRED_BLOCKED_CLAIMS,
            },
            "produced_by_event": "evt_drb_claim_review_0001_written",
        }
    )
    write_json(run_dir / "scorer_manifest.json", scorer_manifest)

    mode = "scored_claims_blocked" if score_supported else "blocked_no_score"
    write_json(
        run_dir / "benchmark_score.json",
        {
            "schema_version": "codex-dr.benchmark_score.v1",
            "run_id": case_id,
            "benchmark_family": BENCHMARK_FAMILY_DEEPRESEARCH_BENCH,
            "mode": mode,
            "case_manifest": "case_manifest.json",
            "scorer_manifest": "scorer_manifest.json",
            "evaluation_output": rel(copied_evaluation, run_dir),
            "race_bridge_receipt": rel(copied_receipt, run_dir),
            "score": score if score_supported else None,
            "raw_score": score if score_supported else None,
            "normalized_score": score if score_supported else None,
            "dimensions": evaluation.get("dimensions") if score_supported else None,
            "claims_enabled": False,
            "reason": (
                "Official DeepResearch Bench RACE scoring produced a score, but "
                "public claims remain blocked pending claim review."
                if score_supported
                else "Official DeepResearch Bench RACE scoring is blocked before "
                "provider execution."
            ),
            "produced_by_event": "evt_drb_claim_review_0001_written",
        },
    )

    grep_target = current_grep_target_from_source_refresh(source)
    failure_taxonomy = []
    if not score_supported:
        failure_taxonomy.append(
            {
                "failure_class": "scorer_blocked",
                "severity": "blocking",
                "root_cause": (
                    "Official RACE scorer did not run because required provider "
                    "authority is absent."
                ),
                "missing_requirements": missing_requirements,
                "blocks": [
                    "DeepResearch Bench score",
                    "Grep parity",
                    "leaderboard rank",
                ],
            }
        )
    write_json(
        run_dir / "evaluation_ledger.json",
        {
            "schema_version": "codex-dr.benchmark_evaluation_ledger.v1",
            "run_id": case_id,
            "benchmark_family": BENCHMARK_FAMILY_DEEPRESEARCH_BENCH,
            "case_id": read_json(run_dir / "case_manifest.json").get("case_id"),
            "scorer_manifest": "scorer_manifest.json",
            "benchmark_score": "benchmark_score.json",
            "evaluation_output": rel(copied_evaluation, run_dir),
            "race_bridge_receipt": rel(copied_receipt, run_dir),
            "result_status": mode,
            "score_status": {
                "score": score if score_supported else None,
                "raw_score": score if score_supported else None,
                "normalized_score": score if score_supported else None,
                "claims_enabled": False,
                "scorer_custody_present": score_supported,
            },
            "evaluator_lane": receipt.get("evaluator_lane"),
            "current_grep_target": grep_target,
            "failure_taxonomy": failure_taxonomy,
            "improvement_recommendations": [
                {
                    "recommendation_id": "rec_drb_score_authority_001",
                    "target_surface": "scoring/deepresearch_bench_race/",
                    "action": (
                        "Provide GEMINI_API_KEY and explicit --allow-provider-run, "
                        "or refresh the evaluator lane when the official benchmark "
                        "changes scorer policy."
                    ),
                },
                {
                    "recommendation_id": "rec_drb_claim_gate_001",
                    "target_surface": "allowed_claims.json",
                    "action": (
                        "Keep DeepResearch Bench score, Grep parity, leaderboard, "
                        "and product-readiness claims blocked until scorer custody "
                        "and multi-case evidence support review."
                    ),
                },
            ],
            "allowed_claim_impact": {
                "may_widen_claims": False,
                "claim_gate_status": "blocked",
                "reason": (
                    "One-case score exists but claims remain blocked."
                    if score_supported
                    else "No official score exists for this run."
                ),
                "blocked_claims": [
                    "DeepResearch Bench score",
                    "Grep parity",
                    "leaderboard rank",
                    "product readiness",
                ],
            },
            "produced_by_event": "evt_drb_claim_review_0001_written",
        },
    )

    decision = "blocked_single_case_review_required" if score_supported else "blocked_no_score"
    write_json(
        run_dir / "claim_review.json",
        {
            "schema_version": "codex-dr.claim_review.v1",
            "run_id": case_id,
            "review_id": "deepresearch_bench_claim_review_001",
            "benchmark_family": BENCHMARK_FAMILY_DEEPRESEARCH_BENCH,
            "decision": decision,
            "may_widen_public_benchmark_claims": False,
            "current_grep_target": grep_target,
            "inputs": {
                "source_refresh": display_path(source_refresh),
                "race_bridge_receipt": rel(copied_receipt, run_dir),
                "race_evaluation_output": rel(copied_evaluation, run_dir),
                "benchmark_score": "benchmark_score.json",
                "evaluation_ledger": "evaluation_ledger.json",
                "allowed_claims": "allowed_claims.json",
            },
            "rationale": (
                "No official score exists because the RACE scorer is blocked."
                if not score_supported
                else "A single scored case cannot open public score, parity, or "
                "leaderboard claims."
            ),
            "blocked_claims": REQUIRED_BLOCKED_CLAIMS,
            "produced_by_event": "evt_drb_claim_review_0001_written",
        },
    )

    update_deepresearch_bench_allowed_claims(
        run_dir,
        score_supported=score_supported,
        copied_receipt=rel(copied_receipt, run_dir),
        copied_evaluation=rel(copied_evaluation, run_dir),
    )
    append_event(
        run_dir,
        event_id="evt_drb_claim_review_0001_written",
        event_type="deepresearch_bench.claim_review_written",
        inputs=[
            display_path(race_bridge_receipt),
            display_path(bridge_manifest),
            display_path(bridge_evaluation),
            display_path(source_refresh),
        ],
        outputs=[
            rel(copied_receipt, run_dir),
            rel(copied_manifest, run_dir),
            rel(copied_evaluation, run_dir),
            "scorer_manifest.json",
            "benchmark_score.json",
            "evaluation_ledger.json",
            "claim_review.json",
            "allowed_claims.json",
        ],
        summary="Wrote DeepResearch Bench score or blocked-score claim review.",
        replace_existing=True,
    )
    refresh_artifact_manifest(run_dir)
    report = validate_run(case_id, runs_dir=runs_dir)
    if report["status"] != "passed":
        raise HarnessError("DeepResearch Bench claim review failed validation")
    return run_dir


def current_grep_target_from_source_refresh(source: dict[str, Any]) -> dict[str, Any]:
    rows = source.get("official_leaderboard", {}).get("top_rows_observed", [])
    grep_row = next(
        (row for row in rows if str(row.get("model", "")).lower() == "grep-v5"),
        None,
    )
    return {
        "model": "grep-v5",
        "overall_score": grep_row.get("overall_score") if grep_row else None,
        "source": "official_leaderboard.top_rows_observed",
        "leaderboard_csv_sha256": source.get("official_leaderboard", {}).get("csv_sha256"),
        "observed_at": source.get("observed_at"),
        "claim_boundary": (
            "Comparison target only. Alexandria has no parity claim without "
            "scorer-backed multi-case evidence."
        ),
    }


def update_deepresearch_bench_allowed_claims(
    run_dir: Path,
    *,
    score_supported: bool,
    copied_receipt: str,
    copied_evaluation: str,
) -> None:
    allowed_path = run_dir / "allowed_claims.json"
    allowed = read_json(allowed_path)
    blocked = set(allowed.get("blocked_claims", []))
    blocked.update(REQUIRED_BLOCKED_CLAIMS)
    claim = {
        "claim": (
            "One live DeepResearch Bench Codex-DR run has an official-format raw "
            "report and a RACE bridge receipt with score claims blocked."
            if not score_supported
            else "One live DeepResearch Bench Codex-DR run has a scorer-backed RACE "
            "artifact with public score claims still blocked."
        ),
        "scope": "single_case_deepresearch_bench_claim_review_only",
        "supporting_artifacts": [
            copied_receipt,
            copied_evaluation,
            "benchmark_score.json",
            "evaluation_ledger.json",
            "claim_review.json",
        ],
    }
    existing = allowed.get("allowed_claims", [])
    if all(item.get("claim") != claim["claim"] for item in existing):
        existing.append(claim)
    allowed["allowed_claims"] = existing
    allowed["blocked_claims"] = sorted(blocked)
    allowed["claim_review"] = {
        "review_ref": "claim_review.json",
        "score_supported": score_supported,
        "may_widen_public_benchmark_claims": False,
    }
    allowed["produced_by_event"] = "evt_drb_claim_review_0001_written"
    write_json(allowed_path, allowed)


def mesh_bootstrap_plan(
    case_id: str,
    *,
    runs_dir: Path | str | None = None,
    case_index: int = 0,
    case_spec: dict[str, Any] | None = None,
    manifest_source: dict[str, Any] | None = None,
) -> Path:
    run_dir = run_path(case_id, runs_dir)
    case_manifest = build_case_manifest_payload(
        run_id=case_id,
        case_index=case_index,
        case_spec=case_spec,
        manifest_source=manifest_source,
    )
    benchmark_family = case_manifest["benchmark_family"]
    question = case_manifest["generator_visible"]["question"]
    source_policy = case_manifest["generator_visible"]["source_policy"]
    if benchmark_family == BENCHMARK_FAMILY_DEEPRESEARCH_BENCH:
        context_line = "External context: public web sources allowed by run control."
        scorer_line = (
            "The DeepResearch Bench RACE bridge remains blocked until scorer "
            "credentials and explicit provider-run authority exist."
        )
        selected_tools = [
            "filesystem",
            "json_validator",
            "artifact_manifest_hasher",
            "public_web_research",
        ]
        blocked_tools = ["codex_exec", "provider_calls", "benchmark_execution"]
    else:
        context_line = "External context: blocked in provider-off mode."
        scorer_line = "The scorer bridge remains a placeholder and cannot enable benchmark claims."
        selected_tools = ["filesystem", "json_validator", "artifact_manifest_hasher"]
        blocked_tools = ["codex_exec", "provider_calls", "benchmark_execution", "network"]
    write_json(
        run_dir / "case_manifest.json",
        case_manifest,
    )
    write_text(
        run_dir / "plan.md",
        f"""# Codex-DR Mesh Plan

## Objective
Answer the benchmark prompt through the Grep-shaped DR mesh while preserving
case, evidence, event, and claim custody.

## Inputs
- Benchmark family: `{benchmark_family}`.
- User question: {question}
- Files/docs: local case manifest and harness contracts.
- Source policy: {source_policy}
- {context_line}

## Task Graph
Run independent deep-search, data-analysis, and verification branches. Read
branch pointers first, admit selected analysis spans, synthesize, review, create
a re-entry branch when the review requires more research, then write one report.

## Adequacy Checks
- Every role-scoped branch returns pointer, analysis, and evidence files.
- The orchestrator records pointer-first selective reads before synthesis.
- Review findings that require more research create linked re-entry tasks.
- {scorer_line}

## Non-Claims
No benchmark score, Grep parity, provider-backed execution, or product readiness.
""",
    )
    write_json(
        run_dir / "skills_tools.json",
        {
            "schema_version": "codex-dr.skills_tools.v1",
            "run_id": case_id,
            "selected_skills": ["center-of-gravity-recovery", "evidence-first-backpressure"],
            "selected_tools": selected_tools,
            "blocked_tools": blocked_tools,
            "produced_by_event": "evt_0002_plan_written",
        },
    )
    write_json(
        run_dir / "adequacy_criteria.json",
        {
            "schema_version": "codex-dr.adequacy_criteria.v1",
            "run_id": case_id,
            "criteria": [
                {
                    "criterion_id": "adequacy_mesh_branch_triplets",
                    "description": "Each mesh branch returns pointer, analysis, and evidence.",
                    "required": True,
                    "validator": "mesh_branch_triplets_present",
                },
                {
                    "criterion_id": "adequacy_pointer_first_reads",
                    "description": "Orchestrator reads pointers before selected analysis spans.",
                    "required": True,
                    "validator": "pointer_first_receipts_present",
                },
                {
                    "criterion_id": "adequacy_review_reentry",
                    "description": "Review findings that require research create re-entry tasks.",
                    "required": True,
                    "validator": "review_reentry_compiled",
                },
            ],
            "produced_by_event": "evt_0002_plan_written",
        },
    )
    write_json(
        run_dir / "role_configs.json",
        mesh_role_configs(case_id, benchmark_family=benchmark_family),
    )
    write_json(
        run_dir / "task_graph.json",
        mesh_initial_task_graph(case_id, benchmark_family=benchmark_family),
    )
    write_json(run_dir / "terminal_agent_boxes.json", mesh_terminal_agent_boxes(case_id))
    append_event(
        run_dir,
        event_id="evt_0002_plan_written",
        event_type="plan.written",
        outputs=["case_manifest.json", "plan.md", "skills_tools.json", "adequacy_criteria.json"],
        summary="Wrote provider-off DR mesh plan, case manifest, and adequacy criteria.",
    )
    append_event(
        run_dir,
        event_id="evt_0003_role_configs_written",
        event_type="role_configs.written",
        outputs=["role_configs.json"],
        summary="Wrote provider-off fake role adapter configs for DR mesh roles.",
    )
    append_event(
        run_dir,
        event_id="evt_0004_task_graph_written",
        event_type="task_graph.written",
        outputs=["task_graph.json"],
        summary="Wrote DR mesh task graph with dependencies and expected returns.",
    )
    append_event(
        run_dir,
        event_id="evt_0005_agent_box_placeholders",
        event_type="agent_box.placeholder_written",
        outputs=["terminal_agent_boxes.json"],
        summary="Wrote Codex CLI box adapter placeholders; no live box launched.",
    )
    update_manifest_status(run_dir, "planned")
    refresh_artifact_manifest(run_dir)
    return run_dir


def mesh_role_configs(
    case_id: str,
    *,
    benchmark_family: str = BENCHMARK_FAMILY_DRACO,
) -> dict[str, Any]:
    roles = []
    for branch_id, branch in MESH_BRANCH_ROLES.items():
        roles.append(
            {
                "role_config_id": f"role_{branch_id}",
                "run_id": case_id,
                "role": branch["role"],
                "adapter_kind": "provider_off_fake_role",
                "live_adapter_kind": "codex_cli_box",
                "launch_status": "not_launched_current_halt",
                "objective": mesh_branch_objective(branch_id, benchmark_family),
                "input_contract": ["plan.md", "case_manifest.json", "task_graph.json"],
                "return_contract": [
                    f"branches/{branch_id}/pointer.md",
                    f"branches/{branch_id}/analysis.md",
                    f"branches/{branch_id}/evidence.jsonl",
                ],
                "blocked_tools": ["codex_exec", "provider_calls", "benchmark_execution"],
            }
        )
    roles.extend(
        [
            {
                "role_config_id": "role_planner",
                "run_id": case_id,
                "role": "planner",
                "adapter_kind": "provider_off_fake_role",
                "live_adapter_kind": "codex_cli_box",
                "launch_status": "not_launched_current_halt",
                "objective": "Create plan, skills/tools, adequacy criteria, and task graph.",
                "input_contract": ["case_manifest.json"],
                "return_contract": ["plan.md", "skills_tools.json", "task_graph.json"],
                "blocked_tools": ["codex_exec", "provider_calls", "benchmark_execution"],
            },
            {
                "role_config_id": "role_orchestrator",
                "run_id": case_id,
                "role": "orchestrator",
                "adapter_kind": "provider_off_fake_role",
                "live_adapter_kind": "codex_cli_box",
                "launch_status": "not_launched_current_halt",
                "objective": "Read pointers first, synthesize, evaluate gaps, and route re-entry.",
                "input_contract": ["branches/*/pointer.md", "branches/*/analysis.md"],
                "return_contract": ["pointer_read_receipts.jsonl", "synthesis.md"],
                "blocked_tools": ["codex_exec", "provider_calls", "benchmark_execution"],
            },
            {
                "role_config_id": "role_reviewer",
                "run_id": case_id,
                "role": "reviewer",
                "adapter_kind": "provider_off_fake_role",
                "live_adapter_kind": "codex_cli_box",
                "launch_status": "not_launched_current_halt",
                "objective": "Fact-check and decide whether research re-entry is required.",
                "input_contract": [
                    "plan.md",
                    "adequacy_criteria.json",
                    "task_graph.json",
                    "pointer_read_receipts.jsonl",
                    "adequacy_assessments.jsonl",
                    "synthesis.md",
                    "contradictions.json",
                    "report_outline.md",
                    "backpressure/adequacy_backpressure_queue.json",
                ],
                "return_contract": [
                    "reviews/review_001.json",
                ],
                "blocked_tools": ["codex_exec", "provider_calls", "benchmark_execution"],
            },
            {
                "role_config_id": "role_writer",
                "run_id": case_id,
                "role": "writer",
                "adapter_kind": "provider_off_fake_role",
                "live_adapter_kind": "codex_cli_box",
                "launch_status": "not_launched_current_halt",
                "objective": "Write one report from synthesized state and claim ledger.",
                "input_contract": [
                    "synthesis.md",
                    "report_outline.md",
                    "reviews/review_001.json",
                    "adequacy_assessments.jsonl",
                    "backpressure/adequacy_backpressure_queue.json",
                    "backpressure/backpressure_gate_receipt.json",
                    "writer_gate_preflight.json",
                    "claim_ledger.json",
                    "allowed_claims.json",
                ],
                "return_contract": ["report.md"],
                "blocked_tools": ["codex_exec", "provider_calls", "benchmark_execution"],
            },
        ]
    )
    return {
        "schema_version": "codex-dr.role_configs.v1",
        "run_id": case_id,
        "roles": roles,
        "produced_by_event": "evt_0003_role_configs_written",
    }


def mesh_initial_task_graph(
    case_id: str,
    *,
    benchmark_family: str = BENCHMARK_FAMILY_DRACO,
) -> dict[str, Any]:
    branch_tasks = []
    for branch_id in MESH_INITIAL_BRANCH_IDS:
        branch = MESH_BRANCH_ROLES[branch_id]
        task = {
            "task_id": branch["task_id"],
            "kind": "branch_research",
            "objective": mesh_branch_objective(branch_id, benchmark_family),
            "depends_on": ["task_plan"],
            "status": "pending",
            "assigned_box_id": branch["box_id"],
            "role_config_id": f"role_{branch_id}",
            "inputs": ["plan.md", "case_manifest.json"],
            "expected_outputs": [
                f"branches/{branch_id}/pointer.md",
                f"branches/{branch_id}/analysis.md",
                f"branches/{branch_id}/evidence.jsonl",
            ],
            "adequacy_checks": ["adequacy_mesh_branch_triplets"],
            "source_review_finding_id": None,
            "reentry_links": [],
        }
        if branch_id == "deep_search":
            task["evidence_quality_handoff"] = {
                "consumer_task_id": "task_verification",
                "rule": "source_discovery_is_not_source_support",
                "required_before_synthesis_admission": "verification_or_explicit_gap",
            }
        elif branch_id == "data_analysis":
            task["comparability_handoff"] = {
                "consumer_task_id": "task_verification",
                "rule": "comparisons_require_commensurability_check",
                "required_before_ranking_or_forecast": "comparability_assessment_or_non_comparable_inputs",
            }
        elif branch_id == "verification":
            task["verification_handoff"] = {
                "verifies_branch_ids": ["deep_search", "data_analysis"],
                "support_classifications": [
                    "directly_supported",
                    "partially_supported",
                    "indirectly_supported",
                    "unsupported",
                    "contradicted",
                    "source_missing",
                    "too_broad_for_evidence",
                    "non_comparable_inputs",
                ],
            }
        branch_tasks.append(task)
    return {
        "schema_version": "codex-dr.task_graph.v1",
        "run_id": case_id,
        "tasks": [
            {
                "task_id": "task_plan",
                "kind": "planning",
                "objective": "Write DR mesh plan, skills/tools, adequacy criteria, and graph.",
                "depends_on": [],
                "status": "completed",
                "assigned_box_id": "box_planner",
                "role_config_id": "role_planner",
                "inputs": ["case_manifest.json"],
                "expected_outputs": [
                    "plan.md",
                    "skills_tools.json",
                    "adequacy_criteria.json",
                    "task_graph.json",
                ],
                "adequacy_checks": [],
                "source_review_finding_id": None,
                "reentry_links": [],
            },
            *branch_tasks,
            {
                "task_id": "task_pointer_first_synthesis",
                "kind": "evaluate_synthesize",
                "objective": "Read pointers first, admit selected spans, and synthesize gaps.",
                "depends_on": [
                    MESH_BRANCH_ROLES[branch_id]["task_id"]
                    for branch_id in MESH_INITIAL_BRANCH_IDS
                ],
                "status": "pending",
                "assigned_box_id": "box_orchestrator",
                "role_config_id": "role_orchestrator",
                "inputs": [
                    f"branches/{branch_id}/{name}"
                    for branch_id in MESH_INITIAL_BRANCH_IDS
                    for name in ["pointer.md", "analysis.md", "evidence.jsonl"]
                ],
                "expected_outputs": [
                    "pointer_read_receipts.jsonl",
                    "adequacy_assessments.jsonl",
                    "synthesis.md",
                    "contradictions.json",
                    "report_outline.md",
                ],
                "adequacy_checks": ["adequacy_pointer_first_reads"],
                "admission_rules": {
                    "source_discovery_requires_verification": True,
                    "comparative_claims_require_comparability": True,
                    "unsupported_verification_blocks_claim_admission": True,
                },
                "source_review_finding_id": None,
                "reentry_links": [],
            },
            {
                "task_id": "task_review",
                "kind": "review",
                "objective": "Review synthesis and request re-entry if evidence is thin.",
                "depends_on": ["task_pointer_first_synthesis"],
                "status": "pending",
                "assigned_box_id": "box_reviewer",
                "role_config_id": "role_reviewer",
                "inputs": [
                    "plan.md",
                    "adequacy_criteria.json",
                    "task_graph.json",
                    "pointer_read_receipts.jsonl",
                    "adequacy_assessments.jsonl",
                    "synthesis.md",
                    "contradictions.json",
                    "report_outline.md",
                    *[
                        f"branches/{branch_id}/{name}"
                        for branch_id in MESH_INITIAL_BRANCH_IDS
                        for name in ["pointer.md", "analysis.md", "evidence.jsonl"]
                    ],
                    "backpressure/adequacy_backpressure_queue.json",
                ],
                "expected_outputs": [
                    "reviews/review_001.json",
                ],
                "adequacy_checks": ["adequacy_review_reentry"],
                "source_review_finding_id": None,
                "reentry_links": [],
            },
            {
                "task_id": "task_final_writer",
                "kind": "report_writer",
                "objective": "Write report from final synthesis, ledger, and allowed claims.",
                "depends_on": ["task_reentry_followup"],
                "status": "pending",
                "assigned_box_id": "box_writer",
                "role_config_id": "role_writer",
                "inputs": [
                    "synthesis.md",
                    "report_outline.md",
                    "reviews/review_001.json",
                    "adequacy_assessments.jsonl",
                    "backpressure/adequacy_backpressure_queue.json",
                    "claim_ledger.json",
                    "allowed_claims.json",
                ],
                "expected_outputs": ["report.md"],
                "adequacy_checks": [],
                "source_review_finding_id": None,
                "reentry_links": [],
            },
        ],
        "produced_by_event": "evt_0004_task_graph_written",
    }


def mesh_terminal_agent_boxes(case_id: str) -> dict[str, Any]:
    boxes = [
        {
            "box_id": "box_planner",
            "role_config_id": "role_planner",
            "role": "planner",
            "adapter_kind": "provider_off_fake_role",
            "live_command_template": "codex exec --json <role prompt>",
            "launch_status": "not_launched_current_halt",
            "transcript_policy": "would_capture_under_runs_transcripts_when_live",
            "run_id": case_id,
        },
        {
            "box_id": "box_orchestrator",
            "role_config_id": "role_orchestrator",
            "role": "orchestrator",
            "adapter_kind": "provider_off_fake_role",
            "live_command_template": "codex exec --json <orchestrator prompt>",
            "launch_status": "not_launched_current_halt",
            "transcript_policy": "would_capture_under_runs_transcripts_when_live",
            "run_id": case_id,
        },
        {
            "box_id": "box_reviewer",
            "role_config_id": "role_reviewer",
            "role": "reviewer",
            "adapter_kind": "provider_off_fake_role",
            "live_command_template": "codex exec --json <review prompt>",
            "launch_status": "not_launched_current_halt",
            "transcript_policy": "would_capture_under_runs_transcripts_when_live",
            "run_id": case_id,
        },
        {
            "box_id": "box_writer",
            "role_config_id": "role_writer",
            "role": "writer",
            "adapter_kind": "provider_off_fake_role",
            "live_command_template": "codex exec --json <writer prompt>",
            "launch_status": "not_launched_current_halt",
            "transcript_policy": "would_capture_under_runs_transcripts_when_live",
            "run_id": case_id,
        },
    ]
    for branch_id, branch in MESH_BRANCH_ROLES.items():
        boxes.append(
            {
                "box_id": branch["box_id"],
                "role_config_id": f"role_{branch_id}",
                "role": branch["role"],
                "branch_id": branch_id,
                "adapter_kind": "provider_off_fake_role",
                "live_command_template": "codex exec --json <branch prompt>",
                "launch_status": "not_launched_current_halt",
                "transcript_policy": "would_capture_under_runs_transcripts_when_live",
                "run_id": case_id,
            }
        )
    return {
        "schema_version": "codex-dr.terminal_agent_boxes.v1",
        "run_id": case_id,
        "boxes": boxes,
        "produced_by_event": "evt_0005_agent_box_placeholders",
    }


def mesh_bootstrap_branch(
    case_id: str,
    branch_id: str,
    *,
    spawn_event_id: str,
    return_event_id: str,
    runs_dir: Path | str | None = None,
) -> Path:
    validate_id(branch_id, "branch_id")
    if branch_id not in MESH_BRANCH_ROLES:
        raise HarnessError(f"unknown DR mesh branch: {branch_id}")
    run_dir = run_path(case_id, runs_dir)
    branch = MESH_BRANCH_ROLES[branch_id]
    branch_dir = run_dir / "branches" / branch_id
    write_json(
        branch_dir / "branch_manifest.json",
        {
            "schema_version": "codex-dr.branch_manifest.v1",
            "run_id": case_id,
            "branch_id": branch_id,
            "task_id": branch["task_id"],
            "role_config_id": f"role_{branch_id}",
            "objective": branch["objective"],
            "mode": "provider_off_fake_role",
            "adapter_boundary": {
                "live_adapter_kind": "codex_cli_box",
                "launch_status": "not_launched_current_halt",
            },
            "outputs": {
                "pointer": f"branches/{branch_id}/pointer.md",
                "analysis": f"branches/{branch_id}/analysis.md",
                "evidence": f"branches/{branch_id}/evidence.jsonl",
            },
            "produced_by_event": spawn_event_id,
        },
    )
    write_text(
        branch_dir / "pointer.md",
        f"""# {branch_id.replace('_', ' ').title()} Pointer

## Objective
{branch["objective"]}

## Key Findings
- This provider-off role adapter preserved the branch return shape.
- The branch supports topology custody only, not benchmark performance.

## Evidence Map
- `{branch["evidence_id"]}` supports the branch-return custody claim.

## Analysis Spans
- `{branch["analysis_section"]}` in `analysis.md`.

## Read Next
Read only the named analysis span after this pointer.
""",
    )
    write_text(
        branch_dir / "analysis.md",
        f"""# {branch_id.replace('_', ' ').title()} Analysis

## {branch["analysis_section"]}
The provider-off fake role adapter produced deterministic content for
`{branch_id}`. The only supported finding is that the DR mesh can route a
role-scoped branch through pointer, analysis, evidence, event, and artifact
custody without launching Codex CLI.

## Unread Fixture Section
This section exists to prove selective span admission; the orchestrator does not
need it for the provider-off topology claim.
""",
    )
    write_jsonl(
        branch_dir / "evidence.jsonl",
        [
            {
                "schema_version": "codex-dr.evidence_item.v1",
                "evidence_id": branch["evidence_id"],
                "run_id": case_id,
                "branch_id": branch_id,
                "record_type": "custody_evidence",
                "source_type": "local_fixture",
                "source_ref": f"provider-off fake role adapter {branch_id}",
                "supports": ["claim_provider_off_mesh_topology_preserved"],
                "quote_or_summary": (
                    "The branch return contains pointer, analysis, and evidence "
                    "files under event and artifact custody."
                ),
                "admission_status": "admitted",
                "produced_by_event": return_event_id,
            }
        ],
    )
    append_event(
        run_dir,
        event_id=spawn_event_id,
        event_type="branch.spawn_declared",
        outputs=[f"branches/{branch_id}/branch_manifest.json"],
        decision={
            "decision_id": f"dec_spawn_{branch_id}",
            "decision_type": "spawn_branch",
            "rationale": f"DR mesh task graph requires the {branch_id} role branch.",
            "status": "accepted",
        },
        summary=f"Declared provider-off DR mesh branch spawn for {branch_id}.",
    )
    append_event(
        run_dir,
        event_id=return_event_id,
        event_type="branch.return_written",
        outputs=[
            f"branches/{branch_id}/pointer.md",
            f"branches/{branch_id}/analysis.md",
            f"branches/{branch_id}/evidence.jsonl",
        ],
        summary=f"Wrote provider-off DR mesh branch return triplet for {branch_id}.",
    )
    mark_task(run_dir, branch["task_id"], "completed")
    update_manifest_status(run_dir, "branched")
    refresh_artifact_manifest(run_dir)
    return run_dir


def mesh_branch_event_ids(branch_id: str) -> tuple[str, str]:
    event_ids = {
        "deep_search": (
            "evt_0006_deep_search_spawn_declared",
            "evt_0007_deep_search_return_written",
        ),
        "data_analysis": (
            "evt_0008_data_analysis_spawn_declared",
            "evt_0009_data_analysis_return_written",
        ),
        "verification": (
            "evt_0010_verification_spawn_declared",
            "evt_0011_verification_return_written",
        ),
        "reentry_followup": (
            "evt_0017_reentry_spawn_declared",
            "evt_0018_reentry_return_written",
        ),
    }
    if branch_id not in event_ids:
        raise HarnessError(f"unknown DR mesh branch: {branch_id}")
    return event_ids[branch_id]


def mesh_record_pointer_reads(
    case_id: str,
    branch_ids: list[str],
    *,
    event_id: str,
    runs_dir: Path | str | None = None,
) -> Path:
    run_dir = run_path(case_id, runs_dir)
    rows = []
    for branch_id in branch_ids:
        branch = MESH_BRANCH_ROLES[branch_id]
        rows.append(
            {
                "schema_version": "codex-dr.pointer_read_receipt.v1",
                "run_id": case_id,
                "receipt_id": f"ptr_read_{branch_id}",
                "branch_id": branch_id,
                "pointer_path": f"branches/{branch_id}/pointer.md",
                "pointer_read_before_analysis": True,
                "selected_analysis_spans": [
                    {
                        "analysis_path": f"branches/{branch_id}/analysis.md",
                        "section": branch["analysis_section"],
                        "reason": "Named by pointer and needed for topology synthesis.",
                    }
                ],
                "evidence_paths": [f"branches/{branch_id}/evidence.jsonl"],
                "produced_by_event": event_id,
            }
        )
    write_jsonl(run_dir / "pointer_read_receipts.jsonl", rows)
    append_event(
        run_dir,
        event_id=event_id,
        event_type="pointer_reads.recorded",
        outputs=["pointer_read_receipts.jsonl"],
        summary="Recorded pointer-first selective analysis reads for DR mesh branches.",
    )
    refresh_artifact_manifest(run_dir)
    return run_dir


def mesh_bootstrap_evaluate(case_id: str, *, runs_dir: Path | str | None = None) -> Path:
    run_dir = run_path(case_id, runs_dir)
    mesh_record_pointer_reads(
        case_id,
        MESH_INITIAL_BRANCH_IDS,
        event_id="evt_0012_pointer_reads_recorded",
        runs_dir=runs_dir,
    )
    write_jsonl(
        run_dir / "adequacy_assessments.jsonl",
        [
            {
                "schema_version": "codex-dr.adequacy_assessment.v1",
                "run_id": case_id,
                "assessment_id": "adequacy_initial_001",
                "criteria_checked": [
                    "adequacy_mesh_branch_triplets",
                    "adequacy_pointer_first_reads",
                ],
                "branch_ids": MESH_INITIAL_BRANCH_IDS,
                "status": "needs_review",
                "gaps": ["reviewer must pressure claim boundary before final report"],
                "decision_event_id": "evt_0013_adequacy_assessed",
                "produced_by_event": "evt_0013_adequacy_assessed",
            }
        ],
    )
    append_event(
        run_dir,
        event_id="evt_0013_adequacy_assessed",
        event_type="adequacy.assessed",
        outputs=["adequacy_assessments.jsonl"],
        decision={
            "decision_id": "dec_assess_initial_mesh",
            "decision_type": "review_before_report",
            "rationale": "Initial branch coverage is shaped but needs outer-loop review.",
            "status": "accepted",
        },
        summary="Assessed initial DR mesh branch adequacy.",
    )
    write_mesh_synthesis(
        run_dir,
        case_id,
        event_id="evt_0014_synthesis_written",
        branch_ids=MESH_INITIAL_BRANCH_IDS,
        review_impact="Review has not yet run.",
    )
    mark_task(run_dir, "task_pointer_first_synthesis", "completed")
    update_manifest_status(run_dir, "synthesized")
    refresh_artifact_manifest(run_dir)
    return run_dir


def write_mesh_synthesis(
    run_dir: Path,
    case_id: str,
    *,
    event_id: str,
    branch_ids: list[str],
    review_impact: str,
) -> None:
    branch_lines = "\n".join(
        f"- `{MESH_BRANCH_ROLES[branch_id]['evidence_id']}`" for branch_id in branch_ids
    )
    write_text(
        run_dir / "synthesis.md",
        f"""# DR Mesh Synthesis

## Pointer-First Admissions
The orchestrator admitted selected analysis spans only after reading branch
pointers for: {", ".join(branch_ids)}.

## Admitted Evidence
{branch_lines}

## Contradictions
No real-world contradiction is asserted by this provider-off fixture.

## Unresolveds
Benchmark scoring and live Codex CLI research remain blocked by run-control.

## Claims Ready For Ledger
- The provider-off DR mesh fixture preserves planner, task graph, branch,
  pointer-first, review re-entry, and writer custody topology.

## Review Impact
{review_impact}
""",
    )
    write_json(
        run_dir / "contradictions.json",
        {
            "schema_version": "codex-dr.contradictions.v1",
            "run_id": case_id,
            "contradictions": [
                {
                    "contradiction_id": "contradiction_none_001",
                    "issue": "No real contradiction in provider-off DR mesh fixture.",
                    "positions": [],
                    "adjudication_status": "not_applicable",
                    "unresolved": False,
                    "report_treatment": "Keep benchmark and parity claims blocked.",
                }
            ],
            "produced_by_event": event_id,
        },
    )
    write_text(
        run_dir / "report_outline.md",
        """# Report Outline

1. Scope and halt state
2. Planner and task graph
3. Branch returns and pointer-first reads
4. Review pressure and re-entry
5. Scorer bridge placeholder
6. Claim ledger and non-claims
""",
    )
    append_event(
        run_dir,
        event_id=event_id,
        event_type="synthesis.written",
        outputs=["synthesis.md", "contradictions.json", "report_outline.md"],
        summary="Wrote provider-off DR mesh synthesis and report outline.",
    )


def mesh_bootstrap_review(case_id: str, *, runs_dir: Path | str | None = None) -> Path:
    run_dir = run_path(case_id, runs_dir)
    write_json(
        run_dir / "reviews" / "review_001.json",
        {
            "schema_version": "codex-dr.review.v1",
            "run_id": case_id,
            "review_id": "review_001",
            "reviewer_role": "provider_off_fact_checker",
            "target_artifacts": ["synthesis.md", "pointer_read_receipts.jsonl"],
            "rubric_results": [
                {
                    "rubric_id": "pointer_first_context_economy",
                    "status": "pass",
                    "notes": "Pointer receipts exist for initial mesh branches.",
                },
                {
                    "rubric_id": "claim_boundary",
                    "status": "needs_reentry",
                    "notes": "Require a focused follow-up before report writing.",
                },
            ],
            "findings": [
                {
                    "finding_id": "finding_reentry_001",
                    "severity": "major",
                    "finding_type": "thin_evidence",
                    "summary": (
                        "Add a targeted re-entry branch proving review pressure changes state."
                    ),
                    "evidence_refs": ["pointer_read_receipts.jsonl#ptr_read_verification"],
                    "requires_reentry": True,
                    "recommended_task": "Run a provider-off re-entry follow-up branch.",
                }
            ],
            "produced_by_event": "evt_0015_review_written",
        },
    )
    append_event(
        run_dir,
        event_id="evt_0015_review_written",
        event_type="review.written",
        outputs=["reviews/review_001.json"],
        summary="Wrote DR mesh review requiring a re-entry branch.",
    )
    mark_task(run_dir, "task_review", "completed")
    update_manifest_status(run_dir, "reviewed")
    refresh_artifact_manifest(run_dir)
    return run_dir


def mesh_bootstrap_reentry(
    case_id: str,
    review_id: str = "review_001",
    *,
    runs_dir: Path | str | None = None,
) -> Path:
    run_dir = run_path(case_id, runs_dir)
    review = read_json(run_dir / "reviews" / f"{review_id}.json")
    finding = next(finding for finding in review["findings"] if finding["requires_reentry"])
    task = {
        "task_id": "task_reentry_followup",
        "kind": "reentry_research",
        "objective": finding["recommended_task"],
        "depends_on": ["task_review"],
        "status": "pending",
        "assigned_box_id": MESH_BRANCH_ROLES["reentry_followup"]["box_id"],
        "role_config_id": "role_reentry_followup",
        "inputs": ["reviews/review_001.json", "synthesis.md"],
        "expected_outputs": [
            "branches/reentry_followup/pointer.md",
            "branches/reentry_followup/analysis.md",
            "branches/reentry_followup/evidence.jsonl",
        ],
        "adequacy_checks": ["adequacy_review_reentry"],
        "source_review_finding_id": finding["finding_id"],
        "reentry_links": [{"review_id": review_id, "finding_id": finding["finding_id"]}],
    }
    reentry_synthesis_task = {
        "task_id": "task_reentry_synthesis",
        "kind": "evaluate_synthesize",
        "objective": (
            "Read the re-entry pointer after the initial branch pointers, admit selected "
            "spans, update synthesis, and close or preserve remaining gaps."
        ),
        "depends_on": ["task_reentry_followup"],
        "status": "pending",
        "assigned_box_id": "box_orchestrator",
        "role_config_id": "role_orchestrator",
        "inputs": [
            f"branches/{branch_id}/{name}"
            for branch_id in MESH_ALL_BRANCH_IDS
            for name in ["pointer.md", "analysis.md", "evidence.jsonl"]
        ]
        + ["reviews/review_001.json"],
        "expected_outputs": [
            "pointer_read_receipts.jsonl",
            "adequacy_assessments.jsonl",
            "synthesis.md",
            "contradictions.json",
            "report_outline.md",
        ],
        "adequacy_checks": ["adequacy_pointer_first_reads", "adequacy_review_reentry"],
        "source_review_finding_id": finding["finding_id"],
        "reentry_links": [{"review_id": review_id, "finding_id": finding["finding_id"]}],
    }
    graph_path = run_dir / "task_graph.json"
    graph = read_json(graph_path)
    graph["tasks"] = [
        existing
        for existing in graph["tasks"]
        if existing["task_id"] not in {task["task_id"], reentry_synthesis_task["task_id"]}
    ]
    graph["tasks"].append(task)
    graph["tasks"].append(reentry_synthesis_task)
    for existing in graph["tasks"]:
        if existing["task_id"] == "task_final_writer":
            existing["depends_on"] = ["task_reentry_synthesis"]
            existing["inputs"] = [
                "synthesis.md",
                "report_outline.md",
                "reviews/review_001.json",
                "adequacy_assessments.jsonl",
                "backpressure/adequacy_backpressure_queue.json",
                "branches/reentry_followup/pointer.md",
                "branches/reentry_followup/analysis.md",
                "branches/reentry_followup/evidence.jsonl",
                "claim_ledger.json",
                "allowed_claims.json",
            ]
    write_json(graph_path, graph)
    write_jsonl(
        run_dir / "reentry_decisions.jsonl",
        [
            {
                "schema_version": "codex-dr.reentry_decision.v1",
                "run_id": case_id,
                "decision_id": "reentry_001",
                "review_id": review_id,
                "finding_id": finding["finding_id"],
                "decision": "create_task",
                "rationale": "Major finding requires research-state change before writing.",
                "created_task_id": "task_reentry_followup",
                "task_graph_path": "task_graph.json",
                "produced_by_event": "evt_0016_reentry_compiled",
            }
        ],
    )
    append_event(
        run_dir,
        event_id="evt_0016_reentry_compiled",
        event_type="reentry.compiled",
        inputs=[f"reviews/{review_id}.json"],
        outputs=["reentry_decisions.jsonl", "task_graph.json"],
        decision={
            "decision_id": "dec_reentry_followup",
            "decision_type": "reenter",
            "rationale": "Review finding requires a targeted follow-up branch.",
            "status": "accepted",
        },
        summary="Compiled DR mesh review finding into re-entry task.",
    )
    mesh_bootstrap_branch(
        case_id,
        "reentry_followup",
        spawn_event_id="evt_0017_reentry_spawn_declared",
        return_event_id="evt_0018_reentry_return_written",
        runs_dir=runs_dir,
    )
    mesh_record_pointer_reads(
        case_id,
        MESH_ALL_BRANCH_IDS,
        event_id="evt_0019_pointer_reads_recorded",
        runs_dir=runs_dir,
    )
    write_jsonl(
        run_dir / "adequacy_assessments.jsonl",
        [
            {
                "schema_version": "codex-dr.adequacy_assessment.v1",
                "run_id": case_id,
                "assessment_id": "adequacy_final_001",
                "criteria_checked": [
                    "adequacy_mesh_branch_triplets",
                    "adequacy_pointer_first_reads",
                    "adequacy_review_reentry",
                ],
                "branch_ids": MESH_ALL_BRANCH_IDS,
                "status": "satisfied_for_provider_off_topology",
                "gaps": ["live Codex CLI execution and benchmark scoring remain blocked"],
                "decision_event_id": "evt_0020_adequacy_assessed",
                "produced_by_event": "evt_0020_adequacy_assessed",
            }
        ],
    )
    append_event(
        run_dir,
        event_id="evt_0020_adequacy_assessed",
        event_type="adequacy.assessed",
        outputs=["adequacy_assessments.jsonl"],
        decision={
            "decision_id": "dec_assess_final_mesh",
            "decision_type": "write_report",
            "rationale": "Provider-off topology is satisfied after re-entry branch.",
            "status": "accepted",
        },
        summary="Assessed final provider-off DR mesh adequacy.",
    )
    write_mesh_synthesis(
        run_dir,
        case_id,
        event_id="evt_0021_synthesis_written",
        branch_ids=MESH_ALL_BRANCH_IDS,
        review_impact="Review finding compiled into `task_reentry_followup` and returned.",
    )
    update_manifest_status(run_dir, "reentered")
    refresh_artifact_manifest(run_dir)
    return run_dir


def mesh_bootstrap_report(case_id: str, *, runs_dir: Path | str | None = None) -> Path:
    run_dir = run_path(case_id, runs_dir)
    write_json(
        run_dir / "compactions" / "compaction_001.json",
        {
            "schema_version": "codex-dr.compaction_receipt.v1",
            "run_id": case_id,
            "compaction_id": "compaction_001",
            "mode": "provider_off_dr_mesh",
            "input_artifacts": [
                "plan.md",
                "pointer_read_receipts.jsonl",
                "synthesis.md",
                "reviews/review_001.json",
            ],
            "output_artifact": "compactions/compaction_001.json",
            "scope": "DR mesh provider-off state summary",
            "claim_impact": "no claim widening",
            "produced_by_event": "evt_0022_compaction_receipt_written",
        },
    )
    append_event(
        run_dir,
        event_id="evt_0022_compaction_receipt_written",
        event_type="compaction.receipt_written",
        outputs=["compactions/compaction_001.json"],
        summary="Wrote provider-off DR mesh compaction receipt.",
    )
    claim_text = (
        "The provider-off DR mesh fixture preserves planner, task graph, branch, "
        "pointer-first, review re-entry, and writer custody topology."
    )
    write_json(
        run_dir / "claim_ledger.json",
        {
            "schema_version": "codex-dr.claim_ledger.v1",
            "run_id": case_id,
            "claims": [
                {
                    "claim_id": "claim_provider_off_mesh_topology_preserved",
                    "text": claim_text,
                    "materiality": "provider_off_topology",
                    "status": "admitted",
                    "source_artifact_refs": [
                        "branches/deep_search/evidence.jsonl#ev_deep_search_001",
                        "branches/data_analysis/evidence.jsonl#ev_data_analysis_001",
                        "branches/verification/evidence.jsonl#ev_verification_001",
                        "branches/reentry_followup/evidence.jsonl#ev_reentry_followup_001",
                    ],
                    "intermediate_artifact_refs": [
                        "task_graph.json",
                        "pointer_read_receipts.jsonl",
                        "reviews/review_001.json",
                        "reentry_decisions.jsonl",
                        "synthesis.md",
                    ],
                    "blocked_from_public_claims": False,
                }
            ],
            "produced_by_event": "evt_0023_claim_ledger_written",
        },
    )
    append_event(
        run_dir,
        event_id="evt_0023_claim_ledger_written",
        event_type="claim_ledger.written",
        outputs=["claim_ledger.json"],
        summary="Wrote provider-off DR mesh claim ledger.",
    )
    write_json(
        run_dir / "allowed_claims.json",
        {
            "schema_version": "codex-dr.allowed_claims.v1",
            "run_id": case_id,
            "allowed_claims": [
                {
                    "claim": (
                        "The provider-off DR mesh topology fixture emitted and "
                        "validated deterministic local custody artifacts."
                    ),
                    "scope": "local_fixture_only",
                    "supporting_artifacts": ["validation_report.json", "claim_ledger.json"],
                }
            ],
            "blocked_claims": REQUIRED_BLOCKED_CLAIMS,
            "produced_by_event": "evt_0024_allowed_claims_written",
        },
    )
    append_event(
        run_dir,
        event_id="evt_0024_allowed_claims_written",
        event_type="allowed_claims.written",
        outputs=["allowed_claims.json"],
        summary="Wrote provider-off DR mesh allowed claims.",
    )
    write_text(
        run_dir / "report.md",
        f"""# Provider-Off DR Mesh Report

## Scope
This deterministic local fixture exercises DR mesh topology without launching
Codex CLI, spending provider tokens, or executing benchmarks.

## What Ran
The planner emitted a plan, skills/tools, adequacy criteria, and a task graph.
Three scoped fake role adapters produced branch returns, the orchestrator read
pointers first, review required re-entry, and a follow-up branch returned before
the writer produced this report.

## Admitted Claim
{claim_text}

## Scorer Bridge
The scorer bridge is present only as a blocked placeholder.

## Non-Claims
- No benchmark score.
- No Grep parity.
- No provider-backed execution.
- No product service readiness.
""",
    )
    append_event(
        run_dir,
        event_id="evt_0025_report_written",
        event_type="report.written",
        outputs=["report.md"],
        summary="Wrote provider-off DR mesh report.",
    )
    mark_task(run_dir, "task_final_writer", "completed")
    update_manifest_status(run_dir, "reported")
    refresh_artifact_manifest(run_dir)
    return run_dir


def mesh_bootstrap_score(case_id: str, *, runs_dir: Path | str | None = None) -> Path:
    run_dir = run_path(case_id, runs_dir)
    case_manifest = read_json(run_dir / "case_manifest.json")
    write_json(
        run_dir / "scorer_manifest.json",
        {
            "schema_version": "codex-dr.draco_scorer_manifest.v1",
            "run_id": case_id,
            "benchmark_family": "DRACO",
            "scorer_status": "blocked",
            "scorer_available": False,
            "execution_allowed": False,
            "manifest_schema": "sandbox/codex-dr/harness-specs/draco_scorer_manifest.schema.json",
            "evaluation_output_schema": (
                "sandbox/codex-dr/harness-specs/draco_evaluation_output.schema.json"
            ),
            "case_manifest": "case_manifest.json",
            "judge_policy": {
                "kind": "model_judge",
                "provider": "evidence-pending",
                "model": "evidence-pending",
                "prompt_version": "evidence-pending",
                "parameters": {
                    "temperature": "evidence-pending",
                    "reasoning_effort": "evidence-pending",
                },
                "execution_status": "blocked_until_run_control_and_scorer_approval",
            },
            "rubric_mapping": [
                {
                    "criterion_group": "factual_accuracy",
                    "draco_axis": "factual accuracy",
                    "output_field": "criterion_verdicts[].factual_accuracy",
                },
                {
                    "criterion_group": "breadth_depth",
                    "draco_axis": "breadth and depth",
                    "output_field": "criterion_verdicts[].breadth_depth",
                },
                {
                    "criterion_group": "presentation_quality",
                    "draco_axis": "presentation quality",
                    "output_field": "criterion_verdicts[].presentation_quality",
                },
                {
                    "criterion_group": "citation_quality",
                    "draco_axis": "citation quality",
                    "output_field": "criterion_verdicts[].citation_quality",
                },
                {
                    "criterion_group": "negative_penalties",
                    "draco_axis": "weighted negative criteria and safety penalties",
                    "output_field": "penalties[]",
                },
            ],
            "scoring_formula": {
                "raw_score": "sum(weight * criterion_verdict) over DRACO criteria",
                "normalized_score": "raw score normalized by DRACO task rubric bounds",
                "score_range": [0, 1],
                "blocked_until": "approved scorer implementation and sealed reference policy",
            },
            "sealed_reference_policy": {
                "status": "sealed_until_scoring",
                "reference_answers_visible_to_generator": False,
                "rubric_payload_visible_to_generator": False,
                "allowed_reader": "approved scorer only",
            },
            "retry_policy": {
                "max_attempts": 1,
                "automatic_retry_allowed": False,
            },
            "variance_policy": {
                "status": "not_estimated_for_single_smoke",
                "requires": "approved repeated-run or judge-variance protocol",
            },
            "output_paths": {
                "evaluation_output": "draco_evaluation_output.json",
                "benchmark_score": "benchmark_score.json",
                "judge_transcript_root": "transcripts/scorer/",
            },
            "claim_boundary": {
                "numeric_score_allowed": False,
                "blocked_claims": [
                    "DRACO score",
                    "Grep parity",
                    "leaderboard rank",
                    "product readiness",
                ],
            },
            "blocked_reason": (
                "No benchmark execution or scorer call is allowed in provider-off mode."
            ),
            "produced_by_event": "evt_0026_scorer_bridge_written",
        },
    )
    append_event(
        run_dir,
        event_id="evt_0026_scorer_bridge_written",
        event_type="scorer_bridge.written",
        outputs=["scorer_manifest.json"],
        summary="Wrote provider-off DR mesh scorer bridge placeholder.",
    )
    write_json(
        run_dir / "benchmark_score.json",
        {
            "schema_version": "codex-dr.benchmark_score.v1",
            "run_id": case_id,
            "mode": "provider_off_placeholder",
            "benchmark_family": "DRACO",
            "case_manifest": "case_manifest.json",
            "scorer_manifest": "scorer_manifest.json",
            "evaluation_output": None,
            "score": None,
            "raw_score": None,
            "normalized_score": None,
            "claims_enabled": False,
            "reason": "Scoring remains blocked until a live run and scorer path are approved.",
            "produced_by_event": "evt_0027_benchmark_placeholder_written",
        },
    )
    append_event(
        run_dir,
        event_id="evt_0027_benchmark_placeholder_written",
        event_type="benchmark.placeholder_written",
        outputs=["benchmark_score.json"],
        summary="Wrote provider-off DR mesh benchmark placeholder.",
    )
    write_json(
        run_dir / "evaluation_ledger.json",
        {
            "schema_version": "codex-dr.benchmark_evaluation_ledger.v1",
            "run_id": case_id,
            "benchmark_family": "DRACO",
            "case_id": case_manifest.get("case_id"),
            "scorer_manifest": "scorer_manifest.json",
            "benchmark_score": "benchmark_score.json",
            "result_status": "blocked_no_score",
            "score_status": {
                "score": None,
                "raw_score": None,
                "normalized_score": None,
                "claims_enabled": False,
                "scorer_custody_present": False,
            },
            "failure_taxonomy": [
                {
                    "failure_class": "scorer_missing",
                    "severity": "blocking",
                    "root_cause": "No approved judge/scorer execution path exists.",
                    "blocks": ["DRACO score", "Grep parity", "leaderboard rank"],
                },
                {
                    "failure_class": "provider_off_placeholder",
                    "severity": "blocking",
                    "root_cause": "Provider-off fixture cannot evaluate answer quality.",
                    "blocks": ["benchmark execution success"],
                },
            ],
            "improvement_recommendations": [
                {
                    "recommendation_id": "rec_draco_scorer_manifest_001",
                    "target_surface": "scorer_manifest.json",
                    "action": (
                        "Approve scorer policy, judge prompt, sealed-reference rule, "
                        "and custody before scoring."
                    ),
                },
                {
                    "recommendation_id": "rec_claim_gate_001",
                    "target_surface": "allowed_claims.json",
                    "action": (
                        "Keep benchmark and parity claims blocked until scorer custody "
                        "validates a non-placeholder score."
                    ),
                },
            ],
            "allowed_claim_impact": {
                "may_widen_claims": False,
                "claim_gate_status": "blocked",
                "reason": "Evaluation is blocked and benchmark_score.json is a placeholder.",
                "blocked_claims": [
                    "DRACO score",
                    "Grep parity",
                    "leaderboard rank",
                    "product readiness",
                ],
            },
            "produced_by_event": "evt_0027_eval_ledger_written",
        },
    )
    append_event(
        run_dir,
        event_id="evt_0027_eval_ledger_written",
        event_type="evaluation_ledger.written",
        inputs=["scorer_manifest.json", "benchmark_score.json"],
        outputs=["evaluation_ledger.json"],
        summary="Wrote benchmark evaluation ledger with claim widening blocked.",
    )
    update_manifest_status(run_dir, "scoring_blocked")
    refresh_artifact_manifest(run_dir)
    return run_dir


def mesh_bootstrap_self_improve(
    case_id: str, *, runs_dir: Path | str | None = None
) -> Path:
    run_dir = run_path(case_id, runs_dir)
    taxonomy = read_json(SELF_IMPROVEMENT_TAXONOMY_PATH)
    corpus = read_json(SELF_IMPROVEMENT_CORPUS_PATH)
    evaluation_ledger = read_json(run_dir / "evaluation_ledger.json")
    evaluation_failures = evaluation_ledger.get("failure_taxonomy", [])
    recommendations = evaluation_ledger.get("improvement_recommendations", [])
    write_json(
        run_dir / "self_improvement" / "replay_corpus.json",
        {
            **corpus,
            "run_id": case_id,
            "source_evaluation_ledger": "evaluation_ledger.json",
            "evaluation_failures": evaluation_failures,
            "source_recommendations": recommendations,
            "source_ref": rel(SELF_IMPROVEMENT_CORPUS_PATH, SANDBOX_ROOT),
            "produced_by_event": "evt_0030_self_improvement_replay_written",
        },
    )
    write_json(
        run_dir / "self_improvement" / "failure_taxonomy.json",
        {
            **taxonomy,
            "run_id": case_id,
            "source_ref": rel(SELF_IMPROVEMENT_TAXONOMY_PATH, SANDBOX_ROOT),
            "produced_by_event": "evt_0030_self_improvement_replay_written",
        },
    )
    append_event(
        run_dir,
        event_id="evt_0030_self_improvement_replay_written",
        event_type="self_improvement.replay_written",
        inputs=["evaluation_ledger.json", "allowed_claims.json"],
        outputs=[
            "self_improvement/replay_corpus.json",
            "self_improvement/failure_taxonomy.json",
        ],
        summary="Wrote provider-off self-improvement replay corpus and taxonomy.",
    )
    write_json(
        run_dir / "self_improvement" / "improvement_proposal.json",
        {
            "schema_version": "codex-dr.improvement_proposal.v1",
            "run_id": case_id,
            "proposal_id": "proposal_prompt_claim_boundary_001",
            "source_fixture_id": "failed_eval_claim_widening_001",
            "source_evaluation_ledger": "evaluation_ledger.json",
            "source_evaluation_failures": [
                failure.get("failure_class")
                for failure in evaluation_failures
                if failure.get("failure_class")
            ],
            "source_recommendation_ids": [
                recommendation.get("recommendation_id")
                for recommendation in recommendations
                if recommendation.get("recommendation_id")
            ],
            "failure_classes": ["claim_boundary", "evidence", "prompt"],
            "target_surfaces": [
                "sandbox/codex-dr/harness-specs/live_role_prompt_pack.md",
                "role_configs.json",
            ],
            "suggested_patch": {
                "prompt_patch": (
                    "Strengthen scorer and writer prompts to state that placeholder "
                    "benchmark outputs can never widen DRACO or parity claims."
                ),
                "role_config_patch": {
                    "role": "writer",
                    "additional_blocked_claim": (
                        "DRACO score until scorer custody validates "
                        "benchmark_score.json"
                    ),
                },
            },
            "promotion_status": "proposed_not_promoted",
            "auto_promotion_allowed": False,
            "automatic_skill_mutation_allowed": False,
            "claim_impact": "no claim widening",
            "produced_by_event": "evt_0031_self_improvement_proposal_written",
        },
    )
    append_event(
        run_dir,
        event_id="evt_0031_self_improvement_proposal_written",
        event_type="self_improvement.proposal_written",
        inputs=[
            "self_improvement/replay_corpus.json",
            "self_improvement/failure_taxonomy.json",
        ],
        outputs=["self_improvement/improvement_proposal.json"],
        summary="Wrote no-auto-promotion improvement proposal.",
    )
    write_json(
        run_dir / "self_improvement" / "regression_gate.json",
        {
            "schema_version": "codex-dr.self_improvement_regression_gate.v1",
            "run_id": case_id,
            "gate_id": "self_improvement_provider_off_gate_001",
            "prior_passing_cases_remain_passing": True,
            "failed_cases_cannot_widen_claims": True,
            "regression_evidence_required_for_promotion": True,
            "automatic_skill_mutation_allowed": False,
            "proposal_promotion_allowed": False,
            "checks": [
                {
                    "check_id": "provider_off_mesh_validation_stays_green",
                    "status": "passed",
                    "evidence": "validate_run required checks remain passing before mutation.",
                },
                {
                    "check_id": "failed_eval_claim_widening_blocked",
                    "status": "passed",
                    "evidence": "benchmark_evaluation_claim_gate_enforced blocks widening.",
                },
                {
                    "check_id": "proposal_not_auto_promoted",
                    "status": "passed",
                    "evidence": "improvement_proposal.auto_promotion_allowed is false.",
                },
            ],
            "blocked_claims": [
                "live benchmark improvement",
                "DRACO score improvement",
                "Grep parity",
                "automatic skill mutation",
            ],
            "produced_by_event": "evt_0032_self_improvement_regression_gate_written",
        },
    )
    append_event(
        run_dir,
        event_id="evt_0032_self_improvement_regression_gate_written",
        event_type="self_improvement.regression_gate_written",
        inputs=[
            "self_improvement/improvement_proposal.json",
            "evaluation_ledger.json",
            "allowed_claims.json",
        ],
        outputs=["self_improvement/regression_gate.json"],
        summary="Wrote provider-off self-improvement regression gate.",
    )
    update_manifest_status(run_dir, "self_improvement_blocked_from_promotion")
    refresh_artifact_manifest(run_dir)
    return run_dir


def deepresearch_bench_improvement_compile(
    case_id: str, *, runs_dir: Path | str | None = None
) -> Path:
    run_dir = run_path(case_id, runs_dir)
    case_manifest = read_json(run_dir / "case_manifest.json")
    if case_manifest.get("benchmark_family") != BENCHMARK_FAMILY_DEEPRESEARCH_BENCH:
        raise HarnessError("DeepResearch Bench improvement compile requires a DRB case")
    evaluation_ledger = read_json(run_dir / "evaluation_ledger.json")
    claim_review = read_json(run_dir / "claim_review.json")
    allowed_claims = read_json(run_dir / "allowed_claims.json")
    taxonomy = read_json(SELF_IMPROVEMENT_TAXONOMY_PATH)
    base_corpus = read_json(SELF_IMPROVEMENT_CORPUS_PATH)
    review = read_optional_json(run_dir / "reviews" / "review_001.json")
    adequacy_rows = read_optional_jsonl(run_dir / "adequacy_assessments.jsonl")
    context_index = read_optional_json(run_dir / "live_executor" / "context_thread_index.json")

    evaluation_failures = evaluation_ledger.get("failure_taxonomy", [])
    recommendations = evaluation_ledger.get("improvement_recommendations", [])
    review_findings = extract_review_failure_surfaces(review)
    unresolved_adequacy = [
        row
        for row in adequacy_rows
        if row.get("remaining_gaps")
        or row.get("remaining_gap")
        or row.get("unresolved_gap")
        or str(row.get("status", "")).lower()
        in {"open", "not_satisfied", "not_satisfied_for_closure"}
        or "gap" in str(row.get("status", "")).lower()
    ]
    source_failure_refs = compile_source_failure_refs(
        evaluation_failures=evaluation_failures,
        review_findings=review_findings,
        unresolved_adequacy=unresolved_adequacy,
        claim_review=claim_review,
    )
    if not source_failure_refs:
        raise HarnessError("no source failures available for improvement compilation")

    replay_fixtures = [
        {
            "fixture_id": "fixture_drb_blocked_scorer_claims_001",
            "kind": "failed_evaluation",
            "input_artifacts": [
                "evaluation_ledger.json",
                "benchmark_score.json",
                "claim_review.json",
                "allowed_claims.json",
            ],
            "failure_classes": ["scorer_integration", "claim_boundary"],
            "failure_summary": (
                "Official RACE scoring is blocked by missing provider authority and "
                "must not widen DeepResearch Bench or Grep parity claims."
            ),
            "expected_gate": "blocked",
        },
        {
            "fixture_id": "fixture_drb_numeric_appendix_gap_001",
            "kind": "failed_evaluation",
            "input_artifacts": [
                "reviews/review_001.json",
                "adequacy_assessments.jsonl",
                "synthesis.md",
            ],
            "failure_classes": ["evidence", "citation", "file_context", "reviewer"],
            "failure_summary": (
                "Reviewer finding F-001 says material numeric claims were not "
                "independently reviewable from the admitted input set."
            ),
            "expected_gate": "needs_reentry_or_report_restructure",
        },
        {
            "fixture_id": "fixture_drb_claim_boundary_blocked_001",
            "kind": "corrected_fixture",
            "input_artifacts": [
                "claim_review.json",
                "allowed_claims.json",
                "benchmark_score.json",
            ],
            "failure_classes": ["claim_boundary"],
            "correction_summary": (
                "The run records blocked scorer custody while keeping score, parity, "
                "leaderboard, product, and submission claims closed."
            ),
            "expected_gate": "passed",
        },
    ]
    corpus_fixtures = merge_fixtures(base_corpus.get("fixtures", []), replay_fixtures)
    self_dir = run_dir / "self_improvement"
    self_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        self_dir / "replay_corpus.json",
        {
            **base_corpus,
            "schema_version": "codex-dr.deepresearch_bench_improvement_replay_corpus.v1",
            "run_id": case_id,
            "source_evaluation_ledger": "evaluation_ledger.json",
            "source_claim_review": "claim_review.json",
            "evaluation_failures": evaluation_failures,
            "review_findings": review_findings,
            "unresolved_adequacy": unresolved_adequacy,
            "source_recommendations": recommendations,
            "fixtures": corpus_fixtures,
            "source_ref": rel(SELF_IMPROVEMENT_CORPUS_PATH, SANDBOX_ROOT),
            "produced_by_event": "evt_0030_self_improvement_replay_written",
        },
    )
    write_json(
        self_dir / "failure_taxonomy.json",
        {
            **taxonomy,
            "schema_version": "codex-dr.deepresearch_bench_failure_taxonomy.v1",
            "run_id": case_id,
            "failure_classes": merge_failure_classes(
                taxonomy.get("failure_classes", []),
                [
                    {
                        "class_id": "scorer_integration",
                        "description": (
                            "The official benchmark scorer path or authority gate is "
                            "absent, blocked, stale, or not claim-reviewable."
                        ),
                    },
                    {
                        "class_id": "file_context",
                        "description": (
                            "The file return economy did not expose enough local "
                            "evidence context for reviewer or synthesis work."
                        ),
                    },
                    {
                        "class_id": "scheduler",
                        "description": (
                            "The task graph or re-entry policy failed to spawn the "
                            "right follow-up when adequacy pressure remained."
                        ),
                    },
                    {
                        "class_id": "benchmark_alignment",
                        "description": (
                            "The run needs benchmark-specific prompt, source, or "
                            "output shape to improve RACE/FACT performance."
                        ),
                    },
                ],
            ),
            "source_ref": rel(SELF_IMPROVEMENT_TAXONOMY_PATH, SANDBOX_ROOT),
            "produced_by_event": "evt_0030_self_improvement_replay_written",
        },
    )
    candidates = deepresearch_bench_candidate_payloads(
        source_failure_refs=source_failure_refs,
        context_index=context_index,
    )
    write_json(
        self_dir / "improvement_candidates.json",
        {
            "schema_version": "codex-dr.deepresearch_bench_improvement_candidates.v1",
            "run_id": case_id,
            "candidate_set_id": "drb_improvement_candidates_001",
            "source_evaluation_ledger": "evaluation_ledger.json",
            "source_claim_review": "claim_review.json",
            "source_allowed_claims": "allowed_claims.json",
            "source_failure_count": len(source_failure_refs),
            "candidate_count": len(candidates),
            "candidates": candidates,
            "claim_boundary": {
                "may_widen_claims": False,
                "blocked_claims": allowed_claims.get("blocked_claims", []),
            },
            "produced_by_event": "evt_0031_self_improvement_proposal_written",
        },
    )
    write_json(
        self_dir / "improvement_proposal.json",
        {
            "schema_version": "codex-dr.improvement_proposal.v1",
            "run_id": case_id,
            "proposal_id": "deepresearch_bench_improvement_candidates_001",
            "source_fixture_id": "fixture_drb_blocked_scorer_claims_001",
            "source_evaluation_ledger": "evaluation_ledger.json",
            "source_claim_review": "claim_review.json",
            "source_evaluation_failures": [
                ref["failure_id"] for ref in source_failure_refs if ref.get("failure_id")
            ],
            "source_recommendation_ids": [
                recommendation.get("recommendation_id")
                for recommendation in recommendations
                if recommendation.get("recommendation_id")
            ],
            "failure_classes": sorted(
                {
                    failure_class
                    for candidate in candidates
                    for failure_class in candidate.get("failure_classes", [])
                }
            ),
            "target_surfaces": sorted({candidate["target_surface"] for candidate in candidates}),
            "suggested_patch": {
                "candidate_file": "self_improvement/improvement_candidates.json",
                "candidate_ids": [candidate["candidate_id"] for candidate in candidates],
                "summary": (
                    "Review these non-promoted DeepResearch Bench candidates before "
                    "any prompt, skill, scheduler, file-context, or evaluator change."
                ),
            },
            "promotion_status": "proposed_not_promoted",
            "auto_promotion_allowed": False,
            "automatic_skill_mutation_allowed": False,
            "claim_impact": "no claim widening",
            "produced_by_event": "evt_0031_self_improvement_proposal_written",
        },
    )
    write_json(
        self_dir / "regression_gate.json",
        {
            "schema_version": "codex-dr.self_improvement_regression_gate.v1",
            "run_id": case_id,
            "gate_id": "deepresearch_bench_improvement_gate_001",
            "prior_passing_cases_remain_passing": True,
            "failed_cases_cannot_widen_claims": True,
            "regression_evidence_required_for_promotion": True,
            "automatic_skill_mutation_allowed": False,
            "proposal_promotion_allowed": False,
            "candidate_file": "self_improvement/improvement_candidates.json",
            "candidate_count": len(candidates),
            "checks": [
                {
                    "check_id": "candidate_schema_valid",
                    "status": "passed",
                    "evidence": (
                        "Each candidate has source failures, target surface, expected "
                        "effect, replay fixture, and promotion gate."
                    ),
                },
                {
                    "check_id": "claim_widening_blocked",
                    "status": "passed",
                    "evidence": "claim_review.may_widen_public_benchmark_claims is false.",
                },
                {
                    "check_id": "proposal_not_auto_promoted",
                    "status": "passed",
                    "evidence": "Improvement candidates are proposed_not_promoted.",
                },
            ],
            "blocked_claims": [
                "DeepResearch Bench score improvement",
                "Grep parity",
                "leaderboard rank",
                "automatic skill mutation",
            ],
            "produced_by_event": "evt_0032_self_improvement_regression_gate_written",
        },
    )
    append_event(
        run_dir,
        event_id="evt_0030_self_improvement_replay_written",
        event_type="self_improvement.replay_written",
        inputs=[
            "evaluation_ledger.json",
            "claim_review.json",
            "allowed_claims.json",
            "reviews/review_001.json",
            "adequacy_assessments.jsonl",
        ],
        outputs=[
            "self_improvement/replay_corpus.json",
            "self_improvement/failure_taxonomy.json",
        ],
        summary="Wrote DeepResearch Bench replay corpus and failure taxonomy.",
        replace_existing=True,
    )
    append_event(
        run_dir,
        event_id="evt_0031_self_improvement_proposal_written",
        event_type="self_improvement.proposal_written",
        inputs=[
            "self_improvement/replay_corpus.json",
            "self_improvement/failure_taxonomy.json",
        ],
        outputs=[
            "self_improvement/improvement_candidates.json",
            "self_improvement/improvement_proposal.json",
        ],
        summary="Wrote non-promoted DeepResearch Bench improvement candidates.",
        replace_existing=True,
    )
    append_event(
        run_dir,
        event_id="evt_0032_self_improvement_regression_gate_written",
        event_type="self_improvement.regression_gate_written",
        inputs=[
            "self_improvement/improvement_candidates.json",
            "self_improvement/improvement_proposal.json",
            "evaluation_ledger.json",
            "allowed_claims.json",
        ],
        outputs=["self_improvement/regression_gate.json"],
        summary="Wrote DeepResearch Bench candidate regression gate.",
        replace_existing=True,
    )
    update_manifest_status(run_dir, "improvement_candidates_not_promoted")
    refresh_artifact_manifest(run_dir)
    report = validate_run(case_id, runs_dir=runs_dir)
    if report["status"] != "passed":
        raise HarnessError("DeepResearch Bench improvement compile failed validation")
    return run_dir


def read_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return read_json(path)


def read_optional_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return read_jsonl(path)


def compile_source_failure_refs(
    *,
    evaluation_failures: list[dict[str, Any]],
    review_findings: list[dict[str, Any]],
    unresolved_adequacy: list[dict[str, Any]],
    claim_review: dict[str, Any],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for index, failure in enumerate(evaluation_failures, start=1):
        refs.append(
            {
                "source_kind": "evaluation_ledger.failure_taxonomy",
                "path": "evaluation_ledger.json",
                "failure_id": failure.get("failure_class") or f"evaluation_failure_{index}",
                "failure_class": failure.get("failure_class", "benchmark_alignment"),
                "severity": failure.get("severity", "unknown"),
                "summary": failure.get("root_cause", "Evaluation failure requires review."),
            }
        )
    for finding in review_findings:
        raw_class = (
            finding.get("failure_class")
            or finding.get("category")
            or finding.get("failure_type")
            or finding.get("resolution_mode")
        )
        refs.append(
            {
                "source_kind": finding.get("source_kind", "review.finding"),
                "path": "reviews/review_001.json",
                "failure_id": finding.get("finding_id") or finding.get("gap_id"),
                "failure_class": normalize_improvement_failure_class(raw_class),
                "severity": finding.get("severity", "unknown"),
                "summary": (
                    finding.get("detail")
                    or finding.get("title")
                    or finding.get("summary")
                    or finding.get("failure_statement")
                ),
            }
        )
    for row in unresolved_adequacy:
        gaps = (
            row.get("remaining_gaps")
            or row.get("remaining_gap")
            or row.get("unresolved_gap")
            or ["open adequacy gap"]
        )
        if isinstance(gaps, str):
            gaps = [gaps]
        for gap_index, gap in enumerate(gaps, start=1):
            refs.append(
                {
                    "source_kind": "adequacy.remaining_gap",
                    "path": "adequacy_assessments.jsonl",
                    "failure_id": (
                        row.get("gap_id")
                        or f"{row.get('criterion_id', 'adequacy')}_{gap_index}"
                    ),
                    "failure_class": adequacy_failure_class(row),
                    "severity": "high",
                    "summary": gap,
                }
            )
    if claim_review.get("may_widen_public_benchmark_claims") is False:
        refs.append(
            {
                "source_kind": "claim_review.decision",
                "path": "claim_review.json",
                "failure_id": claim_review.get("decision", "claim_review_blocked"),
                "failure_class": "claim_boundary",
                "severity": "blocking",
                "summary": claim_review.get("rationale", "Claim review blocks widening."),
            }
        )
    return refs


def extract_review_failure_surfaces(review: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(review, dict):
        return []
    findings: list[dict[str, Any]] = []
    for key in ("findings", "material_findings", "proposed_backpressure_items"):
        value = review.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    findings.append({**item, "source_kind": f"review.{key}"})
    return findings


def normalize_improvement_failure_class(raw_class: Any) -> str:
    raw = str(raw_class or "").lower()
    if raw in {"citation_support_gap", "citation_gap"} or "citation" in raw:
        return "citation"
    if raw in {"methodology_gap", "verification_gap"} or "methodology" in raw:
        return "reviewer"
    if raw in {"non_comparable_inputs", "comparability_gap"} or "compar" in raw:
        return "evidence"
    if raw in {"provenance_gap", "source_missing"} or "provenance" in raw:
        return "citation"
    if raw in {"reentry_research", "scheduler", "task_graph"}:
        return "scheduler"
    if raw in {"claim_boundary", "scorer_missing", "provider_off_placeholder"}:
        return raw
    return raw or "reviewer"


def adequacy_failure_class(row: dict[str, Any]) -> str:
    text = " ".join(
        str(row.get(key, ""))
        for key in (
            "criterion_id",
            "summary",
            "unresolved_gap",
            "remaining_gap",
            "required_action",
            "target_surface",
        )
    ).lower()
    if "citation" in text or "support map" in text:
        return "citation"
    if "compar" in text or "ranking" in text:
        return "evidence"
    if "verification" in text or "review" in text or "methodology" in text:
        return "reviewer"
    if "reentry" in text or "task packet" in text or "queue" in text:
        return "scheduler"
    return "evidence"


def merge_fixtures(
    base_fixtures: list[dict[str, Any]], extra_fixtures: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for fixture in [*base_fixtures, *extra_fixtures]:
        fixture_id = fixture.get("fixture_id")
        if fixture_id:
            merged[fixture_id] = fixture
    return list(merged.values())


def merge_failure_classes(
    base_classes: list[dict[str, Any]], extra_classes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in [*base_classes, *extra_classes]:
        class_id = item.get("class_id")
        if class_id:
            merged[class_id] = item
    return list(merged.values())


def deepresearch_bench_candidate_payloads(
    *, source_failure_refs: list[dict[str, Any]], context_index: dict[str, Any]
) -> list[dict[str, Any]]:
    scorer_refs = refs_for_classes(
        source_failure_refs,
        {
            "scorer_blocked",
            "scorer_missing",
            "provider_off_placeholder",
            "claim_boundary",
        },
    )
    evidence_refs = refs_for_classes(source_failure_refs, {"reviewer", "evidence", "citation"})
    forecast_refs = [
        ref
        for ref in source_failure_refs
        if "2050" in str(ref.get("summary", "")) or "sensitivity" in str(ref.get("summary", ""))
    ] or evidence_refs
    role_count = context_index.get("role_count") if isinstance(context_index, dict) else None
    shared_gate = {
        "requires_regression": True,
        "requires_replay_fixture": True,
        "requires_claim_review": True,
        "promotion_decision": "manual_or_next_bead_only",
    }
    return [
        {
            "candidate_id": "cand_drb_scorer_authority_gate_001",
            "target_surface_type": "evaluator",
            "target_surface": (
                "sandbox/codex-dr/tools/alexandria_dr.py::"
                "deepresearch_bench_race_bridge"
            ),
            "failure_classes": ["scorer_integration", "claim_boundary"],
            "source_failure_refs": scorer_refs,
            "proposed_change": (
                "Add a score-run authority preflight that records provider key presence, "
                "explicit provider-run approval, evaluator lane, and official command "
                "custody before any RACE score can be written."
            ),
            "expected_effect": (
                "Future runs can move from blocked receipt to score-bearing receipt "
                "without hidden provider execution or premature score claims."
            ),
            "replay_fixtures": ["fixture_drb_blocked_scorer_claims_001"],
            "promotion_gate": {
                **shared_gate,
                "first_gate_command": "alexandria-dr deepresearch-bench-race-bridge",
            },
            "promotion_status": "proposed_not_promoted",
            "auto_promotion_allowed": False,
            "automatic_skill_mutation_allowed": False,
            "claim_impact": "no claim widening",
        },
        {
            "candidate_id": "cand_drb_numeric_appendix_prompt_001",
            "target_surface_type": "prompt",
            "target_surface": "sandbox/codex-dr/harness-specs/live_role_prompt_pack.md",
            "failure_classes": ["evidence", "citation", "reviewer"],
            "source_failure_refs": evidence_refs,
            "proposed_change": (
                "Require synthesis and re-entry prompts to produce a numeric claim "
                "support appendix mapping every material quantity to a local artifact "
                "path, cited URL, or admitted evidence id."
            ),
            "expected_effect": (
                "Reviewer roles can independently inspect quantitative claims without "
                "needing opaque internal handles or full branch transcripts."
            ),
            "replay_fixtures": ["fixture_drb_numeric_appendix_gap_001"],
            "promotion_gate": {
                **shared_gate,
                "first_gate_command": "alexandria-dr validate",
            },
            "promotion_status": "proposed_not_promoted",
            "auto_promotion_allowed": False,
            "automatic_skill_mutation_allowed": False,
            "claim_impact": "no claim widening",
        },
        {
            "candidate_id": "cand_drb_file_context_contract_001",
            "target_surface_type": "file_context",
            "target_surface": "sandbox/codex-dr/harness-specs/dr_mesh_parity_charter.md",
            "failure_classes": ["file_context", "evidence", "citation"],
            "source_failure_refs": evidence_refs,
            "proposed_change": (
                "Extend pointer files with a required source-support table that names "
                "analysis spans, evidence rows, source URLs, and claim ids for any "
                "numeric or forecast-like assertion."
            ),
            "expected_effect": (
                "Pointer-first reading remains context-efficient while giving the "
                "orchestrator enough structured evidence for review and synthesis."
            ),
            "replay_fixtures": ["fixture_drb_numeric_appendix_gap_001"],
            "promotion_gate": {
                **shared_gate,
                "first_gate_command": "alexandria-dr mesh-live-plan",
            },
            "promotion_status": "proposed_not_promoted",
            "auto_promotion_allowed": False,
            "automatic_skill_mutation_allowed": False,
            "claim_impact": "no claim widening",
        },
        {
            "candidate_id": "cand_drb_source_triage_skill_001",
            "target_surface_type": "skill",
            "target_surface": "sandbox/codex-dr/skills/deepresearch-bench-source-triage/SKILL.md",
            "failure_classes": ["source", "benchmark_alignment", "writer"],
            "source_failure_refs": forecast_refs,
            "proposed_change": (
                "Draft a local source-triage skill for deciding when a forecast "
                "endpoint is source-grounded, sensitivity-bound, or too weak for the "
                "main answer spine."
            ),
            "expected_effect": (
                "Branch and writer roles handle weak long-horizon inputs in a way "
                "that is explicit enough for RACE-style report quality review."
            ),
            "replay_fixtures": ["fixture_drb_numeric_appendix_gap_001"],
            "promotion_gate": {
                **shared_gate,
                "first_gate_command": "alexandria-dr deepresearch-bench-improvement-compile",
            },
            "promotion_status": "proposed_not_promoted",
            "auto_promotion_allowed": False,
            "automatic_skill_mutation_allowed": False,
            "claim_impact": "no claim widening",
        },
        {
            "candidate_id": "cand_drb_scheduler_reentry_policy_001",
            "target_surface_type": "scheduler",
            "target_surface": "task_graph.json policy / live planner prompt",
            "failure_classes": ["scheduler", "task_graph", "reviewer"],
            "source_failure_refs": evidence_refs,
            "proposed_change": (
                "Add a planner and scheduler rule: if a high-severity reviewer gap "
                "remains after first re-entry, compile a second bounded evidence "
                "appendix task instead of allowing the writer to treat the gap as closed."
            ),
            "expected_effect": (
                "The mesh spends additional agent effort only where reviewer pressure "
                f"shows unresolved evidence risk; observed role_count={role_count}."
            ),
            "replay_fixtures": ["fixture_drb_numeric_appendix_gap_001"],
            "promotion_gate": {
                **shared_gate,
                "first_gate_command": "alexandria-dr validate",
            },
            "promotion_status": "proposed_not_promoted",
            "auto_promotion_allowed": False,
            "automatic_skill_mutation_allowed": False,
            "claim_impact": "no claim widening",
        },
    ]


def refs_for_classes(
    refs: list[dict[str, Any]], classes: set[str]
) -> list[dict[str, Any]]:
    return [
        ref
        for ref in refs
        if ref.get("failure_class") in classes or ref.get("failure_id") in classes
    ]


def refs_matching_summary(
    refs: list[dict[str, Any]], fragments: set[str]
) -> list[dict[str, Any]]:
    selected = []
    for ref in refs:
        haystack = " ".join(
            str(ref.get(field, ""))
            for field in ("failure_id", "failure_class", "summary")
        ).lower()
        if any(fragment.lower() in haystack for fragment in fragments):
            selected.append(ref)
    return selected


def deepresearch_bench_improvement_gate(
    case_id: str, *, runs_dir: Path | str | None = None
) -> Path:
    run_dir = run_path(case_id, runs_dir)
    self_dir = run_dir / "self_improvement"
    candidates_payload = read_json(self_dir / "improvement_candidates.json")
    replay_corpus = read_json(self_dir / "replay_corpus.json")
    claim_review = read_json(run_dir / "claim_review.json")
    allowed_claims = read_json(run_dir / "allowed_claims.json")
    benchmark_score = read_json(run_dir / "benchmark_score.json")
    candidates = candidates_payload.get("candidates", [])
    if not candidates:
        raise HarnessError("no improvement candidates available to gate")

    isolated_root = self_dir / "isolated_candidate_surfaces"
    receipt_root = self_dir / "promotion_receipts"
    isolated_root.mkdir(parents=True, exist_ok=True)
    receipt_root.mkdir(parents=True, exist_ok=True)
    fixture_ids = {fixture.get("fixture_id") for fixture in replay_corpus.get("fixtures", [])}
    results = []
    output_paths = [
        "self_improvement/candidate_gate_results.json",
        "self_improvement/regression_gate.json",
    ]
    for candidate in candidates:
        candidate_id = candidate["candidate_id"]
        candidate_dir = isolated_root / candidate_id
        candidate_dir.mkdir(parents=True, exist_ok=True)
        patch_preview = candidate_dir / "patch_preview.json"
        replay_result = candidate_dir / "replay_result.json"
        receipt_path = receipt_root / f"{candidate_id}.json"
        replay_checks = replay_candidate_checks(
            candidate,
            fixture_ids=fixture_ids,
            claim_review=claim_review,
            allowed_claims=allowed_claims,
            benchmark_score=benchmark_score,
        )
        decision = candidate_gate_decision(candidate, replay_checks)
        write_json(
            patch_preview,
            {
                "schema_version": "codex-dr.candidate_patch_preview.v1",
                "run_id": case_id,
                "candidate_id": candidate_id,
                "target_surface_type": candidate.get("target_surface_type"),
                "target_surface": candidate.get("target_surface"),
                "proposed_change": candidate.get("proposed_change"),
                "expected_effect": candidate.get("expected_effect"),
                "isolated_only": True,
                "live_surface_changed": False,
                "produced_by_event": "evt_drb_improvement_gate_0001_written",
            },
        )
        write_json(
            replay_result,
            {
                "schema_version": "codex-dr.candidate_replay_result.v1",
                "run_id": case_id,
                "candidate_id": candidate_id,
                "replay_fixtures": candidate.get("replay_fixtures", []),
                "checks": replay_checks,
                "passed": all(check["status"] == "passed" for check in replay_checks),
                "produced_by_event": "evt_drb_improvement_gate_0001_written",
            },
        )
        write_json(
            receipt_path,
            {
                "schema_version": "codex-dr.candidate_promotion_receipt.v1",
                "run_id": case_id,
                "candidate_id": candidate_id,
                "decision": decision,
                "promotion_status": "not_promoted",
                "live_surface_changed": False,
                "reason": (
                    "Candidate replay constraints were evaluated in isolation; "
                    "promotion requires a later bead that applies and reruns the "
                    "candidate patch against regression fixtures."
                ),
                "patch_preview": rel(patch_preview, run_dir),
                "replay_result": rel(replay_result, run_dir),
                "claim_impact": "no claim widening",
                "produced_by_event": "evt_drb_improvement_gate_0001_written",
            },
        )
        results.append(
            {
                "candidate_id": candidate_id,
                "target_surface_type": candidate.get("target_surface_type"),
                "target_surface": candidate.get("target_surface"),
                "decision": decision,
                "promotion_status": "not_promoted",
                "live_surface_changed": False,
                "patch_preview": rel(patch_preview, run_dir),
                "replay_result": rel(replay_result, run_dir),
                "promotion_receipt": rel(receipt_path, run_dir),
                "checks_passed": all(check["status"] == "passed" for check in replay_checks),
            }
        )
        output_paths.extend(
            [
                rel(patch_preview, run_dir),
                rel(replay_result, run_dir),
                rel(receipt_path, run_dir),
            ]
        )

    write_json(
        self_dir / "candidate_gate_results.json",
        {
            "schema_version": "codex-dr.deepresearch_bench_candidate_gate_results.v1",
            "run_id": case_id,
            "candidate_set_id": candidates_payload.get("candidate_set_id"),
            "candidate_count": len(candidates),
            "results": results,
            "all_candidates_gated": len(results) == len(candidates),
            "live_surface_changed": False,
            "claim_boundary": {
                "may_widen_claims": False,
                "blocked_claims": allowed_claims.get("blocked_claims", []),
            },
            "produced_by_event": "evt_drb_improvement_gate_0001_written",
        },
    )
    regression_gate = read_json(self_dir / "regression_gate.json")
    regression_gate.update(
        {
            "candidate_gate_results": "self_improvement/candidate_gate_results.json",
            "all_candidates_gated": True,
            "proposal_promotion_allowed": False,
            "live_surface_changed": False,
            "live_surface_mutations": [],
            "produced_by_event": "evt_drb_improvement_gate_0001_written",
        }
    )
    write_json(self_dir / "regression_gate.json", regression_gate)
    append_event(
        run_dir,
        event_id="evt_drb_improvement_gate_0001_written",
        event_type="self_improvement.regression_gate_evaluated",
        inputs=[
            "self_improvement/improvement_candidates.json",
            "self_improvement/replay_corpus.json",
            "claim_review.json",
            "allowed_claims.json",
        ],
        outputs=output_paths,
        summary="Evaluated DeepResearch Bench improvement candidates in isolation.",
        replace_existing=True,
    )
    update_manifest_status(run_dir, "improvement_candidates_gated_not_promoted")
    refresh_artifact_manifest(run_dir)
    report = validate_run(case_id, runs_dir=runs_dir)
    if report["status"] != "passed":
        raise HarnessError("DeepResearch Bench improvement gate failed validation")
    return run_dir


def replay_candidate_checks(
    candidate: dict[str, Any],
    *,
    fixture_ids: set[str],
    claim_review: dict[str, Any],
    allowed_claims: dict[str, Any],
    benchmark_score: dict[str, Any],
) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    missing_fixtures = sorted(set(candidate.get("replay_fixtures", [])) - fixture_ids)
    checks.append(
        {
            "check_id": "replay_fixtures_exist",
            "status": "failed" if missing_fixtures else "passed",
            "details": ", ".join(missing_fixtures) if missing_fixtures else "all present",
        }
    )
    checks.append(
        {
            "check_id": "claim_review_blocks_widening",
            "status": (
                "passed"
                if claim_review.get("may_widen_public_benchmark_claims") is False
                else "failed"
            ),
            "details": str(claim_review.get("decision")),
        }
    )
    blocked_claims = set(allowed_claims.get("blocked_claims", []))
    checks.append(
        {
            "check_id": "score_claims_stay_blocked",
            "status": (
                "passed"
                if {"DeepResearch Bench score", "Grep parity"} <= blocked_claims
                else "failed"
            ),
            "details": "score and parity blocked",
        }
    )
    checks.append(
        {
            "check_id": "no_numeric_score_without_scorer",
            "status": (
                "passed"
                if benchmark_score.get("score") is None
                and benchmark_score.get("claims_enabled") is False
                else "failed"
            ),
            "details": str(benchmark_score.get("mode")),
        }
    )
    checks.append(
        {
            "check_id": "candidate_isolation",
            "status": (
                "passed"
                if candidate.get("promotion_status") == "proposed_not_promoted"
                else "failed"
            ),
            "details": "candidate remains proposed_not_promoted",
        }
    )
    return checks


def candidate_gate_decision(
    candidate: dict[str, Any], replay_checks: list[dict[str, str]]
) -> str:
    if any(check["status"] != "passed" for check in replay_checks):
        return "rejected_replay_failed"
    if candidate.get("target_surface_type") == "evaluator":
        return "deferred_until_provider_authority"
    return "deferred_patch_not_applied"


def adequacy_gap_items(run_dir: Path) -> list[dict[str, Any]]:
    assessments = read_jsonl(run_dir / "adequacy_assessments.jsonl")
    items: list[dict[str, Any]] = []
    for assessment in assessments:
        status = str(assessment.get("status", "")).lower()
        gaps = normalized_adequacy_gaps(assessment)
        if status in SATISFIED_ADEQUACY_STATUSES or not gaps:
            continue
        follow_up_task = str(
            assessment.get("follow_up_task") or assessment.get("recommended_follow_up") or ""
        ).strip()
        writer_constraint_mode = (
            status in {"partially_satisfied", "satisfied_with_constraints", "conditional"}
            and bool(follow_up_task)
        )
        assessment_id = assessment.get("assessment_id", "unknown_assessment")
        source_refs = ["adequacy_assessments.jsonl"]
        if assessment.get("criterion") == "adequacy_review_reentry":
            source_refs.extend(["reviews/review_001.json", "synthesis.md", "report_outline.md"])
        criterion = assessment.get("criterion") or assessment.get("criterion_id")
        failure_type = backpressure_failure_type_from_assessment(assessment, gaps)
        gates = ["claim_blocking"]
        if writer_constraint_mode:
            gates.append("advisory")
        else:
            gates.extend(["writer_blocking", "reentry_required", "review_required"])
        for index, gap in enumerate(gaps, start=1):
            gap_id = f"{assessment_id}_gap_{index:03d}"
            required_outputs = (
                ["report_outline.md"]
                if writer_constraint_mode
                else ["pointer.md", "analysis.md", "evidence.jsonl"]
            )
            if failure_type == "citation_support_gap":
                required_outputs.append("citation_support_map.json")
            items.append(
                {
                    "item_id": gap_id,
                    "gap_id": gap_id,
                    "created_by": "harness_adequacy_compiler",
                    "source_assessment_id": assessment_id,
                    "source_status": assessment.get("status"),
                    "status": (
                        "writer_constraint_queued" if writer_constraint_mode else "open"
                    ),
                    "gates": gates,
                    "failure_type": failure_type,
                    "adequacy_criterion_id": criterion or "unknown_criterion",
                    "affected_answer_object_part": assessment.get(
                        "affected_answer_object_part", "answer adequacy"
                    ),
                    "affected_artifacts": source_refs,
                    "gap": gap,
                    "failure_statement": gap,
                    "required_action": (
                        "carry_forward_writer_constraint"
                        if writer_constraint_mode
                        else "spawn_followup_task_or_record_review_resolution"
                    ),
                    "required_outputs": required_outputs,
                    "target_surface": (
                        "report_outline.md" if writer_constraint_mode else "task_graph.json"
                    ),
                    "writer_blocking": not writer_constraint_mode,
                    "resolution_mode": (
                        "writer_constraint" if writer_constraint_mode else "followup_task"
                    ),
                    "follow_up_task": follow_up_task or None,
                    "writer_constraint": follow_up_task if writer_constraint_mode else None,
                    "closure_condition": (
                        "Writer-facing constraint is preserved in report_outline.md."
                        if writer_constraint_mode
                        else (
                            "Reviewer verifies the required repair outputs against "
                            "the affected adequacy criterion."
                        )
                    ),
                    "closure_authority": "reviewer_semantic_adjudication",
                    "resolution": None,
                    "source_refs": source_refs,
                }
            )
    return items


def backpressure_failure_type_from_assessment(
    assessment: dict[str, Any], gaps: list[str]
) -> str:
    text = " ".join(
        [
            str(assessment.get("criterion") or ""),
            str(assessment.get("criterion_id") or ""),
            str(assessment.get("assessment_id") or ""),
            " ".join(gaps),
        ]
    ).lower()
    if "citation" in text or "statement-to-source" in text or "source support" in text:
        return "citation_support_gap"
    if "provenance" in text or "custody" in text:
        return "provenance_gap"
    if "contradiction" in text:
        return "contradiction"
    if "compar" in text or "commensur" in text or "non-comparable" in text:
        return "non_comparable_inputs"
    if "number" in text or "numeric" in text or "forecast" in text:
        return "numerical_support_gap"
    if "method" in text:
        return "methodology_gap"
    if "tool" in text or "source access" in text:
        return "tooling_gap"
    if "criteria" in text or "criterion" in text:
        return "adequacy_criteria_gap"
    return "evidence_gap"


def normalized_adequacy_gaps(assessment: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    raw_gaps = assessment.get("gaps", [])
    if isinstance(raw_gaps, list):
        gaps.extend(str(gap).strip() for gap in raw_gaps if str(gap).strip())
    elif str(raw_gaps).strip():
        gaps.append(str(raw_gaps).strip())
    for key in ("remaining_gap", "gap", "unresolved_gap"):
        value = str(assessment.get(key) or "").strip()
        if value:
            gaps.append(value)
    if not gaps:
        follow_up = str(
            assessment.get("follow_up_task") or assessment.get("recommended_follow_up") or ""
        ).strip()
        if follow_up:
            gaps.append(follow_up)
    return list(dict.fromkeys(gaps))


def adequacy_backpressure_queue_status(
    items: list[dict[str, Any]],
    quarantined_items: list[dict[str, Any]] | None = None,
) -> tuple[str, bool]:
    quarantined_items = quarantined_items or []
    quarantined_writer_blocking = any(
        str(item.get("status") or "").lower() not in BACKPRESSURE_CLOSED_STATUSES
        and item.get("writer_blocking") is not False
        for item in quarantined_items
    )
    if not items and not quarantined_writer_blocking:
        return "clear", False
    writer_blocking = any(backpressure_item_blocks_writer(item) for item in items)
    if writer_blocking or quarantined_writer_blocking:
        return "open", True
    return "writer_constraints", False


def backpressure_item_blocks_writer(item: dict[str, Any]) -> bool:
    status = str(item.get("status") or "").lower()
    if status in BACKPRESSURE_CLOSED_STATUSES:
        return False
    gates = item.get("gates", [])
    if isinstance(gates, list) and "writer_blocking" in gates:
        return status in BACKPRESSURE_WRITER_BLOCKING_STATUSES or not status
    gate_effects = item.get("gate_effects", {})
    if isinstance(gate_effects, dict) and gate_effects.get("writer_blocking") is True:
        return status in BACKPRESSURE_WRITER_BLOCKING_STATUSES or not status
    return item.get("writer_blocking") is True


def review_proposed_backpressure_items(run_dir: Path) -> list[dict[str, Any]]:
    items, _quarantined = compile_review_proposed_backpressure_items(run_dir)
    return items


def compile_review_proposed_backpressure_items(
    run_dir: Path, *, existing_gap_ids: set[str] | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    review_root = run_dir / "reviews"
    if not review_root.exists():
        return [], []
    items: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    seen_gap_ids = set(existing_gap_ids or set())
    for review_path in sorted(review_root.glob("review_*.json")):
        review = read_optional_json(review_path)
        if not review:
            continue
        review_id = str(review.get("review_id") or review_path.stem)
        proposed = review.get("proposed_backpressure_items", [])
        if not isinstance(proposed, list):
            continue
        for index, item in enumerate(proposed, start=1):
            if isinstance(item, dict):
                canonical, problems = canonical_backpressure_item_from_review_proposal(
                    item,
                    review_id=review_id,
                    review_path=review_path.relative_to(run_dir).as_posix(),
                    index=index,
                    seen_gap_ids=seen_gap_ids,
                )
                if canonical:
                    items.append(canonical)
                    seen_gap_ids.add(str(canonical["gap_id"]))
                elif problems:
                    quarantined.append(
                        quarantined_review_proposal(
                            item,
                            review_id=review_id,
                            review_path=review_path.relative_to(run_dir).as_posix(),
                            index=index,
                            problems=problems,
                        )
                    )
    return items, quarantined


def canonical_backpressure_item_from_review_proposal(
    item: dict[str, Any],
    *,
    review_id: str,
    review_path: str,
    index: int,
    seen_gap_ids: set[str] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    problems = review_proposal_validation_problems(
        item, seen_gap_ids=seen_gap_ids or set()
    )
    if problems:
        return None, problems
    status = str(item.get("status") or "open").lower()
    if status in {"closed", "superseded"}:
        return None, []
    gate_effects = item.get("gate_effects", {})
    gates = [
        gate
        for gate, enabled in gate_effects.items()
        if enabled is True
        and gate
        in {"writer_blocking", "reentry_required", "review_required", "claim_blocking"}
    ] if isinstance(gate_effects, dict) else []
    writer_blocking = (
        "writer_blocking" in gates and status in BACKPRESSURE_WRITER_BLOCKING_STATUSES
    )
    required_action = item["required_action"]
    gap_id = str(item["gap_id"]).strip()
    failure_statement = str(
        item.get("failure_statement") or item.get("gap")
    )
    source_refs = normalize_review_source_refs(item.get("source_refs", []), review_path)
    required_outputs = [
        str(output)
        for output in required_action.get("required_outputs", [])
        if str(output).strip()
    ]
    resolution_mode = item.get("resolution_mode")
    if not resolution_mode:
        resolution_mode = "followup_task" if writer_blocking else "writer_constraint"
    canonical = {
        "item_id": gap_id,
        "gap_id": gap_id,
        "created_by": "harness_review_proposal_compiler",
        "canonical_schema_version": "codex-dr.adequacy_backpressure_item.v2",
        "source_review_id": review_id,
        "source_assessment_id": review_id,
        "source_status": status,
        "status": status,
        "gates": gates,
        "failure_type": item.get("failure_type") or "evidence_gap",
        "adequacy_criterion_id": item.get("adequacy_criterion_id") or "reviewer_proposed",
        "affected_answer_object_part": item.get(
            "affected_answer_object_part", "answer adequacy"
        ),
        "affected_artifacts": [
            ref.get("path") if isinstance(ref, dict) else str(ref)
            for ref in item.get("source_refs", [])
        ],
        "gap": failure_statement,
        "failure_statement": failure_statement,
        "required_action": required_action.get("action_type") or "reviewer_proposed_repair",
        "required_action_detail": {
            "action_type": required_action.get("action_type"),
            "assigned_role_family": required_action.get("assigned_role_family"),
            "objective": required_action.get("objective"),
            "allowed_inputs": required_action.get("allowed_inputs", []),
            "required_outputs": required_outputs,
        },
        "required_outputs": required_outputs,
        "target_surface": item.get("target_surface") or "task_graph.json",
        "writer_blocking": writer_blocking,
        "resolution_mode": resolution_mode,
        "follow_up_task": required_action.get("objective"),
        "writer_constraint": None if writer_blocking else failure_statement,
        "closure_condition": item.get("closure_condition"),
        "closure_authority": item.get("closure_authority") or "reviewer",
        "resolution": item.get("resolution_mode"),
        "resolution_refs": item.get("resolution_refs", []),
        "source_refs": source_refs,
        "normalization_trace": {
            "source": "review.proposed_backpressure_items",
            "gap_id_from": "proposed_backpressure_items[].gap_id",
            "gate_effects_from": "proposed_backpressure_items[].gate_effects",
            "required_action_from": "proposed_backpressure_items[].required_action",
            "closure_condition_from": "proposed_backpressure_items[].closure_condition",
        },
    }
    return canonical, []


def review_proposal_validation_problems(
    item: dict[str, Any], *, seen_gap_ids: set[str]
) -> list[str]:
    problems: list[str] = []
    gap_id = str(item.get("gap_id") or "").strip()
    if not gap_id:
        problems.append("missing gap_id")
    elif gap_id in seen_gap_ids:
        problems.append(f"duplicate gap_id: {gap_id}")
    for field in (
        "failure_type",
        "adequacy_criterion_id",
        "target_surface",
        "failure_statement",
        "closure_condition",
        "closure_authority",
    ):
        if not str(item.get(field) or "").strip():
            problems.append(f"missing {field}")
    source_refs = item.get("source_refs")
    if not isinstance(source_refs, list) or not source_refs:
        problems.append("missing source_refs")
    gate_effects = item.get("gate_effects")
    if not isinstance(gate_effects, dict):
        problems.append("missing gate_effects")
    elif not any(enabled is True for enabled in gate_effects.values()):
        problems.append("gate_effects has no enabled gates")
    required_action = item.get("required_action")
    if not isinstance(required_action, dict):
        problems.append("missing required_action")
    else:
        for field in ("action_type", "objective", "allowed_inputs", "required_outputs"):
            value = required_action.get(field)
            if field in {"allowed_inputs", "required_outputs"}:
                if not isinstance(value, list) or not value:
                    problems.append(f"missing required_action.{field}")
            elif not str(value or "").strip():
                problems.append(f"missing required_action.{field}")
    if not review_proposal_has_bounded_scope(item):
        problems.append("citation-support item lacks bounded claim/span/section scope")
    return problems


def review_proposal_has_bounded_scope(item: dict[str, Any]) -> bool:
    failure_type = str(item.get("failure_type") or "").lower()
    required_action = item.get("required_action", {})
    action_type = (
        str(required_action.get("action_type") or "").lower()
        if isinstance(required_action, dict)
        else ""
    )
    if "citation" not in failure_type and "statement_to_source" not in action_type:
        return True
    source_refs = item.get("source_refs", [])
    if not isinstance(source_refs, list):
        return False
    for ref in source_refs:
        if isinstance(ref, dict):
            if ref.get("claim_ids") or ref.get("statement_ids"):
                return True
            for key in ("span", "section", "slice"):
                if str(ref.get(key) or "").strip():
                    return True
        elif "#" in str(ref):
            return True
    return False


def quarantined_review_proposal(
    item: dict[str, Any],
    *,
    review_id: str,
    review_path: str,
    index: int,
    problems: list[str],
) -> dict[str, Any]:
    gate_effects = item.get("gate_effects")
    writer_blocking = True
    if isinstance(gate_effects, dict) and gate_effects.get("writer_blocking") is False:
        writer_blocking = False
    raw_gap_id = str(item.get("gap_id") or item.get("item_id") or "").strip() or None
    return {
        "quarantine_id": f"{review_id}_proposed_{index:03d}_quarantined",
        "status": "quarantined",
        "created_by": "harness_review_proposal_compiler",
        "source_review_id": review_id,
        "source_review_path": review_path,
        "source_index": index,
        "raw_gap_id": raw_gap_id,
        "writer_blocking": writer_blocking,
        "gate_effects": gate_effects if isinstance(gate_effects, dict) else None,
        "failure_type": item.get("failure_type"),
        "target_surface": item.get("target_surface"),
        "source_refs": normalize_review_source_refs(item.get("source_refs", []), review_path),
        "problems": problems or ["malformed proposed_backpressure_item"],
        "required_action": "repair_review_proposed_backpressure_item",
        "closure_condition": (
            "A reviewer or harness operator supplies a normalized "
            "proposed_backpressure_item with all required control fields."
        ),
        "claim_boundary": {
            "may_widen_claims": False,
            "blocked_claims": [
                "Grep parity",
                "DeepResearch Bench score",
                "DRACO score",
                "leaderboard rank",
                "product readiness",
                "official benchmark submission",
                "scorer-backed evaluation",
            ],
        },
    }


def normalize_review_source_refs(source_refs: Any, review_path: str) -> list[str]:
    normalized = [review_path]
    if isinstance(source_refs, list):
        for ref in source_refs:
            if isinstance(ref, dict):
                path = str(ref.get("path") or "").strip()
                span = str(ref.get("span") or "").strip()
                if path:
                    normalized.append(f"{path}#{span}" if span else path)
            elif str(ref).strip():
                normalized.append(str(ref).strip())
    elif str(source_refs).strip():
        normalized.append(str(source_refs).strip())
    return list(dict.fromkeys(normalized))


def merge_backpressure_items(
    generated_items: list[dict[str, Any]], reviewer_items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    merged = list(generated_items)
    seen = {
        str(item.get("item_id") or item.get("gap_id"))
        for item in merged
        if item.get("item_id") or item.get("gap_id")
    }
    for item in reviewer_items:
        key = str(item.get("item_id") or item.get("gap_id") or "")
        if key and key in seen:
            continue
        merged.append(item)
        if key:
            seen.add(key)
    return merged


def compile_adequacy_backpressure(
    case_id: str,
    *,
    runs_dir: Path | str | None = None,
    event_id: str = "evt_backpressure_0001_adequacy_queue_written",
    causally_after: list[str] | None = None,
) -> Path:
    run_dir = run_path(case_id, runs_dir)
    if not run_dir.exists():
        raise HarnessError(f"run does not exist: {run_dir}")
    queue_path = run_dir / "backpressure" / "adequacy_backpressure_queue.json"
    adequacy_items = adequacy_gap_items(run_dir)
    existing_gap_ids = {
        str(item.get("gap_id") or item.get("item_id"))
        for item in adequacy_items
        if item.get("gap_id") or item.get("item_id")
    }
    review_items, quarantined_items = compile_review_proposed_backpressure_items(
        run_dir, existing_gap_ids=existing_gap_ids
    )
    items = merge_backpressure_items(
        adequacy_items,
        review_items,
    )
    queue_status, writer_blocked = adequacy_backpressure_queue_status(
        items, quarantined_items
    )
    write_json(
        queue_path,
        {
            "schema_version": BACKPRESSURE_QUEUE_SCHEMA_VERSION,
            "run_id": case_id,
            "queue_status": queue_status,
            "source": (
                "adequacy_assessments.jsonl+reviews/*.json"
                if review_items or quarantined_items
                else "adequacy_assessments.jsonl"
            ),
            "writer_blocked": writer_blocked,
            "items": items,
            "quarantined_items": quarantined_items,
            "normalization_summary": {
                "canonical_item_count": len(items),
                "review_proposed_item_count": len(review_items),
                "quarantined_review_proposal_count": len(quarantined_items),
                "legacy_fields_normalized_by": "harness",
            },
            "invalid_success_blocked": (
                "Adequacy gaps cannot remain as prose-only assessment fields while "
                "the run advances toward writing. Open follow-up gaps block the writer; "
                "writer-constraint gaps must be visible in the writer-facing surface."
            ),
            "claim_boundary": {
                "may_widen_claims": False,
                "blocked_claims": [
                    "Grep parity",
                    "DeepResearch Bench score",
                    "DRACO score",
                    "leaderboard rank",
                    "product readiness",
                    "official benchmark submission",
                    "scorer-backed evaluation",
                ],
            },
            "produced_by_event": event_id,
        },
    )
    append_event(
        run_dir,
        event_id=event_id,
        event_type="adequacy.backpressure_queue_written",
        inputs=["adequacy_assessments.jsonl", "task_graph.json"],
        outputs=["backpressure/adequacy_backpressure_queue.json"],
        causally_after=causally_after,
        decision={
            "decision_id": "dec_compile_adequacy_backpressure",
            "decision_type": "compile_backpressure",
            "rationale": (
                "Convert unresolved adequacy pressure into an inspectable queue before "
                "writer or improvement work treats the research state as settled."
            ),
            "status": queue_status,
            "writer_blocked": writer_blocked,
            "quarantined_review_proposal_count": len(quarantined_items),
        },
        summary="Compiled adequacy gaps into backpressure queue.",
        replace_existing=True,
    )
    write_backpressure_gate_receipt(
        run_dir,
        event_id=f"{event_id}_gate_receipt",
        causally_after=[event_id],
    )
    refresh_artifact_manifest(run_dir)
    return run_dir


def backpressure_gate_receipt_payload(
    run_dir: Path, queue: dict[str, Any], *, produced_by_event: str | None = None
) -> dict[str, Any]:
    items = queue.get("items", [])
    if not isinstance(items, list):
        items = []
    quarantined_items = queue.get("quarantined_items", [])
    if not isinstance(quarantined_items, list):
        quarantined_items = []
    writer_blocking_items = [
        str(item.get("gap_id") or item.get("item_id") or "<unknown>")
        for item in items
        if backpressure_item_blocks_writer(item)
    ]
    writer_blocking_quarantines = [
        str(item.get("quarantine_id") or item.get("raw_gap_id") or "<unknown>")
        for item in quarantined_items
        if str(item.get("status") or "").lower() not in BACKPRESSURE_CLOSED_STATUSES
        and item.get("writer_blocking") is not False
    ]
    writer_constraints = [
        {
            "gap_id": item.get("gap_id") or item.get("item_id"),
            "target_surface": item.get("target_surface"),
            "writer_constraint": item.get("writer_constraint"),
        }
        for item in items
        if not backpressure_item_blocks_writer(item)
        and str(item.get("status") or "").lower() not in BACKPRESSURE_CLOSED_STATUSES
    ]
    writer_blocked = bool(writer_blocking_items or writer_blocking_quarantines)
    if writer_blocked:
        gate_status = "writer_blocked"
    elif writer_constraints:
        gate_status = "writer_constraints"
    else:
        gate_status = "writer_allowed"
    return {
        "schema_version": BACKPRESSURE_GATE_RECEIPT_SCHEMA_VERSION,
        "run_id": run_dir.name,
        "source_queue_path": "backpressure/adequacy_backpressure_queue.json",
        "source_queue_schema_version": queue.get("schema_version"),
        "queue_status": queue.get("queue_status"),
        "gate_status": gate_status,
        "writer_blocked": writer_blocked,
        "writer_may_proceed": not writer_blocked,
        "open_writer_blocking_gap_ids": writer_blocking_items,
        "quarantined_writer_blocking_item_ids": writer_blocking_quarantines,
        "writer_constraints": writer_constraints,
        "required_before_writer": (
            [
                "reviewer adjudication closes, supersedes, or authorizes lawful partial for all writer-blocking items",
                "harness recompiles canonical queue",
                "harness regenerates this gate receipt",
            ]
            if writer_blocked
            else []
        ),
        "claim_boundary": {
            "may_widen_claims": False,
            "blocked_claims": queue.get("claim_boundary", {}).get(
                "blocked_claims",
                [
                    "Grep parity",
                    "DeepResearch Bench score",
                    "DRACO score",
                    "leaderboard rank",
                    "product readiness",
                    "official benchmark submission",
                    "scorer-backed evaluation",
                ],
            ),
        },
        "produced_by_event": produced_by_event,
    }


def write_backpressure_gate_receipt(
    run_dir: Path,
    *,
    event_id: str = "evt_backpressure_gate_0001_receipt_written",
    causally_after: list[str] | None = None,
) -> Path | None:
    queue_path = run_dir / "backpressure" / "adequacy_backpressure_queue.json"
    if not queue_path.exists():
        return None
    try:
        queue = read_json(queue_path)
    except json.JSONDecodeError as error:
        raise HarnessError(f"backpressure queue is not valid JSON: {error}") from error
    receipt_path = run_dir / "backpressure" / "backpressure_gate_receipt.json"
    receipt = backpressure_gate_receipt_payload(
        run_dir, queue, produced_by_event=event_id
    )
    write_json(receipt_path, receipt)
    append_event(
        run_dir,
        event_id=event_id,
        event_type="adequacy.backpressure_gate_receipt_written",
        inputs=["backpressure/adequacy_backpressure_queue.json"],
        outputs=["backpressure/backpressure_gate_receipt.json"],
        causally_after=causally_after,
        decision={
            "decision_id": "dec_derive_backpressure_gate",
            "decision_type": "derive_writer_gate",
            "gate_status": receipt["gate_status"],
            "writer_blocked": receipt["writer_blocked"],
            "rationale": (
                "The gate receipt is a deterministic derived view of the canonical "
                "adequacy backpressure queue."
            ),
        },
        summary="Derived writer transition gate from canonical adequacy backpressure.",
        replace_existing=True,
    )
    return receipt_path


def writer_gate_preflight_payload(run_dir: Path) -> dict[str, Any]:
    queue_path = run_dir / "backpressure" / "adequacy_backpressure_queue.json"
    receipt_path = run_dir / "backpressure" / "backpressure_gate_receipt.json"
    queue = read_optional_json(queue_path)
    receipt = read_optional_json(receipt_path)
    if not queue:
        return {
            "schema_version": WRITER_GATE_PREFLIGHT_SCHEMA_VERSION,
            "run_id": run_dir.name,
            "preflight_status": "writer_allowed_no_backpressure_queue",
            "may_writer_proceed": True,
            "writer_blocked": False,
            "source_gate_receipt": None,
            "source_queue": None,
            "blocking_reasons": [],
            "claim_boundary": {"may_widen_claims": False},
        }
    expected = backpressure_gate_receipt_payload(run_dir, queue)
    blocking_reasons: list[str] = []
    if not receipt:
        blocking_reasons.append(
            "gate receipt is missing while backpressure queue exists"
        )
    else:
        if receipt.get("schema_version") != BACKPRESSURE_GATE_RECEIPT_SCHEMA_VERSION:
            blocking_reasons.append("gate receipt schema_version is invalid")
        if receipt.get("writer_blocked") is not expected["writer_blocked"]:
            blocking_reasons.append("gate receipt writer_blocked contradicts queue")
        if receipt.get("gate_status") != expected["gate_status"]:
            blocking_reasons.append("gate receipt gate_status contradicts queue")
    if expected["writer_blocked"]:
        blocking_reasons.append("open writer-blocking adequacy backpressure exists")
    may_proceed = not blocking_reasons
    return {
        "schema_version": WRITER_GATE_PREFLIGHT_SCHEMA_VERSION,
        "run_id": run_dir.name,
        "preflight_status": "writer_allowed" if may_proceed else "writer_blocked",
        "may_writer_proceed": may_proceed,
        "writer_blocked": not may_proceed,
        "source_gate_receipt": (
            "backpressure/backpressure_gate_receipt.json" if receipt else None
        ),
        "source_queue": "backpressure/adequacy_backpressure_queue.json",
        "expected_gate_status": expected["gate_status"],
        "expected_writer_blocked": expected["writer_blocked"],
        "blocking_reasons": list(dict.fromkeys(blocking_reasons)),
        "claim_boundary": expected["claim_boundary"],
    }


def write_writer_gate_preflight(run_dir: Path) -> dict[str, Any]:
    preflight = writer_gate_preflight_payload(run_dir)
    write_json(run_dir / "writer_gate_preflight.json", preflight)
    inputs = [path for path in [
        "backpressure/backpressure_gate_receipt.json",
        "backpressure/adequacy_backpressure_queue.json",
    ] if (run_dir / path).exists()]
    append_event(
        run_dir,
        event_id="evt_writer_gate_preflight_0001_written",
        event_type="writer_gate.preflight_written",
        inputs=inputs,
        outputs=["writer_gate_preflight.json"],
        decision={
            "decision_id": "dec_writer_gate_preflight",
            "decision_type": "preflight_writer_gate",
            "preflight_status": preflight["preflight_status"],
            "may_writer_proceed": preflight["may_writer_proceed"],
            "writer_blocked": preflight["writer_blocked"],
            "blocking_reasons": preflight.get("blocking_reasons", []),
            "rationale": (
                "The writer may run only from a harness-derived gate receipt that "
                "does not contradict canonical adequacy backpressure."
            ),
        },
        summary="Computed writer gate preflight from harness-derived gate state.",
        replace_existing=True,
    )
    return preflight


def sync_adequacy_backpressure_queue_after_live_batch(
    run_dir: Path, *, batch_index: int, task_ids: list[str]
) -> dict[str, Any] | None:
    queue_path = run_dir / "backpressure" / "adequacy_backpressure_queue.json"
    previous_queue = read_json(queue_path) if queue_path.exists() else None
    if not (run_dir / "adequacy_assessments.jsonl").exists():
        return None
    try:
        items = adequacy_gap_items(run_dir)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    existing_gap_ids = {
        str(item.get("gap_id") or item.get("item_id"))
        for item in items
        if item.get("gap_id") or item.get("item_id")
    }
    review_items, quarantined_items = compile_review_proposed_backpressure_items(
        run_dir, existing_gap_ids=existing_gap_ids
    )
    if not items and not review_items and not quarantined_items and not queue_path.exists():
        return None
    event_id = f"evt_backpressure_batch_{batch_index:04d}_adequacy_queue_written"
    compile_adequacy_backpressure(
        run_dir.name,
        runs_dir=run_dir.parent,
        event_id=event_id,
        causally_after=[f"evt_live_batch_{batch_index:04d}_completed"],
    )
    queue = read_json(queue_path)
    previous_gap_ids = (
        {item.get("gap_id") for item in previous_queue.get("items", [])}
        if previous_queue
        else set()
    )
    current_gap_ids = {item.get("gap_id") for item in queue.get("items", [])}
    if (
        previous_queue
        and previous_queue.get("queue_status") == queue.get("queue_status")
        and previous_gap_ids == current_gap_ids
        and previous_queue.get("triggering_task_ids")
    ):
        queue["triggering_task_ids"] = previous_queue["triggering_task_ids"]
    else:
        queue["triggering_task_ids"] = task_ids
    write_json(queue_path, queue)
    refresh_artifact_manifest(run_dir)
    return queue


def writer_blocked_by_adequacy_backpressure(run_dir: Path) -> bool:
    queue_path = run_dir / "backpressure" / "adequacy_backpressure_queue.json"
    if not queue_path.exists():
        return False
    try:
        preflight = write_writer_gate_preflight(run_dir)
    except json.JSONDecodeError:
        return True
    return preflight.get("may_writer_proceed") is not True


def open_adequacy_backpressure_queue(run_dir: Path) -> dict[str, Any] | None:
    queue_path = run_dir / "backpressure" / "adequacy_backpressure_queue.json"
    if not queue_path.exists():
        return None
    try:
        queue = read_json(queue_path)
    except json.JSONDecodeError:
        return {
            "queue_status": "open",
            "writer_blocked": True,
            "items": [],
            "read_error": "json_decode_error",
        }
    if queue.get("queue_status") == "open" and queue.get("writer_blocked") is True:
        return queue
    return None


def safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    path = Path(value)
    if path.is_absolute():
        return False
    return ".." not in path.parts and path.as_posix() not in {"", "."}


def safe_reentry_identifier(value: Any) -> str | None:
    text = re.sub(r"[^a-z0-9_-]+", "_", str(value or "").lower()).strip("_")
    if not text or not ID_RE.match(text):
        return None
    return text


def safe_blocked_invocation_id(value: str) -> str:
    text = re.sub(r"[^a-z0-9_-]+", "_", value.lower()).strip("_")
    if text and ID_RE.match(text):
        return text
    return "compiler_" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def unique_ordered_strings(values: list[Any]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            ordered.append(text)
            seen.add(text)
    return ordered


def normalized_gate_effects(item: dict[str, Any]) -> dict[str, bool]:
    raw = item.get("gate_effects")
    if isinstance(raw, dict):
        return {
            "writer_blocking": raw.get("writer_blocking") is True,
            "reentry_required": raw.get("reentry_required") is True,
            "review_required": raw.get("review_required") is True,
            "claim_blocking": raw.get("claim_blocking") is not False,
        }
    gates = item.get("gates", [])
    if not isinstance(gates, list):
        gates = []
    return {
        "writer_blocking": (
            item.get("writer_blocking") is True or "writer_blocking" in gates
        ),
        "reentry_required": "reentry_required" in gates,
        "review_required": "review_required" in gates,
        "claim_blocking": (
            item.get("claim_blocking") is True or "claim_blocking" in gates
        ),
    }


def normalize_reentry_source_ref(ref: Any) -> dict[str, Any] | None:
    if isinstance(ref, dict):
        path = str(ref.get("path") or "").strip()
        if not path:
            return None
        span = ref.get("span")
        if span is not None:
            span = str(span).strip() or None
        section = ref.get("section")
        if section is not None:
            section = str(section).strip() or None
        claim_ids = [
            str(claim_id)
            for claim_id in ref.get("claim_ids", [])
            if str(claim_id).strip()
        ]
        statement_ids = [
            str(statement_id)
            for statement_id in ref.get("statement_ids", [])
            if str(statement_id).strip()
        ]
        return {
            "path": path,
            "span": span,
            "section": section,
            "claim_ids": claim_ids,
            "statement_ids": statement_ids,
        }
    text = str(ref or "").strip()
    if not text:
        return None
    if "#" in text:
        path, span = text.split("#", 1)
        return {
            "path": path.strip(),
            "span": span.strip() or None,
            "section": None,
            "claim_ids": [],
            "statement_ids": [],
        }
    return {
        "path": text,
        "span": None,
        "section": None,
        "claim_ids": [],
        "statement_ids": [],
    }


def normalized_reentry_source_refs(item: dict[str, Any]) -> list[dict[str, Any]]:
    raw_refs: list[Any] = []
    for key in ("source_refs", "affected_artifacts"):
        raw = item.get(key, [])
        if isinstance(raw, list):
            raw_refs.extend(raw)
        elif raw:
            raw_refs.append(raw)
    refs = []
    seen: set[
        tuple[str, str | None, str | None, tuple[str, ...], tuple[str, ...]]
    ] = set()
    for raw_ref in raw_refs:
        ref = normalize_reentry_source_ref(raw_ref)
        if not ref:
            continue
        key = (
            ref["path"],
            ref.get("span"),
            ref.get("section"),
            tuple(ref.get("claim_ids", [])),
            tuple(ref.get("statement_ids", [])),
        )
        if key in seen:
            continue
        refs.append(ref)
        seen.add(key)
    return refs


def reentry_source_ref_is_bounded(ref: dict[str, Any]) -> bool:
    return bool(
        ref.get("span")
        or ref.get("section")
        or ref.get("claim_ids")
        or ref.get("statement_ids")
    )


def normalized_reentry_required_action(
    item: dict[str, Any], source_refs: list[dict[str, Any]]
) -> dict[str, Any]:
    raw = item.get("required_action_detail")
    if not isinstance(raw, dict):
        raw = item.get("required_action", {})
    if isinstance(raw, dict):
        action_type = str(raw.get("action_type") or raw.get("type") or "").strip()
        role_family = str(
            raw.get("assigned_role_family")
            or raw.get("role_family")
            or "verification"
        ).strip()
        objective = str(raw.get("objective") or "").strip()
        allowed_inputs = raw.get("allowed_inputs", [])
        required_outputs = raw.get("required_outputs", [])
    else:
        action_type = str(raw or "").strip()
        role_family = "verification"
        objective = ""
        allowed_inputs = []
        required_outputs = item.get("required_outputs", [])
    if not objective:
        objective = str(
            item.get("follow_up_task")
            or item.get("recommended_follow_up")
            or item.get("failure_statement")
            or item.get("gap")
            or ""
        ).strip()
    if not allowed_inputs:
        allowed_inputs = [ref["path"] for ref in source_refs if ref.get("path")]
    return {
        "action_type": action_type,
        "assigned_role_family": role_family or "verification",
        "objective": objective,
        "allowed_inputs": unique_ordered_strings(
            allowed_inputs if isinstance(allowed_inputs, list) else [allowed_inputs]
        ),
        "required_outputs": unique_ordered_strings(
            required_outputs
            if isinstance(required_outputs, list)
            else [required_outputs]
        ),
    }


def task_specific_reentry_outputs(
    failure_type: str, action: dict[str, Any]
) -> list[str]:
    outputs = [
        output
        for output in action.get("required_outputs", [])
        if output not in REENTRY_BASE_OUTPUTS
    ]
    if (
        failure_type == "citation_support_gap"
        and "citation_support_map.json" not in outputs
    ):
        outputs.append("citation_support_map.json")
    if (
        failure_type == "non_comparable_inputs"
        and "comparability_assessment.json" not in outputs
    ):
        outputs.append("comparability_assessment.json")
    if failure_type == "provenance_gap" and "provenance_map.json" not in outputs:
        outputs.append("provenance_map.json")
    if failure_type == "contradiction" and "contradiction_assessment.json" not in outputs:
        outputs.append("contradiction_assessment.json")
    if (
        failure_type == "numerical_support_gap"
        and "numerical_support_appendix.json" not in outputs
    ):
        outputs.append("numerical_support_appendix.json")
    return unique_ordered_strings(outputs)


def expand_reentry_allowed_inputs(run_dir: Path, allowed_inputs: list[str]) -> list[str]:
    resolved: list[str] = []
    for relative in allowed_inputs:
        if not safe_relative_path(relative):
            continue
        if any(marker in relative for marker in ["*", "?", "["]):
            for match in sorted(run_dir.glob(relative)):
                if match.is_file():
                    resolved.append(rel(match, run_dir))
            continue
        source = run_dir / relative
        if source.is_file():
            resolved.append(relative)
    return unique_ordered_strings(resolved)


def reentry_queue_item_is_work_candidate(item: dict[str, Any]) -> bool:
    status = str(item.get("status") or "").lower()
    if status in BACKPRESSURE_CLOSED_STATUSES or status == "writer_constraint_queued":
        return False
    gates = normalized_gate_effects(item)
    return gates.get("writer_blocking") is True or gates.get("reentry_required") is True


def select_reentry_work_candidate(
    run_dir: Path, work_items: list[dict[str, Any]]
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[str]]:
    ranked = sorted(work_items, key=reentry_work_item_sort_key)
    first_candidate: dict[str, Any] | None = None
    first_problems: list[str] = []
    for item in ranked:
        candidate, problems = normalize_reentry_candidate(run_dir, item)
        if first_candidate is None:
            first_candidate = candidate
            first_problems = problems
        if not problems:
            return item, candidate, []
    if ranked:
        return ranked[0], first_candidate, first_problems
    return None, None, ["no unresolved writer-blocking or reentry-required item exists"]


def reentry_work_item_sort_key(item: dict[str, Any]) -> tuple[int, int, int, str]:
    gates = normalized_gate_effects(item)
    failure_type = str(item.get("failure_type") or "").lower()
    action = item.get("required_action_detail")
    action_type = ""
    if isinstance(action, dict):
        action_type = str(action.get("action_type") or "").lower()
    else:
        action_type = str(item.get("required_action") or "").lower()
    gap_id = str(item.get("gap_id") or item.get("item_id") or "")
    return (
        0 if gates.get("reentry_required") else 1,
        reentry_failure_type_priority(failure_type),
        reentry_action_priority(action_type),
        gap_id,
    )


def reentry_failure_type_priority(failure_type: str) -> int:
    priorities = {
        "citation_support_gap": 0,
        "non_comparable_inputs": 1,
        "methodology_gap": 2,
        "evidence_gap": 3,
        "provenance_gap": 4,
        "contradiction": 5,
    }
    return priorities.get(failure_type, 50)


def reentry_action_priority(action_type: str) -> int:
    priorities = {
        "citation_verification": 0,
        "statement_to_source_verification": 0,
        "reentry_research": 1,
        "methodology_repair": 2,
        "comparability_repair": 2,
    }
    return priorities.get(action_type, 50)


def normalize_reentry_candidate(
    run_dir: Path, item: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    problems: list[str] = []
    gap_id = str(item.get("gap_id") or item.get("item_id") or "").strip()
    safe_gap_id = safe_reentry_identifier(gap_id)
    if not safe_gap_id:
        problems.append("missing or unsafe gap_id")
    failure_type = str(item.get("failure_type") or "").strip()
    if not failure_type:
        problems.append("missing failure_type")
    source_refs = normalized_reentry_source_refs(item)
    if not source_refs:
        problems.append("missing affected source_refs")
    for ref in source_refs:
        if not safe_relative_path(ref.get("path")):
            problems.append(f"unsafe affected artifact path: {ref.get('path')}")
    action = normalized_reentry_required_action(item, source_refs)
    if not action.get("action_type"):
        problems.append("missing required_action.action_type")
    if not action.get("objective"):
        problems.append("missing required_action.objective")
    if not action.get("allowed_inputs"):
        problems.append("missing required_action.allowed_inputs")
    for input_path in action.get("allowed_inputs", []):
        if not safe_relative_path(input_path):
            problems.append(f"unsafe allowed input path: {input_path}")
    resolved_inputs = expand_reentry_allowed_inputs(
        run_dir, action.get("allowed_inputs", [])
    )
    if action.get("allowed_inputs") and not resolved_inputs:
        problems.append("missing available allowed input files")
    closure_condition = str(item.get("closure_condition") or "").strip()
    if not closure_condition:
        problems.append("missing closure_condition")
    closure_authority = str(item.get("closure_authority") or "").strip()
    if not closure_authority:
        problems.append("missing closure_authority")
    elif "reviewer" not in closure_authority.lower():
        problems.append("closure_authority is not reviewer-owned")
    if failure_type == "citation_support_gap" and not any(
        reentry_source_ref_is_bounded(ref) for ref in source_refs
    ):
        problems.append("citation-support item lacks bounded claim/span/section scope")
    required_outputs = [
        *REENTRY_BASE_OUTPUTS,
        *task_specific_reentry_outputs(failure_type, action),
    ]
    for output in required_outputs:
        if not safe_relative_path(output):
            problems.append(f"unsafe required output path: {output}")
        if output in REENTRY_FORBIDDEN_OUTPUTS:
            problems.append(f"forbidden required output path: {output}")
    candidate = {
        "gap_id": gap_id,
        "safe_gap_id": safe_gap_id,
        "status": str(item.get("status") or "").lower(),
        "failure_type": failure_type,
        "adequacy_criterion_id": item.get("adequacy_criterion_id"),
        "target_surface": item.get("target_surface"),
        "gate_effects": normalized_gate_effects(item),
        "affected_answer_object_part": item.get("affected_answer_object_part"),
        "affected_artifacts": source_refs,
        "action": action,
        "resolved_input_files": resolved_inputs,
        "required_outputs": unique_ordered_strings(required_outputs),
        "failure_to_repair": str(
            item.get("failure_statement") or item.get("gap") or ""
        ).strip(),
        "closure_condition": closure_condition,
        "closure_authority": closure_authority,
        "trace": {
            "objective_from": (
                "queue.required_action.objective"
                if isinstance(item.get("required_action"), dict)
                else "queue.follow_up_task|queue.failure_statement|queue.gap"
            ),
            "closure_condition_from": "queue.closure_condition",
            "closure_authority_from": "queue.closure_authority",
            "affected_artifacts_from": "queue.source_refs|queue.affected_artifacts",
            "allowed_inputs_from": [
                "queue.required_action.allowed_inputs",
                "queue.source_refs",
            ],
            "required_outputs_from": [
                "base_reentry_outputs",
                "queue.required_action.required_outputs|queue.required_outputs",
            ],
        },
    }
    return candidate, problems


def classify_reentry_compile_block(problems: list[str]) -> str:
    if any("missing available allowed input" in problem for problem in problems):
        return "blocked_by_missing_input"
    if any("authority" in problem for problem in problems):
        return "blocked_by_missing_authority"
    return "blocked_malformed_queue_item"


def blocked_reentry_task_packet(
    *,
    run_dir: Path,
    compiler_invocation_id: str,
    compiler_status: str,
    blocked_reason: str,
    candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    invocation_id = safe_blocked_invocation_id(compiler_invocation_id)
    packet_path = f"reentry/_blocked/{invocation_id}/reentry_task_packet.json"
    return {
        "schema_version": REENTRY_TASK_PACKET_SCHEMA_VERSION,
        "run_id": run_dir.name,
        "case_id": run_dir.name,
        "compiler_status": compiler_status,
        "packet_path": packet_path,
        "branch_workspace_packet_path": None,
        "source_queue_path": "backpressure/adequacy_backpressure_queue.json",
        "source_gap_id": candidate.get("gap_id") if candidate else None,
        "failure_type": candidate.get("failure_type") if candidate else None,
        "adequacy_criterion_id": (
            candidate.get("adequacy_criterion_id") if candidate else None
        ),
        "target_surface": candidate.get("target_surface") if candidate else None,
        "gate_effects": candidate.get("gate_effects") if candidate else None,
        "affected_answer_object_part": (
            candidate.get("affected_answer_object_part") if candidate else None
        ),
        "affected_artifacts": (
            candidate.get("affected_artifacts", []) if candidate else []
        ),
        "task": None,
        "closure": {
            "closure_condition": candidate.get("closure_condition") if candidate else None,
            "closure_authority": (
                candidate.get("closure_authority") if candidate else "reviewer"
            ),
            "allowed_repair_result_statuses": [],
        },
        "trace": candidate.get("trace", {}) if candidate else {},
        "claim_boundary": {"must_not_claim": REENTRY_MUST_NOT_CLAIM},
        "writer_permission": False,
        "compiler_blocks_reentry": True,
        "blocked_reason": blocked_reason,
    }


def ready_reentry_task_packet(run_dir: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    gap_id = candidate["safe_gap_id"]
    packet_path = f"reentry/{gap_id}/reentry_task_packet.json"
    return {
        "schema_version": REENTRY_TASK_PACKET_SCHEMA_VERSION,
        "run_id": run_dir.name,
        "case_id": run_dir.name,
        "compiler_status": "ready",
        "packet_path": packet_path,
        "branch_workspace_packet_path": "reentry_task_packet.json",
        "source_queue_path": "backpressure/adequacy_backpressure_queue.json",
        "source_gap_id": candidate["gap_id"],
        "failure_type": candidate["failure_type"],
        "adequacy_criterion_id": candidate.get("adequacy_criterion_id"),
        "target_surface": candidate.get("target_surface"),
        "gate_effects": candidate["gate_effects"],
        "affected_answer_object_part": candidate.get("affected_answer_object_part"),
        "affected_artifacts": candidate["affected_artifacts"],
        "task": {
            "role_family": candidate["action"]["assigned_role_family"],
            "action_type": candidate["action"]["action_type"],
            "objective": candidate["action"]["objective"],
            "allowed_inputs": candidate["action"]["allowed_inputs"],
            "resolved_input_files": candidate["resolved_input_files"],
            "required_outputs": candidate["required_outputs"],
            "non_goals": [
                "Do not reopen the whole research question.",
                "Do not verify unrelated claims outside the affected scope.",
                "Do not rewrite the final report.",
                "Do not update the canonical backpressure queue.",
                "Do not authorize the writer.",
                "Do not claim benchmark score, Grep parity, product readiness, "
                "or final answer success.",
            ],
            "failure_to_repair": candidate["failure_to_repair"],
        },
        "closure": {
            "closure_condition": candidate["closure_condition"],
            "closure_authority": candidate["closure_authority"],
            "allowed_repair_result_statuses": [
                "closed_candidate",
                "narrowed",
                "open",
                "blocked_by_input",
                "blocked_by_tooling",
                "contradicted",
                "lawful_partial_candidate",
            ],
        },
        "trace": candidate["trace"],
        "claim_boundary": {"must_not_claim": REENTRY_MUST_NOT_CLAIM},
        "writer_permission": False,
        "compiler_blocks_reentry": False,
        "blocked_reason": None,
    }


def validate_reentry_task_packet_object(packet: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if packet.get("schema_version") != REENTRY_TASK_PACKET_SCHEMA_VERSION:
        problems.append("invalid schema_version")
    status = packet.get("compiler_status")
    packet_path = packet.get("packet_path")
    if not safe_relative_path(packet_path):
        problems.append("unsafe packet_path")
    if status == "ready":
        source_gap_id = packet.get("source_gap_id")
        safe_gap_id = safe_reentry_identifier(source_gap_id)
        expected_path = (
            f"reentry/{safe_gap_id}/reentry_task_packet.json" if safe_gap_id else None
        )
        if not safe_gap_id:
            problems.append("ready packet missing safe source_gap_id")
        if expected_path and packet_path != expected_path:
            problems.append("ready packet path does not match source_gap_id")
        if packet.get("branch_workspace_packet_path") != "reentry_task_packet.json":
            problems.append("ready packet missing branch workspace packet path")
        task = packet.get("task")
        if not isinstance(task, dict):
            problems.append("ready packet missing task")
        else:
            required_outputs = task.get("required_outputs", [])
            for base_output in REENTRY_BASE_OUTPUTS:
                if base_output not in required_outputs:
                    problems.append(f"ready packet missing base output {base_output}")
            if not task.get("objective"):
                problems.append("ready packet missing task objective")
            if not task.get("resolved_input_files"):
                problems.append("ready packet has no resolved input files")
            if not any(
                "reopen the whole research question" in str(non_goal).lower()
                for non_goal in task.get("non_goals", [])
            ):
                problems.append("ready packet non_goals do not block whole-task reopening")
        closure = packet.get("closure", {})
        if not closure.get("closure_condition"):
            problems.append("ready packet missing closure_condition")
        if "reviewer" not in str(closure.get("closure_authority") or "").lower():
            problems.append("ready packet closure authority is not reviewer-owned")
        if not packet.get("trace"):
            problems.append("ready packet missing trace")
        if packet.get("writer_permission") is not False:
            problems.append("ready packet cannot grant writer permission")
    elif status in REENTRY_BLOCKED_COMPILER_STATUSES:
        if not str(packet.get("blocked_reason") or "").strip():
            problems.append("blocked packet missing blocked_reason")
        if packet.get("task") is not None:
            problems.append("blocked packet must not contain an executable task")
        if packet.get("writer_permission") is not False:
            problems.append("blocked packet cannot grant writer permission")
        if packet.get("compiler_blocks_reentry") is not True:
            problems.append("blocked packet must mark compiler_blocks_reentry true")
        if not str(packet_path or "").startswith("reentry/_blocked/"):
            problems.append("blocked packet path must live under reentry/_blocked/")
    else:
        problems.append(f"invalid compiler_status {status!r}")
    must_not_claim = set(
        (packet.get("claim_boundary") or {}).get("must_not_claim", [])
    )
    missing_claim_blocks = set(REENTRY_MUST_NOT_CLAIM) - must_not_claim
    if missing_claim_blocks:
        problems.append(
            "packet missing claim boundary blocks: "
            + ", ".join(sorted(missing_claim_blocks))
        )
    return problems


def write_reentry_task_packet(run_dir: Path, packet: dict[str, Any]) -> Path:
    problems = validate_reentry_task_packet_object(packet)
    if problems:
        raise HarnessError("reentry task packet failed validation: " + "; ".join(problems))
    packet_path = run_dir / packet["packet_path"]
    write_json(packet_path, packet)
    event_suffix = safe_blocked_invocation_id(packet["packet_path"])
    append_event(
        run_dir,
        event_id=f"evt_reentry_task_packet_{event_suffix}",
        event_type="reentry.task_packet_written",
        inputs=["backpressure/adequacy_backpressure_queue.json"],
        outputs=[packet["packet_path"]],
        decision={
            "decision_type": "compile_bounded_reentry_task_packet",
            "compiler_status": packet["compiler_status"],
            "source_gap_id": packet.get("source_gap_id"),
            "rationale": (
                "Convert canonical adequacy backpressure into exactly one bounded "
                "repair packet, or block if the transition is underspecified."
            ),
        },
        summary="Compiled deterministic re-entry task packet.",
        replace_existing=True,
    )
    refresh_artifact_manifest(run_dir)
    return packet_path


def compile_reentry_task_packet_for_run(
    run_dir: Path,
    *,
    assigned_gap_id: str | None = None,
    compiler_invocation_id: str = "compiler_001",
) -> Path:
    queue_path = run_dir / "backpressure" / "adequacy_backpressure_queue.json"
    if not queue_path.exists():
        packet = blocked_reentry_task_packet(
            run_dir=run_dir,
            compiler_invocation_id=compiler_invocation_id,
            compiler_status="blocked_by_missing_input",
            blocked_reason="backpressure/adequacy_backpressure_queue.json is missing",
        )
        return write_reentry_task_packet(run_dir, packet)
    try:
        queue = read_json(queue_path)
    except json.JSONDecodeError:
        packet = blocked_reentry_task_packet(
            run_dir=run_dir,
            compiler_invocation_id=compiler_invocation_id,
            compiler_status="blocked_malformed_queue_item",
            blocked_reason="backpressure queue is not valid JSON",
        )
        return write_reentry_task_packet(run_dir, packet)
    items = [item for item in queue.get("items", []) if isinstance(item, dict)]
    work_items = [item for item in items if reentry_queue_item_is_work_candidate(item)]
    if assigned_gap_id:
        work_items = [
            item
            for item in items
            if str(item.get("gap_id") or item.get("item_id") or "") == assigned_gap_id
        ]
        if not work_items:
            packet = blocked_reentry_task_packet(
                run_dir=run_dir,
                compiler_invocation_id=compiler_invocation_id,
                compiler_status="blocked_by_missing_input",
                blocked_reason=f"assigned gap_id not found: {assigned_gap_id}",
            )
            return write_reentry_task_packet(run_dir, packet)
    elif not work_items:
        packet = blocked_reentry_task_packet(
            run_dir=run_dir,
            compiler_invocation_id=compiler_invocation_id,
            compiler_status="blocked_no_eligible_item",
            blocked_reason="no unresolved writer-blocking or reentry-required item exists",
        )
        return write_reentry_task_packet(run_dir, packet)
    selected_item, candidate, problems = select_reentry_work_candidate(run_dir, work_items)
    if selected_item is None or candidate is None:
        packet = blocked_reentry_task_packet(
            run_dir=run_dir,
            compiler_invocation_id=compiler_invocation_id,
            compiler_status="blocked_by_assignment_ambiguity",
            blocked_reason="no eligible singular item could be selected",
        )
        return write_reentry_task_packet(run_dir, packet)
    if problems:
        packet = blocked_reentry_task_packet(
            run_dir=run_dir,
            compiler_invocation_id=compiler_invocation_id,
            compiler_status=classify_reentry_compile_block(problems),
            blocked_reason="; ".join(problems),
            candidate=candidate,
        )
        return write_reentry_task_packet(run_dir, packet)
    return write_reentry_task_packet(
        run_dir, ready_reentry_task_packet(run_dir, candidate)
    )


def compile_reentry_task_packet(
    case_id: str,
    *,
    runs_dir: Path | str | None = None,
    assigned_gap_id: str | None = None,
    compiler_invocation_id: str = "compiler_001",
) -> Path:
    run_dir = run_path(case_id, runs_dir)
    if not run_dir.exists():
        raise HarnessError(f"run does not exist: {run_dir}")
    return compile_reentry_task_packet_for_run(
        run_dir,
        assigned_gap_id=assigned_gap_id,
        compiler_invocation_id=compiler_invocation_id,
    )


def reentry_integration_paths_for_packet(packet: dict[str, Any]) -> dict[str, str] | None:
    safe_gap_id = safe_reentry_identifier(packet.get("source_gap_id"))
    if not safe_gap_id:
        return None
    return {
        "reentry_synthesis": f"reentry/{safe_gap_id}/reentry_synthesis.md",
        "adequacy_delta": f"reentry/{safe_gap_id}/adequacy_delta.json",
    }


def ready_reentry_packets(run_dir: Path) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for packet_path in sorted((run_dir / "reentry").rglob("reentry_task_packet.json")):
        packet = read_optional_json(packet_path)
        if packet.get("compiler_status") == "ready":
            packets.append(packet)
    return packets


def reentry_result_paths(run_dir: Path) -> list[Path]:
    branch_paths = sorted((run_dir / "branches").glob("*/reentry_result.json"))
    live_paths = sorted(
        (run_dir / "live_executor" / "role_outputs").glob(
            "task_reentry_followup*/branches/*/reentry_result.json"
        )
    )
    return unique_paths([*branch_paths, *live_paths])


def unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = path.as_posix()
        if key in seen:
            continue
        unique.append(path)
        seen.add(key)
    return unique


def read_reentry_result(path: Path) -> dict[str, Any]:
    result = read_optional_json(path)
    if not result:
        return {}
    result["_path"] = path
    return result


def reentry_results_for_gap(run_dir: Path, gap_id: str) -> list[dict[str, Any]]:
    results = []
    for path in reentry_result_paths(run_dir):
        result = read_reentry_result(path)
        if str(result.get("source_gap_id") or "") == gap_id:
            results.append(result)
    return results


def citation_support_map_path_for_result(result_path: Path) -> Path:
    return result_path.parent / "citation_support_map.json"


def validate_citation_support_map_object(
    support_map: dict[str, Any],
    *,
    require_no_writer_blocking: bool,
) -> list[str]:
    problems: list[str] = []
    schema_version = support_map.get("schema_version")
    if schema_version not in {
        CITATION_SUPPORT_MAP_SCHEMA_VERSION,
        *CITATION_SUPPORT_MAP_LEGACY_SCHEMA_VERSIONS,
    }:
        problems.append("invalid citation_support_map schema_version")
    claims = support_map.get("claims")
    if not isinstance(claims, list):
        claims = support_map.get("support_map")
    if not isinstance(claims, list) or not claims:
        problems.append("citation_support_map claims must be a non-empty list")
        return problems
    for index, claim in enumerate(claims, start=1):
        if not isinstance(claim, dict):
            problems.append(f"claim {index} is not an object")
            continue
        claim_id = str(
            claim.get("claim_id") or claim.get("statement_id") or f"claim_{index}"
        ).strip()
        status = str(claim.get("support_status") or "").strip()
        if status not in CITATION_SUPPORT_STATUSES:
            problems.append(f"{claim_id}: invalid support_status {status!r}")
            continue
        evidence_refs = claim.get("evidence_refs", [])
        if status == "supported":
            status = "directly_supported"
        if status in {
            "directly_supported",
            "partially_supported",
            "indirectly_supported",
        } and (not isinstance(evidence_refs, list) or not evidence_refs):
            problems.append(f"{claim_id}: supported status lacks evidence_refs")
        writer_blocking = claim.get("writer_blocking")
        if writer_blocking is None:
            writer_blocking = status in CITATION_WRITER_BLOCKING_STATUSES
        if require_no_writer_blocking and (
            writer_blocking is True or status in CITATION_WRITER_BLOCKING_STATUSES
        ):
            problems.append(
                f"{claim_id}: writer-blocking citation support remains {status}"
            )
    return problems


def reentry_branch_output_paths(branch_id: str, required_outputs: list[str]) -> list[str]:
    return [f"branches/{branch_id}/{output}" for output in required_outputs]


def read_run_control_receipt(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise HarnessError(f"run-control receipt is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise HarnessError(
            "run-control receipt must be JSON for dry-run planning in this harness"
        ) from error


def require_dry_run_control_receipt(
    receipt_path: Path,
    *,
    run_id: str,
) -> dict[str, Any]:
    receipt = read_run_control_receipt(receipt_path)
    errors = []
    if receipt.get("run_id") != run_id:
        errors.append(f"run_id mismatch: {receipt.get('run_id')!r}")
    if not receipt.get("receipt_id"):
        errors.append("missing receipt_id")
    if not receipt.get("run_purpose"):
        errors.append("missing run_purpose")
    approval = receipt.get("approval", {})
    if approval.get("approved_for_execution"):
        errors.append("dry-run planner refuses receipts approved for live execution")
    if approval.get("approved_for_dry_run_planning") is not True:
        errors.append("receipt is not approved_for_dry_run_planning")
    runner = receipt.get("runner", {})
    if runner.get("kind") != "codex_exec_box":
        errors.append("runner.kind must be codex_exec_box")
    if not runner.get("cwd"):
        errors.append("runner.cwd is required")
    if not runner.get("transcript_root"):
        errors.append("runner.transcript_root is required")
    bounds = receipt.get("operational_bounds", {})
    if not bounds.get("max_wall_clock_minutes"):
        errors.append("operational_bounds.max_wall_clock_minutes is required")
    if bounds.get("foreground_supervision_required") is not True:
        errors.append("foreground_supervision_required must be true")
    if bounds.get("automatic_retry_allowed") is not False:
        errors.append("automatic_retry_allowed must be false")
    if not bounds.get("kill_path"):
        errors.append("operational_bounds.kill_path is required")
    if not receipt.get("allowed_claims_if_success"):
        errors.append("allowed_claims_if_success is required")
    if not receipt.get("non_claims_even_if_success"):
        errors.append("non_claims_even_if_success is required")
    if errors:
        raise HarnessError(f"run-control receipt failed dry-run validation: {'; '.join(errors)}")
    return receipt


def require_live_execution_control_receipt(
    receipt_path: Path,
    *,
    run_id: str,
) -> dict[str, Any]:
    receipt = read_run_control_receipt(receipt_path)
    errors = []
    if receipt.get("schema_version") != "codex-dr.run_control_receipt.v1":
        errors.append("schema_version must be codex-dr.run_control_receipt.v1")
    if receipt.get("run_id") != run_id:
        errors.append(f"run_id mismatch: {receipt.get('run_id')!r}")
    if not receipt.get("receipt_id"):
        errors.append("missing receipt_id")
    if not receipt.get("bead_id"):
        errors.append("missing bead_id")
    if not receipt.get("run_purpose"):
        errors.append("missing run_purpose")
    approval = receipt.get("approval", {})
    if approval.get("approved_for_execution") is not True:
        errors.append("receipt is not approved_for_execution")
    if approval.get("approved_for_dry_run_planning") is not True:
        errors.append("receipt must also be approved_for_dry_run_planning")
    if not approval.get("approval_note"):
        errors.append("approval.approval_note is required")
    runner = receipt.get("runner", {})
    if runner.get("kind") != "codex_exec_box":
        errors.append("runner.kind must be codex_exec_box")
    command_surface = runner.get("command_surface", "")
    if "mesh-execute-live" not in command_surface:
        errors.append("runner.command_surface must name mesh-execute-live")
    if not runner.get("cwd"):
        errors.append("runner.cwd is required")
    if not runner.get("transcript_root"):
        errors.append("runner.transcript_root is required")
    bounds = receipt.get("operational_bounds", {})
    if bounds.get("max_cases") != 1:
        errors.append("operational_bounds.max_cases must be 1")
    if bounds.get("max_live_attempts") != 1:
        errors.append("operational_bounds.max_live_attempts must be 1")
    if bounds.get("max_reentry_rounds") not in {0, 1}:
        errors.append("operational_bounds.max_reentry_rounds must be 0 or 1")
    wall_clock = bounds.get("max_wall_clock_minutes")
    if not isinstance(wall_clock, int) or wall_clock <= 0:
        errors.append("operational_bounds.max_wall_clock_minutes must be a positive integer")
    if bounds.get("foreground_supervision_required") is not True:
        errors.append("foreground_supervision_required must be true")
    if bounds.get("automatic_retry_allowed") is not False:
        errors.append("automatic_retry_allowed must be false")
    if not bounds.get("kill_path"):
        errors.append("operational_bounds.kill_path is required")
    expected = receipt.get("expected_artifacts", {})
    if not expected.get("run_bundle"):
        errors.append("expected_artifacts.run_bundle is required")
    if not expected.get("transcript_capture"):
        errors.append("expected_artifacts.transcript_capture is required")
    scoring = receipt.get("scoring", {})
    if scoring.get("scorer_status") != "blocked":
        errors.append("scoring.scorer_status must remain blocked for this smoke")
    if not receipt.get("allowed_claims_if_success"):
        errors.append("allowed_claims_if_success is required")
    if not receipt.get("non_claims_even_if_success"):
        errors.append("non_claims_even_if_success is required")
    inputs = receipt.get("inputs", {})
    forbidden_sources = {str(item).lower() for item in inputs.get("forbidden_sources", [])}
    for forbidden in ["secrets", "customer data", "root env files"]:
        if forbidden not in forbidden_sources:
            errors.append(f"inputs.forbidden_sources must include {forbidden!r}")
    if errors:
        raise HarnessError(
            f"run-control receipt failed live-execution validation: {'; '.join(errors)}"
        )
    return receipt


def require_scoring_control_receipt(
    receipt_path: Path,
    *,
    run_id: str,
) -> dict[str, Any]:
    receipt = read_run_control_receipt(receipt_path)
    errors = []
    if receipt.get("schema_version") != "codex-dr.run_control_receipt.v1":
        errors.append("schema_version must be codex-dr.run_control_receipt.v1")
    if receipt.get("run_id") != run_id:
        errors.append(f"run_id mismatch: {receipt.get('run_id')!r}")
    if not receipt.get("receipt_id"):
        errors.append("missing receipt_id")
    if not receipt.get("bead_id"):
        errors.append("missing bead_id")
    if not receipt.get("run_purpose"):
        errors.append("missing run_purpose")
    runner = receipt.get("runner", {})
    if runner.get("kind") not in {
        "scorer",
        "local_script",
        "benchmark_owner_api",
        "provider_api",
    }:
        errors.append("runner.kind must name an approved scoring surface")
    if "score" not in str(runner.get("command_surface", "")):
        errors.append("runner.command_surface must name alexandria-dr score")
    if not runner.get("cwd"):
        errors.append("runner.cwd is required")
    if not runner.get("transcript_root"):
        errors.append("runner.transcript_root is required")
    authority = receipt.get("authority", {})
    if not authority.get("case_manifest"):
        errors.append("authority.case_manifest is required")
    if not authority.get("scorer_manifest"):
        errors.append("authority.scorer_manifest is required")
    bounds = receipt.get("operational_bounds", {})
    if bounds.get("max_cases") != 1:
        errors.append("operational_bounds.max_cases must be 1")
    if bounds.get("max_live_attempts") != 1:
        errors.append("operational_bounds.max_live_attempts must be 1")
    if bounds.get("foreground_supervision_required") is not True:
        errors.append("foreground_supervision_required must be true")
    if bounds.get("automatic_retry_allowed") is not False:
        errors.append("automatic_retry_allowed must be false")
    wall_clock = bounds.get("max_wall_clock_minutes")
    if not isinstance(wall_clock, int) or wall_clock <= 0:
        errors.append("operational_bounds.max_wall_clock_minutes must be a positive integer")
    if not bounds.get("kill_path"):
        errors.append("operational_bounds.kill_path is required")
    scoring = receipt.get("scoring", {})
    if scoring.get("benchmark_family") != "DRACO":
        errors.append("scoring.benchmark_family must be DRACO")
    if scoring.get("scorer_status") != "approved":
        errors.append("scoring.scorer_status must be approved")
    if not scoring.get("judge_or_scorer") or scoring.get("judge_or_scorer") == "evidence-pending":
        errors.append("scoring.judge_or_scorer must be concrete")
    if (
        not scoring.get("prompt_or_code_version")
        or scoring.get("prompt_or_code_version") == "evidence-pending"
    ):
        errors.append("scoring.prompt_or_code_version must be concrete")
    if not receipt.get("allowed_claims_if_success"):
        errors.append("allowed_claims_if_success is required")
    if not receipt.get("non_claims_even_if_success"):
        errors.append("non_claims_even_if_success is required")
    approval = receipt.get("approval", {})
    if approval.get("approved_for_execution") is not True:
        errors.append("receipt is not approved_for_execution")
    if errors:
        raise HarnessError(f"run-control receipt failed scoring validation: {'; '.join(errors)}")
    return receipt


def deepresearch_bench_live_run_controls(
    suite_id: str,
    *,
    prompt_overlay: Path,
    output_dir: Path,
    bead_id: str,
    runs_dir: Path | str | None = None,
    max_wall_clock_minutes: int = 25,
) -> Path:
    validate_id(suite_id, "suite_id")
    if not bead_id:
        raise HarnessError("bead_id is required")
    if max_wall_clock_minutes <= 0:
        raise HarnessError("max_wall_clock_minutes must be positive")
    suite_dir = run_path(suite_id, runs_dir)
    suite = read_json(suite_dir / "benchmark_suite_manifest.json")
    if suite.get("benchmark_family") != BENCHMARK_FAMILY_DEEPRESEARCH_BENCH:
        raise HarnessError("live run controls require a DeepResearch Bench suite")
    overlay = read_validated_prompt_overlay(prompt_overlay)
    output_dir.mkdir(parents=True, exist_ok=True)
    receipts = []
    for case in suite.get("cases", []):
        run_id = case.get("run_id")
        if not run_id:
            raise HarnessError("suite case lacks run_id")
        receipt = deepresearch_bench_live_run_control_payload(
            run_id=run_id,
            bead_id=bead_id,
            prompt_overlay=prompt_overlay,
            overlay=overlay,
            max_wall_clock_minutes=max_wall_clock_minutes,
        )
        receipt_path = output_dir / f"{run_id}.json"
        write_json(receipt_path, receipt)
        require_live_execution_control_receipt(receipt_path, run_id=run_id)
        receipts.append(
            {
                "run_id": run_id,
                "receipt": receipt_path.as_posix(),
                "row_indices": case.get("row_indices", []),
            }
        )
    summary = {
        "schema_version": "codex-dr.deepresearch_bench_live_run_controls.v1",
        "suite_id": suite_id,
        "bead_id": bead_id,
        "case_count": len(receipts),
        "prompt_overlay": {
            "path": prompt_overlay.as_posix(),
            "candidate_id": overlay.get("candidate_id"),
            "candidate_chain": overlay.get("candidate_chain", []),
        },
        "operational_bounds": {
            "max_cases_per_receipt": 1,
            "max_live_attempts": 1,
            "max_reentry_rounds": 1,
            "max_wall_clock_minutes": max_wall_clock_minutes,
            "automatic_retry_allowed": False,
        },
        "receipts": receipts,
        "claim_boundary": {
            "allowed_claims_if_success": [
                (
                    "Selected DeepResearch Bench subset cases executed through the "
                    "live Codex CLI DR mesh with composite overlay custody."
                )
            ],
            "blocked_claims": [
                "DeepResearch Bench score",
                "Grep parity",
                "leaderboard rank",
                "product readiness",
                "official benchmark submission",
            ],
        },
        "produced_at": FIXTURE_TIMESTAMP,
    }
    write_json(output_dir / "run_controls_summary.json", summary)
    return output_dir


def deepresearch_bench_live_run_control_payload(
    *,
    run_id: str,
    bead_id: str,
    prompt_overlay: Path,
    overlay: dict[str, Any],
    max_wall_clock_minutes: int,
) -> dict[str, Any]:
    run_bundle = (
        "sandbox/codex-dr/tmp/deepresearch_bench_overlay_subset_v2_2026_04_24/"
        f"runs/{run_id}/"
    )
    return {
        "schema_version": "codex-dr.run_control_receipt.v1",
        "receipt_id": f"run_control_{run_id}_composite_overlay_2026_04_24",
        "run_id": run_id,
        "bead_id": bead_id,
        "run_purpose": (
            "Execute one selected DeepResearch Bench subset prompt through the "
            "live Codex CLI DR mesh with the composite prompt overlay "
            f"`{overlay.get('overlay_id')}`."
        ),
        "approval": {
            "approved_for_dry_run_planning": True,
            "approved_for_execution": True,
            "approval_note": (
                "Principal authorized autonomous Codex-DR benchmark flywheel work; "
                "this receipt scopes one live subset-v2 case and keeps scorer and "
                "public benchmark claims blocked."
            ),
        },
        "runner": {
            "kind": "codex_exec_box",
            "command_surface": "alexandria-dr mesh-execute-live",
            "cwd": "sandbox/codex-dr/",
            "transcript_root": f"{run_bundle}transcripts/",
        },
        "operational_bounds": {
            "max_cases": 1,
            "max_live_attempts": 1,
            "max_reentry_rounds": 1,
            "max_wall_clock_minutes": max_wall_clock_minutes,
            "foreground_supervision_required": True,
            "automatic_retry_allowed": False,
            "kill_path": "foreground supervisor sends SIGINT, then SIGTERM",
        },
        "inputs": {
            "allowed_sources": [
                "DeepResearch Bench generator-visible prompt",
                "case_manifest.json",
                "plan.md",
                "task_graph.json",
                "public web sources",
                "sandbox run artifacts",
                prompt_overlay.as_posix(),
            ],
            "forbidden_sources": [
                "secrets",
                "customer data",
                "root env files",
                "sealed benchmark reference answers",
                "scorer-only criteria",
                "private benchmark corpora",
            ],
            "data_policy": (
                "Generator roles may use the prompt, public sources, and local "
                "run-bundle artifacts. They must not read scorer-only reference "
                "answers, criteria, secrets, or private corpora."
            ),
        },
        "expected_artifacts": {
            "run_bundle": run_bundle,
            "event_log": f"{run_bundle}events.jsonl",
            "transcript_capture": f"{run_bundle}transcripts/",
            "raw_report_export": (
                "sandbox/codex-dr/tmp/deepresearch_bench_overlay_subset_v2_2026_04_24/"
                "deepresearch_bench_overlay_subset_v2_raw_reports.jsonl"
            ),
        },
        "scoring": {
            "benchmark_family": BENCHMARK_FAMILY_DEEPRESEARCH_BENCH,
            "judge_or_scorer": "DeepResearch Bench RACE bridge",
            "scorer_status": "blocked",
        },
        "allowed_claims_if_success": [
            (
                "One selected DeepResearch Bench subset case executed through the "
                "live Codex CLI DR mesh with composite overlay custody and claim "
                "boundaries preserved."
            )
        ],
        "non_claims_even_if_success": [
            "DeepResearch Bench score",
            "Grep parity",
            "leaderboard rank",
            "product readiness",
            "official benchmark submission",
            "scorer-backed evaluation",
        ],
    }


def require_launch_plan_control_receipt(
    receipt_path: Path,
    *,
    run_id: str,
) -> tuple[dict[str, Any], bool]:
    receipt = read_run_control_receipt(receipt_path)
    if receipt.get("approval", {}).get("approved_for_execution") is True:
        return require_live_execution_control_receipt(receipt_path, run_id=run_id), True
    return require_dry_run_control_receipt(receipt_path, run_id=run_id), False


def order_tasks_for_execution(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered: list[dict[str, Any]] = []
    emitted: set[str] = set()
    remaining = list(tasks)
    while remaining:
        ready = [
            task
            for task in remaining
            if all(dependency in emitted for dependency in task.get("depends_on", []))
        ]
        if not ready:
            blocked = ", ".join(task.get("task_id", "<unknown>") for task in remaining)
            raise HarnessError(f"task graph contains unsatisfied or cyclic dependencies: {blocked}")
        for task in ready:
            ordered.append(task)
            emitted.add(task["task_id"])
            remaining.remove(task)
    return ordered


def dependency_order_problems(
    ordered_task_ids: list[str],
    dependencies_by_task: dict[str, list[str]],
) -> list[str]:
    problems = []
    seen: set[str] = set()
    known_task_ids = set(dependencies_by_task)
    for task_id in ordered_task_ids:
        if task_id not in known_task_ids:
            problems.append(f"{task_id}: task not present in dependency graph")
            seen.add(task_id)
            continue
        for dependency in dependencies_by_task.get(task_id, []):
            if dependency not in known_task_ids:
                problems.append(f"{task_id}: dependency {dependency} is missing")
            elif dependency not in seen:
                problems.append(f"{task_id}: dependency {dependency} executed later")
        seen.add(task_id)
    missing_executions = [task_id for task_id in known_task_ids if task_id not in seen]
    if missing_executions:
        problems.append(
            "missing live role execution for task(s): " + ", ".join(sorted(missing_executions))
        )
    return problems


def validate_draco_evaluation_output(
    run_dir: Path,
    *,
    evaluation: dict[str, Any],
    manifest: dict[str, Any],
    receipt: dict[str, Any],
) -> tuple[float, float]:
    problems = []
    if evaluation.get("schema_version") != "codex-dr.draco_evaluation_output.v1":
        problems.append("evaluation output schema_version is invalid")
    if evaluation.get("run_id") != run_dir.name:
        problems.append("evaluation output run_id mismatch")
    if evaluation.get("benchmark_family") != "DRACO":
        problems.append("evaluation output benchmark_family must be DRACO")
    if evaluation.get("scorer_manifest") != "scorer_manifest.json":
        problems.append("evaluation output scorer_manifest must reference scorer_manifest.json")
    verdicts = evaluation.get("criterion_verdicts", [])
    if not verdicts:
        problems.append("evaluation output lacks criterion_verdicts")
    computed_raw = 0.0
    for verdict in verdicts:
        try:
            weight = float(verdict.get("weight"))
            value = float(verdict.get("verdict"))
        except (TypeError, ValueError):
            problems.append("criterion verdicts must have numeric weight and verdict")
            continue
        if not verdict.get("criterion_id") or not verdict.get("criterion_group"):
            problems.append("criterion verdict missing id or group")
        if not verdict.get("rationale"):
            problems.append("criterion verdict missing rationale")
        evidence_refs = verdict.get("evidence_refs", [])
        if not evidence_refs:
            problems.append(f"{verdict.get('criterion_id', '<unknown>')}: missing evidence refs")
        for ref in evidence_refs:
            if not reference_exists(run_dir, ref):
                problems.append(
                    f"{verdict.get('criterion_id', '<unknown>')}: missing evidence ref {ref}"
                )
        computed_raw += weight * value
    try:
        raw_score = float(evaluation.get("raw_score"))
        normalized_score = float(evaluation.get("normalized_score"))
    except (TypeError, ValueError):
        problems.append("raw_score and normalized_score must be numeric")
        raw_score = 0.0
        normalized_score = 0.0
    if not math.isclose(raw_score, computed_raw, rel_tol=1e-9, abs_tol=1e-9):
        problems.append("raw_score does not match weighted criterion verdicts")
    score_range = manifest.get("scoring_formula", {}).get("score_range", [0, 1])
    if (
        not isinstance(score_range, list)
        or len(score_range) != 2
        or normalized_score < float(score_range[0])
        or normalized_score > float(score_range[1])
    ):
        problems.append("normalized_score is outside the declared score_range")
    citations = evaluation.get("citations", [])
    if not citations:
        problems.append("evaluation output lacks citations")
    for citation in citations:
        source_ref = citation.get("source_ref")
        if not source_ref or not reference_exists(run_dir, source_ref):
            problems.append(f"missing citation source ref {source_ref!r}")
        if not citation.get("supports"):
            problems.append(f"citation {source_ref!r} lacks supports")
    transcript_root = manifest.get("output_paths", {}).get("judge_transcript_root", "")
    judge_refs = evaluation.get("judge_transcript_refs", [])
    if not judge_refs:
        problems.append("evaluation output lacks judge_transcript_refs")
    for ref in judge_refs:
        if not reference_exists(run_dir, ref):
            problems.append(f"missing judge transcript ref {ref}")
        elif transcript_root and not ref.startswith(transcript_root):
            problems.append(f"judge transcript ref escapes declared transcript root: {ref}")
    claim_boundary = evaluation.get("claim_boundary", {})
    blocked_after_scoring = {
        claim.lower() for claim in claim_boundary.get("blocked_claims_after_scoring", [])
    }
    if not {"grep parity", "leaderboard rank", "product readiness"}.issubset(
        blocked_after_scoring
    ):
        problems.append("evaluation output claim boundary is missing blocked claims")
    for claim in claim_boundary.get("allowed_claims_after_scoring", []):
        text = str(claim).lower()
        if "grep parity" in text or "leaderboard" in text or "product readiness" in text:
            problems.append(f"evaluation output widens blocked claims: {claim}")
    if manifest.get("benchmark_family") != receipt.get("scoring", {}).get("benchmark_family"):
        problems.append("scorer manifest benchmark family does not match scoring receipt")
    if problems:
        raise HarnessError(f"evaluation output failed validation: {'; '.join(problems)}")
    return raw_score, normalized_score


def mesh_live_plan(
    case_id: str,
    *,
    run_control: Path,
    prompt_overlay: Path | None = None,
    runs_dir: Path | str | None = None,
) -> Path:
    run_dir = run_path(case_id, runs_dir)
    if not run_dir.exists():
        raise HarnessError(f"run does not exist: {run_dir}")
    if not is_mesh_run(run_dir):
        raise HarnessError("mesh-live-plan requires a provider-off DR mesh run bundle")
    receipt, execution_approved = require_launch_plan_control_receipt(
        run_control, run_id=case_id
    )
    graph = read_json(run_dir / "task_graph.json")
    role_configs = read_json(run_dir / "role_configs.json")
    boxes = read_json(run_dir / "terminal_agent_boxes.json")
    roles_by_id = {role["role_config_id"]: role for role in role_configs.get("roles", [])}
    boxes_by_id = {box["box_id"]: box for box in boxes.get("boxes", [])}
    launch_root = run_dir / "live_adapter"
    overlay_payload = (
        read_validated_prompt_overlay(prompt_overlay) if prompt_overlay else None
    )
    if overlay_payload:
        write_json(launch_root / "prompt_overlay.json", overlay_payload)
    role_launch_plans = []
    prompt_outputs = []
    for task in order_tasks_for_execution(graph.get("tasks", [])):
        task_id = task["task_id"]
        role_config_id = task.get("role_config_id")
        role = roles_by_id.get(role_config_id)
        if not role:
            raise HarnessError(f"task {task_id} references missing role config {role_config_id}")
        box = boxes_by_id.get(task.get("assigned_box_id"))
        if not box:
            raise HarnessError(
                f"task {task_id} references missing box {task.get('assigned_box_id')}"
            )
        prompt_path = Path("live_adapter") / "prompts" / f"{task_id}.md"
        workspace = (SANDBOX_ROOT / ".agent-workspaces" / case_id / role["role"]).resolve()
        last_message_path = (run_dir / "last_messages" / f"{task_id}.md").resolve()
        transcript_path = Path("transcripts") / f"{task_id}.jsonl"
        write_text(
            run_dir / prompt_path,
            live_adapter_prompt(
                case_id,
                task,
                role,
                receipt,
                prompt_overlay=overlay_payload,
            ),
        )
        prompt_outputs.append(prompt_path.as_posix())
        command_plan = [
            "codex",
            "exec",
            "--json",
            "--model",
            DEFAULT_CODEX_EXEC_MODEL,
            "--disable",
            "apps",
            "-c",
            'approval_policy="never"',
            "-c",
            f'model_reasoning_effort="{DEFAULT_CODEX_EXEC_REASONING}"',
            "-c",
            "plugins={}",
            "-c",
            "mcp_servers={}",
            "--sandbox",
            "workspace-write",
            "--cd",
            workspace.as_posix(),
            "--add-dir",
            run_dir.resolve().as_posix(),
            "--output-last-message",
            last_message_path.as_posix(),
            "-",
        ]
        role_launch_plans.append(
            {
                "task_id": task_id,
                "role": role["role"],
                "role_config_id": role_config_id,
                "box_id": task.get("assigned_box_id"),
                "adapter_kind": (
                    "codex_cli_box_live_pending_execution"
                    if execution_approved
                    else "codex_cli_box_dry_run"
                ),
                "launch_status": (
                    "planned_for_live_execution"
                    if execution_approved
                    else "planned_not_launched"
                ),
                "command_plan": command_plan,
                "cwd": workspace.as_posix(),
                "prompt_file": prompt_path.as_posix(),
                "prompt_file_abs": (run_dir / prompt_path).resolve().as_posix(),
                "prompt_overlay": (
                    "live_adapter/prompt_overlay.json" if overlay_payload else None
                ),
                "run_bundle_path": run_dir.resolve().as_posix(),
                "allowed_input_files": task.get("inputs", role.get("input_contract", [])),
                "depends_on": task.get("depends_on", []),
                "output_paths": task.get("expected_outputs", role.get("return_contract", [])),
                "last_message_path": f"last_messages/{task_id}.md",
                "last_message_path_abs": last_message_path.as_posix(),
                "transcript_path": transcript_path.as_posix(),
                "transcript_path_abs": (run_dir / transcript_path).resolve().as_posix(),
                "workspace_output_root": (workspace / "outputs").as_posix(),
                "wall_clock_bound_minutes": receipt["operational_bounds"][
                    "max_wall_clock_minutes"
                ],
                "kill_path": receipt["operational_bounds"]["kill_path"],
                "claim_boundary": {
                    "allowed_claims_if_success": receipt["allowed_claims_if_success"],
                    "blocked_claims": receipt["non_claims_even_if_success"],
                },
                "scorer_policy": receipt.get("scoring", {}),
                "will_execute": execution_approved,
            }
        )
    launch_plan = {
        "schema_version": "codex-dr.live_adapter_launch_plan.v1",
        "run_id": case_id,
        "launch_mode": (
            "live_authorized_pending_execution"
            if execution_approved
            else "dry_run_only"
        ),
        "run_control_receipt": str(run_control),
        "prompt_overlay": (
            {
                "path": "live_adapter/prompt_overlay.json",
                "overlay_id": overlay_payload.get("overlay_id"),
                "candidate_id": overlay_payload.get("candidate_id"),
                "live_surface_changed": overlay_payload.get("live_surface_changed"),
            }
            if overlay_payload
            else None
        ),
        "role_launch_plans": role_launch_plans,
        "non_execution_guarantee": (
            "mesh-live-plan renders command plans and prompt files only; "
            "it never invokes codex exec. A later mesh-execute-live command "
            "may consume this plan only with a separately approved live receipt."
        ),
        "produced_by_event": "evt_0028_live_adapter_dry_run_plan_written",
    }
    write_json(launch_root / "launch_plan.json", launch_plan)
    append_event(
        run_dir,
        event_id="evt_0028_live_adapter_dry_run_plan_written",
        event_type="live_adapter.dry_run_plan_written",
        inputs=[
            "task_graph.json",
            "role_configs.json",
            "terminal_agent_boxes.json",
            *(
                ["live_adapter/prompt_overlay.json"]
                if overlay_payload
                else []
            ),
        ],
        outputs=[
            *prompt_outputs,
            *(
                ["live_adapter/prompt_overlay.json"]
                if overlay_payload
                else []
            ),
            "live_adapter/launch_plan.json",
        ],
        summary="Rendered live Codex CLI mesh launch plans without launching.",
    )
    update_manifest_status(run_dir, "live_adapter_planned")
    refresh_artifact_manifest(run_dir)
    return run_dir


def mesh_executor_preflight(
    case_id: str,
    *,
    run_control: Path,
    runs_dir: Path | str | None = None,
) -> Path:
    run_dir = run_path(case_id, runs_dir)
    if not run_dir.exists():
        raise HarnessError(f"run does not exist: {run_dir}")
    if not is_mesh_run(run_dir):
        raise HarnessError("mesh-executor-preflight requires a provider-off DR mesh run bundle")
    receipt = require_dry_run_control_receipt(run_control, run_id=case_id)
    launch_plan_path = run_dir / "live_adapter" / "launch_plan.json"
    if not launch_plan_path.exists():
        raise HarnessError("live_adapter/launch_plan.json is missing")
    launch_plan = read_json(launch_plan_path)
    role_preflights = validate_no_launch_executor_plan(
        case_id=case_id,
        run_control=run_control,
        receipt=receipt,
        launch_plan=launch_plan,
    )
    preflight = {
        "schema_version": "codex-dr.live_executor_preflight.v1",
        "run_id": case_id,
        "run_control_receipt": str(run_control),
        "launch_plan": "live_adapter/launch_plan.json",
        "execution_status": "prepared_not_launched_dry_run_receipt",
        "will_execute": False,
        "non_execution_guarantee": (
            "mesh-executor-preflight validates launch-plan custody and prepares "
            "execution metadata only; it never invokes codex exec."
        ),
        "workspace_root": (SANDBOX_ROOT / ".agent-workspaces" / case_id).as_posix(),
        "transcript_root": receipt["runner"]["transcript_root"],
        "supervision": {
            "foreground_supervision_required": True,
            "automatic_retry_allowed": False,
            "wall_clock_bound_minutes": receipt["operational_bounds"][
                "max_wall_clock_minutes"
            ],
            "kill_path": receipt["operational_bounds"]["kill_path"],
        },
        "role_preflights": role_preflights,
        "blocked_side_effects": [
            "codex exec launch",
            "provider metadata creation",
            "transcript creation",
            "branch live output creation",
            "benchmark execution",
            "benchmark scoring",
        ],
        "produced_by_event": "evt_0029_live_executor_preflight_written",
    }
    write_json(run_dir / "live_executor" / "execution_preflight.json", preflight)
    append_event(
        run_dir,
        event_id="evt_0029_live_executor_preflight_written",
        event_type="live_executor.preflight_written",
        inputs=[
            "live_adapter/launch_plan.json",
            str(run_control),
        ],
        outputs=["live_executor/execution_preflight.json"],
        summary="Prepared no-launch live mesh executor preflight metadata.",
    )
    update_manifest_status(run_dir, "executor_preflighted")
    refresh_artifact_manifest(run_dir)
    return run_dir


def validate_no_launch_executor_plan(
    *,
    case_id: str,
    run_control: Path,
    receipt: dict[str, Any],
    launch_plan: dict[str, Any],
) -> list[dict[str, Any]]:
    errors = []
    if launch_plan.get("schema_version") != "codex-dr.live_adapter_launch_plan.v1":
        errors.append("launch plan schema_version is invalid")
    if launch_plan.get("run_id") != case_id:
        errors.append(f"launch plan run_id mismatch: {launch_plan.get('run_id')!r}")
    if launch_plan.get("launch_mode") != "dry_run_only":
        errors.append("launch plan must be dry_run_only for preflight")
    recorded_receipt = launch_plan.get("run_control_receipt")
    if not recorded_receipt:
        errors.append("launch plan missing run_control_receipt")
    elif Path(recorded_receipt).resolve() != run_control.resolve():
        errors.append("launch plan run_control_receipt does not match supplied receipt")
    role_plans = launch_plan.get("role_launch_plans", [])
    if not role_plans:
        errors.append("launch plan has no role_launch_plans")
    workspace_root = (SANDBOX_ROOT / ".agent-workspaces" / case_id).resolve()
    role_preflights = []
    for index, role_plan in enumerate(role_plans):
        task_id = role_plan.get("task_id") or f"<role_plan_{index}>"
        cwd = role_plan.get("cwd")
        if not cwd:
            errors.append(f"{task_id}: missing workspace root")
            continue
        workspace_path = Path(cwd).resolve()
        if workspace_path != workspace_root and workspace_root not in workspace_path.parents:
            errors.append(f"{task_id}: workspace root is outside sandbox agent workspaces")
        transcript_path = role_plan.get("transcript_path")
        if not transcript_path:
            errors.append(f"{task_id}: missing transcript path")
        output_paths = role_plan.get("output_paths", [])
        if not output_paths:
            errors.append(f"{task_id}: missing output contracts")
        if any(Path(path).is_absolute() for path in output_paths):
            errors.append(f"{task_id}: output contracts must be relative")
        prompt_file = role_plan.get("prompt_file")
        if not prompt_file:
            errors.append(f"{task_id}: missing prompt file")
        if role_plan.get("will_execute") is not False:
            errors.append(f"{task_id}: role plan must have will_execute false")
        role_preflights.append(
            {
                "task_id": task_id,
                "role": role_plan.get("role"),
                "box_id": role_plan.get("box_id"),
                "workspace_path": cwd,
                "prompt_file": prompt_file,
                "transcript_path": transcript_path,
                "output_paths": output_paths,
                "command_plan": role_plan.get("command_plan", []),
                "execution_status": "prepared_not_launched",
                "supervision": {
                    "will_execute": False,
                    "foreground_supervision_required": True,
                    "wall_clock_bound_minutes": role_plan.get(
                        "wall_clock_bound_minutes"
                    ),
                    "kill_path": role_plan.get("kill_path"),
                    "automatic_retry_allowed": False,
                },
                "claim_boundary": role_plan.get("claim_boundary", {}),
                "scorer_policy": role_plan.get("scorer_policy", {}),
            }
        )
    if not receipt["runner"].get("transcript_root"):
        errors.append("receipt missing transcript root")
    if errors:
        raise HarnessError(f"executor preflight failed: {'; '.join(errors)}")
    return role_preflights


def mesh_execute_live(
    case_id: str,
    *,
    run_control: Path,
    runs_dir: Path | str | None = None,
    codex_runner: Any | None = None,
) -> Path:
    run_dir = run_path(case_id, runs_dir)
    if not run_dir.exists():
        raise HarnessError(f"run does not exist: {run_dir}")
    if not is_mesh_run(run_dir):
        raise HarnessError("mesh-execute-live requires a provider-off DR mesh run bundle")
    receipt = require_live_execution_control_receipt(run_control, run_id=case_id)
    execution_summary_path = run_dir / "live_executor" / "execution_summary.json"
    if execution_summary_path.exists():
        raise HarnessError("live execution already has an execution_summary.json")
    launch_plan_path = run_dir / "live_adapter" / "launch_plan.json"
    if not launch_plan_path.exists():
        raise HarnessError("live_adapter/launch_plan.json is missing")
    launch_plan = read_json(launch_plan_path)
    role_plans = validate_live_executor_launch_plan(
        case_id=case_id,
        run_control=run_control,
        launch_plan=launch_plan,
    )
    execution_batches = live_execution_dependency_batches(role_plans)
    scheduler = live_scheduler_summary(execution_batches)
    transcript_root = run_dir / "transcripts"
    last_message_root = run_dir / "last_messages"
    transcript_root.mkdir(parents=True, exist_ok=True)
    last_message_root.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "live_executor" / "run_control_receipt.json", receipt)
    append_event(
        run_dir,
        event_id="evt_live_0000_run_control_receipt_copied",
        event_type="live_executor.run_control_receipt_copied",
        inputs=[str(run_control)],
        outputs=["live_executor/run_control_receipt.json"],
        summary="Copied approved live run-control receipt into the run bundle.",
    )
    execution_summary = {
        "schema_version": "codex-dr.live_execution_summary.v1",
        "run_id": case_id,
        "run_control_receipt": str(run_control),
        "launch_plan": "live_adapter/launch_plan.json",
        "executor": "codex exec",
        "max_live_attempts": receipt["operational_bounds"]["max_live_attempts"],
        "automatic_retry_allowed": False,
        "scorer_status": receipt.get("scoring", {}).get("scorer_status"),
        "claim_boundary": {
            "allowed_claims_if_success": receipt["allowed_claims_if_success"],
            "non_claims_even_if_success": receipt["non_claims_even_if_success"],
        },
        "scheduler": scheduler,
        "roles": [],
        "dynamic_role_launch_plans": [],
        "recursive_reentry_rounds_used": 0,
    }
    write_json(execution_summary_path, {**execution_summary, "execution_status": "running"})
    append_event(
        run_dir,
        event_id="evt_live_0001_execution_started",
        event_type="live_executor.execution_started",
        inputs=["live_adapter/launch_plan.json", str(run_control)],
        outputs=["live_executor/execution_summary.json"],
        summary="Started bounded live Codex CLI DR mesh execution.",
    )
    runner = codex_runner or run_codex_cli_role
    timeout_seconds = int(receipt["operational_bounds"]["max_wall_clock_minutes"]) * 60
    role_offsets = {
        role_plan["task_id"]: index for index, role_plan in enumerate(role_plans, start=1)
    }
    max_reentry_rounds = int(receipt["operational_bounds"].get("max_reentry_rounds") or 0)
    next_batch_index = 1
    for planned_batch_index, batch in enumerate(execution_batches, start=1):
        if any(role_plan["task_id"] == "task_final_writer" for role_plan in batch) and (
            writer_blocked_by_adequacy_backpressure(run_dir)
        ):
            while execution_summary["recursive_reentry_rounds_used"] < max_reentry_rounds:
                queue = open_adequacy_backpressure_queue(run_dir)
                if not queue:
                    break
                round_number = int(execution_summary["recursive_reentry_rounds_used"]) + 1
                dynamic_plans = build_recursive_reentry_role_plans(
                    run_dir=run_dir,
                    receipt=receipt,
                    base_role_plans=role_plans,
                    queue=queue,
                    round_number=round_number,
                )
                for dynamic_plan in dynamic_plans:
                    role_offsets[dynamic_plan["task_id"]] = len(role_offsets) + 1
                    execution_summary["dynamic_role_launch_plans"].append(dynamic_plan)
                followup_batch = [dynamic_plans[0]]
                append_dynamic_scheduler_group(
                    scheduler,
                    group_id=f"dynamic_reentry_{round_number:03d}_followup",
                    batch=followup_batch,
                )
                followup_records = run_live_execution_batch(
                    run_dir=run_dir,
                    receipt=receipt,
                    batch=followup_batch,
                    batch_index=next_batch_index,
                    role_offsets=role_offsets,
                    timeout_seconds=timeout_seconds,
                    codex_runner=runner,
                )
                execution_summary["roles"].extend(followup_records)
                sync_adequacy_backpressure_queue_after_live_batch(
                    run_dir,
                    batch_index=next_batch_index,
                    task_ids=[record["task_id"] for record in followup_records],
                )
                next_batch_index += 1
                synthesis_batch = [dynamic_plans[1]]
                append_dynamic_scheduler_group(
                    scheduler,
                    group_id=f"dynamic_reentry_{round_number:03d}_synthesis",
                    batch=synthesis_batch,
                )
                synthesis_records = run_live_execution_batch(
                    run_dir=run_dir,
                    receipt=receipt,
                    batch=synthesis_batch,
                    batch_index=next_batch_index,
                    role_offsets=role_offsets,
                    timeout_seconds=timeout_seconds,
                    codex_runner=runner,
                )
                execution_summary["roles"].extend(synthesis_records)
                queue_after_synthesis = sync_adequacy_backpressure_queue_after_live_batch(
                    run_dir,
                    batch_index=next_batch_index,
                    task_ids=[record["task_id"] for record in synthesis_records],
                )
                next_batch_index += 1
                execution_summary["recursive_reentry_rounds_used"] = round_number
                write_json(
                    execution_summary_path,
                    {**execution_summary, "execution_status": "running"},
                )
                branch_id = dynamic_plans[0]["dynamic_recursive_reentry"]["branch_id"]
                refresh_final_writer_for_recursive_reentry(
                    run_dir,
                    final_writer_plan=next(
                        role_plan
                        for role_plan in batch
                        if role_plan["task_id"] == "task_final_writer"
                    ),
                    synthesis_task_id=dynamic_plans[1]["task_id"],
                    branch_id=branch_id,
                )
                if (
                    not queue_after_synthesis
                    or queue_after_synthesis.get("queue_status") != "open"
                    or queue_after_synthesis.get("writer_blocked") is not True
                ):
                    break
            if not writer_blocked_by_adequacy_backpressure(run_dir):
                batch_records = run_live_execution_batch(
                    run_dir=run_dir,
                    receipt=receipt,
                    batch=batch,
                    batch_index=next_batch_index,
                    role_offsets=role_offsets,
                    timeout_seconds=timeout_seconds,
                    codex_runner=runner,
                )
                execution_summary["roles"].extend(batch_records)
                sync_adequacy_backpressure_queue_after_live_batch(
                    run_dir,
                    batch_index=next_batch_index,
                    task_ids=[record["task_id"] for record in batch_records],
                )
                next_batch_index += 1
                continue
            execution_summary["execution_status"] = "blocked_by_adequacy_backpressure"
            execution_summary["role_count"] = len(execution_summary["roles"])
            execution_summary["blocked_batch_index"] = next_batch_index
            execution_summary["blocked_task_ids"] = [
                role_plan["task_id"] for role_plan in batch
            ]
            write_json(execution_summary_path, execution_summary)
            write_context_thread_index(
                run_dir,
                roles=execution_summary["roles"],
                scheduler=scheduler,
            )
            append_event(
                run_dir,
                event_id=f"evt_live_batch_{next_batch_index:04d}_blocked_by_backpressure",
                event_type="live_executor.dependency_batch_blocked",
                inputs=[
                    "backpressure/adequacy_backpressure_queue.json",
                    "backpressure/backpressure_gate_receipt.json",
                    "writer_gate_preflight.json",
                    "live_adapter/launch_plan.json",
                ],
                outputs=["live_executor/execution_summary.json"],
                decision={
                    "batch_index": next_batch_index,
                    "planned_batch_index": planned_batch_index,
                    "task_ids": [role_plan["task_id"] for role_plan in batch],
                    "decision_type": "block_writer_on_open_adequacy_pressure",
                    "rationale": (
                        "The final writer cannot run while unresolved adequacy pressure "
                        "is still queued as open follow-up work."
                    ),
                },
                summary="Blocked final-writer dependency batch on adequacy backpressure.",
            )
            update_manifest_status(run_dir, "live_execution_blocked_by_backpressure")
            refresh_artifact_manifest(run_dir)
            raise HarnessError("task_final_writer blocked by open adequacy backpressure queue")
        batch_records = run_live_execution_batch(
            run_dir=run_dir,
            receipt=receipt,
            batch=batch,
            batch_index=next_batch_index,
            role_offsets=role_offsets,
            timeout_seconds=timeout_seconds,
            codex_runner=runner,
        )
        execution_summary["roles"].extend(batch_records)
        sync_adequacy_backpressure_queue_after_live_batch(
            run_dir,
            batch_index=next_batch_index,
            task_ids=[record["task_id"] for record in batch_records],
        )
        next_batch_index += 1
    execution_summary["execution_status"] = "succeeded"
    execution_summary["role_count"] = len(execution_summary["roles"])
    write_json(execution_summary_path, execution_summary)
    write_context_thread_index(
        run_dir,
        roles=execution_summary["roles"],
        scheduler=scheduler,
    )
    update_live_allowed_claims(run_dir, receipt)
    mark_run_live_executed(run_dir, receipt)
    append_event(
        run_dir,
        event_id="evt_live_9999_execution_completed",
        event_type="live_executor.execution_completed",
        inputs=["live_adapter/launch_plan.json", str(run_control)],
        outputs=["run_manifest.json", "live_executor/execution_summary.json"],
        summary="Completed bounded live Codex CLI DR mesh execution.",
    )
    update_manifest_status(run_dir, "live_execution_completed")
    refresh_artifact_manifest(run_dir)
    return run_dir


def score_run(case_id: str, *, run_control: Path, runs_dir: Path | str | None = None) -> Path:
    run_dir = run_path(case_id, runs_dir)
    if not run_dir.exists():
        raise HarnessError(f"run does not exist: {run_dir}")
    if not is_live_mesh_run(run_dir):
        raise HarnessError("score requires a live DR mesh run bundle")
    pre_checks = [
        check_live_execution_custody(run_dir),
        check_report_claims_in_ledger(run_dir),
        check_allowed_claims(run_dir),
        check_generated_path(run_dir),
    ]
    pre_failures = [check["check_id"] for check in pre_checks if check["status"] == "failed"]
    if pre_failures:
        raise HarnessError(
            "score requires a live run bundle that already passes key custody gates: "
            + ", ".join(pre_failures)
        )
    receipt = require_scoring_control_receipt(run_control, run_id=case_id)
    scoring_root = run_dir / "scoring"
    score_receipt_path = scoring_root / "run_control_receipt.json"
    if score_receipt_path.exists():
        raise HarnessError("score already copied a scoring run-control receipt")
    manifest_path = run_dir / "scorer_manifest.json"
    if not manifest_path.exists():
        raise HarnessError("scorer_manifest.json is missing")
    manifest = read_json(manifest_path)
    if manifest.get("scorer_status") == "executed":
        raise HarnessError("score has already been executed for this run")
    if manifest.get("benchmark_family") != "DRACO":
        raise HarnessError("scorer manifest benchmark_family must be DRACO")
    if manifest.get("scorer_status") != "approved":
        raise HarnessError("scorer manifest must be approved before score runs")
    if manifest.get("execution_allowed") is not True:
        raise HarnessError("scorer manifest must set execution_allowed to true")
    evaluation_output_ref = manifest.get("output_paths", {}).get("evaluation_output")
    if not evaluation_output_ref:
        raise HarnessError("scorer manifest lacks output_paths.evaluation_output")
    evaluation_output_path = resolve_run_relative_path(
        run_dir, evaluation_output_ref, "scorer evaluation output"
    )
    if not evaluation_output_path.exists():
        raise HarnessError(f"evaluation output is missing: {evaluation_output_ref}")
    evaluation = read_json(evaluation_output_path)
    raw_score, normalized_score = validate_draco_evaluation_output(
        run_dir,
        evaluation=evaluation,
        manifest=manifest,
        receipt=receipt,
    )
    write_json(score_receipt_path, receipt)
    append_event(
        run_dir,
        event_id="evt_score_0001_run_control_receipt_copied",
        event_type="score.run_control_receipt_copied",
        inputs=[str(run_control)],
        outputs=["scoring/run_control_receipt.json"],
        summary="Copied approved scoring run-control receipt into the run bundle.",
    )
    manifest["scorer_status"] = "executed"
    manifest["scorer_available"] = True
    manifest["execution_allowed"] = True
    manifest["judge_policy"]["execution_status"] = "executed_with_custody"
    manifest["sealed_reference_policy"]["status"] = "opened_for_approved_scorer"
    manifest["claim_boundary"]["numeric_score_allowed"] = False
    manifest["scorer_execution"] = {
        "receipt_ref": "scoring/run_control_receipt.json",
        "evaluation_output": rel(evaluation_output_path, run_dir),
        "executed_with_custody": True,
        "judge_transcript_refs": evaluation.get("judge_transcript_refs", []),
        "executed_at": FIXTURE_TIMESTAMP,
    }
    manifest["produced_by_event"] = "evt_score_0002_scoring_recorded"
    write_json(manifest_path, manifest)
    write_json(
        run_dir / "benchmark_score.json",
        {
            "schema_version": "codex-dr.benchmark_score.v1",
            "run_id": case_id,
            "mode": "scored_claims_blocked",
            "benchmark_family": "DRACO",
            "case_manifest": "case_manifest.json",
            "scorer_manifest": "scorer_manifest.json",
            "evaluation_output": rel(evaluation_output_path, run_dir),
            "score": normalized_score,
            "raw_score": raw_score,
            "normalized_score": normalized_score,
            "claims_enabled": False,
            "reason": (
                "A scorer-backed DRACO evaluation artifact was ingested with custody, "
                "but public benchmark and parity claims remain blocked pending explicit review."
            ),
            "produced_by_event": "evt_score_0002_scoring_recorded",
        },
    )
    write_json(
        run_dir / "evaluation_ledger.json",
        {
            "schema_version": "codex-dr.benchmark_evaluation_ledger.v1",
            "run_id": case_id,
            "benchmark_family": "DRACO",
            "case_id": evaluation.get("case_id"),
            "scorer_manifest": "scorer_manifest.json",
            "benchmark_score": "benchmark_score.json",
            "result_status": "scored_claims_blocked",
            "score_status": {
                "score": normalized_score,
                "raw_score": raw_score,
                "normalized_score": normalized_score,
                "claims_enabled": False,
                "scorer_custody_present": True,
            },
            "failure_taxonomy": [
                {
                    "failure_class": "claim_review_pending",
                    "severity": "major",
                    "root_cause": (
                        "Scorer custody is present, but public benchmark and parity claims "
                        "remain blocked until explicit claim review opens the gate."
                    ),
                    "blocks": ["DRACO score", "Grep parity", "leaderboard rank"],
                }
            ],
            "improvement_recommendations": [
                {
                    "recommendation_id": "rec_claim_review_open_001",
                    "target_surface": "allowed_claims.json",
                    "action": (
                        "Keep benchmark and parity claims blocked until a reviewer opens the "
                        "claim gate for this scored bundle."
                    ),
                }
            ],
            "allowed_claim_impact": {
                "may_widen_claims": False,
                "claim_gate_status": "blocked",
                "reason": (
                    "Scored artifacts exist with scorer custody, but public score claims remain "
                    "blocked pending explicit claim review."
                ),
                "blocked_claims": [
                    "DRACO score",
                    "Grep parity",
                    "leaderboard rank",
                    "product readiness",
                ],
            },
            "produced_by_event": "evt_score_0002_scoring_recorded",
        },
    )
    allowed_path = run_dir / "allowed_claims.json"
    allowed = read_json(allowed_path)
    scoring_claim = {
        "claim": (
            "A scorer-backed DRACO evaluation artifact was ingested with transcript custody "
            "for this run while benchmark claims remained blocked."
        ),
        "scope": "single_scored_bundle_only",
        "supporting_artifacts": [
            "scoring/run_control_receipt.json",
            "scorer_manifest.json",
            rel(evaluation_output_path, run_dir),
            "evaluation_ledger.json",
        ],
    }
    existing_claims = allowed.get("allowed_claims", [])
    if all(claim.get("claim") != scoring_claim["claim"] for claim in existing_claims):
        existing_claims.append(scoring_claim)
    blocked = set(allowed.get("blocked_claims", []))
    blocked.update(REQUIRED_BLOCKED_CLAIMS)
    allowed["allowed_claims"] = existing_claims
    allowed["blocked_claims"] = sorted(blocked)
    allowed["produced_by_event"] = "evt_score_0002_scoring_recorded"
    write_json(allowed_path, allowed)
    append_event(
        run_dir,
        event_id="evt_score_0002_scoring_recorded",
        event_type="benchmark.score_recorded",
        inputs=[
            "scoring/run_control_receipt.json",
            rel(evaluation_output_path, run_dir),
            "scorer_manifest.json",
        ],
        outputs=[
            rel(evaluation_output_path, run_dir),
            *evaluation.get("judge_transcript_refs", []),
            "scorer_manifest.json",
            "benchmark_score.json",
            "evaluation_ledger.json",
            "allowed_claims.json",
        ],
        summary=(
            "Recorded scorer-backed DRACO evaluation artifacts while keeping public "
            "benchmark claims blocked."
        ),
    )
    manifest_data = read_json(run_dir / "run_manifest.json")
    manifest_data["benchmark_evaluation"] = {
        "receipt_ref": "scoring/run_control_receipt.json",
        "result_status": "scored_claims_blocked",
        "benchmark_score_ref": "benchmark_score.json",
        "evaluation_ledger_ref": "evaluation_ledger.json",
        "claims_enabled": False,
    }
    write_json(run_dir / "run_manifest.json", manifest_data)
    update_manifest_status(run_dir, "scored_claims_blocked")
    refresh_artifact_manifest(run_dir)
    post_score = validate_run(case_id, runs_dir=runs_dir)
    if post_score["status"] != "passed":
        raise HarnessError("score wrote artifacts that failed validation")
    return run_dir


def claim_review(case_id: str, *, runs_dir: Path | str | None = None) -> Path:
    run_dir = run_path(case_id, runs_dir)
    if not run_dir.exists():
        raise HarnessError(f"run does not exist: {run_dir}")
    if not is_mesh_run(run_dir):
        raise HarnessError("claim-review requires a DR mesh run bundle")
    score = read_json(run_dir / "benchmark_score.json")
    ledger = read_json(run_dir / "evaluation_ledger.json")
    manifest = read_json(run_dir / "scorer_manifest.json")
    allowed = read_json(run_dir / "allowed_claims.json")
    blocked_phrase_hits = []
    for claim in allowed.get("allowed_claims", []):
        text = claim.get("claim", "").lower()
        if any(phrase in text for phrase in BLOCKED_ALLOWED_CLAIM_PHRASES):
            blocked_phrase_hits.append(claim.get("claim", "<unknown>"))
    if blocked_phrase_hits:
        raise HarnessError(
            "claim-review refuses pre-widened allowed claims: "
            + "; ".join(blocked_phrase_hits)
        )
    score_present = score.get("score") is not None
    scorer_custody = (
        manifest.get("scorer_status") == "executed"
        and manifest.get("scorer_execution", {}).get("executed_with_custody") is True
    )
    if not score_present:
        decision = "blocked_no_score"
        rationale = "No numeric benchmark score exists for review."
    elif not scorer_custody:
        decision = "blocked_missing_scorer_custody"
        rationale = "A numeric score without scorer custody cannot widen claims."
    else:
        decision = "blocked_single_smoke_review_required"
        rationale = (
            "A scorer-backed artifact exists, but a single smoke run cannot open "
            "DRACO score, Grep parity, leaderboard, or product-readiness claims."
        )
    policy = {
        "policy_id": "codex_dr_claim_review_policy_v1",
        "default_for_smoke_runs": "blocked",
        "minimum_open_requirements": [
            "approved scorer custody",
            "sealed reference policy",
            "reviewed scoring receipt",
            "multi-case benchmark evidence",
            "variance or repeatability note",
            "explicit Principal approval for public claim widening",
        ],
        "blocked_claims": [
            *REQUIRED_BLOCKED_CLAIMS,
        ],
    }
    review = {
        "schema_version": "codex-dr.claim_review.v1",
        "run_id": case_id,
        "review_id": "claim_review_001",
        "policy": policy,
        "inputs": {
            "benchmark_score": "benchmark_score.json",
            "evaluation_ledger": "evaluation_ledger.json",
            "scorer_manifest": "scorer_manifest.json",
            "allowed_claims": "allowed_claims.json",
        },
        "score_status": {
            "score_present": score_present,
            "claims_enabled": score.get("claims_enabled"),
            "scorer_custody_present": scorer_custody,
            "evaluation_result_status": ledger.get("result_status"),
        },
        "decision": decision,
        "may_widen_public_benchmark_claims": False,
        "rationale": rationale,
        "produced_by_event": "evt_claim_review_0001_written",
    }
    write_json(run_dir / "claim_review.json", review)
    blocked = set(allowed.get("blocked_claims", []))
    blocked.update(policy["blocked_claims"])
    review_claim = {
        "claim": (
            "A claim-review gate evaluated this run and kept public benchmark "
            "and parity claims blocked."
        ),
        "scope": "single_run_claim_review_only",
        "supporting_artifacts": [
            "claim_review.json",
            "evaluation_ledger.json",
            "allowed_claims.json",
        ],
    }
    existing_claims = allowed.get("allowed_claims", [])
    if all(claim.get("claim") != review_claim["claim"] for claim in existing_claims):
        existing_claims.append(review_claim)
    allowed["allowed_claims"] = existing_claims
    allowed["blocked_claims"] = sorted(blocked)
    allowed["claim_review"] = {
        "review_ref": "claim_review.json",
        "decision": decision,
        "may_widen_public_benchmark_claims": False,
    }
    allowed["produced_by_event"] = "evt_claim_review_0001_written"
    write_json(run_dir / "allowed_claims.json", allowed)
    append_event(
        run_dir,
        event_id="evt_claim_review_0001_written",
        event_type="claim_review.written",
        inputs=[
            "benchmark_score.json",
            "evaluation_ledger.json",
            "scorer_manifest.json",
            "allowed_claims.json",
        ],
        outputs=["claim_review.json", "allowed_claims.json"],
        summary="Reviewed scored-bundle claim boundary and kept public benchmark claims blocked.",
    )
    refresh_artifact_manifest(run_dir)
    post_review = validate_run(case_id, runs_dir=runs_dir)
    if post_review["status"] != "passed":
        raise HarnessError("claim-review wrote artifacts that failed validation")
    return run_dir


def validate_live_executor_launch_plan(
    *,
    case_id: str,
    run_control: Path,
    launch_plan: dict[str, Any],
) -> list[dict[str, Any]]:
    errors = []
    if launch_plan.get("schema_version") != "codex-dr.live_adapter_launch_plan.v1":
        errors.append("launch plan schema_version is invalid")
    if launch_plan.get("run_id") != case_id:
        errors.append(f"launch plan run_id mismatch: {launch_plan.get('run_id')!r}")
    if launch_plan.get("launch_mode") != "live_authorized_pending_execution":
        errors.append("launch plan must be live_authorized_pending_execution")
    recorded_receipt = launch_plan.get("run_control_receipt")
    if not recorded_receipt:
        errors.append("launch plan missing run_control_receipt")
    elif Path(recorded_receipt).resolve() != run_control.resolve():
        errors.append("launch plan run_control_receipt does not match supplied receipt")
    role_plans = launch_plan.get("role_launch_plans", [])
    if not role_plans:
        errors.append("launch plan has no role_launch_plans")
    workspace_root = (SANDBOX_ROOT / ".agent-workspaces" / case_id).resolve()
    for role_plan in role_plans:
        task_id = role_plan.get("task_id", "<unknown>")
        if not role_plan.get("prompt_file"):
            errors.append(f"{task_id}: missing prompt file")
        if role_plan.get("depends_on") is None:
            errors.append(f"{task_id}: missing dependency annotation")
        cwd = role_plan.get("cwd")
        if not cwd:
            errors.append(f"{task_id}: missing workspace root")
        else:
            workspace_path = Path(cwd).resolve()
            if workspace_path != workspace_root and workspace_root not in workspace_path.parents:
                errors.append(f"{task_id}: workspace root is outside sandbox agent workspaces")
        transcript_path = role_plan.get("transcript_path")
        if not transcript_path:
            errors.append(f"{task_id}: missing transcript path")
        elif Path(transcript_path).is_absolute():
            errors.append(f"{task_id}: transcript path must be relative")
        last_message_path = role_plan.get("last_message_path")
        if not last_message_path:
            errors.append(f"{task_id}: missing last_message_path")
        elif Path(last_message_path).is_absolute():
            errors.append(f"{task_id}: last_message_path must be relative")
        if not role_plan.get("output_paths"):
            errors.append(f"{task_id}: missing output contracts")
        if role_plan.get("adapter_kind") != "codex_cli_box_live_pending_execution":
            errors.append(f"{task_id}: adapter_kind must be live pending execution")
        if role_plan.get("will_execute") is not True:
            errors.append(f"{task_id}: launch plan must have will_execute true")
        command_plan = role_plan.get("command_plan", [])
        if command_plan[:3] != ["codex", "exec", "--json"]:
            errors.append(f"{task_id}: command_plan must start with codex exec --json")
        if "--dangerously-bypass-approvals-and-sandbox" in command_plan:
            errors.append(f"{task_id}: command_plan cannot bypass approvals and sandbox")
        if command_plan[-1:] != ["-"]:
            errors.append(f"{task_id}: command_plan must read the role prompt from stdin")
        scorer_status = role_plan.get("scorer_policy", {}).get("scorer_status")
        if scorer_status and scorer_status != "blocked":
            errors.append(f"{task_id}: scorer policy must remain blocked")
    dependencies_by_task = {
        role_plan.get("task_id", "<unknown>"): role_plan.get("depends_on", [])
        for role_plan in role_plans
    }
    order_errors = dependency_order_problems(
        [role_plan.get("task_id", "<unknown>") for role_plan in role_plans],
        dependencies_by_task,
    )
    errors.extend(order_errors)
    if errors:
        raise HarnessError(f"live executor launch plan failed validation: {'; '.join(errors)}")
    return role_plans


def live_execution_dependency_batches(
    role_plans: list[dict[str, Any]],
) -> list[list[dict[str, Any]]]:
    """Group ready live roles by task dependencies and workspace exclusivity."""
    role_by_task = {role_plan["task_id"]: role_plan for role_plan in role_plans}
    if len(role_by_task) != len(role_plans):
        raise HarnessError("live launch plan contains duplicate task ids")
    pending = [role_plan["task_id"] for role_plan in role_plans]
    completed: set[str] = set()
    batches: list[list[dict[str, Any]]] = []
    while pending:
        ready = [
            role_by_task[task_id]
            for task_id in pending
            if all(
                dependency in completed
                for dependency in role_by_task[task_id].get("depends_on", [])
            )
        ]
        if not ready:
            raise HarnessError(
                "live launch plan contains a dependency cycle or unsatisfied "
                "dependency among: " + ", ".join(pending)
            )
        batch = []
        used_workspaces: set[str] = set()
        for role_plan in ready:
            workspace = str(Path(role_plan["cwd"]).resolve())
            if workspace in used_workspaces:
                continue
            batch.append(role_plan)
            used_workspaces.add(workspace)
        if not batch:
            raise HarnessError("live scheduler could not form a runnable batch")
        batches.append(batch)
        for role_plan in batch:
            task_id = role_plan["task_id"]
            completed.add(task_id)
            pending.remove(task_id)
    return batches


def live_scheduler_summary(
    batches: list[list[dict[str, Any]]],
) -> dict[str, Any]:
    concurrency_groups = []
    for index, batch in enumerate(batches, start=1):
        task_ids = [role_plan["task_id"] for role_plan in batch]
        dependency_waits = {
            role_plan["task_id"]: role_plan.get("depends_on", []) for role_plan in batch
        }
        concurrency_groups.append(
            {
                "group_id": f"group_{index:03d}",
                "task_ids": task_ids,
                "dependency_waits": dependency_waits,
                "max_parallel_roles": len(batch),
                "workspace_conflicts_prevented": False,
            }
        )
    return {
        "schema_version": "codex-dr.live_dependency_scheduler.v1",
        "scheduling_mode": "dependency_aware_parallel",
        "concurrency_group_count": len(concurrency_groups),
        "max_parallel_roles": max((len(batch) for batch in batches), default=0),
        "concurrency_groups": concurrency_groups,
        "invalid_success_blocked": (
            "Sequential role replay is invalid when independent branch tasks "
            "are ready in the same dependency layer."
        ),
    }


def live_codex_command_plan(
    *,
    workspace: Path,
    run_dir: Path,
    last_message_path: Path,
) -> list[str]:
    return [
        "codex",
        "exec",
        "--json",
        "--model",
        DEFAULT_CODEX_EXEC_MODEL,
        "--disable",
        "apps",
        "-c",
        'approval_policy="never"',
        "-c",
        f'model_reasoning_effort="{DEFAULT_CODEX_EXEC_REASONING}"',
        "-c",
        "plugins={}",
        "-c",
        "mcp_servers={}",
        "--sandbox",
        "workspace-write",
        "--cd",
        workspace.as_posix(),
        "--add-dir",
        run_dir.resolve().as_posix(),
        "--output-last-message",
        last_message_path.as_posix(),
        "-",
    ]


def read_live_prompt_overlay_payload(run_dir: Path) -> dict[str, Any] | None:
    overlay_path = run_dir / "live_adapter" / "prompt_overlay.json"
    if not overlay_path.exists():
        return None
    return read_json(overlay_path)


def add_missing_ordered(items: list[str], additions: list[str]) -> list[str]:
    result = list(items)
    for item in additions:
        if item not in result:
            result.append(item)
    return result


def recursive_reentry_objective(queue: dict[str, Any], *, round_number: int) -> str:
    open_items = [
        item
        for item in queue.get("items", [])
        if item.get("writer_blocking") is True and item.get("status") == "open"
    ]
    primary = open_items[0] if open_items else {}
    gap = primary.get("gap") or "Resolve the open adequacy gap."
    recommended = primary.get("recommended_follow_up") or primary.get(
        "follow_up_task"
    ) or primary.get("required_action")
    return (
        f"Run recursive re-entry round {round_number} against the open adequacy "
        f"backpressure queue. Resolve this gap with admitted evidence and a "
        f"pointer-first branch triplet: {gap}"
        + (f"\n\nSuggested follow-up: {recommended}" if recommended else "")
    )


def branch_triplet_paths(branch_id: str) -> list[str]:
    return [
        f"branches/{branch_id}/pointer.md",
        f"branches/{branch_id}/analysis.md",
        f"branches/{branch_id}/evidence.jsonl",
    ]


def mesh_branch_triplet_inputs(*branch_ids: str) -> list[str]:
    return [
        f"branches/{branch_id}/{name}"
        for branch_id in branch_ids
        for name in ["pointer.md", "analysis.md", "evidence.jsonl"]
    ]


def append_dynamic_scheduler_group(
    scheduler: dict[str, Any], *, group_id: str, batch: list[dict[str, Any]]
) -> None:
    groups = scheduler.setdefault("concurrency_groups", [])
    group = {
        "group_id": group_id,
        "task_ids": [role_plan["task_id"] for role_plan in batch],
        "dependency_waits": {
            role_plan["task_id"]: role_plan.get("depends_on", [])
            for role_plan in batch
        },
        "max_parallel_roles": len(batch),
        "workspace_conflicts_prevented": False,
        "dynamic_recursive_reentry": True,
    }
    writer_index = next(
        (
            index
            for index, existing in enumerate(groups)
            if "task_final_writer" in set(existing.get("task_ids", []))
        ),
        len(groups),
    )
    groups.insert(writer_index, group)
    scheduler["concurrency_group_count"] = len(groups)
    scheduler["max_parallel_roles"] = max(
        int(scheduler.get("max_parallel_roles") or 0),
        len(batch),
    )


def build_recursive_reentry_role_plans(
    *,
    run_dir: Path,
    receipt: dict[str, Any],
    base_role_plans: list[dict[str, Any]],
    queue: dict[str, Any],
    round_number: int,
) -> list[dict[str, Any]]:
    role_by_task = {role_plan["task_id"]: role_plan for role_plan in base_role_plans}
    followup_base = role_by_task.get("task_reentry_followup")
    synthesis_base = role_by_task.get("task_reentry_synthesis")
    if not followup_base or not synthesis_base:
        raise HarnessError("recursive re-entry requires the base re-entry role plans")
    suffix = f"{round_number + 1:03d}"
    followup_task_id = f"task_reentry_followup_{suffix}"
    synthesis_task_id = f"task_reentry_synthesis_{suffix}"
    branch_id = f"reentry_followup_{suffix}"
    packet_path = compile_reentry_task_packet_for_run(
        run_dir,
        compiler_invocation_id=f"recursive_reentry_{round_number:03d}",
    )
    packet_relative = rel(packet_path, run_dir)
    packet = read_json(packet_path)
    packet_ready = packet.get("compiler_status") == "ready"
    packet_task = packet.get("task") if isinstance(packet.get("task"), dict) else {}
    packet_inputs = (
        packet_task.get("resolved_input_files", []) if packet_ready else []
    )
    fallback_outputs = [
        "pointer.md",
        "analysis.md",
        "evidence.jsonl",
        "reentry_result.json",
    ]
    reentry_outputs = (
        packet_task.get("required_outputs", []) if packet_ready else fallback_outputs
    )
    integration_paths = (
        reentry_integration_paths_for_packet(packet) if packet_ready else None
    )
    synthesis_outputs = [
        "pointer_read_receipts.jsonl",
        "adequacy_assessments.jsonl",
        "synthesis.md",
        "contradictions.json",
        "report_outline.md",
    ]
    if integration_paths:
        synthesis_outputs.extend(
            [
                integration_paths["reentry_synthesis"],
                integration_paths["adequacy_delta"],
            ]
        )
    reentry_objective = (
        packet_task.get("objective")
        if packet_ready
        else (
            "Read the blocked reentry_task_packet.json and produce fallback blocked "
            "outputs without attempting broad repair."
        )
    )
    prompt_overlay = read_live_prompt_overlay_payload(run_dir)
    followup_task = {
        "task_id": followup_task_id,
        "kind": "reentry_research",
        "branch_id": branch_id,
        "objective": (
            f"Run recursive re-entry round {round_number} from the deterministic "
            f"task packet `{packet_relative}`.\n\n{reentry_objective}"
        ),
        "depends_on": ["task_reentry_synthesis"],
        "inputs": add_missing_ordered(
            [
                packet_relative,
                "backpressure/adequacy_backpressure_queue.json",
                "reviews/review_001.json",
                "synthesis.md",
                "report_outline.md",
                "pointer_read_receipts.jsonl",
                "adequacy_assessments.jsonl",
            ],
            [*packet_inputs, *mesh_branch_triplet_inputs(*MESH_ALL_BRANCH_IDS)],
        ),
        "expected_outputs": reentry_branch_output_paths(branch_id, reentry_outputs),
        "adequacy_checks": ["adequacy_review_reentry", "adequacy_backpressure_queue"],
        "input_file_aliases": {packet_relative: "reentry_task_packet.json"},
    }
    synthesis_task = {
        "task_id": synthesis_task_id,
        "kind": "evaluate_synthesize",
        "objective": (
            "Read the recursive re-entry pointer, admit only selected evidence, "
            "update synthesis and report outline, then close the adequacy queue "
            "or preserve any remaining open gap explicitly."
        ),
        "depends_on": [followup_task_id],
        "inputs": add_missing_ordered(
            [
                "backpressure/adequacy_backpressure_queue.json",
                "reviews/review_001.json",
                "synthesis.md",
                "report_outline.md",
                "pointer_read_receipts.jsonl",
                "adequacy_assessments.jsonl",
                packet_relative,
            ],
            [
                *mesh_branch_triplet_inputs(*MESH_ALL_BRANCH_IDS),
                *reentry_branch_output_paths(branch_id, reentry_outputs),
            ],
        ),
        "expected_outputs": [
            *synthesis_outputs,
        ],
        "adequacy_checks": [
            "adequacy_pointer_first_reads",
            "adequacy_review_reentry",
            "adequacy_backpressure_queue",
        ],
    }
    dynamic_specs = [
        (followup_task, followup_base, "recursive_reentry_followup"),
        (synthesis_task, synthesis_base, "recursive_reentry_synthesis"),
    ]
    dynamic_plans = []
    prompt_outputs = []
    for task, base_plan, workspace_leaf in dynamic_specs:
        task_id = task["task_id"]
        prompt_path = Path("live_adapter") / "prompts" / f"{task_id}.md"
        workspace = (
            SANDBOX_ROOT
            / ".agent-workspaces"
            / run_dir.name
            / f"{workspace_leaf}_{round_number:03d}"
        ).resolve()
        last_message_path = (run_dir / "last_messages" / f"{task_id}.md").resolve()
        transcript_path = Path("transcripts") / f"{task_id}.jsonl"
        role = {
            "role": base_plan.get("role"),
            "input_contract": base_plan.get("allowed_input_files", []),
            "return_contract": base_plan.get("output_paths", []),
        }
        write_text(
            run_dir / prompt_path,
            live_adapter_prompt(
                run_dir.name,
                task,
                role,
                receipt,
                prompt_overlay=prompt_overlay,
            ),
        )
        prompt_outputs.append(prompt_path.as_posix())
        dynamic_plans.append(
            {
                **base_plan,
                "task_id": task_id,
                "role": base_plan.get("role"),
                "role_config_id": base_plan.get("role_config_id"),
                "box_id": base_plan.get("box_id"),
                "adapter_kind": "codex_cli_box_live_pending_execution",
                "launch_status": "planned_for_live_execution_dynamic_recursive_reentry",
                "command_plan": live_codex_command_plan(
                    workspace=workspace,
                    run_dir=run_dir,
                    last_message_path=last_message_path,
                ),
                "cwd": workspace.as_posix(),
                "prompt_file": prompt_path.as_posix(),
                "prompt_file_abs": (run_dir / prompt_path).resolve().as_posix(),
                "prompt_overlay": (
                    "live_adapter/prompt_overlay.json" if prompt_overlay else None
                ),
                "run_bundle_path": run_dir.resolve().as_posix(),
                "allowed_input_files": task["inputs"],
                "input_file_aliases": task.get("input_file_aliases", {}),
                "depends_on": task["depends_on"],
                "output_paths": task["expected_outputs"],
                "last_message_path": f"last_messages/{task_id}.md",
                "last_message_path_abs": last_message_path.as_posix(),
                "transcript_path": transcript_path.as_posix(),
                "transcript_path_abs": (run_dir / transcript_path).resolve().as_posix(),
                "workspace_output_root": (workspace / "outputs").as_posix(),
                "wall_clock_bound_minutes": receipt["operational_bounds"][
                    "max_wall_clock_minutes"
                ],
                "kill_path": receipt["operational_bounds"]["kill_path"],
                "dynamic_recursive_reentry": {
                    "round_number": round_number,
                    "source_queue": "backpressure/adequacy_backpressure_queue.json",
                    "branch_id": branch_id,
                    "task_packet": packet_relative,
                    "task_packet_status": packet.get("compiler_status"),
                    "source_gap_id": packet.get("source_gap_id"),
                },
                "claim_boundary": {
                    "allowed_claims_if_success": receipt["allowed_claims_if_success"],
                    "blocked_claims": receipt["non_claims_even_if_success"],
                },
                "scorer_policy": receipt.get("scoring", {}),
                "will_execute": True,
            }
        )
    append_event(
        run_dir,
        event_id=f"evt_live_recursive_reentry_{round_number:04d}_planned",
        event_type="live_executor.recursive_reentry_planned",
        inputs=[
            "backpressure/adequacy_backpressure_queue.json",
            packet_relative,
            "live_adapter/launch_plan.json",
        ],
        outputs=prompt_outputs,
        decision={
            "decision_type": "spawn_recursive_reentry",
            "round_number": round_number,
            "task_ids": [plan["task_id"] for plan in dynamic_plans],
            "task_packet": packet_relative,
            "task_packet_status": packet.get("compiler_status"),
            "rationale": (
                "An open adequacy queue is writer-blocking, and the run-control "
                "receipt permits one bounded recursive re-entry round from a "
                "deterministic re-entry task packet."
            ),
        },
        summary="Planned bounded recursive re-entry roles from the open adequacy queue.",
    )
    return dynamic_plans


def refresh_final_writer_for_recursive_reentry(
    run_dir: Path,
    *,
    final_writer_plan: dict[str, Any],
    synthesis_task_id: str,
    branch_id: str,
) -> None:
    final_writer_plan["depends_on"] = [synthesis_task_id]
    final_writer_plan["allowed_input_files"] = add_missing_ordered(
        final_writer_plan.get("allowed_input_files", []),
        [
            "backpressure/adequacy_backpressure_queue.json",
            "backpressure/backpressure_gate_receipt.json",
            "writer_gate_preflight.json",
            "adequacy_assessments.jsonl",
            "pointer_read_receipts.jsonl",
            *branch_triplet_paths(branch_id),
        ],
    )
    prompt_path = run_dir / final_writer_plan["prompt_file"]
    prompt_text = prompt_path.read_text(encoding="utf-8")
    update_marker = "## Recursive Re-Entry Executor Update"
    if update_marker not in prompt_text:
        prompt_text += f"""

{update_marker}
The live executor ran `{synthesis_task_id}` from an open adequacy backpressure
queue before allowing this writer role. Read the current `synthesis.md`,
`report_outline.md`, `adequacy_assessments.jsonl`, and
`writer_gate_preflight.json`, `backpressure/backpressure_gate_receipt.json`, and
`backpressure/adequacy_backpressure_queue.json` before writing. Include
unresolveds as unresolveds, and do not treat a still-open queue as closure.
"""
        write_text(prompt_path, prompt_text)
    append_event(
        run_dir,
        event_id=f"evt_live_{synthesis_task_id}_writer_prompt_updated",
        event_type="live_adapter.writer_prompt_updated_for_recursive_reentry",
        inputs=[
            final_writer_plan["prompt_file"],
            "backpressure/adequacy_backpressure_queue.json",
            "backpressure/backpressure_gate_receipt.json",
            "writer_gate_preflight.json",
        ],
        outputs=[final_writer_plan["prompt_file"]],
        decision={
            "decision_type": "refresh_writer_after_recursive_reentry",
            "writer_task_id": final_writer_plan["task_id"],
            "depends_on": synthesis_task_id,
            "rationale": (
                "The writer prompt and copied-input list must reflect the recursive "
                "re-entry synthesis that resolved or preserved the adequacy queue."
            ),
        },
        summary="Updated final writer prompt for recursive re-entry state.",
    )


def extract_transcript_thread_ids(transcript_path: Path) -> list[str]:
    thread_ids: list[str] = []
    if not transcript_path.exists():
        return thread_ids
    for line in transcript_path.read_text(encoding="utf-8").splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("type") == "thread.started" and payload.get("thread_id"):
            thread_ids.append(str(payload["thread_id"]))
    return thread_ids


def run_relative_file_size(run_dir: Path, relative: str) -> int:
    path = run_dir / relative
    if not path.exists() or not path.is_file():
        return 0
    return path.stat().st_size


def write_context_thread_index(
    run_dir: Path,
    *,
    roles: list[dict[str, Any]],
    scheduler: dict[str, Any],
) -> None:
    group_by_task: dict[str, str] = {}
    for group in scheduler.get("concurrency_groups", []):
        for task_id in group.get("task_ids", []):
            group_by_task[task_id] = group.get("group_id", "<unknown>")
    entries = []
    total_input_bytes = 0
    for role in roles:
        context = role.get("context_admission", {})
        input_bytes = int(context.get("total_input_bytes") or 0)
        total_input_bytes += input_bytes
        entries.append(
            {
                "task_id": role.get("task_id"),
                "role": role.get("role"),
                "box_id": role.get("box_id"),
                "thread_ids": role.get("thread_ids", []),
                "transcript_path": role.get("transcript_path"),
                "last_message_path": role.get("last_message_path"),
                "workspace_path": role.get("workspace_path"),
                "concurrency_group_id": group_by_task.get(role.get("task_id", "")),
                "context_admission": context,
                "output_contract": role.get("output_contract", []),
            }
        )
    write_json(
        run_dir / "live_executor" / "context_thread_index.json",
        {
            "schema_version": "codex-dr.context_thread_index.v1",
            "run_id": run_dir.name,
            "scheduler_ref": "live_executor/execution_summary.json#scheduler",
            "role_count": len(entries),
            "total_input_context_bytes": total_input_bytes,
            "max_role_input_context_bytes": max(
                (
                    int(entry["context_admission"].get("total_input_bytes") or 0)
                    for entry in entries
                ),
                default=0,
            ),
            "context_policy": (
                "Role boxes receive only their declared allowed_input_files plus "
                "the rendered live prompt overlay."
            ),
            "roles": entries,
            "produced_by_event": "evt_live_9997_context_thread_index_written",
        },
    )
    append_event(
        run_dir,
        event_id="evt_live_9997_context_thread_index_written",
        event_type="live_executor.context_thread_index_written",
        inputs=[
            "live_executor/execution_summary.json",
            *[role.get("transcript_path", "") for role in roles],
        ],
        outputs=["live_executor/context_thread_index.json"],
        summary="Wrote live Codex role context and thread index.",
    )


def run_live_execution_batch(
    *,
    run_dir: Path,
    receipt: dict[str, Any],
    batch: list[dict[str, Any]],
    batch_index: int,
    role_offsets: dict[str, int],
    timeout_seconds: int,
    codex_runner: Any,
) -> list[dict[str, Any]]:
    append_event(
        run_dir,
        event_id=f"evt_live_batch_{batch_index:04d}_started",
        event_type="live_executor.dependency_batch_started",
        inputs=["live_adapter/launch_plan.json"],
        outputs=[],
        decision={
            "batch_index": batch_index,
            "task_ids": [role_plan["task_id"] for role_plan in batch],
            "scheduling_mode": "dependency_aware_parallel",
            "rationale": (
                "Run every dependency-ready role in this batch concurrently unless "
                "workspace exclusivity or explicit dependencies require waiting."
            ),
        },
        summary=f"Started live dependency batch {batch_index}.",
    )
    records: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=len(batch)) as executor:
        futures = {
            executor.submit(
                execute_live_role,
                run_dir=run_dir,
                receipt=receipt,
                role_plan=role_plan,
                role_index=role_offsets[role_plan["task_id"]],
                timeout_seconds=timeout_seconds,
                codex_runner=codex_runner,
            ): role_plan
            for role_plan in batch
        }
        for future in as_completed(futures):
            records.append(future.result())
    records.sort(key=lambda record: role_offsets[record["task_id"]])
    append_event(
        run_dir,
        event_id=f"evt_live_batch_{batch_index:04d}_completed",
        event_type="live_executor.dependency_batch_completed",
        inputs=[record["event_id"] for record in records],
        outputs=[],
        decision={
            "batch_index": batch_index,
            "task_ids": [record["task_id"] for record in records],
            "scheduling_mode": "dependency_aware_parallel",
            "rationale": "All dependency-ready roles in this batch completed.",
        },
        summary=f"Completed live dependency batch {batch_index}.",
    )
    return records


def execute_live_role(
    *,
    run_dir: Path,
    receipt: dict[str, Any],
    role_plan: dict[str, Any],
    role_index: int,
    timeout_seconds: int,
    codex_runner: Any,
) -> dict[str, Any]:
    task_id = role_plan["task_id"]
    started_monotonic = time.monotonic()
    workspace_path = Path(role_plan["cwd"])
    workspace_root = SANDBOX_ROOT / ".agent-workspaces" / run_dir.name
    resolved_workspace_root = workspace_root.resolve()
    resolved_workspace_path = workspace_path.resolve()
    if (
        resolved_workspace_root != resolved_workspace_path
        and resolved_workspace_root not in resolved_workspace_path.parents
    ):
        raise HarnessError(f"{task_id}: workspace root is outside sandbox agent workspaces")
    if workspace_path.exists():
        shutil.rmtree(workspace_path)
    workspace_path.mkdir(parents=True, exist_ok=True)
    copied_inputs = copy_live_role_inputs(run_dir, workspace_path, role_plan)
    copied_input_hashes = workspace_copied_input_hashes(
        workspace_path=workspace_path,
        copied_inputs=copied_inputs,
    )
    prompt_file = run_dir / role_plan["prompt_file"]
    if not prompt_file.exists():
        raise HarnessError(f"{task_id}: prompt file is missing: {prompt_file}")
    live_prompt = live_execution_prompt_overlay(
        prompt_file.read_text(encoding="utf-8"),
        receipt=receipt,
        role_plan=role_plan,
        workspace_path=workspace_path,
    )
    workspace_prompt = workspace_path / "LIVE_PROMPT.md"
    write_text(workspace_prompt, live_prompt)
    transcript_path = run_dir / role_plan["transcript_path"]
    last_message_path = run_dir / "last_messages" / f"{task_id}.md"
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    last_message_path.parent.mkdir(parents=True, exist_ok=True)
    result = codex_runner(
        role_plan=role_plan,
        prompt=live_prompt,
        workspace_path=workspace_path,
        transcript_path=transcript_path,
        last_message_path=last_message_path,
        timeout_seconds=timeout_seconds,
    )
    if result.get("returncode") != 0:
        write_json(
            run_dir / "live_executor" / f"{task_id}_failure.json",
            {
                "schema_version": "codex-dr.live_role_failure.v1",
                "run_id": run_dir.name,
                "task_id": task_id,
                "returncode": result.get("returncode"),
                "transcript_path": rel(transcript_path, run_dir),
                "last_message_path": rel(last_message_path, run_dir),
                "automatic_retry_allowed": False,
            },
        )
        raise HarnessError(
            f"{task_id}: codex exec failed with return code {result.get('returncode')}"
        )
    if not transcript_path.exists():
        raise HarnessError(f"{task_id}: transcript capture was not written")
    if not last_message_path.exists():
        raise HarnessError(f"{task_id}: output-last-message capture was not written")
    validate_live_role_forbidden_outputs(
        workspace_path,
        role_plan,
        copied_input_hashes=copied_input_hashes,
    )
    thread_ids = extract_transcript_thread_ids(transcript_path)
    copied_input_sizes = {
        relative: run_relative_file_size(run_dir, relative) for relative in copied_inputs
    }
    copied_outputs = copy_live_role_outputs(run_dir, workspace_path, role_plan)
    completed_monotonic = time.monotonic()
    event_id = f"evt_live_{role_index:04d}_{task_id}_completed"
    control_outputs = LIVE_CONTROL_OUTPUTS.get(task_id, set())
    canonical_outputs = [
        relative
        for relative in role_plan.get("output_paths", [])
        if relative not in control_outputs
    ]
    event_outputs = [
        *copied_outputs,
        *canonical_outputs,
        rel(transcript_path, run_dir),
        rel(last_message_path, run_dir),
    ]
    append_event(
        run_dir,
        event_id=event_id,
        event_type="live_executor.role_completed",
        inputs=[
            *copied_inputs,
            role_plan["prompt_file"],
            str(Path("LIVE_PROMPT.md")),
        ],
        outputs=event_outputs,
        decision={
            "task_id": task_id,
            "role": role_plan.get("role"),
            "box_id": role_plan.get("box_id"),
            "returncode": result.get("returncode"),
            "automatic_retry_allowed": False,
            "scorer_status": receipt.get("scoring", {}).get("scorer_status"),
            "rationale": (
                "Execute exactly one approved Codex CLI role from the DR mesh "
                "launch plan and copy only declared outputs back into the run bundle."
            ),
        },
        summary=f"Completed live Codex CLI role {task_id}.",
    )
    return {
        "task_id": task_id,
        "role": role_plan.get("role"),
        "box_id": role_plan.get("box_id"),
        "workspace_path": workspace_path.as_posix(),
        "prompt_file": role_plan["prompt_file"],
        "transcript_path": rel(transcript_path, run_dir),
        "last_message_path": rel(last_message_path, run_dir),
        "copied_inputs": copied_inputs,
        "copied_outputs": copied_outputs,
        "thread_ids": thread_ids,
        "context_admission": {
            "allowed_input_files": role_plan.get("allowed_input_files", []),
            "copied_input_files": copied_inputs,
            "copied_input_bytes": copied_input_sizes,
            "total_input_bytes": sum(copied_input_sizes.values()),
            "prompt_file": role_plan["prompt_file"],
            "prompt_bytes": len(live_prompt.encode("utf-8")),
            "live_prompt_copy": "LIVE_PROMPT.md",
        },
        "output_contract": role_plan.get("output_paths", []),
        "returncode": result.get("returncode"),
        "started_monotonic": started_monotonic,
        "completed_monotonic": completed_monotonic,
        "duration_seconds": completed_monotonic - started_monotonic,
        "event_id": event_id,
    }


def workspace_copied_input_hashes(
    *,
    workspace_path: Path,
    copied_inputs: list[str],
) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for copied_input in copied_inputs:
        destination_relative = copied_input.split("=>", 1)[-1]
        if not safe_relative_path(destination_relative):
            continue
        destination = workspace_path / destination_relative
        if destination.exists() and destination.is_file():
            fingerprints[destination_relative] = sha256_file(destination)
    return fingerprints


def validate_live_role_forbidden_outputs(
    workspace_path: Path,
    role_plan: dict[str, Any],
    *,
    copied_input_hashes: dict[str, str] | None = None,
) -> None:
    task_id = str(role_plan.get("task_id") or "")
    if task_id == "task_review":
        forbidden_outputs = REVIEWER_FORBIDDEN_OUTPUTS
        role_label = "task_review"
    elif task_id == "task_reentry_followup" or task_id.startswith("task_reentry_followup_"):
        forbidden_outputs = REENTRY_FORBIDDEN_OUTPUTS
        role_label = task_id
    else:
        return
    input_hashes = copied_input_hashes or {}
    produced = []
    modified = []
    for relative in sorted(forbidden_outputs):
        candidate = workspace_path / relative
        if not candidate.exists():
            continue
        original_hash = input_hashes.get(relative)
        if original_hash is None:
            produced.append(relative)
        elif candidate.is_file() and sha256_file(candidate) != original_hash:
            modified.append(relative)
    if produced:
        raise HarnessError(
            f"{role_label} produced forbidden output(s): " + ", ".join(produced)
        )
    if modified:
        raise HarnessError(
            f"{role_label} modified forbidden input(s): " + ", ".join(modified)
        )


def copy_live_role_inputs(
    run_dir: Path, workspace_path: Path, role_plan: dict[str, Any]
) -> list[str]:
    copied = []
    for relative in role_plan.get("allowed_input_files", []):
        if not safe_relative_path(relative):
            raise HarnessError(f"{role_plan['task_id']}: unsafe input path {relative}")
        source = run_dir / relative
        if not source.exists() or not source.is_file():
            continue
        destination = workspace_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(relative)
    aliases = role_plan.get("input_file_aliases", {})
    if isinstance(aliases, dict):
        for source_relative, destination_relative in aliases.items():
            if not safe_relative_path(source_relative) or not safe_relative_path(
                destination_relative
            ):
                raise HarnessError(
                    f"{role_plan['task_id']}: unsafe input alias "
                    f"{source_relative!r} -> {destination_relative!r}"
                )
            source = run_dir / source_relative
            if not source.exists() or not source.is_file():
                continue
            destination = workspace_path / destination_relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied.append(f"{source_relative}=>{destination_relative}")
    return copied


def copy_live_role_outputs(
    run_dir: Path, workspace_path: Path, role_plan: dict[str, Any]
) -> list[str]:
    copied = []
    missing = []
    control_outputs = LIVE_CONTROL_OUTPUTS.get(role_plan["task_id"], set())
    for relative in role_plan.get("output_paths", []):
        if Path(relative).is_absolute():
            raise HarnessError(f"{role_plan['task_id']}: output path must be relative")
        source = workspace_path / relative
        if not source.exists() or not source.is_file():
            missing.append(relative)
            continue
        destination = (
            run_dir
            / "live_executor"
            / "role_outputs"
            / role_plan["task_id"]
            / relative
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if relative not in control_outputs:
            canonical_destination = run_dir / relative
            canonical_destination.parent.mkdir(parents=True, exist_ok=True)
            if (
                relative in LIVE_CUMULATIVE_JSONL_OUTPUTS
                and canonical_destination.exists()
            ):
                append_jsonl_file(source, canonical_destination)
            else:
                shutil.copy2(source, canonical_destination)
        copied.append(rel(destination, run_dir))
    if missing:
        raise HarnessError(
            f"{role_plan['task_id']}: live role did not produce required outputs: "
            + ", ".join(missing)
        )
    return copied


def append_jsonl_file(source: Path, destination: Path) -> None:
    source_text = source.read_text(encoding="utf-8")
    if not source_text.strip():
        return
    with destination.open("a+", encoding="utf-8") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() > 0:
            handle.seek(handle.tell() - 1)
            if handle.read(1) != "\n":
                handle.write("\n")
            handle.seek(0, os.SEEK_END)
        handle.write(source_text)
        if not source_text.endswith("\n"):
            handle.write("\n")


def live_execution_prompt_overlay(
    prompt: str,
    *,
    receipt: dict[str, Any],
    role_plan: dict[str, Any],
    workspace_path: Path,
) -> str:
    output_paths = json.dumps(role_plan.get("output_paths", []), indent=2)
    input_paths = json.dumps(role_plan.get("allowed_input_files", []), indent=2)
    return f"""{prompt}

## Live Execution Overlay
The Principal has approved this specific live smoke run through receipt
`{receipt["receipt_id"]}`. The dry-run prompt above is now being executed by
the bounded live executor, once, for this role only.

Current workspace:
`{workspace_path.as_posix()}`

Mounted run bundle:
`{role_plan.get("run_bundle_path", "")}`

Input files copied into this workspace:
{input_paths}

You must write the required outputs as files relative to the current workspace:
{output_paths}

Copied input files are local convenience copies. The mounted run bundle is
available for selective reads of the same declared input paths if a file is not
present in the current workspace. For pointer-first synthesis, read each
`pointer.md` before opening that branch's `analysis.md` or `evidence.jsonl`;
then record the selected analysis paths in `pointer_read_receipts.jsonl`.

Do not write outside the current workspace. Do not read env files, secrets,
customer data, raw private benchmark corpora, paid benchmark corpora, or root
environment files. Do not claim Grep parity, a benchmark score, leaderboard rank,
product readiness, or benchmark execution. If evidence is thin or a source is
unavailable, record the gap in the output files.
"""


def run_codex_cli_role(
    *,
    role_plan: dict[str, Any],
    prompt: str,
    workspace_path: Path,
    transcript_path: Path,
    last_message_path: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    command = role_plan.get("command_plan") or [
        "codex",
        "exec",
        "--json",
        "--model",
        DEFAULT_CODEX_EXEC_MODEL,
        "--disable",
        "apps",
        "-c",
        'approval_policy="never"',
        "-c",
        f'model_reasoning_effort="{DEFAULT_CODEX_EXEC_REASONING}"',
        "-c",
        "plugins={}",
        "-c",
        "mcp_servers={}",
        "--sandbox",
        "workspace-write",
        "--cd",
        workspace_path.as_posix(),
        "--add-dir",
        SANDBOX_ROOT.as_posix(),
        "--output-last-message",
        last_message_path.as_posix(),
        "-",
    ]
    if shutil.which(command[0]) is None:
        raise HarnessError("codex CLI is unavailable on PATH")
    header = {
        "schema_version": "codex-dr.live_transcript_header.v1",
        "task_id": role_plan.get("task_id"),
        "command": command,
        "cwd": workspace_path.as_posix(),
        "transcript_path": transcript_path.as_posix(),
        "last_message_path": last_message_path.as_posix(),
    }
    try:
        completed = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            cwd=workspace_path,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""
        transcript_path.write_text(
            json.dumps(header, sort_keys=True) + "\n" + stdout + stderr,
            encoding="utf-8",
        )
        return {"returncode": 124, "command": command}
    transcript_path.write_text(
        json.dumps(header, sort_keys=True)
        + "\n"
        + completed.stdout
        + completed.stderr,
        encoding="utf-8",
    )
    return {"returncode": completed.returncode, "command": command}


def probe_codex_model(
    model: str,
    *,
    output_dir: Path | str | None = None,
    timeout_seconds: int = 60,
    runner: Any | None = None,
) -> dict[str, Any]:
    validate_model_name(model)
    if timeout_seconds < 1:
        raise HarnessError("timeout_seconds must be greater than zero")
    probe_root = Path(output_dir or (SANDBOX_ROOT / "tmp" / "model-probes"))
    probe_root.mkdir(parents=True, exist_ok=True)
    safe_model = safe_model_filename(model)
    workspace_path = (probe_root / f"{safe_model}_workspace").resolve()
    transcript_path = (probe_root / f"{safe_model}_probe.jsonl").resolve()
    last_message_path = (probe_root / f"{safe_model}_last_message.md").resolve()
    receipt_path = (probe_root / f"{safe_model}_model_probe_receipt.json").resolve()
    if workspace_path.exists():
        shutil.rmtree(workspace_path)
    workspace_path.mkdir(parents=True, exist_ok=True)
    for path in [transcript_path, last_message_path]:
        if path.exists():
            path.unlink()
    command = [
        "codex",
        "exec",
        "--json",
        "--model",
        model,
        "--disable",
        "apps",
        "-c",
        'approval_policy="never"',
        "-c",
        f'model_reasoning_effort="{DEFAULT_CODEX_EXEC_REASONING}"',
        "-c",
        "plugins={}",
        "-c",
        "mcp_servers={}",
        "--sandbox",
        "workspace-write",
        "--cd",
        workspace_path.as_posix(),
        "--output-last-message",
        last_message_path.as_posix(),
        "-",
    ]
    probe_runner = runner or run_codex_model_probe_command
    result = probe_runner(
        command=command,
        prompt=MODEL_PROBE_PROMPT,
        workspace_path=workspace_path,
        transcript_path=transcript_path,
        last_message_path=last_message_path,
        timeout_seconds=timeout_seconds,
    )
    if "last_message" in result:
        write_text(last_message_path, str(result.get("last_message", "")))
    stdout = str(result.get("stdout", ""))
    stderr = str(result.get("stderr", ""))
    header = {
        "schema_version": "codex-dr.model_probe_transcript_header.v1",
        "model": model,
        "command": command,
        "cwd": workspace_path.as_posix(),
        "transcript_path": transcript_path.as_posix(),
        "last_message_path": last_message_path.as_posix(),
    }
    write_text(
        transcript_path,
        json.dumps(header, sort_keys=True) + "\n" + stdout + stderr,
    )
    last_message = (
        last_message_path.read_text(encoding="utf-8") if last_message_path.exists() else ""
    )
    returncode = int(result.get("returncode", 1))
    available = (
        returncode == 0
        and last_message.strip() == MODEL_PROBE_EXPECTED_MESSAGE
    )
    error_class = classify_model_probe_error(
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        last_message=last_message,
    )
    receipt = {
        "schema_version": "codex-dr.model_probe_receipt.v1",
        "model": model,
        "reasoning_effort": DEFAULT_CODEX_EXEC_REASONING,
        "status": "available" if available else "unavailable",
        "returncode": returncode,
        "observed_error_class": None if available else error_class,
        "current_live_default": DEFAULT_CODEX_EXEC_MODEL,
        "may_promote_live_default": available,
        "recommendation": (
            "eligible_for_manual_default_promotion"
            if available
            else f"keep {DEFAULT_CODEX_EXEC_MODEL} as live default"
        ),
        "probe_prompt": MODEL_PROBE_PROMPT,
        "expected_last_message": MODEL_PROBE_EXPECTED_MESSAGE,
        "last_message_observed": last_message.strip(),
        "command": command,
        "workspace_path": workspace_path.as_posix(),
        "transcript_path": transcript_path.as_posix(),
        "last_message_path": last_message_path.as_posix(),
        "receipt_path": receipt_path.as_posix(),
        "stdout_excerpt": stdout[-1000:],
        "stderr_excerpt": stderr[-1000:],
        "claim_boundary": {
            "allowed_claims_if_available": [
                f"Codex CLI accepted model {model!r} for a one-line foreground probe."
            ],
            "blocked_claims": [
                "DR mesh quality improvement",
                "Grep parity",
                "DRACO score",
                "product readiness",
            ],
        },
        "produced_at": FIXTURE_TIMESTAMP,
    }
    write_json(receipt_path, receipt)
    return receipt


def run_codex_model_probe_command(
    *,
    command: list[str],
    prompt: str,
    workspace_path: Path,
    transcript_path: Path,
    last_message_path: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    if shutil.which(command[0]) is None:
        raise HarnessError("codex CLI is unavailable on PATH")
    try:
        completed = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            cwd=workspace_path,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        return {
            "returncode": 124,
            "stdout": error.stdout or "",
            "stderr": error.stderr or "",
        }
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def classify_model_probe_error(
    *,
    returncode: int,
    stdout: str,
    stderr: str,
    last_message: str,
) -> str:
    combined = f"{stdout}\n{stderr}\n{last_message}".lower()
    if returncode == 124:
        return "timeout"
    if "does not exist or you do not have access" in combined:
        return "model_unavailable_or_no_access"
    if "not logged in" in combined or "login" in combined and "required" in combined:
        return "codex_login_required"
    if returncode == 0:
        return "unexpected_last_message"
    return "codex_exec_failed"


def mark_run_live_executed(run_dir: Path, receipt: dict[str, Any]) -> None:
    manifest_path = run_dir / "run_manifest.json"
    manifest = read_json(manifest_path)
    manifest["mode"] = "live_dr_mesh_smoke"
    manifest["provider_calls_allowed"] = True
    manifest["benchmark_execution_allowed"] = False
    manifest["live_execution"] = {
        "receipt_id": receipt["receipt_id"],
        "receipt_ref": "live_executor/run_control_receipt.json",
        "executor": "mesh-execute-live",
        "max_cases": receipt["operational_bounds"]["max_cases"],
        "max_live_attempts": receipt["operational_bounds"]["max_live_attempts"],
        "automatic_retry_allowed": False,
        "scorer_status": receipt.get("scoring", {}).get("scorer_status"),
        "claim_boundary": {
            "allowed_claims_if_success": receipt["allowed_claims_if_success"],
            "non_claims_even_if_success": receipt["non_claims_even_if_success"],
        },
    }
    write_json(manifest_path, manifest)


def update_live_allowed_claims(run_dir: Path, receipt: dict[str, Any]) -> None:
    allowed_path = run_dir / "allowed_claims.json"
    allowed = read_json(allowed_path)
    blocked = set(allowed.get("blocked_claims", []))
    blocked.update([*REQUIRED_BLOCKED_CLAIMS, "benchmark execution"])
    live_claim = {
        "claim": (
            "A bounded live Codex CLI DR mesh smoke executed per-role boxes "
            "once with transcript custody for this run."
        ),
        "scope": "single_authorized_smoke_run_only",
        "supporting_artifacts": [
            "live_executor/run_control_receipt.json",
            "live_executor/execution_summary.json",
        ],
    }
    existing_claims = allowed.get("allowed_claims", [])
    if all(claim.get("claim") != live_claim["claim"] for claim in existing_claims):
        existing_claims.append(live_claim)
    allowed["allowed_claims"] = existing_claims
    allowed["blocked_claims"] = sorted(blocked)
    allowed["produced_by_event"] = "evt_live_9998_allowed_claims_written"
    write_json(allowed_path, allowed)
    append_event(
        run_dir,
        event_id="evt_live_9998_allowed_claims_written",
        event_type="allowed_claims.written",
        inputs=[
            "allowed_claims.json",
            "live_executor/run_control_receipt.json",
            "live_executor/execution_summary.json",
        ],
        outputs=["allowed_claims.json"],
        summary="Updated allowed claims for the bounded live Codex CLI smoke.",
    )


def live_adapter_prompt(
    case_id: str,
    task: dict[str, Any],
    role: dict[str, Any],
    receipt: dict[str, Any],
    *,
    prompt_overlay: dict[str, Any] | None = None,
) -> str:
    expected_outputs = task.get("expected_outputs", role.get("return_contract", []))
    if not expected_outputs:
        raise HarnessError(f"task {task['task_id']} lacks output contract")
    non_claims = receipt.get("non_claims_even_if_success")
    if not non_claims:
        raise HarnessError("run-control receipt lacks non-claims for prompt generation")
    profile = role_prompt_profile(task, role)
    adequacy_checks = task.get("adequacy_checks", [])
    allowed_inputs = task.get("inputs", role.get("input_contract", []))
    role_instructions = "\n".join(
        f"- {instruction}" for instruction in profile["instructions"]
    )
    output_schema = live_role_output_schema_notes(task, role)
    overlay_section = prompt_overlay_section_for_task(
        prompt_overlay, task_id=task["task_id"]
    )
    return f"""# Codex-DR Live Adapter Prompt

Run id: `{case_id}`
Task id: `{task["task_id"]}`
Role: `{role["role"]}`
Prompt pack: `{LIVE_ROLE_PROMPT_PACK_REF}`

## DR Mesh Charter
- Governing charter: `sandbox/codex-dr/harness-specs/dr_mesh_parity_charter.md`.
- Preserve the Grep-shaped loop: planner, task graph, scoped branches,
  pointer-first orchestration, adequacy pressure, synthesis, review, re-entry,
  one-writer report, scorer bridge, and claim custody.
- This prompt is rendered during dry-run planning. It may be executed only when
  `mesh-execute-live` supplies a separately approved live run-control receipt.

## Objective
{task["objective"]}

## Role-Specific Instructions
Role family: {profile["title"]}

{role_instructions}

## Allowed Inputs
{json.dumps(allowed_inputs, indent=2)}

## Output File Contract
{json.dumps(expected_outputs, indent=2)}

## Required Output Shape
{output_schema}
{overlay_section}

If this is a branch or re-entry role, return the file triplet:

- `pointer.md` with objective, key findings, evidence map, and `Read Next`;
- `analysis.md` with section headings named by the pointer;
- `evidence.jsonl` with source refs, admission status, and produced-by event
  custody.

## Pointer-First Law
- Branch agents write files; they do not return long chat payloads as the
  authoritative artifact.
- The orchestrator reads `pointer.md` first, then only selected analysis spans
  named by the pointer.
- Synthesis may cite only admitted evidence and recorded pointer-read receipts.

## Source Policy
- Use only allowed input files and sources permitted by the run-control receipt.
- Do not read env files, secrets, customer data, root runtime data, private
  benchmark corpora, or raw paid benchmark payloads.
- If public web access is unavailable or evidence is thin, record the gap
  explicitly instead of filling it by assumption.

## Citation Discipline
- Every material factual claim must map to `evidence.jsonl`, a cited source URL,
  or a local artifact path.
- Quote or summarize only what the source supports.
- Mark unresolveds and contradictions separately from admitted claims.

## Adequacy Criteria
{json.dumps(adequacy_checks, indent=2)}

If adequacy is not satisfied, emit the gap and the specific follow-up task the
orchestrator or reviewer should consider.

## Adequacy Backpressure Law
- `backpressure/adequacy_backpressure_queue.json` is the inspectable queue for
  unresolved adequacy pressure.
- If the queue exists with `queue_status: "open"` and `writer_blocked: true`,
  the final writer must stop and the live executor may lawfully end as
  `blocked_by_adequacy_backpressure`.
- Open queue items must preserve the source adequacy finding, unresolved gap,
  required action, target surface, follow-up task or writer constraint, and
  source refs.
- A `writer_constraints` queue may allow writing only when the constraints are
  carried into the writer-facing surface as unresolved limitations.
- Validation success for a lawfully blocked run is not benchmark success,
  research quality, Grep parity, or final-answer success.

## Run-Control Boundary
- Dry-run planning receipt: `{receipt["receipt_id"]}`
- Wall-clock bound: `{receipt["operational_bounds"]["max_wall_clock_minutes"]}` minutes
- Kill path: {receipt["operational_bounds"]["kill_path"]}
- Automatic retry allowed: false

## Claim Boundary
Allowed claims if this future role succeeds:
{json.dumps(receipt["allowed_claims_if_success"], indent=2)}

Non-claims even if this future role succeeds:
{json.dumps(non_claims, indent=2)}

Do not claim Grep parity, a benchmark score, leaderboard rank, product readiness,
or benchmark execution unless a later validated run and scorer bundle proves it.

This prompt file alone does not authorize live execution.
"""


def live_role_output_schema_notes(task: dict[str, Any], role: dict[str, Any]) -> str:
    task_kind = task.get("kind")
    if task_kind == "planning":
        return """For the researcher-planner role, always write the four planner files:
- `plan.md`
- `skills_tools.json`
- `adequacy_criteria.json`
- `task_graph.json`

Read `case_manifest.json` first when present, then any ratification, governor,
or run-control instruction files included in the allowed inputs. Use only the
allowed files and tools. Treat world knowledge as planning prior only.

Use one planning status consistently across all four files:
- `mesh_plan_ready`: the answer object is fixed enough, or a ratification/default-authorization file explicitly permits planning.
- `awaiting_ratification`: topology-changing ambiguity remains and no ratification/default authorization is present.
- `blocked_by_input`: required source, context, permission, or run-control authority is missing and no safe default exists.

The planner may propose defaults, but it may not authorize defaults. Default
authorization must come from the user, governor, ratification receipt, or
run-control context.

If status is `awaiting_ratification`, write `plan.md` as an intent-ratification
packet with clarification questions, write proposed skill/tool needs rather than
selected runtime skills, mark adequacy criteria as candidate criteria, and write
`task_graph.json` with `executable: false`, `tasks: []`, `reason`, and
`blocked_until`.

If status is `blocked_by_input`, identify the missing input or authority and do
not compile executable branch tasks.

`plan.md` must contain the planning status, recovered objective, answer object
or candidate answer object, assumptions/defaults, scope boundaries,
fake-success modes and controls, methodology, branch rationale when executable,
synthesis plan, review plan, re-entry plan, writer gate, claim boundary, and
open planning risks. When status is `awaiting_ratification`, make it an
intent-ratification packet with topology-changing ambiguities, proposed
defaults, clarification questions, and what ratification would change.

`skills_tools.json` must be valid JSON with `planning_status`,
`selected_skills`, `required_but_missing_skills`, `allowed_tools_or_sources`,
`disabled_tools_or_sources`, `tooling_gaps`, and `methodology_notes`. Do not
pretend a tool, app, plugin, MCP server, or skill is available when the allowed
inputs or run-control context do not provide it.

`adequacy_criteria.json` must be valid JSON with `planning_status`, `criteria`,
`review_checklist`, `writer_blocking_conditions`, `reentry_triggers`,
`lawful_partial_conditions`, and `claim_boundary_checks`. If ratification is
pending, mark these as candidate criteria, not final criteria.

`task_graph.json` must be valid JSON. If status is `awaiting_ratification` or
`blocked_by_input`, set `executable: false`, `tasks: []`, `reason`, and
`blocked_until`. If status is `mesh_plan_ready`, set `executable: true` and
include executable tasks, dependency edges, parallel groups, synthesis task,
review task, re-entry policy, and writer gate.

If status is `mesh_plan_ready`, compile executable branch tasks by epistemic
function. Every branch task must include `task_id`, `role_family`, `objective`,
`why_it_exists`, `failure_prevented`, `allowed_inputs`, `required_outputs`,
`depends_on`, `adequacy_condition`, `valid_failure_returns`, and
`reentry_relevance`. Branches must require pointer / analysis / evidence returns
unless explicitly non-evidence-bearing.

When writing `task_graph.json`, preserve compatibility with the current
`codex-dr.task_graph.v1` file-based harness shape: executable tasks still need
task ids, kind/role mapping, dependencies, status, assigned box or role config
when available, allowed inputs, expected outputs, adequacy checks, review/reentry
links, and explicit dependency edges or parallel groups when the planner is
authoring a richer graph.

Valid failure returns are `evidence_gap`, `provenance_gap`, `contradiction`,
`scope_ambiguity`, `non_comparable_inputs`, `blocked_by_input`, and
`insufficient_budget_or_time`.

Do not answer the research question, do not use world knowledge as evidence, and
do not make Grep parity, score, leaderboard, product-readiness, official
submission, scorer-backed, or improvement claims without later receipts and
claim review."""
    if task_kind == "evaluate_synthesize" and str(task.get("task_id", "")).startswith(
        "task_reentry_synthesis"
    ):
        return """For re-entry synthesis, consume exactly one bounded re-entry
repair packet and the corresponding branch outputs. Read `reentry_task_packet.json`
or the packet referenced by the dynamic role plan, then read the re-entry
branch `pointer.md` before any analysis.

Write:
- `pointer_read_receipts.jsonl`
- `adequacy_assessments.jsonl`
- `synthesis.md`
- `contradictions.json`
- `report_outline.md`
- `reentry/<gap_id>/reentry_synthesis.md` when listed in required outputs
- `reentry/<gap_id>/adequacy_delta.json` when listed in required outputs

Each pointer receipt must preserve `selected_analysis_spans` for the re-entry
branch so later review can inspect exactly what repair analysis was admitted.

Integrate repair evidence into the existing answer substrate or adequacy delta.
Do not perform new research, write the final report, update the canonical
backpressure queue, write a review, close the blocker, or authorize the writer.

Preserve the original blocker id, closure condition, reviewer-owned closure
authority, and remaining gaps. Treat `repair_returned`, `narrowed`, and
`closed_candidate` as review inputs, not closure. If closure evidence improved
but any material gap remains, write an adequacy assessment that preserves the
gap as narrowed or still open.

`adequacy_delta.json` must name the source gap id, source task packet path,
source re-entry result path, re-entry synthesis path, what evidence changed,
proposed next status, remaining blockers, reviewer next action,
reviewer-owned closure authority, `closure_authorized: false`, and
`writer_permission: false`.

Write `adequacy_delta.json` with this exact schema shape:
- `schema_version: "codex_dr_reentry_adequacy_delta.v1"`
- `source_gap_id`
- `source_task_packet_path`
- `source_reentry_result_path`
- `reentry_synthesis_path`
- `evidence_delta`
- `proposed_next_status`
- `remaining_blockers`
- `reviewer_next_action`
- `closure_authority`
- `closure_authorized: false`
- `writer_permission: false`

Do not use `codex_dr_adequacy_delta_v0.1`, do not omit
`closure_authority`, and do not rename `source_reentry_result_path` to
`source_reentry_result`.

If branch outputs include task-specific closure evidence such as
`citation_support_map.json`, `comparability_assessment.json`,
`provenance_map.json`, `contradiction_assessment.json`, or
`numerical_support_appendix.json`, reference it as reviewer input. The reviewer
adjudicates closure; the harness updates queue and gate state."""
    if task_kind == "evaluate_synthesize":
        return """For `pointer_read_receipts.jsonl`, write one JSON object per branch with:
- `branch_id`
- `pointer_path`
- `pointer_read_before_analysis: true`
- `selected_analysis_spans`: array of objects with `analysis_path` and `section_heading`
- `evidence_paths`: array of evidence files inspected
- `admitted_from_pointer`
- `blocked_or_gap_claims`

The synthesis role may inspect each branch's `analysis.md` and `evidence.jsonl`
only after reading that branch's `pointer.md`.

Write unresolved adequacy to `adequacy_assessments.jsonl`; do not write the
canonical backpressure queue or a gate receipt. The harness compiles queue state
from assessments and review artifacts."""
    if task_kind == "review":
        return """For the reviewer / adequacy pressure role, write:
- `reviews/review_001.json`

Do not answer the research question, write the final report, perform broad new
research, score benchmarks, promote claims, update `allowed_claims.json`, or
write `backpressure/adequacy_backpressure_queue.json` or
`backpressure/backpressure_gate_receipt.json`.

Read in this order when present and allowed: `plan.md`,
`adequacy_criteria.json`, `task_graph.json`, `pointer_read_receipts.jsonl`,
`adequacy_assessments.jsonl`, `synthesis.md`, `contradictions.json`,
`report_outline.md`, needed branch pointer/analysis/evidence files, any existing
`backpressure/adequacy_backpressure_queue.json`, and re-entry closure evidence
such as `citation_support_map.json`.

Evidence law: only branch evidence rows, source URLs or local artifact paths
referenced by evidence rows, pointer-read receipts, admitted analysis spans
named by pointers, and closure evidence files count as evidence. Summary prose,
model prior, and nearby citations without evidence mapping do not count.

Use one review status: `adequate_for_writer`,
`not_adequate_writer_blocked`, `narrowed_not_closed`,
`lawful_partial_candidate`, `blocked_by_input`, `requires_reentry`,
`requires_citation_verification`, or `requires_methodology_repair`. Do not mark
adequate because files exist; structural custody is not research quality.

`reviews/review_001.json` must be valid JSON containing `schema_version:
"codex_dr_review_v0.2"`, run id, case id when available, review round, review
mode, review status, answer-object fit, adequacy criteria results, material
findings, writer readiness recommendation, `proposed_backpressure_items`, lawful
partial assessment, and claim-boundary assessment. Use honest `not_assessable`
or null values where evidence is missing.

When a failure blocks writing, requires re-entry, requires review, or blocks
claim promotion, include it inside `proposed_backpressure_items`. The harness
compiles/syncs those proposed items into the canonical
`backpressure/adequacy_backpressure_queue.json`; the reviewer must not write the
canonical queue directly.

Each proposed item must include `gap_id`, `status`, `failure_type`,
`adequacy_criterion_id`, `target_surface`, `source_refs`, `gate_effects`,
`failure_statement`, `required_action`, `closure_condition`,
`closure_authority`, `resolution_mode`, and `resolution_refs`.

`gate_effects` must be an object, not a list. Use only these boolean keys when
they change downstream behavior: `writer_blocking`, `reentry_required`,
`review_required`, and `claim_blocking`.

`required_action` must be an object with `action_type`, `objective`,
`allowed_inputs`, and `required_outputs`; do not write it as a prose string.
Use operational failure types such as `answer_object_mismatch`, `evidence_gap`,
`citation_support_gap`, `provenance_gap`, `contradiction`, `scope_ambiguity`,
`non_comparable_inputs`, `numerical_support_gap`, `methodology_gap`,
`tooling_gap`, `source_access_gap`, `adequacy_criteria_gap`,
`writer_gate_gap`, or `claim_boundary_gap`.

`repair_returned` is not closure. `narrowed` is not closure. A re-entry branch
may propose closure but cannot authorize closure by itself. If any
writer-blocking item remains `open`, `assigned`, `repair_returned`,
`review_pending`, `narrowed`, or `blocked_by_input`, recommend that the writer
remain blocked. The harness derives final transition gates; the reviewer supplies
semantic adjudication.

For citation-support blockers, require statement-to-source verification with
`pointer.md`, `analysis.md`, `evidence.jsonl`, and `citation_support_map.json`.
Do not let the writer proceed through open citation-support blockers."""
    if task_kind == "reentry_research":
        branch_id = task.get("branch_id", "reentry_followup")
        return f"""For the re-entry branch, use `branches/{branch_id}/`.
Consume exactly one `reentry_task_packet.json` when present in the branch
workspace root. The packet is the scope authority; do not broaden it into a
general research task.

For ready packets, write every packet-required output. At minimum write
`pointer.md`, `analysis.md`, `evidence.jsonl`, and `reentry_result.json`, plus
task-specific closure artifacts such as `citation_support_map.json` when named
by the packet.

For missing, malformed, or non-ready packets, write blocked fallback outputs:
`pointer.md`, `analysis.md`, `evidence.jsonl`, and `reentry_result.json`.
The blocked `evidence.jsonl` should contain a `blocker_record` row rather than
being omitted.

The pointer must name the source gap id or blocked packet reason, the bounded
repair objective, affected artifacts inspected, output files written, proposed
repair result status, and remaining blockers.

Every `evidence.jsonl` row must contain `admission_status`; do not write
`status` as a substitute field. Use `admitted_input` for cited input artifacts,
`derived_from_admitted_inputs` for bounded repair results, and `bounded_result`
when the row records a reviewer-facing disposition rather than evidentiary
support for a fact.

For citation-support repair, verify only claim ids, statement ids, spans,
sections, or bounded artifact slices named by the packet. If the packet scope is
too broad, return `blocked_by_input` or `open`; do not perform a whole-document
audit unless explicitly scoped and authorized.

You may propose `closed_candidate`, `narrowed`, `open`, `blocked_by_input`,
`blocked_by_tooling`, `contradicted`, or `lawful_partial_candidate` in
`reentry_result.json`. The reviewer adjudicates closure. Do not write
`backpressure/adequacy_backpressure_queue.json`,
`backpressure/backpressure_gate_receipt.json`, `reviews/review_001.json`,
`report.md`, `allowed_claims.json`, or `benchmark_score.json`."""
    if task_kind == "report_writer":
        return """For `report.md`, write one coherent report voice from admitted
synthesis, `report_outline.md`, latest review, claim ledger, and gate state.

Read `writer_gate_preflight.json` when provided. Otherwise read
`backpressure/backpressure_gate_receipt.json` when present and the canonical
backpressure queue.

If this role somehow runs while gate inputs still show open writer-blocking
adequacy, write `report.md` as a blocked-state output rather than a final
answer. Name the open blockers and stop. Do not invent closure.

When writing is permitted, write only from admitted synthesis and verified
support. Do not introduce new facts, upgrade hypotheses into conclusions, hide
contradictions, cite unadmitted evidence, or convert validation success into
research quality.

Do not claim final-answer success, Grep parity, benchmark score, leaderboard
rank, product readiness, official submission readiness, or scorer-backed
evaluation unless claim review and scorer receipts explicitly permit it."""
    role_name = role.get("role")
    if role_name == "deep_search":
        return """For the deep-search branch, write the pointer / analysis /
evidence triplet. Every `evidence.jsonl` row must include `admission_status`,
source path or URL, what was inspected, what it supports, what it does not
support, and unresolved gaps. `status` is not an acceptable substitute field.

Classify rows as source discovery, direct evidence, contradiction candidate,
provenance note, or access/tooling gap. Source discovery is not source
validation; do not present collected sources as admitted support until
verification or synthesis admits them."""
    if role_name == "data_analysis":
        return """For the data-analysis branch, write the pointer / analysis /
evidence triplet. For every numerical, comparative, or derived claim, include a
claim id, quantity/comparison, derivation, source path, evidence id, confidence,
and unresolved gap. Every evidence row must include `admission_status`; `status`
is not an acceptable substitute field.

Do not rank, compare, forecast, or normalize across entities unless metrics,
time horizon, geography/jurisdiction, entity class, and evidence standard are
explicit. If comparability is unresolved, mark `non_comparable_inputs` or
`scope_ambiguity` rather than forcing a conclusion."""
    if role_name == "verification":
        return """For the verification branch, write the pointer / analysis /
evidence triplet. Consume assigned claims, source rows, pointer receipts, or
branch evidence; do not perform broad new search unless the task contract
explicitly permits it.

Classify each checked claim as `directly_supported`, `partially_supported`,
`indirectly_supported`, `unsupported`, `contradicted`, `source_missing`, or
`too_broad_for_evidence`. Distinguish source existence from statement-to-source
support. Every evidence row must include `admission_status`; `status` is not an
acceptable substitute field."""
    return """For branch roles, write the pointer / analysis / evidence triplet.
Every evidence row needs an `admission_status`; `status` is not an acceptable
substitute field. Use admitted statuses for source-supported facts,
`inference_from_admitted_evidence` for analytic inferences derived from admitted
facts, and explicit gap statuses for unresolveds."""


def role_prompt_profile(task: dict[str, Any], role: dict[str, Any]) -> dict[str, Any]:
    task_kind = task.get("kind")
    role_name = role.get("role")
    if task_kind == "reentry_research":
        return ROLE_PROMPT_PROFILES["reentry"]
    if task_kind == "evaluate_synthesize":
        return ROLE_PROMPT_PROFILES["orchestrator"]
    if task_kind == "review":
        return ROLE_PROMPT_PROFILES["reviewer"]
    if task_kind == "report_writer":
        return ROLE_PROMPT_PROFILES["writer"]
    return ROLE_PROMPT_PROFILES.get(role_name, ROLE_PROMPT_PROFILES["verification"])


def mesh_bootstrap_run(
    case_id: str,
    *,
    runs_dir: Path | str | None = None,
    case_index: int = 0,
    case_spec: dict[str, Any] | None = None,
    manifest_source: dict[str, Any] | None = None,
) -> Path:
    run_dir = mesh_init_case(case_id, runs_dir=runs_dir, force=True)
    mesh_bootstrap_plan(
        case_id,
        runs_dir=runs_dir,
        case_index=case_index,
        case_spec=case_spec,
        manifest_source=manifest_source,
    )
    mesh_bootstrap_branch(
        case_id,
        "deep_search",
        spawn_event_id="evt_0006_deep_search_spawn_declared",
        return_event_id="evt_0007_deep_search_return_written",
        runs_dir=runs_dir,
    )
    mesh_bootstrap_branch(
        case_id,
        "data_analysis",
        spawn_event_id="evt_0008_data_analysis_spawn_declared",
        return_event_id="evt_0009_data_analysis_return_written",
        runs_dir=runs_dir,
    )
    mesh_bootstrap_branch(
        case_id,
        "verification",
        spawn_event_id="evt_0010_verification_spawn_declared",
        return_event_id="evt_0011_verification_return_written",
        runs_dir=runs_dir,
    )
    mesh_bootstrap_evaluate(case_id, runs_dir=runs_dir)
    mesh_bootstrap_review(case_id, runs_dir=runs_dir)
    mesh_bootstrap_reentry(case_id, "review_001", runs_dir=runs_dir)
    mesh_bootstrap_report(case_id, runs_dir=runs_dir)
    mesh_bootstrap_score(case_id, runs_dir=runs_dir)
    mesh_bootstrap_self_improve(case_id, runs_dir=runs_dir)
    return run_dir


def suite_case_record(
    *,
    runs_root: Path,
    case_run_id: str,
) -> dict[str, Any]:
    report = validate_run(case_run_id, runs_dir=runs_root)
    manifest = read_json(runs_root / case_run_id / "case_manifest.json")
    ledger = read_json(runs_root / case_run_id / "evaluation_ledger.json")
    return {
        "run_id": case_run_id,
        "case_id": manifest.get("case_id"),
        "benchmark_family": manifest.get("benchmark_family"),
        "row_indices": manifest.get("source", {}).get("row_indices", []),
        "case_manifest": f"../{case_run_id}/case_manifest.json",
        "evaluation_ledger": f"../{case_run_id}/evaluation_ledger.json",
        "allowed_claims": f"../{case_run_id}/allowed_claims.json",
        "validation_status": report["status"],
        "failed_checks": report["failed_checks"],
        "result_status": ledger.get("result_status"),
    }


def multi_case_smoke(
    suite_id: str,
    *,
    runs_dir: Path | str | None = None,
    case_count: int = 2,
    force: bool = False,
) -> Path:
    validate_id(suite_id, "suite_id")
    if case_count < 2:
        raise HarnessError("multi-case smoke requires at least two cases")
    runs_root = Path(runs_dir or DEFAULT_RUNS_DIR)
    suite_dir = runs_root / suite_id
    if suite_dir.exists() and force:
        shutil.rmtree(suite_dir)
    if suite_dir.exists() and any(suite_dir.iterdir()):
        raise HarnessError(f"suite already exists: {suite_dir}")
    suite_dir.mkdir(parents=True, exist_ok=True)
    case_records = []
    for case_index in range(case_count):
        case_run_id = f"{suite_id}_case_{case_index + 1:03d}"
        mesh_bootstrap_run(case_run_id, runs_dir=runs_root, case_index=case_index)
        case_records.append(suite_case_record(runs_root=runs_root, case_run_id=case_run_id))
    suite_manifest = {
        "schema_version": "codex-dr.multi_case_suite.v1",
        "suite_id": suite_id,
        "benchmark_family": "DRACO",
        "execution_mode": "provider_off_multi_case_smoke",
        "case_selection_contract": {
            "dataset_id": "perplexity-ai/draco",
            "dataset_commit": "ce076749809027649ebd331bcb70f42bf720d387",
            "split": "test",
            "row_indices": list(range(case_count)),
            "raw_data_in_git": False,
            "reference_and_rubric_visibility": "scorer_only",
        },
        "cases": case_records,
        "claim_boundary": {
            "allowed_claims_if_valid": [
                "Multiple sealed DRACO-shaped cases passed through the provider-off "
                "DR mesh validation lane."
            ],
            "blocked_claims": [
                "DRACO score",
                "Grep parity",
                "leaderboard rank",
                "product readiness",
            ],
        },
    }
    write_json(suite_dir / "benchmark_suite_manifest.json", suite_manifest)
    summary = validate_multi_case_suite(suite_id, runs_dir=runs_root)
    write_json(suite_dir / "benchmark_suite_summary.json", summary)
    if summary["status"] != "passed":
        raise HarnessError(
            "manifest-driven multi-case suite failed validation: "
            + "; ".join(summary["failed_checks"])
        )
    return suite_dir


def multi_case_from_manifest(
    suite_id: str,
    *,
    manifest_path: Path,
    runs_dir: Path | str | None = None,
    force: bool = False,
) -> Path:
    validate_id(suite_id, "suite_id")
    manifest = read_case_spec_manifest(manifest_path)
    benchmark_family = manifest["benchmark_family"]
    runs_root = Path(runs_dir or DEFAULT_RUNS_DIR)
    suite_dir = runs_root / suite_id
    if suite_dir.exists() and force:
        shutil.rmtree(suite_dir)
    if suite_dir.exists() and any(suite_dir.iterdir()):
        raise HarnessError(f"suite already exists: {suite_dir}")
    suite_dir.mkdir(parents=True, exist_ok=True)
    case_records = []
    for case_index, case_spec in enumerate(manifest["cases"]):
        case_run_id = f"{suite_id}_case_{case_index + 1:03d}"
        mesh_bootstrap_run(
            case_run_id,
            runs_dir=runs_root,
            case_index=case_index,
            case_spec=case_spec,
            manifest_source=manifest.get("source", {}),
        )
        case_records.append(suite_case_record(runs_root=runs_root, case_run_id=case_run_id))
    row_indices = [
        row_index
        for case in case_records
        for row_index in case.get("row_indices", [])
    ]
    suite_manifest = {
        "schema_version": "codex-dr.multi_case_suite.v1",
        "suite_id": suite_id,
        "benchmark_family": benchmark_family,
        "execution_mode": "provider_off_multi_case_manifest",
        "source_case_spec_manifest": manifest_path.as_posix(),
        "case_selection_contract": {
            **manifest.get("source", {}),
            "row_indices": row_indices,
            "raw_data_in_git": False,
            "reference_and_rubric_visibility": "scorer_only",
        },
        "cases": case_records,
        "claim_boundary": {
            "allowed_claims_if_valid": [
                f"Manifest-selected sealed {benchmark_family} cases passed through "
                "the provider-off DR mesh validation lane."
            ],
            "blocked_claims": [
                f"{benchmark_family} score",
                "Grep parity",
                "leaderboard rank",
                "product readiness",
            ],
        },
    }
    write_json(suite_dir / "benchmark_suite_manifest.json", suite_manifest)
    summary = validate_multi_case_suite(suite_id, runs_dir=runs_root)
    write_json(suite_dir / "benchmark_suite_summary.json", summary)
    if summary["status"] != "passed":
        raise HarnessError(
            "manifest-driven multi-case suite failed validation: "
            + "; ".join(summary["failed_checks"])
        )
    return suite_dir


def validate_multi_case_suite(
    suite_id: str,
    *,
    runs_dir: Path | str | None = None,
) -> dict[str, Any]:
    runs_root = Path(runs_dir or DEFAULT_RUNS_DIR)
    suite_dir = runs_root / suite_id
    manifest = read_json(suite_dir / "benchmark_suite_manifest.json")
    problems = []
    if manifest.get("schema_version") != "codex-dr.multi_case_suite.v1":
        problems.append("invalid suite schema_version")
    cases = manifest.get("cases", [])
    if len(cases) < 2:
        problems.append("suite must include at least two cases")
    benchmark_families = set()
    case_ids = set()
    for case in cases:
        run_id = case.get("run_id")
        if not run_id:
            problems.append("case missing run_id")
            continue
        run_dir = runs_root / run_id
        try:
            case_manifest = read_json(run_dir / "case_manifest.json")
            ledger = read_json(run_dir / "evaluation_ledger.json")
        except (FileNotFoundError, json.JSONDecodeError) as error:
            problems.append(f"{run_id}: case artifacts unavailable: {error}")
            continue
        if case_manifest.get("schema_version") != "codex-dr.case_manifest.v1":
            problems.append(f"{run_id}: invalid case manifest schema")
        benchmark_families.add(case_manifest.get("benchmark_family"))
        case_id = case_manifest.get("case_id")
        if not case_id:
            problems.append(f"{run_id}: missing case_id")
        elif case_id in case_ids:
            problems.append(f"{run_id}: duplicate case_id {case_id}")
        case_ids.add(case_id)
        if ledger.get("case_id") != case_id:
            problems.append(f"{run_id}: evaluation ledger case_id mismatch")
        report = validate_run(run_id, runs_dir=runs_root)
        if report["status"] != "passed":
            problems.append(f"{run_id}: validation failed {report['failed_checks']}")
    if len(benchmark_families) != 1:
        problems.append("suite mixes benchmark families")
    elif not benchmark_families.issubset(SUPPORTED_CASE_MANIFEST_FAMILIES):
        problems.append("suite has unsupported benchmark family")
    benchmark_family = next(iter(benchmark_families), None)
    status = "failed" if problems else "passed"
    return {
        "schema_version": "codex-dr.multi_case_validation.v1",
        "suite_id": suite_id,
        "status": status,
        "case_count": len(cases),
        "benchmark_family": (
            benchmark_family
            if not problems
            else sorted(str(item) for item in benchmark_families)
        ),
        "failed_checks": problems,
        "cases": cases,
        "claim_boundary": manifest.get("claim_boundary", {}),
    }


def suite_claim_review(
    suite_id: str,
    *,
    runs_dir: Path | str | None = None,
) -> Path:
    validate_id(suite_id, "suite_id")
    runs_root = Path(runs_dir or DEFAULT_RUNS_DIR)
    suite_dir = runs_root / suite_id
    try:
        manifest = read_json(suite_dir / "benchmark_suite_manifest.json")
    except (FileNotFoundError, json.JSONDecodeError) as error:
        raise HarnessError(f"suite manifest unavailable: {error}") from error
    if manifest.get("schema_version") != "codex-dr.multi_case_suite.v1":
        raise HarnessError("suite manifest schema_version is invalid")
    problems = []
    case_reviews = []
    for case in manifest.get("cases", []):
        run_id = case.get("run_id")
        if not run_id:
            problems.append("suite case missing run_id")
            continue
        run_dir = runs_root / run_id
        report = validate_run(run_id, runs_dir=runs_root)
        if report["status"] != "passed":
            problems.append(f"{run_id}: validation failed {report['failed_checks']}")
        try:
            score = read_json(run_dir / "benchmark_score.json")
            allowed = read_json(run_dir / "allowed_claims.json")
        except (FileNotFoundError, json.JSONDecodeError) as error:
            problems.append(f"{run_id}: claim artifacts unavailable: {error}")
            continue
        widened_claims = []
        for claim in allowed.get("allowed_claims", []):
            text = str(claim.get("claim", "")).lower()
            if any(phrase in text for phrase in BLOCKED_ALLOWED_CLAIM_PHRASES):
                widened_claims.append(claim.get("claim", "<unknown>"))
        if widened_claims:
            problems.append(
                f"{run_id}: widened blocked claims: {'; '.join(widened_claims)}"
            )
        if score.get("score") is None:
            decision = "blocked_no_score"
            reason = "Case has no numeric score."
        elif not (run_dir / "claim_review.json").exists():
            decision = "blocked_missing_case_claim_review"
            reason = "Scored case lacks its own claim-review artifact."
            problems.append(f"{run_id}: scored case lacks claim_review.json")
        else:
            case_review = read_json(run_dir / "claim_review.json")
            if case_review.get("may_widen_public_benchmark_claims") is True:
                decision = "blocked_suite_review_required"
                reason = "Case review is not enough to open suite-level claims."
            else:
                decision = "blocked_by_case_claim_review"
                reason = "Case claim-review keeps public benchmark claims blocked."
        case_reviews.append(
            {
                "run_id": run_id,
                "case_id": case.get("case_id"),
                "row_indices": case.get("row_indices", []),
                "score_mode": score.get("mode"),
                "score_present": score.get("score") is not None,
                "case_claim_review_present": (run_dir / "claim_review.json").exists(),
                "decision": decision,
                "reason": reason,
            }
        )
    review_status = "failed" if problems else "passed"
    if problems:
        suite_decision = "failed_closed"
    elif all(review["decision"] == "blocked_no_score" for review in case_reviews):
        suite_decision = "blocked_no_score"
    else:
        suite_decision = "blocked_suite_review_required"
    review = {
        "schema_version": "codex-dr.benchmark_suite_claim_review.v1",
        "suite_id": suite_id,
        "benchmark_family": manifest.get("benchmark_family"),
        "status": review_status,
        "decision": suite_decision,
        "may_widen_public_benchmark_claims": False,
        "case_count": len(case_reviews),
        "case_reviews": case_reviews,
        "failed_checks": problems,
        "policy": {
            "policy_id": "codex_dr_suite_claim_review_policy_v1",
            "minimum_open_requirements": [
                "all cases pass validation",
                "all scored cases have case-level claim review",
                "suite-level variance or repeatability evidence",
                "explicit Principal approval for public claim widening",
            ],
            "blocked_claims": [
                "DRACO score",
                "Grep parity",
                "leaderboard rank",
                "product readiness",
            ],
        },
        "claim_boundary": {
            "allowed_claims_if_passed": [
                "A suite-level claim-review gate evaluated the benchmark suite and "
                "kept public benchmark claims blocked."
            ],
            "blocked_claims": [
                "DRACO score",
                "Grep parity",
                "leaderboard rank",
                "product readiness",
            ],
        },
        "produced_at": FIXTURE_TIMESTAMP,
    }
    write_json(suite_dir / "benchmark_suite_claim_review.json", review)
    if problems:
        raise HarnessError(
            "suite claim-review failed closed: " + "; ".join(problems)
        )
    return suite_dir


def deepresearch_bench_subset_pressure(
    suite_id: str,
    *,
    manifest_path: Path,
    source_refresh: Path,
    official_repo: Path,
    runs_dir: Path | str | None = None,
    force: bool = False,
    limit: int | None = None,
    allow_invalid_reports: bool = False,
) -> Path:
    validate_id(suite_id, "suite_id")
    source = read_json(source_refresh)
    if source.get("schema_version") != "codex-dr.deepresearch_bench_source_refresh.v1":
        raise HarnessError("source refresh is not a DeepResearch Bench receipt")
    suite_dir = multi_case_from_manifest(
        suite_id,
        manifest_path=manifest_path,
        runs_dir=runs_dir,
        force=force,
    )
    return deepresearch_bench_existing_subset_pressure(
        suite_id,
        source_refresh=source_refresh,
        official_repo=official_repo,
        runs_dir=runs_dir,
        limit=limit,
        source=source,
        suite_dir=suite_dir,
        allow_invalid_reports=allow_invalid_reports,
    )


def deepresearch_bench_existing_subset_pressure(
    suite_id: str,
    *,
    source_refresh: Path,
    official_repo: Path,
    runs_dir: Path | str | None = None,
    limit: int | None = None,
    allow_invalid_reports: bool = False,
    source: dict[str, Any] | None = None,
    suite_dir: Path | None = None,
) -> Path:
    validate_id(suite_id, "suite_id")
    source = source or read_json(source_refresh)
    if source.get("schema_version") != "codex-dr.deepresearch_bench_source_refresh.v1":
        raise HarnessError("source refresh is not a DeepResearch Bench receipt")
    runs_root = Path(runs_dir or DEFAULT_RUNS_DIR)
    suite_dir = suite_dir or (runs_root / suite_id)
    if not suite_dir.exists():
        raise HarnessError(f"existing subset suite is missing: {suite_dir}")
    suite_manifest = read_json(suite_dir / "benchmark_suite_manifest.json")
    if suite_manifest.get("benchmark_family") != BENCHMARK_FAMILY_DEEPRESEARCH_BENCH:
        raise HarnessError("subset pressure requires a DeepResearch Bench suite")
    cases = suite_manifest.get("cases", [])
    if limit is not None:
        cases = cases[:limit]
    if len(cases) < 2:
        raise HarnessError("DeepResearch Bench subset pressure requires at least two cases")
    case_ids = [case["run_id"] for case in cases]
    raw_reports = suite_dir / "deepresearch_bench_subset_raw_reports.jsonl"
    raw_custody = suite_dir / "deepresearch_bench_subset_raw_reports_custody.json"
    deepresearch_bench_report_export(
        case_ids,
        output=raw_reports,
        custody_output=raw_custody,
        runs_dir=runs_root,
        allow_invalid=allow_invalid_reports,
    )
    race_dir = suite_dir / "race_bridge"
    race_manifest_path = deepresearch_bench_race_bridge(
        raw_reports=raw_reports,
        source_refresh=source_refresh,
        official_repo=official_repo,
        output_dir=race_dir,
        model_name=f"{suite_id}-subset",
        allow_provider_run=False,
        limit=len(case_ids),
        max_workers=1,
        timeout_seconds=1800,
    )
    race_receipt = read_json(race_dir / "race_bridge_receipt.json")
    suite_validation = validate_multi_case_suite(suite_id, runs_dir=runs_root)
    suite_claim = deepresearch_bench_subset_claim_review_payload(
        suite_id=suite_id,
        suite_manifest=suite_manifest,
        case_ids=case_ids,
        race_receipt=race_receipt,
        allow_invalid_reports=allow_invalid_reports,
    )
    write_json(suite_dir / "benchmark_suite_claim_review.json", suite_claim)
    subset_summary = deepresearch_bench_subset_summary_payload(
        suite_id=suite_id,
        suite_manifest=suite_manifest,
        cases=cases,
        source=source,
        suite_validation=suite_validation,
        raw_reports=raw_reports,
        raw_custody=raw_custody,
        race_manifest_path=race_manifest_path,
        race_receipt=race_receipt,
        allow_invalid_reports=allow_invalid_reports,
    )
    write_json(suite_dir / "deepresearch_bench_subset_pressure_summary.json", subset_summary)
    write_json(
        suite_dir / "subset_improvement_inputs.json",
        deepresearch_bench_subset_improvement_inputs(subset_summary),
    )
    validation = validate_deepresearch_bench_subset_pressure(suite_id, runs_dir=runs_root)
    write_json(suite_dir / "deepresearch_bench_subset_pressure_validation.json", validation)
    if validation["status"] != "passed":
        raise HarnessError(
            "DeepResearch Bench subset pressure failed validation: "
            + "; ".join(validation["failed_checks"])
        )
    return suite_dir


def deepresearch_bench_subset_claim_review_payload(
    *,
    suite_id: str,
    suite_manifest: dict[str, Any],
    case_ids: list[str],
    race_receipt: dict[str, Any],
    allow_invalid_reports: bool = False,
) -> dict[str, Any]:
    scorer_blocked = race_receipt.get("status") != "scored_claims_blocked"
    decision = "blocked_no_score" if scorer_blocked else "blocked_suite_review_required"
    return {
        "schema_version": "codex-dr.benchmark_suite_claim_review.v1",
        "suite_id": suite_id,
        "benchmark_family": BENCHMARK_FAMILY_DEEPRESEARCH_BENCH,
        "status": "passed",
        "decision": decision,
        "may_widen_public_benchmark_claims": False,
        "allow_invalid_reports": allow_invalid_reports,
        "case_count": len(case_ids),
        "case_reviews": [
            {
                "run_id": run_id,
                "decision": "blocked_no_score" if scorer_blocked else "blocked_pending_review",
                "reason": (
                    "Official RACE scorer did not produce a score for the subset."
                    if scorer_blocked
                    else "Subset requires suite-level review before any public claim."
                ),
            }
            for run_id in case_ids
        ],
        "policy": {
            "policy_id": "codex_dr_deepresearch_bench_subset_claim_review_v1",
            "minimum_open_requirements": [
                "all selected cases included in raw report export",
                "official scorer custody for every selected case",
                "aggregate score evidence",
                "explicit Principal approval for public claim widening",
            ],
            "blocked_claims": [
                "DeepResearch Bench score",
                "Grep parity",
                "leaderboard rank",
                "product readiness",
            ],
        },
        "claim_boundary": suite_manifest.get("claim_boundary", {}),
        "race_bridge_receipt": "race_bridge/race_bridge_receipt.json",
        "produced_at": FIXTURE_TIMESTAMP,
    }


def deepresearch_bench_subset_summary_payload(
    *,
    suite_id: str,
    suite_manifest: dict[str, Any],
    cases: list[dict[str, Any]],
    source: dict[str, Any],
    suite_validation: dict[str, Any],
    raw_reports: Path,
    raw_custody: Path,
    race_manifest_path: Path,
    race_receipt: dict[str, Any],
    allow_invalid_reports: bool = False,
) -> dict[str, Any]:
    case_count = len(cases)
    scorer_blocked = race_receipt.get("status") != "scored_claims_blocked"
    failure_taxonomy = []
    blocked_adequacy_cases = []
    planned_unexecuted_cases = []
    suite_run_root = raw_reports.parent.parent
    for case in cases:
        case_run_id = case.get("run_id")
        if not case_run_id:
            continue
        case_run_dir = run_path(case_run_id, suite_run_root)
        if (
            (case_run_dir / "live_adapter" / "launch_plan.json").exists()
            and not is_live_mesh_run(case_run_dir)
        ):
            planned_unexecuted_cases.append(case_run_id)
        if not is_live_mesh_blocked_by_adequacy(case_run_dir):
            continue
        queue = read_optional_json(
            case_run_dir / "backpressure" / "adequacy_backpressure_queue.json"
        )
        blocked_adequacy_cases.append(
            {
                "run_id": case_run_id,
                "queue_status": queue.get("queue_status"),
                "writer_blocked": queue.get("writer_blocked"),
                "gap_count": len(queue.get("items", [])),
                "required_actions": [
                    item.get("required_action") for item in queue.get("items", [])
                ],
            }
        )
    if suite_validation.get("status") != "passed":
        failure_taxonomy.append(
            {
                "failure_class": "suite_validation_failed",
                "severity": "blocking",
                "root_cause": "; ".join(suite_validation.get("failed_checks", [])),
                "affected_cases": [case.get("run_id") for case in cases],
                "raw_export_policy": (
                    "exported_for_failure_analysis"
                    if allow_invalid_reports
                    else "blocked_until_validation_passes"
                ),
            }
        )
    if blocked_adequacy_cases:
        failure_taxonomy.append(
            {
                "failure_class": "adequacy_backpressure_open",
                "severity": "blocking",
                "root_cause": (
                    "At least one live subset case lawfully stopped before the "
                    "final writer on an open adequacy_backpressure queue; the "
                    "mesh needs another narrow re-entry pass before report writing."
                ),
                "affected_cases": [case["run_id"] for case in blocked_adequacy_cases],
                "blocked_cases": blocked_adequacy_cases,
                "raw_export_policy": "blocked_partial_exported_for_failure_analysis",
            }
        )
    if planned_unexecuted_cases:
        failure_taxonomy.append(
            {
                "failure_class": "live_subset_cases_unexecuted",
                "severity": "blocking",
                "root_cause": (
                    "Some selected subset cases have live launch plans but no live "
                    "execution summary because the continuation stopped at the "
                    "first fresh pressure signal."
                ),
                "affected_cases": planned_unexecuted_cases,
                "raw_export_policy": "planned_placeholders_exported_for_failure_analysis",
            }
        )
    if scorer_blocked:
        failure_taxonomy.append(
            {
                "failure_class": "scorer_blocked",
                "severity": "blocking",
                "root_cause": "Official RACE scorer is blocked before provider execution.",
                "missing_requirements": race_receipt.get("provider_requirements", {}).get(
                    "missing_requirements", []
                ),
                "affected_cases": [case.get("run_id") for case in cases],
            }
        )
    return {
        "schema_version": "codex-dr.deepresearch_bench_subset_pressure_summary.v1",
        "suite_id": suite_id,
        "benchmark_family": BENCHMARK_FAMILY_DEEPRESEARCH_BENCH,
        "case_count": case_count,
        "execution_mode": suite_manifest.get("execution_mode"),
        "case_selection_policy": {
            "source_case_spec_manifest": suite_manifest.get("source_case_spec_manifest"),
            "row_indices": [
                row_index
                for case in cases
                for row_index in case.get("row_indices", [])
            ],
            "diversity_basis": "manifest order from refreshed DeepResearch Bench source",
            "excluded_cases_recorded": True,
            "selected_run_ids": [case.get("run_id") for case in cases],
        },
        "source_refresh": {
            "official_repository_commit": source.get("official_repository", {}).get(
                "commit_sha"
            ),
            "official_dataset_revision": source.get("official_dataset", {}).get(
                "revision_sha"
            ),
            "grep_target": current_grep_target_from_source_refresh(source),
        },
        "suite_validation": suite_validation,
        "raw_report_export": {
            "path": raw_reports.as_posix(),
            "custody_path": raw_custody.as_posix(),
            "sha256": sha256_file(raw_reports),
            "case_count": count_jsonl_rows(raw_reports),
            "allow_invalid_reports": allow_invalid_reports,
        },
        "race_bridge": {
            "manifest": race_manifest_path.as_posix(),
            "receipt": "race_bridge/race_bridge_receipt.json",
            "status": race_receipt.get("status"),
            "execution": race_receipt.get("execution", {}),
            "claim_boundary": race_receipt.get("claim_boundary", {}),
        },
        "aggregate_result": {
            "score": None,
            "score_status": "blocked_no_score" if scorer_blocked else "score_claims_blocked",
            "may_claim_parity": False,
        },
        "failure_taxonomy": failure_taxonomy,
        "claim_boundary": {
            "may_widen_claims": False,
            "blocked_claims": [
                "DeepResearch Bench score",
                "Grep parity",
                "leaderboard rank",
                "product readiness",
                "official benchmark submission",
            ],
        },
        "produced_at": FIXTURE_TIMESTAMP,
    }


def deepresearch_bench_subset_improvement_inputs(
    subset_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "codex-dr.deepresearch_bench_subset_improvement_inputs.v1",
        "suite_id": subset_summary["suite_id"],
        "source_summary": "deepresearch_bench_subset_pressure_summary.json",
        "failure_taxonomy": subset_summary.get("failure_taxonomy", []),
        "candidate_inputs": [
            {
                "candidate_input_id": "subset_output_schema_enforcement_001",
                "target_surface_type": "prompt_and_validator",
                "source_failure_classes": ["suite_validation_failed"],
                "recommended_action": (
                    "Tighten re-entry evidence schema instructions and add a "
                    "validator or repair gate so live roles emit `admission_status` "
                    "for every evidence row before subset execution continues."
                ),
            },
            {
                "candidate_input_id": "subset_scorer_authority_001",
                "target_surface_type": "evaluator",
                "source_failure_classes": ["scorer_blocked"],
                "recommended_action": (
                    "Resolve provider authority or keep subset scores blocked with "
                    "explicit receipts."
                ),
            },
            {
                "candidate_input_id": "subset_case_diversity_001",
                "target_surface_type": "scheduler",
                "source_failure_classes": ["subset_pressure"],
                "recommended_action": (
                    "Use subset failures to select the next pressure cases and avoid "
                    "single-case prompt overfitting."
                ),
            },
            {
                "candidate_input_id": "subset_open_backpressure_reentry_001",
                "target_surface_type": "control_flow",
                "source_failure_classes": ["adequacy_backpressure_open"],
                "recommended_action": (
                    "When the queue is open after re-entry synthesis, compile the "
                    "queue item into another narrow re-entry task instead of "
                    "ending the loop before the writer."
                ),
            },
        ],
        "promotion_status": "inputs_only_not_promoted",
        "claim_impact": "no claim widening",
        "produced_at": FIXTURE_TIMESTAMP,
    }


def deepresearch_bench_subset_improvement_compile(
    suite_id: str,
    *,
    runs_dir: Path | str | None = None,
) -> Path:
    validate_id(suite_id, "suite_id")
    runs_root = Path(runs_dir or DEFAULT_RUNS_DIR)
    suite_dir = runs_root / suite_id
    summary = read_json(suite_dir / "deepresearch_bench_subset_pressure_summary.json")
    inputs = read_json(suite_dir / "subset_improvement_inputs.json")
    claim_review = read_json(suite_dir / "benchmark_suite_claim_review.json")
    raw_custody = read_json(suite_dir / "deepresearch_bench_subset_raw_reports_custody.json")
    validation = read_json(suite_dir / "deepresearch_bench_subset_pressure_validation.json")
    out_dir = suite_dir / "subset_improvement"
    receipts_dir = out_dir / "promotion_receipts"
    isolated_dir = out_dir / "isolated_candidate_surfaces"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    isolated_dir.mkdir(parents=True, exist_ok=True)
    failures = inputs.get("failure_taxonomy", [])
    source_refs = subset_failure_source_refs(failures)
    replay_corpus = {
        "schema_version": "codex-dr.deepresearch_bench_subset_replay_corpus.v1",
        "suite_id": suite_id,
        "source_summary": "deepresearch_bench_subset_pressure_summary.json",
        "source_improvement_inputs": "subset_improvement_inputs.json",
        "fixtures": [
            {
                "fixture_id": "fixture_subset_reentry_schema_failure_001",
                "kind": "failed_live_subset_case",
                "input_artifacts": [
                    "deepresearch_bench_subset_pressure_summary.json",
                    "deepresearch_bench_subset_raw_reports_custody.json",
                ],
                "failure_classes": ["suite_validation_failed", "output_schema"],
                "failure_summary": (
                    "A live re-entry branch completed but its evidence rows used "
                    "`status` where the schema requires `admission_status`."
                ),
                "expected_gate": "schema_repair_required_before_more_live_subset_runs",
            },
            {
                "fixture_id": "fixture_subset_adequacy_backpressure_queue_001",
                "kind": "failed_live_subset_case",
                "input_artifacts": [
                    "deepresearch_bench_subset_pressure_summary.json",
                    "deepresearch_bench_subset_raw_reports_custody.json",
                ],
                "failure_classes": [
                    "suite_validation_failed",
                    "adequacy_backpressure",
                ],
                "failure_summary": (
                    "A live case retained an unresolved adequacy gap without "
                    "writing the required backpressure queue artifact."
                ),
                "expected_gate": "backpressure_queue_required_before_more_live_subset_runs",
            },
            {
                "fixture_id": "fixture_subset_open_backpressure_followup_001",
                "kind": "lawful_blocked_live_subset_case",
                "input_artifacts": [
                    "deepresearch_bench_subset_pressure_summary.json",
                    "deepresearch_bench_subset_raw_reports_custody.json",
                    "backpressure/adequacy_backpressure_queue.json",
                ],
                "failure_classes": [
                    "adequacy_backpressure_open",
                    "recursive_reentry",
                ],
                "failure_summary": (
                    "A live case lawfully stopped before the writer because the "
                    "open adequacy queue required one more narrow re-entry pass."
                ),
                "expected_gate": "recursive_reentry_required_before_full_run_gate",
            },
            {
                "fixture_id": "fixture_subset_scorer_blocked_001",
                "kind": "blocked_evaluator",
                "input_artifacts": [
                    "race_bridge/race_bridge_receipt.json",
                    "benchmark_suite_claim_review.json",
                ],
                "failure_classes": ["scorer_blocked", "claim_boundary"],
                "failure_summary": (
                    "The official RACE scorer remains blocked without provider key "
                    "and explicit provider-run approval."
                ),
                "expected_gate": "claims_remain_blocked",
            },
        ],
        "produced_at": FIXTURE_TIMESTAMP,
    }
    candidates = subset_improvement_candidate_payloads(source_refs)
    write_json(out_dir / "failure_taxonomy.json", {
        "schema_version": "codex-dr.deepresearch_bench_subset_failure_taxonomy.v1",
        "suite_id": suite_id,
        "failure_classes": failures,
        "source_validation": "deepresearch_bench_subset_pressure_validation.json",
        "produced_at": FIXTURE_TIMESTAMP,
    })
    write_json(out_dir / "replay_corpus.json", replay_corpus)
    write_json(
        out_dir / "improvement_candidates.json",
        {
            "schema_version": "codex-dr.deepresearch_bench_subset_candidates.v1",
            "suite_id": suite_id,
            "candidate_set_id": "drb_subset_improvement_candidates_001",
            "source_failure_count": len(source_refs),
            "candidate_count": len(candidates),
            "candidates": candidates,
            "claim_boundary": {
                "may_widen_claims": False,
                "blocked_claims": summary.get("claim_boundary", {}).get("blocked_claims", []),
            },
            "produced_at": FIXTURE_TIMESTAMP,
        },
    )
    gate_results = []
    for candidate in candidates:
        candidate_id = candidate["candidate_id"]
        candidate_dir = isolated_dir / candidate_id
        candidate_dir.mkdir(parents=True, exist_ok=True)
        patch_preview = candidate_dir / "patch_preview.json"
        replay_result = candidate_dir / "replay_result.json"
        receipt = receipts_dir / f"{candidate_id}.json"
        checks = subset_candidate_checks(candidate, replay_corpus, claim_review, validation)
        checks_passed = all(check["status"] == "passed" for check in checks)
        write_json(
            patch_preview,
            {
                "schema_version": "codex-dr.subset_candidate_patch_preview.v1",
                "suite_id": suite_id,
                "candidate_id": candidate_id,
                "target_surface_type": candidate["target_surface_type"],
                "target_surface": candidate["target_surface"],
                "proposed_change": candidate["proposed_change"],
                "isolated_only": True,
                "live_surface_changed": False,
                "produced_at": FIXTURE_TIMESTAMP,
            },
        )
        write_json(
            replay_result,
            {
                "schema_version": "codex-dr.subset_candidate_replay_result.v1",
                "suite_id": suite_id,
                "candidate_id": candidate_id,
                "checks": checks,
                "passed": checks_passed,
                "produced_at": FIXTURE_TIMESTAMP,
            },
        )
        write_json(
            receipt,
            {
                "schema_version": "codex-dr.subset_candidate_promotion_receipt.v1",
                "suite_id": suite_id,
                "candidate_id": candidate_id,
                "decision": "gate_passed_not_promoted" if checks_passed else "blocked",
                "promotion_status": "not_promoted",
                "live_surface_changed": False,
                "patch_preview": rel(patch_preview, suite_dir),
                "replay_result": rel(replay_result, suite_dir),
                "claim_impact": "no claim widening",
                "produced_at": FIXTURE_TIMESTAMP,
            },
        )
        gate_results.append(
            {
                "candidate_id": candidate_id,
                "target_surface_type": candidate["target_surface_type"],
                "decision": "gate_passed_not_promoted" if checks_passed else "blocked",
                "checks_passed": checks_passed,
                "live_surface_changed": False,
                "patch_preview": rel(patch_preview, suite_dir),
                "replay_result": rel(replay_result, suite_dir),
                "promotion_receipt": rel(receipt, suite_dir),
            }
        )
    selected = select_next_subset_candidate(candidates, gate_results)
    next_action = subset_next_action_for_candidate(selected)
    write_json(
        out_dir / "candidate_gate_results.json",
        {
            "schema_version": "codex-dr.deepresearch_bench_subset_candidate_gate_results.v1",
            "suite_id": suite_id,
            "candidate_count": len(candidates),
            "results": gate_results,
            "all_candidates_gated": len(gate_results) == len(candidates),
            "live_surface_changed": False,
            "claim_boundary": {
                "may_widen_claims": False,
                "blocked_claims": summary.get("claim_boundary", {}).get("blocked_claims", []),
            },
            "produced_at": FIXTURE_TIMESTAMP,
        },
    )
    write_json(
        out_dir / "next_flywheel_plan.json",
        {
            "schema_version": "codex-dr.deepresearch_bench_subset_next_flywheel_plan.v1",
            "suite_id": suite_id,
            "status": next_action["status"],
            "selected_candidate": selected,
            "source_artifacts": {
                "subset_summary": "deepresearch_bench_subset_pressure_summary.json",
                "subset_improvement_inputs": "subset_improvement_inputs.json",
                "raw_report_custody": "deepresearch_bench_subset_raw_reports_custody.json",
                "suite_claim_review": "benchmark_suite_claim_review.json",
            },
            "next_action": next_action["next_action"],
            "live_subset_state": {
                "selected_case_count": summary.get("case_count"),
                "raw_export_case_count": summary.get("raw_report_export", {}).get("case_count"),
                "contains_validation_failures": raw_custody.get(
                    "contains_validation_failures"
                ),
            },
            "claim_boundary": {
                "may_claim_deepresearch_bench_score": False,
                "may_claim_grep_parity": False,
                "may_claim_leaderboard_rank": False,
                "may_claim_product_readiness": False,
                "blocked_claims": summary.get("claim_boundary", {}).get("blocked_claims", []),
            },
            "produced_at": FIXTURE_TIMESTAMP,
        },
    )
    validation_payload = validate_deepresearch_bench_subset_improvement(out_dir)
    write_json(out_dir / "subset_improvement_validation.json", validation_payload)
    if validation_payload["status"] != "passed":
        raise HarnessError(
            "DeepResearch Bench subset improvement compile failed validation: "
            + "; ".join(validation_payload["failed_checks"])
        )
    return out_dir


def subset_failure_source_refs(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs = []
    for index, failure in enumerate(failures, start=1):
        refs.append(
            {
                "source_kind": "subset.failure_taxonomy",
                "failure_id": failure.get("failure_class") or f"subset_failure_{index}",
                "failure_class": failure.get("failure_class", "subset_pressure"),
                "severity": failure.get("severity", "unknown"),
                "summary": failure.get("root_cause", "Subset failure requires review."),
                "affected_cases": failure.get("affected_cases", []),
            }
        )
    return refs


def subset_improvement_candidate_payloads(
    source_refs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    schema_refs = refs_matching_summary(
        source_refs,
        {
            "branch_triplets_present",
            "admission_status",
            "unknown evidence statuses",
            "`status`",
        },
    )
    adequacy_refs = refs_matching_summary(
        source_refs,
        {"adequacy_backpressure_queue_present", "adequacy_backpressure"},
    )
    open_backpressure_refs = refs_for_classes(
        source_refs,
        {"adequacy_backpressure_open"},
    )
    scorer_refs = refs_for_classes(source_refs, {"scorer_blocked"})
    shared_gate = {
        "requires_replay_fixture": True,
        "requires_claim_review": True,
        "promotion_decision": "manual_or_next_bead_only",
    }
    return [
        {
            "candidate_id": "cand_drb_open_backpressure_reentry_001",
            "target_surface_type": "control_flow",
            "target_surface": (
                "sandbox/codex-dr/tools/alexandria_dr.py::mesh_execute_live"
            ),
            "failure_classes": ["adequacy_backpressure_open", "recursive_reentry"],
            "source_failure_refs": open_backpressure_refs,
            "proposed_change": (
                "When re-entry synthesis leaves an open adequacy queue, compile the "
                "queue item into a bounded additional re-entry task before the final "
                "writer gate is considered again."
            ),
            "expected_effect": (
                "The mesh behaves like the Grep inner loop: unresolved gaps spawn "
                "more focused research instead of stopping at a single re-entry pass."
            ),
            "replay_fixtures": ["fixture_subset_open_backpressure_followup_001"],
            "promotion_gate": shared_gate,
            "promotion_status": "proposed_not_promoted",
            "claim_impact": "no claim widening",
        },
        {
            "candidate_id": "cand_drb_adequacy_backpressure_queue_001",
            "target_surface_type": "control_flow",
            "target_surface": (
                "sandbox/codex-dr/tools/alexandria_dr.py::"
                "check_adequacy_backpressure_queue"
            ),
            "failure_classes": ["suite_validation_failed", "adequacy_backpressure"],
            "source_failure_refs": adequacy_refs,
            "proposed_change": (
                "When live synthesis or review leaves an unresolved adequacy gap, "
                "write `backpressure/adequacy_backpressure_queue.json` with the "
                "specific follow-up task before the writer is treated as complete."
            ),
            "expected_effect": (
                "The live mesh stops with an explicit follow-up queue instead of "
                "shipping a report with unresolved adequacy pressure hidden in prose."
            ),
            "replay_fixtures": ["fixture_subset_adequacy_backpressure_queue_001"],
            "promotion_gate": shared_gate,
            "promotion_status": "proposed_not_promoted",
            "claim_impact": "no claim widening",
        },
        {
            "candidate_id": "cand_drb_reentry_admission_status_prompt_001",
            "target_surface_type": "prompt",
            "target_surface": (
                "sandbox/codex-dr/tools/alexandria_dr.py::"
                "live_role_output_schema_notes"
            ),
            "failure_classes": ["suite_validation_failed", "output_schema"],
            "source_failure_refs": schema_refs,
            "proposed_change": (
                "Make the re-entry prompt require `admission_status` on every "
                "evidence row and explicitly forbid substituting `status`."
            ),
            "expected_effect": (
                "Live re-entry branches produce schema-valid evidence files before "
                "the subset runner spends more cases."
            ),
            "replay_fixtures": ["fixture_subset_reentry_schema_failure_001"],
            "promotion_gate": shared_gate,
            "promotion_status": "proposed_not_promoted",
            "claim_impact": "no claim widening",
        },
        {
            "candidate_id": "cand_drb_reentry_schema_preflight_001",
            "target_surface_type": "validator",
            "target_surface": "sandbox/codex-dr/tools/alexandria_dr.py::check_branch_triplets",
            "failure_classes": ["suite_validation_failed", "output_schema"],
            "source_failure_refs": schema_refs,
            "proposed_change": (
                "Add a branch-output preflight that reports missing "
                "`admission_status` fields as a repairable role-output schema "
                "failure before more live subset cases are launched."
            ),
            "expected_effect": (
                "The flywheel can stop after the first schema miss, compile a "
                "candidate, and avoid burning the rest of the subset budget."
            ),
            "replay_fixtures": ["fixture_subset_reentry_schema_failure_001"],
            "promotion_gate": shared_gate,
            "promotion_status": "proposed_not_promoted",
            "claim_impact": "no claim widening",
        },
        {
            "candidate_id": "cand_drb_scorer_authority_packet_001",
            "target_surface_type": "evaluator",
            "target_surface": (
                "sandbox/codex-dr/tools/alexandria_dr.py::"
                "deepresearch_bench_race_bridge"
            ),
            "failure_classes": ["scorer_blocked", "claim_boundary"],
            "source_failure_refs": scorer_refs,
            "proposed_change": (
                "Keep the scorer lane blocked until provider key presence, explicit "
                "provider-run approval, evaluator lane, and budget are receipted."
            ),
            "expected_effect": "Score and parity claims remain impossible without scorer custody.",
            "replay_fixtures": ["fixture_subset_scorer_blocked_001"],
            "promotion_gate": shared_gate,
            "promotion_status": "proposed_not_promoted",
            "claim_impact": "no claim widening",
        },
    ]


def subset_candidate_checks(
    candidate: dict[str, Any],
    replay_corpus: dict[str, Any],
    claim_review: dict[str, Any],
    validation: dict[str, Any],
) -> list[dict[str, str]]:
    fixture_ids = {fixture.get("fixture_id") for fixture in replay_corpus.get("fixtures", [])}
    missing_fixtures = [
        fixture
        for fixture in candidate.get("replay_fixtures", [])
        if fixture not in fixture_ids
    ]
    return [
        {
            "check_id": "source_failures_present",
            "status": "passed" if candidate.get("source_failure_refs") else "failed",
            "details": "Candidate references subset failure evidence.",
        },
        {
            "check_id": "replay_fixtures_present",
            "status": "passed" if not missing_fixtures else "failed",
            "details": ", ".join(missing_fixtures) or "Replay fixtures present.",
        },
        {
            "check_id": "claim_boundary_closed",
            "status": (
                "passed"
                if claim_review.get("may_widen_public_benchmark_claims") is False
                else "failed"
            ),
            "details": "Suite claim review keeps public claims closed.",
        },
        {
            "check_id": "subset_validation_available",
            "status": "passed" if validation.get("status") in {"passed", "failed"} else "failed",
            "details": "Subset validation receipt is available.",
        },
    ]


def select_next_subset_candidate(
    candidates: list[dict[str, Any]], gate_results: list[dict[str, Any]]
) -> dict[str, Any]:
    passed = {item["candidate_id"] for item in gate_results if item.get("checks_passed")}
    priority = {"control_flow": 0, "prompt": 1, "validator": 2, "evaluator": 3}
    candidate_priority = {
        "cand_drb_open_backpressure_reentry_001": 0,
        "cand_drb_adequacy_backpressure_queue_001": 1,
    }
    eligible = [candidate for candidate in candidates if candidate["candidate_id"] in passed]
    if not eligible:
        return {
            "candidate_id": None,
            "selection_status": "blocked_no_gated_candidate",
        }
    selected = sorted(
        eligible,
        key=lambda candidate: (
            priority.get(candidate.get("target_surface_type"), 99),
            candidate_priority.get(candidate["candidate_id"], 50),
            candidate["candidate_id"],
        ),
    )[0]
    return {**selected, "selection_status": "selected_for_next_overlay"}


def subset_next_action_for_candidate(selected: dict[str, Any]) -> dict[str, Any]:
    candidate_id = selected.get("candidate_id")
    if candidate_id == "cand_drb_open_backpressure_reentry_001":
        return {
            "status": "ready_for_recursive_reentry_repair",
            "next_action": {
                "action_id": "apply_open_backpressure_recursive_reentry_repair",
                "purpose": (
                    "Convert open adequacy queues into bounded additional re-entry "
                    "tasks so the inner loop can continue until satisfied."
                ),
                "claim_impact": "no claim widening",
            },
        }
    if candidate_id == "cand_drb_adequacy_backpressure_queue_001":
        return {
            "status": "ready_for_backpressure_queue_repair",
            "next_action": {
                "action_id": "apply_adequacy_backpressure_queue_repair",
                "purpose": (
                    "Prevent further live subset token spend until unresolved "
                    "adequacy gaps create an explicit follow-up queue artifact."
                ),
                "claim_impact": "no claim widening",
            },
        }
    if candidate_id == "cand_drb_reentry_admission_status_prompt_001":
        return {
            "status": "ready_for_schema_repair_overlay",
            "next_action": {
                "action_id": "apply_reentry_evidence_schema_overlay",
                "purpose": (
                    "Prevent further live subset token spend until re-entry evidence "
                    "rows reliably emit `admission_status` and failed schemas are "
                    "caught before writer progression."
                ),
                "claim_impact": "no claim widening",
            },
        }
    if candidate_id == "cand_drb_scorer_authority_packet_001":
        return {
            "status": "ready_for_scorer_authority_packet",
            "next_action": {
                "action_id": "prepare_scorer_authority_packet",
                "purpose": "Keep public benchmark claims blocked until scorer custody exists.",
                "claim_impact": "no claim widening",
            },
        }
    return {
        "status": "blocked_no_next_candidate",
        "next_action": {
            "action_id": "inspect_subset_failures",
            "purpose": "No gated candidate was selected.",
            "claim_impact": "no claim widening",
        },
    }


def validate_deepresearch_bench_subset_improvement(out_dir: Path) -> dict[str, Any]:
    problems = []
    try:
        taxonomy = read_json(out_dir / "failure_taxonomy.json")
        replay = read_json(out_dir / "replay_corpus.json")
        candidates = read_json(out_dir / "improvement_candidates.json")
        gates = read_json(out_dir / "candidate_gate_results.json")
        plan = read_json(out_dir / "next_flywheel_plan.json")
    except (FileNotFoundError, json.JSONDecodeError) as error:
        problems.append(f"subset improvement artifacts unavailable: {error}")
        return {
            "schema_version": "codex-dr.deepresearch_bench_subset_improvement_validation.v1",
            "status": "failed",
            "failed_checks": problems,
        }
    if not taxonomy.get("failure_classes"):
        problems.append("failure taxonomy is empty")
    if not replay.get("fixtures"):
        problems.append("replay corpus is empty")
    if candidates.get("candidate_count") != len(candidates.get("candidates", [])):
        problems.append("candidate count mismatch")
    if gates.get("all_candidates_gated") is not True:
        problems.append("not all candidates gated")
    if gates.get("live_surface_changed") is not False:
        problems.append("candidate gates changed live surfaces")
    if plan.get("claim_boundary", {}).get("may_claim_grep_parity") is not False:
        problems.append("next flywheel plan widened parity claims")
    if not plan.get("selected_candidate", {}).get("candidate_id"):
        problems.append("next flywheel plan did not select a candidate")
    status = "failed" if problems else "passed"
    return {
        "schema_version": "codex-dr.deepresearch_bench_subset_improvement_validation.v1",
        "status": status,
        "failed_checks": problems,
        "candidate_count": candidates.get("candidate_count"),
        "selected_candidate_id": plan.get("selected_candidate", {}).get("candidate_id"),
    }


def count_jsonl_rows(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def validate_deepresearch_bench_subset_pressure(
    suite_id: str,
    *,
    runs_dir: Path | str | None = None,
) -> dict[str, Any]:
    runs_root = Path(runs_dir or DEFAULT_RUNS_DIR)
    suite_dir = runs_root / suite_id
    problems = []
    try:
        suite_manifest = read_json(suite_dir / "benchmark_suite_manifest.json")
        subset_summary = read_json(
            suite_dir / "deepresearch_bench_subset_pressure_summary.json"
        )
        suite_claim = read_json(suite_dir / "benchmark_suite_claim_review.json")
        improvement_inputs = read_json(suite_dir / "subset_improvement_inputs.json")
    except (FileNotFoundError, json.JSONDecodeError) as error:
        problems.append(f"subset artifacts unavailable: {error}")
        return {
            "schema_version": "codex-dr.deepresearch_bench_subset_pressure_validation.v1",
            "suite_id": suite_id,
            "status": "failed",
            "failed_checks": problems,
        }
    if suite_manifest.get("benchmark_family") != BENCHMARK_FAMILY_DEEPRESEARCH_BENCH:
        problems.append("suite is not DeepResearch Bench")
    if subset_summary.get("case_count", 0) < 2:
        problems.append("subset has fewer than two cases")
    selected_ids = set(
        subset_summary.get("case_selection_policy", {}).get("selected_run_ids", [])
    )
    manifest_ids = {case.get("run_id") for case in suite_manifest.get("cases", [])}
    if not selected_ids or not selected_ids.issubset(manifest_ids):
        problems.append("selected cases are not recorded in suite manifest")
    raw_export = subset_summary.get("raw_report_export", {})
    if raw_export.get("case_count") != subset_summary.get("case_count"):
        problems.append("raw report export case count mismatch")
    raw_path_value = raw_export.get("path")
    raw_path = Path(raw_path_value) if raw_path_value else None
    if not raw_path or not raw_path.exists():
        problems.append("raw report export missing")
    elif count_jsonl_rows(raw_path) != subset_summary.get("case_count"):
        problems.append("raw report export row count does not match selected cases")
    if not (suite_dir / "race_bridge" / "race_bridge_receipt.json").exists():
        problems.append("race bridge receipt missing")
    scorer_status = subset_summary.get("race_bridge", {}).get("status")
    if scorer_status == "blocked" and not any(
        failure.get("failure_class") == "scorer_blocked"
        for failure in subset_summary.get("failure_taxonomy", [])
    ):
        problems.append("blocked scorer is not recorded in failure taxonomy")
    if suite_claim.get("may_widen_public_benchmark_claims") is not False:
        problems.append("suite claim review widened claims")
    if not improvement_inputs.get("candidate_inputs"):
        problems.append("subset improvement inputs missing")
    status = "failed" if problems else "passed"
    return {
        "schema_version": "codex-dr.deepresearch_bench_subset_pressure_validation.v1",
        "suite_id": suite_id,
        "status": status,
        "case_count": subset_summary.get("case_count"),
        "failed_checks": problems,
        "claim_boundary": subset_summary.get("claim_boundary", {}),
    }


def deepresearch_bench_full_run_package(
    package_id: str,
    *,
    query_jsonl: Path,
    source_refresh: Path,
    subset_summary: Path,
    official_repo: Path,
    output_dir: Path,
) -> Path:
    validate_id(package_id, "package_id")
    source = read_json(source_refresh)
    if source.get("schema_version") != "codex-dr.deepresearch_bench_source_refresh.v1":
        raise HarnessError("source refresh is not a DeepResearch Bench receipt")
    query_rows = read_jsonl(query_jsonl)
    subset = read_json(subset_summary)
    repo_probe = probe_deepresearch_bench_official_race_repo(official_repo)
    output_dir.mkdir(parents=True, exist_ok=True)
    package = deepresearch_bench_full_run_package_payload(
        package_id=package_id,
        query_jsonl=query_jsonl,
        query_rows=query_rows,
        source=source,
        source_refresh=source_refresh,
        subset=subset,
        subset_summary=subset_summary,
        repo_probe=repo_probe,
    )
    write_json(output_dir / "full_run_package.json", package)
    write_json(
        output_dir / "grep_comparison_gate.json",
        deepresearch_bench_grep_comparison_gate_payload(package),
    )
    write_json(
        output_dir / "official_submission_prerequisites.json",
        deepresearch_bench_submission_prerequisites_payload(package),
    )
    validation = validate_deepresearch_bench_full_run_package(output_dir)
    write_json(output_dir / "full_run_package_validation.json", validation)
    if validation["status"] != "passed":
        raise HarnessError(
            "DeepResearch Bench full-run package failed validation: "
            + "; ".join(validation["failed_checks"])
        )
    return output_dir


def deepresearch_bench_full_run_package_payload(
    *,
    package_id: str,
    query_jsonl: Path,
    query_rows: list[dict[str, Any]],
    source: dict[str, Any],
    source_refresh: Path,
    subset: dict[str, Any],
    subset_summary: Path,
    repo_probe: dict[str, Any],
) -> dict[str, Any]:
    query_count = len(query_rows)
    scorer_missing = [
        "GEMINI_API_KEY",
        "explicit --allow-provider-run",
        "full 100-case run-control budget",
    ]
    grep_target = current_grep_target_from_source_refresh(source)
    return {
        "schema_version": "codex-dr.deepresearch_bench_full_run_package.v1",
        "package_id": package_id,
        "status": "blocked_before_full_execution",
        "benchmark_family": BENCHMARK_FAMILY_DEEPRESEARCH_BENCH,
        "full_case_contract": {
            "required_case_count": 100,
            "observed_query_count": query_count,
            "query_jsonl": query_jsonl.as_posix(),
            "query_jsonl_sha256": sha256_file(query_jsonl),
            "all_cases_present": query_count == 100,
        },
        "source_refresh": {
            "path": source_refresh.as_posix(),
            "official_repository": source.get("official_repository", {}),
            "official_dataset": source.get("official_dataset", {}),
            "official_leaderboard": source.get("official_leaderboard", {}),
            "evaluator_lane": source.get("evaluator_lane", {}),
        },
        "current_grep_target": grep_target,
        "official_scorer": {
            **repo_probe,
            "scorer_requirements": scorer_missing,
            "scorer_status": "blocked_before_provider_execution",
        },
        "subset_evidence": {
            "summary_path": subset_summary.as_posix(),
            "suite_id": subset.get("suite_id"),
            "case_count": subset.get("case_count"),
            "aggregate_result": subset.get("aggregate_result"),
            "failure_taxonomy": subset.get("failure_taxonomy", []),
        },
        "full_run_execution_plan": {
            "case_manifest_command": (
                "alexandria-dr deepresearch-bench-case-manifest --limit 100"
            ),
            "mesh_execution_requirement": (
                "Run all 100 sealed cases through the same DR mesh path with "
                "transcript, event, raw report, and claim custody."
            ),
            "raw_report_export_requirement": (
                "Export exactly 100 official-format rows: id, prompt, article."
            ),
            "scoring_requirement": (
                "Run official RACE scorer with evaluator-lane lock and provider "
                "authority, or emit a blocked scorer receipt."
            ),
        },
        "variance_policy": {
            "best_of_n_allowed": False,
            "repeat_scoring_required_for_public_claim": True,
            "lane_mixing_allowed": False,
            "comparison_rule": (
                "Compare Alexandria only to Grep-v5 on the same evaluator lane and "
                "fresh leaderboard snapshot."
            ),
        },
        "claim_boundary": {
            "may_claim_deepresearch_bench_score": False,
            "may_claim_grep_parity": False,
            "may_claim_leaderboard_rank": False,
            "may_claim_product_readiness": False,
            "blocked_claims": [
                "DeepResearch Bench score",
                "Grep parity",
                "leaderboard rank",
                "product readiness",
                "official benchmark submission",
            ],
        },
        "empirical_gap": {
            "gap_status": "full_run_not_executed",
            "missing_requirements": scorer_missing,
            "next_loop": [
                "obtain scorer authority and budget",
                "materialize all 100 case manifests",
                "run full mesh",
                "export 100 raw reports",
                "score or block official scorer",
                "run claim review against current Grep target",
            ],
        },
        "produced_at": FIXTURE_TIMESTAMP,
    }


def deepresearch_bench_grep_comparison_gate_payload(
    package: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "codex-dr.deepresearch_bench_grep_comparison_gate.v1",
        "package_id": package["package_id"],
        "decision": "blocked_full_run_not_scored",
        "may_claim_parity": False,
        "current_grep_target": package.get("current_grep_target", {}),
        "required_before_open": [
            "100 generated reports",
            "official scorer custody",
            "aggregate score",
            "same evaluator lane as Grep target",
            "fresh leaderboard snapshot",
            "suite-level claim review",
        ],
        "blocked_claims": package.get("claim_boundary", {}).get("blocked_claims", []),
        "produced_at": FIXTURE_TIMESTAMP,
    }


def deepresearch_bench_submission_prerequisites_payload(
    package: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "codex-dr.deepresearch_bench_submission_prerequisites.v1",
        "package_id": package["package_id"],
        "submission_status": "not_ready",
        "required_artifacts": [
            "full_run_package.json",
            "100-row raw generated report JSONL",
            "official scorer outputs",
            "aggregate metrics",
            "claim review",
            "fresh source refresh",
        ],
        "external_actions": [
            "Principal/account owner performs any official leaderboard submission.",
            "Refresh evaluator policy before submission.",
        ],
        "blocked_reason": "Full scored run has not been executed.",
        "produced_at": FIXTURE_TIMESTAMP,
    }


def validate_deepresearch_bench_full_run_package(package_dir: Path) -> dict[str, Any]:
    problems = []
    try:
        package = read_json(package_dir / "full_run_package.json")
        comparison = read_json(package_dir / "grep_comparison_gate.json")
        prerequisites = read_json(package_dir / "official_submission_prerequisites.json")
    except (FileNotFoundError, json.JSONDecodeError) as error:
        problems.append(f"full-run package artifacts unavailable: {error}")
        return {
            "schema_version": "codex-dr.deepresearch_bench_full_run_validation.v1",
            "status": "failed",
            "failed_checks": problems,
        }
    if package.get("schema_version") != "codex-dr.deepresearch_bench_full_run_package.v1":
        problems.append("invalid full-run package schema_version")
    full_case_contract = package.get("full_case_contract", {})
    if full_case_contract.get("required_case_count") != 100:
        problems.append("full-run package does not require 100 cases")
    if full_case_contract.get("observed_query_count") != 100:
        problems.append("full-run package lacks all 100 query rows")
    if not package.get("source_refresh", {}).get("evaluator_lane"):
        problems.append("full-run package lacks evaluator lane")
    if package.get("current_grep_target", {}).get("overall_score") is None:
        problems.append("full-run package lacks current Grep target score")
    if not package.get("official_scorer", {}).get("script"):
        problems.append("full-run package lacks official scorer script")
    if not package.get("variance_policy"):
        problems.append("full-run package lacks variance policy")
    if comparison.get("may_claim_parity") is not False:
        problems.append("comparison gate opened parity without scored evidence")
    if prerequisites.get("submission_status") != "not_ready":
        problems.append("submission prerequisites incorrectly mark package ready")
    blocked = set(package.get("claim_boundary", {}).get("blocked_claims", []))
    if not {"DeepResearch Bench score", "Grep parity", "leaderboard rank"} <= blocked:
        problems.append("full-run package did not block score/parity/leaderboard claims")
    status = "failed" if problems else "passed"
    return {
        "schema_version": "codex-dr.deepresearch_bench_full_run_validation.v1",
        "status": status,
        "failed_checks": problems,
        "package_id": package.get("package_id"),
        "claim_boundary": package.get("claim_boundary", {}),
    }


def deepresearch_bench_score_control_packet(
    packet_id: str,
    *,
    full_run_package: Path,
    prompt_overlay: Path,
    output_dir: Path,
    repair_run_id: str | None = None,
    runs_dir: Path | str | None = None,
) -> Path:
    validate_id(packet_id, "packet_id")
    output_dir.mkdir(parents=True, exist_ok=True)
    package = read_json(full_run_package)
    overlay = read_validated_prompt_overlay(prompt_overlay)
    repair_validation = (
        validate_run(repair_run_id, runs_dir=runs_dir) if repair_run_id else None
    )
    packet = deepresearch_bench_score_control_packet_payload(
        packet_id=packet_id,
        full_run_package=full_run_package,
        package=package,
        prompt_overlay=prompt_overlay,
        overlay=overlay,
        repair_run_id=repair_run_id,
        repair_validation=repair_validation,
    )
    write_json(output_dir / "score_control_packet.json", packet)
    validation = validate_deepresearch_bench_score_control_packet(output_dir)
    write_json(output_dir / "score_control_packet_validation.json", validation)
    if validation["status"] != "passed":
        raise HarnessError(
            "DeepResearch Bench score-control packet failed validation: "
            + "; ".join(validation["failed_checks"])
        )
    return output_dir


def deepresearch_bench_score_control_packet_payload(
    *,
    packet_id: str,
    full_run_package: Path,
    package: dict[str, Any],
    prompt_overlay: Path,
    overlay: dict[str, Any],
    repair_run_id: str | None,
    repair_validation: dict[str, Any] | None,
) -> dict[str, Any]:
    claim_boundary = package.get("claim_boundary", {})
    scorer = package.get("official_scorer", {})
    source = package.get("source_refresh", {})
    full_case_contract = package.get("full_case_contract", {})
    raw_report_location = (
        "sandbox/codex-dr/tmp/deepresearch_bench_full_run_2026_04_24/"
        "raw_generated_reports.jsonl"
    )
    scorer_output_location = (
        "sandbox/codex-dr/tmp/deepresearch_bench_full_run_2026_04_24/"
        "race_bridge/"
    )
    return {
        "schema_version": "codex-dr.deepresearch_bench_score_control_packet.v1",
        "packet_id": packet_id,
        "status": "blocked_before_score_bearing_execution",
        "full_run_package": artifact_ref(full_run_package),
        "prompt_overlay": {
            **artifact_ref(prompt_overlay),
            "candidate_id": overlay.get("candidate_id"),
            "candidate_chain": overlay.get("candidate_chain", []),
            "live_surface_changed": overlay.get("live_surface_changed"),
        },
        "evaluator_lane": source.get("evaluator_lane", {}),
        "official_repo": {
            "repository": scorer.get("repository"),
            "commit": scorer.get("commit"),
            "script": scorer.get("script"),
            "required_paths": scorer.get("required_paths", []),
        },
        "dataset_revision": {
            "dataset_id": source.get("official_dataset", {}).get("dataset_id"),
            "revision_sha": source.get("official_dataset", {}).get("revision_sha"),
            "query_jsonl_sha256": full_case_contract.get("query_jsonl_sha256"),
            "required_case_count": full_case_contract.get("required_case_count"),
            "observed_query_count": full_case_contract.get("observed_query_count"),
        },
        "leaderboard_snapshot": {
            "observed_at": package.get("current_grep_target", {}).get("observed_at"),
            "grep_target": package.get("current_grep_target", {}),
            "leaderboard": source.get("official_leaderboard", {}),
        },
        "provider_authority": {
            "status": "blocked",
            "missing_requirements": scorer.get("scorer_requirements", []),
            "allow_provider_run_required": True,
            "gemini_api_key_required": True,
        },
        "budget": {
            "status": "not_approved",
            "case_count": 100,
            "max_live_attempts_per_case": 1,
            "automatic_retry_allowed": False,
            "estimated_provider_cost": "not_estimated_in_packet_provider_run_blocked",
            "requires_principal_budget_approval": True,
        },
        "command_plan": [
            {
                "step": "materialize_case_manifest",
                "command": (
                    "alexandria-dr deepresearch-bench-case-manifest --limit 100 "
                    "--query-jsonl <official query.jsonl> --source-refresh <fresh receipt>"
                ),
            },
            {
                "step": "bootstrap_suite",
                "command": (
                    "alexandria-dr multi-case-from-manifest <suite_id> "
                    "--manifest <100-case manifest>"
                ),
            },
            {
                "step": "plan_live_mesh",
                "command": (
                    "alexandria-dr mesh-live-plan <case_id> --run-control <receipt> "
                    "--prompt-overlay <composite overlay>"
                ),
            },
            {
                "step": "execute_live_mesh",
                "command": "alexandria-dr mesh-execute-live <case_id> --run-control <receipt>",
            },
            {
                "step": "export_raw_reports",
                "command": "alexandria-dr deepresearch-bench-report-export <100 case ids>",
                "output": raw_report_location,
            },
            {
                "step": "score_or_block",
                "command": (
                    "alexandria-dr deepresearch-bench-race-bridge --allow-provider-run "
                    "--raw-reports <100-row JSONL>"
                ),
                "output": scorer_output_location,
            },
            {
                "step": "claim_review",
                "command": "alexandria-dr deepresearch-bench-claim-review <full suite>",
            },
        ],
        "kill_path": {
            "foreground": "send SIGINT to the active mesh-execute-live process, then SIGTERM",
            "resume_policy": "resume only from completed run bundles with validation receipts",
            "automatic_retry_allowed": False,
        },
        "output_locations": {
            "raw_report_jsonl": raw_report_location,
            "scorer_output_dir": scorer_output_location,
            "claim_review": (
                "sandbox/codex-dr/tmp/deepresearch_bench_full_run_2026_04_24/"
                "full_suite_claim_review.json"
            ),
        },
        "variance_policy": package.get("variance_policy", {}),
        "repair_proof": {
            "repair_run_id": repair_run_id,
            "validation_status": (
                repair_validation.get("status") if repair_validation else "not_provided"
            ),
            "failed_checks": repair_validation.get("failed_checks", [])
            if repair_validation
            else [],
        },
        "claim_review": {
            "status": "blocked_until_full_scorer_custody",
            "may_widen_public_benchmark_claims": False,
            "required_before_claim_change": [
                "100 generated reports",
                "official scorer output",
                "same evaluator lane as Grep target",
                "fresh leaderboard snapshot",
                "suite-level claim review",
            ],
        },
        "claim_boundary": claim_boundary,
        "produced_at": FIXTURE_TIMESTAMP,
    }


def validate_deepresearch_bench_score_control_packet(packet_dir: Path) -> dict[str, Any]:
    problems = []
    try:
        packet = read_json(packet_dir / "score_control_packet.json")
    except (FileNotFoundError, json.JSONDecodeError) as error:
        problems.append(f"score-control packet unavailable: {error}")
        return {
            "schema_version": "codex-dr.deepresearch_bench_score_control_validation.v1",
            "status": "failed",
            "failed_checks": problems,
        }
    if packet.get("schema_version") != "codex-dr.deepresearch_bench_score_control_packet.v1":
        problems.append("invalid score-control packet schema_version")
    if not packet.get("evaluator_lane"):
        problems.append("score-control packet lacks evaluator lane")
    if not packet.get("official_repo", {}).get("commit"):
        problems.append("score-control packet lacks official repo commit")
    if not packet.get("dataset_revision", {}).get("revision_sha"):
        problems.append("score-control packet lacks dataset revision")
    if packet.get("provider_authority", {}).get("status") != "blocked":
        problems.append("score-control packet did not block provider authority")
    if packet.get("budget", {}).get("status") != "not_approved":
        problems.append("score-control packet did not block budget")
    if len(packet.get("command_plan", [])) < 6:
        problems.append("score-control packet lacks full command plan")
    if not packet.get("kill_path"):
        problems.append("score-control packet lacks kill path")
    outputs = packet.get("output_locations", {})
    if not outputs.get("raw_report_jsonl") or not outputs.get("scorer_output_dir"):
        problems.append("score-control packet lacks output locations")
    if not packet.get("variance_policy"):
        problems.append("score-control packet lacks variance policy")
    if packet.get("claim_review", {}).get("may_widen_public_benchmark_claims") is not False:
        problems.append("score-control packet claim review can widen claims")
    blocked = set(packet.get("claim_boundary", {}).get("blocked_claims", []))
    if not {
        "DeepResearch Bench score",
        "Grep parity",
        "leaderboard rank",
        "product readiness",
        "official benchmark submission",
    } <= blocked:
        problems.append("score-control packet lacks required blocked claims")
    if packet.get("repair_proof", {}).get("validation_status") not in {
        "passed",
        "not_provided",
    }:
        problems.append("score-control packet references failed repair proof")
    status = "failed" if problems else "passed"
    return {
        "schema_version": "codex-dr.deepresearch_bench_score_control_validation.v1",
        "status": status,
        "failed_checks": problems,
        "packet_id": packet.get("packet_id"),
        "claim_boundary": packet.get("claim_boundary", {}),
    }


def deepresearch_bench_flywheel_plan(
    plan_id: str,
    *,
    case_id: str,
    subset_summary: Path,
    full_run_package: Path,
    output_dir: Path,
    runs_dir: Path | str | None = None,
) -> Path:
    validate_id(plan_id, "plan_id")
    run_dir = run_path(case_id, runs_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    case_manifest = read_optional_json(run_dir / "case_manifest.json")
    benchmark_score = read_optional_json(run_dir / "benchmark_score.json")
    claim_review = read_optional_json(run_dir / "claim_review.json")
    allowed_claims = read_optional_json(run_dir / "allowed_claims.json")
    evaluation_ledger = read_optional_json(run_dir / "evaluation_ledger.json")
    candidates = read_optional_json(
        run_dir / "self_improvement" / "improvement_candidates.json"
    )
    gate_results = read_optional_json(
        run_dir / "self_improvement" / "candidate_gate_results.json"
    )
    regression_gate = read_optional_json(
        run_dir / "self_improvement" / "regression_gate.json"
    )
    subset = read_json(subset_summary)
    package = read_json(full_run_package)
    plan = deepresearch_bench_flywheel_plan_payload(
        plan_id=plan_id,
        case_id=case_id,
        run_dir=run_dir,
        subset_summary=subset_summary,
        full_run_package=full_run_package,
        case_manifest=case_manifest,
        benchmark_score=benchmark_score,
        claim_review=claim_review,
        allowed_claims=allowed_claims,
        evaluation_ledger=evaluation_ledger,
        candidates_payload=candidates,
        gate_results=gate_results,
        regression_gate=regression_gate,
        subset=subset,
        package=package,
    )
    write_json(output_dir / "flywheel_next_action_plan.json", plan)
    write_text(
        output_dir / "architect_work_packet.md",
        deepresearch_bench_flywheel_work_packet(plan),
    )
    validation = validate_deepresearch_bench_flywheel_plan(output_dir)
    write_json(output_dir / "flywheel_next_action_validation.json", validation)
    if validation["status"] != "passed":
        raise HarnessError(
            "DeepResearch Bench flywheel plan failed validation: "
            + "; ".join(validation["failed_checks"])
        )
    return output_dir


def deepresearch_bench_flywheel_plan_payload(
    *,
    plan_id: str,
    case_id: str,
    run_dir: Path,
    subset_summary: Path,
    full_run_package: Path,
    case_manifest: dict[str, Any],
    benchmark_score: dict[str, Any],
    claim_review: dict[str, Any],
    allowed_claims: dict[str, Any],
    evaluation_ledger: dict[str, Any],
    candidates_payload: dict[str, Any],
    gate_results: dict[str, Any],
    regression_gate: dict[str, Any],
    subset: dict[str, Any],
    package: dict[str, Any],
) -> dict[str, Any]:
    candidate_results = gate_results.get("results", [])
    gated_by_id = {
        item.get("candidate_id"): item for item in candidate_results if item.get("candidate_id")
    }
    candidates = candidates_payload.get("candidates", [])
    selected_candidate = select_next_deepresearch_bench_candidate(candidates, gated_by_id)
    blocked_claims = sorted(
        set(allowed_claims.get("blocked_claims", []))
        | set(package.get("claim_boundary", {}).get("blocked_claims", []))
        | {"DeepResearch Bench score", "Grep parity", "leaderboard rank", "product readiness"}
    )
    scorer_missing = package.get("empirical_gap", {}).get("missing_requirements", [])
    score_status = package.get("official_scorer", {}).get(
        "scorer_status", "blocked_before_provider_execution"
    )
    candidate_action = deepresearch_bench_candidate_next_action(selected_candidate)
    next_actions = [
        {
            "action_id": "resolve_scorer_authority_run_control",
            "action_type": "run_control",
            "status": "blocked_external_authority",
            "purpose": (
                "Move from blocked official RACE receipt to score-bearing custody "
                "only after explicit provider authority and budget exist."
            ),
            "missing_requirements": scorer_missing,
            "commands": [
                "alexandria-dr deepresearch-bench-race-bridge --allow-provider-run",
                "alexandria-dr deepresearch-bench-claim-review",
            ],
            "claim_impact": "no claim widening until scorer output and claim review pass",
        },
        candidate_action,
        {
            "action_id": "rerun_subset_pressure_after_candidate_overlay",
            "action_type": "benchmark_pressure",
            "status": "waiting_on_candidate_overlay",
            "purpose": (
                "Run a multi-case DeepResearch Bench subset after the selected prompt, "
                "skill, scheduler, or file-context overlay has a promotion receipt."
            ),
            "commands": [
                "alexandria-dr deepresearch-bench-case-manifest --limit 5",
                "alexandria-dr multi-case-from-manifest",
                "alexandria-dr deepresearch-bench-subset-pressure",
            ],
            "acceptance": [
                "every selected case has raw report export custody",
                "subset claim review blocks score and parity claims without scorer output",
                "subset failures compile into the next improvement input set",
            ],
            "claim_impact": "no claim widening",
        },
        {
            "action_id": "prepare_full_100_case_run_control_packet",
            "action_type": "full_run_readiness",
            "status": package.get("status", "unknown"),
            "purpose": (
                "Turn the full-run package into an executable run-control packet once "
                "scorer authority, budget, and operator approval are present."
            ),
            "commands": package.get("full_run_execution_plan", {}),
            "claim_impact": "no claim widening",
        },
    ]
    return {
        "schema_version": "codex-dr.deepresearch_bench_flywheel_plan.v1",
        "plan_id": plan_id,
        "status": "ready_for_next_improvement_loop",
        "completion_object": (
            "Codex-CLI native DeepResearch mesh flywheel: plan, spawn scoped Codex "
            "workers, read pointer-first returns, synthesize, review, re-enter, "
            "write, score, compile failures, gate improvements, and rerun pressure."
        ),
        "center_of_gravity": {
            "intended_system": "Grep-parity research cognition with benchmark pressure.",
            "current_center_to_demote": (
                "Blocked score packages and proof receipts are evidence inputs, not "
                "the organizing abstraction."
            ),
            "missing_center_added": (
                "Evidence-driven next-action planning from scorer, subset, full-run, "
                "and improvement-gate artifacts."
            ),
        },
        "source_artifacts": {
            "run_id": case_id,
            "run_dir": run_dir.as_posix(),
            "case_manifest": artifact_ref(run_dir / "case_manifest.json"),
            "benchmark_score": artifact_ref(run_dir / "benchmark_score.json"),
            "claim_review": artifact_ref(run_dir / "claim_review.json"),
            "evaluation_ledger": artifact_ref(run_dir / "evaluation_ledger.json"),
            "improvement_candidates": artifact_ref(
                run_dir / "self_improvement" / "improvement_candidates.json"
            ),
            "candidate_gate_results": artifact_ref(
                run_dir / "self_improvement" / "candidate_gate_results.json"
            ),
            "subset_summary": artifact_ref(subset_summary),
            "full_run_package": artifact_ref(full_run_package),
        },
        "state_assessment": {
            "benchmark_family": case_manifest.get("benchmark_family"),
            "score_mode": benchmark_score.get("mode"),
            "score": benchmark_score.get("score"),
            "score_status": score_status,
            "claim_review_decision": claim_review.get("decision"),
            "may_widen_public_benchmark_claims": claim_review.get(
                "may_widen_public_benchmark_claims"
            ),
            "candidate_count": candidates_payload.get("candidate_count", len(candidates)),
            "all_candidates_gated": gate_results.get("all_candidates_gated") is True,
            "subset_case_count": subset.get("case_count"),
            "full_run_status": package.get("status"),
            "current_grep_target": package.get("current_grep_target")
            or evaluation_ledger.get("current_grep_target"),
        },
        "selected_candidate": selected_candidate,
        "next_actions": next_actions,
        "bead_seed_packet": {
            "epic_title": "Codex-DR autonomous improvement flywheel execution",
            "beads": [
                {
                    "name": "Apply selected candidate as isolated overlay",
                    "acceptance": (
                        "Overlay has a promotion receipt, leaves live base surfaces "
                        "unchanged until explicitly adopted, and keeps claims blocked."
                    ),
                },
                {
                    "name": "Run one live mesh case against overlay",
                    "acceptance": (
                        "Planner, parallel branches, synthesis, review, re-entry, writer, "
                        "raw export, blocked scorer receipt, and claim review all pass."
                    ),
                },
                {
                    "name": "Run subset pressure against overlay",
                    "acceptance": (
                        "At least five sealed DeepResearch Bench cases complete or fail "
                        "with explicit custody and next improvement inputs."
                    ),
                },
                {
                    "name": "Prepare scorer authority packet",
                    "acceptance": (
                        "Provider key presence, explicit provider-run approval, evaluator "
                        "lane, budget, and official command custody are checked before "
                        "score-bearing execution."
                    ),
                },
            ],
        },
        "claim_boundary": {
            "may_claim_deepresearch_bench_score": False,
            "may_claim_grep_parity": False,
            "may_claim_leaderboard_rank": False,
            "may_claim_product_readiness": False,
            "blocked_claims": blocked_claims,
        },
        "produced_at": FIXTURE_TIMESTAMP,
    }


def artifact_ref(path: Path) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "exists": path.exists(),
        "sha256": sha256_file(path) if path.exists() else None,
    }


def select_next_deepresearch_bench_candidate(
    candidates: list[dict[str, Any]], gated_by_id: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    priority = {
        "prompt": 0,
        "file_context": 1,
        "scheduler": 2,
        "skill": 3,
        "evaluator": 4,
    }
    eligible = []
    for candidate in candidates:
        gate = gated_by_id.get(candidate.get("candidate_id"), {})
        if gate.get("checks_passed") is True and gate.get("live_surface_changed") is False:
            eligible.append({**candidate, "gate_result": gate})
    if not eligible:
        return {
            "candidate_id": None,
            "selection_status": "blocked_no_gated_candidate",
            "reason": "No candidate has a passed isolated gate result.",
        }
    selected = sorted(
        eligible,
        key=lambda item: (
            priority.get(str(item.get("target_surface_type")), 99),
            str(item.get("candidate_id")),
        ),
    )[0]
    selected["selection_status"] = "selected_for_next_overlay"
    return selected


def deepresearch_bench_candidate_next_action(
    selected_candidate: dict[str, Any],
) -> dict[str, Any]:
    if not selected_candidate.get("candidate_id"):
        return {
            "action_id": "select_candidate_overlay",
            "action_type": "candidate_experiment",
            "status": "blocked_no_gated_candidate",
            "purpose": "Gate improvement candidates before applying an overlay.",
            "claim_impact": "no claim widening",
        }
    return {
        "action_id": "apply_selected_candidate_overlay",
        "action_type": "candidate_experiment",
        "status": "ready_for_isolated_overlay_bead",
        "candidate_id": selected_candidate["candidate_id"],
        "target_surface_type": selected_candidate.get("target_surface_type"),
        "target_surface": selected_candidate.get("target_surface"),
        "purpose": selected_candidate.get("proposed_change"),
        "expected_effect": selected_candidate.get("expected_effect"),
        "commands": [
            "alexandria-dr validate",
            "alexandria-dr mesh-live-plan",
            "alexandria-dr mesh-execute-live",
            "alexandria-dr deepresearch-bench-report-export",
            "alexandria-dr deepresearch-bench-claim-review",
        ],
        "acceptance": [
            "overlay is isolated or explicitly receipted before live surface mutation",
            "prior provider-off and live mesh validation remain passing",
            "claim review remains closed without official score evidence",
        ],
        "claim_impact": "no claim widening",
    }


def deepresearch_bench_flywheel_work_packet(plan: dict[str, Any]) -> str:
    lines = [
        "# DeepResearch Bench Flywheel Work Packet",
        "",
        f"Plan: `{plan['plan_id']}`",
        "",
        "## Center",
        plan["center_of_gravity"]["missing_center_added"],
        "",
        "## Selected Candidate",
        f"`{plan.get('selected_candidate', {}).get('candidate_id')}`",
        "",
        "## Next Actions",
    ]
    for action in plan.get("next_actions", []):
        lines.append(f"- `{action['action_id']}`: {action['status']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "No score, Grep parity, leaderboard, product-readiness, or submission claim is open.",
            "",
        ]
    )
    return "\n".join(lines)


def validate_deepresearch_bench_flywheel_plan(output_dir: Path) -> dict[str, Any]:
    problems = []
    try:
        plan = read_json(output_dir / "flywheel_next_action_plan.json")
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return {
            "schema_version": "codex-dr.deepresearch_bench_flywheel_plan_validation.v1",
            "status": "failed",
            "failed_checks": [f"flywheel plan unavailable: {error}"],
        }
    if plan.get("schema_version") != "codex-dr.deepresearch_bench_flywheel_plan.v1":
        problems.append("invalid flywheel plan schema_version")
    if "DeepResearch mesh flywheel" not in plan.get("completion_object", ""):
        problems.append("completion object does not name the DR mesh flywheel")
    state = plan.get("state_assessment", {})
    if state.get("benchmark_family") != BENCHMARK_FAMILY_DEEPRESEARCH_BENCH:
        problems.append("state assessment is not DeepResearch Bench")
    if state.get("all_candidates_gated") is not True:
        problems.append("improvement candidates have not all been gated")
    selected = plan.get("selected_candidate", {})
    if selected.get("selection_status") != "selected_for_next_overlay":
        problems.append("no gated candidate selected for next overlay")
    action_ids = {action.get("action_id") for action in plan.get("next_actions", [])}
    required_actions = {
        "resolve_scorer_authority_run_control",
        "apply_selected_candidate_overlay",
        "rerun_subset_pressure_after_candidate_overlay",
        "prepare_full_100_case_run_control_packet",
    }
    if not required_actions <= action_ids:
        problems.append("flywheel plan lacks required next actions")
    claim_boundary = plan.get("claim_boundary", {})
    if any(
        claim_boundary.get(field) is not False
        for field in [
            "may_claim_deepresearch_bench_score",
            "may_claim_grep_parity",
            "may_claim_leaderboard_rank",
            "may_claim_product_readiness",
        ]
    ):
        problems.append("flywheel plan widened benchmark or product claims")
    blocked = set(claim_boundary.get("blocked_claims", []))
    if not {"DeepResearch Bench score", "Grep parity", "leaderboard rank"} <= blocked:
        problems.append("flywheel plan does not block score/parity/leaderboard claims")
    source_artifacts = plan.get("source_artifacts", {})
    for name in [
        "benchmark_score",
        "claim_review",
        "evaluation_ledger",
        "improvement_candidates",
        "candidate_gate_results",
        "subset_summary",
        "full_run_package",
    ]:
        artifact = source_artifacts.get(name, {})
        if artifact.get("exists") is not True or not artifact.get("sha256"):
            problems.append(f"missing source artifact custody for {name}")
    status = "failed" if problems else "passed"
    return {
        "schema_version": "codex-dr.deepresearch_bench_flywheel_plan_validation.v1",
        "status": status,
        "failed_checks": problems,
        "plan_id": plan.get("plan_id"),
        "selected_candidate_id": selected.get("candidate_id"),
        "claim_boundary": claim_boundary,
    }


def deepresearch_bench_apply_candidate_overlay(
    overlay_id: str,
    *,
    flywheel_plan: Path,
    output_dir: Path,
    base_prompt_overlay: Path | None = None,
) -> Path:
    validate_id(overlay_id, "overlay_id")
    output_dir.mkdir(parents=True, exist_ok=True)
    plan = read_json(flywheel_plan)
    base_overlay = (
        read_validated_prompt_overlay(base_prompt_overlay) if base_prompt_overlay else None
    )
    overlay = deepresearch_bench_candidate_overlay_payload(
        overlay_id=overlay_id,
        flywheel_plan=flywheel_plan,
        plan=plan,
        base_overlay=base_overlay,
        base_prompt_overlay=base_prompt_overlay,
    )
    write_json(output_dir / "prompt_overlay.json", overlay)
    write_text(output_dir / "prompt_overlay.md", prompt_overlay_markdown(overlay))
    write_json(
        output_dir / "overlay_promotion_receipt.json",
        {
            "schema_version": "codex-dr.prompt_overlay_promotion_receipt.v1",
            "overlay_id": overlay_id,
            "candidate_id": overlay["candidate_id"],
            "promotion_status": "overlay_created_not_live_mutated",
            "live_surface_changed": False,
            "base_surface": overlay["target_surface"],
            "overlay_artifact": "prompt_overlay.json",
            "claim_impact": "no claim widening",
            "produced_at": FIXTURE_TIMESTAMP,
        },
    )
    validation = validate_prompt_overlay(output_dir / "prompt_overlay.json")
    write_json(output_dir / "prompt_overlay_validation.json", validation)
    if validation["status"] != "passed":
        raise HarnessError(
            "DeepResearch Bench prompt overlay failed validation: "
            + "; ".join(validation["failed_checks"])
        )
    return output_dir


def deepresearch_bench_candidate_overlay_payload(
    *,
    overlay_id: str,
    flywheel_plan: Path,
    plan: dict[str, Any],
    base_overlay: dict[str, Any] | None = None,
    base_prompt_overlay: Path | None = None,
) -> dict[str, Any]:
    selected = plan.get("selected_candidate", {})
    if selected.get("selection_status") != "selected_for_next_overlay":
        selected = {}
    candidate_id = selected.get("candidate_id")
    overlay_spec = prompt_overlay_spec_for_candidate(candidate_id)
    instruction_blocks = list(overlay_spec["instruction_blocks"])
    applies_to_task_ids = list(overlay_spec["applies_to_task_ids"])
    parent_overlays = []
    candidate_chain = []
    if base_overlay:
        base_instruction_blocks = []
        for block in base_overlay.get("instruction_blocks", []):
            if "applies_to_task_ids" in block:
                base_instruction_blocks.append(block)
            else:
                base_instruction_blocks.append(
                    {
                        **block,
                        "applies_to_task_ids": base_overlay.get(
                            "applies_to_task_ids", []
                        ),
                    }
                )
        instruction_blocks = [
            *base_instruction_blocks,
            *instruction_blocks,
        ]
        applies_to_task_ids = sorted(
            set(base_overlay.get("applies_to_task_ids", [])) | set(applies_to_task_ids)
        )
        parent_overlays.append(
            {
                "overlay_id": base_overlay.get("overlay_id"),
                "candidate_id": base_overlay.get("candidate_id"),
                "path": base_prompt_overlay.as_posix() if base_prompt_overlay else None,
                "sha256": (
                    sha256_file(base_prompt_overlay) if base_prompt_overlay else None
                ),
            }
        )
        candidate_chain.extend(base_overlay.get("candidate_chain", []))
        if not candidate_chain and base_overlay.get("candidate_id"):
            candidate_chain.append(base_overlay["candidate_id"])
    if candidate_id:
        candidate_chain.append(candidate_id)
    return {
        "schema_version": "codex-dr.deepresearch_bench_prompt_overlay.v1",
        "overlay_id": overlay_id,
        "candidate_id": candidate_id,
        "candidate_chain": candidate_chain,
        "parent_overlays": parent_overlays,
        "source_flywheel_plan": flywheel_plan.as_posix(),
        "source_plan_sha256": sha256_file(flywheel_plan),
        "target_surface_type": selected.get("target_surface_type"),
        "target_surface": selected.get("target_surface"),
        "source_failure_refs": selected.get("source_failure_refs", []),
        "replay_fixtures": selected.get("replay_fixtures", []),
        "applies_to_task_ids": applies_to_task_ids,
        "instruction_blocks": instruction_blocks,
        "expected_effect": selected.get("expected_effect"),
        "live_surface_changed": False,
        "base_surface_mutation_allowed": False,
        "claim_boundary": {
            "may_widen_claims": False,
            "blocked_claims": plan.get("claim_boundary", {}).get("blocked_claims", []),
        },
        "produced_at": FIXTURE_TIMESTAMP,
    }


def prompt_overlay_spec_for_candidate(candidate_id: Any) -> dict[str, Any]:
    if candidate_id == "cand_drb_reentry_admission_status_prompt_001":
        return {
            "applies_to_task_ids": ["task_reentry_followup"],
            "instruction_blocks": [
                {
                    "block_id": "reentry_evidence_admission_status_lock",
                    "title": "Re-entry Evidence Admission Status Lock",
                    "applies_to_task_ids": ["task_reentry_followup"],
                    "instructions": [
                        (
                            "Every row in `branches/reentry_followup/evidence.jsonl` "
                            "must contain `admission_status`; do not write `status` "
                            "as a substitute field."
                        ),
                        (
                            "Use `admitted_input` for cited input artifacts, "
                            "`derived_from_admitted_inputs` for bounded conclusions "
                            "derived from admitted inputs, and `bounded_result` for "
                            "reviewer-facing dispositions."
                        ),
                        (
                            "If evidence is absent or unresolved, write an explicit "
                            "gap value in `admission_status` and keep the gap visible "
                            "for synthesis and review."
                        ),
                        (
                            "Before finishing, inspect the evidence JSONL and repair "
                            "any row that lacks `admission_status`."
                        ),
                    ],
                }
            ],
        }
    return {
        "applies_to_task_ids": [
            "task_pointer_first_synthesis",
            "task_reentry_synthesis",
            "task_review",
            "task_final_writer",
        ],
        "instruction_blocks": [
            {
                "block_id": "numeric_claim_support_appendix",
                "title": "Numeric Claim Support Appendix",
                "applies_to_task_ids": [
                    "task_pointer_first_synthesis",
                    "task_reentry_synthesis",
                    "task_review",
                    "task_final_writer",
                ],
                "instructions": [
                    (
                        "When the output contains a material number, estimate, "
                        "forecast, percentage, currency amount, count, or derived "
                        "total, add a `## Numeric Claim Support Appendix` section."
                    ),
                    (
                        "For each material quantity, record `claim_id`, `quantity`, "
                        "`calculation_or_derivation`, `support_path`, `evidence_id`, "
                        "`source_url`, `confidence`, and `unresolved_gap`."
                    ),
                    (
                        "Use local run-bundle paths, admitted evidence ids, or cited "
                        "public URLs. If support is absent, write `unresolved_gap` "
                        "and keep the claim out of the main conclusion."
                    ),
                    (
                        "Do not use sealed benchmark references, scorer-only material, "
                        "hidden transcripts, or unadmitted evidence to support "
                        "generator-facing claims."
                    ),
                ],
            }
        ],
    }


def prompt_overlay_markdown(overlay: dict[str, Any]) -> str:
    lines = [
        "# Prompt Overlay",
        "",
        f"Overlay: `{overlay['overlay_id']}`",
        f"Candidate: `{overlay.get('candidate_id')}`",
        f"Target surface: `{overlay.get('target_surface')}`",
        "",
        "## Instructions",
    ]
    for block in overlay.get("instruction_blocks", []):
        lines.append(f"### {block.get('title')}")
        for instruction in block.get("instructions", []):
            lines.append(f"- {instruction}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            (
                "This overlay opens no score, Grep parity, leaderboard, "
                "product-readiness, or submission claim."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def validate_prompt_overlay(path: Path) -> dict[str, Any]:
    problems = []
    try:
        overlay = read_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return {
            "schema_version": "codex-dr.prompt_overlay_validation.v1",
            "status": "failed",
            "failed_checks": [f"prompt overlay unavailable: {error}"],
        }
    if overlay.get("schema_version") != "codex-dr.deepresearch_bench_prompt_overlay.v1":
        problems.append("invalid prompt overlay schema_version")
    if not overlay.get("candidate_id"):
        problems.append("prompt overlay lacks candidate_id")
    if overlay.get("target_surface_type") != "prompt":
        problems.append("prompt overlay target is not a prompt surface")
    if overlay.get("live_surface_changed") is not False:
        problems.append("prompt overlay changed live surface")
    if overlay.get("base_surface_mutation_allowed") is not False:
        problems.append("prompt overlay allows base surface mutation")
    if not overlay.get("source_failure_refs"):
        problems.append("prompt overlay lacks source failure refs")
    candidate_id = overlay.get("candidate_id")
    replay_fixtures = set(overlay.get("replay_fixtures", []))
    task_ids = set(overlay.get("applies_to_task_ids", []))
    block_text = json.dumps(overlay.get("instruction_blocks", []))
    for block in overlay.get("instruction_blocks", []):
        block_task_ids = set(block.get("applies_to_task_ids", task_ids))
        if not block_task_ids <= task_ids:
            problems.append(
                f"prompt overlay block {block.get('block_id')} targets tasks outside overlay"
            )
    if candidate_id == "cand_drb_numeric_appendix_prompt_001":
        if "fixture_drb_numeric_appendix_gap_001" not in replay_fixtures:
            problems.append("prompt overlay lacks numeric appendix replay fixture")
        if not {"task_pointer_first_synthesis", "task_reentry_synthesis"} <= task_ids:
            problems.append(
                "prompt overlay does not apply to synthesis and re-entry synthesis"
            )
        if "Numeric Claim Support Appendix" not in block_text:
            problems.append("prompt overlay lacks numeric support appendix instruction")
    elif candidate_id == "cand_drb_reentry_admission_status_prompt_001":
        if "fixture_subset_reentry_schema_failure_001" not in replay_fixtures:
            problems.append("prompt overlay lacks re-entry schema replay fixture")
        if "task_reentry_followup" not in task_ids:
            problems.append("prompt overlay does not apply to re-entry follow-up")
        if "admission_status" not in block_text or "status` as a substitute" not in block_text:
            problems.append("prompt overlay lacks re-entry admission_status instruction")
    else:
        problems.append(f"unsupported prompt overlay candidate: {candidate_id}")
    claim_boundary = overlay.get("claim_boundary", {})
    if claim_boundary.get("may_widen_claims") is not False:
        problems.append("prompt overlay widens claims")
    status = "failed" if problems else "passed"
    return {
        "schema_version": "codex-dr.prompt_overlay_validation.v1",
        "status": status,
        "failed_checks": problems,
        "overlay_id": overlay.get("overlay_id"),
        "candidate_id": overlay.get("candidate_id"),
        "claim_boundary": claim_boundary,
    }


def read_validated_prompt_overlay(path: Path) -> dict[str, Any]:
    validation = validate_prompt_overlay(path)
    if validation["status"] != "passed":
        raise HarnessError(
            "prompt overlay failed validation: " + "; ".join(validation["failed_checks"])
        )
    return read_json(path)


def prompt_overlay_section_for_task(
    overlay: dict[str, Any] | None, *, task_id: str
) -> str:
    task_aliases = {task_id}
    if task_id.startswith("task_reentry_followup_"):
        task_aliases.add("task_reentry_followup")
    if task_id.startswith("task_reentry_synthesis_"):
        task_aliases.add("task_reentry_synthesis")
    overlay_task_ids = set(overlay.get("applies_to_task_ids", [])) if overlay else set()
    if not overlay or not (task_aliases & overlay_task_ids):
        return ""
    blocks = []
    for block in overlay.get("instruction_blocks", []):
        block_task_ids = set(
            block.get("applies_to_task_ids", overlay.get("applies_to_task_ids", []))
        )
        if not (task_aliases & block_task_ids):
            continue
        instructions = "\n".join(
            f"- {instruction}" for instruction in block.get("instructions", [])
        )
        blocks.append(f"### {block.get('title')}\n{instructions}")
    if not blocks:
        return ""
    block_text = "\n\n".join(blocks)
    return f"""

## Candidate Prompt Overlay
Overlay id: `{overlay.get("overlay_id")}`
Candidate id: `{overlay.get("candidate_id")}`
Target surface: `{overlay.get("target_surface")}`
Live surface changed: `{overlay.get("live_surface_changed")}`

{block_text}
"""


def validate_run(case_id: str, *, runs_dir: Path | str | None = None) -> dict[str, Any]:
    run_dir = run_path(case_id, runs_dir)
    checks = [
        check_required_files(run_dir),
        check_required_event_types(run_dir),
        check_event_chain(run_dir),
        check_orchestrator_state_machine_order(run_dir),
        check_artifact_manifest(run_dir),
        check_benchmark_case_manifest(run_dir),
        check_branch_triplets(run_dir),
        check_prompt_contract_drift_guard(run_dir),
        check_evidence_quality_handoffs(run_dir),
        check_task_graph_dependencies(run_dir),
        check_pointer_first_receipts(run_dir),
        check_adequacy_criteria(run_dir),
        check_adequacy_backpressure_queue(run_dir),
        check_backpressure_gate_receipt(run_dir),
        check_writer_gate_preflight(run_dir),
        check_reentry_task_packets(run_dir),
        check_reentry_synthesis_outputs(run_dir),
        check_citation_support_maps(run_dir),
        check_review_reentry(run_dir),
        check_reviewer_output_whitelist(run_dir),
        check_compaction_receipt(run_dir),
        check_scorer_manifest(run_dir),
        check_benchmark_placeholder(run_dir),
        check_evaluation_ledger_claim_gate(run_dir),
        check_self_improvement_replay_gate(run_dir),
        check_live_execution_custody(run_dir),
        check_report_claims_in_ledger(run_dir),
        check_claim_review_artifact(run_dir),
        check_allowed_claims(run_dir),
        check_provider_off_artifacts(run_dir),
        check_generated_path(run_dir),
    ]
    failed = [check for check in checks if check["status"] == "failed"]
    report = {
        "schema_version": "codex-dr.validation_report.v1",
        "run_id": case_id,
        "status": "failed" if failed else "passed",
        "validated_at": FIXTURE_TIMESTAMP,
        "checks": checks,
        "failed_checks": [check["check_id"] for check in failed],
        "produced_by_event": None,
    }
    write_json(run_dir / "validation_report.json", report)
    return report


def pass_check(check_id: str, details: str) -> dict[str, str]:
    return {"check_id": check_id, "status": "passed", "details": details}


def fail_check(check_id: str, details: str) -> dict[str, str]:
    return {"check_id": check_id, "status": "failed", "details": details}


def check_required_files(run_dir: Path) -> dict[str, str]:
    missing = [path for path in required_files_for_run(run_dir) if not (run_dir / path).exists()]
    if missing:
        return fail_check("required_files_present", f"Missing files: {', '.join(missing)}")
    return pass_check("required_files_present", "All required provider-off files are present.")


def check_required_event_types(run_dir: Path) -> dict[str, str]:
    events = read_jsonl(run_dir / "events.jsonl")
    present = {event.get("event_type") for event in events}
    missing = [
        event_type
        for event_type in required_event_types_for_run(run_dir)
        if event_type not in present
    ]
    if missing:
        return fail_check(
            "events_required_types_present", f"Missing event types: {', '.join(missing)}"
        )
    return pass_check("events_required_types_present", "All required event types are present.")


def check_event_chain(run_dir: Path) -> dict[str, str]:
    events = read_jsonl(run_dir / "events.jsonl")
    if not events:
        return fail_check("events_causal_chain_connected", "No events found.")
    seen: set[str] = set()
    for event in events:
        event_id = event.get("event_id")
        if not event_id or event_id in seen:
            return fail_check(
                "events_causal_chain_connected", f"Duplicate or missing event id: {event_id}"
            )
        for parent in event.get("causally_after", []):
            if parent not in seen:
                return fail_check(
                    "events_causal_chain_connected",
                    f"Event {event_id} references missing or later parent {parent}.",
                )
        if event.get("decision") and not event["decision"].get("rationale"):
            return fail_check(
                "events_causal_chain_connected", f"Decision on {event_id} lacks rationale."
            )
        seen.add(event_id)
    if events[0].get("event_type") != "case.initialized":
        return fail_check("events_causal_chain_connected", "First event is not case.initialized.")
    return pass_check("events_causal_chain_connected", "Event causal chain is connected.")


def check_orchestrator_state_machine_order(run_dir: Path) -> dict[str, str]:
    if not is_mesh_run(run_dir):
        return pass_check(
            "orchestrator_state_machine_order_valid",
            "Legacy bootstrap is outside the DR mesh state-machine contract.",
        )
    events = read_jsonl(run_dir / "events.jsonl")
    positions: dict[str, list[int]] = {}
    for index, event in enumerate(events):
        positions.setdefault(str(event.get("event_type")), []).append(index)

    def first(event_type: str) -> int | None:
        values = positions.get(event_type)
        return values[0] if values else None

    def last(event_type: str) -> int | None:
        values = positions.get(event_type)
        return values[-1] if values else None

    def require_before(left: str, right: str) -> None:
        left_last = last(left)
        right_first = first(right)
        if left_last is None or right_first is None:
            return
        if left_last >= right_first:
            problems.append(f"{left} must complete before {right}")

    def require_first_before_first(left: str, right: str) -> None:
        left_first = first(left)
        right_first = first(right)
        if left_first is None or right_first is None:
            return
        if left_first >= right_first:
            problems.append(f"{left} must start before {right}")

    problems: list[str] = []
    require_before("plan.written", "task_graph.written")
    require_before("task_graph.written", "branch.spawn_declared")
    require_first_before_first("branch.return_written", "pointer_reads.recorded")
    require_first_before_first("pointer_reads.recorded", "adequacy.assessed")
    require_first_before_first("adequacy.assessed", "synthesis.written")
    require_first_before_first("synthesis.written", "review.written")
    require_before("review.written", "reentry.compiled")
    require_before("reentry.compiled", "report.written")
    require_before("report.written", "scorer_bridge.written")
    require_before("report.written", "benchmark.placeholder_written")
    require_before("report.written", "benchmark.score_recorded")
    require_before("benchmark.placeholder_written", "evaluation_ledger.written")
    require_before("evaluation_ledger.written", "self_improvement.replay_written")
    require_before(
        "self_improvement.replay_written",
        "self_improvement.proposal_written",
    )
    require_before(
        "self_improvement.proposal_written",
        "self_improvement.regression_gate_written",
    )

    if is_live_mesh_run(run_dir):
        require_before("report.written", "live_executor.execution_started")
        require_before("live_executor.execution_started", "live_executor.role_completed")
        require_before("live_executor.role_completed", "live_executor.execution_completed")

    if problems:
        return fail_check(
            "orchestrator_state_machine_order_valid",
            "; ".join(problems),
        )
    return pass_check(
        "orchestrator_state_machine_order_valid",
        "Orchestrator events preserve the DR mesh state-machine order.",
    )


def check_artifact_manifest(run_dir: Path) -> dict[str, str]:
    manifest_path = run_dir / "artefact_manifest.json"
    if not manifest_path.exists():
        return fail_check("artefact_manifest_hashes_match", "Artifact manifest is missing.")
    try:
        manifest = read_json(manifest_path)
    except json.JSONDecodeError as error:
        return fail_check(
            "artefact_manifest_hashes_match", f"Artifact manifest is invalid JSON: {error}"
        )
    artifacts = {artifact["path"]: artifact for artifact in manifest.get("artifacts", [])}
    missing = [
        path
        for path in required_files_for_run(run_dir)
        if path not in {"artefact_manifest.json", "validation_report.json"}
        and path not in artifacts
    ]
    if missing:
        return fail_check(
            "artefact_manifest_hashes_match", f"Missing manifest entries: {', '.join(missing)}"
        )
    mismatches = []
    for path, artifact in artifacts.items():
        file_path = run_dir / path
        if not file_path.exists():
            mismatches.append(f"{path}: missing file")
            continue
        if artifact.get("sha256") != sha256_file(file_path):
            mismatches.append(f"{path}: hash mismatch")
        if artifact.get("produced_by_event") is None:
            mismatches.append(f"{path}: missing produced_by_event")
    if mismatches:
        return fail_check("artefact_manifest_hashes_match", "; ".join(mismatches))
    return pass_check("artefact_manifest_hashes_match", "Artifact manifest hashes match.")


def check_benchmark_case_manifest(run_dir: Path) -> dict[str, str]:
    if not is_mesh_run(run_dir):
        return pass_check(
            "benchmark_case_manifest_sealed",
            "Legacy bootstrap has no benchmark case manifest.",
        )
    try:
        manifest = read_json(run_dir / "case_manifest.json")
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return fail_check(
            "benchmark_case_manifest_sealed",
            f"Case manifest unavailable: {error}",
        )
    problems = []
    if manifest.get("schema_version") != "codex-dr.case_manifest.v1":
        problems.append("invalid case manifest schema_version")
    if manifest.get("benchmark_family") not in SUPPORTED_CASE_MANIFEST_FAMILIES:
        problems.append(
            "benchmark_family must be one of "
            + ", ".join(sorted(SUPPORTED_CASE_MANIFEST_FAMILIES))
        )
    if manifest.get("raw_data_in_git") is not False:
        problems.append("raw_data_in_git must be false")
    source = manifest.get("source", {})
    for field in [
        "dataset_id",
        "dataset_commit",
        "split",
        "source_file",
        "row_indices",
        "license_observed",
        "access_observed",
        "manifest_ref",
    ]:
        if not source.get(field):
            problems.append(f"missing source.{field}")
    generator_visible = manifest.get("generator_visible", {})
    if not generator_visible:
        problems.append("missing generator_visible payload")
    sealed = manifest.get("sealed_scorer_only", {})
    for field in ["reference_answer", "rubric"]:
        sealed_item = sealed.get(field, {})
        if not sealed_item:
            problems.append(f"missing sealed_scorer_only.{field}")
            continue
        if sealed_item.get("visibility") != "scorer_only":
            problems.append(f"sealed_scorer_only.{field}.visibility must be scorer_only")
        if sealed_item.get("generator_visible") is not False:
            problems.append(f"sealed_scorer_only.{field} leaked to generator")
        if sealed_item.get("payload_status") == "materialized_in_git":
            problems.append(f"sealed_scorer_only.{field} is materialized in git")
    leakage_policy = manifest.get("leakage_policy", {})
    if leakage_policy.get("reference_answers_visible_to_generator") is not False:
        problems.append("reference answers are visible to generator")
    if leakage_policy.get("rubric_payload_visible_to_generator") is not False:
        problems.append("rubric payload is visible to generator")
    if leakage_policy.get("fail_closed_on_generator_leak") is not True:
        problems.append("generator leak policy must fail closed")

    forbidden_key_fragments = {
        "reference_answer",
        "gold_answer",
        "scorer_only",
        "sealed",
        "rubric_payload",
    }
    forbidden_value_fragments = {
        "reference answer:",
        "gold answer:",
        "rubric payload:",
        "scorer-only payload:",
    }

    def walk_generator_payload(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                key_text = str(key).lower()
                if any(fragment in key_text for fragment in forbidden_key_fragments):
                    problems.append(f"generator_visible leaks forbidden key {path}.{key}")
                walk_generator_payload(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk_generator_payload(child, f"{path}[{index}]")
        elif isinstance(value, str):
            text = value.lower()
            if any(fragment in text for fragment in forbidden_value_fragments):
                problems.append(f"generator_visible leaks forbidden value at {path}")

    walk_generator_payload(generator_visible, "generator_visible")
    if problems:
        return fail_check("benchmark_case_manifest_sealed", "; ".join(problems))
    return pass_check(
        "benchmark_case_manifest_sealed",
        "Benchmark case manifest separates generator-visible data from scorer-only material.",
    )


def check_branch_triplets(run_dir: Path) -> dict[str, str]:
    branch_ids = MESH_ALL_BRANCH_IDS if is_mesh_run(run_dir) else ["branch_a"]
    triplet = ["pointer.md", "analysis.md", "evidence.jsonl"]
    missing = []
    for branch_id in branch_ids:
        branch_dir = run_dir / "branches" / branch_id
        missing.extend(
            f"branches/{branch_id}/{name}" for name in triplet if not (branch_dir / name).exists()
        )
    if missing:
        return fail_check(
            "branch_triplets_present", f"Missing branch triplet files: {', '.join(missing)}"
        )
    for branch_id in branch_ids:
        branch_dir = run_dir / "branches" / branch_id
        pointer = (branch_dir / "pointer.md").read_text(encoding="utf-8")
        if not pointer_has_read_next_section(pointer):
            return fail_check(
                "branch_triplets_present", f"Branch {branch_id} pointer lacks Read Next section."
            )
        evidence = read_jsonl(branch_dir / "evidence.jsonl")
        admitted = [
            item
            for item in evidence
            if evidence_status_is_admitted(item.get("admission_status"))
        ]
        gap_or_result = [
            item
            for item in evidence
            if evidence_status_is_gap(item.get("admission_status"))
            or evidence_status_is_result(item.get("admission_status"))
        ]
        unknown_statuses = sorted(
            {
                str(item.get("admission_status"))
                for item in evidence
                if not evidence_status_is_admitted(item.get("admission_status"))
                and not evidence_status_is_gap(item.get("admission_status"))
                and not evidence_status_is_result(item.get("admission_status"))
            }
        )
        if not evidence or not admitted:
            if not (
                branch_id.startswith("reentry_followup")
                and gap_or_result
                and run_has_writer_blocking_backpressure(run_dir)
            ):
                return fail_check(
                    "branch_triplets_present",
                    f"Branch {branch_id} evidence is missing or not admitted.",
                )
        if unknown_statuses:
            return fail_check(
                "branch_triplets_present",
                f"Branch {branch_id} has unknown evidence statuses: "
                + ", ".join(unknown_statuses),
            )
    return pass_check(
        "branch_triplets_present", "Branch pointer, analysis, and evidence are present."
    )


def pointer_has_read_next_section(pointer_text: str) -> bool:
    return any(
        line.strip().casefold().lstrip("#").strip() == "read next"
        for line in pointer_text.splitlines()
    )


def evidence_status_is_admitted(status: Any) -> bool:
    if not isinstance(status, str):
        return False
    return (
        status in EVIDENCE_ADMITTED_STATUSES
        or status.startswith("admitted_")
        or status.startswith("derived_from_admitted")
        or status.startswith("inference_from_admitted")
        or status.startswith("produced_from_admitted")
    )


def evidence_status_is_gap(status: Any) -> bool:
    if not isinstance(status, str):
        return False
    return status in EVIDENCE_GAP_STATUSES or status.startswith("gap_")


def evidence_status_is_result(status: Any) -> bool:
    if not isinstance(status, str):
        return False
    return status in EVIDENCE_RESULT_STATUSES


def run_has_writer_blocking_backpressure(run_dir: Path) -> bool:
    queue_path = run_dir / "backpressure" / "adequacy_backpressure_queue.json"
    try:
        queue = read_json(queue_path)
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    return bool(queue.get("writer_blocked")) or queue.get("queue_status") == "open"


def normalized_prompt_clause_text(text: str) -> str:
    return " ".join(text.casefold().split())


def prompt_authority_task_key(task_id: str) -> str | None:
    if task_id.startswith("task_reentry_followup"):
        return "task_reentry_followup"
    if task_id.startswith("task_reentry_synthesis"):
        return "task_reentry_synthesis"
    if task_id in PROMPT_AUTHORITY_CLAUSES:
        return task_id
    return None


def prompt_authority_clause_problems(run_dir: Path) -> list[str]:
    pack_path = SANDBOX_ROOT / "harness-specs" / "live_role_prompt_pack.md"
    problems: list[str] = []
    try:
        pack_text = normalized_prompt_clause_text(pack_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"{rel(pack_path, SANDBOX_ROOT)}: durable prompt pack missing"]
    for task_key, clauses in PROMPT_AUTHORITY_CLAUSES.items():
        for clause in clauses:
            clause_text = normalized_prompt_clause_text(clause["text"])
            if clause_text not in pack_text:
                problems.append(
                    f"{LIVE_ROLE_PROMPT_PACK_REF}: {task_key} missing "
                    f"{clause['clause_id']}"
                )
    prompt_root = run_dir / "live_adapter" / "prompts"
    if not prompt_root.exists():
        return problems
    for prompt_path in sorted(prompt_root.glob("*.md")):
        task_key = prompt_authority_task_key(prompt_path.stem)
        if task_key is None:
            continue
        prompt_text = normalized_prompt_clause_text(
            prompt_path.read_text(encoding="utf-8")
        )
        for clause in PROMPT_AUTHORITY_CLAUSES[task_key]:
            clause_text = normalized_prompt_clause_text(clause["text"])
            if clause_text not in prompt_text:
                problems.append(
                    f"{rel(prompt_path, run_dir)} ({task_key}) missing "
                    f"{clause['clause_id']}"
                )
    return problems


def check_prompt_contract_drift_guard(run_dir: Path) -> dict[str, str]:
    if not is_mesh_run(run_dir):
        return pass_check(
            "prompt_contract_drift_guard",
            "Legacy bootstrap has no DR mesh live prompt contract drift guard.",
        )
    problems = prompt_authority_clause_problems(run_dir)
    if problems:
        return fail_check("prompt_contract_drift_guard", "; ".join(problems))
    prompt_root = run_dir / "live_adapter" / "prompts"
    if prompt_root.exists():
        return pass_check(
            "prompt_contract_drift_guard",
            "Generated live prompts preserve authority-critical clauses from the durable prompt pack.",
        )
    return pass_check(
        "prompt_contract_drift_guard",
        "Durable prompt pack preserves authority-critical clauses; no generated live prompts were present.",
    )


def check_evidence_quality_handoffs(run_dir: Path) -> dict[str, str]:
    if not is_mesh_run(run_dir):
        return pass_check(
            "evidence_quality_handoffs_valid",
            "Legacy bootstrap has no DR mesh evidence-quality handoffs.",
        )
    try:
        graph = read_json(run_dir / "task_graph.json")
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return fail_check(
            "evidence_quality_handoffs_valid",
            f"Task graph unavailable: {error}",
        )
    tasks = {task.get("task_id"): task for task in graph.get("tasks", [])}
    problems: list[str] = []
    deep_search = tasks.get("task_deep_search", {})
    data_analysis = tasks.get("task_data_analysis", {})
    verification = tasks.get("task_verification", {})
    synthesis = tasks.get("task_pointer_first_synthesis", {})
    if (
        deep_search.get("evidence_quality_handoff", {}).get("rule")
        != "source_discovery_is_not_source_support"
    ):
        problems.append("task_deep_search lacks source-discovery handoff rule")
    if (
        deep_search.get("evidence_quality_handoff", {}).get("consumer_task_id")
        != "task_verification"
    ):
        problems.append("task_deep_search handoff must target task_verification")
    if (
        data_analysis.get("comparability_handoff", {}).get("rule")
        != "comparisons_require_commensurability_check"
    ):
        problems.append("task_data_analysis lacks comparability handoff rule")
    verified_branch_ids = set(
        verification.get("verification_handoff", {}).get("verifies_branch_ids", [])
    )
    if not {"deep_search", "data_analysis"} <= verified_branch_ids:
        problems.append("task_verification must verify deep_search and data_analysis")
    classifications = set(
        verification.get("verification_handoff", {}).get("support_classifications", [])
    )
    if not {
        "directly_supported",
        "unsupported",
        "too_broad_for_evidence",
        "non_comparable_inputs",
    } <= classifications:
        problems.append("task_verification lacks required support classifications")
    admission_rules = synthesis.get("admission_rules", {})
    if admission_rules.get("source_discovery_requires_verification") is not True:
        problems.append("synthesis can admit source discovery without verification")
    if admission_rules.get("comparative_claims_require_comparability") is not True:
        problems.append("synthesis can admit comparisons without comparability")

    deep_rows = read_jsonl(run_dir / "branches" / "deep_search" / "evidence.jsonl")
    for row in deep_rows:
        row_kind = str(
            row.get("record_type") or row.get("evidence_kind") or ""
        ).lower()
        if row_kind in {"source_discovery", "source_candidate"} and evidence_status_is_admitted(
            row.get("admission_status")
        ) and not row.get("verified_by"):
            problems.append(
                f"{row.get('evidence_id', '<unknown>')}: source discovery admitted without verification"
            )
    data_rows = read_jsonl(run_dir / "branches" / "data_analysis" / "evidence.jsonl")
    for row in data_rows:
        claim_type = str(row.get("claim_type") or row.get("record_type") or "").lower()
        comparative = claim_type in {"ranking", "comparison", "forecast"} or row.get(
            "comparative_claim"
        ) is True
        if not comparative:
            continue
        status = str(row.get("admission_status") or "").lower()
        if status in {"non_comparable_inputs", "scope_ambiguity"}:
            continue
        if evidence_status_is_admitted(status) and not row.get("comparability_assessment"):
            problems.append(
                f"{row.get('evidence_id', '<unknown>')}: comparative claim lacks comparability assessment"
            )
    if problems:
        return fail_check("evidence_quality_handoffs_valid", "; ".join(problems))
    return pass_check(
        "evidence_quality_handoffs_valid",
        "Evidence-quality handoffs prevent source discovery and unverified comparisons from becoming support.",
    )


def check_task_graph_dependencies(run_dir: Path) -> dict[str, str]:
    try:
        graph = read_json(run_dir / "task_graph.json")
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return fail_check("task_graph_dependencies_valid", f"Task graph unavailable: {error}")
    tasks = graph.get("tasks", [])
    if is_mesh_run(run_dir) and not tasks:
        return fail_check("task_graph_dependencies_valid", "Task graph has no executable tasks.")
    task_ids = {task.get("task_id") for task in tasks}
    problems = []
    for task in tasks:
        task_id = task.get("task_id", "<unknown>")
        for dependency in task.get("depends_on", []):
            if dependency not in task_ids:
                problems.append(f"{task_id} depends on missing {dependency}")
        expected_outputs = task.get("expected_outputs", [])
        if not expected_outputs:
            problems.append(f"{task_id} lacks expected outputs")
        if is_mesh_run(run_dir) and not task.get("role_config_id"):
            problems.append(f"{task_id} lacks role_config_id")
    if problems:
        return fail_check("task_graph_dependencies_valid", "; ".join(problems))
    return pass_check("task_graph_dependencies_valid", "Task dependencies and outputs are valid.")


def check_pointer_first_receipts(run_dir: Path) -> dict[str, str]:
    if not is_mesh_run(run_dir):
        return pass_check(
            "pointer_first_receipts_present", "Legacy bootstrap has no mesh receipts."
        )
    receipts = read_jsonl(run_dir / "pointer_read_receipts.jsonl")
    if not receipts:
        return fail_check("pointer_first_receipts_present", "Pointer read receipts are missing.")
    by_branch = {}
    for receipt in receipts:
        branch_id = receipt.get("branch_id") or branch_id_from_pointer_path(
            receipt.get("pointer_path")
        )
        if branch_id:
            candidate = {**receipt, "branch_id": branch_id}
            if "pointer_read_before_analysis" not in candidate:
                candidate["pointer_read_before_analysis"] = bool(
                    candidate.get("pointer_first_read")
                    or candidate.get("pointer_read_first")
                )
            existing = by_branch.get(branch_id)
            if existing is None or (
                not existing.get("pointer_read_before_analysis")
                and candidate.get("pointer_read_before_analysis")
            ):
                by_branch[branch_id] = candidate
    missing = [branch_id for branch_id in MESH_ALL_BRANCH_IDS if branch_id not in by_branch]
    if missing:
        return fail_check(
            "pointer_first_receipts_present",
            f"Missing pointer read receipts: {', '.join(missing)}",
        )
    problems = []
    for branch_id, receipt in by_branch.items():
        if not receipt.get("pointer_read_before_analysis"):
            problems.append(f"{branch_id}: pointer_read_before_analysis is false")
        pointer_path = receipt.get("pointer_path")
        if not pointer_path or not (run_dir / pointer_path).exists():
            problems.append(f"{branch_id}: pointer path missing")
        spans = normalize_selected_analysis_spans(receipt, branch_id)
        if not spans:
            problems.append(f"{branch_id}: no selected analysis spans")
        for span in spans:
            analysis_path = span.get("analysis_path")
            if not analysis_path or not (run_dir / analysis_path).exists():
                problems.append(f"{branch_id}: analysis span path missing")
    if problems:
        return fail_check("pointer_first_receipts_present", "; ".join(problems))
    return pass_check(
        "pointer_first_receipts_present",
        "Pointer-first receipts cover all DR mesh branches.",
    )


def branch_id_from_pointer_path(pointer_path: Any) -> str | None:
    if not isinstance(pointer_path, str):
        return None
    parts = Path(pointer_path).parts
    if len(parts) >= 3 and parts[0] == "branches" and parts[2] == "pointer.md":
        return parts[1]
    return None


def normalize_selected_analysis_spans(
    receipt: dict[str, Any], branch_id: str
) -> list[dict[str, str]]:
    spans = receipt.get("selected_analysis_spans", [])
    normalized = []
    for span in spans:
        if isinstance(span, dict):
            analysis_path = span.get("analysis_path")
            if analysis_path and not str(analysis_path).startswith("branches/"):
                analysis_path = f"branches/{branch_id}/{analysis_path}"
            normalized.append({**span, "analysis_path": analysis_path})
        elif isinstance(span, str):
            analysis_path = span.split("#", 1)[0]
            section_heading = span.split("#", 1)[1] if "#" in span else ""
            if analysis_path and not analysis_path.startswith("branches/"):
                analysis_path = f"branches/{branch_id}/{analysis_path}"
            normalized.append(
                {
                    "analysis_path": analysis_path,
                    "section_heading": section_heading,
                }
            )
    return normalized


def check_adequacy_criteria(run_dir: Path) -> dict[str, str]:
    try:
        criteria = read_json(run_dir / "adequacy_criteria.json").get("criteria", [])
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return fail_check("adequacy_criteria_mapped", f"Adequacy criteria unavailable: {error}")
    missing = [
        criterion.get("criterion_id", "<unknown>")
        for criterion in criteria
        if criterion.get("required") and criterion.get("validator") not in VALIDATOR_NAMES
    ]
    if not criteria or missing:
        return fail_check("adequacy_criteria_mapped", f"Unmapped criteria: {', '.join(missing)}")
    return pass_check("adequacy_criteria_mapped", "Required adequacy criteria map to validators.")


def check_adequacy_backpressure_queue(run_dir: Path) -> dict[str, str]:
    if not is_mesh_run(run_dir):
        return pass_check(
            "adequacy_backpressure_queue_present",
            "Legacy bootstrap has no DR mesh adequacy backpressure queue.",
        )
    try:
        items = adequacy_gap_items(run_dir)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return fail_check(
            "adequacy_backpressure_queue_present",
            f"Adequacy assessments unavailable: {error}",
        )
    existing_gap_ids = {
        str(item.get("gap_id") or item.get("item_id"))
        for item in items
        if item.get("gap_id") or item.get("item_id")
    }
    review_items, quarantined_items = compile_review_proposed_backpressure_items(
        run_dir, existing_gap_ids=existing_gap_ids
    )
    effective_items = merge_backpressure_items(items, review_items)
    queue_path = run_dir / "backpressure" / "adequacy_backpressure_queue.json"
    if not effective_items and not quarantined_items and not queue_path.exists():
        return pass_check(
            "adequacy_backpressure_queue_present",
            "No unresolved adequacy gaps require a backpressure queue.",
        )
    try:
        queue = read_json(queue_path)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return fail_check(
            "adequacy_backpressure_queue_present",
            f"Unresolved adequacy gaps lack queue: {error}",
        )
    if not effective_items and not quarantined_items:
        return pass_check(
            "adequacy_backpressure_queue_present",
            "No unresolved adequacy gaps require a backpressure queue.",
        )
    problems = []
    if queue.get("schema_version") != BACKPRESSURE_QUEUE_SCHEMA_VERSION:
        problems.append("queue schema is invalid")
    expected_status, expected_writer_blocked = adequacy_backpressure_queue_status(
        effective_items, quarantined_items
    )
    if queue.get("queue_status") != expected_status:
        problems.append(f"queue_status must be {expected_status} while these gaps exist")
    if queue.get("writer_blocked") is not expected_writer_blocked:
        problems.append(
            f"writer_blocked must be {str(expected_writer_blocked).lower()} "
            "for the queued adequacy pressure"
        )
    live_writer_output_exists = (
        run_dir
        / "live_executor"
        / "role_outputs"
        / "task_final_writer"
        / "report.md"
    ).exists()
    if expected_writer_blocked and live_writer_output_exists:
        problems.append("live writer output exists while adequacy backpressure queue is open")
    queued_gap_ids = {item.get("gap_id") for item in queue.get("items", [])}
    expected_gap_ids = {item.get("gap_id") for item in effective_items}
    missing = expected_gap_ids - queued_gap_ids
    if missing:
        problems.append(f"queue missing gap ids: {', '.join(sorted(missing))}")
    queued_quarantine_ids = {
        item.get("quarantine_id") for item in queue.get("quarantined_items", [])
    }
    expected_quarantine_ids = {
        item.get("quarantine_id") for item in quarantined_items
    }
    missing_quarantines = expected_quarantine_ids - queued_quarantine_ids
    if missing_quarantines:
        problems.append(
            "queue missing quarantined review proposals: "
            + ", ".join(sorted(missing_quarantines))
        )
    if quarantined_items and not queue.get("quarantined_items"):
        problems.append("malformed review proposals were not quarantined")
    summary = queue.get("normalization_summary", {})
    if queue.get("schema_version") == BACKPRESSURE_QUEUE_SCHEMA_VERSION:
        if not isinstance(summary, dict):
            problems.append("queue missing normalization_summary")
        elif summary.get("legacy_fields_normalized_by") != "harness":
            problems.append("queue normalization_summary must name harness normalization")
    for item in queue.get("items", []):
        if not item.get("required_action"):
            problems.append(f"{item.get('gap_id', '<unknown>')}: missing required_action")
        if not item.get("target_surface"):
            problems.append(f"{item.get('gap_id', '<unknown>')}: missing target_surface")
        if backpressure_item_blocks_writer(item):
            if item.get("status") != "open":
                status = str(item.get("status") or "").lower()
                if status not in BACKPRESSURE_WRITER_BLOCKING_STATUSES:
                    problems.append(
                        f"{item.get('gap_id', '<unknown>')}: open item status invalid"
                    )
        else:
            if item.get("resolution_mode") != "writer_constraint":
                problems.append(
                    f"{item.get('gap_id', '<unknown>')}: "
                    "non-blocking item lacks writer_constraint mode"
                )
            if not item.get("writer_constraint"):
                problems.append(
                    f"{item.get('gap_id', '<unknown>')}: missing writer constraint"
                )
            if item.get("target_surface") != "report_outline.md":
                problems.append(
                    f"{item.get('gap_id', '<unknown>')}: writer constraint targets wrong surface"
                )
        if not item.get("source_refs"):
            problems.append(f"{item.get('gap_id', '<unknown>')}: missing source refs")
    for item in queue.get("quarantined_items", []):
        if not item.get("problems"):
            problems.append(
                f"{item.get('quarantine_id', '<unknown>')}: missing quarantine reasons"
            )
        if not item.get("required_action"):
            problems.append(
                f"{item.get('quarantine_id', '<unknown>')}: missing repair action"
            )
    if problems:
        return fail_check("adequacy_backpressure_queue_present", "; ".join(problems))
    if expected_status == "writer_constraints":
        return pass_check(
            "adequacy_backpressure_queue_present",
            "Unresolved adequacy pressure is captured as writer-facing constraints.",
        )
    return pass_check(
        "adequacy_backpressure_queue_present",
        "Unresolved adequacy gaps are captured in a writer-blocking queue.",
    )


def check_backpressure_gate_receipt(run_dir: Path) -> dict[str, str]:
    if not is_mesh_run(run_dir):
        return pass_check(
            "backpressure_gate_receipt_valid",
            "Legacy bootstrap has no DR mesh backpressure gate receipt.",
        )
    queue_path = run_dir / "backpressure" / "adequacy_backpressure_queue.json"
    if not queue_path.exists():
        return pass_check(
            "backpressure_gate_receipt_valid",
            "No adequacy backpressure queue requires a gate receipt.",
        )
    try:
        queue = read_json(queue_path)
    except json.JSONDecodeError as error:
        return fail_check(
            "backpressure_gate_receipt_valid",
            f"Cannot derive gate receipt from invalid queue JSON: {error}",
        )
    if queue.get("schema_version") != BACKPRESSURE_QUEUE_SCHEMA_VERSION:
        return fail_check(
            "backpressure_gate_receipt_valid",
            "Gate receipt requires canonical backpressure queue v2.",
        )
    receipt_path = run_dir / "backpressure" / "backpressure_gate_receipt.json"
    try:
        receipt = read_json(receipt_path)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return fail_check(
            "backpressure_gate_receipt_valid",
            f"Backpressure queue exists without a valid gate receipt: {error}",
        )
    expected = backpressure_gate_receipt_payload(run_dir, queue)
    problems = []
    for field in [
        "schema_version",
        "run_id",
        "source_queue_path",
        "source_queue_schema_version",
        "queue_status",
        "gate_status",
        "writer_blocked",
        "writer_may_proceed",
        "open_writer_blocking_gap_ids",
        "quarantined_writer_blocking_item_ids",
        "writer_constraints",
        "required_before_writer",
    ]:
        if receipt.get(field) != expected.get(field):
            problems.append(f"{field} does not match canonical queue")
    claim_boundary = receipt.get("claim_boundary", {})
    if claim_boundary.get("may_widen_claims") is not False:
        problems.append("claim_boundary may_widen_claims must be false")
    if receipt.get("produced_by_event") is None:
        problems.append("produced_by_event is required")
    if problems:
        return fail_check("backpressure_gate_receipt_valid", "; ".join(problems))
    return pass_check(
        "backpressure_gate_receipt_valid",
        "Backpressure gate receipt is harness-derived from canonical queue state.",
    )


def check_writer_gate_preflight(run_dir: Path) -> dict[str, str]:
    if not is_mesh_run(run_dir):
        return pass_check(
            "writer_gate_preflight_valid",
            "Legacy bootstrap has no DR mesh writer preflight.",
        )
    preflight_path = run_dir / "writer_gate_preflight.json"
    blocked_live_run = is_live_mesh_blocked_by_adequacy(run_dir)
    if not preflight_path.exists():
        if blocked_live_run:
            return fail_check(
                "writer_gate_preflight_valid",
                "Live writer was blocked without a writer_gate_preflight.json artifact.",
            )
        return pass_check(
            "writer_gate_preflight_valid",
            "No writer preflight was required for this run.",
        )
    try:
        preflight = read_json(preflight_path)
    except json.JSONDecodeError as error:
        return fail_check(
            "writer_gate_preflight_valid",
            f"Writer gate preflight is invalid JSON: {error}",
        )
    expected = writer_gate_preflight_payload(run_dir)
    problems = []
    for field in [
        "schema_version",
        "run_id",
        "preflight_status",
        "may_writer_proceed",
        "writer_blocked",
        "source_gate_receipt",
        "source_queue",
        "blocking_reasons",
    ]:
        if preflight.get(field) != expected.get(field):
            problems.append(f"{field} does not match derived gate state")
    if blocked_live_run and preflight.get("may_writer_proceed") is not False:
        problems.append("blocked live run must have may_writer_proceed false")
    if problems:
        return fail_check("writer_gate_preflight_valid", "; ".join(problems))
    return pass_check(
        "writer_gate_preflight_valid",
        "Writer preflight matches harness-derived gate state.",
    )


def check_reentry_task_packets(run_dir: Path) -> dict[str, str]:
    if not is_mesh_run(run_dir):
        return pass_check(
            "reentry_task_packets_valid",
            "Legacy bootstrap has no DR mesh re-entry task packets.",
        )
    reentry_root = run_dir / "reentry"
    if not reentry_root.exists():
        return pass_check(
            "reentry_task_packets_valid",
            "No deterministic re-entry task packets were compiled for this run.",
        )
    problems = []
    for packet_path in sorted(reentry_root.rglob("reentry_task_packet.json")):
        try:
            packet = read_json(packet_path)
        except (FileNotFoundError, json.JSONDecodeError) as error:
            problems.append(f"{rel(packet_path, run_dir)}: unreadable packet: {error}")
            continue
        packet_problems = validate_reentry_task_packet_object(packet)
        relative = rel(packet_path, run_dir)
        if packet.get("packet_path") != relative:
            packet_problems.append("packet_path does not match file location")
        if packet_problems:
            problems.append(f"{relative}: " + "; ".join(packet_problems))
    if problems:
        return fail_check("reentry_task_packets_valid", "; ".join(problems))
    return pass_check(
        "reentry_task_packets_valid",
        "Deterministic re-entry task packets are valid and preserve "
        "writer/claim boundaries.",
    )


def check_reentry_synthesis_outputs(run_dir: Path) -> dict[str, str]:
    if not is_mesh_run(run_dir):
        return pass_check(
            "reentry_synthesis_outputs_valid",
            "Legacy bootstrap has no DR mesh re-entry synthesis outputs.",
        )
    problems: list[str] = []
    inspected = 0
    for packet in ready_reentry_packets(run_dir):
        gap_id = str(packet.get("source_gap_id") or "")
        results = reentry_results_for_gap(run_dir, gap_id)
        if not results:
            continue
        paths = reentry_integration_paths_for_packet(packet)
        if not paths:
            problems.append(f"{gap_id}: cannot derive re-entry integration paths")
            continue
        inspected += 1
        synthesis_path = run_dir / paths["reentry_synthesis"]
        delta_path = run_dir / paths["adequacy_delta"]
        if not synthesis_path.exists():
            problems.append(f"{gap_id}: missing {paths['reentry_synthesis']}")
        elif gap_id not in synthesis_path.read_text(encoding="utf-8"):
            problems.append(f"{gap_id}: reentry_synthesis.md does not name source gap")
        try:
            delta = read_json(delta_path)
        except (FileNotFoundError, json.JSONDecodeError) as error:
            problems.append(f"{gap_id}: adequacy_delta unavailable: {error}")
            continue
        if delta.get("schema_version") != REENTRY_ADEQUACY_DELTA_SCHEMA_VERSION:
            problems.append(f"{gap_id}: invalid adequacy_delta schema_version")
        if delta.get("source_gap_id") != gap_id:
            problems.append(f"{gap_id}: adequacy_delta source_gap_id mismatch")
        if delta.get("source_task_packet_path") != packet.get("packet_path"):
            problems.append(f"{gap_id}: adequacy_delta packet path mismatch")
        if delta.get("reentry_synthesis_path") != paths["reentry_synthesis"]:
            problems.append(f"{gap_id}: adequacy_delta synthesis path mismatch")
        if "reviewer" not in str(delta.get("closure_authority") or "").lower():
            problems.append(f"{gap_id}: adequacy_delta closure authority not reviewer-owned")
        if delta.get("closure_authorized") is not False:
            problems.append(f"{gap_id}: adequacy_delta cannot authorize closure")
        if delta.get("writer_permission") is not False:
            problems.append(f"{gap_id}: adequacy_delta cannot authorize writer")
        if delta.get("proposed_next_status") not in REENTRY_RESULT_STATUSES:
            problems.append(f"{gap_id}: adequacy_delta has invalid proposed_next_status")
        if not delta.get("reviewer_next_action"):
            problems.append(f"{gap_id}: adequacy_delta missing reviewer_next_action")
    if problems:
        return fail_check("reentry_synthesis_outputs_valid", "; ".join(problems))
    if inspected:
        return pass_check(
            "reentry_synthesis_outputs_valid",
            "Re-entry synthesis outputs integrate repair artifacts without closure authority.",
        )
    return pass_check(
        "reentry_synthesis_outputs_valid",
        "No completed deterministic re-entry repair required synthesis integration.",
    )


def check_citation_support_maps(run_dir: Path) -> dict[str, str]:
    if not is_mesh_run(run_dir):
        return pass_check(
            "citation_support_maps_valid",
            "Legacy bootstrap has no DR mesh citation-support maps.",
        )
    packet_by_gap = {
        str(packet.get("source_gap_id")): packet
        for packet in ready_reentry_packets(run_dir)
        if packet.get("source_gap_id")
    }
    problems: list[str] = []
    inspected = 0
    for result_path in reentry_result_paths(run_dir):
        try:
            result = read_json(result_path)
        except json.JSONDecodeError as error:
            problems.append(f"{rel(result_path, run_dir)}: invalid reentry_result: {error}")
            continue
        gap_id = str(result.get("source_gap_id") or "")
        proposed_status = str(result.get("proposed_next_status") or "")
        packet = packet_by_gap.get(gap_id)
        packet_outputs = []
        if packet and isinstance(packet.get("task"), dict):
            packet_outputs = packet["task"].get("required_outputs", [])
        requires_citation_map = (
            "citation_support_map.json" in packet_outputs
            or result.get("failure_type") == "citation_support_gap"
        )
        map_path = citation_support_map_path_for_result(result_path)
        if requires_citation_map and proposed_status == "closed_candidate" and not map_path.exists():
            problems.append(
                f"{rel(result_path, run_dir)}: closed_candidate lacks citation_support_map.json"
            )
            continue
        if not map_path.exists():
            continue
        inspected += 1
        try:
            support_map = read_json(map_path)
        except json.JSONDecodeError as error:
            problems.append(
                f"{rel(map_path, run_dir)}: invalid citation_support_map JSON: {error}"
            )
            continue
        map_problems = validate_citation_support_map_object(
            support_map,
            require_no_writer_blocking=proposed_status == "closed_candidate",
        )
        if support_map.get("source_gap_id") != gap_id:
            map_problems.append("citation_support_map source_gap_id mismatch")
        if proposed_status == "closed_candidate" and map_problems:
            problems.extend(f"{rel(map_path, run_dir)}: {problem}" for problem in map_problems)
        else:
            severe = [
                problem
                for problem in map_problems
                if "invalid" in problem or "mismatch" in problem
            ]
            problems.extend(f"{rel(map_path, run_dir)}: {problem}" for problem in severe)
    for map_path in sorted(run_dir.glob("branches/*/citation_support_map.json")):
        if any(citation_support_map_path_for_result(path) == map_path for path in reentry_result_paths(run_dir)):
            continue
        try:
            support_map = read_json(map_path)
        except json.JSONDecodeError as error:
            problems.append(
                f"{rel(map_path, run_dir)}: invalid citation_support_map JSON: {error}"
            )
            continue
        inspected += 1
        problems.extend(
            f"{rel(map_path, run_dir)}: {problem}"
            for problem in validate_citation_support_map_object(
                support_map,
                require_no_writer_blocking=False,
            )
        )
    if problems:
        return fail_check("citation_support_maps_valid", "; ".join(problems))
    if inspected:
        return pass_check(
            "citation_support_maps_valid",
            "Citation-support maps preserve statement-to-source support without self-closure.",
        )
    return pass_check(
        "citation_support_maps_valid",
        "No citation-support closure evidence was required for this run.",
    )


def check_review_reentry(run_dir: Path) -> dict[str, str]:
    review_path = run_dir / "reviews" / "review_001.json"
    decisions_path = run_dir / "reentry_decisions.jsonl"
    graph_path = run_dir / "task_graph.json"
    try:
        review = read_json(review_path)
        decisions = read_jsonl(decisions_path)
        graph = read_json(graph_path)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return fail_check(
            "review_reentry_compiled", f"Review re-entry artifacts unavailable: {error}"
        )
    required_findings = [
        finding
        for finding in review.get("findings", [])
        if finding.get("requires_reentry") or finding.get("requires_more_research")
    ]
    proposed_items = [
        item
        for item in review.get("proposed_backpressure_items", [])
        if isinstance(item, dict)
        and review_gate_effect_enabled(item.get("gate_effects"), "reentry_required")
    ]
    if proposed_items:
        queue = read_optional_json(run_dir / "backpressure" / "adequacy_backpressure_queue.json")
        queued_gap_ids = {item.get("gap_id") for item in queue.get("items", [])}
        quarantined_gap_ids = {
            item.get("raw_gap_id")
            for item in queue.get("quarantined_items", [])
            if item.get("raw_gap_id")
        }
        proposed_gap_ids = {item.get("gap_id") for item in proposed_items}
        if proposed_gap_ids <= (queued_gap_ids | quarantined_gap_ids):
            return pass_check(
                "review_reentry_compiled",
                "Review proposed backpressure items were compiled or quarantined by the canonical queue compiler.",
            )
        return fail_check(
            "review_reentry_compiled",
            "Review proposed backpressure items are missing from the canonical queue: "
            + ", ".join(sorted(proposed_gap_ids - queued_gap_ids)),
        )
    decision_by_finding = {decision.get("finding_id"): decision for decision in decisions}
    task_ids = {task.get("task_id") for task in graph.get("tasks", [])}
    missing = []
    for finding in required_findings:
        finding_id = finding.get("finding_id") or finding.get("id")
        if not finding_id:
            missing.append("<missing finding id>")
            continue
        decision = decision_by_finding.get(finding_id)
        if not decision:
            if is_live_mesh_run(run_dir) and (
                run_dir / "branches" / "reentry_followup" / "pointer.md"
            ).exists():
                continue
            missing.append(finding_id)
            continue
        if (
            decision.get("decision") == "create_task"
            and decision.get("created_task_id") not in task_ids
        ):
            if is_live_mesh_run(run_dir) and (
                run_dir / "branches" / "reentry_followup" / "pointer.md"
            ).exists():
                continue
            missing.append(f"{finding_id} missing task")
    if not required_findings or missing:
        return fail_check(
            "review_reentry_compiled", f"Missing re-entry decisions: {', '.join(missing)}"
        )
    return pass_check("review_reentry_compiled", "Review finding compiled into re-entry task.")


def review_gate_effect_enabled(gate_effects: Any, gate_name: str) -> bool:
    if isinstance(gate_effects, dict):
        return gate_effects.get(gate_name) is True
    if isinstance(gate_effects, list):
        return gate_name in {str(item) for item in gate_effects}
    return False


def check_reviewer_output_whitelist(run_dir: Path) -> dict[str, str]:
    if not is_mesh_run(run_dir):
        return pass_check(
            "reviewer_output_whitelist",
            "Legacy bootstrap has no live reviewer output whitelist.",
        )
    reviewer_output_root = run_dir / "live_executor" / "role_outputs" / "task_review"
    if not reviewer_output_root.exists():
        return pass_check(
            "reviewer_output_whitelist",
            "No live reviewer output bundle to inspect.",
        )
    forbidden = [
        relative
        for relative in sorted(REVIEWER_FORBIDDEN_OUTPUTS)
        if (reviewer_output_root / relative).exists()
    ]
    if forbidden:
        return fail_check(
            "reviewer_output_whitelist",
            "Reviewer produced forbidden output(s): " + ", ".join(forbidden),
        )
    role_outputs_root = run_dir / "live_executor" / "role_outputs"
    reentry_forbidden = []
    if role_outputs_root.exists():
        for output_root in sorted(role_outputs_root.glob("task_reentry_followup*")):
            for relative in sorted(REENTRY_FORBIDDEN_OUTPUTS):
                if (output_root / relative).exists():
                    reentry_forbidden.append(f"{output_root.name}:{relative}")
    if reentry_forbidden:
        return fail_check(
            "reviewer_output_whitelist",
            "Re-entry branch produced forbidden output(s): " + ", ".join(reentry_forbidden),
        )
    return pass_check(
        "reviewer_output_whitelist",
        "Reviewer and re-entry custody did not produce canonical queue, gate, "
        "writer, score, or claim files.",
    )


def check_compaction_receipt(run_dir: Path) -> dict[str, str]:
    path = run_dir / "compactions" / "compaction_001.json"
    if not path.exists():
        return fail_check("compaction_receipt_present", "Compaction receipt is missing.")
    receipt = read_json(path)
    if not receipt.get("claim_impact"):
        return fail_check("compaction_receipt_present", "Compaction receipt lacks claim impact.")
    return pass_check("compaction_receipt_present", "Compaction receipt is present.")


def check_scorer_manifest(run_dir: Path) -> dict[str, str]:
    if not is_mesh_run(run_dir):
        return pass_check(
            "draco_scorer_manifest_valid", "Legacy bootstrap has no DRACO scorer manifest."
        )
    try:
        manifest = read_json(run_dir / "scorer_manifest.json")
        score = read_json(run_dir / "benchmark_score.json")
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return fail_check("draco_scorer_manifest_valid", f"Scorer artifacts unavailable: {error}")
    if manifest.get("schema_version") == "codex-dr.deepresearch_bench_race_scorer_manifest.v1":
        return check_deepresearch_bench_scorer_manifest(run_dir, manifest, score)
    problems = []
    if manifest.get("schema_version") != "codex-dr.draco_scorer_manifest.v1":
        problems.append("invalid scorer manifest schema_version")
    if manifest.get("benchmark_family") != "DRACO":
        problems.append("benchmark_family must be DRACO")
    judge_policy = manifest.get("judge_policy")
    if not isinstance(judge_policy, dict):
        problems.append("missing judge policy")
    elif not all(judge_policy.get(field) for field in ["kind", "provider", "model"]):
        problems.append("judge policy missing kind/provider/model")
    if not manifest.get("rubric_mapping"):
        problems.append("missing rubric mapping")
    if not manifest.get("scoring_formula"):
        problems.append("missing scoring formula")
    if not manifest.get("sealed_reference_policy"):
        problems.append("missing sealed-reference policy")
    if not manifest.get("retry_policy"):
        problems.append("missing retry policy")
    if not manifest.get("variance_policy"):
        problems.append("missing variance policy")
    output_paths = manifest.get("output_paths", {})
    if not output_paths.get("benchmark_score") or not output_paths.get("evaluation_output"):
        problems.append("missing scorer output paths")
    score_values = [score.get("score"), score.get("raw_score"), score.get("normalized_score")]
    score_has_numeric_value = any(value is not None for value in score_values)
    scorer_has_custody = (
        manifest.get("scorer_status") in {"approved", "executed"}
        and manifest.get("execution_allowed") is True
        and manifest.get("scorer_execution", {}).get("executed_with_custody") is True
    )
    if manifest.get("scorer_status") == "executed":
        execution = manifest.get("scorer_execution", {})
        if not execution.get("receipt_ref"):
            problems.append("executed scorer manifest lacks receipt_ref")
        for ref in execution.get("judge_transcript_refs", []):
            if not reference_exists(run_dir, ref):
                problems.append(f"missing scorer transcript ref {ref}")
    if score_has_numeric_value and not scorer_has_custody:
        problems.append("non-null benchmark score lacks scorer custody")
    if problems:
        return fail_check("draco_scorer_manifest_valid", "; ".join(problems))
    return pass_check(
        "draco_scorer_manifest_valid",
        "DRACO scorer manifest is present and any numeric score is custody-backed.",
    )


def check_deepresearch_bench_scorer_manifest(
    run_dir: Path, manifest: dict[str, Any], score: dict[str, Any]
) -> dict[str, str]:
    problems = []
    if manifest.get("benchmark_family") != BENCHMARK_FAMILY_DEEPRESEARCH_BENCH:
        problems.append("benchmark_family must be DEEPRESEARCH_BENCH")
    valid_statuses = {
        "blocked",
        "failed",
        "scored_claims_blocked",
        "executed",
    }
    if manifest.get("scorer_status") not in valid_statuses:
        problems.append("invalid DeepResearch Bench scorer_status")
    lane = manifest.get("evaluator_lane", {})
    if lane.get("name") != "RACE":
        problems.append("evaluator lane must be RACE")
    if not manifest.get("official_scorer", {}).get("command_plan"):
        problems.append("official scorer command plan is missing")
    output_paths = manifest.get("output_paths", {})
    for field in ["bridge_receipt", "evaluation_output"]:
        ref = output_paths.get(field)
        if not ref or not (run_dir / ref).exists():
            problems.append(f"missing scorer output path {field}")
    score_has_numeric_value = any(
        score.get(field) is not None for field in ["score", "raw_score", "normalized_score"]
    )
    execution = manifest.get("execution", {})
    scorer_executed = manifest.get("scorer_status") in {
        "executed",
        "scored_claims_blocked",
    }
    if score_has_numeric_value and not (scorer_executed and execution.get("ran") is True):
        problems.append("numeric DeepResearch Bench score lacks executed scorer custody")
    if score.get("claims_enabled") is not False:
        problems.append("DeepResearch Bench scorer manifest cannot open claims directly")
    if problems:
        return fail_check("draco_scorer_manifest_valid", "; ".join(problems))
    return pass_check(
        "draco_scorer_manifest_valid",
        "DeepResearch Bench RACE scorer manifest is custody-backed or explicitly blocked.",
    )


def check_benchmark_placeholder(run_dir: Path) -> dict[str, str]:
    try:
        score = read_json(run_dir / "benchmark_score.json")
        manifest = read_json(run_dir / "scorer_manifest.json") if is_mesh_run(run_dir) else {}
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return fail_check(
            "benchmark_placeholder_not_score", f"Benchmark placeholder unavailable: {error}"
        )
    if score.get("mode") == "blocked_no_score":
        score_values = [score.get("score"), score.get("raw_score"), score.get("normalized_score")]
        if any(value is not None for value in score_values):
            return fail_check(
                "benchmark_placeholder_not_score",
                "Blocked benchmark state contains numeric score fields.",
            )
        if score.get("claims_enabled") is not False:
            return fail_check(
                "benchmark_placeholder_not_score",
                "Blocked benchmark state widened claims.",
            )
        return pass_check(
            "benchmark_placeholder_not_score",
            "Benchmark scoring is explicitly blocked without score claims.",
        )
    if score.get("mode") != "provider_off_placeholder":
        if score.get("mode") != "scored_claims_blocked":
            return fail_check(
                "benchmark_placeholder_not_score",
                f"Unexpected benchmark mode {score.get('mode')!r}.",
            )
        numeric_values = [score.get("score"), score.get("raw_score"), score.get("normalized_score")]
        if any(value is None for value in numeric_values):
            return fail_check(
                "benchmark_placeholder_not_score",
                "Scored benchmark state lacks numeric score fields.",
            )
        if score.get("claims_enabled") is not False:
            return fail_check(
                "benchmark_placeholder_not_score",
                "Scored benchmark state widened claims without review.",
            )
        if manifest.get("scorer_execution", {}).get("executed_with_custody") is not True:
            return fail_check(
                "benchmark_placeholder_not_score",
                "Scored benchmark state lacks scorer execution custody.",
            )
        evaluation_output = score.get("evaluation_output")
        if not evaluation_output or not reference_exists(run_dir, evaluation_output):
            return fail_check(
                "benchmark_placeholder_not_score",
                "Scored benchmark state lacks evaluation output custody.",
            )
        return pass_check(
            "benchmark_placeholder_not_score",
            "Benchmark score state is scorer-backed and still claim-gated.",
        )
    if score.get("score") is not None or score.get("claims_enabled") is not False:
        return fail_check(
            "benchmark_placeholder_not_score",
            "Provider-off benchmark placeholder looks like a score.",
        )
    return pass_check("benchmark_placeholder_not_score", "Benchmark output is a placeholder only.")


def check_evaluation_ledger_claim_gate(run_dir: Path) -> dict[str, str]:
    if not is_mesh_run(run_dir):
        return pass_check(
            "benchmark_evaluation_claim_gate_enforced",
            "Legacy bootstrap has no benchmark evaluation ledger.",
        )
    try:
        ledger = read_json(run_dir / "evaluation_ledger.json")
        score = read_json(run_dir / "benchmark_score.json")
        manifest = read_json(run_dir / "scorer_manifest.json")
        allowed = read_json(run_dir / "allowed_claims.json")
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return fail_check(
            "benchmark_evaluation_claim_gate_enforced",
            f"Evaluation ledger artifacts unavailable: {error}",
        )
    problems = []
    for field in [
        "scorer_manifest",
        "result_status",
        "failure_taxonomy",
        "improvement_recommendations",
        "allowed_claim_impact",
    ]:
        if not ledger.get(field):
            problems.append(f"missing {field}")
    impact = ledger.get("allowed_claim_impact", {})
    scorer_custody = (
        manifest.get("scorer_status") in {"approved", "executed"}
        and manifest.get("execution_allowed") is True
        and manifest.get("scorer_execution", {}).get("executed_with_custody") is True
    )
    score_is_supported = (
        score.get("score") is not None
        and score.get("claims_enabled") is True
        and scorer_custody
    )
    evaluation_blocks_claims = (
        score.get("score") is None
        or score.get("mode") == "provider_off_placeholder"
        or score.get("claims_enabled") is not True
        or ledger.get("result_status") in {"blocked_no_score", "failed", "null"}
        or not scorer_custody
    )
    if evaluation_blocks_claims and impact.get("may_widen_claims") is not False:
        problems.append("evaluation attempts to widen claims without supported score")
    if evaluation_blocks_claims and impact.get("claim_gate_status") != "blocked":
        problems.append("claim gate is not blocked for unsupported evaluation")
    blocked_phrases = [
        "draco score",
        "deepresearch bench score",
        "grep parity",
        "leaderboard rank",
    ]
    for claim in allowed.get("allowed_claims", []):
        text = claim.get("claim", "").lower()
        if evaluation_blocks_claims and any(phrase in text for phrase in blocked_phrases):
            problems.append(f"allowed claim exceeds evaluation support: {claim['claim']}")
    if score_is_supported and impact.get("claim_gate_status") not in {"review_required", "open"}:
        problems.append("supported score still requires explicit claim-gate review status")
    if problems:
        return fail_check("benchmark_evaluation_claim_gate_enforced", "; ".join(problems))
    return pass_check(
        "benchmark_evaluation_claim_gate_enforced",
        "Benchmark evaluation ledger keeps unsupported score claims blocked.",
    )


def check_self_improvement_replay_gate(run_dir: Path) -> dict[str, str]:
    if not is_mesh_run(run_dir):
        return pass_check(
            "self_improvement_replay_gate_enforced",
            "Legacy bootstrap has no self-improvement replay loop.",
        )
    try:
        corpus = read_json(run_dir / "self_improvement" / "replay_corpus.json")
        taxonomy = read_json(run_dir / "self_improvement" / "failure_taxonomy.json")
        proposal = read_json(run_dir / "self_improvement" / "improvement_proposal.json")
        regression = read_json(run_dir / "self_improvement" / "regression_gate.json")
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return fail_check(
            "self_improvement_replay_gate_enforced",
            f"Self-improvement artifacts unavailable: {error}",
        )
    problems = []
    fixture_kinds = {fixture.get("kind") for fixture in corpus.get("fixtures", [])}
    if {"failed_evaluation", "corrected_fixture"} - fixture_kinds:
        problems.append("replay corpus lacks failed and corrected fixtures")
    if corpus.get("source_evaluation_ledger") != "evaluation_ledger.json":
        problems.append("replay corpus lacks evaluation ledger source")
    if not corpus.get("evaluation_failures"):
        problems.append("replay corpus lacks evaluation failures")
    required_classes = {
        "prompt",
        "source",
        "citation",
        "evidence",
        "synthesis",
        "task_graph",
        "reviewer",
        "writer",
        "claim_boundary",
    }
    present_classes = {item.get("class_id") for item in taxonomy.get("failure_classes", [])}
    missing_classes = required_classes - present_classes
    if missing_classes:
        problems.append(f"failure taxonomy missing classes: {', '.join(sorted(missing_classes))}")
    if not proposal.get("suggested_patch"):
        problems.append("improvement proposal lacks suggested patch")
    if proposal.get("source_evaluation_ledger") != "evaluation_ledger.json":
        problems.append("improvement proposal lacks evaluation ledger source")
    if not proposal.get("source_evaluation_failures"):
        problems.append("improvement proposal lacks source evaluation failures")
    if not proposal.get("target_surfaces"):
        problems.append("improvement proposal lacks target surfaces")
    if proposal.get("promotion_status") != "proposed_not_promoted":
        problems.append("improvement proposal was promoted")
    if proposal.get("auto_promotion_allowed") is not False:
        problems.append("improvement proposal allows auto-promotion")
    if proposal.get("automatic_skill_mutation_allowed") is not False:
        problems.append("improvement proposal allows automatic skill mutation")
    if regression.get("prior_passing_cases_remain_passing") is not True:
        problems.append("regression gate does not preserve passing cases")
    if regression.get("failed_cases_cannot_widen_claims") is not True:
        problems.append("regression gate allows failed cases to widen claims")
    if regression.get("regression_evidence_required_for_promotion") is not True:
        problems.append("regression evidence is not required for promotion")
    if regression.get("automatic_skill_mutation_allowed") is not False:
        problems.append("regression gate allows automatic skill mutation")
    if regression.get("proposal_promotion_allowed") is not False:
        problems.append("regression gate allows proposal promotion")
    candidates_path = run_dir / "self_improvement" / "improvement_candidates.json"
    if candidates_path.exists():
        candidate_problems = improvement_candidate_problems(candidates_path, corpus)
        problems.extend(candidate_problems)
    gate_results_path = run_dir / "self_improvement" / "candidate_gate_results.json"
    if gate_results_path.exists():
        gate_problems = improvement_candidate_gate_problems(
            gate_results_path,
            regression,
            candidates_path,
            run_dir,
        )
        problems.extend(gate_problems)
    for mutation in regression.get("live_surface_mutations", []):
        receipt_ref = mutation.get("promotion_receipt")
        receipt = read_json(run_dir / receipt_ref) if receipt_ref else {}
        if mutation.get("live_surface_changed") is True and receipt.get("decision") != "promoted":
            problems.append(
                "live surface mutation lacks promoted candidate promotion receipt"
            )
    if problems:
        return fail_check("self_improvement_replay_gate_enforced", "; ".join(problems))
    return pass_check(
        "self_improvement_replay_gate_enforced",
        "Provider-off self-improvement replay loop is bounded and not promoted.",
    )


def improvement_candidate_problems(
    candidates_path: Path, corpus: dict[str, Any]
) -> list[str]:
    problems: list[str] = []
    try:
        payload = read_json(candidates_path)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return [f"improvement candidates unavailable: {error}"]
    if payload.get("schema_version") != "codex-dr.deepresearch_bench_improvement_candidates.v1":
        problems.append("improvement candidates have invalid schema_version")
    candidates = payload.get("candidates", [])
    if not candidates:
        problems.append("improvement candidates list is empty")
        return problems
    fixture_ids = {fixture.get("fixture_id") for fixture in corpus.get("fixtures", [])}
    seen_ids: set[str] = set()
    required_fields = {
        "candidate_id",
        "target_surface_type",
        "target_surface",
        "source_failure_refs",
        "proposed_change",
        "expected_effect",
        "replay_fixtures",
        "promotion_gate",
    }
    allowed_surface_types = {
        "prompt",
        "skill",
        "scheduler",
        "file_context",
        "evaluator",
    }
    for candidate in candidates:
        candidate_id = candidate.get("candidate_id", "<missing>")
        if candidate_id in seen_ids:
            problems.append(f"duplicate improvement candidate {candidate_id}")
        seen_ids.add(candidate_id)
        missing = sorted(field for field in required_fields if not candidate.get(field))
        if missing:
            problems.append(f"{candidate_id} missing fields: {', '.join(missing)}")
        if candidate.get("target_surface_type") not in allowed_surface_types:
            problems.append(f"{candidate_id} has invalid target_surface_type")
        source_refs = candidate.get("source_failure_refs", [])
        if not all(ref.get("path") and ref.get("failure_class") for ref in source_refs):
            problems.append(f"{candidate_id} has invalid source_failure_refs")
        replay_fixtures = set(candidate.get("replay_fixtures", []))
        if not replay_fixtures <= fixture_ids:
            missing_fixtures = ", ".join(sorted(replay_fixtures - fixture_ids))
            problems.append(
                f"{candidate_id} references missing replay fixtures: {missing_fixtures}"
            )
        gate = candidate.get("promotion_gate", {})
        if gate.get("requires_regression") is not True:
            problems.append(f"{candidate_id} lacks regression promotion gate")
        if gate.get("requires_replay_fixture") is not True:
            problems.append(f"{candidate_id} lacks replay fixture promotion gate")
        if candidate.get("promotion_status") != "proposed_not_promoted":
            problems.append(f"{candidate_id} was promoted")
        if candidate.get("auto_promotion_allowed") is not False:
            problems.append(f"{candidate_id} allows auto-promotion")
        if candidate.get("automatic_skill_mutation_allowed") is not False:
            problems.append(f"{candidate_id} allows automatic skill mutation")
        if candidate.get("claim_impact") != "no claim widening":
            problems.append(f"{candidate_id} can widen claims")
    if payload.get("candidate_count") != len(candidates):
        problems.append("improvement candidate count mismatch")
    return problems


def improvement_candidate_gate_problems(
    gate_results_path: Path,
    regression: dict[str, Any],
    candidates_path: Path,
    run_dir: Path,
) -> list[str]:
    problems: list[str] = []
    try:
        payload = read_json(gate_results_path)
        candidates = read_json(candidates_path)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return [f"improvement candidate gate unavailable: {error}"]
    if payload.get("schema_version") != "codex-dr.deepresearch_bench_candidate_gate_results.v1":
        problems.append("candidate gate results have invalid schema_version")
    results = payload.get("results", [])
    candidate_ids = {
        candidate.get("candidate_id") for candidate in candidates.get("candidates", [])
    }
    result_ids = {result.get("candidate_id") for result in results}
    if candidate_ids != result_ids:
        problems.append("candidate gate results do not cover every candidate")
    if payload.get("all_candidates_gated") is not True:
        problems.append("candidate gate did not mark all candidates gated")
    if payload.get("live_surface_changed") is not False:
        problems.append("candidate gate changed live surface without promotion")
    if regression.get("candidate_gate_results") != "self_improvement/candidate_gate_results.json":
        problems.append("regression gate does not reference candidate gate results")
    for result in results:
        candidate_id = result.get("candidate_id", "<missing>")
        if result.get("promotion_status") == "promoted" and result.get("decision") != "promoted":
            problems.append(f"{candidate_id} has inconsistent promotion status")
        if result.get("live_surface_changed") is True and result.get("decision") != "promoted":
            problems.append(f"{candidate_id} changed live surface without promotion")
        for field in ["patch_preview", "replay_result", "promotion_receipt"]:
            ref = result.get(field)
            if not ref or not (run_dir / ref).exists():
                problems.append(f"{candidate_id} missing {field}")
        receipt_ref = result.get("promotion_receipt")
        if receipt_ref and (run_dir / receipt_ref).exists():
            receipt = read_json(run_dir / receipt_ref)
            if receipt.get("live_surface_changed") is not False:
                problems.append(f"{candidate_id} receipt changed live surface")
            if receipt.get("promotion_status") == "promoted":
                problems.append(f"{candidate_id} was promoted by replay gate")
    return problems


def check_live_execution_custody(run_dir: Path) -> dict[str, str]:
    if not is_live_mesh_run(run_dir):
        return pass_check(
            "live_execution_custody_present",
            "No live execution manifest is present for this provider-off run.",
        )
    try:
        summary = read_json(run_dir / "live_executor" / "execution_summary.json")
        receipt = read_json(run_dir / "live_executor" / "run_control_receipt.json")
        launch_plan = read_json(run_dir / "live_adapter" / "launch_plan.json")
        context_index = read_json(run_dir / "live_executor" / "context_thread_index.json")
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return fail_check("live_execution_custody_present", f"Live custody unavailable: {error}")
    problems = []
    if summary.get("schema_version") != "codex-dr.live_execution_summary.v1":
        problems.append("invalid live execution summary schema")
    execution_status = summary.get("execution_status")
    allowed_statuses = {"succeeded", "blocked_by_adequacy_backpressure"}
    if execution_status not in allowed_statuses:
        problems.append("live execution summary did not reach a lawful terminal state")
    if receipt.get("approval", {}).get("approved_for_execution") is not True:
        problems.append("run-control receipt is not approved for execution")
    bounds = receipt.get("operational_bounds", {})
    if bounds.get("max_cases") != 1 or bounds.get("max_live_attempts") != 1:
        problems.append("live run exceeded bounded max_cases/max_live_attempts policy")
    if bounds.get("automatic_retry_allowed") is not False:
        problems.append("automatic retry is not blocked")
    if receipt.get("scoring", {}).get("scorer_status") != "blocked":
        problems.append("scorer status is not blocked")
    if launch_plan.get("launch_mode") != "live_authorized_pending_execution":
        problems.append("launch plan was not live-authorized pending execution")
    expected_roles = [
        *launch_plan.get("role_launch_plans", []),
        *summary.get("dynamic_role_launch_plans", []),
    ]
    actual_roles = summary.get("roles", [])
    blocked_task_ids = set(summary.get("blocked_task_ids", []))
    expected_executed_roles = [
        role for role in expected_roles if role.get("task_id") not in blocked_task_ids
    ]
    if execution_status == "succeeded" and len(actual_roles) != len(expected_roles):
        problems.append("role execution count does not match launch plan")
    if execution_status == "blocked_by_adequacy_backpressure":
        if "task_final_writer" not in blocked_task_ids:
            problems.append("blocked adequacy run must name task_final_writer as blocked")
        if len(actual_roles) != len(expected_executed_roles):
            problems.append("blocked role execution count does not match lawful prefix")
        try:
            queue = read_json(run_dir / "backpressure" / "adequacy_backpressure_queue.json")
            if queue.get("queue_status") != "open" or queue.get("writer_blocked") is not True:
                problems.append("blocked adequacy run lacks an open writer-blocking queue")
        except (FileNotFoundError, json.JSONDecodeError) as error:
            problems.append(f"blocked adequacy queue unavailable: {error}")
    if context_index.get("schema_version") != "codex-dr.context_thread_index.v1":
        problems.append("context/thread index schema is invalid")
    if context_index.get("role_count") != len(actual_roles):
        problems.append("context/thread index role count does not match execution summary")
    indexed_roles = {
        role.get("task_id"): role for role in context_index.get("roles", [])
    }
    scheduler = summary.get("scheduler", {})
    if scheduler.get("schema_version") != "codex-dr.live_dependency_scheduler.v1":
        problems.append("live scheduler summary is missing or invalid")
    if scheduler.get("scheduling_mode") != "dependency_aware_parallel":
        problems.append("live scheduler did not run in dependency-aware parallel mode")
    concurrency_groups = scheduler.get("concurrency_groups", [])
    if not concurrency_groups:
        problems.append("live scheduler recorded no concurrency groups")
    branch_parallel_set = {"task_deep_search", "task_data_analysis", "task_verification"}
    expected_task_ids = {role.get("task_id") for role in expected_roles}
    if branch_parallel_set.issubset(expected_task_ids):
        parallel_group_found = any(
            branch_parallel_set.issubset(set(group.get("task_ids", [])))
            for group in concurrency_groups
        )
        if not parallel_group_found:
            problems.append(
                "independent branch tasks were not scheduled in the same concurrency group"
            )
        if int(scheduler.get("max_parallel_roles") or 0) < len(branch_parallel_set):
            problems.append("live scheduler max_parallel_roles does not prove branch fan-out")
    dependency_roles = (
        expected_executed_roles
        if execution_status == "blocked_by_adequacy_backpressure"
        else expected_roles
    )
    graph_dependencies = {
        role.get("task_id", "<unknown>"): role.get("depends_on", [])
        for role in dependency_roles
    }
    dynamic_syntheses = [
        role.get("task_id")
        for role in summary.get("dynamic_role_launch_plans", [])
        if str(role.get("task_id", "")).startswith("task_reentry_synthesis_")
    ]
    if dynamic_syntheses and "task_final_writer" in graph_dependencies:
        graph_dependencies["task_final_writer"] = [dynamic_syntheses[-1]]
    role_order = [role.get("task_id", "<unknown>") for role in actual_roles]
    problems.extend(dependency_order_problems(role_order, graph_dependencies))
    if blocked_task_ids & set(role_order):
        problems.append("blocked task appears in executed role list")
    for role in actual_roles:
        task_id = role.get("task_id", "<unknown>")
        if role.get("returncode") != 0:
            problems.append(f"{task_id}: non-zero returncode")
        indexed_role = indexed_roles.get(task_id)
        if not indexed_role:
            problems.append(f"{task_id}: missing from context/thread index")
        elif not indexed_role.get("thread_ids"):
            problems.append(f"{task_id}: context/thread index lacks thread ids")
        transcript_path = role.get("transcript_path")
        if not transcript_path or not (run_dir / transcript_path).exists():
            problems.append(f"{task_id}: transcript missing")
        last_message_path = role.get("last_message_path")
        if not last_message_path or not (run_dir / last_message_path).exists():
            problems.append(f"{task_id}: last message missing")
        if not role.get("copied_outputs"):
            problems.append(f"{task_id}: live role outputs missing")
        for output in role.get("copied_outputs", []):
            if not (run_dir / output).exists():
                problems.append(f"{task_id}: copied output missing {output}")
    if problems:
        return fail_check("live_execution_custody_present", "; ".join(problems))
    return pass_check(
        "live_execution_custody_present",
        (
            "Live execution has approved receipt, per-role transcripts, outputs, and no scorer."
            if execution_status == "succeeded"
            else "Live execution lawfully stopped on adequacy backpressure with custody."
        ),
    )


def check_report_claims_in_ledger(run_dir: Path) -> dict[str, str]:
    try:
        ledger = read_json(run_dir / "claim_ledger.json")
        report = (run_dir / "report.md").read_text(encoding="utf-8")
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return fail_check("report_claims_in_ledger", f"Claim ledger or report unavailable: {error}")
    problems = []
    for claim in ledger.get("claims", []):
        if claim.get("status") != "admitted":
            continue
        if not claim.get("source_artifact_refs") or not claim.get("intermediate_artifact_refs"):
            problems.append(f"{claim['claim_id']}: missing custody refs")
        should_check_report_text = not (
            is_live_mesh_run(run_dir) and claim.get("materiality") == "provider_off_topology"
        )
        if should_check_report_text and not claim_text_represented_in_report(
            claim.get("text", ""), report
        ):
            problems.append(f"{claim['claim_id']}: claim text absent from report")
        for ref in claim.get("source_artifact_refs", []) + claim.get(
            "intermediate_artifact_refs", []
        ):
            ref_path = ref.split("#", 1)[0]
            if not (run_dir / ref_path).exists():
                problems.append(f"{claim['claim_id']}: missing ref {ref_path}")
    if problems:
        return fail_check("report_claims_in_ledger", "; ".join(problems))
    return pass_check("report_claims_in_ledger", "Report claims are represented in claim ledger.")


def check_claim_review_artifact(run_dir: Path) -> dict[str, str]:
    claim_review_path = run_dir / "claim_review.json"
    allowed_path = run_dir / "allowed_claims.json"
    allowed = read_optional_json(allowed_path)
    allowed_review = allowed.get("claim_review", {}) if isinstance(allowed, dict) else {}
    if not claim_review_path.exists():
        if allowed_review:
            return fail_check(
                "claim_review_artifact_valid",
                "allowed_claims.json references claim_review but claim_review.json is missing.",
            )
        return pass_check(
            "claim_review_artifact_valid",
            "No claim-review artifact was required for this run state.",
        )
    try:
        review = read_json(claim_review_path)
    except json.JSONDecodeError as error:
        return fail_check(
            "claim_review_artifact_valid",
            f"claim_review.json is invalid JSON: {error}",
        )
    problems: list[str] = []
    if review.get("schema_version") != "codex-dr.claim_review.v1":
        problems.append("invalid claim_review schema_version")
    if review.get("may_widen_public_benchmark_claims") is not False:
        problems.append("claim_review may_widen_public_benchmark_claims must be false")
    if not review.get("decision"):
        problems.append("claim_review missing decision")
    policy = review.get("policy", {})
    blocked_claims = {
        str(claim).lower()
        for claim in (
            policy.get("blocked_claims", [])
            if isinstance(policy, dict) and policy.get("blocked_claims")
            else review.get("blocked_claims", [])
        )
    }
    missing_policy_blocks = {
        claim.lower() for claim in REQUIRED_BLOCKED_CLAIMS
    } - blocked_claims
    if missing_policy_blocks:
        problems.append(
            "claim_review policy missing blocked claims: "
            + ", ".join(sorted(missing_policy_blocks))
        )
    for label, relative in review.get("inputs", {}).items():
        if not relative:
            continue
        relative_text = str(relative)
        if not (
            (run_dir / relative_text).exists()
            or resolve_sandbox_display_path(relative_text).exists()
        ):
            problems.append(f"claim_review input {label} missing: {relative}")
    if allowed_review:
        if allowed_review.get("review_ref") != "claim_review.json":
            problems.append("allowed_claims claim_review review_ref mismatch")
        if allowed_review.get("decision") and allowed_review.get("decision") != review.get("decision"):
            problems.append("allowed_claims claim_review decision mismatch")
        if allowed_review.get("may_widen_public_benchmark_claims") is not False:
            problems.append("allowed_claims claim_review widens benchmark claims")
    if problems:
        return fail_check("claim_review_artifact_valid", "; ".join(problems))
    return pass_check(
        "claim_review_artifact_valid",
        "Claim review preserves benchmark, parity, leaderboard, product, and submission claim locks.",
    )


def claim_text_represented_in_report(claim_text: str, report: str) -> bool:
    if not claim_text:
        return False
    if claim_text in report:
        return True
    claim_tokens = meaningful_claim_tokens(claim_text)
    if not claim_tokens:
        return False
    report_tokens = meaningful_claim_tokens(report)
    overlap = claim_tokens & report_tokens
    return len(overlap) / len(claim_tokens) >= 0.8


def meaningful_claim_tokens(text: str) -> set[str]:
    stopwords = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "for",
        "from",
        "in",
        "into",
        "is",
        "of",
        "or",
        "the",
        "this",
        "to",
        "with",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in stopwords
    }


def check_allowed_claims(run_dir: Path) -> dict[str, str]:
    try:
        allowed = read_json(run_dir / "allowed_claims.json")
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return fail_check("allowed_claims_scope_enforced", f"Allowed claims unavailable: {error}")
    blocked = {claim.lower() for claim in allowed.get("blocked_claims", [])}
    required_blocked = {claim.lower() for claim in REQUIRED_BLOCKED_CLAIMS}
    if not required_blocked.issubset(blocked):
        missing = ", ".join(sorted(required_blocked - blocked))
        return fail_check(
            "allowed_claims_scope_enforced",
            f"Blocked claims list is incomplete: {missing}",
        )
    for claim in allowed.get("allowed_claims", []):
        text = claim.get("claim", "").lower()
        if any(phrase in text for phrase in BLOCKED_ALLOWED_CLAIM_PHRASES):
            return fail_check(
                "allowed_claims_scope_enforced", f"Allowed claim is too wide: {claim['claim']}"
            )
        for artifact in claim.get("supporting_artifacts", []):
            if artifact != "validation_report.json" and not (run_dir / artifact).exists():
                return fail_check(
                    "allowed_claims_scope_enforced", f"Missing support artifact: {artifact}"
                )
    return pass_check(
        "allowed_claims_scope_enforced", "Allowed claims remain within provider-off scope."
    )


def check_provider_off_artifacts(run_dir: Path) -> dict[str, str]:
    if is_live_mesh_run(run_dir):
        forbidden_live = ["provider_metadata.json", "run_control_receipt.yaml"]
        present_live = [name for name in forbidden_live if (run_dir / name).exists()]
        if present_live:
            return fail_check(
                "provider_off_no_provider_artifacts",
                f"Forbidden live smoke artifacts: {', '.join(present_live)}",
            )
        return pass_check(
            "provider_off_no_provider_artifacts",
            "Live smoke uses approved run-control and transcript custody.",
        )
    forbidden = [
        "run_control_receipt.yaml",
        "provider_metadata.json",
        "transcripts",
    ]
    if not is_mesh_run(run_dir):
        forbidden.extend(["case_manifest.json", "scorer_manifest.json"])
    present = [name for name in forbidden if (run_dir / name).exists()]
    if present:
        return fail_check(
            "provider_off_no_provider_artifacts",
            f"Forbidden provider artifacts: {', '.join(present)}",
        )
    return pass_check(
        "provider_off_no_provider_artifacts", "No provider-backed artifacts are present."
    )


def check_generated_path(run_dir: Path) -> dict[str, str]:
    resolved = run_dir.resolve()
    allowed_roots = [(SANDBOX_ROOT / "runs").resolve(), (SANDBOX_ROOT / "tmp").resolve()]
    if any(resolved == root or root in resolved.parents for root in allowed_roots):
        return pass_check(
            "generated_path_is_ignored", "Run bundle lives under ignored sandbox runs/tmp path."
        )
    return fail_check(
        "generated_path_is_ignored", f"Run bundle is outside ignored sandbox paths: {resolved}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="alexandria-dr")
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init-case")
    init.add_argument("case_id")
    init.add_argument("--force", action="store_true")

    mesh_init = subparsers.add_parser("mesh-init-case")
    mesh_init.add_argument("case_id")
    mesh_init.add_argument("--force", action="store_true")

    for name in [
        "bootstrap-plan",
        "bootstrap-review",
        "bootstrap-report",
        "bootstrap-run",
        "mesh-bootstrap-run",
        "validate",
    ]:
        command = subparsers.add_parser(name)
        command.add_argument("case_id")

    for name in [
        "mesh-plan",
        "mesh-evaluate",
        "mesh-review",
        "mesh-report",
        "mesh-score",
        "mesh-self-improve",
        "mesh-adequacy-backpressure",
        "claim-review",
    ]:
        command = subparsers.add_parser(name)
        command.add_argument("case_id")

    branch = subparsers.add_parser("bootstrap-branch")
    branch.add_argument("case_id")
    branch.add_argument("branch_id")

    mesh_branch = subparsers.add_parser("mesh-branch")
    mesh_branch.add_argument("case_id")
    mesh_branch.add_argument("branch_id", choices=MESH_ALL_BRANCH_IDS)

    reentry = subparsers.add_parser("bootstrap-reentry")
    reentry.add_argument("case_id")
    reentry.add_argument("review_id")

    mesh_reentry = subparsers.add_parser("mesh-reentry")
    mesh_reentry.add_argument("case_id")
    mesh_reentry.add_argument("review_id")

    mesh_live = subparsers.add_parser("mesh-live-plan")
    mesh_live.add_argument("case_id")
    mesh_live.add_argument("--run-control", required=True, type=Path)
    mesh_live.add_argument("--prompt-overlay", type=Path)

    mesh_executor = subparsers.add_parser("mesh-executor-preflight")
    mesh_executor.add_argument("case_id")
    mesh_executor.add_argument("--run-control", required=True, type=Path)

    mesh_execute = subparsers.add_parser("mesh-execute-live")
    mesh_execute.add_argument("case_id")
    mesh_execute.add_argument("--run-control", required=True, type=Path)

    provider_backed = subparsers.add_parser("run-planner")
    provider_backed.add_argument("case_id")
    provider_backed.add_argument("--run-control", required=True)

    provider_branch = subparsers.add_parser("run-branch")
    provider_branch.add_argument("case_id")
    provider_branch.add_argument("branch_id")
    provider_branch.add_argument("--run-control", required=True)

    provider_review = subparsers.add_parser("run-review")
    provider_review.add_argument("case_id")
    provider_review.add_argument("--run-control", required=True)

    provider_reentry = subparsers.add_parser("run-reentry")
    provider_reentry.add_argument("case_id")
    provider_reentry.add_argument("review_id")
    provider_reentry.add_argument("--run-control", required=True)

    provider_score = subparsers.add_parser("score")
    provider_score.add_argument("case_id")
    provider_score.add_argument("--run-control", required=True, type=Path)

    model_probe = subparsers.add_parser("model-probe")
    model_probe.add_argument("--model", required=True)
    model_probe.add_argument(
        "--output-dir",
        type=Path,
        default=SANDBOX_ROOT / "tmp" / "model-probes",
    )
    model_probe.add_argument("--timeout-seconds", type=int, default=60)

    multi_case = subparsers.add_parser("multi-case-smoke")
    multi_case.add_argument("suite_id")
    multi_case.add_argument("--case-count", type=int, default=2)
    multi_case.add_argument("--force", action="store_true")

    multi_case_manifest = subparsers.add_parser("multi-case-from-manifest")
    multi_case_manifest.add_argument("suite_id")
    multi_case_manifest.add_argument("--manifest", required=True, type=Path)
    multi_case_manifest.add_argument("--force", action="store_true")

    drb_manifest = subparsers.add_parser("deepresearch-bench-case-manifest")
    drb_manifest.add_argument("--query-jsonl", required=True, type=Path)
    drb_manifest.add_argument("--source-refresh", required=True, type=Path)
    drb_manifest.add_argument("--output", required=True, type=Path)
    drb_manifest.add_argument("--row-indices")
    drb_manifest.add_argument("--limit", type=int)

    drb_export = subparsers.add_parser("deepresearch-bench-report-export")
    drb_export.add_argument("case_ids", nargs="+")
    drb_export.add_argument("--output", required=True, type=Path)
    drb_export.add_argument("--custody-output", type=Path)
    drb_export.add_argument("--allow-invalid", action="store_true")

    drb_race = subparsers.add_parser("deepresearch-bench-race-bridge")
    drb_race.add_argument("--raw-reports", required=True, type=Path)
    drb_race.add_argument("--source-refresh", required=True, type=Path)
    drb_race.add_argument(
        "--official-repo",
        type=Path,
        default=DEFAULT_DEEPRESEARCH_BENCH_OFFICIAL_REPO,
    )
    drb_race.add_argument("--output-dir", required=True, type=Path)
    drb_race.add_argument("--model-name", default="alexandria-codex-dr")
    drb_race.add_argument("--allow-provider-run", action="store_true")
    drb_race.add_argument("--limit", type=int)
    drb_race.add_argument("--max-workers", type=int, default=1)
    drb_race.add_argument("--timeout-seconds", type=int, default=1800)

    drb_claim = subparsers.add_parser("deepresearch-bench-claim-review")
    drb_claim.add_argument("case_id")
    drb_claim.add_argument("--race-bridge-receipt", required=True, type=Path)
    drb_claim.add_argument("--source-refresh", required=True, type=Path)

    drb_improve = subparsers.add_parser("deepresearch-bench-improvement-compile")
    drb_improve.add_argument("case_id")

    drb_improve_gate = subparsers.add_parser("deepresearch-bench-improvement-gate")
    drb_improve_gate.add_argument("case_id")

    drb_subset = subparsers.add_parser("deepresearch-bench-subset-pressure")
    drb_subset.add_argument("suite_id")
    drb_subset.add_argument("--manifest", required=True, type=Path)
    drb_subset.add_argument("--source-refresh", required=True, type=Path)
    drb_subset.add_argument(
        "--official-repo",
        type=Path,
        default=DEFAULT_DEEPRESEARCH_BENCH_OFFICIAL_REPO,
    )
    drb_subset.add_argument("--limit", type=int)
    drb_subset.add_argument("--force", action="store_true")
    drb_subset.add_argument("--allow-invalid-reports", action="store_true")

    drb_existing_subset = subparsers.add_parser(
        "deepresearch-bench-existing-subset-pressure"
    )
    drb_existing_subset.add_argument("suite_id")
    drb_existing_subset.add_argument("--source-refresh", required=True, type=Path)
    drb_existing_subset.add_argument(
        "--official-repo",
        type=Path,
        default=DEFAULT_DEEPRESEARCH_BENCH_OFFICIAL_REPO,
    )
    drb_existing_subset.add_argument("--limit", type=int)
    drb_existing_subset.add_argument("--allow-invalid-reports", action="store_true")

    drb_subset_improve = subparsers.add_parser(
        "deepresearch-bench-subset-improvement-compile"
    )
    drb_subset_improve.add_argument("suite_id")

    drb_quality_gate = subparsers.add_parser(
        "deepresearch-bench-pre-scorer-quality-gate"
    )
    drb_quality_gate.add_argument("suite_id")
    drb_quality_gate.add_argument("--output-dir", type=Path)

    drb_run_controls = subparsers.add_parser(
        "deepresearch-bench-live-run-controls"
    )
    drb_run_controls.add_argument("suite_id")
    drb_run_controls.add_argument("--prompt-overlay", required=True, type=Path)
    drb_run_controls.add_argument("--output-dir", required=True, type=Path)
    drb_run_controls.add_argument("--bead-id", required=True)
    drb_run_controls.add_argument("--max-wall-clock-minutes", type=int, default=25)

    drb_full = subparsers.add_parser("deepresearch-bench-full-run-package")
    drb_full.add_argument("package_id")
    drb_full.add_argument("--query-jsonl", required=True, type=Path)
    drb_full.add_argument("--source-refresh", required=True, type=Path)
    drb_full.add_argument("--subset-summary", required=True, type=Path)
    drb_full.add_argument(
        "--official-repo",
        type=Path,
        default=DEFAULT_DEEPRESEARCH_BENCH_OFFICIAL_REPO,
    )
    drb_full.add_argument("--output-dir", required=True, type=Path)

    drb_score_packet = subparsers.add_parser(
        "deepresearch-bench-score-control-packet"
    )
    drb_score_packet.add_argument("packet_id")
    drb_score_packet.add_argument("--full-run-package", required=True, type=Path)
    drb_score_packet.add_argument("--prompt-overlay", required=True, type=Path)
    drb_score_packet.add_argument("--output-dir", required=True, type=Path)
    drb_score_packet.add_argument("--repair-run-id")

    drb_flywheel = subparsers.add_parser("deepresearch-bench-flywheel-plan")
    drb_flywheel.add_argument("plan_id")
    drb_flywheel.add_argument("--case-id", required=True)
    drb_flywheel.add_argument("--subset-summary", required=True, type=Path)
    drb_flywheel.add_argument("--full-run-package", required=True, type=Path)
    drb_flywheel.add_argument("--output-dir", required=True, type=Path)

    drb_overlay = subparsers.add_parser("deepresearch-bench-apply-candidate-overlay")
    drb_overlay.add_argument("overlay_id")
    drb_overlay.add_argument("--flywheel-plan", required=True, type=Path)
    drb_overlay.add_argument("--output-dir", required=True, type=Path)
    drb_overlay.add_argument("--base-prompt-overlay", type=Path)

    multi_case_validate = subparsers.add_parser("multi-case-validate")
    multi_case_validate.add_argument("suite_id")

    suite_review = subparsers.add_parser("suite-claim-review")
    suite_review.add_argument("suite_id")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init-case":
            init_case(args.case_id, runs_dir=args.runs_dir, force=args.force)
        elif args.command == "mesh-init-case":
            mesh_init_case(args.case_id, runs_dir=args.runs_dir, force=args.force)
        elif args.command == "bootstrap-plan":
            bootstrap_plan(args.case_id, runs_dir=args.runs_dir)
        elif args.command == "bootstrap-branch":
            bootstrap_branch(args.case_id, args.branch_id, runs_dir=args.runs_dir)
        elif args.command == "bootstrap-review":
            bootstrap_review(args.case_id, runs_dir=args.runs_dir)
        elif args.command == "bootstrap-reentry":
            bootstrap_reentry(args.case_id, args.review_id, runs_dir=args.runs_dir)
        elif args.command == "bootstrap-report":
            bootstrap_report(args.case_id, runs_dir=args.runs_dir)
        elif args.command == "bootstrap-run":
            bootstrap_run(args.case_id, runs_dir=args.runs_dir)
        elif args.command == "mesh-plan":
            mesh_bootstrap_plan(args.case_id, runs_dir=args.runs_dir)
        elif args.command == "mesh-branch":
            spawn_event_id, return_event_id = mesh_branch_event_ids(args.branch_id)
            mesh_bootstrap_branch(
                args.case_id,
                args.branch_id,
                spawn_event_id=spawn_event_id,
                return_event_id=return_event_id,
                runs_dir=args.runs_dir,
            )
        elif args.command == "mesh-evaluate":
            mesh_bootstrap_evaluate(args.case_id, runs_dir=args.runs_dir)
        elif args.command == "mesh-review":
            mesh_bootstrap_review(args.case_id, runs_dir=args.runs_dir)
        elif args.command == "mesh-reentry":
            mesh_bootstrap_reentry(args.case_id, args.review_id, runs_dir=args.runs_dir)
        elif args.command == "mesh-report":
            mesh_bootstrap_report(args.case_id, runs_dir=args.runs_dir)
        elif args.command == "mesh-score":
            mesh_bootstrap_score(args.case_id, runs_dir=args.runs_dir)
        elif args.command == "mesh-self-improve":
            mesh_bootstrap_self_improve(args.case_id, runs_dir=args.runs_dir)
        elif args.command == "mesh-adequacy-backpressure":
            compile_adequacy_backpressure(args.case_id, runs_dir=args.runs_dir)
        elif args.command == "mesh-live-plan":
            mesh_live_plan(
                args.case_id,
                run_control=args.run_control,
                prompt_overlay=args.prompt_overlay,
                runs_dir=args.runs_dir,
            )
        elif args.command == "mesh-executor-preflight":
            mesh_executor_preflight(
                args.case_id, run_control=args.run_control, runs_dir=args.runs_dir
            )
        elif args.command == "mesh-execute-live":
            mesh_execute_live(args.case_id, run_control=args.run_control, runs_dir=args.runs_dir)
        elif args.command == "mesh-bootstrap-run":
            mesh_bootstrap_run(args.case_id, runs_dir=args.runs_dir)
        elif args.command == "score":
            score_run(args.case_id, run_control=args.run_control, runs_dir=args.runs_dir)
        elif args.command == "claim-review":
            claim_review(args.case_id, runs_dir=args.runs_dir)
        elif args.command == "model-probe":
            receipt = probe_codex_model(
                args.model,
                output_dir=args.output_dir,
                timeout_seconds=args.timeout_seconds,
            )
            print(json.dumps(receipt, indent=2, sort_keys=True))
            return 0 if receipt["status"] == "available" else 1
        elif args.command == "multi-case-smoke":
            multi_case_smoke(
                args.suite_id,
                runs_dir=args.runs_dir,
                case_count=args.case_count,
                force=args.force,
            )
        elif args.command == "multi-case-from-manifest":
            multi_case_from_manifest(
                args.suite_id,
                manifest_path=args.manifest,
                runs_dir=args.runs_dir,
                force=args.force,
            )
        elif args.command == "deepresearch-bench-case-manifest":
            output = deepresearch_bench_case_manifest(
                query_jsonl=args.query_jsonl,
                source_refresh=args.source_refresh,
                output=args.output,
                row_indices=args.row_indices,
                limit=args.limit,
            )
            print(output.as_posix())
        elif args.command == "deepresearch-bench-report-export":
            output = deepresearch_bench_report_export(
                args.case_ids,
                output=args.output,
                custody_output=args.custody_output,
                runs_dir=args.runs_dir,
                allow_invalid=args.allow_invalid,
            )
            print(output.as_posix())
        elif args.command == "deepresearch-bench-race-bridge":
            output = deepresearch_bench_race_bridge(
                raw_reports=args.raw_reports,
                source_refresh=args.source_refresh,
                official_repo=args.official_repo,
                output_dir=args.output_dir,
                model_name=args.model_name,
                allow_provider_run=args.allow_provider_run,
                limit=args.limit,
                max_workers=args.max_workers,
                timeout_seconds=args.timeout_seconds,
            )
            print(output.as_posix())
        elif args.command == "deepresearch-bench-claim-review":
            output = deepresearch_bench_claim_review(
                args.case_id,
                race_bridge_receipt=args.race_bridge_receipt,
                source_refresh=args.source_refresh,
                runs_dir=args.runs_dir,
            )
            print(output.as_posix())
        elif args.command == "deepresearch-bench-improvement-compile":
            output = deepresearch_bench_improvement_compile(
                args.case_id,
                runs_dir=args.runs_dir,
            )
            print(output.as_posix())
        elif args.command == "deepresearch-bench-improvement-gate":
            output = deepresearch_bench_improvement_gate(
                args.case_id,
                runs_dir=args.runs_dir,
            )
            print(output.as_posix())
        elif args.command == "deepresearch-bench-subset-pressure":
            output = deepresearch_bench_subset_pressure(
                args.suite_id,
                manifest_path=args.manifest,
                source_refresh=args.source_refresh,
                official_repo=args.official_repo,
                runs_dir=args.runs_dir,
                force=args.force,
                limit=args.limit,
                allow_invalid_reports=args.allow_invalid_reports,
            )
            print(output.as_posix())
        elif args.command == "deepresearch-bench-existing-subset-pressure":
            output = deepresearch_bench_existing_subset_pressure(
                args.suite_id,
                source_refresh=args.source_refresh,
                official_repo=args.official_repo,
                runs_dir=args.runs_dir,
                limit=args.limit,
                allow_invalid_reports=args.allow_invalid_reports,
            )
            print(output.as_posix())
        elif args.command == "deepresearch-bench-subset-improvement-compile":
            output = deepresearch_bench_subset_improvement_compile(
                args.suite_id,
                runs_dir=args.runs_dir,
            )
            print(output.as_posix())
        elif args.command == "deepresearch-bench-pre-scorer-quality-gate":
            output = deepresearch_bench_pre_scorer_quality_gate(
                args.suite_id,
                output_dir=args.output_dir,
                runs_dir=args.runs_dir,
            )
            print(output.as_posix())
        elif args.command == "deepresearch-bench-live-run-controls":
            output = deepresearch_bench_live_run_controls(
                args.suite_id,
                prompt_overlay=args.prompt_overlay,
                output_dir=args.output_dir,
                bead_id=args.bead_id,
                runs_dir=args.runs_dir,
                max_wall_clock_minutes=args.max_wall_clock_minutes,
            )
            print(output.as_posix())
        elif args.command == "deepresearch-bench-full-run-package":
            output = deepresearch_bench_full_run_package(
                args.package_id,
                query_jsonl=args.query_jsonl,
                source_refresh=args.source_refresh,
                subset_summary=args.subset_summary,
                official_repo=args.official_repo,
                output_dir=args.output_dir,
            )
            print(output.as_posix())
        elif args.command == "deepresearch-bench-score-control-packet":
            output = deepresearch_bench_score_control_packet(
                args.packet_id,
                full_run_package=args.full_run_package,
                prompt_overlay=args.prompt_overlay,
                output_dir=args.output_dir,
                repair_run_id=args.repair_run_id,
                runs_dir=args.runs_dir,
            )
            print(output.as_posix())
        elif args.command == "deepresearch-bench-flywheel-plan":
            output = deepresearch_bench_flywheel_plan(
                args.plan_id,
                case_id=args.case_id,
                subset_summary=args.subset_summary,
                full_run_package=args.full_run_package,
                output_dir=args.output_dir,
                runs_dir=args.runs_dir,
            )
            print(output.as_posix())
        elif args.command == "deepresearch-bench-apply-candidate-overlay":
            output = deepresearch_bench_apply_candidate_overlay(
                args.overlay_id,
                flywheel_plan=args.flywheel_plan,
                output_dir=args.output_dir,
                base_prompt_overlay=args.base_prompt_overlay,
            )
            print(output.as_posix())
        elif args.command == "multi-case-validate":
            report = validate_multi_case_suite(args.suite_id, runs_dir=args.runs_dir)
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0 if report["status"] == "passed" else 1
        elif args.command == "suite-claim-review":
            suite_claim_review(args.suite_id, runs_dir=args.runs_dir)
        elif args.command == "validate":
            report = validate_run(args.case_id, runs_dir=args.runs_dir)
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0 if report["status"] == "passed" else 1
        elif args.command in {"run-planner", "run-branch", "run-review", "run-reentry"}:
            print(
                "error: provider-backed and benchmark commands are blocked until "
                "provider-off bootstrap validation, harness gates, and an approved "
                "run-control receipt exist",
                file=sys.stderr,
            )
            return 2
        else:
            parser.error(f"unknown command {args.command}")
    except HarnessError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
