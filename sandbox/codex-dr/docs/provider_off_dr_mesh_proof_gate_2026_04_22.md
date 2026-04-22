# Provider-Off DR Mesh Proof Gate

Status: completed provider-off proof gate
Date: 2026-04-22
Bead: `alexandriacleanroom-91.1.5.8`

## Completion Object

The provider-off DR mesh topology is now a proof gate, not only an
implementation detail.

This receipt records the exact generated runs, commands, validators, proof
ceiling, blocked claims, invalid success conditions, and next live-run
preconditions.

## Intended Object

The intended object is the Codex-DR mesh: a Grep-style recursive deep-research
agent topology validated through Codex CLI harnessing.

The provider-off gate preserves the same topology without launching Codex:

- planner;
- task graph;
- scoped branch roles;
- pointer / analysis / evidence returns;
- pointer-first context economy;
- evaluate/synthesize inner loop;
- reviewer-driven re-entry;
- one-writer report;
- scorer bridge placeholder;
- event, artifact, compaction, claim, and allowed-claims custody.

## Commands Run

One-shot provider-off mesh run:

```bash
rm -rf sandbox/codex-dr/tmp/proof-gate-one-shot sandbox/codex-dr/tmp/proof-gate-staged
uv run python sandbox/codex-dr/tools/alexandria_dr.py --runs-dir sandbox/codex-dr/tmp/proof-gate-one-shot mesh-bootstrap-run dr_mesh_proof_one_shot_001
uv run python sandbox/codex-dr/tools/alexandria_dr.py --runs-dir sandbox/codex-dr/tmp/proof-gate-one-shot validate dr_mesh_proof_one_shot_001
```

Staged provider-off mesh run:

```bash
uv run python sandbox/codex-dr/tools/alexandria_dr.py --runs-dir sandbox/codex-dr/tmp/proof-gate-staged mesh-init-case dr_mesh_proof_staged_001 --force
uv run python sandbox/codex-dr/tools/alexandria_dr.py --runs-dir sandbox/codex-dr/tmp/proof-gate-staged mesh-plan dr_mesh_proof_staged_001
uv run python sandbox/codex-dr/tools/alexandria_dr.py --runs-dir sandbox/codex-dr/tmp/proof-gate-staged mesh-branch dr_mesh_proof_staged_001 deep_search
uv run python sandbox/codex-dr/tools/alexandria_dr.py --runs-dir sandbox/codex-dr/tmp/proof-gate-staged mesh-branch dr_mesh_proof_staged_001 data_analysis
uv run python sandbox/codex-dr/tools/alexandria_dr.py --runs-dir sandbox/codex-dr/tmp/proof-gate-staged mesh-branch dr_mesh_proof_staged_001 verification
uv run python sandbox/codex-dr/tools/alexandria_dr.py --runs-dir sandbox/codex-dr/tmp/proof-gate-staged mesh-evaluate dr_mesh_proof_staged_001
uv run python sandbox/codex-dr/tools/alexandria_dr.py --runs-dir sandbox/codex-dr/tmp/proof-gate-staged mesh-review dr_mesh_proof_staged_001
uv run python sandbox/codex-dr/tools/alexandria_dr.py --runs-dir sandbox/codex-dr/tmp/proof-gate-staged mesh-reentry dr_mesh_proof_staged_001 review_001
uv run python sandbox/codex-dr/tools/alexandria_dr.py --runs-dir sandbox/codex-dr/tmp/proof-gate-staged mesh-report dr_mesh_proof_staged_001
uv run python sandbox/codex-dr/tools/alexandria_dr.py --runs-dir sandbox/codex-dr/tmp/proof-gate-staged mesh-score dr_mesh_proof_staged_001
uv run python sandbox/codex-dr/tools/alexandria_dr.py --runs-dir sandbox/codex-dr/tmp/proof-gate-staged validate dr_mesh_proof_staged_001
```

## Validation Result

Both generated runs wrote validation reports with:

```json
{
  "status": "passed",
  "failed_checks": []
}
```

Validated check classes:

- required files present;
- required event types present;
- causal event chain connected;
- artifact manifest hashes and produced-by custody match;
- branch pointer / analysis / evidence triplets present;
- task graph dependencies valid;
- pointer-first receipts present;
- adequacy criteria mapped to validators;
- review finding compiled into re-entry task;
- compaction receipt present;
- benchmark placeholder is not a score;
- report claims are represented in the claim ledger;
- allowed claims remain provider-off scoped;
- no forbidden provider artifacts are present;
- generated path is under ignored sandbox `runs/` or `tmp/`.

## Negative Tests

`uv run pytest sandbox/codex-dr/tests/test_provider_off_bootstrap.py -q`
passed after covering mutations for:

- missing branch triplet;
- invalid task dependency;
- missing pointer-first receipt;
- missing review re-entry;
- scorer placeholder turned into a score;
- allowed-claim widening;
- missing event/artifact custody;
- artifact hash mismatch.

## Proof Ceiling

Permitted claim:

- The provider-off DR mesh topology can emit and validate deterministic local
  run bundles that preserve the Grep-shaped loop interfaces and custody
  surfaces.

This is topology proof for the harness only.

## Blocked Claims

These remain blocked:

- Grep parity;
- DRACO score;
- leaderboard rank;
- provider-backed research quality;
- product readiness;
- service-runtime maturity;
- benchmark execution success.

## Invalid Success Conditions

Do not count any of these as completion:

- a provider-off bundle described as a real research result;
- a scorer placeholder described as a score;
- fake role adapters described as Codex CLI execution;
- a report file without task graph, branch returns, synthesis, review,
  re-entry, claim ledger, and allowed claims;
- launch-control docs with no role-adapter execution surface;
- product-service readiness inferred from sandbox custody.

## Next Live-Run Preconditions

A future live Codex CLI mesh run still requires:

- Principal authorization for a named run;
- run-control receipt;
- foreground supervision or external monitoring;
- wall-clock bound;
- kill path;
- transcript capture policy;
- generated-output path policy;
- case manifest;
- scorer status or scorer manifest;
- allowed-claims and blocked-claims policy;
- no automatic retry unless separately approved.

No live command is authorized by this receipt.
