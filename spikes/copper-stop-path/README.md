# Copper stop-path spike (N3-copper)

Independent Cargo workspace. It is not a member of the root workspace and
does not change the root Cargo.toml, root Cargo.lock, or the root MSRV
(1.74). Its own rust-toolchain.toml pins Rust 1.95.0; any Rust >= 1.95
toolchain satisfies the spike locally.

Dependencies are pinned exactly: cu29, cu29-derive, cu29-export,
cu29-runtime, cu29-unifiedlog and (build) cu29-build all at =1.3.0
(see Cargo.lock).

## What it does

A three-task Copper graph (copper.ron, sim mode):

  InterventionSource --Intervention--> Authorization
  Authorization --AuthorizationDecision--> SimulatedActuator

InterventionSource emits Intervention{command:"STOP", sequence:1}.
Authorization authorizes iff command == "STOP". SimulatedActuator errors
on any non-STOP or unauthorized decision. One iteration is run on the
mock (deterministic) RobotClock, recorded to a Copper unified log, then
replayed via replay_recorded_copperlist with the recorded keyframe into
a second unified log. Both CopperLists are re-read from disk, bincode
encoded, and compared byte for byte; keyframes are compared too. The
program exits non-zero on any mismatch or if the recorded run does not
contain an authorized STOP.

## Run / verify

  cargo build --locked
  ./target/debug/copper-stop-path evidence      # regenerate evidence/
  python3 verify.py                             # full deterministic gate

verify.py runs the binary twice into fresh temp dirs and checks, with
plain byte/hash operations only: original vs replay task outputs and
Copper logs byte-identical within each run, task outputs byte-identical
across both runs, and comparison.txt records the authorized STOP.

## Committed evidence (evidence/)

- original_0.copper / replay_0.copper: raw Copper unified logs (16 MiB
  preallocated mmap sections; mostly zero padding, byte-identical).
- original-task-outputs.bin / replay-task-outputs.bin: bincode-encoded
  recorded task outputs (39 bytes, byte-identical).
- comparison.txt: deterministic record/replay comparison.
- evidence-run.stdout.log / evidence-run.stderr.log: raw stdout/stderr
  of the run that produced this evidence.
- verify.log: raw stdout of python3 verify.py (two runs, hashes, PASS).

## Limits

Simulated tasks only, single iteration, mock clock, no hardware, no Pi,
no latency claim. Replay byte-identity is the acceptance criterion here;
nothing in this spike is an adopted OD/Quberon policy position.
