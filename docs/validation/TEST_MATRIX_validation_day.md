# CARS — Rigorous Validation Day: Test Matrix (MITRE ATT&CK for ICS mapped)

_2026-07-20. Process under protection = the Q0.3 relay + the CRITICAL HMI↔PLC loop (no new logic). Attackers = real VMs
(insider + IT) to be stood up, plus existing netns for quick rows. Rule 0: every row has a PRE-DEFINED expected decision
and pass criterion; we do not judge outcomes after the fact. Technique IDs verified against attack.mitre.org (2026-07)._

## Conventions
- **Vantages:** `opns .2.31` = trusted operator (allowlisted, baseline legit) · `insider VM` = OT-segment host, unlisted ·
  `IT VM` = across the IT/OT boundary, unlisted · `atkns .2.66` = netns attacker (quick rows).
- **Expected decision** = the CARS decision line we predict (ALLOW / THROTTLE / BLOCK / ISOLATE / DEFLECT / REFUSE / [FLOOD]).
- **Pass criterion** = objective, checkable from audit/flows/client outcome.
- **Process-harm check** = (a) HMI↔PLC loop continuity counter never drops (Phase-2c style), (b) Q0.3 relay returns to safe
  (OFF) after the row, (c) legit operator traffic uninterrupted (zero collateral). A row only fully passes if harm-check = clean.
- **Reactive first-packet caveat (CC-54):** for a forbidden WRITE, the first packet may land (relay ticks ≤1) before the
  cut — pass = "cut within a few ms + attacker locked out", NOT "relay never moves".

## VM standup design (VD-1)
| VM | Placement | IP | Allowlisted? | Represents | Inspectable by CARS? |
|---|---|---|---|---|---|
| **Insider** | OVS port on `ovsgw` (OT L2, same segment as PLC1/Modbus) | `192.168.2.77/24` | **No** | compromised OT workstation / malicious insider | Yes — crosses ovsgw SPAN → Snort |
| **IT** | OVS port on an IT-side segment reaching OT only via the gateway/transit | e.g. `10.20.20.5/24` → OT via gw | **No** | external/IT attacker pivoting to OT | Yes if path traverses ovsgw transit (else G6) |

Both **unlisted** ⇒ A2 proactive default-deny should block them from the PLCs *before* any detection. Verify after standup:
reachability per vantage, and that Snort logs their traffic (mirror coverage).

---

## The matrix

### Discovery (VD-2)
| # | Scenario | Vantage | MITRE ICS | Expected CARS decision | Pass criterion | Harm |
|---|---|---|---|---|---|---|
| R1 | Network/host sweep | IT VM | **T0846** Remote System Discovery | A2 default-deny + per-source ISOLATE on scan pattern | PLC ports unreachable; scanner quarantined all-switches | none |
| R2 | Port scan .2.10:102 / .2.20:502 | Insider VM | **T0846** | Same; ISOLATE source | No service enumerated from unlisted host | none |

### Command injection / manipulation (VD-3)
| # | Scenario | Vantage | MITRE ICS | Expected CARS decision | Pass criterion | Harm |
|---|---|---|---|---|---|---|
| R3 | S7 write Q0.3, PLC1 | Insider VM | **T0855** Unauthorized Command Message / **T0831** Manipulation of Control | `S7 CONTROL => BLOCK` then `ISOLATE` | source cut ≤ ~10 ms; audit shows CONTROL/FORBIDDEN | relay ticks ≤1, loop OK, returns OFF |
| R4 | S7 write PLC2 (.3.10, cross-NAT) | IT VM | **T0855/T0831** | `S7 CONTROL => ISOLATE` | conduit cut (snap7 timeout) | relay ticks ≤1, loop OK |
| R5 | Modbus coil force FC5/15 | Insider VM | **T0855/T0831** | `MODBUS CONTROL => BLOCK/ISOLATE` | coil-force blocked | none |
| R6 | Modbus register write FC6/16 (setpoint) | Insider VM | **T0836** Modify Parameter | `MODBUS WRITE` flagged (SENSITIVE/FORBIDDEN) | parameter change flagged/blocked | none |
| R7 | S7 PLC-Stop (0x29) | Insider VM | **T0816** Device Restart/Shutdown | `S7 DIAG => BLOCK/ISOLATE` | stop attempt detected+blocked (defense-in-depth) | loop OK |
| R8 | S7/Modbus program download (FC43) | IT VM | **T0843** Program Download / **T0889** Modify Program | `PROGRAM => FORBIDDEN` | blocked; **and** allowed only for authorized EWS inside maintenance window (matches T0843 detection guidance) | none |

### Denial of service / impair control (VD-4)
| # | Scenario | Vantage | MITRE ICS | Expected CARS decision | Pass criterion | Harm |
|---|---|---|---|---|---|---|
| R9 | Volumetric DDoS to PLC (multi-source) | IT+Insider+atkns | **T0814** Denial of Service | A2 blocks unlisted sources + per-source ISOLATE + A5 rate | PLC comms protected; **legit operator zero timeouts** | loop OK |
| R10 | Read/poll flood (legal op) | Insider VM | **T0814** | `[FLOOD] THROTTLE → BLOCK → ALLOW` (recover) | graded + reversible, single reads still ALLOW | none |
| R11 | Write storm (forbidden burst) | Insider VM | **T0814/T0831** | immediate `ISOLATE` | source quarantined, loop untouched | relay ticks, returns OFF |

### Spoofing / evasion / trusted-path (VD-5)
| # | Scenario | Vantage | MITRE ICS | Expected CARS decision | Pass criterion | Harm |
|---|---|---|---|---|---|---|
| R12 | IP/MAC spoof of HMI/operator identity | Insider VM | **T0856** Spoof Reporting Message (prevented via anti-spoof) | GUARD T0 drop (binding mismatch) | spoofed frames dropped at T0 | none |
| R13 | DPI evasion (fragment / low-and-slow one-shot) | IT VM | (tests **G3** detection dependency) | reactive may MISS a lone one-shot (honest); A2 still bounds unlisted source | A2 blocks unlisted source; any reactive miss measured + reported, not hidden | none |
| R14 | Compromised trusted endpoint over CRITICAL conduit (source as .2.9 HMI) | Insider VM w/ stolen identity | **T0831** via trusted conduit | **REFUSE** (loop never cut) — detection/alert only | documented boundary **G1**: CARS does not enforce the CRITICAL loop; GUARD makes identity theft hard but endpoint compromise is out of scope | this is the one row where a write can land — state it honestly |

### Cross-cutting (VD-6)
- **Process integrity:** run an HMI↔PLC loop-continuity counter throughout the whole day; assert it never drops during any
  row (target: monotonic, like Phase-2c 4032→4324). Relay returns to OFF after every row.
- **Load / stress:** sustained concurrent multi-attacker (all vantages at once); record controller decide+enforce latency
  distribution, MTTM, legit-traffic timeouts (target 0), collateral (target 0).
- **Verdict artifact:** a MITRE ATT&CK for ICS **coverage table** — technique → detect? → block/mitigate? → miss (with why) —
  plus one consolidated pass/fail, feeding the evaluation chapter.

## Honest boundaries carried in (own them, don't get caught by them)
- **G1** — R14: compromised trusted endpoint over the CRITICAL loop is by-design not enforced (safety cap).
- **G3** — R13: reactive layer depends on the IDS; a lone DPI-evading packet can slip; A2 still bounds sources.
- **G6** — any attack sourced *inside* Cell-2 (on ovs2/Dell#3) is not mirrored → not inspected; VM placement determines this.

Sources for MITRE mappings: [T0855](https://attack.mitre.org/techniques/T0855/), [T0846](https://attack.mitre.org/techniques/T0846/), and the ATT&CK for ICS matrix at [attack.mitre.org](https://attack.mitre.org/).
