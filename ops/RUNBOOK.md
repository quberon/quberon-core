# Quberon ops runbook

## Step 4 Hermes invocation verification — 2026-11-06

The placeholder command in the supplied files was:

```text
hermes run --non-interactive --prompt-file <file>
```

That command does not exist on this host: `hermes run --help` returns
`hermes: 'run' is not a 'hermes' command.`

The real non-interactive Hermes form is:

```bash
hermes chat --oneshot --query-file <prompt-file> --in <worktree> \
  --provider meta-ai -Q -m muse-wonder-1.0
```

Verified directly on this Mac:

1. **No TTY / no interactive prompt:** ran with stdin redirected from
   `/dev/null`; it printed only `HERMES_PROBE_OK` and exited.
2. **Prompt from file:** used `--query-file`, not a prompt on argv.
3. **Meaningful exit code:** the valid probe exited `0`; an intentionally
   invalid provider exited `1` with `Unknown provider ...` on stderr.
4. **Model:** provider `meta-ai`, model `muse-wonder-1.0`. No distinct
   verified "fast" model exists on this install, so `ops/config.json`
   intentionally maps both model tiers to the same verified model.

### Worker detachment blocker

`ops/worker.sh` was updated to the real command above and probed with a
throwaway prompt. It reported `started pid=...` and exited `0`, but the log
contains:

```text
ops/worker.sh: line 69: setsid: command not found
```

macOS on this host has no `setsid` binary (`/usr/bin/setsid`,
`/bin/setsid`, and `/opt/homebrew/bin/setsid` are all absent). Therefore the
worker's survive-the-launcher property is **not verified**, and the launcher
can falsely report success after the detached command fails to start.
`ops/config.json` therefore keeps `hermes.verified: false`.

Do not install or trust the launchd supervisor for unattended dispatch
until the detachment mechanism is corrected for macOS and retested:
a worker must complete after its launcher exits, and a failed launch must
not be recorded as started.

## Host path note

The supplied launchd plists set `QUBERON_REPO` to
`/Users/quberon1/quberon-core`. The actual checkout on this host is
`/Users/quberon1/quberon-robot-interface`, and `/Users/quberon1/quberon-core`
does not exist. Host installation must resolve this explicitly (for example
by a symlink or plist correction) before bootstrap; the supervisor must not
be loaded against a missing repository path.
