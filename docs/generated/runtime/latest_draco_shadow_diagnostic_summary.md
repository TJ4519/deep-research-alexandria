# DRACO Shadow Diagnostic Summary

Run: `draco_shadow_048_20260429_case_001`

Prompt row: DRACO row 48, pharma cold-chain procurement comparison.

Result: `blocked_by_adequacy_backpressure`. The final writer was blocked by open adequacy backpressure, so this is not scoreable and does not support an official DRACO score.

## Rubric Surface

- Criteria: 54
- Total rubric weight: 358.0
- Sections: factual-accuracy, breadth-and-depth-of-analysis, presentation-quality, citation-quality

## Open Writer-Blocking Gaps

- `review_001_procurement_comparison_gap` (non_comparable_inputs): The synthesis cannot support a procurement-grade comparison or ranking of Thermo King, Carrier Transicold, and off-grid alternatives for the West Africa vaccine cold-chain case.
- `review_001_cost_per_dose_gap` (numerical_support_gap): The current evidence does not provide capex, opex, utilization, route, dose-volume, wastage, maintenance, monitoring subscription, fuel or energy, or throughput inputs sufficient to calculate total cost per vaccine dose delivered.
- `review_001_run_custody_claim_gap` (provenance_gap): Branch evidence proves a planned case and manifest custody, but not completed live Codex CLI mesh execution with transcript, artifact, event, and claim custody.

## Validation

Validation status: `failed`.

Failed checks: branch_triplets_present, reentry_synthesis_outputs_valid, citation_support_maps_valid.

## Claim Boundary

Allowed: the run exercised the live Codex CLI mesh on one selected DRACO prompt until harness backpressure blocked the writer.

Blocked: DRACO score, Grep parity, leaderboard rank, product readiness, official benchmark submission, scorer-backed evaluation.
