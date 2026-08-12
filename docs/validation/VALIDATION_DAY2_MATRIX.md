# CARS — Validation Campaign 2 (BULLETPROOF): scenario matrix + pass criteria
_2026-07-23 night run. Predefine the verdict BEFORE firing. Whole integrated system: live tank process (PLC1 Sim DB7),
PLC2, HMI (.2.9), EWS (.2.55), relay Q0.3, remediation agent (.2.45), A2 allowlist, A3 DPI, A4 rulebook, A5 rate, updated dashboard._

## States (S)
- **S1 ARMED** — proactive default-deny + reactive enforcement ON (normal posture).
- **S2 DISARMED** — enforcement OFF; decisions logged `MONITOR` (would-block). Baseline = what CARS prevents.
- **S3 MAINT-ON** — maintenance window open; dangerous ENG ops from an AUTHORISED role permitted-with-monitoring (`MAINT`).
- **S4 CONTROLLER-OFF** — os-ken stopped; OVS `fail_mode=secure` holds last policy (fail-secure). No new reactive decisions.
- **S5 CONTROLLER-RECOVERING** — controller restarts; re-syncs; enforcement resumes; no exploitable gap.

## Attack classes (A) → MITRE ATT&CK for ICS
| id | attack | technique | tool |
|----|--------|-----------|------|
| A1 | recon / scan | T0846 Discovery | nmap, `mb_attack.py scan`, `s7_write.py --read` |
| A2 | unauthorised command / manip of control | T0855 / T0831 | `s7_write.py` output write, `mb_attack.py coil` |
| A3 | modify parameter | T0836 | DB / holding-register write |
| A4 | device stop / restart | T0816 | `s7_write.py --stop/--start` |
| A5 | program download | T0843 | `mb_attack.py program`, S7 program |
| A6 | **sensor false-data injection** | T0856 Spoof Reporting | `s7_write.py --dbspoof` (novelty) |
| A7 | DoS / flood (legal-op volumetric) | T0814 | `s7_write.py --storm`, `cars_dos_flicker.sh` |
| A8 | spoof / ARP poisoning | T0856 | IP/MAC spoof vs GUARD |
| A9 | evasion | — | slow/frag, S7CommPlus (honest boundary G3) |
| A10 | multi-source / distributed | T0814 | Kali insider .2.77 + IT VM .2.1 concurrent |

## Targets (T): PLC1 .2.10 (live tank), PLC2 .3.10, HMI .2.9, EWS-path .2.55

## Cross-cutting checks (every scenario)
- **C1 process-harm** — tank `Level` (DB7) stays in a safe band or is restored; relay Q0.3 not driven to a harmful state. **No physical harm, ever.**
- **C2 false-positive / "hallucination"** — legit allowlisted flows NEVER blocked: HMI↔PLC control loop, authorised reads, remediation writes. **CARS never REFUSEs the critical loop.**
- **C3 remediation** — sensor attacks (A6) → agent restores last-good (`REMEDIATE` rows), process maintained.
- **C4 load/stress** — sustained/multi-source flood: MTTM stable, controller no-crash, legit traffic not starved.
- **C5 failure-mode/gap** — S4 fail-secure holds; first-packet reality (CC-54, ~11 ms); documented boundaries hold honestly (G1 compromised endpoint, G3 S7CommPlus, G5 NAT identity collapse, G6 single controller).

## Expected-outcome grid (the predefined verdict)
| state | A1 recon | A2/A3 cmd/param | A4 stop | A5 program | A6 sensor | A7 DoS | A8 spoof | critical loop (C2) | process (C1) |
|-------|----------|-----------------|---------|-----------|-----------|--------|----------|--------------------|--------------|
| **S1 ARMED** | MONITOR/BLOCK per policy | **BLOCK→ISOLATE** ENFORCED | BLOCK/ISOLATE | BLOCK/ISOLATE | **BLOCK + REMEDIATE** | THROTTLE→BLOCK/ISOLATE | **GUARD drop** | **ALLOW (never cut)** | safe/restored |
| **S2 DISARMED** | MONITOR | MONITOR (lands) | MONITOR (lands) | MONITOR | MONITOR + **REMEDIATE still heals** | MONITOR | MONITOR/drop | ALLOW | attack visible; agent heals |
| **S3 MAINT-ON** | — | ENG from EWS = **MAINT-authorised**; unauth src still BLOCK | MAINT if authorised | MAINT if authorised | BLOCK+REMEDIATE (not an ENG op) | THROTTLE/BLOCK | GUARD drop | ALLOW | safe |
| **S4 CTRL-OFF** | last-policy holds | **existing blocks persist; no NEW flow admitted** | held | held | agent still heals (autonomous) | held | GUARD held | ALLOW (loop pre-admitted) | safe (fail-secure) |
| **S5 RECOVER** | resumes | enforcement resumes, re-syncs | resumes | resumes | resumes | resumes | resumes | ALLOW | safe |

## Pass criterion (per cell)
`actual CARS decision == expected` AND C1 (no harm) AND C2 (no false-positive) AND logs corroborate across audit + agent feed + dashboard. Any deviation → GAP row in the audit report (expected vs actual vs root-cause vs is-it-an-honest-boundary).

## Deliverable
`VALIDATION_DAY2_REPORT.md` — per-scenario result, the MITRE coverage table, C1–C5 verdicts, MTTM/load numbers, and an explicit **gap/limitations** section (honest boundaries vs genuine defects).
