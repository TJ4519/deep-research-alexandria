# DRB II Task 73 Rubric Execution Packet

Generated for bead `alexandriacleanroom-99.26`.

## Purpose

This packet converts the DRB II task-73 shadow failure into a rubric-led execution surface for the next run. The prior report collected and presented facts but failed all analysis rubrics, so the next run must treat analysis and exact-fact reconciliation as pre-writing adequacy criteria.

## Claim Boundary

Local Codex shadow diagnostic only; not official DRB II score, not Grep parity, not leaderboard rank, not product readiness, not official submission.

## Baseline

| Dimension | Hits | Total | Ratio |
|---|---:|---:|---:|
| info_recall | 46 | 78 | 0.5897 |
| analysis | 0 | 8 | 0.0000 |
| presentation | 5 | 5 | 1.0000 |
| overall | 51 | 91 | 0.5604 |

## Required Next-Run Artifacts

- before_generation: `run_control_receipt.json`, `execution_packet.json`, `generator_prompt.md`
- during_generation: `search_log.jsonl`, `source_claim_map.json`, `draft_report.md`
- after_generation: `idx-73.md`, `self_audit.json`, `blocked_source_scan.txt`, `shadow_evaluator_prompt.md`, `codex_shadow_eval.json`, `rerun_summary.md`

## Analysis Checklist

- `analysis_00`: 解释了CKG是药物重用领域内规模最庞大的知识图谱之一。
- `analysis_01`: 解释了PharMeBINet是HetioNet的显著演进版本，并量化了其增长（例如，节点数增长61倍，关系数增长7倍）。
- `analysis_02`: 在介绍DrugCombDB时，能够分析并指出其独特之处在于专注于“药物组合”而非单个药物的治疗方案。
- `analysis_03`: 在介绍KEGG时，能够解释其节点和边数量不固定的原因是其“每日更新”的动态特性。
- `analysis_04`: 在介绍BioKG时，能够分析并指出其包含“映射模块”是其关键优势，因为它提升了与其他知识图谱的互操作性。
- `analysis_05`: 在介绍NeDRexDB时，能够分析其构建方法（众包）和使用本体（Monarch Disease Ontology）是为了解决跨数据源的数据整合与一致性问题。
- `analysis_06`: 能够总结出不同知识图谱之间存在数据来源重叠的现象，并举例说明，如DrugBank被多个KG使用。
- `analysis_07`: 能够总结出“药物”、“基因”、“疾病”是绝大多数用于药物重用的知识图谱中都包含的核心实体类型。

## Exact Fact Ledger

| KG | Nodes | Edges | Node Types | Edge Types | Last Update |
|---|---:|---:|---:|---:|---|
| OREGANO | 88,937 | 824,231 | 12 | 19 | 10 Nov 2023 |
| CKG | 16 million | 220 million | 19 | 57 | 17 Aug 2021 |
| PrimeKG | 129,375 | 4,050,249 | 10 | 30 | 25 Apr 2022 |
| PharMeBINet | 2,869,407 | 15,883,653 | 66 | 208 | 5 Jan 2024 |
| MSI | 29,959 | 478,728 | 4 | 5 | 19 Mar 2021 |
| HetioNet | 47,031 | 2,250,197 | 11 | 24 | 12 Apr 2016 |
| DRKG | 97,238 | 5,874,261 | 13 | 17 | 4 May 2020 |
| BioKG | 11,479,285 | 42,504,077 | 12 | 52 | 21 Mar 2024 |
| KEGG | daily update or equivalent | daily update or equivalent | 5 | 10 | daily update or equivalent |
| DrugCombDB | 3,011 | 6,891,566 | 2 | 1 | 31 May 2019 |
| NeDRex | 278,826 | 2,327,974 | 6 | 12 | 25 Nov 2021 |

## Completion Gate

- Persist generator and evaluator prompts.
- Score all 91 rubrics in the Codex shadow evaluator.
- Improve analysis above `0/8` or record a narrower blocker.
- Preserve blocked-source discipline.
- Keep official score, Grep parity, leaderboard, product-readiness, and official-submission claims blocked.
