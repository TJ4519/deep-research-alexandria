#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

SANDBOX_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS_DIR = SANDBOX_ROOT / "runs"
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


def run_mode(run_dir: Path) -> str:
    try:
        return str(read_json(run_dir / "run_manifest.json").get("mode", "provider_off_bootstrap"))
    except (FileNotFoundError, json.JSONDecodeError):
        return "unknown"


def is_mesh_run(run_dir: Path) -> bool:
    return run_mode(run_dir) == "provider_off_dr_mesh"


def required_files_for_run(run_dir: Path) -> list[str]:
    if is_mesh_run(run_dir):
        return MESH_REQUIRED_FILES
    return REQUIRED_FILES


def required_event_types_for_run(run_dir: Path) -> list[str]:
    if is_mesh_run(run_dir):
        return MESH_REQUIRED_EVENT_TYPES
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
            "schema_version": "codex-dr.scorer_manifest.v1",
            "run_id": case_id,
            "benchmark_family": "DRACO",
            "scorer_available": False,
            "mode": "provider_off_placeholder",
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
            "score": None,
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
    update_manifest_status(run_dir, "scoring_blocked")
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
    receipt = require_dry_run_control_receipt(run_control, run_id=case_id)
    graph = read_json(run_dir / "task_graph.json")
    role_configs = read_json(run_dir / "role_configs.json")
    boxes = read_json(run_dir / "terminal_agent_boxes.json")
    roles_by_id = {role["role_config_id"]: role for role in role_configs.get("roles", [])}
    boxes_by_id = {box["box_id"]: box for box in boxes.get("boxes", [])}
    launch_root = run_dir / "live_adapter"
    role_launch_plans = []
    prompt_outputs = []
    for task in graph.get("tasks", []):
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
        workspace = SANDBOX_ROOT / ".agent-workspaces" / case_id / role["role"]
        write_text(
            run_dir / prompt_path,
            live_adapter_prompt(case_id, task, role, receipt),
        )
        prompt_outputs.append(prompt_path.as_posix())
        role_launch_plans.append(
            {
                "task_id": task_id,
                "role": role["role"],
                "role_config_id": role_config_id,
                "box_id": task.get("assigned_box_id"),
                "adapter_kind": "codex_cli_box_dry_run",
                "launch_status": "planned_not_launched",
                "command_plan": [
                    "codex",
                    "exec",
                    "--json",
                    "--output-last-message",
                    f"live_adapter/last_messages/{task_id}.txt",
                    "--",
                    f"@{prompt_path.as_posix()}",
                ],
                "cwd": workspace.as_posix(),
                "prompt_file": prompt_path.as_posix(),
                "allowed_input_files": task.get("inputs", role.get("input_contract", [])),
                "output_paths": task.get("expected_outputs", role.get("return_contract", [])),
                "transcript_path": f"transcripts/{task_id}.jsonl",
                "wall_clock_bound_minutes": receipt["operational_bounds"][
                    "max_wall_clock_minutes"
                ],
                "kill_path": receipt["operational_bounds"]["kill_path"],
                "claim_boundary": {
                    "allowed_claims_if_success": receipt["allowed_claims_if_success"],
                    "blocked_claims": receipt["non_claims_even_if_success"],
                },
                "scorer_policy": receipt.get("scoring", {}),
                "will_execute": False,
            }
        )
    launch_plan = {
        "schema_version": "codex-dr.live_adapter_launch_plan.v1",
        "run_id": case_id,
        "launch_mode": "dry_run_only",
        "run_control_receipt": str(run_control),
        "role_launch_plans": role_launch_plans,
        "non_execution_guarantee": (
            "mesh-live-plan renders command plans and prompt files only; "
            "it never invokes codex exec."
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


def live_adapter_prompt(
    case_id: str,
    task: dict[str, Any],
    role: dict[str, Any],
    receipt: dict[str, Any],
) -> str:
    return f"""# Codex-DR Live Adapter Prompt

Run id: `{case_id}`
Task id: `{task["task_id"]}`
Role: `{role["role"]}`

## Objective
{task["objective"]}

## Allowed Inputs
{json.dumps(task.get("inputs", role.get("input_contract", [])), indent=2)}

## Expected Outputs
{json.dumps(task.get("expected_outputs", role.get("return_contract", [])), indent=2)}

## Run-Control Boundary
- Dry-run planning receipt: `{receipt["receipt_id"]}`
- Wall-clock bound: `{receipt["operational_bounds"]["max_wall_clock_minutes"]}` minutes
- Kill path: {receipt["operational_bounds"]["kill_path"]}
- Automatic retry allowed: false

## Non-Claims
{json.dumps(receipt["non_claims_even_if_success"], indent=2)}

This prompt file is a dry-run artifact. It does not authorize live execution.
"""


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
        check_benchmark_placeholder(run_dir),
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
        elif args.command == "mesh-live-plan":
            mesh_live_plan(args.case_id, run_control=args.run_control, runs_dir=args.runs_dir)
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
