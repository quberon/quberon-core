# Safety-input qualification harness — SYNTHETIC ONLY

Deterministic, offline boundary harness for the existing deterministic
recognizers in `integrations/recognizers.py` (read-only import; no app,
control, endpoint, or recognizer code is changed here).

NO QUALIFICATION CLAIM: no microphone, camera, sensor, speaker, person,
field condition, or learned model is tested. Results describe only how the
deterministic code behaves on enumerated synthetic inputs. They must not be
represented as sensor/model qualification, safety validation, or QIP
conformance (QIP-R9.3, R11.2).

## Run

    python3 research/safety-inputs/generate.py   # regenerates datasets/*.jsonl (byte-identical)
    python3 research/safety-inputs/harness.py    # writes results/results.jsonl + results/summary.json
    python3 -m pytest research/safety-inputs/tests -q

## Datasets (83 enumerated cases, no RNG)

- datasets/voice.jsonl (45): canonical positives; confidence sweep
  0.0/0.5/0.80/0.84/0.849/0.85/0.851/0.90/1.0 and invalid -0.1/1.01/1.5;
  interim (final=false); negated/embedded/conversation negatives; stale
  (age 301 s, 3600 s, future -31 s vs fresh 299 s) and event replay.
- datasets/gesture.jsonl (30): synthetic 21-landmark frames; hold
  600/699/700/701 ms, 1/2/3+ consecutive frames, interrupted runs;
  visibility 0.0/0.5/0.79/0.80/0.81/1.0; 20/22 landmarks, out-of-range
  coordinates, empty sequence; fist/pointing/thumb-tucked/sideways/brief-wave
  negatives; duplicate timestamps and event replay; out-of-order input.
- datasets/crossmodal.jsonl (8): contradictory voice/gesture pairs under a
  harness-only OR policy (any valid STOP-only signal triggers). No fusion
  exists in the app — separate endpoints — so this claims no app behaviour.

## Layers measured (kept distinct in results)

1. Recognizer only: VoiceStopRecognizer (final, conf >= 0.85, standalone
   non-negated STOP/STOPP) and OpenPalmStopRecognizer (21 landmarks,
   visibility >= 0.8, >= 3 consecutive qualifying frames, >= 700 ms hold).
2. Harness pipeline: recognizer + existing InterventionEvent freshness
   bounds (stale > 300 s, future skew < -30 s, from
   integrations/interventions.py) + a harness-only event_id replay guard.
   Recognizers alone have no timestamp/replay concept: the probe in
   summary.json (`recognizer_only_replay_and_stale_probe`) shows stale and
   replayed voice inputs still trigger recognizer-only and are blocked only
   at the pipeline layer. Downstream app idempotency is out of scope here.

## Reading the rates

Ground truth is labelled synthetic intent. Every rate carries a denominator
(`numerator/denominator` in summary.json). "Missed" includes deliberate
boundary abstentions (below-threshold confidence, interim, short hold,
insufficient frames, low visibility) and stale/replay suppression — the
by-category breakdown and `nontriggering_intended_stop_ids` separate those
causes; the aggregate missed rate is therefore not a field failure rate.
See results/report.md for the exact numbers and findings.
