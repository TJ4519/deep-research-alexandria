from __future__ import annotations

import importlib.util
import json
import shutil
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HARNESS_PATH = ROOT / "sandbox" / "codex-dr" / "tools" / "alexandria_dr.py"
TEST_RUNS_ROOT = ROOT / "sandbox" / "codex-dr" / "tmp" / "pytest-runs"


def load_harness():
    spec = importlib.util.spec_from_file_location("alexandria_dr", HARNESS_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fresh_run(tmp_path: Path):
    harness = load_harness()
    runs_dir = TEST_RUNS_ROOT / tmp_path.name
    shutil.rmtree(runs_dir, ignore_errors=True)
    harness.bootstrap_run("local_fixture_001", runs_dir=runs_dir)
    return harness, runs_dir / "local_fixture_001", runs_dir


def fresh_mesh_run(tmp_path: Path):
    harness = load_harness()
    runs_dir = TEST_RUNS_ROOT / f"{tmp_path.name}-mesh"
    shutil.rmtree(runs_dir, ignore_errors=True)
    harness.mesh_bootstrap_run("draco_mesh_fixture_001", runs_dir=runs_dir)
    return harness, runs_dir / "draco_mesh_fixture_001", runs_dir


def write_backpressure_queue(run_dir: Path, items: list[dict]) -> None:
    queue_path = run_dir / "backpressure" / "adequacy_backpressure_queue.json"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(
        json.dumps(
            {
                "schema_version": "codex-dr.adequacy_backpressure_queue.v2",
                "run_id": run_dir.name,
                "queue_status": "open" if items else "clear",
                "writer_blocked": bool(items),
                "items": items,
                "quarantined_items": [],
                "normalization_summary": {
                    "canonical_item_count": len(items),
                    "review_proposed_item_count": 0,
                    "quarantined_review_proposal_count": 0,
                    "legacy_fields_normalized_by": "harness",
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def failed_check_ids(report: dict) -> set[str]:
    return {check["check_id"] for check in report["checks"] if check["status"] == "failed"}


def test_provider_off_bootstrap_run_validates(tmp_path: Path):
    harness, run_dir, runs_dir = fresh_run(tmp_path)

    report = harness.validate_run("local_fixture_001", runs_dir=runs_dir)

    assert report["status"] == "passed"
    assert (run_dir / "validation_report.json").exists()
    assert report["failed_checks"] == []


def test_provider_off_dr_mesh_run_validates(tmp_path: Path):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)

    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=runs_dir)

    assert report["status"] == "passed"
    assert report["failed_checks"] == []
    for branch_id in ["deep_search", "data_analysis", "verification", "reentry_followup"]:
        branch_dir = run_dir / "branches" / branch_id
        assert (branch_dir / "pointer.md").exists()
        assert (branch_dir / "analysis.md").exists()
        assert (branch_dir / "evidence.jsonl").exists()
    task_graph = json.loads((run_dir / "task_graph.json").read_text(encoding="utf-8"))
    task_ids = {task["task_id"] for task in task_graph["tasks"]}
    assert {"task_deep_search", "task_data_analysis", "task_verification"} <= task_ids
    reentry_task = next(
        task for task in task_graph["tasks"] if task["task_id"] == "task_reentry_followup"
    )
    assert reentry_task["source_review_finding_id"] == "finding_reentry_001"
    receipts = [
        json.loads(line)
        for line in (run_dir / "pointer_read_receipts.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert {receipt["branch_id"] for receipt in receipts} == {
        "deep_search",
        "data_analysis",
        "verification",
        "reentry_followup",
    }
    replay = json.loads(
        (run_dir / "self_improvement" / "replay_corpus.json").read_text(encoding="utf-8")
    )
    assert {fixture["kind"] for fixture in replay["fixtures"]} == {
        "failed_evaluation",
        "corrected_fixture",
    }
    taxonomy = json.loads(
        (run_dir / "self_improvement" / "failure_taxonomy.json").read_text(
            encoding="utf-8"
        )
    )
    assert {
        "prompt",
        "source",
        "citation",
        "evidence",
        "synthesis",
        "task_graph",
        "reviewer",
        "writer",
        "claim_boundary",
    } <= {item["class_id"] for item in taxonomy["failure_classes"]}


def test_validator_accepts_reentry_results_derived_from_admitted_inputs():
    harness = load_harness()

    assert harness.evidence_status_is_admitted("derived_from_admitted_inputs")
    assert harness.evidence_status_is_admitted("derived_from_admitted_branch_rows")
    assert harness.evidence_status_is_admitted("inference_from_admitted_evidence")
    assert harness.evidence_status_is_admitted("inference_from_admitted_branch_rows")
    assert harness.evidence_status_is_admitted("limited_admission")
    assert not harness.evidence_status_is_admitted("derived_from_unadmitted_inputs")
    assert not harness.evidence_status_is_admitted("inference_from_unadmitted_evidence")
    assert harness.evidence_status_is_gap("explicit_gap")
    assert harness.evidence_status_is_gap("blocked_by_input")
    assert harness.evidence_status_is_gap("missing_reentry_task_packet")
    assert harness.evidence_status_is_gap("unadmitted")
    assert harness.evidence_status_is_gap("not_admitted_for_claim_support")
    assert harness.evidence_status_is_gap("needs_synthesis")


def test_validator_treats_bounded_result_as_non_evidence_result_status():
    harness = load_harness()

    assert harness.evidence_status_is_result("bounded_result")
    assert not harness.evidence_status_is_admitted("bounded_result")
    assert not harness.evidence_status_is_gap("bounded_result")


def test_pointer_receipts_keep_stronger_schema_receipt_over_selection_receipt(
    tmp_path: Path,
):
    harness, run_dir, _runs_dir = fresh_mesh_run(tmp_path)
    receipts_path = run_dir / "pointer_read_receipts.jsonl"
    with receipts_path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "branch": "reentry_followup",
                    "pointer_path": "branches/reentry_followup/pointer.md",
                    "analysis_path": "branches/reentry_followup/analysis.md",
                    "selected_analysis_spans": ["analysis.md#Blocked Result"],
                    "evidence_path": "branches/reentry_followup/evidence.jsonl",
                },
                sort_keys=True,
            )
            + "\n"
        )

    result = harness.check_pointer_first_receipts(run_dir)

    assert result["status"] == "passed"


def test_pointer_receipts_accept_pointer_first_read_alias(tmp_path: Path):
    harness, run_dir, _runs_dir = fresh_mesh_run(tmp_path)
    receipts_path = run_dir / "pointer_read_receipts.jsonl"
    receipts = [
        {
            "branch_id": branch_id,
            "pointer_path": f"branches/{branch_id}/pointer.md",
            "pointer_first_read": True,
            "selected_analysis_spans": [
                {
                    "analysis_path": f"branches/{branch_id}/analysis.md",
                    "section_heading": "Read Next",
                }
            ],
            "evidence_paths": [f"branches/{branch_id}/evidence.jsonl"],
        }
        for branch_id in harness.MESH_ALL_BRANCH_IDS
    ]
    receipts_path.write_text(
        "\n".join(json.dumps(receipt, sort_keys=True) for receipt in receipts) + "\n",
        encoding="utf-8",
    )

    result = harness.check_pointer_first_receipts(run_dir)

    assert result["status"] == "passed"


def test_pointer_receipts_accept_pointer_read_first_alias(tmp_path: Path):
    harness, run_dir, _runs_dir = fresh_mesh_run(tmp_path)
    receipts_path = run_dir / "pointer_read_receipts.jsonl"
    receipts = [
        {
            "branch_id": branch_id,
            "pointer_path": f"branches/{branch_id}/pointer.md",
            "pointer_read_first": True,
            "selected_analysis_spans": [
                {
                    "analysis_path": f"branches/{branch_id}/analysis.md",
                    "section_heading": "Read Next",
                }
            ],
            "evidence_paths": [f"branches/{branch_id}/evidence.jsonl"],
        }
        for branch_id in harness.MESH_ALL_BRANCH_IDS
    ]
    receipts_path.write_text(
        "\n".join(json.dumps(receipt, sort_keys=True) for receipt in receipts) + "\n",
        encoding="utf-8",
    )

    result = harness.check_pointer_first_receipts(run_dir)

    assert result["status"] == "passed"


def test_branch_triplets_accept_any_read_next_heading_level(tmp_path: Path):
    harness, run_dir, _runs_dir = fresh_mesh_run(tmp_path)
    pointer_path = run_dir / "branches" / "data_analysis" / "pointer.md"
    pointer_path.write_text(
        pointer_path.read_text(encoding="utf-8").replace("## Read Next", "# Read Next"),
        encoding="utf-8",
    )

    result = harness.check_branch_triplets(run_dir)

    assert result["status"] == "passed"


def test_branch_triplets_allow_writer_blocked_reentry_gap_branch(tmp_path: Path):
    harness, run_dir, _runs_dir = fresh_mesh_run(tmp_path)
    write_backpressure_queue(
        run_dir,
        [
            {
                "item_id": "bp_missing_reentry_packet",
                "status": "open",
                "writer_blocking": True,
                "source": "reviewer",
            }
        ],
    )
    (run_dir / "branches" / "reentry_followup" / "evidence.jsonl").write_text(
        json.dumps(
            {
                "evidence_id": "RF-BLK-001",
                "record_type": "blocker_record",
                "admission_status": "blocked_by_input",
                "summary": "Required re-entry packet is absent.",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    result = harness.check_branch_triplets(run_dir)

    assert result["status"] == "passed"


def test_improvement_refs_include_reviewer_v2_and_singular_adequacy_gap():
    harness = load_harness()
    refs = harness.compile_source_failure_refs(
        evaluation_failures=[
            {
                "failure_class": "scorer_missing",
                "root_cause": "No approved scorer execution path exists.",
                "severity": "blocking",
            }
        ],
        review_findings=harness.extract_review_failure_surfaces(
            {
                "material_findings": [
                    {
                        "finding_id": "F-001",
                        "category": "citation_support_gap",
                        "severity": "high",
                        "summary": "Statement-level support map is missing.",
                    }
                ],
                "proposed_backpressure_items": [
                    {
                        "gap_id": "RVW-002",
                        "failure_type": "non_comparable_inputs",
                        "severity": "high",
                        "failure_statement": "Comparable inputs are absent.",
                    }
                ],
            }
        ),
        unresolved_adequacy=[
            {
                "criterion_id": "adequacy_review_reentry",
                "status": "not_satisfied",
                "unresolved_gap": "The verification methodology remains stale.",
                "target_surface": "branches/verification/analysis.md",
            }
        ],
        claim_review={
            "decision": "blocked_no_score",
            "may_widen_public_benchmark_claims": False,
            "rationale": "No numeric benchmark score exists for review.",
        },
    )

    failure_classes = {ref["failure_class"] for ref in refs}

    assert {"citation", "evidence", "reviewer", "claim_boundary"} <= failure_classes
    assert any(ref["failure_class"] == "scorer_missing" for ref in refs)


def test_evidence_quality_handoff_blocks_source_discovery_as_support(tmp_path: Path):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    (run_dir / "branches" / "deep_search" / "evidence.jsonl").write_text(
        json.dumps(
            {
                "schema_version": "codex-dr.evidence_item.v1",
                "evidence_id": "ev_source_discovery_only",
                "branch_id": "deep_search",
                "record_type": "source_discovery",
                "source_ref": "candidate source URL",
                "admission_status": "admitted",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=runs_dir)

    assert report["status"] == "failed"
    assert "evidence_quality_handoffs_valid" in report["failed_checks"]


def test_evidence_quality_handoff_blocks_non_comparable_ranking(tmp_path: Path):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    (run_dir / "branches" / "data_analysis" / "evidence.jsonl").write_text(
        json.dumps(
            {
                "schema_version": "codex-dr.evidence_item.v1",
                "evidence_id": "ev_unchecked_ranking",
                "branch_id": "data_analysis",
                "record_type": "comparison",
                "claim_type": "ranking",
                "comparative_claim": True,
                "source_ref": "local fixture",
                "admission_status": "admitted",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=runs_dir)

    assert report["status"] == "failed"
    assert "evidence_quality_handoffs_valid" in report["failed_checks"]


def test_provider_off_dr_mesh_cli_stages_validate(tmp_path: Path):
    harness = load_harness()
    runs_dir = TEST_RUNS_ROOT / f"{tmp_path.name}-mesh-staged"
    shutil.rmtree(runs_dir, ignore_errors=True)
    case_id = "draco_mesh_staged_001"
    commands = [
        ["mesh-init-case", case_id, "--force"],
        ["mesh-plan", case_id],
        ["mesh-branch", case_id, "deep_search"],
        ["mesh-branch", case_id, "data_analysis"],
        ["mesh-branch", case_id, "verification"],
        ["mesh-evaluate", case_id],
        ["mesh-review", case_id],
        ["mesh-reentry", case_id, "review_001"],
        ["mesh-report", case_id],
        ["mesh-score", case_id],
        ["mesh-self-improve", case_id],
    ]

    for command in commands:
        assert harness.main(["--runs-dir", str(runs_dir), *command]) == 0

    report = harness.validate_run(case_id, runs_dir=runs_dir)

    assert report["status"] == "passed"
    assert report["failed_checks"] == []


def test_mesh_adequacy_backpressure_queue_compiles_open_gaps(tmp_path: Path):
    harness = load_harness()
    runs_dir = TEST_RUNS_ROOT / f"{tmp_path.name}-mesh-backpressure"
    shutil.rmtree(runs_dir, ignore_errors=True)
    case_id = "draco_mesh_backpressure_001"
    commands = [
        ["mesh-init-case", case_id, "--force"],
        ["mesh-plan", case_id],
        ["mesh-branch", case_id, "deep_search"],
        ["mesh-branch", case_id, "data_analysis"],
        ["mesh-branch", case_id, "verification"],
        ["mesh-evaluate", case_id],
        ["mesh-adequacy-backpressure", case_id],
    ]

    for command in commands:
        assert harness.main(["--runs-dir", str(runs_dir), *command]) == 0

    queue = json.loads(
        (
            runs_dir
            / case_id
            / "backpressure"
            / "adequacy_backpressure_queue.json"
        ).read_text(encoding="utf-8")
    )
    assert queue["schema_version"] == "codex-dr.adequacy_backpressure_queue.v2"
    assert queue["queue_status"] == "open"
    assert queue["writer_blocked"] is True
    assert queue["items"][0]["source_assessment_id"] == "adequacy_initial_001"
    assert queue["items"][0]["required_action"]
    assert queue["items"][0]["target_surface"] == "task_graph.json"
    assert queue["items"][0]["source_refs"] == ["adequacy_assessments.jsonl"]
    assert queue["items"][0]["item_id"] == queue["items"][0]["gap_id"]
    assert "writer_blocking" in queue["items"][0]["gates"]
    assert queue["items"][0]["failure_type"]
    assert queue["items"][0]["closure_authority"] == "reviewer_semantic_adjudication"
    assert "DeepResearch Bench score" in queue["claim_boundary"]["blocked_claims"]
    assert "official benchmark submission" in queue["claim_boundary"]["blocked_claims"]
    assert "scorer-backed evaluation" in queue["claim_boundary"]["blocked_claims"]
    receipt = json.loads(
        (
            runs_dir
            / case_id
            / "backpressure"
            / "backpressure_gate_receipt.json"
        ).read_text(encoding="utf-8")
    )
    assert receipt["schema_version"] == "codex-dr.backpressure_gate_receipt.v1"
    assert receipt["gate_status"] == "writer_blocked"
    assert receipt["writer_blocked"] is True
    assert receipt["writer_may_proceed"] is False
    assert receipt["open_writer_blocking_gap_ids"] == [queue["items"][0]["gap_id"]]


def test_mesh_adequacy_backpressure_queue_compiles_remaining_gap_status(
    tmp_path: Path,
):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    (run_dir / "adequacy_assessments.jsonl").write_text(
        json.dumps(
            {
                "schema_version": "codex-dr.adequacy_assessment.v1",
                "run_id": "draco_mesh_fixture_001",
                "assessment_id": "adequacy_review_reentry",
                "criterion": "adequacy_review_reentry",
                "status": "not_satisfied",
                "evidence": ["reviews/review_001.json", "synthesis.md"],
                "remaining_gap": "A same-basis comparison table is still missing.",
                "follow_up_task": (
                    "Run one narrow re-entry comparison pass before final writing."
                ),
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "mesh-adequacy-backpressure",
                "draco_mesh_fixture_001",
            ]
        )
        == 0
    )

    queue = json.loads(
        (run_dir / "backpressure" / "adequacy_backpressure_queue.json").read_text(
            encoding="utf-8"
        )
    )
    assert queue["queue_status"] == "open"
    assert queue["writer_blocked"] is True
    assert queue["items"][0]["gap"] == "A same-basis comparison table is still missing."
    assert queue["items"][0]["follow_up_task"].startswith("Run one narrow re-entry")
    assert "reviews/review_001.json" in queue["items"][0]["source_refs"]


def test_mesh_adequacy_backpressure_queue_allows_writer_constraints(tmp_path: Path):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    (run_dir / "adequacy_assessments.jsonl").write_text(
        json.dumps(
            {
                "schema_version": "codex-dr.adequacy_assessment.v1",
                "run_id": "draco_mesh_fixture_001",
                "assessment_id": "adequacy_review_reentry",
                "criterion": "adequacy_review_reentry",
                "status": "partially_satisfied",
                "evidence": ["reviews/review_001.json", "synthesis.md"],
                "gaps": [
                    "Market/outlook framing remains constrained to admitted evidence.",
                    "Nine-strata counts require analytical labeling.",
                ],
                "follow_up_task": (
                    "Use the updated synthesis and report_outline as the writer-facing "
                    "surface and preserve these items as unresolved constraints."
                ),
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "mesh-adequacy-backpressure",
                "draco_mesh_fixture_001",
            ]
        )
        == 0
    )

    queue = json.loads(
        (run_dir / "backpressure" / "adequacy_backpressure_queue.json").read_text(
            encoding="utf-8"
        )
    )
    assert queue["queue_status"] == "writer_constraints"
    assert queue["writer_blocked"] is False
    assert {item["target_surface"] for item in queue["items"]} == {"report_outline.md"}
    assert all(item["writer_constraint"] for item in queue["items"])
    assert all("reviews/review_001.json" in item["source_refs"] for item in queue["items"])
    receipt = json.loads(
        (run_dir / "backpressure" / "backpressure_gate_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    assert receipt["gate_status"] == "writer_constraints"
    assert receipt["writer_blocked"] is False
    assert receipt["writer_may_proceed"] is True
    assert len(receipt["writer_constraints"]) == len(queue["items"])
    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=runs_dir)
    assert report["status"] == "passed"
    assert report["failed_checks"] == []


def test_writer_gate_preflight_blocks_missing_or_contradictory_receipt(
    tmp_path: Path,
):
    harness, run_dir, _runs_dir = fresh_mesh_run(tmp_path)
    write_backpressure_queue(run_dir, [citation_reentry_item()])

    preflight = harness.write_writer_gate_preflight(run_dir)

    assert preflight["preflight_status"] == "writer_blocked"
    assert preflight["may_writer_proceed"] is False
    assert "gate receipt is missing" in preflight["blocking_reasons"][0]

    (run_dir / "backpressure" / "backpressure_gate_receipt.json").write_text(
        json.dumps(
            {
                "schema_version": "codex-dr.backpressure_gate_receipt.v1",
                "writer_blocked": False,
                "writer_may_proceed": True,
                "gate_status": "writer_allowed",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    preflight = harness.write_writer_gate_preflight(run_dir)

    assert preflight["preflight_status"] == "writer_blocked"
    assert preflight["may_writer_proceed"] is False
    assert "gate receipt writer_blocked contradicts queue" in preflight[
        "blocking_reasons"
    ]


def test_mesh_adequacy_backpressure_compiles_review_proposed_items(
    tmp_path: Path,
):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    (run_dir / "adequacy_assessments.jsonl").write_text(
        json.dumps(
            {
                "schema_version": "codex-dr.adequacy_assessment.v1",
                "run_id": "draco_mesh_fixture_001",
                "assessment_id": "adequacy_review_reentry",
                "criterion": "adequacy_review_reentry",
                "status": "satisfied",
                "evidence": ["reviews/review_001.json", "synthesis.md"],
                "gaps": [],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "reviews" / "review_001.json").write_text(
        json.dumps(
            {
                "schema_version": "codex_dr_review_v0.2",
                "run_id": "draco_mesh_fixture_001",
                "case_id": "draco_mesh_fixture_001",
                "review_id": "review_001",
                "review_round": 1,
                "review_mode": "initial_synthesis_review",
                "review_status": "requires_citation_verification",
                "proposed_backpressure_items": [
                    {
                        "gap_id": "reviewer_citation_gap_001",
                        "status": "open",
                        "failure_type": "citation_support_gap",
                        "adequacy_criterion_id": "citation_support",
                        "target_surface": "synthesis_and_report_outline",
                        "source_refs": [
                            {
                                "path": "synthesis.md",
                                "span": "material findings",
                                "claim_ids": ["claim_001"],
                            }
                        ],
                        "gate_effects": {
                            "writer_blocking": True,
                            "reentry_required": True,
                            "review_required": True,
                            "claim_blocking": True,
                        },
                        "failure_statement": "A material claim lacks admitted support.",
                        "required_action": {
                            "action_type": "statement_to_source_verification",
                            "assigned_role_family": "verification",
                            "objective": "Map the affected claim to admitted evidence.",
                            "allowed_inputs": ["synthesis.md", "branches/*/evidence.jsonl"],
                            "required_outputs": [
                                "pointer.md",
                                "analysis.md",
                                "evidence.jsonl",
                                "citation_support_map.json",
                            ],
                        },
                        "closure_condition": "Reviewer verifies citation map closure.",
                        "closure_authority": "reviewer",
                        "resolution_mode": None,
                        "resolution_refs": [],
                    }
                ],
                "writer_readiness": {
                    "may_writer_proceed": False,
                    "reason": "Citation support gap remains open.",
                },
                "claim_boundary": {
                    "claims_must_remain_blocked": [
                        "Grep parity",
                        "benchmark score",
                    ],
                    "rationale": "No scorer or claim review authority.",
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    assert not (run_dir / "backpressure" / "adequacy_backpressure_queue.json").exists()

    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "mesh-adequacy-backpressure",
                "draco_mesh_fixture_001",
            ]
        )
        == 0
    )

    queue = json.loads(
        (run_dir / "backpressure" / "adequacy_backpressure_queue.json").read_text(
            encoding="utf-8"
        )
    )
    assert queue["queue_status"] == "open"
    assert queue["writer_blocked"] is True
    assert queue["items"][0]["item_id"] == "reviewer_citation_gap_001"
    assert queue["items"][0]["created_by"] == "harness_review_proposal_compiler"
    assert queue["items"][0]["required_action"] == "statement_to_source_verification"
    assert "reviews/review_001.json" in queue["items"][0]["source_refs"]
    assert "synthesis.md#material findings" in queue["items"][0]["source_refs"]
    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=runs_dir)
    assert report["status"] == "passed"


def compile_review_proposal_queue(
    tmp_path: Path, proposed_items: list[dict]
) -> tuple[object, Path, dict]:
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    (run_dir / "adequacy_assessments.jsonl").write_text(
        json.dumps(
            {
                "schema_version": "codex-dr.adequacy_assessment.v1",
                "run_id": "draco_mesh_fixture_001",
                "assessment_id": "adequacy_review_reentry",
                "criterion": "adequacy_review_reentry",
                "status": "satisfied",
                "evidence": ["reviews/review_001.json", "synthesis.md"],
                "gaps": [],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "reviews" / "review_001.json").write_text(
        json.dumps(
            {
                "schema_version": "codex_dr_review_v0.2",
                "run_id": "draco_mesh_fixture_001",
                "case_id": "draco_mesh_fixture_001",
                "review_id": "review_001",
                "review_status": "not_adequate_writer_blocked",
                "proposed_backpressure_items": proposed_items,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "mesh-adequacy-backpressure",
                "draco_mesh_fixture_001",
            ]
        )
        == 0
    )
    queue = json.loads(
        (run_dir / "backpressure" / "adequacy_backpressure_queue.json").read_text(
            encoding="utf-8"
        )
    )
    return harness, run_dir, queue


def review_proposed_citation_item(gap_id: str = "reviewer_citation_gap_001") -> dict:
    return {
        "gap_id": gap_id,
        "status": "open",
        "failure_type": "citation_support_gap",
        "adequacy_criterion_id": "citation_support",
        "target_surface": "synthesis_and_report_outline",
        "source_refs": [
            {
                "path": "synthesis.md",
                "span": "material findings",
                "claim_ids": ["claim_001"],
            }
        ],
        "gate_effects": {
            "writer_blocking": True,
            "reentry_required": True,
            "review_required": True,
            "claim_blocking": True,
        },
        "failure_statement": "A material claim lacks admitted support.",
        "required_action": {
            "action_type": "statement_to_source_verification",
            "assigned_role_family": "verification",
            "objective": "Map the affected claim to admitted evidence.",
            "allowed_inputs": ["synthesis.md", "branches/*/evidence.jsonl"],
            "required_outputs": [
                "pointer.md",
                "analysis.md",
                "evidence.jsonl",
                "citation_support_map.json",
            ],
        },
        "closure_condition": "Reviewer verifies citation map closure.",
        "closure_authority": "reviewer",
        "resolution_mode": None,
        "resolution_refs": [],
    }


def test_review_proposed_item_missing_closure_is_quarantined(tmp_path: Path):
    item = review_proposed_citation_item()
    item.pop("closure_condition")
    harness, run_dir, queue = compile_review_proposal_queue(tmp_path, [item])

    assert queue["schema_version"] == "codex-dr.adequacy_backpressure_queue.v2"
    assert queue["queue_status"] == "open"
    assert queue["writer_blocked"] is True
    assert queue["items"] == []
    assert queue["quarantined_items"][0]["raw_gap_id"] == "reviewer_citation_gap_001"
    assert "missing closure_condition" in queue["quarantined_items"][0]["problems"]
    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=run_dir.parent)
    assert report["status"] == "passed"


def test_review_proposed_item_missing_required_action_is_quarantined(tmp_path: Path):
    item = review_proposed_citation_item()
    item.pop("required_action")
    _harness, _run_dir, queue = compile_review_proposal_queue(tmp_path, [item])

    assert queue["queue_status"] == "open"
    assert queue["writer_blocked"] is True
    assert queue["items"] == []
    assert "missing required_action" in queue["quarantined_items"][0]["problems"]


def test_review_proposed_item_with_broad_citation_scope_is_quarantined(tmp_path: Path):
    item = review_proposed_citation_item()
    item["source_refs"] = [{"path": "synthesis.md", "span": None, "claim_ids": []}]
    _harness, _run_dir, queue = compile_review_proposal_queue(tmp_path, [item])

    assert queue["queue_status"] == "open"
    assert queue["writer_blocked"] is True
    assert queue["items"] == []
    assert (
        "citation-support item lacks bounded claim/span/section scope"
        in queue["quarantined_items"][0]["problems"]
    )


def test_review_proposed_duplicate_gap_id_is_quarantined(tmp_path: Path):
    item = review_proposed_citation_item()
    duplicate = review_proposed_citation_item()
    _harness, _run_dir, queue = compile_review_proposal_queue(
        tmp_path, [item, duplicate]
    )

    assert [entry["gap_id"] for entry in queue["items"]] == [
        "reviewer_citation_gap_001"
    ]
    assert queue["quarantined_items"][0]["raw_gap_id"] == "reviewer_citation_gap_001"
    assert "duplicate gap_id: reviewer_citation_gap_001" in queue[
        "quarantined_items"
    ][0]["problems"]


def citation_reentry_item(gap_id: str = "gap_citation_support_001") -> dict:
    return {
        "gap_id": gap_id,
        "status": "open",
        "failure_type": "citation_support_gap",
        "adequacy_criterion_id": "material_claims_have_source_support",
        "target_surface": "synthesis_and_report_outline",
        "source_refs": [
            {
                "path": "synthesis.md",
                "span": "material findings",
                "claim_ids": ["claim_001"],
            }
        ],
        "gate_effects": {
            "writer_blocking": True,
            "reentry_required": True,
            "review_required": True,
            "claim_blocking": True,
        },
        "failure_statement": "Material claims are not mapped to admitted evidence.",
        "required_action": {
            "action_type": "statement_to_source_verification",
            "assigned_role_family": "verification",
            "objective": "Map the affected material claim to admitted evidence.",
            "allowed_inputs": [
                "synthesis.md",
                "report_outline.md",
                "branches/*/evidence.jsonl",
            ],
            "required_outputs": ["citation_support_map.json"],
        },
        "closure_condition": (
            "Every affected material claim is directly supported, downgraded, "
            "removed, or accepted as lawful partial by reviewer authority."
        ),
        "closure_authority": "reviewer",
        "resolution_mode": None,
        "resolution_refs": [],
    }


def test_reentry_task_packet_compiler_selects_citation_from_multiple_items(
    tmp_path: Path,
):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    write_backpressure_queue(
        run_dir,
        [
            citation_reentry_item("gap_citation_support_001"),
            citation_reentry_item("gap_citation_support_002"),
        ],
    )

    packet_path = harness.compile_reentry_task_packet(
        "draco_mesh_fixture_001",
        runs_dir=runs_dir,
        compiler_invocation_id="test_multi",
    )

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["compiler_status"] == "ready"
    assert packet["source_gap_id"] == "gap_citation_support_001"
    assert "citation_support_map.json" in packet["task"]["required_outputs"]
    assert packet["writer_permission"] is False
    check = harness.check_reentry_task_packets(run_dir)
    assert check["status"] == "passed"


def test_reentry_task_packet_compiler_blocks_malformed_missing_closure(
    tmp_path: Path,
):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    item = citation_reentry_item()
    item.pop("closure_condition")
    write_backpressure_queue(run_dir, [item])

    packet_path = harness.compile_reentry_task_packet(
        "draco_mesh_fixture_001",
        runs_dir=runs_dir,
        compiler_invocation_id="test_missing_closure",
    )

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["compiler_status"] == "blocked_malformed_queue_item"
    assert "missing closure_condition" in packet["blocked_reason"]
    assert packet["task"] is None


def test_reentry_task_packet_compiler_blocks_broad_citation_scope(tmp_path: Path):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    item = citation_reentry_item()
    item["source_refs"] = [{"path": "synthesis.md", "span": None, "claim_ids": []}]
    write_backpressure_queue(run_dir, [item])

    packet_path = harness.compile_reentry_task_packet(
        "draco_mesh_fixture_001",
        runs_dir=runs_dir,
        compiler_invocation_id="test_broad_citation",
    )

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["compiler_status"] == "blocked_malformed_queue_item"
    assert "citation-support item lacks bounded" in packet["blocked_reason"]
    assert packet["task"] is None


def test_reentry_task_packet_compiler_writes_ready_citation_packet(tmp_path: Path):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    write_backpressure_queue(run_dir, [citation_reentry_item()])

    packet_path = harness.compile_reentry_task_packet(
        "draco_mesh_fixture_001",
        runs_dir=runs_dir,
        compiler_invocation_id="test_ready",
    )

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["compiler_status"] == "ready"
    assert (
        packet["packet_path"]
        == "reentry/gap_citation_support_001/reentry_task_packet.json"
    )
    assert packet["branch_workspace_packet_path"] == "reentry_task_packet.json"
    assert packet["source_gap_id"] == "gap_citation_support_001"
    assert packet["closure"]["closure_authority"] == "reviewer"
    assert packet["writer_permission"] is False
    assert {
        "pointer.md",
        "analysis.md",
        "evidence.jsonl",
        "reentry_result.json",
        "citation_support_map.json",
    } <= set(packet["task"]["required_outputs"])
    assert "synthesis.md" in packet["task"]["resolved_input_files"]
    assert (
        "branches/deep_search/evidence.jsonl"
        in packet["task"]["resolved_input_files"]
    )
    assert packet["trace"]["closure_condition_from"] == "queue.closure_condition"
    check = harness.check_reentry_task_packets(run_dir)
    assert check["status"] == "passed"


def comparability_reentry_item(gap_id: str = "gap_comparability_001") -> dict:
    return {
        "gap_id": gap_id,
        "status": "open",
        "failure_type": "non_comparable_inputs",
        "adequacy_criterion_id": "adequacy_review_reentry",
        "target_surface": "synthesis.md",
        "source_refs": [
            "synthesis.md",
            "branches/data_analysis/analysis.md#Comparability Limits And Follow-up",
            "branches/deep_search/analysis.md#Contradictions And Gaps",
        ],
        "gates": [
            "writer_blocking",
            "reentry_required",
            "review_required",
            "claim_blocking",
        ],
        "writer_blocking": True,
        "failure_statement": "The comparison is not closed on a common metric.",
        "required_action_detail": {
            "action_type": "reentry_research",
            "objective": "Collect comparison-ready evidence or preserve a narrowed answer.",
            "allowed_inputs": [
                "synthesis.md",
                "branches/data_analysis/analysis.md",
                "branches/deep_search/analysis.md",
            ],
            "required_outputs": ["comparability_assessment.json"],
        },
        "closure_condition": (
            "Reviewer verifies the comparison is closed or explicitly narrowed."
        ),
        "closure_authority": "reviewer_semantic_adjudication_after_reentry",
    }


def test_reentry_task_packet_compiler_selects_reentry_required_comparability(
    tmp_path: Path,
):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    methodology_item = citation_reentry_item("gap_methodology_001")
    methodology_item["failure_type"] = "methodology_gap"
    methodology_item["gates"] = ["writer_blocking", "review_required"]
    methodology_item["gate_effects"] = {
        "writer_blocking": True,
        "reentry_required": False,
        "review_required": True,
        "claim_blocking": True,
    }
    write_backpressure_queue(
        run_dir,
        [
            methodology_item,
            comparability_reentry_item("RVW-002"),
        ],
    )

    packet_path = harness.compile_reentry_task_packet(
        "draco_mesh_fixture_001",
        runs_dir=runs_dir,
        compiler_invocation_id="test_comparability_selection",
    )

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["compiler_status"] == "ready"
    assert packet["source_gap_id"] == "RVW-002"
    assert packet["packet_path"] == "reentry/rvw-002/reentry_task_packet.json"
    assert packet["task"]["action_type"] == "reentry_research"
    assert "comparability_assessment.json" in packet["task"]["required_outputs"]
    assert packet["writer_permission"] is False


def write_reentry_result(
    branch_dir: Path,
    *,
    gap_id: str,
    proposed_next_status: str,
) -> Path:
    branch_dir.mkdir(parents=True, exist_ok=True)
    result_path = branch_dir / "reentry_result.json"
    result_path.write_text(
        json.dumps(
            {
                "schema_version": "codex_dr_reentry_result_v0.2",
                "run_id": "draco_mesh_fixture_001",
                "case_id": "draco_mesh_fixture_001",
                "source_gap_id": gap_id,
                "source_task_packet_path": "reentry_task_packet.json",
                "branch_status": "completed",
                "attempted_action": "Verify scoped citation support.",
                "artifacts_written": ["pointer.md", "analysis.md", "evidence.jsonl"],
                "closure_condition_assessment": {
                    "closure_condition": "Reviewer verifies citation map closure.",
                    "condition_satisfied": proposed_next_status == "closed_candidate",
                    "rationale": "Branch proposal is not reviewer closure.",
                },
                "proposed_next_status": proposed_next_status,
                "remaining_blockers": [],
                "reviewer_notes": "Reviewer must adjudicate.",
                "claim_boundary": {"must_not_claim": ["grep_parity"]},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return result_path


def write_adequacy_delta(
    run_dir: Path,
    *,
    gap_id: str,
    proposed_next_status: str,
    closure_authorized: bool = False,
) -> None:
    reentry_dir = run_dir / "reentry" / gap_id
    reentry_dir.mkdir(parents=True, exist_ok=True)
    (reentry_dir / "reentry_synthesis.md").write_text(
        f"# Re-entry Synthesis\n\nSource gap: `{gap_id}`\n\n"
        "Repair evidence remains reviewer-adjudicated.\n",
        encoding="utf-8",
    )
    (reentry_dir / "adequacy_delta.json").write_text(
        json.dumps(
            {
                "schema_version": "codex_dr_reentry_adequacy_delta.v1",
                "run_id": "draco_mesh_fixture_001",
                "case_id": "draco_mesh_fixture_001",
                "source_gap_id": gap_id,
                "source_task_packet_path": f"reentry/{gap_id}/reentry_task_packet.json",
                "source_reentry_result_path": (
                    "branches/reentry_followup_002/reentry_result.json"
                ),
                "reentry_synthesis_path": f"reentry/{gap_id}/reentry_synthesis.md",
                "evidence_delta": ["Scoped citation support was checked."],
                "proposed_next_status": proposed_next_status,
                "remaining_blockers": (
                    ["One material claim remains unsupported."]
                    if proposed_next_status == "narrowed"
                    else []
                ),
                "reviewer_next_action": "Adjudicate whether the blocker remains open.",
                "closure_authority": "reviewer",
                "closure_authorized": closure_authorized,
                "writer_permission": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def test_citation_support_closed_candidate_without_map_fails(tmp_path: Path):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    write_backpressure_queue(run_dir, [citation_reentry_item()])
    harness.compile_reentry_task_packet(
        "draco_mesh_fixture_001",
        runs_dir=runs_dir,
        compiler_invocation_id="test_citation_missing_map",
    )
    write_reentry_result(
        run_dir / "branches" / "reentry_followup_002",
        gap_id="gap_citation_support_001",
        proposed_next_status="closed_candidate",
    )

    check = harness.check_citation_support_maps(run_dir)

    assert check["status"] == "failed"
    assert "closed_candidate lacks citation_support_map.json" in check["details"]


def test_reentry_synthesis_delta_preserves_narrowed_not_closed(tmp_path: Path):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    write_backpressure_queue(run_dir, [citation_reentry_item()])
    harness.compile_reentry_task_packet(
        "draco_mesh_fixture_001",
        runs_dir=runs_dir,
        compiler_invocation_id="test_narrowed",
    )
    branch_dir = run_dir / "branches" / "reentry_followup_002"
    write_reentry_result(
        branch_dir,
        gap_id="gap_citation_support_001",
        proposed_next_status="narrowed",
    )
    (branch_dir / "citation_support_map.json").write_text(
        json.dumps(
            {
                "schema_version": "codex_dr_citation_support_map.v1",
                "source_gap_id": "gap_citation_support_001",
                "claims": [
                    {
                        "claim_id": "claim_001",
                        "claim_text": "Unsupported material claim.",
                        "support_status": "unsupported",
                        "evidence_refs": [],
                        "writer_blocking": True,
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    write_adequacy_delta(
        run_dir,
        gap_id="gap_citation_support_001",
        proposed_next_status="narrowed",
    )

    synthesis_check = harness.check_reentry_synthesis_outputs(run_dir)
    citation_check = harness.check_citation_support_maps(run_dir)
    harness.write_backpressure_gate_receipt(run_dir)
    preflight = harness.write_writer_gate_preflight(run_dir)

    assert synthesis_check["status"] == "passed"
    assert citation_check["status"] == "passed"
    assert preflight["may_writer_proceed"] is False
    assert "open writer-blocking adequacy backpressure exists" in preflight[
        "blocking_reasons"
    ]


def test_legacy_citation_support_map_shape_remains_inspectable(tmp_path: Path):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    write_backpressure_queue(run_dir, [citation_reentry_item()])
    harness.compile_reentry_task_packet(
        "draco_mesh_fixture_001",
        runs_dir=runs_dir,
        compiler_invocation_id="test_legacy_citation_map",
    )
    branch_dir = run_dir / "branches" / "reentry_followup_002"
    write_reentry_result(
        branch_dir,
        gap_id="gap_citation_support_001",
        proposed_next_status="narrowed",
    )
    (branch_dir / "citation_support_map.json").write_text(
        json.dumps(
            {
                "schema_version": "codex_dr_citation_support_map_v0.1",
                "source_gap_id": "gap_citation_support_001",
                "support_map": [
                    {
                        "statement_id": "claim_001",
                        "statement": "A bounded statement.",
                        "support_status": "supported",
                        "evidence_refs": [
                            "branches/reentry_followup_002/evidence.jsonl#e1"
                        ],
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    check = harness.check_citation_support_maps(run_dir)

    assert check["status"] == "passed"


def test_reentry_synthesis_delta_rejects_self_closure(tmp_path: Path):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    write_backpressure_queue(run_dir, [citation_reentry_item()])
    harness.compile_reentry_task_packet(
        "draco_mesh_fixture_001",
        runs_dir=runs_dir,
        compiler_invocation_id="test_self_closure",
    )
    write_reentry_result(
        run_dir / "branches" / "reentry_followup_002",
        gap_id="gap_citation_support_001",
        proposed_next_status="closed_candidate",
    )
    write_adequacy_delta(
        run_dir,
        gap_id="gap_citation_support_001",
        proposed_next_status="closed_candidate",
        closure_authorized=True,
    )

    check = harness.check_reentry_synthesis_outputs(run_dir)

    assert check["status"] == "failed"
    assert "adequacy_delta cannot authorize closure" in check["details"]


def test_reentry_synthesis_accepts_narrowed_review_pending_delta(tmp_path: Path):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    write_backpressure_queue(run_dir, [citation_reentry_item()])
    harness.compile_reentry_task_packet(
        "draco_mesh_fixture_001",
        runs_dir=runs_dir,
        compiler_invocation_id="test_narrowed_review_pending",
    )
    branch_dir = run_dir / "branches" / "reentry_followup_002"
    write_reentry_result(
        branch_dir,
        gap_id="gap_citation_support_001",
        proposed_next_status="narrowed",
    )
    write_adequacy_delta(
        run_dir,
        gap_id="gap_citation_support_001",
        proposed_next_status="narrowed_review_pending",
    )

    check = harness.check_reentry_synthesis_outputs(run_dir)

    assert check["status"] == "passed"


def test_mesh_execute_live_fails_on_forbidden_reviewer_queue_output(tmp_path: Path):
    harness, _run_dir, runs_dir, _dry_receipt = fresh_live_planned_mesh(tmp_path)
    live_receipt = runs_dir / "live_control.json"
    write_live_execution_control_receipt(live_receipt, "draco_mesh_fixture_001")
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "mesh-live-plan",
                "draco_mesh_fixture_001",
                "--run-control",
                str(live_receipt),
            ]
        )
        == 0
    )

    with pytest.raises(harness.HarnessError, match="forbidden output"):
        harness.mesh_execute_live(
            "draco_mesh_fixture_001",
            run_control=live_receipt,
            runs_dir=runs_dir,
            codex_runner=fake_live_codex_runner_with_forbidden_reviewer_queue,
        )


def test_mesh_execute_live_allows_reviewer_to_read_existing_queue_input(tmp_path: Path):
    harness, run_dir, runs_dir, _dry_receipt = fresh_live_planned_mesh(tmp_path)
    live_receipt = runs_dir / "live_control.json"
    write_live_execution_control_receipt(live_receipt, "draco_mesh_fixture_001")
    queue_path = run_dir / "backpressure" / "adequacy_backpressure_queue.json"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(
        json.dumps(
            {
                "schema_version": "codex-dr.adequacy_backpressure_queue.v2",
                "queue_status": "open",
                "writer_blocked": True,
                "items": [],
                "quarantined_items": [],
                "normalization_summary": {
                    "canonical_item_count": 0,
                    "review_proposed_item_count": 0,
                    "quarantined_review_proposal_count": 0,
                    "legacy_fields_normalized_by": "harness",
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "mesh-live-plan",
                "draco_mesh_fixture_001",
                "--run-control",
                str(live_receipt),
            ]
        )
        == 0
    )

    harness.mesh_execute_live(
        "draco_mesh_fixture_001",
        run_control=live_receipt,
        runs_dir=runs_dir,
        codex_runner=fake_live_codex_runner,
    )

    summary = json.loads(
        (run_dir / "live_executor" / "execution_summary.json").read_text(
            encoding="utf-8"
        )
    )
    review_role = next(role for role in summary["roles"] if role["task_id"] == "task_review")
    assert "backpressure/adequacy_backpressure_queue.json" in review_role["copied_inputs"]


def test_mesh_execute_live_fails_on_forbidden_reentry_queue_output(tmp_path: Path):
    harness, _run_dir, runs_dir, _dry_receipt = fresh_live_planned_mesh(tmp_path)
    live_receipt = runs_dir / "live_control.json"
    write_live_execution_control_receipt(live_receipt, "draco_mesh_fixture_001")
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "mesh-live-plan",
                "draco_mesh_fixture_001",
                "--run-control",
                str(live_receipt),
            ]
        )
        == 0
    )

    with pytest.raises(harness.HarnessError, match="forbidden output"):
        harness.mesh_execute_live(
            "draco_mesh_fixture_001",
            run_control=live_receipt,
            runs_dir=runs_dir,
            codex_runner=fake_live_codex_runner_with_forbidden_reentry_queue,
        )


def test_mesh_validation_fails_unqueued_adequacy_gaps(tmp_path: Path):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    (run_dir / "adequacy_assessments.jsonl").write_text(
        json.dumps(
            {
                "schema_version": "codex-dr.adequacy_assessment.v1",
                "run_id": "draco_mesh_fixture_001",
                "assessment_id": "adequacy_regression_001",
                "criteria_checked": ["adequacy_mesh_branch_triplets"],
                "branch_ids": ["deep_search"],
                "status": "needs_more_research",
                "gaps": ["verification branch needs a targeted follow-up"],
                "decision_event_id": "evt_0020_adequacy_assessed",
                "produced_by_event": "evt_0020_adequacy_assessed",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=runs_dir)

    assert report["status"] == "failed"
    assert "adequacy_backpressure_queue_present" in report["failed_checks"]


def test_mesh_live_plan_fails_closed_without_run_control(tmp_path: Path):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)

    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "mesh-live-plan",
            "draco_mesh_fixture_001",
            "--run-control",
            str(runs_dir / "missing_run_control.json"),
        ]
    )

    assert result == 2
    assert not (run_dir / "live_adapter").exists()
    assert not (run_dir / "provider_metadata.json").exists()
    assert not (run_dir / "transcripts").exists()


def test_mesh_live_plan_renders_dry_run_launch_plan(tmp_path: Path):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    receipt_path = runs_dir / "dry_run_control.json"
    write_dry_run_control_receipt(receipt_path, "draco_mesh_fixture_001")

    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "mesh-live-plan",
            "draco_mesh_fixture_001",
            "--run-control",
            str(receipt_path),
        ]
    )

    assert result == 0
    launch_plan_path = run_dir / "live_adapter" / "launch_plan.json"
    launch_plan = json.loads(launch_plan_path.read_text(encoding="utf-8"))
    assert launch_plan["launch_mode"] == "dry_run_only"
    assert launch_plan["run_control_receipt"] == str(receipt_path)
    assert len(launch_plan["role_launch_plans"]) >= 6
    task_order = [plan["task_id"] for plan in launch_plan["role_launch_plans"]]
    assert task_order.index("task_reentry_followup") < task_order.index("task_final_writer")
    assert task_order.index("task_reentry_followup") < task_order.index(
        "task_reentry_synthesis"
    )
    assert task_order.index("task_reentry_synthesis") < task_order.index(
        "task_final_writer"
    )
    deep_search = next(
        plan for plan in launch_plan["role_launch_plans"] if plan["task_id"] == "task_deep_search"
    )
    assert deep_search["command_plan"][:3] == ["codex", "exec", "--json"]
    assert deep_search["cwd"].endswith(
        "sandbox/codex-dr/.agent-workspaces/draco_mesh_fixture_001/deep_search"
    )
    assert deep_search["output_paths"] == [
        "branches/deep_search/pointer.md",
        "branches/deep_search/analysis.md",
        "branches/deep_search/evidence.jsonl",
    ]
    assert deep_search["wall_clock_bound_minutes"] == 15
    assert deep_search["kill_path"] == "foreground supervisor sends SIGINT, then SIGTERM"
    assert deep_search["claim_boundary"]["blocked_claims"] == [
        "Grep parity",
        "DRACO score",
        "leaderboard rank",
        "product readiness",
    ]
    assert (run_dir / deep_search["prompt_file"]).exists()
    assert not (run_dir / "provider_metadata.json").exists()
    assert not (run_dir / "transcripts").exists()


def test_live_role_prompts_include_hardened_sections(tmp_path: Path):
    _harness, run_dir, _runs_dir, _receipt_path = fresh_live_planned_mesh(tmp_path)
    prompt_root = run_dir / "live_adapter" / "prompts"
    required_sections = [
        "## DR Mesh Charter",
        "## Role-Specific Instructions",
        "## Output File Contract",
        "## Pointer-First Law",
        "## Source Policy",
        "## Citation Discipline",
        "## Adequacy Criteria",
        "## Adequacy Backpressure Law",
        "## Claim Boundary",
    ]

    for prompt_path in prompt_root.glob("*.md"):
        prompt = prompt_path.read_text(encoding="utf-8")
        for section in required_sections:
            assert section in prompt
        assert "sandbox/codex-dr/harness-specs/live_role_prompt_pack.md" in prompt
        assert "sandbox/codex-dr/harness-specs/dr_mesh_parity_charter.md" in prompt
        assert "Do not claim Grep parity" in prompt

    planner_prompt = (prompt_root / "task_plan.md").read_text(encoding="utf-8")
    assert "Researcher-Planner" in planner_prompt
    assert "awaiting_ratification" in planner_prompt
    assert "blocked_by_input" in planner_prompt
    assert "executable: false" in planner_prompt
    assert "Do not answer the research question" in planner_prompt
    assert "default authorization must come from the user" in planner_prompt
    assert "codex-dr.task_graph.v1" in planner_prompt
    assert "`skills_tools.json` must be valid JSON" in planner_prompt
    assert "`adequacy_criteria.json` must be valid JSON" in planner_prompt
    assert "`task_graph.json` must be valid JSON" in planner_prompt
    deep_search_prompt = (prompt_root / "task_deep_search.md").read_text(
        encoding="utf-8"
    )
    assert "source discovery as source validation" in deep_search_prompt
    assert "what each source supports, what it does not support" in deep_search_prompt
    assert "`status` is not an acceptable" in deep_search_prompt
    data_prompt = (prompt_root / "task_data_analysis.md").read_text(
        encoding="utf-8"
    )
    assert "non_comparable_inputs" in data_prompt
    assert "Do not rank, compare, forecast, or normalize" in data_prompt
    verification_prompt = (prompt_root / "task_verification.md").read_text(
        encoding="utf-8"
    )
    assert "Distinguish source existence from statement-to-source support" in (
        verification_prompt
    )
    assert "too_broad_for_evidence" in verification_prompt
    assert "Read pointer files before analysis files" in (
        prompt_root / "task_pointer_first_synthesis.md"
    ).read_text(encoding="utf-8")
    synthesis_prompt = (prompt_root / "task_pointer_first_synthesis.md").read_text(
        encoding="utf-8"
    )
    assert "do not write the\ncanonical backpressure queue" in synthesis_prompt
    reentry_synthesis_prompt = (
        prompt_root / "task_reentry_synthesis.md"
    ).read_text(encoding="utf-8")
    assert "selected_analysis_spans" in reentry_synthesis_prompt
    assert "Treat `repair_returned`, `narrowed`, and" in reentry_synthesis_prompt
    assert "adjudicates closure; the harness updates queue" in reentry_synthesis_prompt
    assert "schema_version: \"codex_dr_reentry_adequacy_delta.v1\"" in (
        reentry_synthesis_prompt
    )
    assert "source_reentry_result_path" in reentry_synthesis_prompt
    assert "Do not use `codex_dr_adequacy_delta_v0.1`" in reentry_synthesis_prompt
    assert "Adjudicate admitted synthesis" in (
        prompt_root / "task_review.md"
    ).read_text(encoding="utf-8")
    review_prompt = (prompt_root / "task_review.md").read_text(encoding="utf-8")
    assert "backpressure/backpressure_gate_receipt.json" in review_prompt
    assert "`repair_returned` is not closure" in review_prompt
    assert "citation_support_map.json" in review_prompt
    launch_plan = json.loads(
        (run_dir / "live_adapter" / "launch_plan.json").read_text(encoding="utf-8")
    )
    review_plan = next(
        plan for plan in launch_plan["role_launch_plans"] if plan["task_id"] == "task_review"
    )
    assert review_plan["output_paths"] == ["reviews/review_001.json"]
    assert "proposed_backpressure_items" in review_prompt
    assert "canonical queue directly" in review_prompt
    assert "backpressure/adequacy_backpressure_queue.json" not in review_plan[
        "output_paths"
    ]
    writer_plan = next(
        plan
        for plan in launch_plan["role_launch_plans"]
        if plan["task_id"] == "task_final_writer"
    )
    assert (
        "backpressure/adequacy_backpressure_queue.json"
        in writer_plan["allowed_input_files"]
    )
    reentry_prompt = (prompt_root / "task_reentry_followup.md").read_text(
        encoding="utf-8"
    )
    assert "reentry_task_packet.json" in reentry_prompt
    assert "blocker_record" in reentry_prompt
    assert "citation_support_map.json" in reentry_prompt
    assert "The reviewer adjudicates closure" in reentry_prompt
    assert "Do not write\n`backpressure/adequacy_backpressure_queue.json`" in reentry_prompt
    assert "`status` as a substitute field" in reentry_prompt
    writer_prompt = (prompt_root / "task_final_writer.md").read_text(
        encoding="utf-8"
    )
    assert "one coherent report voice" in writer_prompt
    assert "blocked-state output rather than a final answer" in writer_prompt
    assert "Do not claim final-answer success" in writer_prompt


def test_prompt_contract_drift_guard_fails_generated_prompt_authority_drift(
    tmp_path: Path,
):
    harness, run_dir, runs_dir, _receipt_path = fresh_live_planned_mesh(tmp_path)
    prompt_path = run_dir / "live_adapter" / "prompts" / "task_final_writer.md"
    prompt = prompt_path.read_text(encoding="utf-8")
    prompt_path.write_text(
        prompt.replace("writer_gate_preflight.json", "writer_gate_status.txt"),
        encoding="utf-8",
    )
    harness.refresh_artifact_manifest(run_dir)

    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=runs_dir)

    assert "prompt_contract_drift_guard" in report["failed_checks"]
    check = next(
        item
        for item in report["checks"]
        if item["check_id"] == "prompt_contract_drift_guard"
    )
    assert "task_final_writer" in check["details"]
    assert "writer_gate_preflight" in check["details"]


def test_live_prompt_builder_requires_output_contract_and_non_claims(tmp_path: Path):
    harness = load_harness()
    receipt_path = tmp_path / "receipt.json"
    write_dry_run_control_receipt(receipt_path, "draco_mesh_fixture_001")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    task = {
        "task_id": "task_bad",
        "kind": "branch_research",
        "objective": "Bad task lacks output contract.",
        "inputs": ["plan.md"],
        "expected_outputs": [],
        "adequacy_checks": [],
    }
    role = {"role": "deep_search", "return_contract": []}

    with pytest.raises(harness.HarnessError, match="lacks output contract"):
        harness.live_adapter_prompt("draco_mesh_fixture_001", task, role, receipt)

    task["expected_outputs"] = ["branches/deep_search/pointer.md"]
    receipt["non_claims_even_if_success"] = []
    with pytest.raises(harness.HarnessError, match="lacks non-claims"):
        harness.live_adapter_prompt("draco_mesh_fixture_001", task, role, receipt)


def test_mesh_executor_preflight_prepares_no_launch_metadata(tmp_path: Path):
    harness, run_dir, runs_dir, receipt_path = fresh_live_planned_mesh(tmp_path)

    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "mesh-executor-preflight",
            "draco_mesh_fixture_001",
            "--run-control",
            str(receipt_path),
        ]
    )

    assert result == 0
    preflight_path = run_dir / "live_executor" / "execution_preflight.json"
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    assert preflight["execution_status"] == "prepared_not_launched_dry_run_receipt"
    assert preflight["will_execute"] is False
    assert preflight["run_control_receipt"] == str(receipt_path)
    assert preflight["transcript_root"].endswith(
        "sandbox/codex-dr/runs/draco_mesh_fixture_001/transcripts/"
    )
    deep_search = next(
        role for role in preflight["role_preflights"] if role["task_id"] == "task_deep_search"
    )
    assert deep_search["workspace_path"].endswith(
        "sandbox/codex-dr/.agent-workspaces/draco_mesh_fixture_001/deep_search"
    )
    assert deep_search["transcript_path"] == "transcripts/task_deep_search.jsonl"
    assert deep_search["output_paths"] == [
        "branches/deep_search/pointer.md",
        "branches/deep_search/analysis.md",
        "branches/deep_search/evidence.jsonl",
    ]
    assert deep_search["supervision"]["will_execute"] is False
    assert not (run_dir / "provider_metadata.json").exists()
    assert not (run_dir / "transcripts").exists()
    assert not (run_dir / "live_executor" / "outputs").exists()


def test_model_probe_records_unavailable_model_without_promotion(tmp_path: Path):
    harness = load_harness()

    receipt = harness.probe_codex_model(
        "gpt-5.5",
        output_dir=tmp_path,
        runner=fake_unavailable_model_probe_runner,
    )

    assert receipt["schema_version"] == "codex-dr.model_probe_receipt.v1"
    assert receipt["model"] == "gpt-5.5"
    assert receipt["status"] == "unavailable"
    assert receipt["observed_error_class"] == "model_unavailable_or_no_access"
    assert receipt["current_live_default"] == "gpt-5.4"
    assert receipt["may_promote_live_default"] is False
    assert receipt["recommendation"] == "keep gpt-5.4 as live default"
    assert Path(receipt["receipt_path"]).exists()
    assert Path(receipt["transcript_path"]).exists()
    assert "--model" in receipt["command"]
    assert "gpt-5.5" in receipt["command"]


def test_model_probe_records_available_model_as_manual_promotion_candidate(
    tmp_path: Path,
):
    harness = load_harness()

    receipt = harness.probe_codex_model(
        "gpt-5.4",
        output_dir=tmp_path,
        runner=fake_available_model_probe_runner,
    )

    assert receipt["status"] == "available"
    assert receipt["observed_error_class"] is None
    assert receipt["may_promote_live_default"] is True
    assert receipt["recommendation"] == "eligible_for_manual_default_promotion"
    assert receipt["last_message_observed"] == "codex-dr model probe ok"
    assert "Grep parity" in receipt["claim_boundary"]["blocked_claims"]


def test_model_probe_rejects_unsafe_model_name(tmp_path: Path):
    harness = load_harness()

    with pytest.raises(harness.HarnessError, match="model must match"):
        harness.probe_codex_model("../gpt-5.5", output_dir=tmp_path)


def test_mesh_executor_preflight_fails_closed_without_launch_plan(tmp_path: Path):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    receipt_path = runs_dir / "dry_run_control.json"
    write_dry_run_control_receipt(receipt_path, "draco_mesh_fixture_001")

    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "mesh-executor-preflight",
            "draco_mesh_fixture_001",
            "--run-control",
            str(receipt_path),
        ]
    )

    assert result == 2
    assert not (run_dir / "live_executor").exists()
    assert not (run_dir / "provider_metadata.json").exists()
    assert not (run_dir / "transcripts").exists()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda receipt_path, _run_dir: set_receipt_execution_approved(receipt_path),
        lambda _receipt_path, run_dir: set_launch_plan_run_id(
            run_dir / "live_adapter" / "launch_plan.json", "other_run"
        ),
        lambda _receipt_path, run_dir: remove_launch_plan_field(
            run_dir / "live_adapter" / "launch_plan.json", "cwd"
        ),
        lambda receipt_path, _run_dir: remove_receipt_transcript_root(receipt_path),
        lambda _receipt_path, run_dir: remove_launch_plan_field(
            run_dir / "live_adapter" / "launch_plan.json", "output_paths"
        ),
    ],
)
def test_mesh_executor_preflight_fails_closed_on_invalid_preconditions(
    tmp_path: Path, mutation
):
    harness, run_dir, runs_dir, receipt_path = fresh_live_planned_mesh(tmp_path)
    mutation(receipt_path, run_dir)

    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "mesh-executor-preflight",
            "draco_mesh_fixture_001",
            "--run-control",
            str(receipt_path),
        ]
    )

    assert result == 2
    assert not (run_dir / "live_executor").exists()
    assert not (run_dir / "provider_metadata.json").exists()
    assert not (run_dir / "transcripts").exists()


def test_mesh_execute_live_refuses_dry_run_receipt(tmp_path: Path):
    harness, run_dir, runs_dir, receipt_path = fresh_live_planned_mesh(tmp_path)

    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "mesh-execute-live",
            "draco_mesh_fixture_001",
            "--run-control",
            str(receipt_path),
        ]
    )

    assert result == 2
    assert not (run_dir / "transcripts").exists()
    assert not (run_dir / "live_executor" / "execution_summary.json").exists()


def test_mesh_execute_live_stubbed_roles_write_custody(tmp_path: Path):
    harness, run_dir, runs_dir, _dry_receipt = fresh_live_planned_mesh(tmp_path)
    live_receipt = runs_dir / "live_control.json"
    write_live_execution_control_receipt(live_receipt, "draco_mesh_fixture_001")
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "mesh-live-plan",
                "draco_mesh_fixture_001",
                "--run-control",
                str(live_receipt),
            ]
        )
        == 0
    )

    harness.mesh_execute_live(
        "draco_mesh_fixture_001",
        run_control=live_receipt,
        runs_dir=runs_dir,
        codex_runner=fake_live_codex_runner,
    )

    summary = json.loads(
        (run_dir / "live_executor" / "execution_summary.json").read_text(
            encoding="utf-8"
        )
    )
    launch_plan = json.loads(
        (run_dir / "live_adapter" / "launch_plan.json").read_text(encoding="utf-8")
    )
    assert launch_plan["launch_mode"] == "live_authorized_pending_execution"
    assert launch_plan["run_control_receipt"] == str(live_receipt)
    assert summary["run_control_receipt"] == str(live_receipt)
    assert summary["automatic_retry_allowed"] is False
    assert len(summary["roles"]) == len(launch_plan["role_launch_plans"])
    role_order = [role["task_id"] for role in summary["roles"]]
    assert role_order.index("task_reentry_followup") < role_order.index("task_final_writer")
    assert role_order.index("task_reentry_followup") < role_order.index(
        "task_reentry_synthesis"
    )
    assert role_order.index("task_reentry_synthesis") < role_order.index(
        "task_final_writer"
    )
    assert summary["scorer_status"] == "blocked"
    assert all(role["returncode"] == 0 for role in summary["roles"])
    context_index = json.loads(
        (run_dir / "live_executor" / "context_thread_index.json").read_text(
            encoding="utf-8"
        )
    )
    assert context_index["schema_version"] == "codex-dr.context_thread_index.v1"
    assert context_index["role_count"] == len(summary["roles"])
    plan_context = next(
        role for role in context_index["roles"] if role["task_id"] == "task_plan"
    )
    assert plan_context["thread_ids"] == ["thread_task_plan"]
    assert plan_context["context_admission"]["copied_input_files"] == ["case_manifest.json"]
    assert plan_context["context_admission"]["total_input_bytes"] > 0
    deep_search = next(role for role in summary["roles"] if role["task_id"] == "task_deep_search")
    assert deep_search["copied_outputs"] == [
        "live_executor/role_outputs/task_deep_search/branches/deep_search/pointer.md",
        "live_executor/role_outputs/task_deep_search/branches/deep_search/analysis.md",
        "live_executor/role_outputs/task_deep_search/branches/deep_search/evidence.jsonl",
    ]
    assert (run_dir / deep_search["transcript_path"]).exists()
    assert (run_dir / deep_search["last_message_path"]).exists()
    assert (run_dir / "live_executor" / "run_control_receipt.json").exists()
    events = [
        json.loads(line)
        for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    live_events = [
        event for event in events if event["event_type"] == "live_executor.role_completed"
    ]
    assert len(live_events) == len(launch_plan["role_launch_plans"])
    assert all(event["decision"]["rationale"] for event in live_events)
    assert (
        "Live stub output for task_deep_search"
        in (
            run_dir
            / "live_executor"
            / "role_outputs"
            / "task_deep_search"
            / "branches"
            / "deep_search"
            / "pointer.md"
        ).read_text(encoding="utf-8")
    )
    task_graph = json.loads((run_dir / "task_graph.json").read_text(encoding="utf-8"))
    assert any(task["task_id"] == "task_reentry_synthesis" for task in task_graph["tasks"])
    assert all("stubbed_live_role" not in json.dumps(task) for task in task_graph["tasks"])
    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=runs_dir)
    assert report["status"] == "passed"
    assert report["failed_checks"] == []

    writer_index = role_order.index("task_final_writer")
    reentry_index = role_order.index("task_reentry_followup")
    summary["roles"][writer_index], summary["roles"][reentry_index] = (
        summary["roles"][reentry_index],
        summary["roles"][writer_index],
    )
    (run_dir / "live_executor" / "execution_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=runs_dir)
    assert report["status"] == "failed"
    assert "live_execution_custody_present" in report["failed_checks"]


def test_mesh_execute_live_materializes_writer_constraint_backpressure(tmp_path: Path):
    harness, run_dir, runs_dir, _dry_receipt = fresh_live_planned_mesh(tmp_path)
    live_receipt = runs_dir / "live_control.json"
    write_live_execution_control_receipt(live_receipt, "draco_mesh_fixture_001")
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "mesh-live-plan",
                "draco_mesh_fixture_001",
                "--run-control",
                str(live_receipt),
            ]
        )
        == 0
    )

    harness.mesh_execute_live(
        "draco_mesh_fixture_001",
        run_control=live_receipt,
        runs_dir=runs_dir,
        codex_runner=fake_live_codex_runner_with_writer_constraints,
    )

    queue = json.loads(
        (run_dir / "backpressure" / "adequacy_backpressure_queue.json").read_text(
            encoding="utf-8"
        )
    )
    assert queue["queue_status"] == "writer_constraints"
    assert queue["writer_blocked"] is False
    assert queue["triggering_task_ids"] == ["task_reentry_synthesis"]
    assert all(item["resolution_mode"] == "writer_constraint" for item in queue["items"])
    assert (run_dir / "report.md").exists()
    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=runs_dir)
    assert report["status"] == "passed"
    assert report["failed_checks"] == []


def test_mesh_execute_live_lawfully_blocks_writer_on_open_backpressure(tmp_path: Path):
    harness, run_dir, runs_dir, _dry_receipt = fresh_live_planned_mesh(tmp_path)
    live_receipt = runs_dir / "live_control.json"
    write_live_execution_control_receipt(live_receipt, "draco_mesh_fixture_001")
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "mesh-live-plan",
                "draco_mesh_fixture_001",
                "--run-control",
                str(live_receipt),
            ]
        )
        == 0
    )

    with pytest.raises(harness.HarnessError, match="blocked by open adequacy"):
        harness.mesh_execute_live(
            "draco_mesh_fixture_001",
            run_control=live_receipt,
            runs_dir=runs_dir,
            codex_runner=fake_live_codex_runner_with_open_backpressure,
        )

    summary = json.loads(
        (run_dir / "live_executor" / "execution_summary.json").read_text(
            encoding="utf-8"
        )
    )
    queue = json.loads(
        (run_dir / "backpressure" / "adequacy_backpressure_queue.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["execution_status"] == "blocked_by_adequacy_backpressure"
    assert summary["blocked_task_ids"] == ["task_final_writer"]
    assert summary["role_count"] == 10
    assert summary["recursive_reentry_rounds_used"] == 1
    assert [
        role["task_id"] for role in summary["dynamic_role_launch_plans"]
    ] == ["task_reentry_followup_002", "task_reentry_synthesis_002"]
    assert queue["queue_status"] == "open"
    assert queue["writer_blocked"] is True
    receipt = json.loads(
        (run_dir / "backpressure" / "backpressure_gate_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    preflight = json.loads(
        (run_dir / "writer_gate_preflight.json").read_text(encoding="utf-8")
    )
    assert receipt["gate_status"] == "writer_blocked"
    assert receipt["writer_may_proceed"] is False
    assert preflight["preflight_status"] == "writer_blocked"
    assert preflight["may_writer_proceed"] is False
    assert "open writer-blocking adequacy backpressure exists" in preflight[
        "blocking_reasons"
    ]
    assert (run_dir / "live_executor" / "context_thread_index.json").exists()
    assert not (
        run_dir
        / "live_executor"
        / "role_outputs"
        / "task_final_writer"
        / "report.md"
    ).exists()
    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=runs_dir)
    assert report["status"] == "passed"
    assert report["failed_checks"] == []


def test_mesh_execute_live_runs_recursive_reentry_before_writer(tmp_path: Path):
    harness, run_dir, runs_dir, _dry_receipt = fresh_live_planned_mesh(tmp_path)
    live_receipt = runs_dir / "live_control.json"
    write_live_execution_control_receipt(live_receipt, "draco_mesh_fixture_001")
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "mesh-live-plan",
                "draco_mesh_fixture_001",
                "--run-control",
                str(live_receipt),
            ]
        )
        == 0
    )

    harness.mesh_execute_live(
        "draco_mesh_fixture_001",
        run_control=live_receipt,
        runs_dir=runs_dir,
        codex_runner=fake_live_codex_runner_with_recursive_reentry_closure,
    )

    summary = json.loads(
        (run_dir / "live_executor" / "execution_summary.json").read_text(
            encoding="utf-8"
        )
    )
    queue = json.loads(
        (run_dir / "backpressure" / "adequacy_backpressure_queue.json").read_text(
            encoding="utf-8"
        )
    )
    role_order = [role["task_id"] for role in summary["roles"]]
    assert summary["execution_status"] == "succeeded"
    assert summary["recursive_reentry_rounds_used"] == 1
    assert summary["role_count"] == 11
    dynamic_followup = next(
        plan
        for plan in summary["dynamic_role_launch_plans"]
        if plan["task_id"] == "task_reentry_followup_002"
    )
    packet_ref = dynamic_followup["dynamic_recursive_reentry"]["task_packet"]
    assert packet_ref == "reentry/adequacy_review_reentry_gap_001/reentry_task_packet.json"
    packet = json.loads((run_dir / packet_ref).read_text(encoding="utf-8"))
    assert packet["compiler_status"] == "ready"
    assert dynamic_followup["input_file_aliases"] == {
        packet_ref: "reentry_task_packet.json"
    }
    assert "branches/reentry_followup_002/reentry_result.json" in dynamic_followup[
        "output_paths"
    ]
    assert role_order.index("task_reentry_followup_002") < role_order.index(
        "task_reentry_synthesis_002"
    )
    assert role_order.index("task_reentry_synthesis_002") < role_order.index(
        "task_final_writer"
    )
    assert queue["queue_status"] == "clear"
    assert queue["writer_blocked"] is False
    assert (
        run_dir
        / "live_executor"
        / "role_outputs"
        / "task_reentry_followup_002"
        / "branches"
        / "reentry_followup_002"
        / "pointer.md"
    ).exists()
    assert (
        run_dir
        / "live_executor"
        / "role_outputs"
        / "task_final_writer"
        / "report.md"
    ).exists()
    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=runs_dir)
    assert report["status"] == "passed"
    assert report["failed_checks"] == []


def test_mesh_execute_live_runs_independent_branches_concurrently(tmp_path: Path):
    harness, run_dir, runs_dir, _dry_receipt = fresh_live_planned_mesh(tmp_path)
    live_receipt = runs_dir / "live_control.json"
    write_live_execution_control_receipt(live_receipt, "draco_mesh_fixture_001")
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "mesh-live-plan",
                "draco_mesh_fixture_001",
                "--run-control",
                str(live_receipt),
            ]
        )
        == 0
    )

    branch_tasks = {"task_deep_search", "task_data_analysis", "task_verification"}
    started_branch_tasks: set[str] = set()
    release_branches = threading.Event()
    lock = threading.Lock()

    def concurrent_branch_runner(
        *,
        role_plan: dict,
        prompt: str,
        workspace_path: Path,
        transcript_path: Path,
        last_message_path: Path,
        timeout_seconds: int,
    ) -> dict:
        task_id = role_plan["task_id"]
        if task_id in branch_tasks:
            with lock:
                started_branch_tasks.add(task_id)
                if started_branch_tasks == branch_tasks:
                    release_branches.set()
            if not release_branches.wait(timeout=2):
                raise AssertionError("independent branch roles were serialized")
            time.sleep(0.02)
        return fake_live_codex_runner(
            role_plan=role_plan,
            prompt=prompt,
            workspace_path=workspace_path,
            transcript_path=transcript_path,
            last_message_path=last_message_path,
            timeout_seconds=timeout_seconds,
        )

    harness.mesh_execute_live(
        "draco_mesh_fixture_001",
        run_control=live_receipt,
        runs_dir=runs_dir,
        codex_runner=concurrent_branch_runner,
    )

    summary = json.loads(
        (run_dir / "live_executor" / "execution_summary.json").read_text(
            encoding="utf-8"
        )
    )
    scheduler = summary["scheduler"]
    assert scheduler["scheduling_mode"] == "dependency_aware_parallel"
    assert scheduler["max_parallel_roles"] >= 3
    assert any(
        branch_tasks <= set(group["task_ids"])
        for group in scheduler["concurrency_groups"]
    )
    assert started_branch_tasks == branch_tasks
    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=runs_dir)
    assert report["status"] == "passed"
    assert report["failed_checks"] == []


def test_live_validation_fails_without_context_thread_index(tmp_path: Path):
    harness, run_dir, runs_dir, _dry_receipt = fresh_live_planned_mesh(tmp_path)
    live_receipt = runs_dir / "live_control.json"
    write_live_execution_control_receipt(live_receipt, "draco_mesh_fixture_001")
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "mesh-live-plan",
                "draco_mesh_fixture_001",
                "--run-control",
                str(live_receipt),
            ]
        )
        == 0
    )

    harness.mesh_execute_live(
        "draco_mesh_fixture_001",
        run_control=live_receipt,
        runs_dir=runs_dir,
        codex_runner=fake_live_codex_runner,
    )
    (run_dir / "live_executor" / "context_thread_index.json").unlink()

    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=runs_dir)
    assert report["status"] == "failed"
    assert "live_execution_custody_present" in report["failed_checks"]


def test_score_finalizes_scored_bundle_but_keeps_claims_blocked(tmp_path: Path):
    harness, run_dir, runs_dir = prepare_scored_live_mesh_inputs(tmp_path)
    scoring_receipt = runs_dir / "scoring_control.json"
    write_scoring_control_receipt(scoring_receipt, "draco_mesh_fixture_001")

    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "score",
            "draco_mesh_fixture_001",
            "--run-control",
            str(scoring_receipt),
        ]
    )

    assert result == 0
    manifest = json.loads((run_dir / "scorer_manifest.json").read_text(encoding="utf-8"))
    score = json.loads((run_dir / "benchmark_score.json").read_text(encoding="utf-8"))
    ledger = json.loads((run_dir / "evaluation_ledger.json").read_text(encoding="utf-8"))
    allowed = json.loads((run_dir / "allowed_claims.json").read_text(encoding="utf-8"))
    assert manifest["scorer_status"] == "executed"
    assert manifest["scorer_execution"]["executed_with_custody"] is True
    assert manifest["scorer_execution"]["receipt_ref"] == "scoring/run_control_receipt.json"
    assert score["mode"] == "scored_claims_blocked"
    assert score["score"] == pytest.approx(0.84)
    assert score["raw_score"] == pytest.approx(0.84)
    assert score["normalized_score"] == pytest.approx(0.84)
    assert score["claims_enabled"] is False
    assert ledger["result_status"] == "scored_claims_blocked"
    assert ledger["score_status"]["scorer_custody_present"] is True
    assert ledger["allowed_claim_impact"]["claim_gate_status"] == "blocked"
    assert (run_dir / "scoring" / "run_control_receipt.json").exists()
    assert any(
        "scorer-backed DRACO evaluation artifact" in claim["claim"]
        for claim in allowed["allowed_claims"]
    )
    assert "DRACO score" in allowed["blocked_claims"]
    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=runs_dir)
    assert report["status"] == "passed"
    assert report["failed_checks"] == []


def test_score_fails_closed_without_approved_scorer_manifest(tmp_path: Path):
    harness, run_dir, runs_dir, _dry_receipt = fresh_live_planned_mesh(tmp_path)
    live_receipt = runs_dir / "live_control.json"
    write_live_execution_control_receipt(live_receipt, "draco_mesh_fixture_001")
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "mesh-live-plan",
                "draco_mesh_fixture_001",
                "--run-control",
                str(live_receipt),
            ]
        )
        == 0
    )
    harness.mesh_execute_live(
        "draco_mesh_fixture_001",
        run_control=live_receipt,
        runs_dir=runs_dir,
        codex_runner=fake_live_codex_runner,
    )
    scoring_receipt = runs_dir / "scoring_control.json"
    write_scoring_control_receipt(scoring_receipt, "draco_mesh_fixture_001")

    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "score",
            "draco_mesh_fixture_001",
            "--run-control",
            str(scoring_receipt),
        ]
    )

    assert result == 2
    assert not (run_dir / "scoring").exists()


def test_score_fails_closed_without_evaluation_output(tmp_path: Path):
    harness, run_dir, runs_dir = prepare_scored_live_mesh_inputs(tmp_path)
    (run_dir / "draco_evaluation_output.json").unlink()
    scoring_receipt = runs_dir / "scoring_control.json"
    write_scoring_control_receipt(scoring_receipt, "draco_mesh_fixture_001")

    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "score",
            "draco_mesh_fixture_001",
            "--run-control",
            str(scoring_receipt),
        ]
    )

    assert result == 2
    assert not (run_dir / "scoring").exists()


def test_score_refuses_unapproved_scoring_receipt(tmp_path: Path):
    harness, run_dir, runs_dir = prepare_scored_live_mesh_inputs(tmp_path)
    scoring_receipt = runs_dir / "scoring_control.json"
    write_scoring_control_receipt(scoring_receipt, "draco_mesh_fixture_001")
    receipt = json.loads(scoring_receipt.read_text(encoding="utf-8"))
    receipt["approval"]["approved_for_execution"] = False
    scoring_receipt.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "score",
            "draco_mesh_fixture_001",
            "--run-control",
            str(scoring_receipt),
        ]
    )

    assert result == 2
    assert not (run_dir / "scoring").exists()


def test_validator_fails_scored_state_without_scorer_transcript(tmp_path: Path):
    harness, run_dir, runs_dir = prepare_scored_live_mesh_inputs(tmp_path)
    scoring_receipt = runs_dir / "scoring_control.json"
    write_scoring_control_receipt(scoring_receipt, "draco_mesh_fixture_001")
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "score",
                "draco_mesh_fixture_001",
                "--run-control",
                str(scoring_receipt),
            ]
        )
        == 0
    )

    (run_dir / "transcripts" / "scorer" / "judge_001.jsonl").unlink()
    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=runs_dir)

    assert report["status"] == "failed"
    assert "draco_scorer_manifest_valid" in report["failed_checks"]


def test_claim_review_keeps_scored_smoke_blocked(tmp_path: Path):
    harness, run_dir, runs_dir = prepare_scored_live_mesh_inputs(tmp_path)
    scoring_receipt = runs_dir / "scoring_control.json"
    write_scoring_control_receipt(scoring_receipt, "draco_mesh_fixture_001")
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "score",
                "draco_mesh_fixture_001",
                "--run-control",
                str(scoring_receipt),
            ]
        )
        == 0
    )

    result = harness.main(
        ["--runs-dir", str(runs_dir), "claim-review", "draco_mesh_fixture_001"]
    )

    assert result == 0
    review = json.loads((run_dir / "claim_review.json").read_text(encoding="utf-8"))
    allowed = json.loads((run_dir / "allowed_claims.json").read_text(encoding="utf-8"))
    assert review["decision"] == "blocked_single_smoke_review_required"
    assert review["may_widen_public_benchmark_claims"] is False
    assert allowed["claim_review"]["review_ref"] == "claim_review.json"
    assert allowed["claim_review"]["may_widen_public_benchmark_claims"] is False
    assert "DRACO score" in allowed["blocked_claims"]
    assert "official benchmark submission" in allowed["blocked_claims"]
    assert "scorer-backed evaluation" in allowed["blocked_claims"]
    assert any(
        "claim-review gate evaluated" in claim["claim"]
        for claim in allowed["allowed_claims"]
    )
    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=runs_dir)
    assert report["status"] == "passed"


def test_claim_review_fails_closed_on_pre_widened_score_claim(tmp_path: Path):
    harness, run_dir, runs_dir = prepare_scored_live_mesh_inputs(tmp_path)
    scoring_receipt = runs_dir / "scoring_control.json"
    write_scoring_control_receipt(scoring_receipt, "draco_mesh_fixture_001")
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "score",
                "draco_mesh_fixture_001",
                "--run-control",
                str(scoring_receipt),
            ]
        )
        == 0
    )
    add_draco_score_allowed_claim(run_dir / "allowed_claims.json")

    result = harness.main(
        ["--runs-dir", str(runs_dir), "claim-review", "draco_mesh_fixture_001"]
    )

    assert result == 2
    assert not (run_dir / "claim_review.json").exists()


def test_allowed_claims_require_full_claim_lock_set(tmp_path: Path):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    allowed_path = run_dir / "allowed_claims.json"
    allowed = json.loads(allowed_path.read_text(encoding="utf-8"))
    allowed["blocked_claims"] = [
        claim
        for claim in allowed["blocked_claims"]
        if claim != "official benchmark submission"
    ]
    allowed_path.write_text(
        json.dumps(allowed, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=runs_dir)

    assert report["status"] == "failed"
    assert "allowed_claims_scope_enforced" in report["failed_checks"]


def test_allowed_claims_cannot_reference_missing_claim_review(tmp_path: Path):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    allowed_path = run_dir / "allowed_claims.json"
    allowed = json.loads(allowed_path.read_text(encoding="utf-8"))
    allowed["claim_review"] = {
        "review_ref": "claim_review.json",
        "decision": "blocked_no_score",
        "may_widen_public_benchmark_claims": False,
    }
    allowed_path.write_text(
        json.dumps(allowed, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=runs_dir)

    assert report["status"] == "failed"
    assert "claim_review_artifact_valid" in report["failed_checks"]


def test_multi_case_smoke_runs_two_provider_off_cases(tmp_path: Path):
    harness = load_harness()
    runs_dir = TEST_RUNS_ROOT / f"{tmp_path.name}-multi"
    shutil.rmtree(runs_dir, ignore_errors=True)

    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "multi-case-smoke",
            "draco_suite_001",
            "--case-count",
            "2",
        ]
    )

    assert result == 0
    summary = json.loads(
        (runs_dir / "draco_suite_001" / "benchmark_suite_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["status"] == "passed"
    assert summary["case_count"] == 2
    row_indices = []
    ledger_case_ids = []
    for case in summary["cases"]:
        run_dir = runs_dir / case["run_id"]
        report = harness.validate_run(case["run_id"], runs_dir=runs_dir)
        manifest = json.loads((run_dir / "case_manifest.json").read_text(encoding="utf-8"))
        ledger = json.loads((run_dir / "evaluation_ledger.json").read_text(encoding="utf-8"))
        assert report["status"] == "passed"
        row_indices.extend(manifest["source"]["row_indices"])
        ledger_case_ids.append(ledger["case_id"])
        assert ledger["allowed_claim_impact"]["claim_gate_status"] == "blocked"
    assert row_indices == [0, 1]
    assert len(set(ledger_case_ids)) == 2


def test_multi_case_validate_rejects_mixed_case_schema(tmp_path: Path):
    harness = load_harness()
    runs_dir = TEST_RUNS_ROOT / f"{tmp_path.name}-multi"
    shutil.rmtree(runs_dir, ignore_errors=True)
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "multi-case-smoke",
                "draco_suite_001",
                "--case-count",
                "2",
            ]
        )
        == 0
    )
    manifest_path = runs_dir / "draco_suite_001_case_002" / "case_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = "codex-dr.case_manifest.v0"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = harness.main(
        ["--runs-dir", str(runs_dir), "multi-case-validate", "draco_suite_001"]
    )

    assert result == 1


def test_multi_case_from_manifest_uses_manifest_rows(tmp_path: Path):
    harness = load_harness()
    runs_dir = TEST_RUNS_ROOT / f"{tmp_path.name}-manifest-suite"
    shutil.rmtree(runs_dir, ignore_errors=True)
    manifest_path = tmp_path / "case_spec_manifest.json"
    write_case_spec_manifest(manifest_path)

    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "multi-case-from-manifest",
            "draco_manifest_suite_001",
            "--manifest",
            str(manifest_path),
        ]
    )

    assert result == 0
    summary = json.loads(
        (
            runs_dir
            / "draco_manifest_suite_001"
            / "benchmark_suite_summary.json"
        ).read_text(encoding="utf-8")
    )
    assert summary["status"] == "passed"
    assert summary["case_count"] == 2
    assert [case["case_id"] for case in summary["cases"]] == [
        "draco_manifest_case_a",
        "draco_manifest_case_b",
    ]
    assert [case["row_indices"] for case in summary["cases"]] == [[5], [8]]
    first_manifest = json.loads(
        (
            runs_dir
            / "draco_manifest_suite_001_case_001"
            / "case_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert first_manifest["generator_visible"]["question"] == "Manifest question A"
    assert first_manifest["source"]["row_indices"] == [5]
    assert first_manifest["sealed_scorer_only"]["reference_answer"]["visibility"] == (
        "scorer_only"
    )


def test_multi_case_from_manifest_fails_closed_on_generator_leak(tmp_path: Path):
    harness = load_harness()
    runs_dir = TEST_RUNS_ROOT / f"{tmp_path.name}-manifest-suite"
    shutil.rmtree(runs_dir, ignore_errors=True)
    manifest_path = tmp_path / "case_spec_manifest.json"
    write_case_spec_manifest(
        manifest_path,
        first_question="Reference answer: leaked into generator question",
    )

    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "multi-case-from-manifest",
            "draco_manifest_suite_001",
            "--manifest",
            str(manifest_path),
        ]
    )

    assert result == 2
    summary = json.loads(
        (
            runs_dir
            / "draco_manifest_suite_001"
            / "benchmark_suite_summary.json"
        ).read_text(encoding="utf-8")
    )
    assert summary["status"] == "failed"
    assert any("benchmark_case_manifest_sealed" in failure for failure in summary["failed_checks"])
    assert (
        runs_dir
        / "draco_manifest_suite_001_case_001"
        / "case_manifest.json"
    ).exists()


def test_deepresearch_bench_case_manifest_imports_sealed_cases(tmp_path: Path):
    harness = load_harness()
    runs_dir = TEST_RUNS_ROOT / f"{tmp_path.name}-drb-manifest-suite"
    shutil.rmtree(runs_dir, ignore_errors=True)
    query_jsonl = tmp_path / "query.jsonl"
    source_refresh = tmp_path / "deepresearch_bench_source_refresh.json"
    output_manifest = tmp_path / "deepresearch_bench_case_spec_manifest.json"
    write_deepresearch_bench_query_jsonl(query_jsonl)
    write_deepresearch_bench_refresh(source_refresh)

    result = harness.main(
        [
            "deepresearch-bench-case-manifest",
            "--query-jsonl",
            str(query_jsonl),
            "--source-refresh",
            str(source_refresh),
            "--output",
            str(output_manifest),
            "--row-indices",
            "0,1",
        ]
    )

    assert result == 0
    manifest = json.loads(output_manifest.read_text(encoding="utf-8"))
    assert manifest["benchmark_family"] == "DEEPRESEARCH_BENCH"
    assert manifest["source"]["dataset_id"] == "Ayanami0730/deep_research_bench"
    assert manifest["source"]["dataset_commit"] == (
        "eb155b23543399cf2114a403cb1d3c0b776a8a64"
    )
    assert manifest["cases"][0]["case_id"] == "deepresearch_bench_query_001"
    assert manifest["cases"][0]["generator_visible"]["question"].startswith("Research")
    assert manifest["cases"][0]["sealed_scorer_only"]["reference_answer"][
        "visibility"
    ] == "scorer_only"

    suite_result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "multi-case-from-manifest",
            "deepresearch_bench_manifest_suite_001",
            "--manifest",
            str(output_manifest),
        ]
    )

    assert suite_result == 0
    summary = json.loads(
        (
            runs_dir
            / "deepresearch_bench_manifest_suite_001"
            / "benchmark_suite_summary.json"
        ).read_text(encoding="utf-8")
    )
    assert summary["status"] == "passed"
    assert summary["benchmark_family"] == "DEEPRESEARCH_BENCH"
    first_manifest = json.loads(
        (
            runs_dir
            / "deepresearch_bench_manifest_suite_001_case_001"
            / "case_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert first_manifest["benchmark_family"] == "DEEPRESEARCH_BENCH"
    assert first_manifest["source"]["source_file"] == "data/prompt_data/query.jsonl"
    assert first_manifest["generator_visible"]["benchmark_prompt_id"] == 1


def test_deepresearch_bench_manifest_fails_closed_on_reference_leak(tmp_path: Path):
    harness = load_harness()
    runs_dir = TEST_RUNS_ROOT / f"{tmp_path.name}-drb-leak-suite"
    shutil.rmtree(runs_dir, ignore_errors=True)
    query_jsonl = tmp_path / "query.jsonl"
    source_refresh = tmp_path / "deepresearch_bench_source_refresh.json"
    output_manifest = tmp_path / "deepresearch_bench_case_spec_manifest.json"
    write_deepresearch_bench_query_jsonl(
        query_jsonl,
        first_prompt="Reference answer: leaked benchmark reference.",
    )
    write_deepresearch_bench_refresh(source_refresh)
    assert (
        harness.main(
            [
                "deepresearch-bench-case-manifest",
                "--query-jsonl",
                str(query_jsonl),
                "--source-refresh",
                str(source_refresh),
                "--output",
                str(output_manifest),
                "--limit",
                "2",
            ]
        )
        == 0
    )
    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "multi-case-from-manifest",
            "deepresearch_bench_manifest_suite_001",
            "--manifest",
            str(output_manifest),
        ]
    )

    assert result == 2
    summary = json.loads(
        (
            runs_dir
            / "deepresearch_bench_manifest_suite_001"
            / "benchmark_suite_summary.json"
        ).read_text(encoding="utf-8")
    )
    assert summary["status"] == "failed"
    assert any("benchmark_case_manifest_sealed" in failure for failure in summary["failed_checks"])


def test_deepresearch_bench_report_export_writes_raw_jsonl_and_custody(tmp_path: Path):
    harness = load_harness()
    runs_dir = TEST_RUNS_ROOT / f"{tmp_path.name}-drb-export-suite"
    shutil.rmtree(runs_dir, ignore_errors=True)
    query_jsonl = tmp_path / "query.jsonl"
    source_refresh = tmp_path / "deepresearch_bench_source_refresh.json"
    case_manifest = tmp_path / "deepresearch_bench_case_spec_manifest.json"
    report_export = tmp_path / "raw_generated_reports.jsonl"
    custody_export = tmp_path / "raw_generated_reports_custody.json"
    write_deepresearch_bench_query_jsonl(query_jsonl)
    write_deepresearch_bench_refresh(source_refresh)

    assert (
        harness.main(
            [
                "deepresearch-bench-case-manifest",
                "--query-jsonl",
                str(query_jsonl),
                "--source-refresh",
                str(source_refresh),
                "--output",
                str(case_manifest),
                "--limit",
                "2",
            ]
        )
        == 0
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "multi-case-from-manifest",
                "deepresearch_bench_export_suite",
                "--manifest",
                str(case_manifest),
            ]
        )
        == 0
    )
    live_report = (
        runs_dir
        / "deepresearch_bench_export_suite_case_001"
        / "live_executor"
        / "role_outputs"
        / "task_final_writer"
        / "report.md"
    )
    live_report.parent.mkdir(parents=True, exist_ok=True)
    live_report.write_text(
        "# Live DeepResearch Bench Report\n\nLive writer output.\n",
        encoding="utf-8",
    )

    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "deepresearch-bench-report-export",
            "deepresearch_bench_export_suite_case_001",
            "deepresearch_bench_export_suite_case_002",
            "--output",
            str(report_export),
            "--custody-output",
            str(custody_export),
        ]
    )

    assert result == 0
    rows = [
        json.loads(line)
        for line in report_export.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [set(row) for row in rows] == [
        {"id", "prompt", "article"},
        {"id", "prompt", "article"},
    ]
    assert rows[0]["id"] == 1
    assert rows[0]["prompt"] == "Research the industrial outlook for green ammonia."
    assert "Live DeepResearch Bench Report" in rows[0]["article"]

    custody = json.loads(custody_export.read_text(encoding="utf-8"))
    assert custody["schema_version"] == "codex-dr.deepresearch_bench_raw_report_export.v1"
    assert custody["case_count"] == 2
    assert custody["raw_report_jsonl_sha256"]
    assert custody["claim_boundary"]["may_claim_score"] is False
    assert custody["cases"][0]["benchmark_prompt_id"] == 1
    assert custody["cases"][0]["inputs"]["report"].endswith(
        "live_executor/role_outputs/task_final_writer/report.md"
    )
    assert custody["cases"][0]["inputs"]["claim_ledger"].endswith("claim_ledger.json")
    assert custody["cases"][0]["hashes"]["claim_ledger_sha256"]
    assert custody["cases"][0]["claim_boundary"]["allowed_claim_count"] == 1


def test_deepresearch_bench_report_export_fails_without_valid_custody(tmp_path: Path):
    harness = load_harness()
    runs_dir = TEST_RUNS_ROOT / f"{tmp_path.name}-drb-export-invalid"
    shutil.rmtree(runs_dir, ignore_errors=True)
    query_jsonl = tmp_path / "query.jsonl"
    source_refresh = tmp_path / "deepresearch_bench_source_refresh.json"
    case_manifest = tmp_path / "deepresearch_bench_case_spec_manifest.json"
    report_export = tmp_path / "raw_generated_reports.jsonl"
    write_deepresearch_bench_query_jsonl(query_jsonl)
    write_deepresearch_bench_refresh(source_refresh)
    assert (
        harness.main(
            [
                "deepresearch-bench-case-manifest",
                "--query-jsonl",
                str(query_jsonl),
                "--source-refresh",
                str(source_refresh),
                "--output",
                str(case_manifest),
                "--limit",
                "2",
            ]
        )
        == 0
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "multi-case-from-manifest",
                "deepresearch_bench_export_suite",
                "--manifest",
                str(case_manifest),
            ]
        )
        == 0
    )
    (runs_dir / "deepresearch_bench_export_suite_case_001" / "allowed_claims.json").unlink()

    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "deepresearch-bench-report-export",
            "deepresearch_bench_export_suite_case_001",
            "--output",
            str(report_export),
        ]
    )

    assert result == 2
    assert not report_export.exists()


def test_deepresearch_bench_race_bridge_blocks_without_provider_key(tmp_path: Path):
    harness = load_harness()
    runs_dir = TEST_RUNS_ROOT / f"{tmp_path.name}-drb-race-bridge"
    shutil.rmtree(runs_dir, ignore_errors=True)
    official_repo = tmp_path / "official_deepresearch_bench"
    bridge_dir = tmp_path / "race_bridge"
    query_jsonl = tmp_path / "query.jsonl"
    source_refresh = tmp_path / "deepresearch_bench_source_refresh.json"
    case_manifest = tmp_path / "deepresearch_bench_case_spec_manifest.json"
    report_export = tmp_path / "raw_generated_reports.jsonl"
    write_deepresearch_bench_official_repo_fixture(official_repo)
    write_deepresearch_bench_query_jsonl(query_jsonl)
    write_deepresearch_bench_refresh(source_refresh)

    assert (
        harness.main(
            [
                "deepresearch-bench-case-manifest",
                "--query-jsonl",
                str(query_jsonl),
                "--source-refresh",
                str(source_refresh),
                "--output",
                str(case_manifest),
                "--limit",
                "2",
            ]
        )
        == 0
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "multi-case-from-manifest",
                "deepresearch_bench_race_suite",
                "--manifest",
                str(case_manifest),
            ]
        )
        == 0
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-report-export",
                "deepresearch_bench_race_suite_case_001",
                "deepresearch_bench_race_suite_case_002",
                "--output",
                str(report_export),
            ]
        )
        == 0
    )

    result = harness.main(
        [
            "deepresearch-bench-race-bridge",
            "--raw-reports",
            str(report_export),
            "--source-refresh",
            str(source_refresh),
            "--official-repo",
            str(official_repo),
            "--output-dir",
            str(bridge_dir),
            "--model-name",
            "codex-dr-smoke",
            "--limit",
            "2",
        ]
    )

    assert result == 0
    manifest = json.loads((bridge_dir / "scorer_manifest.json").read_text(encoding="utf-8"))
    evaluation = json.loads(
        (bridge_dir / "race_evaluation_output.json").read_text(encoding="utf-8")
    )
    receipt = json.loads((bridge_dir / "race_bridge_receipt.json").read_text(encoding="utf-8"))
    copied_raw = bridge_dir / "official_inputs" / "raw_data" / "codex-dr-smoke.jsonl"
    assert copied_raw.exists()
    assert manifest["schema_version"] == (
        "codex-dr.deepresearch_bench_race_scorer_manifest.v1"
    )
    assert manifest["benchmark_family"] == "DEEPRESEARCH_BENCH"
    assert manifest["scorer_status"] == "blocked"
    assert manifest["execution_allowed"] is False
    assert "GEMINI_API_KEY" in manifest["provider_requirements"]["missing_requirements"]
    assert "explicit --allow-provider-run" in manifest["provider_requirements"][
        "missing_requirements"
    ]
    assert "deepresearch_bench_race.py" in manifest["official_scorer"]["command_plan"]
    assert manifest["raw_reports"]["case_count"] == 2
    assert evaluation["status"] == "blocked"
    assert evaluation["score"] is None
    assert evaluation["claim_boundary"]["may_claim_score"] is False
    assert receipt["status"] == "blocked"


def test_deepresearch_bench_claim_review_records_blocked_score_boundary(tmp_path: Path):
    harness = load_harness()
    runs_dir = TEST_RUNS_ROOT / f"{tmp_path.name}-drb-claim-review"
    shutil.rmtree(runs_dir, ignore_errors=True)
    official_repo = tmp_path / "official_deepresearch_bench"
    bridge_dir = tmp_path / "race_bridge"
    query_jsonl = tmp_path / "query.jsonl"
    source_refresh = tmp_path / "deepresearch_bench_source_refresh.json"
    case_manifest = tmp_path / "deepresearch_bench_case_spec_manifest.json"
    report_export = tmp_path / "raw_generated_reports.jsonl"
    run_id = "deepresearch_bench_claim_suite_case_001"
    live_receipt = runs_dir / "live_control.json"
    write_deepresearch_bench_official_repo_fixture(official_repo)
    write_deepresearch_bench_query_jsonl(query_jsonl)
    write_deepresearch_bench_refresh(source_refresh)

    assert (
        harness.main(
            [
                "deepresearch-bench-case-manifest",
                "--query-jsonl",
                str(query_jsonl),
                "--source-refresh",
                str(source_refresh),
                "--output",
                str(case_manifest),
                "--limit",
                "2",
            ]
        )
        == 0
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "multi-case-from-manifest",
                "deepresearch_bench_claim_suite",
                "--manifest",
                str(case_manifest),
            ]
        )
        == 0
    )
    write_live_execution_control_receipt(live_receipt, run_id)
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "mesh-live-plan",
                run_id,
                "--run-control",
                str(live_receipt),
            ]
        )
        == 0
    )
    harness.mesh_execute_live(
        run_id,
        run_control=live_receipt,
        runs_dir=runs_dir,
        codex_runner=fake_live_codex_runner,
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-report-export",
                run_id,
                "--output",
                str(report_export),
            ]
        )
        == 0
    )
    assert (
        harness.main(
            [
                "deepresearch-bench-race-bridge",
                "--raw-reports",
                str(report_export),
                "--source-refresh",
                str(source_refresh),
                "--official-repo",
                str(official_repo),
                "--output-dir",
                str(bridge_dir),
                "--model-name",
                "codex-dr-claim-review",
                "--limit",
                "1",
            ]
        )
        == 0
    )

    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "deepresearch-bench-claim-review",
            run_id,
            "--race-bridge-receipt",
            str(bridge_dir / "race_bridge_receipt.json"),
            "--source-refresh",
            str(source_refresh),
        ]
    )

    assert result == 0
    run_dir = runs_dir / run_id
    validation = harness.validate_run(run_id, runs_dir=runs_dir)
    score = json.loads((run_dir / "benchmark_score.json").read_text(encoding="utf-8"))
    ledger = json.loads((run_dir / "evaluation_ledger.json").read_text(encoding="utf-8"))
    review = json.loads((run_dir / "claim_review.json").read_text(encoding="utf-8"))
    allowed = json.loads((run_dir / "allowed_claims.json").read_text(encoding="utf-8"))
    artefact_manifest = json.loads(
        (run_dir / "artefact_manifest.json").read_text(encoding="utf-8")
    )

    assert validation["status"] == "passed"
    assert score["benchmark_family"] == "DEEPRESEARCH_BENCH"
    assert score["mode"] == "blocked_no_score"
    assert score["score"] is None
    assert score["claims_enabled"] is False
    assert ledger["current_grep_target"]["overall_score"] == 56.23
    assert ledger["allowed_claim_impact"]["may_widen_claims"] is False
    assert review["decision"] == "blocked_no_score"
    assert review["may_widen_public_benchmark_claims"] is False
    assert "DeepResearch Bench score" in allowed["blocked_claims"]
    assert {
        "scoring/deepresearch_bench_race/race_bridge_receipt.json",
        "scoring/deepresearch_bench_race/race_scorer_manifest.original.json",
        "scoring/deepresearch_bench_race/race_evaluation_output.json",
    } <= {
        item["path"]
        for item in artefact_manifest["artifacts"]
        if item["produced_by_event"] == "evt_drb_claim_review_0001_written"
    }


def test_deepresearch_bench_improvement_compile_writes_non_promoted_candidates(
    tmp_path: Path,
):
    harness, run_dir, runs_dir, run_id = prepare_deepresearch_bench_claim_review_run(
        tmp_path, "drb-improve"
    )

    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "deepresearch-bench-improvement-compile",
            run_id,
        ]
    )

    assert result == 0
    validation = harness.validate_run(run_id, runs_dir=runs_dir)
    candidates = json.loads(
        (run_dir / "self_improvement" / "improvement_candidates.json").read_text(
            encoding="utf-8"
        )
    )
    proposal = json.loads(
        (run_dir / "self_improvement" / "improvement_proposal.json").read_text(
            encoding="utf-8"
        )
    )

    assert validation["status"] == "passed"
    assert candidates["schema_version"] == (
        "codex-dr.deepresearch_bench_improvement_candidates.v1"
    )
    assert candidates["candidate_count"] == 5
    assert {
        candidate["target_surface_type"] for candidate in candidates["candidates"]
    } == {"evaluator", "prompt", "file_context", "skill", "scheduler"}
    for candidate in candidates["candidates"]:
        assert candidate["source_failure_refs"]
        assert candidate["target_surface"]
        assert candidate["expected_effect"]
        assert candidate["replay_fixtures"]
        assert candidate["promotion_gate"]["requires_regression"] is True
        assert candidate["promotion_status"] == "proposed_not_promoted"
        assert candidate["auto_promotion_allowed"] is False
        assert candidate["automatic_skill_mutation_allowed"] is False
        assert candidate["claim_impact"] == "no claim widening"
    assert proposal["suggested_patch"]["candidate_file"] == (
        "self_improvement/improvement_candidates.json"
    )
    assert proposal["promotion_status"] == "proposed_not_promoted"


def test_deepresearch_bench_improvement_candidates_need_source_failure_refs(
    tmp_path: Path,
):
    harness, run_dir, runs_dir, run_id = prepare_deepresearch_bench_claim_review_run(
        tmp_path, "drb-improve-red"
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-improvement-compile",
                run_id,
            ]
        )
        == 0
    )
    candidates_path = run_dir / "self_improvement" / "improvement_candidates.json"
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    candidates["candidates"][0]["source_failure_refs"] = []
    candidates_path.write_text(
        json.dumps(candidates, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    validation = harness.validate_run(run_id, runs_dir=runs_dir)

    assert validation["status"] == "failed"
    assert "self_improvement_replay_gate_enforced" in validation["failed_checks"]


def test_deepresearch_bench_improvement_gate_writes_isolated_receipts(
    tmp_path: Path,
):
    harness, run_dir, runs_dir, run_id = prepare_deepresearch_bench_claim_review_run(
        tmp_path, "drb-gate"
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-improvement-compile",
                run_id,
            ]
        )
        == 0
    )

    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "deepresearch-bench-improvement-gate",
            run_id,
        ]
    )

    assert result == 0
    validation = harness.validate_run(run_id, runs_dir=runs_dir)
    gate_results = json.loads(
        (run_dir / "self_improvement" / "candidate_gate_results.json").read_text(
            encoding="utf-8"
        )
    )

    assert validation["status"] == "passed"
    assert gate_results["candidate_count"] == 5
    assert gate_results["all_candidates_gated"] is True
    assert gate_results["live_surface_changed"] is False
    for result_item in gate_results["results"]:
        assert result_item["promotion_status"] == "not_promoted"
        assert result_item["live_surface_changed"] is False
        assert result_item["checks_passed"] is True
        assert (run_dir / result_item["patch_preview"]).exists()
        assert (run_dir / result_item["replay_result"]).exists()
        receipt = json.loads(
            (run_dir / result_item["promotion_receipt"]).read_text(encoding="utf-8")
        )
        assert receipt["promotion_status"] == "not_promoted"
        assert receipt["live_surface_changed"] is False


def test_deepresearch_bench_improvement_gate_rejects_unreceipted_live_mutation(
    tmp_path: Path,
):
    harness, run_dir, runs_dir, run_id = prepare_deepresearch_bench_claim_review_run(
        tmp_path, "drb-gate-red"
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-improvement-compile",
                run_id,
            ]
        )
        == 0
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-improvement-gate",
                run_id,
            ]
        )
        == 0
    )
    regression_path = run_dir / "self_improvement" / "regression_gate.json"
    regression = json.loads(regression_path.read_text(encoding="utf-8"))
    regression["live_surface_mutations"] = [
        {
            "candidate_id": "cand_drb_numeric_appendix_prompt_001",
            "target_surface": "sandbox/codex-dr/harness-specs/live_role_prompt_pack.md",
            "live_surface_changed": True,
        }
    ]
    regression_path.write_text(
        json.dumps(regression, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    validation = harness.validate_run(run_id, runs_dir=runs_dir)

    assert validation["status"] == "failed"
    assert "self_improvement_replay_gate_enforced" in validation["failed_checks"]


def test_deepresearch_bench_subset_pressure_writes_aggregate_blocked_suite(
    tmp_path: Path,
):
    harness, suite_dir, _runs_dir, _suite_id = prepare_deepresearch_bench_subset_pressure(
        tmp_path, "drb-subset"
    )

    summary = json.loads(
        (suite_dir / "deepresearch_bench_subset_pressure_summary.json").read_text(
            encoding="utf-8"
        )
    )
    validation = json.loads(
        (suite_dir / "deepresearch_bench_subset_pressure_validation.json").read_text(
            encoding="utf-8"
        )
    )
    claim_review = json.loads(
        (suite_dir / "benchmark_suite_claim_review.json").read_text(encoding="utf-8")
    )
    improvement_inputs = json.loads(
        (suite_dir / "subset_improvement_inputs.json").read_text(encoding="utf-8")
    )

    assert validation["status"] == "passed"
    assert summary["case_count"] == 2
    assert summary["raw_report_export"]["case_count"] == 2
    assert summary["race_bridge"]["status"] == "blocked"
    assert summary["aggregate_result"]["score"] is None
    assert summary["aggregate_result"]["may_claim_parity"] is False
    assert summary["failure_taxonomy"][0]["failure_class"] == "scorer_blocked"
    assert claim_review["decision"] == "blocked_no_score"
    assert claim_review["may_widen_public_benchmark_claims"] is False
    assert improvement_inputs["candidate_inputs"]
    assert improvement_inputs["claim_impact"] == "no claim widening"
    assert harness.validate_deepresearch_bench_subset_pressure(
        _suite_id, runs_dir=_runs_dir
    )["status"] == "passed"


def test_deepresearch_bench_existing_subset_pressure_uses_existing_suite(
    tmp_path: Path,
):
    harness, suite_dir, runs_dir, suite_id = prepare_deepresearch_bench_subset_pressure(
        tmp_path, "drb-existing-subset"
    )
    source_refresh = tmp_path / "deepresearch_bench_source_refresh_drb-existing-subset.json"
    official_repo = tmp_path / "official_deepresearch_bench_drb-existing-subset"

    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-existing-subset-pressure",
                suite_id,
                "--source-refresh",
                str(source_refresh),
                "--official-repo",
                str(official_repo),
                "--limit",
                "2",
            ]
        )
        == 0
    )

    validation = json.loads(
        (suite_dir / "deepresearch_bench_subset_pressure_validation.json").read_text(
            encoding="utf-8"
        )
    )
    summary = json.loads(
        (suite_dir / "deepresearch_bench_subset_pressure_summary.json").read_text(
            encoding="utf-8"
        )
    )

    assert validation["status"] == "passed"
    assert summary["case_count"] == 2
    assert summary["raw_report_export"]["case_count"] == 2


def test_deepresearch_bench_existing_subset_pressure_can_record_invalid_cases(
    tmp_path: Path,
):
    harness, suite_dir, runs_dir, suite_id = prepare_deepresearch_bench_subset_pressure(
        tmp_path, "drb-existing-subset-invalid"
    )
    source_refresh = (
        tmp_path / "deepresearch_bench_source_refresh_drb-existing-subset-invalid.json"
    )
    official_repo = tmp_path / "official_deepresearch_bench_drb-existing-subset-invalid"
    suite_manifest = json.loads(
        (suite_dir / "benchmark_suite_manifest.json").read_text(encoding="utf-8")
    )
    first_case_id = suite_manifest["cases"][0]["run_id"]
    evidence_path = runs_dir / first_case_id / "branches" / "reentry_followup" / "evidence.jsonl"
    evidence_rows = [
        json.loads(line)
        for line in evidence_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    evidence_rows[0]["admission_status"] = "unknown_status_for_pressure"
    evidence_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in evidence_rows) + "\n",
        encoding="utf-8",
    )

    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-existing-subset-pressure",
                suite_id,
                "--source-refresh",
                str(source_refresh),
                "--official-repo",
                str(official_repo),
                "--limit",
                "2",
                "--allow-invalid-reports",
            ]
        )
        == 0
    )

    summary = json.loads(
        (suite_dir / "deepresearch_bench_subset_pressure_summary.json").read_text(
            encoding="utf-8"
        )
    )
    custody = json.loads(
        (suite_dir / "deepresearch_bench_subset_raw_reports_custody.json").read_text(
            encoding="utf-8"
        )
    )

    assert summary["raw_report_export"]["case_count"] == 2
    assert summary["raw_report_export"]["allow_invalid_reports"] is True
    assert any(
        failure["failure_class"] == "suite_validation_failed"
        for failure in summary["failure_taxonomy"]
    )
    assert custody["contains_validation_failures"] is True
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-subset-improvement-compile",
                suite_id,
            ]
        )
        == 0
    )
    improvement_validation = json.loads(
        (suite_dir / "subset_improvement" / "subset_improvement_validation.json").read_text(
            encoding="utf-8"
        )
    )
    next_plan = json.loads(
        (suite_dir / "subset_improvement" / "next_flywheel_plan.json").read_text(
            encoding="utf-8"
        )
    )

    assert improvement_validation["status"] == "passed"
    assert (
        improvement_validation["selected_candidate_id"]
        == "cand_drb_reentry_admission_status_prompt_001"
    )
    assert next_plan["claim_boundary"]["may_claim_grep_parity"] is False


def test_deepresearch_bench_pre_scorer_quality_gate_passes_clean_subset(
    tmp_path: Path,
):
    harness, suite_dir, runs_dir, suite_id = prepare_deepresearch_bench_subset_pressure(
        tmp_path, "drb-pre-scorer-clean"
    )
    output_dir = tmp_path / "pre_scorer_quality_gate_clean"

    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-pre-scorer-quality-gate",
                suite_id,
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    gate = json.loads(
        (output_dir / "pre_scorer_quality_gate.json").read_text(encoding="utf-8")
    )

    assert gate["suite_id"] == suite_id
    assert gate["status"] == "passed"
    assert gate["case_count"] == 2
    assert gate["scorer_spend_decision"]["official_scorer_should_run_for_quality_smoke"]
    assert gate["claim_boundary"]["may_claim_grep_parity"] is False
    assert (output_dir / "pre_scorer_quality_gate.md").exists()
    assert suite_dir.exists()


def test_deepresearch_bench_pre_scorer_quality_gate_blocks_unsatisfied_adequacy(
    tmp_path: Path,
):
    harness, suite_dir, runs_dir, suite_id = prepare_deepresearch_bench_subset_pressure(
        tmp_path, "drb-pre-scorer-blocked"
    )
    suite_manifest = json.loads(
        (suite_dir / "benchmark_suite_manifest.json").read_text(encoding="utf-8")
    )
    first_case_id = suite_manifest["cases"][0]["run_id"]
    adequacy_path = runs_dir / first_case_id / "adequacy_assessments.jsonl"
    rows = [
        json.loads(line)
        for line in adequacy_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows.append(
        {
            "criterion": "adequacy_review_reentry",
            "status": "not_satisfied",
            "follow_up_task": "Run a targeted comparison re-entry before scorer spend.",
        }
    )
    adequacy_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "pre_scorer_quality_gate_blocked"

    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-pre-scorer-quality-gate",
                suite_id,
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    gate = json.loads(
        (output_dir / "pre_scorer_quality_gate.json").read_text(encoding="utf-8")
    )

    assert gate["status"] == "blocked"
    assert (
        gate["selected_candidate"]["candidate_id"]
        == "cand_drb_recursive_reentry_from_adequacy_status_001"
    )
    assert gate["scorer_spend_decision"][
        "official_scorer_should_run_for_quality_smoke"
    ] is False
    assert any(
        failure["failure_class"] == "answer_adequacy_pre_scorer_risk"
        for failure in gate["failure_taxonomy"]
    )
    blocked_case = next(
        case for case in gate["cases"] if case["run_id"] == first_case_id
    )
    assert blocked_case["status"] == "blocked"
    assert any(
        issue["issue_id"] == "unresolved_adequacy_status"
        for issue in blocked_case["issues"]
    )
    assert gate["claim_boundary"]["may_claim_deepresearch_bench_score"] is False


def test_deepresearch_bench_subset_candidate_overlay_targets_reentry_schema(
    tmp_path: Path,
):
    harness, suite_dir, runs_dir, suite_id = prepare_deepresearch_bench_subset_pressure(
        tmp_path, "drb-subset-overlay"
    )
    source_refresh = tmp_path / "deepresearch_bench_source_refresh_drb-subset-overlay.json"
    official_repo = tmp_path / "official_deepresearch_bench_drb-subset-overlay"
    suite_manifest = json.loads(
        (suite_dir / "benchmark_suite_manifest.json").read_text(encoding="utf-8")
    )
    first_case_id = suite_manifest["cases"][0]["run_id"]
    evidence_path = runs_dir / first_case_id / "branches" / "reentry_followup" / "evidence.jsonl"
    evidence_rows = [
        json.loads(line)
        for line in evidence_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    evidence_rows[0].pop("admission_status", None)
    evidence_rows[0]["status"] = "derived_from_admitted_inputs"
    evidence_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in evidence_rows) + "\n",
        encoding="utf-8",
    )

    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-existing-subset-pressure",
                suite_id,
                "--source-refresh",
                str(source_refresh),
                "--official-repo",
                str(official_repo),
                "--limit",
                "2",
                "--allow-invalid-reports",
            ]
        )
        == 0
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-subset-improvement-compile",
                suite_id,
            ]
        )
        == 0
    )

    base_overlay_dir = tmp_path / "numeric_base_overlay"
    base_overlay_dir.mkdir(parents=True, exist_ok=True)
    base_overlay_path = base_overlay_dir / "prompt_overlay.json"
    base_overlay_path.write_text(
        json.dumps(
            {
                "schema_version": "codex-dr.deepresearch_bench_prompt_overlay.v1",
                "overlay_id": "drb_numeric_base_overlay_fixture",
                "candidate_id": "cand_drb_numeric_appendix_prompt_001",
                "candidate_chain": ["cand_drb_numeric_appendix_prompt_001"],
                "parent_overlays": [],
                "source_flywheel_plan": "fixture_flywheel_plan.json",
                "source_plan_sha256": "0" * 64,
                "target_surface_type": "prompt",
                "target_surface": "sandbox/codex-dr/harness-specs/live_role_prompt_pack.md",
                "source_failure_refs": [{"failure_id": "fixture_numeric_gap"}],
                "replay_fixtures": ["fixture_drb_numeric_appendix_gap_001"],
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
                        "instructions": [
                            "Add a `## Numeric Claim Support Appendix` section."
                        ],
                    }
                ],
                "expected_effect": "fixture numeric appendix retained",
                "live_surface_changed": False,
                "base_surface_mutation_allowed": False,
                "claim_boundary": {"may_widen_claims": False, "blocked_claims": []},
                "produced_at": "2026-04-22T00:00:00Z",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    assert harness.validate_prompt_overlay(base_overlay_path)["status"] == "passed"

    overlay_dir = tmp_path / "reentry_schema_overlay"
    assert (
        harness.main(
            [
                "deepresearch-bench-apply-candidate-overlay",
                "drb_reentry_schema_overlay_fixture",
                "--flywheel-plan",
                str(suite_dir / "subset_improvement" / "next_flywheel_plan.json"),
                "--output-dir",
                str(overlay_dir),
                "--base-prompt-overlay",
                str(base_overlay_path),
            ]
        )
        == 0
    )
    overlay = json.loads((overlay_dir / "prompt_overlay.json").read_text(encoding="utf-8"))
    validation = json.loads(
        (overlay_dir / "prompt_overlay_validation.json").read_text(encoding="utf-8")
    )

    assert validation["status"] == "passed"
    assert overlay["candidate_id"] == "cand_drb_reentry_admission_status_prompt_001"
    assert overlay["candidate_chain"] == [
        "cand_drb_numeric_appendix_prompt_001",
        "cand_drb_reentry_admission_status_prompt_001",
    ]
    assert "task_reentry_followup" in overlay["applies_to_task_ids"]
    assert "admission_status" in (overlay_dir / "prompt_overlay.md").read_text(
        encoding="utf-8"
    )

    mesh_harness, run_dir, mesh_runs_dir = fresh_mesh_run(tmp_path)
    receipt_path = mesh_runs_dir / "dry_run_control.json"
    write_dry_run_control_receipt(receipt_path, "draco_mesh_fixture_001")
    assert (
        mesh_harness.main(
            [
                "--runs-dir",
                str(mesh_runs_dir),
                "mesh-live-plan",
                "draco_mesh_fixture_001",
                "--run-control",
                str(receipt_path),
                "--prompt-overlay",
                str(overlay_dir / "prompt_overlay.json"),
            ]
        )
        == 0
    )
    reentry_prompt = (
        run_dir / "live_adapter" / "prompts" / "task_reentry_followup.md"
    ).read_text(encoding="utf-8")
    synthesis_prompt = (
        run_dir / "live_adapter" / "prompts" / "task_pointer_first_synthesis.md"
    ).read_text(encoding="utf-8")
    assert "## Candidate Prompt Overlay" in reentry_prompt
    assert "status` as a substitute" in reentry_prompt
    assert "Numeric Claim Support Appendix" not in reentry_prompt
    assert "Numeric Claim Support Appendix" in synthesis_prompt
    assert "status` as a substitute" not in synthesis_prompt


def test_deepresearch_bench_subset_candidate_selection_uses_adequacy_backpressure():
    harness = load_harness()
    candidates = harness.subset_improvement_candidate_payloads(
        [
            {
                "source_kind": "subset.failure_taxonomy",
                "failure_id": "suite_validation_failed",
                "failure_class": "suite_validation_failed",
                "severity": "blocking",
                "summary": (
                    "case: validation failed "
                    "['adequacy_backpressure_queue_present']"
                ),
                "affected_cases": ["case_001"],
            },
            {
                "source_kind": "subset.failure_taxonomy",
                "failure_id": "scorer_blocked",
                "failure_class": "scorer_blocked",
                "severity": "blocking",
                "summary": "Official RACE scorer is blocked.",
                "affected_cases": ["case_001"],
            },
        ]
    )
    gate_results = [
        {
            "candidate_id": candidate["candidate_id"],
            "checks_passed": bool(candidate["source_failure_refs"]),
        }
        for candidate in candidates
    ]
    selected = harness.select_next_subset_candidate(candidates, gate_results)
    action = harness.subset_next_action_for_candidate(selected)

    assert selected["candidate_id"] == "cand_drb_adequacy_backpressure_queue_001"
    assert action["status"] == "ready_for_backpressure_queue_repair"
    assert (
        action["next_action"]["action_id"]
        == "apply_adequacy_backpressure_queue_repair"
    )


def test_deepresearch_bench_subset_pressure_detects_hidden_missing_report_row(
    tmp_path: Path,
):
    harness, suite_dir, runs_dir, suite_id = prepare_deepresearch_bench_subset_pressure(
        tmp_path, "drb-subset-red"
    )
    summary = json.loads(
        (suite_dir / "deepresearch_bench_subset_pressure_summary.json").read_text(
            encoding="utf-8"
        )
    )
    raw_path = Path(summary["raw_report_export"]["path"])
    rows = [line for line in raw_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    raw_path.write_text(rows[0] + "\n", encoding="utf-8")

    validation = harness.validate_deepresearch_bench_subset_pressure(
        suite_id, runs_dir=runs_dir
    )

    assert validation["status"] == "failed"
    assert "raw report export row count does not match selected cases" in validation[
        "failed_checks"
    ]


def test_deepresearch_bench_full_run_package_blocks_parity_without_score(
    tmp_path: Path,
):
    harness, suite_dir, _runs_dir, _suite_id = prepare_deepresearch_bench_subset_pressure(
        tmp_path, "drb-full"
    )
    official_repo = tmp_path / "official_deepresearch_bench_full"
    source_refresh = tmp_path / "deepresearch_bench_source_refresh_full.json"
    query_jsonl = tmp_path / "query_100.jsonl"
    output_dir = tmp_path / "full_run_package"
    write_deepresearch_bench_official_repo_fixture(official_repo)
    write_deepresearch_bench_refresh(source_refresh)
    write_deepresearch_bench_query_jsonl(query_jsonl, row_count=100)

    result = harness.main(
        [
            "deepresearch-bench-full-run-package",
            "deepresearch_bench_full_package_fixture",
            "--query-jsonl",
            str(query_jsonl),
            "--source-refresh",
            str(source_refresh),
            "--subset-summary",
            str(suite_dir / "deepresearch_bench_subset_pressure_summary.json"),
            "--official-repo",
            str(official_repo),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert result == 0
    package = json.loads((output_dir / "full_run_package.json").read_text(encoding="utf-8"))
    comparison = json.loads(
        (output_dir / "grep_comparison_gate.json").read_text(encoding="utf-8")
    )
    validation = json.loads(
        (output_dir / "full_run_package_validation.json").read_text(encoding="utf-8")
    )

    assert validation["status"] == "passed"
    assert package["full_case_contract"]["observed_query_count"] == 100
    assert package["full_case_contract"]["all_cases_present"] is True
    assert package["current_grep_target"]["overall_score"] == 56.23
    assert package["status"] == "blocked_before_full_execution"
    assert package["claim_boundary"]["may_claim_grep_parity"] is False
    assert comparison["decision"] == "blocked_full_run_not_scored"
    assert comparison["may_claim_parity"] is False


def test_deepresearch_bench_score_control_packet_blocks_execution_claims(
    tmp_path: Path,
):
    harness, suite_dir, runs_dir, suite_id = prepare_deepresearch_bench_subset_pressure(
        tmp_path, "drb-score-control"
    )
    package_dir = write_deepresearch_bench_full_package_fixture(
        tmp_path, harness, suite_dir, "drb-score-control"
    )
    overlay_dir = tmp_path / "score_control_overlay"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    overlay_path = overlay_dir / "prompt_overlay.json"
    overlay_path.write_text(
        json.dumps(
            {
                "schema_version": "codex-dr.deepresearch_bench_prompt_overlay.v1",
                "overlay_id": "drb_score_control_overlay_fixture",
                "candidate_id": "cand_drb_numeric_appendix_prompt_001",
                "candidate_chain": ["cand_drb_numeric_appendix_prompt_001"],
                "parent_overlays": [],
                "source_flywheel_plan": "fixture_flywheel_plan.json",
                "source_plan_sha256": "0" * 64,
                "target_surface_type": "prompt",
                "target_surface": "sandbox/codex-dr/harness-specs/live_role_prompt_pack.md",
                "source_failure_refs": [{"failure_id": "fixture_numeric_gap"}],
                "replay_fixtures": ["fixture_drb_numeric_appendix_gap_001"],
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
                        "instructions": [
                            "Add a `## Numeric Claim Support Appendix` section."
                        ],
                    }
                ],
                "expected_effect": "fixture numeric appendix retained",
                "live_surface_changed": False,
                "base_surface_mutation_allowed": False,
                "claim_boundary": {"may_widen_claims": False, "blocked_claims": []},
                "produced_at": "2026-04-22T00:00:00Z",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "score_control_packet"

    assert (
        harness.main(
            [
                "deepresearch-bench-score-control-packet",
                "deepresearch_bench_score_control_fixture",
                "--full-run-package",
                str(package_dir / "full_run_package.json"),
                "--prompt-overlay",
                str(overlay_path),
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )
    packet = json.loads((output_dir / "score_control_packet.json").read_text(encoding="utf-8"))
    validation = json.loads(
        (output_dir / "score_control_packet_validation.json").read_text(encoding="utf-8")
    )

    assert validation["status"] == "passed"
    assert packet["provider_authority"]["status"] == "blocked"
    assert packet["budget"]["status"] == "not_approved"
    assert packet["official_repo"]["commit"]
    assert packet["dataset_revision"]["revision_sha"]
    assert packet["claim_review"]["may_widen_public_benchmark_claims"] is False
    assert packet["claim_boundary"]["may_claim_grep_parity"] is False

    controls_dir = tmp_path / "live_run_controls"
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-live-run-controls",
                suite_id,
                "--prompt-overlay",
                str(overlay_path),
                "--output-dir",
                str(controls_dir),
                "--bead-id",
                "alexandriacleanroom-99.8",
            ]
        )
        == 0
    )
    controls = json.loads(
        (controls_dir / "run_controls_summary.json").read_text(encoding="utf-8")
    )
    assert controls["case_count"] == 2
    assert controls["claim_boundary"]["blocked_claims"]
    first_receipt = json.loads(
        Path(controls["receipts"][0]["receipt"]).read_text(encoding="utf-8")
    )
    assert first_receipt["approval"]["approved_for_execution"] is True
    assert first_receipt["scoring"]["scorer_status"] == "blocked"


def test_deepresearch_bench_full_run_package_rejects_partial_query_set(
    tmp_path: Path,
):
    harness, suite_dir, _runs_dir, _suite_id = prepare_deepresearch_bench_subset_pressure(
        tmp_path, "drb-full-red"
    )
    official_repo = tmp_path / "official_deepresearch_bench_full_red"
    source_refresh = tmp_path / "deepresearch_bench_source_refresh_full_red.json"
    query_jsonl = tmp_path / "query_2.jsonl"
    output_dir = tmp_path / "full_run_package_red"
    write_deepresearch_bench_official_repo_fixture(official_repo)
    write_deepresearch_bench_refresh(source_refresh)
    write_deepresearch_bench_query_jsonl(query_jsonl, row_count=2)

    result = harness.main(
        [
            "deepresearch-bench-full-run-package",
            "deepresearch_bench_full_package_fixture",
            "--query-jsonl",
            str(query_jsonl),
            "--source-refresh",
            str(source_refresh),
            "--subset-summary",
            str(suite_dir / "deepresearch_bench_subset_pressure_summary.json"),
            "--official-repo",
            str(official_repo),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert result == 2
    validation = json.loads(
        (output_dir / "full_run_package_validation.json").read_text(encoding="utf-8")
    )
    assert validation["status"] == "failed"
    assert "full-run package lacks all 100 query rows" in validation["failed_checks"]


def test_deepresearch_bench_flywheel_plan_selects_next_overlay_without_claims(
    tmp_path: Path,
):
    harness, run_dir, runs_dir, run_id = prepare_deepresearch_bench_claim_review_run(
        tmp_path, "drb-flywheel"
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-improvement-compile",
                run_id,
            ]
        )
        == 0
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-improvement-gate",
                run_id,
            ]
        )
        == 0
    )
    subset_harness, suite_dir, _subset_runs_dir, _suite_id = (
        prepare_deepresearch_bench_subset_pressure(tmp_path, "drb-flywheel-subset")
    )
    package_dir = write_deepresearch_bench_full_package_fixture(
        tmp_path, subset_harness, suite_dir, "drb-flywheel"
    )
    output_dir = tmp_path / "flywheel_plan"

    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "deepresearch-bench-flywheel-plan",
            "deepresearch_bench_flywheel_fixture",
            "--case-id",
            run_id,
            "--subset-summary",
            str(suite_dir / "deepresearch_bench_subset_pressure_summary.json"),
            "--full-run-package",
            str(package_dir / "full_run_package.json"),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert result == 0
    plan = json.loads(
        (output_dir / "flywheel_next_action_plan.json").read_text(encoding="utf-8")
    )
    validation = json.loads(
        (output_dir / "flywheel_next_action_validation.json").read_text(
            encoding="utf-8"
        )
    )

    assert validation["status"] == "passed"
    assert plan["state_assessment"]["all_candidates_gated"] is True
    assert plan["selected_candidate"]["candidate_id"] == (
        "cand_drb_numeric_appendix_prompt_001"
    )
    assert {action["action_id"] for action in plan["next_actions"]} == {
        "resolve_scorer_authority_run_control",
        "apply_selected_candidate_overlay",
        "rerun_subset_pressure_after_candidate_overlay",
        "prepare_full_100_case_run_control_packet",
    }
    assert plan["claim_boundary"]["may_claim_grep_parity"] is False
    assert "DeepResearch Bench score" in plan["claim_boundary"]["blocked_claims"]
    assert plan["source_artifacts"]["candidate_gate_results"]["sha256"]
    assert (output_dir / "architect_work_packet.md").exists()


def test_deepresearch_bench_flywheel_plan_fails_until_candidates_are_gated(
    tmp_path: Path,
):
    harness, _run_dir, runs_dir, run_id = prepare_deepresearch_bench_claim_review_run(
        tmp_path, "drb-flywheel-red"
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-improvement-compile",
                run_id,
            ]
        )
        == 0
    )
    subset_harness, suite_dir, _subset_runs_dir, _suite_id = (
        prepare_deepresearch_bench_subset_pressure(tmp_path, "drb-flywheel-red-subset")
    )
    package_dir = write_deepresearch_bench_full_package_fixture(
        tmp_path, subset_harness, suite_dir, "drb-flywheel-red"
    )
    output_dir = tmp_path / "flywheel_plan_red"

    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "deepresearch-bench-flywheel-plan",
            "deepresearch_bench_flywheel_red_fixture",
            "--case-id",
            run_id,
            "--subset-summary",
            str(suite_dir / "deepresearch_bench_subset_pressure_summary.json"),
            "--full-run-package",
            str(package_dir / "full_run_package.json"),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert result == 2
    validation = json.loads(
        (output_dir / "flywheel_next_action_validation.json").read_text(
            encoding="utf-8"
        )
    )
    assert validation["status"] == "failed"
    assert "improvement candidates have not all been gated" in validation[
        "failed_checks"
    ]


def test_deepresearch_bench_candidate_overlay_writes_isolated_prompt_overlay(
    tmp_path: Path,
):
    harness, flywheel_dir, _runs_dir, _run_id = prepare_deepresearch_bench_flywheel_plan(
        tmp_path, "drb-overlay"
    )
    output_dir = tmp_path / "prompt_overlay"
    prompt_pack = ROOT / "sandbox" / "codex-dr" / "harness-specs" / "live_role_prompt_pack.md"
    original_prompt_pack = prompt_pack.read_text(encoding="utf-8")

    result = harness.main(
        [
            "deepresearch-bench-apply-candidate-overlay",
            "drb_numeric_appendix_overlay_fixture",
            "--flywheel-plan",
            str(flywheel_dir / "flywheel_next_action_plan.json"),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert result == 0
    overlay = json.loads((output_dir / "prompt_overlay.json").read_text(encoding="utf-8"))
    validation = json.loads(
        (output_dir / "prompt_overlay_validation.json").read_text(encoding="utf-8")
    )
    receipt = json.loads(
        (output_dir / "overlay_promotion_receipt.json").read_text(encoding="utf-8")
    )

    assert validation["status"] == "passed"
    assert overlay["candidate_id"] == "cand_drb_numeric_appendix_prompt_001"
    assert overlay["target_surface_type"] == "prompt"
    assert overlay["live_surface_changed"] is False
    assert overlay["base_surface_mutation_allowed"] is False
    assert "task_reentry_synthesis" in overlay["applies_to_task_ids"]
    assert "Numeric Claim Support Appendix" in (output_dir / "prompt_overlay.md").read_text(
        encoding="utf-8"
    )
    assert receipt["promotion_status"] == "overlay_created_not_live_mutated"
    assert prompt_pack.read_text(encoding="utf-8") == original_prompt_pack


def test_mesh_live_plan_can_render_numeric_appendix_prompt_overlay(
    tmp_path: Path,
):
    harness, flywheel_dir, _runs_dir, _run_id = prepare_deepresearch_bench_flywheel_plan(
        tmp_path, "drb-overlay-render"
    )
    overlay_dir = tmp_path / "prompt_overlay_render"
    assert (
        harness.main(
            [
                "deepresearch-bench-apply-candidate-overlay",
                "drb_numeric_appendix_overlay_render_fixture",
                "--flywheel-plan",
                str(flywheel_dir / "flywheel_next_action_plan.json"),
                "--output-dir",
                str(overlay_dir),
            ]
        )
        == 0
    )
    mesh_harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    receipt_path = runs_dir / "dry_run_control.json"
    write_dry_run_control_receipt(receipt_path, "draco_mesh_fixture_001")

    result = mesh_harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "mesh-live-plan",
            "draco_mesh_fixture_001",
            "--run-control",
            str(receipt_path),
            "--prompt-overlay",
            str(overlay_dir / "prompt_overlay.json"),
        ]
    )

    assert result == 0
    launch_plan = json.loads(
        (run_dir / "live_adapter" / "launch_plan.json").read_text(encoding="utf-8")
    )
    assert launch_plan["prompt_overlay"]["candidate_id"] == (
        "cand_drb_numeric_appendix_prompt_001"
    )
    synthesis_prompt = (
        run_dir / "live_adapter" / "prompts" / "task_pointer_first_synthesis.md"
    ).read_text(encoding="utf-8")
    branch_prompt = (
        run_dir / "live_adapter" / "prompts" / "task_deep_search.md"
    ).read_text(encoding="utf-8")
    assert "## Candidate Prompt Overlay" in synthesis_prompt
    assert "Numeric Claim Support Appendix" in synthesis_prompt
    assert "## Candidate Prompt Overlay" not in branch_prompt
    assert (run_dir / "live_adapter" / "prompt_overlay.json").exists()


def test_deepresearch_bench_race_bridge_fails_when_official_path_missing(tmp_path: Path):
    harness = load_harness()
    source_refresh = tmp_path / "deepresearch_bench_source_refresh.json"
    report_export = tmp_path / "raw_generated_reports.jsonl"
    official_repo = tmp_path / "missing_official_repo"
    bridge_dir = tmp_path / "race_bridge"
    write_deepresearch_bench_refresh(source_refresh)
    report_export.write_text(
        json.dumps(
            {
                "id": 1,
                "prompt": "Research the industrial outlook for green ammonia.",
                "article": "A benchmark article.",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    result = harness.main(
        [
            "deepresearch-bench-race-bridge",
            "--raw-reports",
            str(report_export),
            "--source-refresh",
            str(source_refresh),
            "--official-repo",
            str(official_repo),
            "--output-dir",
            str(bridge_dir),
        ]
    )

    assert result == 2
    assert not (bridge_dir / "scorer_manifest.json").exists()


def test_suite_claim_review_keeps_provider_off_suite_blocked(tmp_path: Path):
    harness = load_harness()
    runs_dir = TEST_RUNS_ROOT / f"{tmp_path.name}-suite-review"
    shutil.rmtree(runs_dir, ignore_errors=True)
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "multi-case-smoke",
                "draco_suite_001",
                "--case-count",
                "2",
            ]
        )
        == 0
    )

    result = harness.main(
        ["--runs-dir", str(runs_dir), "suite-claim-review", "draco_suite_001"]
    )

    assert result == 0
    review = json.loads(
        (
            runs_dir / "draco_suite_001" / "benchmark_suite_claim_review.json"
        ).read_text(encoding="utf-8")
    )
    assert review["status"] == "passed"
    assert review["decision"] == "blocked_no_score"
    assert review["may_widen_public_benchmark_claims"] is False
    assert {case["decision"] for case in review["case_reviews"]} == {"blocked_no_score"}
    assert "Grep parity" in review["claim_boundary"]["blocked_claims"]


def test_suite_claim_review_fails_closed_on_widened_case_claim(tmp_path: Path):
    harness = load_harness()
    runs_dir = TEST_RUNS_ROOT / f"{tmp_path.name}-suite-review"
    shutil.rmtree(runs_dir, ignore_errors=True)
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "multi-case-smoke",
                "draco_suite_001",
                "--case-count",
                "2",
            ]
        )
        == 0
    )
    add_draco_score_allowed_claim(
        runs_dir / "draco_suite_001_case_001" / "allowed_claims.json"
    )

    result = harness.main(
        ["--runs-dir", str(runs_dir), "suite-claim-review", "draco_suite_001"]
    )

    assert result == 2
    review = json.loads(
        (
            runs_dir / "draco_suite_001" / "benchmark_suite_claim_review.json"
        ).read_text(encoding="utf-8")
    )
    assert review["status"] == "failed"
    assert review["decision"] == "failed_closed"
    assert any("validation failed" in failure for failure in review["failed_checks"])


@pytest.mark.parametrize(
    "args",
    [
        ["run-planner", "local_fixture_001", "--run-control", "missing.yaml"],
        [
            "run-branch",
            "local_fixture_001",
            "branch_a",
            "--run-control",
            "missing.yaml",
        ],
        ["run-review", "local_fixture_001", "--run-control", "missing.yaml"],
        [
            "run-reentry",
            "local_fixture_001",
            "review_001",
            "--run-control",
            "missing.yaml",
        ],
        ["score", "local_fixture_001", "--run-control", "missing.yaml"],
    ],
)
def test_future_provider_backed_commands_fail_closed(tmp_path: Path, args: list[str]):
    harness = load_harness()
    runs_dir = TEST_RUNS_ROOT / tmp_path.name
    shutil.rmtree(runs_dir, ignore_errors=True)

    result = harness.main(["--runs-dir", str(runs_dir), *args])

    assert result == 2
    assert not (runs_dir / "local_fixture_001" / "provider_metadata.json").exists()
    assert not (runs_dir / "local_fixture_001" / "transcripts").exists()


@pytest.mark.parametrize(
    ("mutation", "expected_check"),
    [
        (lambda run_dir: (run_dir / "events.jsonl").unlink(), "required_files_present"),
        (
            lambda run_dir: remove_event_type(run_dir / "events.jsonl", "review.written"),
            "events_required_types_present",
        ),
        (
            lambda run_dir: disconnect_event_chain(run_dir / "events.jsonl"),
            "events_causal_chain_connected",
        ),
        (
            lambda run_dir: (run_dir / "branches" / "branch_a" / "pointer.md").unlink(),
            "branch_triplets_present",
        ),
        (
            lambda run_dir: (run_dir / "reentry_decisions.jsonl").write_text("", encoding="utf-8"),
            "review_reentry_compiled",
        ),
        (
            lambda run_dir: (run_dir / "compactions" / "compaction_001.json").unlink(),
            "compaction_receipt_present",
        ),
        (
            lambda run_dir: set_benchmark_score(run_dir / "benchmark_score.json"),
            "benchmark_placeholder_not_score",
        ),
        (
            lambda run_dir: add_widened_allowed_claim(run_dir / "allowed_claims.json"),
            "allowed_claims_scope_enforced",
        ),
    ],
)
def test_validator_fails_expected_provider_off_mutations(
    tmp_path: Path, mutation, expected_check: str
):
    harness, run_dir, runs_dir = fresh_run(tmp_path)
    mutation(run_dir)

    report = harness.validate_run("local_fixture_001", runs_dir=runs_dir)

    assert report["status"] == "failed"
    assert expected_check in failed_check_ids(report)


@pytest.mark.parametrize(
    ("mutation", "expected_check"),
    [
        (
            lambda run_dir: (run_dir / "branches" / "data_analysis" / "evidence.jsonl").unlink(),
            "branch_triplets_present",
        ),
        (
            lambda run_dir: add_generator_reference_leak(run_dir / "case_manifest.json"),
            "benchmark_case_manifest_sealed",
        ),
        (
            lambda run_dir: add_generator_rubric_leak(run_dir / "case_manifest.json"),
            "benchmark_case_manifest_sealed",
        ),
        (
            lambda run_dir: remove_case_manifest_source_field(
                run_dir / "case_manifest.json", "license_observed"
            ),
            "benchmark_case_manifest_sealed",
        ),
        (
            lambda run_dir: add_missing_dependency(run_dir / "task_graph.json"),
            "task_graph_dependencies_valid",
        ),
        (
            lambda run_dir: (run_dir / "pointer_read_receipts.jsonl").unlink(),
            "pointer_first_receipts_present",
        ),
        (
            lambda run_dir: (run_dir / "reentry_decisions.jsonl").write_text("", encoding="utf-8"),
            "review_reentry_compiled",
        ),
        (
            lambda run_dir: set_benchmark_score(run_dir / "benchmark_score.json"),
            "benchmark_placeholder_not_score",
        ),
        (
            lambda run_dir: (run_dir / "scorer_manifest.json").unlink(),
            "draco_scorer_manifest_valid",
        ),
        (
            lambda run_dir: remove_scorer_manifest_field(
                run_dir / "scorer_manifest.json", "rubric_mapping"
            ),
            "draco_scorer_manifest_valid",
        ),
        (
            lambda run_dir: remove_scorer_manifest_field(
                run_dir / "scorer_manifest.json", "judge_policy"
            ),
            "draco_scorer_manifest_valid",
        ),
        (
            lambda run_dir: remove_scorer_manifest_field(
                run_dir / "scorer_manifest.json", "sealed_reference_policy"
            ),
            "draco_scorer_manifest_valid",
        ),
        (
            lambda run_dir: set_benchmark_score(run_dir / "benchmark_score.json"),
            "draco_scorer_manifest_valid",
        ),
        (
            lambda run_dir: (run_dir / "evaluation_ledger.json").unlink(),
            "benchmark_evaluation_claim_gate_enforced",
        ),
        (
            lambda run_dir: remove_evaluation_ledger_field(
                run_dir / "evaluation_ledger.json", "failure_taxonomy"
            ),
            "benchmark_evaluation_claim_gate_enforced",
        ),
        (
            lambda run_dir: set_evaluation_ledger_allows_claim_widening(
                run_dir / "evaluation_ledger.json"
            ),
            "benchmark_evaluation_claim_gate_enforced",
        ),
        (
            lambda run_dir: add_draco_score_allowed_claim(run_dir / "allowed_claims.json"),
            "benchmark_evaluation_claim_gate_enforced",
        ),
        (
            lambda run_dir: remove_failure_taxonomy_class(
                run_dir / "self_improvement" / "failure_taxonomy.json", "prompt"
            ),
            "self_improvement_replay_gate_enforced",
        ),
        (
            lambda run_dir: promote_improvement_proposal(
                run_dir / "self_improvement" / "improvement_proposal.json"
            ),
            "self_improvement_replay_gate_enforced",
        ),
        (
            lambda run_dir: remove_replay_evaluation_failures(
                run_dir / "self_improvement" / "replay_corpus.json"
            ),
            "self_improvement_replay_gate_enforced",
        ),
        (
            lambda run_dir: remove_proposal_source_evaluation_failures(
                run_dir / "self_improvement" / "improvement_proposal.json"
            ),
            "self_improvement_replay_gate_enforced",
        ),
        (
            lambda run_dir: remove_regression_evidence_requirement(
                run_dir / "self_improvement" / "regression_gate.json"
            ),
            "self_improvement_replay_gate_enforced",
        ),
        (
            lambda run_dir: allow_failed_replay_claim_widening(
                run_dir / "self_improvement" / "regression_gate.json"
            ),
            "self_improvement_replay_gate_enforced",
        ),
        (
            lambda run_dir: add_widened_allowed_claim(run_dir / "allowed_claims.json"),
            "allowed_claims_scope_enforced",
        ),
        (
            lambda run_dir: swap_event_types(
                run_dir / "events.jsonl", "reentry.compiled", "report.written"
            ),
            "orchestrator_state_machine_order_valid",
        ),
        (
            lambda run_dir: swap_event_types(
                run_dir / "events.jsonl",
                "report.written",
                "benchmark.placeholder_written",
            ),
            "orchestrator_state_machine_order_valid",
        ),
        (
            lambda run_dir: swap_event_types(
                run_dir / "events.jsonl",
                "evaluation_ledger.written",
                "self_improvement.replay_written",
            ),
            "orchestrator_state_machine_order_valid",
        ),
        (
            lambda run_dir: remove_artifact_event_custody(
                run_dir / "artefact_manifest.json", "synthesis.md"
            ),
            "artefact_manifest_hashes_match",
        ),
        (
            lambda run_dir: corrupt_after_manifest(run_dir / "report.md"),
            "artefact_manifest_hashes_match",
        ),
    ],
)
def test_validator_fails_expected_dr_mesh_mutations(tmp_path: Path, mutation, expected_check: str):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    mutation(run_dir)

    report = harness.validate_run("draco_mesh_fixture_001", runs_dir=runs_dir)

    assert report["status"] == "failed"
    assert expected_check in failed_check_ids(report)


def remove_event_type(events_path: Path, event_type: str) -> None:
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    kept = [event for event in events if event["event_type"] != event_type]
    events_path.write_text(
        "\n".join(json.dumps(event, sort_keys=True) for event in kept) + "\n",
        encoding="utf-8",
    )


def swap_event_types(events_path: Path, first_type: str, second_type: str) -> None:
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    first_event = next(event for event in events if event["event_type"] == first_type)
    second_event = next(event for event in events if event["event_type"] == second_type)
    first_event["event_type"], second_event["event_type"] = (
        second_event["event_type"],
        first_event["event_type"],
    )
    events_path.write_text(
        "\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n",
        encoding="utf-8",
    )


def disconnect_event_chain(events_path: Path) -> None:
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    events[1]["causally_after"] = ["evt_missing_parent"]
    events_path.write_text(
        "\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n",
        encoding="utf-8",
    )


def add_missing_dependency(graph_path: Path) -> None:
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["tasks"][1]["depends_on"].append("task_missing")
    graph_path.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def add_generator_reference_leak(manifest_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["generator_visible"]["reference_answer"] = "Reference answer: leaked payload"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def add_generator_rubric_leak(manifest_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["generator_visible"]["rubric_payload"] = {
        "criterion": "Rubric payload: leaked scorer-only criterion"
    }
    manifest["leakage_policy"]["rubric_payload_visible_to_generator"] = True
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def remove_case_manifest_source_field(manifest_path: Path, field: str) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source"].pop(field, None)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def remove_artifact_event_custody(manifest_path: Path, artifact_path: str) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in manifest["artifacts"]:
        if artifact["path"] == artifact_path:
            artifact["produced_by_event"] = None
            break
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def corrupt_after_manifest(path: Path) -> None:
    path.write_text(path.read_text(encoding="utf-8") + "\nCorrupted after manifest.\n")


def write_case_spec_manifest(
    path: Path,
    *,
    first_question: str = "Manifest question A",
) -> None:
    manifest = {
        "schema_version": "codex-dr.case_spec_manifest.v1",
        "benchmark_family": "DRACO",
        "source": {
            "dataset_id": "perplexity-ai/draco",
            "dataset_commit": "ce076749809027649ebd331bcb70f42bf720d387",
            "split": "test",
            "source_file": "test.jsonl",
            "license_observed": "mit",
            "access_observed": "public_ungated",
            "manifest_ref": "sandbox/codex-dr/benchmark-manifests/draco_manifest.md",
        },
        "cases": [
            {
                "case_id": "draco_manifest_case_a",
                "row_indices": [5],
                "generator_visible": {
                    "question": first_question,
                    "case_pointer": "Manifest row 5 pointer; raw row not committed.",
                    "allowed_context": ["case source metadata", "local artifacts"],
                    "source_policy": "Use manifest-selected provider-off fixture facts.",
                },
            },
            {
                "case_id": "draco_manifest_case_b",
                "row_indices": [8],
                "generator_visible": {
                    "question": "Manifest question B",
                    "case_pointer": "Manifest row 8 pointer; raw row not committed.",
                    "allowed_context": ["case source metadata", "local artifacts"],
                    "source_policy": "Use manifest-selected provider-off fixture facts.",
                },
            },
        ],
    }
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_deepresearch_bench_refresh(path: Path) -> None:
    refresh = {
        "schema_version": "codex-dr.deepresearch_bench_source_refresh.v1",
        "official_repository": {
            "full_name": "Ayanami0730/deep_research_bench",
            "commit_sha": "eb155b23543399cf2114a403cb1d3c0b776a8a64",
            "license_observed": "Apache-2.0",
        },
        "official_dataset": {
            "dataset_id": "muset-ai/DeepResearch-Bench-Dataset",
            "revision_sha": "f7d27cdd3930dd1eaf67a217821e616cc62e9f8e",
            "license_observed": "apache-2.0",
        },
        "official_leaderboard": {
            "csv_sha256": "fixture-leaderboard-sha",
            "top_rows_observed": [
                {
                    "model": "grep-v5",
                    "overall_score": 56.23,
                }
            ],
        },
        "evaluator_lane": {
            "current_lane_before_may_2026": "Gemini-2.5-Pro based RACE evaluation."
        },
        "observed_at": "2026-04-24T11:35:00+01:00",
    }
    path.write_text(json.dumps(refresh, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_deepresearch_bench_query_jsonl(
    path: Path,
    *,
    first_prompt: str = "Research the industrial outlook for green ammonia.",
    row_count: int = 2,
) -> None:
    base_prompts = [
        first_prompt,
        "Summarize current approaches to long-duration grid storage.",
    ]
    rows = []
    for index in range(row_count):
        rows.append(
            {
                "id": index + 1,
                "topic": "Finance & Business" if index % 2 == 0 else "Science & Technology",
                "language": "en",
                "prompt": (
                    base_prompts[index]
                    if index < len(base_prompts)
                    else f"Research synthetic DeepResearch Bench fixture topic {index + 1}."
                ),
            }
        )
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def write_deepresearch_bench_official_repo_fixture(path: Path) -> None:
    required_files = {
        "README.md": "DeepResearch Bench fixture README\n",
        "deepresearch_bench_race.py": "# fixture official RACE script\n",
        "run_benchmark.sh": "#!/bin/bash\n",
        "utils/api.py": "# fixture API client\n",
        "data/prompt_data/query.jsonl": (
            json.dumps(
                {
                    "id": 1,
                    "language": "en",
                    "prompt": "Research the industrial outlook for green ammonia.",
                },
                sort_keys=True,
            )
            + "\n"
        ),
        "data/criteria_data/criteria.jsonl": (
            json.dumps({"prompt": "Research the industrial outlook for green ammonia."})
            + "\n"
        ),
        "data/test_data/cleaned_data/reference.jsonl": (
            json.dumps(
                {
                    "id": 1,
                    "prompt": "Research the industrial outlook for green ammonia.",
                    "article": "Reference article for scorer-only fixture.",
                },
                sort_keys=True,
            )
            + "\n"
        ),
    }
    for relative, content in required_files.items():
        target = path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def write_dry_run_control_receipt(path: Path, run_id: str) -> None:
    receipt = {
        "schema_version": "codex-dr.run_control_receipt.v1",
        "receipt_id": f"run_control_{run_id}",
        "bead_id": "alexandriacleanroom-91.1.5.9",
        "run_id": run_id,
        "run_purpose": "Dry-run render of Codex CLI DR mesh role launch plans.",
        "runner": {
            "kind": "codex_exec_box",
            "command_surface": "mesh-live-plan",
            "cwd": "sandbox/codex-dr/",
            "transcript_root": f"sandbox/codex-dr/runs/{run_id}/transcripts/",
        },
        "operational_bounds": {
            "max_wall_clock_minutes": 15,
            "foreground_supervision_required": True,
            "automatic_retry_allowed": False,
            "kill_path": "foreground supervisor sends SIGINT, then SIGTERM",
        },
        "expected_artifacts": {
            "run_bundle": f"sandbox/codex-dr/runs/{run_id}/",
            "transcript_capture": f"sandbox/codex-dr/runs/{run_id}/transcripts/",
        },
        "inputs": {
            "allowed_sources": [
                "DRACO row pointer",
                "public web sources",
                "sandbox run manifests",
            ],
            "forbidden_sources": [
                "secrets",
                "customer data",
                "root env files",
            ],
            "data_policy": "No secrets, customer data, or root env files.",
        },
        "scoring": {
            "benchmark_family": "DRACO",
            "scorer_status": "blocked",
            "judge_or_scorer": "evidence-pending",
        },
        "allowed_claims_if_success": [
            "A dry-run launch plan was rendered without live Codex execution."
        ],
        "non_claims_even_if_success": [
            "Grep parity",
            "DRACO score",
            "leaderboard rank",
            "product readiness",
        ],
        "approval": {
            "approved_for_execution": False,
            "approved_for_dry_run_planning": True,
            "approval_note": "Dry-run launch planning only; no codex exec allowed.",
        },
    }
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_live_execution_control_receipt(path: Path, run_id: str) -> None:
    receipt = {
        "schema_version": "codex-dr.run_control_receipt.v1",
        "receipt_id": f"run_control_{run_id}_approved",
        "bead_id": "alexandriacleanroom-91.1.5.16",
        "run_id": run_id,
        "run_purpose": "Execute a bounded live Codex CLI DR mesh smoke.",
        "runner": {
            "kind": "codex_exec_box",
            "command_surface": "alexandria-dr mesh-execute-live",
            "cwd": "sandbox/codex-dr/",
            "transcript_root": f"sandbox/codex-dr/runs/{run_id}/transcripts/",
        },
        "operational_bounds": {
            "max_cases": 1,
            "max_live_attempts": 1,
            "max_reentry_rounds": 1,
            "max_wall_clock_minutes": 15,
            "foreground_supervision_required": True,
            "automatic_retry_allowed": False,
            "kill_path": "foreground supervisor sends SIGINT, then SIGTERM",
        },
        "expected_artifacts": {
            "run_bundle": f"sandbox/codex-dr/runs/{run_id}/",
            "transcript_capture": f"sandbox/codex-dr/runs/{run_id}/transcripts/",
        },
        "inputs": {
            "allowed_sources": [
                "DRACO row pointer",
                "public web sources",
                "sandbox run manifests",
            ],
            "forbidden_sources": [
                "secrets",
                "customer data",
                "root env files",
            ],
            "data_policy": "No secrets, customer data, or root env files.",
        },
        "scoring": {
            "benchmark_family": "DRACO",
            "scorer_status": "blocked",
            "judge_or_scorer": "evidence-pending",
        },
        "allowed_claims_if_success": [
            "Codex CLI roles executed once for a bounded DR mesh smoke with transcript custody."
        ],
        "non_claims_even_if_success": [
            "Grep parity",
            "DRACO score",
            "leaderboard rank",
            "product readiness",
            "benchmark execution",
        ],
        "approval": {
            "approved_for_execution": True,
            "approved_for_dry_run_planning": True,
            "approval_note": "Principal authorized the live Codex DR mesh smoke.",
        },
    }
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_scoring_control_receipt(path: Path, run_id: str) -> None:
    receipt = {
        "schema_version": "codex-dr.run_control_receipt.v1",
        "receipt_id": f"run_control_{run_id}_score_approved",
        "bead_id": "alexandriacleanroom-91.1.5.17",
        "run_id": run_id,
        "run_purpose": (
            "Record a scorer-backed DRACO evaluation artifact with claims still blocked."
        ),
        "runner": {
            "kind": "scorer",
            "command_surface": "alexandria-dr score",
            "cwd": "sandbox/codex-dr/",
            "transcript_root": f"sandbox/codex-dr/runs/{run_id}/transcripts/scorer/",
        },
        "authority": {
            "case_manifest": (
                "sandbox/codex-dr/benchmark-manifests/draco_tiny_smoke_case_manifest.md"
            ),
            "scorer_manifest": f"sandbox/codex-dr/runs/{run_id}/scorer_manifest.json",
        },
        "operational_bounds": {
            "max_cases": 1,
            "max_live_attempts": 1,
            "max_wall_clock_minutes": 15,
            "foreground_supervision_required": True,
            "automatic_retry_allowed": False,
            "kill_path": "foreground supervisor sends SIGINT, then SIGTERM",
        },
        "scoring": {
            "benchmark_family": "DRACO",
            "scorer_status": "approved",
            "judge_or_scorer": "local_draco_stub_judge",
            "prompt_or_code_version": "draco-judge-v1",
        },
        "allowed_claims_if_success": [
            "A scorer-backed DRACO evaluation artifact was recorded with transcript "
            "custody for this run."
        ],
        "non_claims_even_if_success": [
            "Grep parity",
            "DRACO score",
            "leaderboard rank",
            "product readiness",
            "benchmark execution",
        ],
        "approval": {
            "approved_for_execution": True,
            "approved_for_dry_run_planning": False,
            "approval_note": "Approved scoring finalization only; claim gate remains closed.",
        },
    }
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fake_live_codex_runner(
    *,
    role_plan: dict,
    prompt: str,
    workspace_path: Path,
    transcript_path: Path,
    last_message_path: Path,
    timeout_seconds: int,
) -> dict:
    assert "Live Execution Overlay" in prompt
    assert timeout_seconds > 0
    task_id = role_plan["task_id"]
    for relative in role_plan["output_paths"]:
        output = workspace_path / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        if relative == "pointer_read_receipts.jsonl":
            branch_ids = ["deep_search", "data_analysis", "verification", "reentry_followup"]
            output.write_text(
                "\n".join(
                    json.dumps(
                        {
                            "branch_id": branch_id,
                            "pointer_path": f"branches/{branch_id}/pointer.md",
                            "pointer_read_before_analysis": True,
                            "selected_analysis_spans": [
                                {
                                    "analysis_path": f"branches/{branch_id}/analysis.md",
                                    "section_heading": "Stubbed live runner",
                                }
                            ],
                            "evidence_paths": [f"branches/{branch_id}/evidence.jsonl"],
                        },
                        sort_keys=True,
                    )
                    for branch_id in branch_ids
                )
                + "\n",
                encoding="utf-8",
            )
        elif relative == "adequacy_assessments.jsonl":
            output.write_text(
                json.dumps(
                    {
                        "assessment_id": f"adequacy_{task_id}",
                        "status": "satisfied_for_live_stub",
                        "gaps": [],
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        elif relative.endswith("reviews/review_001.json"):
            output.write_text(
                json.dumps(
                    {
                        "schema_version": "codex-dr.stubbed_live_review.v1",
                        "review_id": "review_001",
                        "status": "reentry_required",
                        "findings": [
                            {
                                "finding_id": "finding_reentry_001",
                                "severity": "high",
                                "requires_reentry": True,
                                "title": "Stubbed re-entry required",
                                "detail": "Stubbed live review requires a bounded follow-up.",
                                "evidence": ["synthesis.md"],
                                "recommended_task": "Run a bounded re-entry follow-up.",
                            }
                        ],
                        "claim_boundary_check": {"within_allowed_boundary": True},
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        elif relative == "backpressure/adequacy_backpressure_queue.json":
            output.write_text(
                json.dumps(
                    {
                        "schema_version": "codex-dr.adequacy_backpressure_queue.v2",
                        "queue_status": "clear",
                        "writer_blocked": False,
                        "items": [],
                        "quarantined_items": [],
                        "normalization_summary": {
                            "canonical_item_count": 0,
                            "review_proposed_item_count": 0,
                            "quarantined_review_proposal_count": 0,
                            "legacy_fields_normalized_by": "harness",
                        },
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        elif relative.endswith("reentry_result.json"):
            packet_path = workspace_path / "reentry_task_packet.json"
            packet = (
                json.loads(packet_path.read_text(encoding="utf-8"))
                if packet_path.exists()
                else {}
            )
            output.write_text(
                json.dumps(
                    {
                        "schema_version": "codex_dr_reentry_result_v0.2",
                        "run_id": "draco_mesh_fixture_001",
                        "case_id": "draco_mesh_fixture_001",
                        "source_gap_id": packet.get("source_gap_id"),
                        "source_task_packet_path": "reentry_task_packet.json",
                        "branch_status": "completed",
                        "attempted_action": "Stubbed bounded re-entry repair.",
                        "artifacts_written": role_plan.get("output_paths", []),
                        "closure_condition_assessment": {
                            "closure_condition": (
                                packet.get("closure", {}).get("closure_condition")
                            ),
                            "condition_satisfied": False,
                            "rationale": (
                                "Stubbed live runner returns repair evidence for "
                                "reviewer adjudication, not closure."
                            ),
                        },
                        "proposed_next_status": "narrowed",
                        "remaining_blockers": [
                            {
                                "description": "Reviewer must adjudicate repair evidence.",
                                "affected_claim_ids": [],
                                "affected_artifact_path": "synthesis.md",
                            }
                        ],
                        "reviewer_notes": "Stubbed repair returned for review.",
                        "claim_boundary": {"must_not_claim": ["grep_parity"]},
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        elif relative.endswith("citation_support_map.json"):
            output.write_text(
                json.dumps(
                    {
                        "schema_version": "codex_dr_citation_support_map.v1",
                        "source_gap_id": "gap_citation_support_001",
                        "claims": [
                            {
                                "claim_id": "claim_001",
                                "claim_text": "Stubbed claim.",
                                "support_status": "directly_supported",
                                "evidence_refs": ["branches/verification/evidence.jsonl#ev"],
                                "writer_blocking": False,
                            }
                        ],
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        elif relative.endswith("adequacy_delta.json"):
            gap_id = Path(relative).parts[1] if len(Path(relative).parts) > 1 else None
            branch_id = "reentry_followup"
            if role_plan["task_id"].startswith("task_reentry_synthesis_"):
                branch_id = "reentry_followup_" + role_plan["task_id"].rsplit("_", 1)[1]
            output.write_text(
                json.dumps(
                    {
                        "schema_version": "codex_dr_reentry_adequacy_delta.v1",
                        "run_id": "draco_mesh_fixture_001",
                        "case_id": "draco_mesh_fixture_001",
                        "source_gap_id": gap_id,
                        "source_task_packet_path": (
                            f"reentry/{gap_id}/reentry_task_packet.json"
                            if gap_id
                            else None
                        ),
                        "source_reentry_result_path": (
                            f"branches/{branch_id}/reentry_result.json"
                        ),
                        "reentry_synthesis_path": (
                            f"reentry/{gap_id}/reentry_synthesis.md"
                            if gap_id
                            else None
                        ),
                        "evidence_delta": [
                            "Stubbed recursive repair evidence was integrated."
                        ],
                        "proposed_next_status": "narrowed",
                        "remaining_blockers": [
                            "Reviewer must adjudicate whether repair closed the gap."
                        ],
                        "reviewer_next_action": "Review repair artifacts.",
                        "closure_authority": "reviewer",
                        "closure_authorized": False,
                        "writer_permission": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        elif relative.endswith(".jsonl"):
            output.write_text(
                json.dumps(
                    {
                        "evidence_id": f"ev_{task_id}",
                        "admission_status": "admitted",
                        "source": "stubbed-live-runner",
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        elif relative.endswith("reentry_synthesis.md"):
            gap_id = Path(relative).parts[1] if len(Path(relative).parts) > 1 else None
            output.write_text(
                f"# Re-entry Synthesis\n\nSource gap: `{gap_id}`\n\n"
                "Repair evidence was integrated for reviewer adjudication only.\n",
                encoding="utf-8",
            )
        elif relative.endswith(".json"):
            output.write_text(
                json.dumps(
                    {
                        "schema_version": "codex-dr.stubbed_live_role.v1",
                        "task_id": task_id,
                        "requires_reentry": True,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        elif relative == "report.md":
            output.write_text(
                "# Live stub report\n\n"
                "The provider-off DR mesh fixture preserves planner, task graph, "
                "branch, pointer-first, review re-entry, and writer custody topology.\n",
                encoding="utf-8",
            )
        else:
            output.write_text(
                f"# Live stub output for {task_id}\n\n## Read Next\n- Stubbed live runner.\n",
                encoding="utf-8",
            )
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.write_text(
        json.dumps(
            {"type": "thread.started", "thread_id": f"thread_{task_id}"},
            sort_keys=True,
        )
        + "\n"
        + json.dumps({"type": "stub", "task_id": task_id}, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    last_message_path.parent.mkdir(parents=True, exist_ok=True)
    last_message_path.write_text(f"stub completed {task_id}\n", encoding="utf-8")
    return {"returncode": 0}


def fake_live_codex_runner_with_writer_constraints(
    *,
    role_plan: dict,
    prompt: str,
    workspace_path: Path,
    transcript_path: Path,
    last_message_path: Path,
    timeout_seconds: int,
) -> dict:
    result = fake_live_codex_runner(
        role_plan=role_plan,
        prompt=prompt,
        workspace_path=workspace_path,
        transcript_path=transcript_path,
        last_message_path=last_message_path,
        timeout_seconds=timeout_seconds,
    )
    if role_plan["task_id"] == "task_reentry_synthesis":
        (workspace_path / "adequacy_assessments.jsonl").write_text(
            json.dumps(
                {
                    "assessment_id": "adequacy_review_reentry",
                    "criterion": "adequacy_review_reentry",
                    "status": "partially_satisfied",
                    "evidence": ["reviews/review_001.json", "synthesis.md"],
                    "gaps": [
                        "Market/outlook framing remains constrained to admitted evidence."
                    ],
                    "follow_up_task": (
                        "Use the updated synthesis and report_outline as the "
                        "writer-facing surface and preserve this item as unresolved."
                    ),
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    return result


def fake_live_codex_runner_with_forbidden_reviewer_queue(
    *,
    role_plan: dict,
    prompt: str,
    workspace_path: Path,
    transcript_path: Path,
    last_message_path: Path,
    timeout_seconds: int,
) -> dict:
    result = fake_live_codex_runner(
        role_plan=role_plan,
        prompt=prompt,
        workspace_path=workspace_path,
        transcript_path=transcript_path,
        last_message_path=last_message_path,
        timeout_seconds=timeout_seconds,
    )
    if role_plan["task_id"] == "task_review":
        forbidden = workspace_path / "backpressure" / "adequacy_backpressure_queue.json"
        forbidden.parent.mkdir(parents=True, exist_ok=True)
        forbidden.write_text(
            json.dumps(
                {
                    "schema_version": "codex-dr.adequacy_backpressure_queue.v2",
                    "queue_status": "open",
                    "writer_blocked": True,
                    "items": [],
                    "quarantined_items": [],
                    "normalization_summary": {
                        "canonical_item_count": 0,
                        "review_proposed_item_count": 0,
                        "quarantined_review_proposal_count": 0,
                        "legacy_fields_normalized_by": "harness",
                    },
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    return result


def fake_live_codex_runner_with_forbidden_reentry_queue(
    *,
    role_plan: dict,
    prompt: str,
    workspace_path: Path,
    transcript_path: Path,
    last_message_path: Path,
    timeout_seconds: int,
) -> dict:
    result = fake_live_codex_runner(
        role_plan=role_plan,
        prompt=prompt,
        workspace_path=workspace_path,
        transcript_path=transcript_path,
        last_message_path=last_message_path,
        timeout_seconds=timeout_seconds,
    )
    if role_plan["task_id"] == "task_reentry_followup":
        forbidden = workspace_path / "backpressure" / "adequacy_backpressure_queue.json"
        forbidden.parent.mkdir(parents=True, exist_ok=True)
        forbidden.write_text(
            json.dumps(
                {
                    "schema_version": "codex-dr.adequacy_backpressure_queue.v2",
                    "queue_status": "open",
                    "writer_blocked": True,
                    "items": [],
                    "quarantined_items": [],
                    "normalization_summary": {
                        "canonical_item_count": 0,
                        "review_proposed_item_count": 0,
                        "quarantined_review_proposal_count": 0,
                        "legacy_fields_normalized_by": "harness",
                    },
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    return result


def fake_live_codex_runner_with_open_backpressure(
    *,
    role_plan: dict,
    prompt: str,
    workspace_path: Path,
    transcript_path: Path,
    last_message_path: Path,
    timeout_seconds: int,
) -> dict:
    result = fake_live_codex_runner(
        role_plan=role_plan,
        prompt=prompt,
        workspace_path=workspace_path,
        transcript_path=transcript_path,
        last_message_path=last_message_path,
        timeout_seconds=timeout_seconds,
    )
    if role_plan["task_id"] == "task_reentry_synthesis" or role_plan[
        "task_id"
    ].startswith("task_reentry_synthesis_"):
        (workspace_path / "adequacy_assessments.jsonl").write_text(
            json.dumps(
                {
                    "assessment_id": "adequacy_review_reentry",
                    "criterion": "adequacy_review_reentry",
                    "status": "not_satisfied_for_closure",
                    "evidence": ["reviews/review_001.json", "synthesis.md"],
                    "remaining_gap": (
                        "A narrow comparison table is still missing from admitted evidence."
                    ),
                    "recommended_follow_up": (
                        "Run one narrow re-entry comparison pass and return an "
                        "admitted normalization table."
                    ),
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    return result


def fake_live_codex_runner_with_recursive_reentry_closure(
    *,
    role_plan: dict,
    prompt: str,
    workspace_path: Path,
    transcript_path: Path,
    last_message_path: Path,
    timeout_seconds: int,
) -> dict:
    result = fake_live_codex_runner(
        role_plan=role_plan,
        prompt=prompt,
        workspace_path=workspace_path,
        transcript_path=transcript_path,
        last_message_path=last_message_path,
        timeout_seconds=timeout_seconds,
    )
    task_id = role_plan["task_id"]
    if task_id == "task_reentry_synthesis":
        (workspace_path / "adequacy_assessments.jsonl").write_text(
            json.dumps(
                {
                    "assessment_id": "adequacy_review_reentry",
                    "criterion": "adequacy_review_reentry",
                    "status": "not_satisfied_for_closure",
                    "evidence": ["reviews/review_001.json", "synthesis.md"],
                    "remaining_gap": (
                        "A narrow comparison table is still missing from admitted evidence."
                    ),
                    "recommended_follow_up": (
                        "Run one narrow re-entry comparison pass and return an "
                        "admitted normalization table."
                    ),
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    if task_id.startswith("task_reentry_synthesis_"):
        (workspace_path / "pointer_read_receipts.jsonl").write_text(
            "\n".join(
                json.dumps(
                    {
                        "branch_id": branch_id,
                        "pointer_path": f"branches/{branch_id}/pointer.md",
                        "pointer_read_before_analysis": True,
                        "selected_analysis_spans": [
                            {
                                "analysis_path": f"branches/{branch_id}/analysis.md",
                                "section_heading": "Recursive re-entry closure",
                            }
                        ],
                        "evidence_paths": [f"branches/{branch_id}/evidence.jsonl"],
                    },
                    sort_keys=True,
                )
                for branch_id in [
                    "deep_search",
                    "data_analysis",
                    "verification",
                    "reentry_followup",
                    "reentry_followup_002",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (workspace_path / "adequacy_assessments.jsonl").write_text(
            json.dumps(
                {
                    "assessment_id": "adequacy_review_reentry",
                    "criterion": "adequacy_review_reentry",
                    "status": "satisfied_for_live_stub",
                    "evidence": [
                        "branches/reentry_followup_002/evidence.jsonl",
                        "synthesis.md",
                    ],
                    "gaps": [],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    return result


def fake_unavailable_model_probe_runner(
    *,
    command,
    prompt,
    workspace_path,
    transcript_path,
    last_message_path,
    timeout_seconds,
):
    return {
        "returncode": 1,
        "stdout": "",
        "stderr": (
            "stream disconnected before completion: The model 'gpt-5.5' does not "
            "exist or you do not have access to it."
        ),
    }


def fake_available_model_probe_runner(
    *,
    command,
    prompt,
    workspace_path,
    transcript_path,
    last_message_path,
    timeout_seconds,
):
    return {
        "returncode": 0,
        "stdout": json.dumps({"type": "message", "model": command[4]}) + "\n",
        "stderr": "",
        "last_message": "codex-dr model probe ok\n",
    }


def prepare_deepresearch_bench_claim_review_run(tmp_path: Path, suffix: str):
    harness = load_harness()
    runs_dir = TEST_RUNS_ROOT / f"{tmp_path.name}-{suffix}"
    shutil.rmtree(runs_dir, ignore_errors=True)
    official_repo = tmp_path / f"official_deepresearch_bench_{suffix}"
    bridge_dir = tmp_path / f"race_bridge_{suffix}"
    query_jsonl = tmp_path / f"query_{suffix}.jsonl"
    source_refresh = tmp_path / f"deepresearch_bench_source_refresh_{suffix}.json"
    case_manifest = tmp_path / f"deepresearch_bench_case_spec_manifest_{suffix}.json"
    report_export = tmp_path / f"raw_generated_reports_{suffix}.jsonl"
    suite_id = f"deepresearch_bench_claim_suite_{suffix.replace('-', '_')}"
    run_id = f"{suite_id}_case_001"
    live_receipt = runs_dir / "live_control.json"
    write_deepresearch_bench_official_repo_fixture(official_repo)
    write_deepresearch_bench_query_jsonl(query_jsonl)
    write_deepresearch_bench_refresh(source_refresh)
    assert (
        harness.main(
            [
                "deepresearch-bench-case-manifest",
                "--query-jsonl",
                str(query_jsonl),
                "--source-refresh",
                str(source_refresh),
                "--output",
                str(case_manifest),
                "--limit",
                "2",
            ]
        )
        == 0
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "multi-case-from-manifest",
                suite_id,
                "--manifest",
                str(case_manifest),
            ]
        )
        == 0
    )
    write_live_execution_control_receipt(live_receipt, run_id)
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "mesh-live-plan",
                run_id,
                "--run-control",
                str(live_receipt),
            ]
        )
        == 0
    )
    harness.mesh_execute_live(
        run_id,
        run_control=live_receipt,
        runs_dir=runs_dir,
        codex_runner=fake_live_codex_runner,
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-report-export",
                run_id,
                "--output",
                str(report_export),
            ]
        )
        == 0
    )
    assert (
        harness.main(
            [
                "deepresearch-bench-race-bridge",
                "--raw-reports",
                str(report_export),
                "--source-refresh",
                str(source_refresh),
                "--official-repo",
                str(official_repo),
                "--output-dir",
                str(bridge_dir),
                "--model-name",
                f"codex-dr-{suffix}",
                "--limit",
                "1",
            ]
        )
        == 0
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-claim-review",
                run_id,
                "--race-bridge-receipt",
                str(bridge_dir / "race_bridge_receipt.json"),
                "--source-refresh",
                str(source_refresh),
            ]
        )
        == 0
    )
    return harness, runs_dir / run_id, runs_dir, run_id


def prepare_deepresearch_bench_subset_pressure(tmp_path: Path, suffix: str):
    harness = load_harness()
    runs_dir = TEST_RUNS_ROOT / f"{tmp_path.name}-{suffix}"
    shutil.rmtree(runs_dir, ignore_errors=True)
    official_repo = tmp_path / f"official_deepresearch_bench_{suffix}"
    query_jsonl = tmp_path / f"query_{suffix}.jsonl"
    source_refresh = tmp_path / f"deepresearch_bench_source_refresh_{suffix}.json"
    case_manifest = tmp_path / f"deepresearch_bench_case_spec_manifest_{suffix}.json"
    suite_id = f"deepresearch_bench_subset_{suffix.replace('-', '_')}"
    write_deepresearch_bench_official_repo_fixture(official_repo)
    write_deepresearch_bench_query_jsonl(query_jsonl)
    write_deepresearch_bench_refresh(source_refresh)
    assert (
        harness.main(
            [
                "deepresearch-bench-case-manifest",
                "--query-jsonl",
                str(query_jsonl),
                "--source-refresh",
                str(source_refresh),
                "--output",
                str(case_manifest),
                "--limit",
                "2",
            ]
        )
        == 0
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-subset-pressure",
                suite_id,
                "--manifest",
                str(case_manifest),
                "--source-refresh",
                str(source_refresh),
                "--official-repo",
                str(official_repo),
                "--limit",
                "2",
                "--force",
            ]
        )
        == 0
    )
    return harness, runs_dir / suite_id, runs_dir, suite_id


def write_deepresearch_bench_full_package_fixture(
    tmp_path: Path, harness, suite_dir: Path, suffix: str
) -> Path:
    official_repo = tmp_path / f"official_deepresearch_bench_full_{suffix}"
    source_refresh = tmp_path / f"deepresearch_bench_source_refresh_full_{suffix}.json"
    query_jsonl = tmp_path / f"query_100_{suffix}.jsonl"
    output_dir = tmp_path / f"full_run_package_{suffix}"
    write_deepresearch_bench_official_repo_fixture(official_repo)
    write_deepresearch_bench_refresh(source_refresh)
    write_deepresearch_bench_query_jsonl(query_jsonl, row_count=100)
    assert (
        harness.main(
            [
                "deepresearch-bench-full-run-package",
                f"deepresearch_bench_full_package_{suffix.replace('-', '_')}",
                "--query-jsonl",
                str(query_jsonl),
                "--source-refresh",
                str(source_refresh),
                "--subset-summary",
                str(suite_dir / "deepresearch_bench_subset_pressure_summary.json"),
                "--official-repo",
                str(official_repo),
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )
    return output_dir


def prepare_deepresearch_bench_flywheel_plan(tmp_path: Path, suffix: str):
    harness, _run_dir, runs_dir, run_id = prepare_deepresearch_bench_claim_review_run(
        tmp_path, suffix
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-improvement-compile",
                run_id,
            ]
        )
        == 0
    )
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-improvement-gate",
                run_id,
            ]
        )
        == 0
    )
    subset_harness, suite_dir, _subset_runs_dir, _suite_id = (
        prepare_deepresearch_bench_subset_pressure(tmp_path, f"{suffix}-subset")
    )
    package_dir = write_deepresearch_bench_full_package_fixture(
        tmp_path, subset_harness, suite_dir, suffix
    )
    output_dir = tmp_path / f"flywheel_plan_{suffix}"
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "deepresearch-bench-flywheel-plan",
                f"deepresearch_bench_flywheel_{suffix.replace('-', '_')}",
                "--case-id",
                run_id,
                "--subset-summary",
                str(suite_dir / "deepresearch_bench_subset_pressure_summary.json"),
                "--full-run-package",
                str(package_dir / "full_run_package.json"),
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )
    return harness, output_dir, runs_dir, run_id


def fresh_live_planned_mesh(tmp_path: Path):
    harness, run_dir, runs_dir = fresh_mesh_run(tmp_path)
    receipt_path = runs_dir / "dry_run_control.json"
    write_dry_run_control_receipt(receipt_path, "draco_mesh_fixture_001")
    result = harness.main(
        [
            "--runs-dir",
            str(runs_dir),
            "mesh-live-plan",
            "draco_mesh_fixture_001",
            "--run-control",
            str(receipt_path),
        ]
    )
    assert result == 0
    return harness, run_dir, runs_dir, receipt_path


def prepare_scored_live_mesh_inputs(tmp_path: Path):
    harness, run_dir, runs_dir, _dry_receipt = fresh_live_planned_mesh(tmp_path)
    live_receipt = runs_dir / "live_control.json"
    write_live_execution_control_receipt(live_receipt, "draco_mesh_fixture_001")
    assert (
        harness.main(
            [
                "--runs-dir",
                str(runs_dir),
                "mesh-live-plan",
                "draco_mesh_fixture_001",
                "--run-control",
                str(live_receipt),
            ]
        )
        == 0
    )
    harness.mesh_execute_live(
        "draco_mesh_fixture_001",
        run_control=live_receipt,
        runs_dir=runs_dir,
        codex_runner=fake_live_codex_runner,
    )
    manifest_path = run_dir / "scorer_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["scorer_status"] = "approved"
    manifest["scorer_available"] = True
    manifest["execution_allowed"] = True
    manifest["judge_policy"]["provider"] = "openai"
    manifest["judge_policy"]["model"] = "gpt-5"
    manifest["judge_policy"]["prompt_version"] = "draco-judge-v1"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    scorer_transcript = run_dir / "transcripts" / "scorer" / "judge_001.jsonl"
    scorer_transcript.parent.mkdir(parents=True, exist_ok=True)
    scorer_transcript.write_text(
        json.dumps({"criterion": "accuracy", "verdict": 0.9}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    evaluation_output = {
        "schema_version": "codex-dr.draco_evaluation_output.v1",
        "run_id": "draco_mesh_fixture_001",
        "benchmark_family": "DRACO",
        "case_id": "draco_tiny_smoke_row_0",
        "scorer_manifest": "scorer_manifest.json",
        "criterion_verdicts": [
            {
                "criterion_id": "criterion_accuracy",
                "criterion_group": "factual_accuracy",
                "weight": 0.6,
                "verdict": 0.9,
                "rationale": "Citations and branch evidence support the main answer.",
                "evidence_refs": [
                    "live_executor/role_outputs/task_deep_search/branches/deep_search/evidence.jsonl#ev_task_deep_search"
                ],
            },
            {
                "criterion_id": "criterion_verification",
                "criterion_group": "citation_quality",
                "weight": 0.4,
                "verdict": 0.75,
                "rationale": "Verification branch preserved source and claim boundaries.",
                "evidence_refs": [
                    "live_executor/role_outputs/task_verification/branches/verification/evidence.jsonl#ev_task_verification"
                ],
            },
        ],
        "raw_score": 0.84,
        "normalized_score": 0.84,
        "citations": [
            {
                "source_ref": (
                    "live_executor/role_outputs/task_deep_search/branches/deep_search/"
                    "evidence.jsonl#ev_task_deep_search"
                ),
                "supports": ["criterion_accuracy"],
            },
            {
                "source_ref": (
                    "live_executor/role_outputs/task_verification/branches/verification/"
                    "evidence.jsonl#ev_task_verification"
                ),
                "supports": ["criterion_verification"],
            },
        ],
        "judge_transcript_refs": ["transcripts/scorer/judge_001.jsonl"],
        "claim_boundary": {
            "allowed_claims_after_scoring": [
                "A scored evaluation artifact exists for this run."
            ],
            "blocked_claims_after_scoring": [
                "DRACO score",
                "Grep parity",
                "leaderboard rank",
                "product readiness",
            ],
        },
    }
    (run_dir / "draco_evaluation_output.json").write_text(
        json.dumps(evaluation_output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return harness, run_dir, runs_dir


def set_receipt_execution_approved(receipt_path: Path) -> None:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["approval"]["approved_for_execution"] = True
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def remove_receipt_transcript_root(receipt_path: Path) -> None:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["runner"].pop("transcript_root")
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def set_launch_plan_run_id(launch_plan_path: Path, run_id: str) -> None:
    launch_plan = json.loads(launch_plan_path.read_text(encoding="utf-8"))
    launch_plan["run_id"] = run_id
    launch_plan_path.write_text(
        json.dumps(launch_plan, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def remove_launch_plan_field(launch_plan_path: Path, field: str) -> None:
    launch_plan = json.loads(launch_plan_path.read_text(encoding="utf-8"))
    launch_plan["role_launch_plans"][0].pop(field, None)
    launch_plan_path.write_text(
        json.dumps(launch_plan, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def remove_scorer_manifest_field(manifest_path: Path, field: str) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop(field, None)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def remove_evaluation_ledger_field(ledger_path: Path, field: str) -> None:
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger.pop(field, None)
    ledger_path.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def set_evaluation_ledger_allows_claim_widening(ledger_path: Path) -> None:
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["allowed_claim_impact"]["may_widen_claims"] = True
    ledger["allowed_claim_impact"]["claim_gate_status"] = "open"
    ledger_path.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def add_draco_score_allowed_claim(allowed_claims_path: Path) -> None:
    allowed = json.loads(allowed_claims_path.read_text(encoding="utf-8"))
    allowed["allowed_claims"].append(
        {
            "claim": "Codex-DR has a DRACO score.",
            "scope": "invalid",
            "supporting_artifacts": ["benchmark_score.json"],
        }
    )
    allowed_claims_path.write_text(
        json.dumps(allowed, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def remove_failure_taxonomy_class(taxonomy_path: Path, class_id: str) -> None:
    taxonomy = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    taxonomy["failure_classes"] = [
        item for item in taxonomy["failure_classes"] if item.get("class_id") != class_id
    ]
    taxonomy_path.write_text(
        json.dumps(taxonomy, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def promote_improvement_proposal(proposal_path: Path) -> None:
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    proposal["promotion_status"] = "promoted"
    proposal["auto_promotion_allowed"] = True
    proposal_path.write_text(
        json.dumps(proposal, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def remove_replay_evaluation_failures(corpus_path: Path) -> None:
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    corpus["evaluation_failures"] = []
    corpus_path.write_text(json.dumps(corpus, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def remove_proposal_source_evaluation_failures(proposal_path: Path) -> None:
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    proposal["source_evaluation_failures"] = []
    proposal_path.write_text(
        json.dumps(proposal, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def remove_regression_evidence_requirement(regression_path: Path) -> None:
    regression = json.loads(regression_path.read_text(encoding="utf-8"))
    regression["regression_evidence_required_for_promotion"] = False
    regression_path.write_text(
        json.dumps(regression, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def allow_failed_replay_claim_widening(regression_path: Path) -> None:
    regression = json.loads(regression_path.read_text(encoding="utf-8"))
    regression["failed_cases_cannot_widen_claims"] = False
    regression_path.write_text(
        json.dumps(regression, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def set_benchmark_score(score_path: Path) -> None:
    score = json.loads(score_path.read_text(encoding="utf-8"))
    score["score"] = 0.99
    score_path.write_text(json.dumps(score, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def add_widened_allowed_claim(allowed_claims_path: Path) -> None:
    allowed = json.loads(allowed_claims_path.read_text(encoding="utf-8"))
    allowed["allowed_claims"].append(
        {
            "claim": "Codex-DR has achieved Grep parity.",
            "scope": "invalid",
            "supporting_artifacts": [],
        }
    )
    allowed_claims_path.write_text(
        json.dumps(allowed, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
