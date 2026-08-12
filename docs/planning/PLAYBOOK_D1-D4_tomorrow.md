# TOMORROW — D1–D4 execution playbook (process extensions on real hardware)

_2026-07-23 prep for the lab. Goal: run it, don't design it. Order = highest-value first: sensor attack + the P1 novelty,
then HMI visual, then TB2 pairing, then controller-DoS resilience. Everything is on real hardware. Point-to-point PLC
programming = unplug PLC from Dell#1 → laptop → download → replug SAME port (CARS-invisible, topology intact)._

## 0. Pre-flight (bring the testbed up + verify green)
- Power: `hAP → teaching boxes → Dells`. Auto-restores fire (OVS ports, seams, services, docker). Start the controller in
  its tmux (Dell#2). Launch GNS3 (Dell#1). Boot the Kali VM; the EWS Windows/TIA laptop on `ovsgw` (`.2.55`).
- Verify: `systemctl is-active cars-bridge cars-snort cars-modbus`; `curl -s http://10.10.10.1:8080/cars/defense`;
  confirm PLC1's Q0.3 is cycling (the process auto-resumed from flash). Insider `.2.77` read → ALLOW.

## 1. D3 — Sensor false-data-injection attack (the Cárdenas signature attack)
**The "sensor" = the `Tank.Level` DB** (the value the control law reads). Attacking it = an external S7 write that pins it.
- **Attack (pin the level LOW so the pump never stops = overflow):** from an attacker, write a false `Level` (e.g. 20.0)
  repeatedly. Since the OB reads `Level` then increments it, a sustained overwrite to 20 holds it < LowL(30) → `Pump` stays
  TRUE → **Q0.3 stuck ON = the tank "overflows"** (pump never cuts). This reproduces the paper's LIT101→overflow result.
  - Tooling: extend `s7_write.py` with a DB-write mode, or use snap7 `db_write` to `Tank.Level`. (Prep tomorrow: add
    `--dbspoof <db> <val>` writing a REAL to the Tank DB offset; confirm the DB number/offset from TIA — DB is non-optimized.)
- **DISARMED run:** relay stuck ON, HMI shows Level=20 (low) while pump runs = operator deceived. = the unprotected baseline.
- **ARMED run:** the DB write is S7 write-var `0x05` → CARS classifies `CONTROL` → BLOCK/ISOLATE the attacker → its writes
  stop reaching the PLC → the internal increment resumes → **Level oscillates normally, pump cycles = process maintained.**

## 2. D4 / P1 — "block AND maintain" (the NOVELTY)
Two rungs; do rung A (clean, achievable), then attempt rung B (the explicit state-estimation, the real differentiator):
- **Rung A — maintain-by-prevention (primary claim):** ARMED, CARS blocking the tamper prevents corruption; the PLC's own
  loop continues correct. Demonstrated directly by D3-armed. Contrast disarmed(overflow) vs armed(held). This alone is
  "network-level block that *guarantees* process continuity on real hardware" — already beyond pure IDS-response.
- **Rung B — maintain-by-substitution (borrow the paper's estimation, the novel stretch):** a small **CARS remediation
  agent** (Python on Dell#1) tails the audit; when it sees a `CONTROL`/tamper decision on `.2.10`'s `Tank.Level`, it writes
  the **last-good `Level`** back to the PLC from an authorized `remediation` identity — actively restoring the correct value
  even if one bad write landed (CC-54 first-packet). Setup: register a `remediation` role IP + a rulebook rule permitting
  its write (like the controller-exemption pattern), agent remembers the last read-good level and re-asserts it on attack.
  → This is CARS *bounding the attacker AND maintaining the state via estimation*, on hardware — the sentence for the viva.
  - If Rung B setup runs long, ship Rung A (fully sufficient for the claim) and mark Rung B as the extension.

## 3. D1 — HMI1 visual + controller-DoS resilience
- **HMI1 display (TIA/WinCC):** add a screen showing `Tank.Level` (bar/numeric) + `Pump` (indicator). Steps: in the project,
  add/open the HMI device (KTP panel), add I/O fields bound to `Tank.Level` and `Tank.Pump`, download to HMI1. Now the D3
  attack is *visible* on the panel (shows the false low level while pump runs). Great figure for the report.
- **Controller-DoS resilience:** with an active block on an attacker, kill the CARS controller on Dell#2 (`Ctrl-C`). Show the
  attacker STILL blocked (the OVS drop flows persist = fail-secure data plane); the process keeps running. Restart controller.
  Answers "attack the controller" + a resilience result. (Note honestly: NEW detections stop while the controller is down.)

## 4. D2 — Pair TB2 into a two-tank plant
- Program **PLC2 (TB2)** with the same bang-bang tank loop (Tank_301), point-to-point download (unplug PLC2 from Dell#3 →
  laptop → download IP `192.168.2.10` in Cell-2 addressing → replug). Q0.2/Q0.3 relay = its pump. HMI2 display like D1.
- Result: a two-tank process, both cells CARS-protected (we already proved PLC2 op-aware). Re-run a sensor attack on PLC2 to
  show symmetry. (Coupled version — PLC1 fill depends on PLC2 level via cross-cell comms — is the optional stretch; needs
  cross-cell routing, defer unless time.)

## Deliverables to capture for the report (F2 figures)
- Disarmed-vs-armed **process traces** (Level/Pump over time, attack window marked) for D3/D4 — the headline no-harm figure.
- HMI screenshot showing the deception (false low level, pump on) vs protected.
- Controller-DoS timeline (block persists through controller down).
- Two-tank plant photo/diagram.
Log each as a CC-entry + into VALIDATION_DAY_RESULTS.md.

## Prep tonight (no lab): DONE = this playbook. Optional if awake: draft the `s7_write.py --dbspoof` + the remediation-agent
skeleton so they're paste-ready tomorrow. Otherwise first lab task is writing those two small scripts.
