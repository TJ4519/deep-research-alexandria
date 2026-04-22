# Boxed Codex Runner Capability Probe

Status: completed local capability probe
Date: 2026-04-22
Bead: `alexandriacleanroom-91.1.5.1`
Scope: harmless local CLI/help/version probe only

## Purpose

Determine whether this sandbox has a local Codex/terminal-agent box launch
surface and a transcript-capture path suitable for the corrected boxed Codex
DRACO smoke runway.

This probe did not start provider-backed research, did not call a model, and
did not execute a benchmark.

## Commands Attempted

All commands were run from:

```text
/Users/singh/Desktop/alexandria_cleanroom/sandbox/codex-dr
```

| Command | Result | Meaning |
| --- | --- | --- |
| `command -v codex` | exit 0, `/usr/local/bin/codex` | Codex CLI is installed. |
| `codex --version` | exit 0, `codex-cli 0.120.0` | CLI version is discoverable without a model call. |
| `codex --help` | exit 0 | Top-level CLI exposes `exec`, `review`, `resume`, `fork`, `sandbox`, and related commands. |
| `codex exec --help` | exit 0 | Non-interactive Codex execution surface exists. Options include `--cd`, `--sandbox`, `--json`, and `--output-last-message`. |
| `command -v script` | exit 0, `/usr/bin/script` | Local terminal transcript wrapper is available. |
| `mkdir -p tmp/boxed_runner_probe && script -q tmp/boxed_runner_probe/codex_version_transcript.txt codex --version` | exit 0 | Transcript capture works for a harmless local Codex CLI command. |
| `git check-ignore -v sandbox/codex-dr/tmp/boxed_runner_probe/codex_version_transcript.txt` | exit 0 | Probe transcript path is ignored by git through `sandbox/codex-dr/tmp/*`. |
| `codex sandbox --help` | exit 0 | Codex-provided sandbox command surface exists for local command sandboxing. |
| `codex features --help` | exit 0 | Feature inspection command surface exists. |

## Codex Box Launch Availability

Available as a command surface, not yet executed as a provider-backed research
run.

The local CLI supports:

```text
codex exec [OPTIONS] [PROMPT]
```

The probe establishes that a future bead can attempt a boxed Codex execution
through `codex exec` after a run-control receipt exists. This probe does
not prove model credentials, run discipline, or research quality, because no
provider-backed `codex exec` prompt was run.

## Transcript Capture Path

Transcript capture is available through `/usr/bin/script`.

Observed ignored transcript path:

```text
sandbox/codex-dr/tmp/boxed_runner_probe/codex_version_transcript.txt
```

Recommended smoke-run transcript root:

```text
sandbox/codex-dr/runs/draco_smoke_001/transcripts/
```

Recommended wrapper shape after run-control approval:

```text
script -q sandbox/codex-dr/runs/draco_smoke_001/transcripts/codex_exec_planner.txt \
  codex exec \
  --cd sandbox/codex-dr \
  --sandbox workspace-write \
  --ask-for-approval never \
  --output-last-message sandbox/codex-dr/runs/draco_smoke_001/planner_last_message.md \
  "<bounded smoke prompt from run-control receipt and case manifest>"
```

The exact prompt, model/profile, stop rules, transcript path, output contract,
wall-clock bound, kill path, and claim boundary must come from the run-control
receipt. Do not use this command before that gate.

## Next Command If Available

The next safe, unblocked command is not a provider-backed launch. It is the
DRACO smoke manifest bead:

```text
bd --no-daemon show alexandriacleanroom-91.1.5.2
```

After the DRACO manifest and run-control receipt exist, the first candidate boxed run
command should use the transcript wrapper above, with the manifest-owned prompt
and caps.

## Exact Blocker

No local CLI blocker was found for the command surface or transcript wrapper.

The remaining blocker for actual boxed Codex research execution is governance
and live-run control, not local CLI availability:

- no run-control receipt exists yet;
- no DRACO tiny smoke case manifest exists yet;
- no scorer bridge exists yet;
- no provider/model-backed `codex exec` run was authorized or attempted by this
  probe.

## Claims

Permitted:

- Codex CLI `0.120.0` is installed.
- `codex exec` is available as a non-interactive execution command surface.
- `/usr/bin/script` can capture a local Codex CLI command transcript under an
  ignored sandbox path.

Blocked:

- A real boxed Codex recursive research run has happened.
- Model/provider credentials are valid.
- DRACO execution or scoring has happened.
- Grep parity, benchmark score, leaderboard rank, or product readiness.
