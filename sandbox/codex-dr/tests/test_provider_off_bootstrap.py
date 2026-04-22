from __future__ import annotations

import importlib.util
import json
import shutil
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
    ]

    for command in commands:
        assert harness.main(["--runs-dir", str(runs_dir), *command]) == 0

    report = harness.validate_run(case_id, runs_dir=runs_dir)

    assert report["status"] == "passed"
    assert report["failed_checks"] == []


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
            lambda run_dir: add_widened_allowed_claim(run_dir / "allowed_claims.json"),
            "allowed_claims_scope_enforced",
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
