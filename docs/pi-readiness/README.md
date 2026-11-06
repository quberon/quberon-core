# Pi readiness — first-session runbook (Wave 6, Tier 1 prep)

Status: PREP ONLY. The Pi is powered off / charging. Nothing in this document
has been run against the Pi in Wave 6, and nothing here authorizes a deploy.
Base: `origin/main` @ `65f5271aa59d90a76ec53a0f0f6d750f9e566f4b`.

Scope owned by this node: `docs/pi-readiness/**`,
`scripts/pi_readiness_check.sh`, `progress/Pi-readiness.md`.
Out of scope: accessing the Pi, deploying, changing services, AP changes,
e-ink/SPI, cellular, GNSS writes, any physical robot.

Principles carried from repo context (`DECISIONS.md`, `ROLLBACK.md`,
`INVENTORY.md`, `scripts/*`, skill `single-board-computer-setup`):

- D6: Ethernet `10.77.0.2/24` SSH is the management/recovery anchor.
  Mac peer is `10.77.0.1/24`, no gateway/DNS on Ethernet,
  `ipv4.never-default=yes` on the Pi; Wi-Fi stays the Mac default route.
- D7: Project AP is `10.99.0.1/24`. Do not touch it in the first session.
- Guest-Wi-Fi client isolation is intentional. Never "fix" SSH by disabling
  it, and never fall back to guest-Wi-Fi SSH as the management path.
- Simulation only (D1/D2). A `/healthz` OK or simulator STOP ack is not a
  physical stop. Do not word it as one.
- Separate layers: power != Ethernet link != OS boot != SSH auth != app
  health != camera framing. Prove each layer separately; earlier success
  is not evidence after a power/cable/topology change.
- Evidence before claim: record raw output, UTC, commits and hashes.
  A summary line where raw output was requested is a failed gate
  (GRAPH-HARNESS Part 5.8). Three attempts per gate, then blocker.

Known prior facts (dated, re-verify — do not assume): Pi 3B+, Debian 13,
hostname `quberon-pi`, user `quberon1`, camera 0 = OV5647 via
libcamera/rpicam, prior deploy at `~/quberon-robot-interface` (user service)
and/or `/opt/quberon-robot-interface` (system service) — `INVENTORY.md`,
2026-11-02. These are hypotheses for the first session to confirm, not facts
about the Pi today.

---

## Phase 0 — Artifacts (Mac only, no Pi contact)

Do this while the Pi is still off. Goal: the session starts from code, not
judgment (GRAPH-HARNESS Part 5.1-5.2).

```sh
git fetch --prune
git log -1 --format=%H origin/main        # expect 65f5271aa59d... or newer; record it
gh pr list --state open
git status --short --branch
sh -n scripts/pi_readiness_check.sh
ls -l scripts/deploy_pi.sh scripts/deploy_user_pi.sh scripts/healthcheck.sh scripts/setup_ap.sh
```

Record: Mac UTC (`date -u`), repo path, `git rev-parse HEAD`, branch,
open PRs. Confirm the deploy scripts' defaults still say
`PI=${PI:-quberon1@10.77.0.2}` and that `scripts/healthcheck.sh` defaults to
`https://10.77.0.2:8443`. If `origin/main` moved, note the new base — do not
silently rebase this prep onto it mid-session.

Gate 0: checkout clean or dirt understood, script syntax OK, base commit
recorded. If not, stop here; there is nothing to run against the Pi yet.

## Phase 1 — Reachability (Pi may now be powered, human present)

Prerequisites: human has connected power + direct Ethernet cable, HDMI
optional. Do not ask anyone to send passwords/keys in chat.

1. Inspect the Mac first, before guessing an address:

```sh
networksetup -listallhardwareports
ifconfig
netstat -rn -f inet
route -n get default        # must still be Wi-Fi, NOT the Ethernet cable
arp -an
```

Expect: Mac Ethernet `10.77.0.1/24`, Wi-Fi default route intact, internet
still works with the cable attached. If the default route moved to Ethernet,
fix Mac service order (Wi-Fi first) before touching the Pi.

2. Run the read-only probe. It pings, and only on ping success attempts one
BatchMode SSH inventory; it fails cleanly otherwise:

```sh
scripts/pi_readiness_check.sh; echo "exit=$?"
```

Exit `10` = ping failed. Exit `11` = SSH failed. Exit `2` = local prereq.
Any non-zero exit is a STOP for this phase (see section 6), not a prompt to
try passwords, `StrictHostKeyChecking=no`, or Wi-Fi SSH.

If you need link-local discovery because `10.77.0.2` does not answer but the
cable shows link, use the skill's IPv6 path on the *actual* wired interface
(do not assume `en0`):

```sh
ping6 -c 3 -I <WIRED_IFACE> ff02::1%<WIRED_IFACE>
ndp -an
```

A ping/SSH banner proves only that layer, at that moment. It does not prove
auth, app health, or camera.

Gate 1: ping to `10.77.0.2` succeeds AND Mac default route is still Wi-Fi
AND internet still works. Record raw ping output.

## Phase 2 — Read-only SSH inventory (BatchMode, exact probes)

Preferred: `scripts/pi_readiness_check.sh` (single SSH session, read-only).
If running probes manually, every command uses the same options — BatchMode
(no password prompt, no hang), bounded timeout, strict host-key checking:

```sh
SSH="ssh -o BatchMode=yes -o ConnectTimeout=8 -o ConnectionAttempts=1 -o StrictHostKeyChecking=yes quberon1@10.77.0.2"

$SSH 'hostname; date -u +%Y-%m-%dT%H:%M:%SZ; uname -a'
$SSH 'cat /etc/os-release; tr -d "\000" < /proc/device-tree/model; echo'
$SSH 'ip -br addr; ip route'
$SSH 'nmcli -t -f NAME,TYPE,DEVICE connection show --active'
$SSH 'uptime; df -h /; free -h'
$SSH 'command -v vcgencmd && vcgencmd get_throttled && vcgencmd measure_temp'
$SSH 'systemctl is-active quberon-robot-interface.service; systemctl --user is-active quberon-robot-interface.service'
$SSH 'ss -lntp | grep -E ":(22|8443)[[:space:]]" || true'
```

Deployed commit / service inventory — set expectations honestly first:
both deploy scripts use `rsync --exclude .git`, so the Pi copy normally has
**no `.git`** and no deployed commit hash can be read from it. Record the
Mac-side source commit at deploy time instead; on the Pi record presence,
paths, and timestamps:

```sh
$SSH 'ls -ld ~/quberon-robot-interface /opt/quberon-robot-interface 2>&1; ls -l ~/quberon-robot-interface/requirements.txt ~/quberon-robot-interface/app/main.py 2>&1'
$SSH 'test -d ~/quberon-robot-interface/.git && git -C ~/quberon-robot-interface rev-parse HEAD || echo "no .git in user deploy (expected)"'
$SSH 'systemctl --user --no-pager --full status quberon-robot-interface.service | head -40'
$SSH 'systemctl --no-pager --full status quberon-robot-interface.service | head -40'
```

Config: presence and permissions only. **Never** cat/print/copy any
`*.env`, `*.key`, secrets file, token, or password, on either machine:

```sh
$SSH 'for f in /etc/quberon-robot-interface/ca.crt ~/.config/quberon-robot-interface/ca.crt; do test -f "$f" && echo "present: $f" || echo "absent: $f"; done'
$SSH 'stat -c "%a %n" ~/.config/quberon-robot-interface/app.env ~/.quberon-robot-interface-secrets.env 2>&1 || true'
```

Healthcheck (read-only GET; on the Pi the system CA path is the
`scripts/healthcheck.sh` default second argument; for the user-service
deploy use the `~/.config/...` CA). A health pass proves the app answered
over Ethernet HTTPS at that moment — nothing about a physical robot:

```sh
$SSH 'curl --fail --silent --max-time 8 --cacert ~/.config/quberon-robot-interface/ca.crt https://10.77.0.2:8443/healthz; echo'
# or, once SSH-verified, from the Mac if the PUBLIC ca.crt was copied over (never the ca.key):
curl --fail --silent --cacert artifacts/quberon-ca.crt https://10.77.0.2:8443/healthz; echo
```

Gate 2: hostname/OS/model recorded, `eth0=10.77.0.2/24` confirmed, no
unexpected default route on the Pi, throttled `0x0` (or deviation recorded),
service state stated as active/inactive/absent (not assumed), deployed dir
and its no-`.git` limitation recorded, health result recorded verbatim or
marked NOT RUN with reason. Do not restart a stopped service to make this
gate pass — that belongs to the Phase 4 gate, with human approval.

## Phase 3 — Camera capture (first Pi write: a /tmp file only)

Detection first (read-only, also in the probe script):

```sh
$SSH 'for t in rpicam-still libcamera-still rpicam-hello libcamera-hello; do command -v $t || echo "absent: $t"; done'
$SSH 'rpicam-hello --list-cameras 2>&1 | head -20'
# older stack fallback:
$SSH 'libcamera-hello --list-cameras 2>&1 | head -20'
```

Pick exactly one capture tool: prefer `rpicam-still`, fall back to
`libcamera-still`. If neither exists, STOP this phase — do not install
anything in the first session.

Timestamped capture on the Pi (UTC stamp, `/tmp` only, nothing under the
deployed app dirs), then pull it back and verify on the Mac by hash + type.
The image itself is evidence only of what the sensor saw (lighting/framing
included); a dark/blurred frame proves the pipeline responded, not useful
framing (`INVENTORY.md` camera note):

```sh
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
$SSH "rpicam-still --nopic 2>/dev/null; rpicam-still -o /tmp/quberon-camera-$STAMP.jpg --timeout 2000"
# fallback if only libcamera-still exists:
# $SSH "libcamera-still -o /tmp/quberon-camera-$STAMP.jpg --timeout 2000"

scp -o BatchMode=yes -o ConnectTimeout=8 quberon1@10.77.0.2:/tmp/quberon-camera-$STAMP.jpg ./quberon-camera-$STAMP.jpg
$SSH "sha256sum /tmp/quberon-camera-$STAMP.jpg; ls -l /tmp/quberon-camera-$STAMP.jpg"
shasum -a 256 ./quberon-camera-$STAMP.jpg    # macOS; must match the Pi hash exactly
file ./quberon-camera-$STAMP.jpg             # must report JPEG, plausible size (>0, not an error page)
ls -l ./quberon-camera-$STAMP.jpg
```

Keep the local copy outside git unless a human approves committing it
(prior art: `artifacts/camera-eink-view.jpg` is excluded from deploy rsync).
Visually inspect the frame before claiming anything about the display,
framing, or focus. Do not delete the `/tmp` file from the Mac side as part
of "cleanup proof" — record its path; `/tmp` is transient by design.

Gate 3: exactly one tool path used, hashes match Pi<->Mac, `file` says JPEG,
visual-inspection note written (even if it is "dark/uninformative").

## Phase 4 — Deployment gate (decision point, NOT a deploy)

No deploy happens in the first session unless a human explicitly approves
it after Gates 0-3. At the gate, present — in this order — the base commit,
probe/inventory output, health result, camera result, and the exact deploy
command that *would* run. Prefer the read-only dry run first:

```sh
DRY_RUN=1 scripts/deploy_pi.sh     # rsync -n to a staging dir; changes nothing live
```

Then, only with explicit human approval in-session, choose exactly one path:
`scripts/deploy_pi.sh` (system service; needs interactive sudo on the Pi —
do not design around `sudo -n` succeeding later) or
`scripts/deploy_user_pi.sh` (unprivileged user service; must have linger:
`loginctl enable-linger quberon1`, verified `Linger=yes`, and survival
proven after SSH logout). Never run both. AP work (`scripts/setup_ap.sh`)
is a separate later gate: it requires Ethernet SSH verified, the Pi-local
rollback timer armed *and proven able to control the profile*, and the
secrets file present at mode 600 — its contents are never printed.

Rollback path (from `ROLLBACK.md`, rehearse verbally before any deploy):
Ethernet anchor is never removed; app rollback = disable/remove the unit
and only then, if fully removing the prototype, delete `/opt/...`,
`/var/lib/...`, `/etc/...` **after** backing up `/var/lib` if the audit
trail matters; AP rollback = down `Quberon-Demo-AP`, up the prior client
profile, never delete `aiwifi`/`eth0`. Before changing any Pi system
file/profile, copy the original to a timestamped dir under
`/var/backups/quberon-robot-interface/` and record the path.

Gate 4: human approval recorded, dry-run output reviewed, rollback steps
named, post-deploy healthcheck command named
(`scripts/healthcheck.sh https://10.77.0.2:8443 <ca.crt>` semantics). If any
element is missing, the deploy does not happen and that is a successful
gate outcome, not a failure to hide.

## Section 6 — Stop conditions (any one stops the session)

- Ping/SSH fails (probe exit 10/11), host key changed/unverified, or SSH
  would require a password prompt, `accept-new`, or `StrictHostKeyChecking=no`.
- Mac default route moved to Ethernet, or internet breaks with cable attached.
- `vcgencmd get_throttled` != `0x0`, unexpected Pi default route, or the
  active NetworkManager Ethernet profile is not the one you think it is.
- A secret, token, `.env`/key contents, or password would need to be printed,
  pasted in chat, or committed. Presence/permission checks only.
- Camera tools absent, capture hash mismatch, or `file` is not JPEG.
- Service is stopped and the only fix is restart/reinstall — that needs the
  Phase 4 human gate, not a probe-side fix.
- Any step would touch AP/Wi-Fi profiles, SPI/e-ink, cellular/GNSS writes,
  GPIO, or a physical robot. All are out of first-session scope.
- Three attempts at the same gate have failed (GRAPH-HARNESS gate rules).
  Record the blocker with evidence; do not weaken the gate to pass.

## Evidence to leave behind (first session)

- This runbook's Phase 0-2 raw outputs with UTC and commit.
- `scripts/pi_readiness_check.sh` output (exit code included).
- Camera file name, both sha256 hashes, `file` output, inspection note.
- A `progress/` update stating PASS/FAIL/BLOCKED/NOT RUN per phase,
  separating code-tested, deployed-on-Pi, physically-observed, simulated
  and mocked claims. Pi-offline failure-mode evidence for this prep lives in
  `docs/pi-readiness/evidence/local-failure-mode-attempt1.txt`.
