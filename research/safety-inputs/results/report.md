# Synthetic safety-input boundary report

SYNTHETIC ONLY — no sensor, microphone, camera, speaker, person, field, or
learned-model qualification is claimed or implied. System under test: the
unmodified deterministic recognizers (voice conf >= 0.85/final/standalone
STOP-STOPP; gesture visibility >= 0.8, >= 3 consecutive frames, >= 700 ms),
plus harness-only freshness (stale > 300 s, future < -30 s) and event_id
replay layers. Ground truth = labelled synthetic intent; every rate shows
its denominator. Source: results/summary.json (83 cases) + results/results.jsonl.

## Headline (intent-based, all 83 cases)

- False triggers: 1/25 intent-no-stop cases triggered (FP/(FP+TN) = 1/25 = 0.04).
- Missed triggers: 31/58 intent-stop cases did not trigger (FN/(FN+TP) = 31/58 = 0.534483).
  This aggregate deliberately includes boundary abstentions and stale/replay
  suppression (below); it is NOT a canonical-case or field failure rate.

## By modality

- Voice (45): false trigger 1/17 = 0.058824; missed 16/28 = 0.571429.
- Gesture (30): false trigger 0/5 = 0.0; missed 15/25 = 0.6.
- Crossmodal, harness-only OR (8): false trigger 0/3 = 0.0; missed 0/5 = 0.0.
  No app fusion exists; this measures only the harness OR policy.

## By category (false = FP/negatives, missed = FN/positives)

- voice canonical_positive (6): missed 0/6.
- voice degraded_confidence (12): missed 8/12 (conf 0.0, 0.5, 0.80, 0.84,
  0.849 and invalid -0.1, 1.01, 1.5 abstain; 0.85, 0.851, 0.90, 1.0 trigger).
- voice missed_trigger_boundary (3): missed 3/3 (all interim final=false).
- voice false_trigger (17): false 1/17 — the sole FP is V-NEG-08,
  "the bus stop is near": a standalone `stop` token in a non-command sentence
  triggers under the declared token policy (documented matcher limit in
  integrations/interventions.py; quoted/reported speech is not distinguished).
  Negations ("do not stop", "inte stopp", ...), "nonstop", "stopwatch" do not trigger.
- voice stale_replay (7): non-trigger 5/7 by design at pipeline layer
  (3 stale/future + 2 replays); fresh (299 s) and first delivery trigger.
- gesture canonical_positive (3): missed 0/3.
- gesture hold_frame_boundary (7): missed 5/7 (600 ms, 699 ms, 2-frame/700 ms,
  1-frame, interrupted-short-run); 701 ms and interrupted-then-valid-run trigger.
- gesture degraded_confidence (10): missed 7/10 (visibility 0.0/0.5/0.79,
  20/22 landmarks, out-of-range coordinates, empty); 0.80/0.81/1.0 trigger.
- gesture false_trigger (5): false 0/5 (fist, pointing, thumb-tucked,
  sideways palm, brief 200 ms wave).
- gesture stale_replay (5): non-trigger 3/5 (2 duplicate-timestamp sequences
  rejected by the recognizer itself + 1 event replay blocked only by the
  harness guard); first delivery and out-of-order (recognizer sorts) trigger.
- crossmodal contradictory_signals (8): 0/5 missed, 0/3 false — a valid palm
  overrides a negated voice transcript and vice versa under OR; degraded
  voice (0.50) + brief palm correctly does not trigger.

## Key boundary findings

1. Exact thresholds behave as declared: voice 0.849 no / 0.85 yes;
   gesture 699 ms no / 700 ms yes, 2 frames no / 3 yes, visibility 0.79 no / 0.80 yes.
2. Recognizers alone have no freshness/replay concept: stale (301 s) and
   replayed voice inputs trigger recognizer-only (see
   `recognizer_only_replay_and_stale_probe` in summary.json) and are blocked
   only by the harness freshness/replay layers. Any deployment claim must
   therefore credit the surrounding event/idempotency layer, not the recognizer.
3. Gesture duplicate timestamps are rejected by the recognizer itself;
   out-of-order frames are sorted and may trigger — timestamp *age* is not
   evaluated for gesture at recognizer level.
4. The one false trigger is a known token-policy limit (non-command
   standalone "stop"), not a threshold failure.
5. Contradictory signals: no veto semantics exist; under harness OR a valid
   STOP-only signal wins. This is a measurement policy, not app behaviour.

## Limits

Enumerated synthetic grids authored against the same thresholds they probe
(same-author weakness, as in research/adversarial): they verify boundary
behaviour of the deterministic code, not recognizer accuracy on real speech
or hands. No latency, subgroup, acoustic, visual, or environmental claim.
QIP-R9.1 remains UNIMPLEMENTED in the profile traceability sense; this
harness does not change that status and claims no QIP class.
