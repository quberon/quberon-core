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

### Worker detachment — corrected and verified

The first probe found a genuine macOS defect in the supplied worker:

```text
ops/worker.sh: line 69: setsid: command not found
```

macOS on this host has no `setsid` binary (`/usr/bin/setsid`,
`/bin/setsid`, and `/opt/homebrew/bin/setsid` are all absent), and the
worker initially reported a start even though the detached command had
not run. `ops/worker.sh` now preflights detachment: it uses `setsid(1)`
when present and otherwise falls back to base-system Perl
`POSIX::setsid`, failing before it claims a worker started.

Detached proof on 2026-11-06: the launcher returned in 0 seconds; the
worker process had PPID 1 and its own process group; it slept inside the
agent task, wrote `/tmp/quberon-detached-proof.txt` at
`2026-11-06T10:16:09Z`, printed `DETACHED_WORKER_DONE`, and the worker log
recorded `exit rc=0`. Therefore `ops/config.json` sets
`hermes.verified: true` for the invocation and worker detachment.

## Host path note

The supplied launchd plists set `QUBERON_REPO` to
`/Users/quberon1/quberon-core`. The actual checkout on this host is
`/Users/quberon1/quberon-robot-interface`, and `/Users/quberon1/quberon-core`
does not exist. Host installation must resolve this explicitly (for example
by a symlink or plist correction) before bootstrap; the supervisor must not
be loaded against a missing repository path.
