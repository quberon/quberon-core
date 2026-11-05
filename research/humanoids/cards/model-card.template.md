# Model card: voice/gesture STOP recognizer (template)

- Model/version, training dataset cards (ds-*), code + config hashes:
- Intended use: propose STOP only, via the existing intervention path.
  Non-goals: reset/unlatch, resume, motion, identity, emotion inference.
- Metrics by subgroup/environment (see VOICE-GESTURE-STOP-TRAINING-ROADMAP):
  false-negative rate, false-positive rate, abstention rate, latency.
- Abstention + fail-closed behaviour: low confidence / OOD => no action,
  state UNKNOWN, never an upgraded success.
- Limitations + untested conditions:   Reproducibility: seeds, env, hashes.
- Deployment gate: human approval record; rollback plan; audit integration.
