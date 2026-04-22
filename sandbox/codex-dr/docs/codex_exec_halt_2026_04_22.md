# Codex Exec Halt

Status: active halt
Date: 2026-04-22
Scope: `sandbox/codex-dr/`

## Decision

Do not launch `codex exec`, `codex-exec`, `/usr/bin/script ... codex exec`, or
any terminal-agent provider-backed smoke run from the Codex-DR sandbox until
the Principal explicitly reopens a named run.

This halt applies even if a run manifest, token manifest, or case manifest
already exists.

## Reason

The authorized `draco_smoke_001` run completed, but it exposed a token-burn
control failure. The transcript reported:

```text
tokens used
270,716
```

The prompt-level budget target was `42,000` total tokens. That target was not
mechanically enforced by the current `codex exec` command surface.

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

A future boxed provider-backed run requires one of:

- mechanical token or cost cap enforcement;
- external metering plus a hard timeout and kill path;
- a much smaller context envelope with an explicit token budget check;
- a fresh Principal waiver naming the exact run id.

Any reopened run must create a new authorization receipt before launch.
