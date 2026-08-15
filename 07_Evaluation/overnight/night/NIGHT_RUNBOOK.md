# Overnight CARS stress campaign — runbook

A single orchestrated 12–14 h run that exercises all seven areas and captures the
evidence, then self-heals and stays green. Runs on **Dell 1**. Built from the
existing harness interfaces (`cars_campaign_lib` idioms, `s7_write.py`,
`mb_attack.py`, the `/cars/*` API, the b2 single-clock MTTM method). I could not
test these on the live rig, so **do the dry-run in step 3 before committing to the
night.**

## What it does (maps to your seven scripts)
1. `night_monitor.sh` — continuous mirror + PLC-port capture (rotating hourly) and a per-minute health/behaviour snapshot (`monitor.csv`).
2+5. `night_attack_battery.sh` — rotates realistic OT vectors (unauthorised connect/write/control/stop, Modbus write, FDI sensor-spoof low & high, scan).
3+4. Every attack is measured by `measure_attack` in `night_lib.sh`: single-clock **MTTM**, **leaked frames at the PLC port**, response, and `hard_timeout` → `mttm_all.csv`.
6. `night_ddos.sh` — bounded sustained diverse-source flood through the real Snort→bridge→controller pipeline, sampling probe MTTM + alert rate + controller decide-time under load → `ddos.csv`.
7. `night_gaphunt.sh` — genuine attempts at the documented residuals (fragmentation, sub-poll transient, TCP-seq injection, bounded state-exhaustion, half-open pool, rare Modbus codes) → `gaphunt.csv`.

### Coverage extensions (close the covered-but-thin / not-covered items)
8. `night_coverage.sh` — (A) full **response ladder**: ALLOW / REFUSE (safety loop, never cut) / THROTTLE (real SENSITIVE write installs a meter) / DEFLECT (forced deception redirect) recorded to `ladder.csv`; ISOLATE + BLOCK come at scale from the battery. (B) four-tier + **Cell-2 sweep** — identical forbidden control against CRITICAL PLC1, HIGH PLC2 (Cell-2 via NAT), MEDIUM historian, LOW Modbus, so the 75/60/45/30 s `hard_timeout` ladder is captured at scale (`mttm_all.csv`, labels `tier_*`). (C) **GUARD anti-spoof** probe — spoofed protected identities from the attacker port, `/cars/guard` drop-counter delta. (D) **authenticated-API** probe — unauthenticated `POST /cars/{defense,restore,reload}` must return 401 and CARS must stay armed → `controlplane.csv`. Runs every `COV_EVERY` cycles (default 4).
9. `night_fpstress.sh` — **adversarial-benign false-positive stress**: noisy-but-legitimate traffic (varied-rate legit reads + odd-but-valid offsets + ARP/mDNS broadcast storms from allowlisted sources) while watching for any reactive rule installed against a legit source or any legit conduit removed. A false positive = any non-zero count. → `fpstress.csv`. Runs every `FP_EVERY` cycles (default 10). Closes the "0% FP shown only on clean traffic" point.
10. `night_remediation.sh` — bounded **last-good restore** test: a short low-rate FDI from an allowlisted host, watching whether the remediation agent was invoked (restores counter climbs, level restored) or the fast cut pre-empted any drift (no restore needed) — both honest outcomes. Aborts on any tank-level excursion. → `remediation.csv`. Runs every `REM_EVERY` cycles (default 10).

**Left as honest caveats (not automated):** controller-crash / control-plane failover, trusted-insider slow-and-low within the operating envelope, and encrypted-protocol / TLS DPI. These are documented as limitations rather than staged, because staging them safely on the live rig would risk the process or misrepresent what CARS claims.

## Safety rails (built in)
- Cookie-scoped deletes only (`cookie=0xca/-1`), never by src/dst.
- Green-check + self-heal each cycle; if unhealthy, attacks pause and monitoring continues.
- **Never** `del-controller` (that froze the process before).
- The two risky gap probes (state-exhaustion, half-open) abort if the process goes offline.
- Leaves the rig armed and green; writes `greencheck_start/end.txt`.

## 1. Prerequisites — verify these rig-specific values first
```
# interfaces used by the captures — confirm names:
ip -br link | grep -E 'snort0|enx'      # mirror = snort0 ; PLC1 port = enx9c69d331d874 (edit night_lib.sh if different)
# attack clients present:
ls /home/msclab/s7_write.py /home/msclab/mb_attack.py
ls /home/msclab/frag_s7_write.py        # optional (fragmentation probe skips if absent)
# scapy present for the DDoS + gap probes:
python3 -c 'import scapy; print("scapy ok")'
# API token readable:
cat /home/msclab/cars/api_token >/dev/null && echo token-ok
```
Edit the interface name / client paths at the top of `night_lib.sh` if any differ.

## 2. Green baseline
```
bash 07_Evaluation/overnight/green_check.sh   # must be green before starting
```

## 3. DRY RUN (one short cycle — do this before the night)
```
cd 07_Evaluation/overnight/night
D=/home/msclab/night_$(date +%Y%m%d)
sudo NIGHT_ROOT=$D ROUNDS=1 bash night_attack_battery.sh   # ~1 min; also proves sudo runs without a prompt
cat $D/logs/mttm_all.csv
sudo NIGHT_ROOT=$D bash night_coverage.sh                   # ~2 min; proves ladder/tier-sweep/GUARD/auth-API probes work
cat $D/logs/ladder.csv $D/logs/controlplane.csv
bash ../green_check.sh                                       # confirm still green
```
If the battery logs sane MTTM values and the rig is green, proceed. If a command
errors (interface, client path, scapy), fix it and re-dry-run.

## 4. Launch the full night — fully unattended (walk away, come back when done)
Yes, this is designed to run start-to-finish with no mid-run intervention. Two
things make that safe, and both are enforced at launch:
- **Run as root** so no `sudo` password prompt can ever hang it mid-run. The
  orchestrator's preflight aborts immediately (while you are still there) if it is
  not root/passwordless-sudo, if an attack client is missing, or if the rig is not
  green — so an unrunnable night fails at second 0, not at hour 3.
- It launches the monitor and all phases itself, self-heals and green-checks each
  cycle, bounds every capture and flood with `timeout`, caps pcap disk use with a
  headers-only snaplen + a disk guard, and writes `SUMMARY.txt` at the end.

```
cd 07_Evaluation/overnight/night
D=/home/msclab/night_$(date +%Y%m%d)            # fixed output path (root's $HOME differs)
# detached in tmux so it survives logout; run as root:
tmux new -d -s cars "sudo NIGHT_ROOT=$D HOURS=14 bash night_orchestrator.sh"
#   ... or without tmux:
# sudo NIGHT_ROOT=$D HOURS=14 nohup bash night_orchestrator.sh >/tmp/cars_night.out 2>&1 &
```
After launching, confirm it actually started (preflight passed) before you leave:
```
sleep 20; tail -5 $D/logs/campaign.log        # should show "preflight passed ... Safe to walk away"
```
If instead you see `PREFLIGHT FAILED`, fix the one thing it names and relaunch — do
not walk away until you have seen "preflight passed".
Knobs: `HOURS` (default 14), `DDOS_EVERY` (cycles between DDoS phases, default 6),
`GAP_EVERY` (default 8), `COV_EVERY` (coverage pass, default 4), `FP_EVERY` (FP stress,
default 10), `REM_EVERY` (restore test, default 10), `DDOS_PPS` (default 200, raise
cautiously), `GAP` (inter-attack gap, default 4 s).

### Optional: add the real Kali VM as an attacker vantage
The namespaces give throughput; the real Kali VM gives the realistic attacker path
(`.2.77` on-segment). Off by default. To include it:
```
# prereq: passwordless SSH from Dell 1 to Kali (its mgmt/eth0 interface up),
# and the S7 client on Kali at /home/msclab/s7_write.py
sudo ssh msclab@<kali-mgmt-ip> true   # must succeed without a password AS ROOT
# (the campaign runs as root, so root's SSH key must be authorised on Kali;
#  install it with:  sudo ssh-keygen -t ed25519 -N '' -f /root/.ssh/id_ed25519;
#  sudo ssh-copy-id msclab@<kali-mgmt-ip> )
# then launch with:
D=/home/msclab/night_$(date +%Y%m%d)
tmux new -d -s cars "sudo NIGHT_ROOT=$D HOURS=14 USE_KALI=1 KALI_SSH=msclab@<kali-mgmt-ip> bash night_orchestrator.sh"
```
Notes: Kali single-injection attacks are measured on the same Dell-1 mirror clock
and logged with `kali_` labels in `mttm_all.csv`, so the at-scale MTTM then
includes real-VM path samples, not only namespaces. Kali runs every `KALI_EVERY`
cycles (default 3). A real-VM *sustained flood* (`KALI_DDOS=1`) is cut in about a
second, not 7.6 ms, because a continuous flood interacts with the 3 s dedup window
— report it as the sustained-flood cut time, not a single-injection reaction
window (consistent with the two-pivot section). The `.1` NAT pivot is already
captured in the report, so drive that one manually if you want it re-measured;
the overnight automation covers the common on-segment `.77` case. If Kali is
"confined to OT" (eth0/eth2 down for the honest-insider posture) it cannot be
SSH-driven — either bring mgmt up for the night, or launch `night_kali.sh` on Kali
by hand.

## 5. In the morning
```
cat "$HOME"/night_*/logs/SUMMARY.txt          # auto-generated summary
bash 07_Evaluation/overnight/green_check.sh   # confirm the rig survived green
```
Then copy the results into the repo and upload:
```
cp -r "$HOME"/night_$(date +%Y%m%d)/logs  <repo>/07_Evaluation/overnight/results/night/
```
Upload `logs/` (the CSVs + SUMMARY.txt + greencheck_start/end.txt). Keep the pcaps
locally unless a specific one is needed (they are large). I then fold the fresh
figures in and **reconcile any shifted headline number to the overnight run (R10)** —
if the at-scale MTTM or a gap outcome differs from what the report says, the report
gets the fresh figure, honestly.

## Only after the results are folded in and validated: disassemble the testbed.
