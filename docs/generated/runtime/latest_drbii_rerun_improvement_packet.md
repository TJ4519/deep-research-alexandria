# DRB II Rerun Improvement Packet

Generated: 2026-04-30

## Summary

The rubric-aware rerun repaired the main failure: analysis moved from 0/8 to 8/8 and overall shadow hits moved from 51/91 to 84/91. The remaining failures are seven information-recall items requiring explicit wording or source reconciliation.

## Remaining Failures

- `info_recall_01`: 在介绍OREGANO时，明确指出其数据来源包含约10个精选数据库和本体，如DrugBank、Uniprot、REACTOME和HPO。
- `info_recall_10`: 在介绍HetioNet时，明确指出其可通过Neo4j服务器访问。
- `info_recall_12`: 在介绍PharMeBINet时，明确指出其节点类型从11种扩展到66种。
- `info_recall_13`: 在介绍PharMeBINet时，明确指出其边类型从24种增加到208种。
- `info_recall_15`: 在介绍Multiscale Interactome (MSI)时，明确指出其数据来自约14个精选数据源，包括DrugBank和PsyGeNET等。
- `info_recall_19`: 在介绍BioKG时，明确指出其数据来源包括DrugBank, UniProt, 和KEGG等18个数据源。
- `info_recall_21`: 在介绍NeDRexDB时，明确指出它是通过众包框架（crowdsourcing framework）整合10个源数据库的数据构建的。

## Next Candidate

- Candidate: `cand_drbii_task73_explicit_recall_closure_001`
- Target surface: generator prompt/report checklist for DRB II task 73 shadow lane
- Expected effect: close seven remaining information-recall misses while preserving 8/8 analysis and 5/5 presentation
- Validation gate: rerun Codex shadow evaluator; require >84/91 or a narrower blocker; no official score or parity claim

## Claim Boundary

non-official Codex shadow rubric diagnostic; not official DRB II score, Grep parity, leaderboard rank, product readiness, or research-quality proof
