# Wave5 F3 — STOP priority under load (exact report)

Node: F3 (Tier 1). Base: 35ee2aef6f7a2fcf17e51de40678aee97ba0b350
(= origin/main at start; `git log -1 origin/main` verified).
Owns only: loadtest/** and progress/F3-stop-load.md. No other file edited.

## Spec / gap read first

- docs/specs/intervention-profile/QIP-v0.1.md Section 6 / Section 11:
  QIP-R3.1, R3.2, R3.3 all traced UNIMPLEMENTED —
  "no load/priority test in N4".
- TRACEABILITY.md R3: "No end-to-end load, deadline, starvation,
  network partition, or physical stop-time test."
- graph.md R-IMM-1 (STOP proceeds unsigned when core unavailable;
  permission fails closed), R-IMM-2 (unreachable != reachable refusal),
  R-IMM-4 (raw output required), QIP-R3.3 (priority handling MUST NOT
  be represented as a real-time / physical stop-time guarantee).

This node supplies local simulated load evidence for that gap. It does
not promote any QIP requirement, claim a QIP class, or amend QIP
traceability — that amendment procedure belongs to the profile owner
(QIP-v0.1.md Section 11) using this raw output if they choose.

## What was built

- loadtest/harness.py — harness (docstring states method + limits).
- loadtest/run.py — CLI: `.venv/bin/python -m loadtest.run --samples 30
  --out <json>`; prints one line per scenario.
- loadtest/test_loadtest.py — 6 determinism tests (below).
- loadtest/README.md — run instructions and claim scope.
- loadtest/results/attempt{1,2,3}.json — raw output of the three full
  attempts (every sample, outcome counts, load counters; not summaries
  only, per R-IMM-4).

## Method

- Real HTTP: uvicorn serving the real simulated app (create_app) on
  127.0.0.1, fresh app + fresh SQLite DB per scenario, authenticated
  operator session per client. Adapter: SimulatedRobotAdapter only.
- Timing: time.perf_counter_ns() around POST /api/robots/{id}/stop only.
- Samples: n=30 measured STOPs per scenario per attempt, STOPs
  sequential (stop_concurrency=1) except concurrent_stops (8-way
  batches). Unique idempotency key per STOP (no duplicate shortcut).
- Percentiles: nearest-rank on sorted samples. jitter_ms = mean
  absolute successive difference in sample order. Stats keys:
  n, min, median, mean, p95, p99, max, jitter.
- Background load runs during sampling (0.3 s warm-up):
  planner_load = 4 planner workers against a 30 ms slow planner stub
  (plan semaphore is 2, so saturation returns bounded "busy", R3.2);
  status_task_load = 3 status + 3 simulated-task workers;
  cpu_contention = 10 forked busy-loop processes (= os.cpu_count());
  slow_adapter = injected 100 ms delay in SimulatedRobotAdapter.stop;
  core_unavailable = secure_core=None (the real unsigned path);
  core_rejecting / baseline = fake secure-core stubs (rejecting raises
  SecureCoreRejected; accepted returns ACCEPTED code). Stubs involve
  no Rust subprocess and no signing; they are not secure-core evidence.
- Host: Darwin 24.3.0 arm64, Python 3.11.15, load averages at run time
  approx 4.44 / 2.87 / 2.54 (shared, busy host — see Negative result).

## Attempts (three-attempt gate)

- Build attempt 1: `pytest loadtest/ -q` = 4 failed, 2 passed.
  Cause: httpx.Client re-entered as a context manager after use
  (RuntimeError: Cannot open a client instance more than once).
  Fixed in harness only (explicit close()); no gate weakened.
- Build attempt 2: `pytest loadtest/ -q` = 6 passed in 1.44s.
- Full-load attempts 1, 2, 3: all completed, exit 0. Raw JSON in
  loadtest/results/attempt{1,2,3}.json. Outcome classification was
  identical across all three attempts for every scenario (see table);
  timing values were not identical and are not claimed to be.

## Results — three attempts (ms; n=30 per scenario per attempt)

scenario               core          median (a1/a2/a3)      p95 (a1/a2/a3)        p99 a1/a2/a3        max a1/a2/a3       jitter (a1/a2/a3)
baseline_accepted_stub accepted_stub 1.06 / 1.08 / 1.21     1.61 / 1.61 / 1.95    1.72/1.62/2.28      1.72/1.62/2.28     0.24 / 0.23 / 0.31
planner_load           accepted_stub 3.51 / 3.14 / 3.32     4.28 / 4.33 / 8.54    5.22/4.54/8.75      5.22/4.54/8.75     0.45 / 0.33 / 1.02
status_task_load       accepted_stub 7.12 / 6.92 / 7.00     9.11 / 8.50 / 8.48    10.40/13.32/15.45   10.40/13.32/15.45  1.66 / 1.45 / 1.62
cpu_contention         accepted_stub 1.36 / 1.35 / 1.20     2.08 / 2.29 / 2.42    2.12/2.67/2.75      2.12/2.67/2.75     0.35 / 0.30 / 0.34
slow_adapter           accepted_stub 155.13 / 169.52 / 154.66  180.47 / 184.00 / 176.54  180.65/184.92/176.75  180.65/184.92/176.75  27.94 / 21.58 / 20.63
core_unavailable       unavailable   1.23 / 1.09 / 1.16     1.93 / 2.18 / 1.83    3.00/2.26/3.04      3.00/2.26/3.04     0.35 / 0.33 / 0.35
core_rejecting         rejecting     1.05 / 1.02 / 1.12     1.75 / 1.64 / 1.97    1.80/1.67/12.50     1.80/1.67/12.50    0.26 / 0.26 / 1.03
concurrent_stops (x8)  accepted_stub 6.41 / 6.12 / 6.54     8.28 / 8.13 / 8.34    8.45/8.25/8.71      8.45/8.25/8.71     1.36 / 1.51 / 1.42

Outcomes (identical in all 3 attempts; adapter_stop_calls per attempt):
- baseline / planner / status_task / cpu / slow / concurrent:
  30 x "200/ACKNOWLEDGED/accepted", adapter calls = 30.
- core_unavailable: 30 x "200/ACKNOWLEDGED/unavailable", adapter = 30
  (STOP proceeds unsigned, R-IMM-1, as designed).
- core_rejecting: 30 x "503/UNKNOWN/rejected", adapter calls = 0
  (reachable refusal fails closed, adapter never invoked, R-IMM-2 /
  QIP-R7.4 behaviour — via a stub, not the Rust core).
- Load actually generated (attempt 1; a2/a3 in raw JSON):
  planner_load: planner_200=14, planner_busy=517 (bounded "busy"
  refusals observed while every STOP still returned 200);
  status_task_load: status_200=418, task_409=336.

## Determinism tests (loadtest/test_loadtest.py, 6 passed)

- summarize() on fixed input returns the exact expected dict, and a
  repeated call is byte-identical; nearest-rank p95/p99 verified on
  1..100. Timing equality across runs is never asserted.
- Two fresh small runs (n=3) give identical outcome classification,
  sample counts, and adapter-call counts.
- Rejecting stub: 3x 503/UNKNOWN/rejected, adapter calls = 0.
- Unavailable: 3x 200/ACKNOWLEDGED/unavailable, adapter calls = 3.
- Slow adapter (20 ms injected, n=3): outcomes/counts exact; median
  >= 10 ms asserted only as a wiring sanity check, not a latency claim.
- Full suite: `make test` = 137 passed, 13 skipped (includes the 6
  new loadtest tests; skips are the pre-existing Rust/make-gated ones).

## Findings (behavioural, simulation only)

1. Planner saturation did not block STOP in this simulation: with the
   planner semaphore saturated (hundreds of bounded "busy" replies),
   all 90 STOPs (3 attempts x 30) returned 200/ACKNOWLEDGED. Median
   STOP latency rose from ~1.1 ms baseline to ~3.1-3.5 ms.
2. Status+task load inflated STOP most among non-adapter loads
   (median ~7.0 ms vs ~1.1 ms baseline), consistent with
   simulated-task and STOP sharing Store.lock (app/main.py
   execute_stop / simulated_task). Task load here is *rejected* task
   load (task_409: the latch is active from initial state), so this
   measures lock contention on the rejection path, not on successful
   task execution. Successful-task contention remains unmeasured.
3. CPU contention (10 spin processes on 10 CPUs) barely moved the
   median (~1.2-1.4 ms). This is not evidence STOP is CPU-immune:
   the STOP path is mostly I/O/lock waiting, and the host was already
   loaded; it only shows this workload did not starve it here.
4. Concurrent STOPs (8-way) serialize observably: median ~6.1-6.5 ms
   vs ~1.1 ms sequential baseline, consistent with Store.lock
   serializing execute_stop. Priority is per-path isolation from
   planner/status, not parallelism among STOPs.
5. Fail direction under load-free conditions held exactly as
   specified in all attempts: unavailable -> unsigned STOP proceeds;
   reachable rejection -> 503, UNKNOWN, adapter never called.

## Negative result — timing isolation is NOT honestly achievable here

The harness cannot isolate STOP-path timing on this host, and its
numbers must not be quoted as STOP latency:

- Calibration failure: a bare time.sleep(0.100) in isolation on this
  machine measured 101.1-175.0 ms over 10 trials. Accordingly the
  injected 100 ms adapter delay was recovered as median
  154.66-169.52 ms, min 105.48-117.86 ms, jitter 20.63-27.94 ms —
  a systematic +55-70 ms median inflation that is host scheduling
  noise, not app behaviour.
- Host was shared and busy (load avg ~4.4) throughout; no CPU
  pinning, no real-time scheduling, Python/GIL, uvicorn threadpool,
  SQLite WAL and Store.lock waits are all inside every sample.
- Tail instability across attempts confirms this: planner_load p95
  4.28 / 4.33 / 8.54 ms; core_rejecting p99 spiked to 12.50 ms in
  attempt 3 against 1.67-1.80 ms in attempts 1-2.
- Therefore: the deterministic, citable result of this node is the
  *behavioural* one (outcome classification, adapter-call counts,
  bounded planner "busy", fail direction — identical across 3
  attempts and in the pytest determinism tests). All millisecond
  figures are local Mac simulation observations with the stated
  method, useful for relative comparison inside this run only.
  They are not Pi figures, not hardware figures, not a deadline,
  starvation, or network-partition result, and not a physical
  stop-time claim (QIP-R3.3). No latency claim is made.

Still unmeasured (gaps remain): successful-task lock contention,
network partition, Rust-core subprocess under load, Pi execution,
any deadline/starvation bound. QIP-R3.1/R3.2 stay UNIMPLEMENTED in
the profile until its owner amends traceability per QIP Section 11.

## Verification

- `.venv/bin/python -m pytest loadtest/ -q` -> 6 passed in 1.44s
- `make test` -> 137 passed, 13 skipped
- Three full harness runs -> exit 0 each; raw JSON committed in
  loadtest/results/.
