#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

SANDBOX_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS_DIR = SANDBOX_ROOT / "runs"
SELF_IMPROVEMENT_TAXONOMY_PATH = (
    SANDBOX_ROOT / "harness-specs" / "self_improvement_failure_taxonomy.json"
)
SELF_IMPROVEMENT_CORPUS_PATH = (
    SANDBOX_ROOT / "harness-specs" / "provider_off_self_improvement_replay_corpus.json"
)
FIXTURE_TIMESTAMP = "2026-04-22T00:00:00Z"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

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

ROLE_PROMPT_PROFILES = {
    "planner": {
        "title": "Planner",
        "instructions": [
            "Recover the user question, available files/docs, and allowed external context.",
            "Emit a Plan File, skills/tools selection, adequacy criteria, and task graph.",
            "Make dependencies, branch roles, output contracts, and review checklist explicit.",
        ],
    },
    "deep_search": {
        "title": "Deep Search Branch",
        "instructions": [
            "Collect public-source orientation only within the run-control data policy.",
            "Return source-backed findings through pointer, analysis, and evidence files.",
            "Mark uncertainty and access gaps instead of stretching source claims.",
        ],
    },
    "data_analysis": {
        "title": "Data Analysis Branch",
        "instructions": [
            "Inspect case fields, benchmark-relevant structure, and scoring implications.",
            "Separate observed data from inference and blocked reference-answer material.",
            "Return analysis spans named by the pointer for selective orchestration.",
        ],
    },
    "verification": {
        "title": "Verification Branch",
        "instructions": [
            "Check claim boundaries, source admission, citation support, and non-claims.",
            "Identify unsupported or overbroad claims before synthesis or report writing.",
            "Return verification evidence without enabling benchmark or parity claims.",
        ],
    },
    "orchestrator": {
        "title": "Evaluate And Synthesize Orchestrator",
        "instructions": [
            "Read pointer files before analysis files and admit only named analysis spans.",
            "Assess adequacy criteria, contradictions, unresolved gaps, and re-entry needs.",
            "Write synthesis from admitted evidence and preserve blocked claims.",
        ],
    },
    "reviewer": {
        "title": "Reviewer And Fact-Checker",
        "instructions": [
            "Fact-check synthesis/report state against the planning-time checklist.",
            "Classify findings by severity and whether more research is required.",
            "Write review output that can compile into specific re-entry tasks.",
        ],
    },
    "reentry": {
        "title": "Reviewer-Driven Re-Entry Branch",
        "instructions": [
            "Answer only the cited reviewer finding and keep the scope narrow.",
            "Return pointer, analysis, and evidence files linked to the review finding.",
            "Do not widen claims beyond the source-supported follow-up result.",
        ],
    },
    "writer": {
        "title": "One Writer Report",
        "instructions": [
            "Write one coherent report from synthesis, review state, and claim ledger.",
            "Preserve unresolveds, non-claims, and benchmark/scorer blockers.",
            "Do not introduce new facts that lack evidence custody.",
        ],
    },
    "scorer_bridge": {
        "title": "Scorer Bridge",
        "instructions": [
            "Prepare scoring inputs and schema only after scorer policy is approved.",
            "Keep sealed references, judge prompts, variance policy, and transcripts explicit.",
            "Never convert a placeholder score into a numeric benchmark claim.",
        ],
    },
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
]

LIVE_MESH_REQUIRED_EVENT_TYPES = [
    "live_executor.run_control_receipt_copied",
    "live_executor.execution_started",
    "live_executor.role_completed",
    "live_executor.execution_completed",
]

VALIDATOR_NAMES = {
    "branch_triplet_present",
    "mesh_branch_triplets_present",
    "events_required_types_present",
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
    "provider-backed",
    "provider backed",
    "product service readiness",
    "leaderboard",
]


class HarnessError(RuntimeError):
    pass


def run_path(case_id: str, runs_dir: Path | str | None = None) -> Path:
    validate_id(case_id, "case_id")
    return Path(runs_dir or DEFAULT_RUNS_DIR) / case_id


def validate_id(value: str, label: str) -> None:
    if not ID_RE.match(value):
        raise HarnessError(f"{label} must match {ID_RE.pattern}: {value!r}")


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


def run_mode(run_dir: Path) -> str:
    try:
        return str(read_json(run_dir / "run_manifest.json").get("mode", "provider_off_bootstrap"))
    except (FileNotFoundError, json.JSONDecodeError):
        return "unknown"


def is_mesh_run(run_dir: Path) -> bool:
    return run_mode(run_dir) in {"provider_off_dr_mesh", "live_dr_mesh_smoke"}


def is_live_mesh_run(run_dir: Path) -> bool:
    return (run_dir / "live_executor" / "execution_summary.json").exists()


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
            required.extend(LIVE_MESH_REQUIRED_EVENT_TYPES)
        return required
    return REQUIRED_EVENT_TYPES


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


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
) -> None:
    events_path = run_dir / "events.jsonl"
    events = read_jsonl(events_path)
    if any(event["event_id"] == event_id for event in events):
        return
    if causally_after is None:
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
    events.append(event)
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
            "blocked_claims": [
                "Grep parity",
                "benchmark score",
                "provider-backed execution",
                "product service readiness",
            ],
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


def mesh_bootstrap_plan(case_id: str, *, runs_dir: Path | str | None = None) -> Path:
    run_dir = run_path(case_id, runs_dir)
    write_json(
        run_dir / "case_manifest.json",
        {
            "schema_version": "codex-dr.case_manifest.v1",
            "run_id": case_id,
            "benchmark_family": "DRACO",
            "case_id": "draco_provider_off_mesh_fixture",
            "case_count": 1,
            "raw_data_in_git": False,
            "execution_mode": "provider_off_fixture",
            "question": "What evidence is needed to answer the tiny DRACO-shaped smoke case?",
            "source_policy": "Use only deterministic local fixture facts; no benchmark execution.",
            "produced_by_event": "evt_0002_plan_written",
        },
    )
    write_text(
        run_dir / "plan.md",
        """# Provider-Off DR Mesh Plan

## Objective
Exercise the Grep-shaped DR mesh topology without launching Codex CLI boxes.

## Inputs
- User question: tiny DRACO-shaped smoke fixture.
- Files/docs: local case manifest and harness contracts.
- External context: blocked in provider-off mode.

## Task Graph
Run independent deep-search, data-analysis, and verification branches. Read
branch pointers first, admit selected analysis spans, synthesize, review, create
a re-entry branch when the review requires more research, then write one report.

## Adequacy Checks
- Every role-scoped branch returns pointer, analysis, and evidence files.
- The orchestrator records pointer-first selective reads before synthesis.
- Review findings that require more research create linked re-entry tasks.
- The scorer bridge remains a placeholder and cannot enable benchmark claims.

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
            "selected_tools": ["filesystem", "json_validator", "artifact_manifest_hasher"],
            "blocked_tools": ["codex_exec", "provider_calls", "benchmark_execution", "network"],
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
    write_json(run_dir / "role_configs.json", mesh_role_configs(case_id))
    write_json(run_dir / "task_graph.json", mesh_initial_task_graph(case_id))
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


def mesh_role_configs(case_id: str) -> dict[str, Any]:
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
                "objective": branch["objective"],
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
                "input_contract": ["synthesis.md", "report_outline.md"],
                "return_contract": ["reviews/review_001.json"],
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
                "input_contract": ["synthesis.md", "claim_ledger.json"],
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


def mesh_initial_task_graph(case_id: str) -> dict[str, Any]:
    branch_tasks = []
    for branch_id in MESH_INITIAL_BRANCH_IDS:
        branch = MESH_BRANCH_ROLES[branch_id]
        branch_tasks.append(
            {
                "task_id": branch["task_id"],
                "kind": "branch_research",
                "objective": branch["objective"],
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
        )
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
                    f"branches/{branch_id}/pointer.md"
                    for branch_id in MESH_INITIAL_BRANCH_IDS
                ],
                "expected_outputs": [
                    "pointer_read_receipts.jsonl",
                    "adequacy_assessments.jsonl",
                    "synthesis.md",
                    "contradictions.json",
                    "report_outline.md",
                ],
                "adequacy_checks": ["adequacy_pointer_first_reads"],
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
                "inputs": ["synthesis.md", "report_outline.md"],
                "expected_outputs": ["reviews/review_001.json"],
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
                "inputs": ["synthesis.md", "claim_ledger.json"],
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
    graph_path = run_dir / "task_graph.json"
    graph = read_json(graph_path)
    graph["tasks"] = [
        existing for existing in graph["tasks"] if existing["task_id"] != task["task_id"]
    ]
    graph["tasks"].append(task)
    for existing in graph["tasks"]:
        if existing["task_id"] == "task_final_writer":
            existing["depends_on"] = ["task_reentry_followup"]
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
            "blocked_claims": [
                "Grep parity",
                "benchmark score",
                "provider-backed execution",
                "product service readiness",
            ],
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
            "case_id": "draco_provider_off_mesh_fixture",
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
    write_json(
        run_dir / "self_improvement" / "replay_corpus.json",
        {
            **corpus,
            "run_id": case_id,
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


def mesh_live_plan(
    case_id: str,
    *,
    run_control: Path,
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
            live_adapter_prompt(case_id, task, role, receipt),
        )
        prompt_outputs.append(prompt_path.as_posix())
        command_plan = [
            "codex",
            "exec",
            "--json",
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
        inputs=["task_graph.json", "role_configs.json", "terminal_agent_boxes.json"],
        outputs=[*prompt_outputs, "live_adapter/launch_plan.json"],
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
        "execution_status": "not_launched_current_halt",
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
        "roles": [],
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
    for index, role_plan in enumerate(role_plans, start=1):
        role_record = execute_live_role(
            run_dir=run_dir,
            receipt=receipt,
            role_plan=role_plan,
            role_index=index,
            timeout_seconds=timeout_seconds,
            codex_runner=runner,
        )
        execution_summary["roles"].append(role_record)
    execution_summary["execution_status"] = "succeeded"
    execution_summary["role_count"] = len(execution_summary["roles"])
    write_json(execution_summary_path, execution_summary)
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
    copied_outputs = copy_live_role_outputs(run_dir, workspace_path, role_plan)
    event_id = f"evt_live_{role_index:04d}_{task_id}_completed"
    event_outputs = [
        *copied_outputs,
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
        "returncode": result.get("returncode"),
        "event_id": event_id,
    }


def copy_live_role_inputs(
    run_dir: Path, workspace_path: Path, role_plan: dict[str, Any]
) -> list[str]:
    copied = []
    for relative in role_plan.get("allowed_input_files", []):
        source = run_dir / relative
        if not source.exists() or not source.is_file():
            continue
        destination = workspace_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(relative)
    return copied


def copy_live_role_outputs(
    run_dir: Path, workspace_path: Path, role_plan: dict[str, Any]
) -> list[str]:
    copied = []
    missing = []
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
        copied.append(rel(destination, run_dir))
    if missing:
        raise HarnessError(
            f"{role_plan['task_id']}: live role did not produce required outputs: "
            + ", ".join(missing)
        )
    return copied


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

Input files copied into this workspace:
{input_paths}

You must write the required outputs as files relative to the current workspace:
{output_paths}

Do not write outside the current workspace. Do not read env files, secrets,
customer data, raw private benchmark corpora, paid benchmark corpora, or root
environment files. Do not claim Grep parity, a DRACO score, leaderboard rank,
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
    blocked.update(
        [
            "Grep parity",
            "DRACO score",
            "leaderboard rank",
            "product readiness",
            "benchmark score",
            "benchmark execution",
        ]
    )
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

Do not claim Grep parity, a DRACO score, leaderboard rank, product readiness,
or benchmark execution unless a later validated run and scorer bundle proves it.

This prompt file alone does not authorize live execution.
"""


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


def mesh_bootstrap_run(case_id: str, *, runs_dir: Path | str | None = None) -> Path:
    run_dir = mesh_init_case(case_id, runs_dir=runs_dir, force=True)
    mesh_bootstrap_plan(case_id, runs_dir=runs_dir)
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


def validate_run(case_id: str, *, runs_dir: Path | str | None = None) -> dict[str, Any]:
    run_dir = run_path(case_id, runs_dir)
    checks = [
        check_required_files(run_dir),
        check_required_event_types(run_dir),
        check_event_chain(run_dir),
        check_artifact_manifest(run_dir),
        check_branch_triplets(run_dir),
        check_task_graph_dependencies(run_dir),
        check_pointer_first_receipts(run_dir),
        check_adequacy_criteria(run_dir),
        check_review_reentry(run_dir),
        check_compaction_receipt(run_dir),
        check_scorer_manifest(run_dir),
        check_benchmark_placeholder(run_dir),
        check_evaluation_ledger_claim_gate(run_dir),
        check_self_improvement_replay_gate(run_dir),
        check_live_execution_custody(run_dir),
        check_report_claims_in_ledger(run_dir),
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
        if "## Read Next" not in pointer:
            return fail_check(
                "branch_triplets_present", f"Branch {branch_id} pointer lacks Read Next section."
            )
        evidence = read_jsonl(branch_dir / "evidence.jsonl")
        if not evidence or any(item.get("admission_status") != "admitted" for item in evidence):
            return fail_check(
                "branch_triplets_present",
                f"Branch {branch_id} evidence is missing or not admitted.",
            )
    return pass_check(
        "branch_triplets_present", "Branch pointer, analysis, and evidence are present."
    )


def check_task_graph_dependencies(run_dir: Path) -> dict[str, str]:
    try:
        graph = read_json(run_dir / "task_graph.json")
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return fail_check("task_graph_dependencies_valid", f"Task graph unavailable: {error}")
    tasks = graph.get("tasks", [])
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
    by_branch = {receipt.get("branch_id"): receipt for receipt in receipts}
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
        spans = receipt.get("selected_analysis_spans", [])
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
        finding for finding in review.get("findings", []) if finding.get("requires_reentry")
    ]
    decision_by_finding = {decision.get("finding_id"): decision for decision in decisions}
    task_ids = {task.get("task_id") for task in graph.get("tasks", [])}
    missing = []
    for finding in required_findings:
        decision = decision_by_finding.get(finding["finding_id"])
        if not decision:
            missing.append(finding["finding_id"])
            continue
        if (
            decision.get("decision") == "create_task"
            and decision.get("created_task_id") not in task_ids
        ):
            missing.append(f"{finding['finding_id']} missing task")
    if not required_findings or missing:
        return fail_check(
            "review_reentry_compiled", f"Missing re-entry decisions: {', '.join(missing)}"
        )
    return pass_check("review_reentry_compiled", "Review finding compiled into re-entry task.")


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
        manifest.get("scorer_status") == "approved"
        and manifest.get("execution_allowed") is True
        and manifest.get("scorer_execution", {}).get("executed_with_custody") is True
    )
    if score_has_numeric_value and not scorer_has_custody:
        problems.append("non-null benchmark score lacks scorer custody")
    if problems:
        return fail_check("draco_scorer_manifest_valid", "; ".join(problems))
    return pass_check(
        "draco_scorer_manifest_valid",
        "DRACO scorer manifest is present and scoring remains blocked.",
    )


def check_benchmark_placeholder(run_dir: Path) -> dict[str, str]:
    try:
        score = read_json(run_dir / "benchmark_score.json")
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return fail_check(
            "benchmark_placeholder_not_score", f"Benchmark placeholder unavailable: {error}"
        )
    if score.get("mode") != "provider_off_placeholder":
        return fail_check(
            "benchmark_placeholder_not_score", "Benchmark mode is not provider_off_placeholder."
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
        manifest.get("scorer_status") == "approved"
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
    blocked_phrases = ["draco score", "grep parity", "leaderboard rank"]
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
    if regression.get("automatic_skill_mutation_allowed") is not False:
        problems.append("regression gate allows automatic skill mutation")
    if regression.get("proposal_promotion_allowed") is not False:
        problems.append("regression gate allows proposal promotion")
    if problems:
        return fail_check("self_improvement_replay_gate_enforced", "; ".join(problems))
    return pass_check(
        "self_improvement_replay_gate_enforced",
        "Provider-off self-improvement replay loop is bounded and not promoted.",
    )


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
        task_graph = read_json(run_dir / "task_graph.json")
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return fail_check("live_execution_custody_present", f"Live custody unavailable: {error}")
    problems = []
    if summary.get("schema_version") != "codex-dr.live_execution_summary.v1":
        problems.append("invalid live execution summary schema")
    if summary.get("execution_status") != "succeeded":
        problems.append("live execution summary did not succeed")
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
    expected_roles = launch_plan.get("role_launch_plans", [])
    actual_roles = summary.get("roles", [])
    if len(actual_roles) != len(expected_roles):
        problems.append("role execution count does not match launch plan")
    graph_dependencies = {
        task.get("task_id", "<unknown>"): task.get("depends_on", [])
        for task in task_graph.get("tasks", [])
    }
    role_order = [role.get("task_id", "<unknown>") for role in actual_roles]
    problems.extend(dependency_order_problems(role_order, graph_dependencies))
    for role in actual_roles:
        task_id = role.get("task_id", "<unknown>")
        if role.get("returncode") != 0:
            problems.append(f"{task_id}: non-zero returncode")
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
        "Live execution has approved receipt, per-role transcripts, outputs, and no scorer.",
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
        if claim.get("text") not in report:
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


def check_allowed_claims(run_dir: Path) -> dict[str, str]:
    try:
        allowed = read_json(run_dir / "allowed_claims.json")
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return fail_check("allowed_claims_scope_enforced", f"Allowed claims unavailable: {error}")
    blocked = {claim.lower() for claim in allowed.get("blocked_claims", [])}
    required_blocked = {
        "grep parity",
        "benchmark score",
        "provider-backed execution",
        "product service readiness",
    }
    if not required_blocked.issubset(blocked):
        return fail_check("allowed_claims_scope_enforced", "Blocked claims list is incomplete.")
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
    provider_score.add_argument("--run-control", required=True)

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
        elif args.command == "mesh-live-plan":
            mesh_live_plan(args.case_id, run_control=args.run_control, runs_dir=args.runs_dir)
        elif args.command == "mesh-executor-preflight":
            mesh_executor_preflight(
                args.case_id, run_control=args.run_control, runs_dir=args.runs_dir
            )
        elif args.command == "mesh-execute-live":
            mesh_execute_live(args.case_id, run_control=args.run_control, runs_dir=args.runs_dir)
        elif args.command == "mesh-bootstrap-run":
            mesh_bootstrap_run(args.case_id, runs_dir=args.runs_dir)
        elif args.command == "validate":
            report = validate_run(args.case_id, runs_dir=args.runs_dir)
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0 if report["status"] == "passed" else 1
        elif args.command in {"run-planner", "run-branch", "run-review", "run-reentry", "score"}:
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
