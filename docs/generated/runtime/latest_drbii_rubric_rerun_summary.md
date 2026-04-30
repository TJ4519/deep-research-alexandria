# DRB II Rubric-Aware Rerun Summary

Generated: 2026-04-30

## Claim Boundary

non-official Codex shadow rubric diagnostic; not official DRB II score, Grep parity, leaderboard rank, product readiness, or research-quality proof

## Result

| Dimension | Baseline | Rerun | Delta |
|---|---:|---:|---:|
| info_recall | 46/78 (0.5897) | 71/78 (0.9103) | +25 |
| analysis | 0/8 (0.0000) | 8/8 (1.0000) | +8 |
| presentation | 5/5 (1.0000) | 5/5 (1.0000) | +0 |
| overall | 51/91 (0.5604) | 84/91 (0.9231) | +33 |

## Remaining Failures

- Information recall failure indices: `1, 10, 12, 13, 15, 19, 21`
- Analysis failures: none in the Codex shadow eval.
- Presentation failures: none in the Codex shadow eval.

## Artifacts

- `sandbox/codex-dr/tmp/drbii_task73_rubric_rerun_2026_04_30/codex_shadow_eval.json`
- `sandbox/codex-dr/tmp/drbii_task73_rubric_rerun_2026_04_30/execution_packet.json`
- `sandbox/codex-dr/tmp/drbii_task73_rubric_rerun_2026_04_30/generator_prompt.md`
- `sandbox/codex-dr/tmp/drbii_task73_rubric_rerun_2026_04_30/run_control_receipt.json`
- `sandbox/codex-dr/tmp/drbii_task73_rubric_rerun_2026_04_30/shadow_evaluator_prompt.md`
- `sandbox/codex-dr/tmp/drbii_task73_rubric_rerun_2026_04_30/shadow_evaluator_prompt_strict.md`
- `sandbox/codex-dr/tmp/drbii_task73_rubric_rerun_2026_04_30/workspace/draft_report.md`
- `sandbox/codex-dr/tmp/drbii_task73_rubric_rerun_2026_04_30/workspace/idx-73.md`
- `sandbox/codex-dr/tmp/drbii_task73_rubric_rerun_2026_04_30/workspace/search_log.jsonl`
- `sandbox/codex-dr/tmp/drbii_task73_rubric_rerun_2026_04_30/workspace/self_audit.json`
- `sandbox/codex-dr/tmp/drbii_task73_rubric_rerun_2026_04_30/workspace/source_claim_map.json`

## Blocked Source Scan

Blocked source terms appear only in `self_audit.json` and `search_log.jsonl` as recorded encounters. They do not appear in the report or source-claim map.

## Interpretation

The repair worked for the diagnosed root cause. The previous failure was the absence of rubric-led analysis and exact-fact pressure before writing. The rerun satisfied all eight analysis rubrics and improved overall shadow rubric hits from 51/91 to 84/91. The remaining work is now narrower: seven information-recall misses that require explicit wording or source reconciliation, not a general synthesis failure.
