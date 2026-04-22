# Boxed Recursive Smoke Preflight

Status: stopped before provider-backed execution
Date: 2026-04-22
Bead: `alexandriacleanroom-91.1.5.4`
Run id: `draco_smoke_001`

## Purpose

Attempt the first safe preflight for the boxed Codex recursive DRACO smoke run
after runner probe, DRACO case manifest, and run-specific token manifest were
created.

This preflight did not start a provider/model-backed Codex run and did not
execute a benchmark.

## Gates Checked

| Gate | Status | Evidence |
| --- | --- | --- |
| Boxed runner command surface | available | `sandbox/codex-dr/docs/boxed_codex_runner_capability_probe_2026_04_22.md` records `codex exec` availability. |
| Transcript wrapper | available | `/usr/bin/script` captured a harmless `codex --version` transcript under ignored `sandbox/codex-dr/tmp/`. |
| DRACO tiny smoke case manifest | available | `sandbox/codex-dr/benchmark-manifests/draco_tiny_smoke_case_manifest.md`. |
| Run-specific token manifest | available | `sandbox/codex-dr/harness-specs/draco_smoke_001_token_manifest.yaml`. |
| Mechanical token/cost cap enforcement | blocked | `codex exec --help` exposes `--model`, `--sandbox`, `--json`, and `--output-last-message`, but no `max_tokens`, `max_cost`, or equivalent budget cap option. |

## Commands Used For This Preflight

```text
codex exec --help
rg -n "max_|token|cost|budget|output-last-message|json|model|sandbox" <(codex exec --help)
```

Observed relevant options:

- `--model`
- `--sandbox`
- `--json`
- `--output-last-message`
- `--cd`
- `--config`

No mechanical token or cost cap flag was observed.

## Exact Blocker

The token manifest has a hard stop:

```yaml
hard_stop:
  - budget cap cannot be enforced or monitored
```

The manifest also caps:

```yaml
max_total_tokens: 42000
max_provider_cost_usd: 1.00
max_attempts: 1
```

The available `codex exec` command surface does not expose a mechanical
`max_total_tokens` or `max_provider_cost_usd` control. A prompt-level
instruction would not be a reliable enforcement mechanism. Launching the
boxed run now would violate the manifest's hard-stop rule.

Therefore the boxed recursive smoke run is blocked before spend by budget-cap
enforcement ambiguity.

## Next Command If Principal/Main Coordinator Waives This Blocker

Only run after one of these is true:

- a Codex CLI budget/cost cap mechanism is identified; or
- the Principal/main coordinator explicitly waives mechanical budget-cap
  enforcement for this one smoke run and accepts the manifest's prompt-level
  stop rules plus one-attempt transcript capture.

Candidate command shape after waiver or cap mechanism:

```text
mkdir -p sandbox/codex-dr/runs/draco_smoke_001/transcripts \
  sandbox/codex-dr/runs/draco_smoke_001/last_messages

script -q sandbox/codex-dr/runs/draco_smoke_001/transcripts/codex_exec_planner.txt \
  codex exec \
  --cd sandbox/codex-dr \
  --sandbox workspace-write \
  --ask-for-approval never \
  --output-last-message sandbox/codex-dr/runs/draco_smoke_001/last_messages/planner.md \
  "<bounded DRACO smoke prompt from draco_smoke_001_token_manifest.yaml>"
```

## Claims

Permitted:

- Runner, transcript, case manifest, and token manifest gates exist.
- The boxed recursive smoke run was stopped before spend because the current
  Codex CLI surface did not show mechanical token/cost cap enforcement.

Blocked:

- A real boxed Codex recursive research smoke run happened.
- Any model/provider-backed call occurred.
- DRACO execution or scoring occurred.
- Grep parity, benchmark score, leaderboard rank, or product readiness.
