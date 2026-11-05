# Progress - N3-copper

Owner: N3-copper alone. Other nodes must not edit this file.
Base at start: origin/main aab6496699490f8deb15edd67fc65f481200e33a
Gate (graph.md): Record a run containing a STOP, replay it, show
byte-identical task outputs. Replay is the acceptance criterion;
latency is secondary. Scope: spikes/copper-stop-path/** only, plus
this progress file. No Pi. Root Cargo/MSRV untouched.

Resumed in place: partial spikes/copper-stop-path/ from the
rate-limited worker (Cargo.toml, Cargo.lock, build.rs, copper.ron,
rust-toolchain.toml, src/main.rs, target/) was preserved and inspected,
not restarted. One change to its code: cargo fmt; the 16 MiB logger
preallocation from the partial spike was retained after a 1 MiB trial
split the unified log into 12 section files (trial reverted).

## Verdict: PASS (positive result, attempt 1 of 3)

The resumed spike built and passed on the first run; no fix attempts
were consumed beyond formatting and evidence generation.

## Raw evidence

Toolchain (no rustup on this host; rust-toolchain.toml pins 1.95.0,
Homebrew toolchain satisfies >= 1.95):
  rustc 1.99.1 (58cf8f9c3 2026-10-13) (Homebrew)
  cargo 1.99.1 (5f94df478 2026-08-27) (Homebrew)

cu29 lock check (python parse of spikes/copper-stop-path/Cargo.lock):
  all 16 cu29-* packages version = 1.3.0; all_cu29_1.3.0= True

cargo fmt --check: FMT_OK
cargo clippy --locked --all-targets -- -D warnings: exit 0

python3 verify.py (evidence/verify.log, verbatim key lines):
  STOP_RECORDED sequence=1
  TASK_OUTPUTS_BYTE_IDENTICAL bytes=39
  KEYFRAME_BYTE_IDENTICAL
  run1 task_outputs_cmp=IDENTICAL
  run1 copper_logs_cmp=IDENTICAL
  run2 task_outputs_cmp=IDENTICAL
  run2 copper_logs_cmp=IDENTICAL
  cross_run_task_outputs_cmp=IDENTICAL
  N3_GATE_PASS
  VERIFY_EXIT:0

sha256 (committed evidence):
  f5ac0065cf3b603cad9df9d8a0d396945912e2c3a18a2b328a9d9ce9752d1be5  evidence/original_0.copper
  f5ac0065cf3b603cad9df9d8a0d396945912e2c3a18a2b328a9d9ce9752d1be5  evidence/replay_0.copper
  249509dc1dd8890886210406a1d5bee1787d6a896165acdcec7aac606506361d  evidence/original-task-outputs.bin
  249509dc1dd8890886210406a1d5bee1787d6a896165acdcec7aac606506361d  evidence/replay-task-outputs.bin
  cmp original vs replay task outputs: IDENTICAL
  cmp original vs replay Copper logs: IDENTICAL

evidence/comparison.txt (verbatim):
  command=STOP
  sequence=1
  authorized=true
  original_task_outputs_bytes=39
  replay_task_outputs_bytes=39
  byte_identical=true
  keyframe_byte_identical=true

Root isolation: git diff -- Cargo.toml Cargo.lock prints nothing
(exit 0). Root rust-version stays 1.74. The spike has its own
[workspace] in its Cargo.toml and its own rust-toolchain.toml (1.95.0).

## Outputs

spikes/copper-stop-path/{Cargo.toml,Cargo.lock,build.rs,copper.ron,
rust-toolchain.toml,src/main.rs,README.md,verify.py,.gitignore,
evidence/**}; progress/N3-copper.md (this file).

## Limits

Simulated tasks, one iteration, mock clock, no hardware/Pi, no latency
claim. Local make test not run: .venv absent in this worktree; PR CI
is the root-suite evidence. This spike is not an adopted policy.
