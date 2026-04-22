# DRACO Tiny Smoke Case Manifest

Status: pointer-only case manifest
Date: 2026-04-22
Bead: `alexandriacleanroom-91.1.5.2`
Purpose: prepare the smallest benchmark-facing DRACO smoke input for boxed
Codex recursive research without committing raw benchmark data.

## Source

| Field | Value |
| --- | --- |
| Benchmark | DRACO |
| Canonical paper | https://arxiv.org/abs/2602.11685 |
| Dataset URL | https://huggingface.co/datasets/perplexity-ai/draco |
| HF dataset id | `perplexity-ai/draco` |
| HF commit SHA | `ce076749809027649ebd331bcb70f42bf720d387` |
| Last modified | `2026-02-20T23:02:24.000Z` |
| License observed | `mit` |
| Access observed | public, ungated |
| Data file selected | `test.jsonl` |
| Data file oid observed | `0d146672ce72278415f66eaf0985854dbf7ae8d5` |
| Data file size observed | `909190` bytes |
| Case count from audit | 100 test rows across 10 domains |

Source facts are copied from
`sandbox/codex-dr/benchmark-manifests/benchmark_acquisition_audit.md` and a
public Hugging Face metadata probe. The raw dataset was not committed.

## Smoke Selection

```yaml
manifest_id: draco_tiny_smoke_001
benchmark_family: DRACO
dataset_id: perplexity-ai/draco
dataset_commit: ce076749809027649ebd331bcb70f42bf720d387
split: test
source_file: test.jsonl
selection:
  method: first-row-pointer
  row_indices: [0]
  case_ids:
    - draco_test_row_000
raw_data_in_git: false
allowed_local_cache:
  root: sandbox/codex-dr/tmp/draco_tiny_smoke_001/
  ignored_by_git: true
future_run_bundle:
  root: sandbox/codex-dr/runs/draco_smoke_001/
```

This manifest deliberately selects by dataset commit, file, and row pointer
rather than embedding the prompt, rubric, or criteria in git. A future execution
bead may fetch only this row into the ignored cache path, then copy the
execution-specific case payload into the ignored run bundle.

## Fetch Command For Future Execution

Do not run this as benchmark execution. It only fetches the public dataset file
into ignored scratch space for the future smoke runner:

```text
mkdir -p sandbox/codex-dr/tmp/draco_tiny_smoke_001
curl -L \
  https://huggingface.co/datasets/perplexity-ai/draco/resolve/ce076749809027649ebd331bcb70f42bf720d387/test.jsonl \
  -o sandbox/codex-dr/tmp/draco_tiny_smoke_001/test.jsonl
```

Future smoke selection should read only row `0` from that ignored local file.

## Evaluator Shape

DRACO uses long-form answers judged against task-specific rubrics across:

- factual accuracy;
- breadth and depth;
- presentation quality;
- citation quality.

The acquisition audit records that the HF card describes about 40 criteria per
task and 3,934 criteria across all tasks.

## Non-Authorization

This manifest does not authorize:

- benchmark execution;
- model/provider calls;
- judge/scorer calls;
- numeric DRACO scores;
- Grep parity or leaderboard claims.

It only authorizes future work to use the selected source pointer when a
run-control receipt and boxed-run custody path exist.

## Red/Green Result

Red before this file:

- no DRACO smoke case pointer existed;
- the boxed smoke runner had no benchmark-facing case identity.

Green after this file:

- one tiny DRACO smoke pointer exists;
- source URL, commit, license, access, data file, and row pointer are recorded;
- raw/full benchmark data remains out of git.
