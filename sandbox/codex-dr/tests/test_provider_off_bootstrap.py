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


def failed_check_ids(report: dict) -> set[str]:
    return {check["check_id"] for check in report["checks"] if check["status"] == "failed"}


def test_provider_off_bootstrap_run_validates(tmp_path: Path):
    harness, run_dir, runs_dir = fresh_run(tmp_path)

    report = harness.validate_run("local_fixture_001", runs_dir=runs_dir)

    assert report["status"] == "passed"
    assert (run_dir / "validation_report.json").exists()
    assert report["failed_checks"] == []


@pytest.mark.parametrize(
    "args",
    [
        ["run-planner", "local_fixture_001", "--token-manifest", "missing.yaml"],
        [
            "run-branch",
            "local_fixture_001",
            "branch_a",
            "--token-manifest",
            "missing.yaml",
        ],
        ["run-review", "local_fixture_001", "--token-manifest", "missing.yaml"],
        [
            "run-reentry",
            "local_fixture_001",
            "review_001",
            "--token-manifest",
            "missing.yaml",
        ],
        ["score", "local_fixture_001", "--token-manifest", "missing.yaml"],
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
