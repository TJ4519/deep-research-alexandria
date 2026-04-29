# DeepResearch Bench II Shadow Probe Summary

Generated: 2026-04-30 00:09:55 BST

## Purpose

This file records a local Codex preflight run against one DeepResearch Bench II task. It exists to test whether DRB II can be used as a practical diagnostic lane for the Codex-DR mesh without confusing that lane with official Grep parity scoring.

## Benchmark Position

DeepResearch Bench II is useful for diagnostic pressure because it evaluates long-form deep-research reports against fine-grained rubrics across information recall, analysis, and presentation. It is not a Grep-parity gate unless Grep has a comparable DeepResearch Bench II score, or unless Grep is rerun under the same task set, evaluator, judge model, and submission protocol.

The current Grep-parity gate remains the original DeepResearch Bench lane already recorded in the sandbox runway: same public leaderboard/evaluator lane, same report-output protocol, official scorer custody, and the refreshed Grep-v5 comparison target.

## Probe

- Benchmark family: DeepResearch Bench II
- Task index: 73
- Task id: `task28+`
- Theme: Health
- Language: Chinese
- Task description: `A Survey of Knowledge Graphs for Drug Repurposing`
- Rubrics: 78 information-recall, 8 analysis, 5 presentation, 91 total

## Artifacts

- Candidate report: `sandbox/codex-dr/tmp/deepresearch_bench_ii_shadow_2026_04_30/workspace/idx-73.md`
- Self audit: `sandbox/codex-dr/tmp/deepresearch_bench_ii_shadow_2026_04_30/workspace/self_audit.json`
- Codex shadow eval: `sandbox/codex-dr/tmp/deepresearch_bench_ii_shadow_2026_04_30/codex_shadow_eval.json`
- Official DRB II clone: `sandbox/codex-dr/tmp/deepresearch_bench_ii_official`

## Codex Shadow Result

This is a non-official Codex shadow rubric diagnostic.

| Dimension | Hits | Total | Ratio |
|---|---:|---:|---:|
| Information recall | 46 | 78 | 0.5897 |
| Analysis | 0 | 8 | 0.0000 |
| Presentation | 5 | 5 | 1.0000 |
| Overall | 51 | 91 | 0.5604 |

The main failure signal is clear: the generated report did a reasonable first-pass collection job and presented it cleanly, but it did not satisfy the analysis rubrics. The next improvement should force explicit synthesis over KG scale, entity-type commonality, graph evolution, drug-combination specialization, and KG methodology implications.

## Blocked Source Scan

A blocked-source scan found no blocked-source terms in the candidate report or shadow evaluation. The candidate self-audit also states that the blocked review article was surfaced during search but was not opened, cited, quoted, paraphrased, or used as authority.

## Claim Boundary

This run does not prove DeepResearch Bench II performance, Grep parity, leaderboard rank, product readiness, or research quality. It proves only that the sandbox can import a DRB II task, generate a candidate report with Codex, and run a bounded Codex shadow evaluation against the task rubrics.

## Candidate Next Step

Use DRB II as a shadow improvement lane: run a mesh-generated report, score with Codex shadow rubrics, patch prompts or skills against concrete misses, rerun the same task, then graduate to the official DRB II Gemini scorer only when credentials and run-control authority exist.
