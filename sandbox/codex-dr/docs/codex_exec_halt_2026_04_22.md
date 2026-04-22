# Codex Exec Halt

Status: active halt
Date: 2026-04-22
Scope: `sandbox/codex-dr/`

## Decision

Do not launch `codex exec`, `codex-exec`, `/usr/bin/script ... codex exec`, or
any terminal-agent provider-backed smoke run from the Codex-DR sandbox until
the Principal explicitly reopens a named run.

This halt applies even if a run manifest, run-control receipt, or case manifest
already exists.

## Reason

The authorized `draco_smoke_001` run completed, but it exposed a live-run
control failure. The transcript reported:

```text
tokens used
270,716
```

The earlier prompt-level budget target was `42,000` total tokens. That target is
now classified as runtime-control leakage, not as a Codex-DR architecture
requirement.

The actual halt reason is simpler: no more hidden, repeated, or unsupervised
live Codex CLI launches until the Principal reopens a named run under the
run-control receipt rules in `docs/codex_mesh_launch_control_2026_04_22.md`.

## Current Process Sweep

On 2026-04-22, the coordinator ran a process sweep for:

- `codex exec`
- `codex-exec`
- `/usr/bin/script ... codex exec`

Result: no live matching process remained after the sweep.

The Codex desktop app and old interactive `codex` CLI sessions were observed
separately. This halt is aimed at non-interactive `codex exec` launches from
the sandbox, not at quitting the desktop app.

## Reopen Conditions

A future boxed provider-backed run requires:

- a fresh Principal authorization naming the exact run id or authorized class;
- a run-control receipt;
- foreground supervision or external monitoring;
- wall-clock bound and kill path;
- transcript capture and output boundary;
- no automatic retries unless separately approved;
- data and claim boundaries.

Any reopened run must create a new authorization receipt before launch.
