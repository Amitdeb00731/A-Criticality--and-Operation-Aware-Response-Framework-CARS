# CARS — Session Handoff & Running Workflow

_Last updated 2026-07-20 (end of session). Purpose: meet at the lab next session with today's validation setup intact,
and hold the standing between-sessions workflow._

---

## RESUME 2026-07-23 (end of a big session)
Since 07-20: **P1 novelty complete** (CC-72 block-AND-maintain on hardware), **unified remediation feed** in the dashboard
(CC-73: live card + Decision-Log RESTORE/REMEDIATE rows, three-source corroboration at 21:37:43 & 22:20:40), live tank
process on real PLC1 (Sim DB7), EWS (.2.55), HMI operator-deception figure (D1), remediation agent as systemd service
(`cars-remediation`, .2.45 in remns), dashboard reconciled + fixed (IIFE bug, steadiness cache, REMEDIATE mode, ISO timestamps).
See SYNC_STATE.md for master↔deployed truth and the operating rules (restart dashboard + cache-bust after edits; enx USB-NICs
emit benign IPv6 churn — silenced).

**DONE 2026-07-24 (late):** Validation Campaign 2 COMPLETE (VALIDATION_DAY2_REPORT.md — PASS, 1381/1501 ALLOW, MTTM 12.2ms,
all 5 states, C1-C5, fail-secure, honest boundaries). Disarmed worst-case "devastation" baseline run (CC-75): raw unprotected
sensor/relay carnage captured (evidence `~/cars_evidence_passA_*.csv` on Dell#1 — FOLD INTO REPORT next session); 2 findings —
T0816 CPU stop/start rejected by S7-1200 firmware (attack vector closed on this HW), PLC self-drops excess concurrent S7 sessions.
Testbed put down SAFE: re-armed, agent active, blocks empty, process cycling, program intact.

**Next tracks:**
0. Fold `cars_evidence_passA_*.csv` (upload it) into VALIDATION_DAY2_REPORT.md as the unprotected-baseline figure. (Pass B agent-on-disarmed already covered by the 137-write/47-restore result — skip.)
1. **VALIDATION CAMPAIGN 2 (bulletproof)** — DONE (see above). — heavy, professionally-crafted, all-scenario integrated validation of the WHOLE
   system now running together (process + EWS + HMI + relay Q0.3 + remediation + updated dashboard). Scenario grid:
   {armed, disarmed, controller-off, controller-recovering, maintenance-window-on} × {recon, unauthorised command, param
   manip, device stop/restart, program download, sensor false-data, DoS/flood, spoof/ARP, evasion, multi-source} ×
   {PLC1, PLC2, HMI, EWS-path} — with predefined expected decision + pass criterion + process-harm check + false-positive
   (hallucination) check, plus load/stress and failure-mode/gap analysis, then a deep audit of all logs. Build the matrix +
   harness FIRST, then execute in one disciplined pass. (This is P3 rigor + integration hardening.)
2. **D2** — pair TB2 into the two-tank plant (TIA laptop → PLC2, need CPU order number), then HMI2 + symmetric sensor attack.

## A. State to bring back up ("today's validation setup")
Everything from today is deployed, tested, and file-locked (Decision Log through CC-66, A5_DESIGN.md, PAPER_MAP doc).

**Live services (should already be running; verify first):**
- Dell#2 controller: os-ken running `~/cars/cars_engine.py` **in tmux** (never Ctrl-Z — Ctrl-C + up-arrow to restart). A5 patched (rate/flood).
- Dell#1 systemd units: `cars-bridge` (bridge v4, A3+A5 rate), `cars-snort`, `cars-modbus`, `cars-hpot`, `cars-ins2`, `cars-seams`. Restart via `systemctl`, **never** pkill/nohup (double-instance hazard).
- Quick health check: `systemctl --no-pager status cars-bridge cars-snort cars-modbus | head`; controller tmux alive; `curl -s http://10.10.10.1:8080/cars/defense`.

**Ready-to-run harnesses (Dell#1, all `sudo bash`):**
- `cars_validate_all.sh` — consolidated both-cells regression (general + ICS + agendas + additions), one verdict.
- `cars_showcase.sh` / `cars_showcase_plc2.sh` — audible arm/disarm on TB1 / TB2.
- `cars_dos_flicker.sh [HZ] [SECS]` — dual-PLC DoS-style flicker (disarmed baseline vs armed protection).
- `cars_rate_demo.sh` — A5 rate intelligence (ALLOW → THROTTLE → BLOCK → ALLOW on a legal read flood).
- Attack clients: `s7_write.py` (`--read/--readstorm/--storm/--flap/--stop`, `--hz/--secs/--val`), `mb_attack.py` (coil/diag/program/illegal/scan), `mb_client.py`.

---

## B. Next session = RIGOROUS VALIDATION DAY
**Start by locking a test matrix BEFORE firing anything** (today's lesson: predefine the verdict, don't chase artifacts).
Matrix columns: `scenario → attacker vantage → MITRE ATT&CK for ICS technique → expected CARS decision → pass criterion →
process-harm check`.

Scenarios to cover:
- **Load / stress testing** — sustained multi-source, concurrent attackers, controller/bridge under load.
- **Real deployed-VM attacks** (not just netns): **insider VM** (trusted OT segment) and **IT VM** (crossing IT→OT boundary).
- **DDoS** — volumetric, multi-source (exercises A5 rate + A2 default-deny).
- **Professionally-crafted ICS attacks** — realistic S7/Modbus command-injection, PLC stop/program, setpoint tampering.
- **Cleverly-crafted / evasive attacks** — DPI-evasion attempts, fragmentation, low-and-slow, trusted-conduit abuse.
- **Live process on BOTH PLCs** — deploy a real control process across TB1+TB2; **validate NO harm to the process** under every attack (the headline safety claim — CRITICAL→REFUSE, bounded/reversible).
- **MITRE ATT&CK for ICS coverage table** — map each scenario to techniques (e.g. T0855 Unauthorized Command Message, T0814 DoS, T0836 Modify Parameter, T0889 Modify Program, T0846 Remote System Discovery) → detect / block / miss.

**Boundaries to own up-front (from GAP_AND_NOVELTY.md), because a rigorous day WILL press them:**
- **G1** — a *compromised trusted endpoint* attacking over the CRITICAL conduit is by-design not enforced (safety cap). The insider-VM test hits this directly; frame it as a stated boundary.
- **G6** — Cell-2-*internal* attacks aren't mirrored to Snort; attacker VM placement determines what's inspectable.
- **G3** — reactive layer depends on the IDS; DPI-evasion is the clever-attack surface. A2 proactive still bounds unauthorized sources IDS-down.

---

## C. Standing between-sessions workflow (Amit's note, 2026-07-20)
Between lab sessions we will:
1. **Review more papers' notes** (continue from the Phase-0 set; Etxezarreta survey already mapped).
2. **Keep adding our own notes** to the corpus for later **referencing and write-ups** (related-work, methodology, evaluation).
3. **Benchmark / map / evaluate our build against each paper** — same rigor as the Etxezarreta pass: situate CARS on the
   paper's framework, mark covered / partial / not-covered honestly, and extract any future-work or novelty-comparison items.

**Convention for each new paper:** produce a `PAPER_MAP_<author>.md` (mapping + honest verdict + what it contributes to the
write-up), and fold reusable framing/gaps into the Decision Log / GAP_AND_NOVELTY.md. Target of the related-work chapter:
the focused novelty comparison against the closest 3–5 systems (the survey gives the taxonomy; individual papers give the
head-to-head delta).

---

## D. Paper-aligned process extensions — NEXT-SESSION AGENDA (from the Cárdenas-group papers, 2026-07-23)
_Basis: `PROCESS_and_PAPER_LEARNINGS.md`. Current state to build on: a REAL bang-bang tank process runs on PLC1 (S7-1200,
SCL cyclic OB, pump=`%Q0.3`, cycles ~ON 5 s / OFF 3 s); EWS = Windows/TIA at `.2.55` (role `ews`, on `ovsgw`, in the
dashboard); insider Kali `.2.77`; IT via GNS3 kill chain (`.2.1` SNAT). Program the PLCs point-to-point (unplug from Dell#1
→ laptop → download → replug SAME port). `.2.55/.2.77` registrations persist in the engine/a2_policy files._

**D1 — HMI visual + operator-deception attack (T0856), with CARS protecting operator-visible integrity.**
- Configure **HMI1 (TB1)** in TIA/WinCC to display `Tank.Level` (bar) + `Pump` (indicator) — operator screen for the process.
- Attack: write a **false `Level`** into the PLC `Tank` DB (classic S7 write-var `0x05`) from an untrusted source → HMI shows
  the wrong value (operator deceived). CARS detects the write as `CONTROL` → blocks it → HMI keeps the TRUE value. Contrast
  disarmed (HMI lies, process wrong) vs armed (blocked, correct). Caveat: a *compromised HMI endpoint* is G1 (out of scope).
- Bonus — **controller-DoS resilience:** kill the CARS controller (Dell#2) and show the *already-installed* OVS drop flows
  still block the attacker (fail-secure data plane) — a resilience result, and answers "attack the controller".

**D2 — Pair TB2 (PLC2 + HMI2) into the process (two-tank plant, like the paper).**
- Simplest: program PLC2 with a second independent tank loop (Tank_301, same SCL, point-to-point download), HMI2 display →
  two-tank plant, both cells CARS-protected.
- Faithful (coupled): make PLC1's fill depend on PLC2's level (paper's P101↔LIT301 coupling) → a **cross-cell PLC↔PLC data
  exchange** over the NAT/transit that CARS mediates — a novel "protect inter-cell control comms" angle (more setup).

**D3 — Sensor false-data-injection attack (the paper's signature attack) on real hardware.**
- The "sensor" = the `Level` in the DB. Spoof it with a false-`Level` write. Show **unprotected** (disarm → tank over/
  underflows, relay wrong, HMI lies = the paper's overflow result) then **armed** (CARS blocks the write → control law keeps
  the tank in band). Our S7 write rule (`0x05`) already catches DB writes, so detection works.

**D4 — Mitigation, two levels (this is the NOVELTY-COMPARISON delta to write up):**
- **CARS (network-level) — "change the forwarding rule to drop":** block/isolate the sensor-spoof conduit so false data
  never reaches the PLC. Already proven; demo it on D3.
- **Papers (process-level) — "change the source of readings":** replace the compromised sensor with a **model-estimated /
  last-good value** (virtual sensor / state estimation) so the loop keeps running *correctly* during the attack. CARS does
  NOT do this — it is the **future-work extension**. Optional prototype: on detecting sensor tampering, feed the PLC a
  last-good/estimated `Level`. Write-up framing: CARS bounds the attacker at the network with a safety cap; the Cárdenas
  group maintains the process via estimation; a combined system does both.

**Also still open (from validation day):** multi-source concurrent DDoS + load/latency numbers; DPI-evasion (R13/G3); R14
compromised-trusted CRITICAL-loop live demo (G1); tune `A5 FLOOD_RATE` so bursty EWS/HMI polling isn't throttled; add an
S7CommPlus download-request DPI rule (CC-68 boundary).
