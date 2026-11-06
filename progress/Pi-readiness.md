# Pi readiness — Wave 6 Tier 1 prep

Base: `origin/main` (`65f5271aa59d90a76ec53a0f0f6d750f9e566f4b`)
Branch: `wave6/pi-prep`
Scope owned: `docs/pi-readiness/**`, `scripts/pi_readiness_check.sh`,
`progress/Pi-readiness.md`. Nothing else was changed.
Pi accessed: NO. Pi deployed: NO. Services changed: NO. Pi state at prep
time (per task): powered off / charging — expected probe outcome is a
clean failure, not a connection.

## Deliverables

- `docs/pi-readiness/README.md` — first-session runbook separated into
  Phase 0 artifacts -> Phase 1 reachability -> Phase 2 read-only SSH
  inventory -> Phase 3 camera capture -> Phase 4 deployment gate, plus
  Section 6 stop conditions. Includes: exact BatchMode SSH probes,
  `rpicam-still` / `libcamera-still` detection order, timestamped
  `/tmp/quberon-camera-<UTC>.jpg` capture + `scp` + Pi/Mac sha256 match +
  `file` verification, deployed commit/service inventory (with the
  honest limit that rsync deploys carry no `.git`, so no deployed commit
  is readable on the Pi), CA-verified healthcheck, rollback path from
  `ROLLBACK.md`, and stop conditions.
- `scripts/pi_readiness_check.sh` — read-only probe. Phases 0-2/3 of the
  runbook: local artifact check, ping, one BatchMode
  (`BatchMode=yes ConnectTimeout=8 ConnectionAttempts=1
  StrictHostKeyChecking=yes`) SSH inventory, camera-stack name detection.
  No install, apt, pip, rsync, scp, sudo, systemctl mutation, nmcli
  mutation, reboot, Pi file write, or camera capture in the script;
  no secret contents printed (presence/mode only for config files).
  Exit codes: 0 ok, 2 local prereq, 10 ping fail, 11 SSH fail.
- Evidence: `docs/pi-readiness/evidence/local-failure-mode-attempt1.txt`,
  `docs/pi-readiness/evidence/local-failure-mode-attempt2.txt`.

## Attempts (graph-harness: 3 max, then blocker)

Attempt 1 — probe before runbook README existed.
Command: `scripts/pi_readiness_check.sh` (Mac, 2026-11-06T06:43:49Z).
Result: Phase 0 warned `missing local artifact: docs/pi-readiness/README.md`
(expected at that point), Phase 1 ping to 10.77.0.2: 3 transmitted,
0 received, 100% loss; script exited `10` with STOP guidance. No hang,
no prompt, no SSH attempt, no secret output. PASS for failure mode.
Raw output: `docs/pi-readiness/evidence/local-failure-mode-attempt1.txt`.

Attempt 2 — probe after runbook README created.
Command: `scripts/pi_readiness_check.sh` (2026-11-06T06:44:27Z).
Result: Phase 0 all five artifacts `present`; Phase 1 ping failed
identically; exit `10`. Improvement over Attempt 1 confirmed (artifact
warning gone). Raw: `.../local-failure-mode-attempt2.txt`.
Forbidden-pattern grep over the script: only comment/doc lines mention
install/rsync/sudo words; secret-print grep: none found. `sh -n`: OK.
shellcheck: not installed locally (skipped, not claimed as a pass).

Attempt 3 — not needed for the probe's failure gate (Attempt 2 passed it).
Success-path (ping/SSH/camera) testing is deliberately NOT attempted:
the Pi is off and accessing it is out of scope for this Tier 1 node.
That path remains UNVERIFIED / NOT RUN, to be exercised in the first
real session under the runbook.

## Local verification

- `sh -n scripts/pi_readiness_check.sh` -> OK.
- `make test` (Python 3.11.15 venv via `make setup`) -> `202 passed`.
  Note: an initial venv built with system Python 3.9.6 gave
  `1 failed, 189 passed` (`int | None` syntax in `adapters/gnss.py`);
  that was a local interpreter error, not a repo failure, and is not
  claimed as a test result. The 202-pass run above is the claimed one.
- `git status`: only the three owned paths are new/changed.

## Honesty limits

- Pi success path, camera capture, health endpoint, deployed inventory:
  NOT RUN. Prior Pi facts cited in the runbook are dated 2026-11-02
  hypotheses to re-verify, not current claims.
- No claim is made about AP, e-ink, cellular, GNSS, or any physical robot.
- Next ready node: first supervised Pi session following
  `docs/pi-readiness/README.md` Phases 0-4, with the Phase 4 human
  deployment gate. No deploy is authorized by this prep.
