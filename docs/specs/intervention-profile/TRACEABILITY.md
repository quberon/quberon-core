# Intervention profile traceability (gate zero)

Status: descriptive test inventory only; **not normative text** and not evidence of standards conformity.

Mapping rule: only exact test function names that exist at base `aab6496699490f8deb15edd67fc65f481200e33a` are listed. `gap` means no existing test was found for that part of the outline. N4-dependent manufacturer conclusions are not inferred.

| Outline ID | Existing test evidence | Gap / limitation |
|---|---|---|
| R1 | `tests/test_app.py::test_cross_robot_and_bad_action_rejected`; `tests/test_app.py::test_intervention_viewer_rejected_stale_rejected_wrong_robot`; `tests/test_secure_core.py::test_scope_mismatch_client_rejected`; `tests/test_secure_core.py::test_bounded_subject_rejected`; `tests/test_safety_inputs.py::test_isaac_transport_rejects_wrong_scene_stale_replay_and_non_stop` | No vendor-neutral intervention-envelope schema test; no manufacturer target/capability identifier mapping. |
| R2 | `tests/test_app.py::test_unauthenticated_and_viewer_cannot_stop`; `tests/test_app.py::test_csrf_required_and_operator_stop_idempotent_conflict`; `tests/test_app.py::test_intervention_viewer_rejected_stale_rejected_wrong_robot`; `tests/test_app.py::test_voice_safety_endpoint_is_authenticated_conservative_and_idempotent`; `tests/test_secure_core.py::test_client_accepts_stop_and_rejected_client_fails_closed` | Application auth tests do not establish a safety-rated authorization architecture or validate deployment roles. |
| R3 | `tests/test_secure_core.py::test_rate_limiter_stop_isolated_from_other_traffic`; `tests/test_app.py::test_planner_gate_busy_and_page_polling`; `tests/test_app.py::test_live_unconfigured_starts_with_unavailable_planner` | No end-to-end load, deadline, starvation, network partition, or physical stop-time test. |
| R4 | `tests/test_app.py::test_csrf_required_and_operator_stop_idempotent_conflict`; `tests/test_app.py::test_stale_stop_replay_after_reset_and_task`; `tests/test_app.py::test_duplicate_task_key_does_not_reinvoke_or_500`; `tests/test_app.py::test_intervention_voice_stop_converges_and_panic_is_audit_only`; `tests/test_app.py::test_voice_safety_endpoint_is_authenticated_conservative_and_idempotent`; `tests/test_safety_inputs.py::test_isaac_transport_rejects_wrong_scene_stale_replay_and_non_stop`; `tests/test_secure_core.py::test_epoch_advances_across_clients_sequence_preserved` | No cross-vendor idempotency semantics or restart/reconnect test against a real manufacturer controller. |
| R5 | `tests/test_app.py::test_task_blocked_latched_admin_reset_no_task_started`; `tests/test_app.py::test_restart_persists_latch`; `tests/test_app.py::test_stale_stop_replay_after_reset_and_task`; `tests/test_app.py::test_gesture_safety_endpoint_stops_but_cannot_reset`; `tests/test_meta_live.py::test_planner_cannot_reset_latch`; `tests/test_secure_core.py::test_stop_executes_without_secure_core_but_reset_does_not` | Simulation latch behavior is not evidence of a physical emergency-stop reset/restart function. No manufacturer reset interface is mapped. |
| R6 | `tests/test_app.py::test_adapter_failure_is_unknown_not_stopped_claim`; `tests/test_safety_inputs.py::test_isaac_bridge_contract_acknowledges_only_observed_stop`; `tests/test_secure_core.py::test_client_accepts_stop_and_rejected_client_fails_closed`; `tests/test_secure_core.py::test_stop_rejected_by_secure_core_does_not_invoke_adapter`; `tests/test_secure_core.py::test_sqlite_failure_never_invokes_adapter` | No independent physical-state sensor validation, bounded observation latency, or real robot stop-state semantics. |
| R7 | `tests/test_secure_core.py::test_stop_executes_without_secure_core_but_reset_does_not`; `tests/test_secure_core.py::test_stop_rejected_by_secure_core_does_not_invoke_adapter`; `tests/test_secure_core.py::test_subprocess_timeout_fails_closed`; `tests/test_app.py::test_b5_degraded_ui_message_and_disabled_controls`; `tests/test_app.py::test_runtime_db_failure_fails_closed` | Current behavior is project policy, not a standards-derived rule. Additional fault classes and deployment safety analysis remain gaps. |
| R8 | `tests/test_secure_core.py::test_app_stop_with_secure_core_accepted`; `tests/test_secure_core.py::test_stop_executes_without_secure_core_but_reset_does_not`; `tests/test_secure_core.py::test_epoch_advances_across_clients_sequence_preserved`; `tests/test_secure_core.py::test_key_file_permissions_enforced`; `tests/test_secure_core.py::test_production_mode_with_key_file_accepts`; `tests/test_app.py::test_restart_persists_latch` | No retention policy, clock trust, external audit export, tamper-evidence recovery, or complete custody-chain test. No control-path blockchain dependency is tested because the design excludes it. |
| R9 | `tests/test_safety_inputs.py::test_voice_recognizer_requires_final_confident_standalone_stop`; `tests/test_safety_inputs.py::test_open_palm_requires_visibility_consecutive_frames_and_hold`; `tests/test_app.py::test_transcript_matcher_policy`; `tests/test_app.py::test_voice_safety_endpoint_is_authenticated_conservative_and_idempotent`; `tests/test_app.py::test_gesture_safety_endpoint_stops_but_cannot_reset`; `tests/test_app.py::test_intervention_voice_stop_converges_and_panic_is_audit_only` | Synthetic recognizer tests do not qualify sensors, AI models, microphones/cameras, ESPE, environmental robustness, diagnostic coverage, or human-factors performance. |
| R10 | `gap` | `research/humanoids/registry/api-surfaces.jsonl` is empty. No observed manufacturer interface, protocol, stop category, status semantics, capability negotiation, timing, authentication, or reset mapping is available. This is the explicit N4 dependency. |
| R11 | `tests/test_humanoid_registry.py::test_registry_validates_clean`; `tests/test_humanoid_registry.py::test_verified_without_evidence_is_rejected`; `tests/test_humanoid_registry.py::test_lane_d_discovery_is_evidenced_without_promotion`; plus the R1-R9 tests above | No intervention-profile schema/conformance suite exists; no licensed-standard clause matrix; no hazard analysis, PL/SIL calculation, independent assessment, real manufacturer integration test, or physical stopping-time evidence. |

## Gate-zero verdict

- R1-R9 and R11 have real project tests that can inform a later profile, with the limitations shown.
- R10 is a hard evidence gap, not a failed inference.
- The node-level full gate (“every requirement traceable to an observed manufacturer interface or a stated design decision”) cannot be closed for a normative profile until N4 supplies observed interfaces. Gate zero passes only as research and gap documentation: every outline item above is labelled either a stated design decision/test observation or an N4-dependent gap.

## Wave 4 QIP v0.1 addendum (2026-11-05, N5)

`QIP-v0.1.md` in this directory is the normative RFC 2119 profile built on
the R1–R11 outline above. Its traceability does not reuse the test names
in the table above as conformance evidence: every QIP MUST traces to a
actual Wave 4 N4 stable test identifier shipped by N4
(`QIP-ID-*`, `QIP-AUTH-*`, `QIP-INT-*`, `QIP-LATCH-*`, `QIP-STATE-*`,
`QIP-AUDIT-*`, `QIP-PROP-*`, `QIP-DEG-*`; see QIP-v0.1.md Section 11) or
carries the explicit marker `UNIMPLEMENTED` (18 of 34 at drafting, incl.
all of R3, R10, R11); identifiers must be verified against merged N4 raw
output (fetch, rebase, grep, amend) before the profile merges. The
review-depth markers and the no-abstract-derived-requirement rule from
PRIOR-ART.md are preserved in QIP-v0.1 Annex A.
