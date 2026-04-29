# DRACO Shadow Baseline Comparison

Case: `draco_test_row_048`

This is a shadow diagnostic comparison. It is not an official DRACO score.

## Baseline

- Status: `completed`
- Prompt facet coverage: `1.0`
- Citations detected: `28`

## Mesh

- Execution status: `blocked_by_adequacy_backpressure`
- Roles completed: `10`
- Recursive re-entry rounds: `1`
- Writer blocked: `True`
- Open backpressure items: `3`
- Validation status: `failed`

## Interpretation

The single-pass baseline produces an answer surface, while the mesh currently proves topology and backpressure behavior but blocks final writing on unresolved adequacy gaps.

## Next Work

- Normalize live citation-support and adequacy-delta statuses so validation can pass.
- Close procurement comparison and cost-per-dose evidence gaps before final writer.
- Only then run scorer-backed DRACO evaluation or DeepResearch Bench scoring.

## Claim Boundary

Blocked: DRACO score, Grep parity, leaderboard rank, product readiness, official benchmark submission.
