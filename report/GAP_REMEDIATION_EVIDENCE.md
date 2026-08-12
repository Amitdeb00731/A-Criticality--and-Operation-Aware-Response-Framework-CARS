# CARS gap remediation — evidence record

Purpose: the consolidated proof trail for the security gaps identified late in the project, each investigated on the live testbed, then fixed, tested, or framed. Every output below was captured fresh on the upstanding system (7–8 August 2026) with CARS armed; the rig was returned to green after each run (armed, all services active, `flow-audit ok:1`, `0xca`=0). This record backs the write-ups in Chapter 4 (`04_evaluation.tex`) and the appendix.

Legend: **FIXED** = implementation changed and re-validated; **MITIGATED** = new defence-in-depth layer added and validated; **TESTED** = evaluated fresh (a demonstrated limitation or capability); **FRAMED** = verified real but out of scope / unsafe to test on the live process, documented as a bounded limitation.

---

## Gap A — DPI defeated by TCP fragmentation  [FIXED]

**Gap.** The S7 rules matched the operation byte at a fixed packet offset (`content:"|05|"; offset:17`) with no stream reassembly, so a Write-Var split across two TCP segments was never recovered; the op fell to the source's base tier and was permitted.

**Fresh proof of the gap (allowlisted `.2.31`, armed):**
```
# fragmented (--split 14):
[*] Write-Var FRAGMENTED: seg1=14B seg2=22B (0x05 now in seg2)   ; PLC replied
audit:  192.168.2.31(scada) -> 192.168.2.10(plc) TCP => ALLOW (operational) - monitor only
snort:  CARS-S7-CONTROL-write only for 192.168.2.55 (the legit loop) — none for .31
0xca count: 0                                   # EVADED: no detection, no rule, write reached the PLC
# same write WHOLE:
audit:  FORBIDDEN 192.168.2.31(scada) -> 192.168.2.10(plc) S7 CONTROL => ISOLATE source 192.168.2.31 75s
0xca:   nw_src=192.168.2.31 ... actions=drop    # CAUGHT — only difference is fragmentation
```

**Fix (two parts; reassembly alone was insufficient).**
- `cars.conf`: `stream5_global` + `stream5_tcp: policy linux, ports both 102 502` (TCP reassembly on the ICS ports).
- `cars.rules`: S7 rules re-anchored PDU-relative, e.g. `content:"|03 00|"; content:"|32 01|"; distance:5; within:7; content:"|05|"; distance:8; within:9;` (match relative to the S7 job header, not a fixed offset).
- Intermediate result recorded honestly: with stream5 on but the offsets unchanged, the fragmented write **still evaded** (`.2.31 => ALLOW`, `0xca`=0) — proving the rule re-anchoring was necessary.

**After the fix (same fragmented attack):**
```
--split 14:  FORBIDDEN 192.168.2.31 ... S7 CONTROL => ISOLATE source 192.168.2.31 75s ; 0xca nw_src=192.168.2.31
--split 9 :  FORBIDDEN 192.168.2.31 ... S7 CONTROL => ISOLATE            # caught regardless of split point
legit .55 :  OPERATIONAL 192.168.2.55(ews) -> .2.10 READ/CONTROL => ALLOW   # no new false positive
```

**Verdict:** fragmentation gap closed; residual = overlapping-segment/timing evasion (general IDS problem) and rare-code recognition.
**Documented:** §4.5 (`sec:evaldpi`); Threats (detection-sensor paragraph); Appendix `lst:dpihard`, `lst:frag`; Appendix A.3 snapshot refreshed to the hardened rules.
**Artefacts:** frag harness `~/frag_s7_write.py`; `of_control.pcap` (the `OFPT_FLOW_MOD` decode, `lst:flowmod`).

---

## Gap B — trusted-insider process blind spot  [MITIGATED]

**Gap.** A trusted, allowlisted party acting within its permitted operations (compromised HMI/EWS/agent) is not cut by the network layer by design, so a process attack from such a party could go unchecked; CARS lacked process-variable anomaly detection.

**Investigation narrowed it (all on-device):**
- High-rate overflow is already covered — the FDI run from the trusted `.45` was flood-blocked:
  `192.168.2.45(remediation) -> .2.10 S7 CONTROL => [FLOOD 51 ops/s] BLOCK conduit 75s` ; FDI cut after **77 writes**; tank peaked in the mid-70s, no overflow.
- TIA/PLC program: fill thresholds `30/70` are constants in OB30; the `Setpoint` word (`%IW104`) is unused; `Sim.Level (DB7.0) = LevelIn(%ID100) * 20` is recomputed every scan → **no low-rate overflow path**.
- Remediation code: `tampered(lvl,prev) = (lvl < 25) or (lvl < prev-15)` — **low-side only**, blind to a rising/high level. `FLOOD_EXEMPT = {192.168.2.55}` — the remediation agent is not exempt (so its own high-rate abuse is also cut).

**Mitigation.** `cars_process_guardian.py` — an independent, **read-only, alarm-only** monitor adding the checks the remediation agent lacks: high-side envelope, symmetric rate, and liveness/stall. It never writes the PLC or touches enforcement.

**Validated fresh (guardian silent under normal load, then):**
```
# Demo 1 (low-rate denial): trusted .45 issues one authorised HMI_Stop
audit:      192.168.2.45(remediation) -> .2.10 S7 CONTROL => ALLOW (operational)   # network correctly permits it
process:    halted, tank frozen at 40.4%
guardian:   [GUARDIAN] ALARM STALL {level: 40.4, frozen_s: 12.0}                    # caught the denial (fresh 8 Aug run, cars_guardian.jsonl)

# Demo 2 (spoof-to-high): reported level pinned at 90 (real tank drains beneath)
remediation: status level=90.0, restores unchanged                                 # low-side agent stays SILENT (blind)
guardian:    [GUARDIAN] ALARM HIGH_LEVEL {level: 90.0, ceiling: 78.0}  + ALARM RATE # caught what the agent misses
observed:    HMI froze at 90 while the Factory IO tank drained low (the deception)
```

**Provenance note.** The STALL alarm above was re-captured fresh on 8 Aug and is in the harvested `logs/cars_guardian.jsonl` (`{"level": 40.4, "frozen_s": 12.0, "kind": "STALL"}`). The HIGH_LEVEL alarm is from the 7 Aug demo. On the 8 Aug re-run it could not be regenerated: pinning `%ID100` high needs a sustained write loop to hold the value against the Factory IO scan, but that high-rate loop from `.45` trips the flood backstop after a single write (`spoof_high` reported `interrupted (S7TimeoutError)`, `1 writes`), so the spoofed value never held the one poll the guardian needs. This is an incidental, honest confirmation that the volumetric overlay also resists the sustained high-rate writes a sensor-pin requires, on top of the runaway-agent backstop already shown in `flows/ovsgw_dump.txt`.

**Verdict:** the guardian catches the denial and the high-side spoof the existing agent misses; residual = a stealthy, in-envelope, slow manipulation (evades an invariant monitor); the guardian is detection, not prevention (prevention on the safety loop must not be automated).
**Documented:** §4.6 (`sec:evalguardian`); Threats (trusted-party boundary, with the flood-backstop nuance); Appendix `lst:guardian`, `lst:insider`.
**Artefacts:** `~/cars_process_guardian.py`; `/tmp/guardian.log`; `~/hmi_cmd.py`, `~/spoof_high.py`.

---

## Gap C — flow-integrity poll window (transient injection)  [TESTED]

**Gap.** `cars_flow_audit.py` polls every 10 s; a rule injected and deleted inside the interval can evade it.

**Fresh proof:**
```
baseline:                    {"ok": 1, "extra": 0}
2 s transient inject+delete: t+7s ok:1 | t+14s ok:1 | t+21s ok:1        # MISSED (never flipped)
persistent inject (left):    ok:0, extra:1                              # CAUGHT within one poll
after cleanup:               {"ok": 1, "extra": 0}
```

**Verdict:** a sub-poll transient beats the poller; a persistent change is caught within one poll. Remedy = event-driven flow-monitoring (an OpenFlow flow-monitor subscription); a shorter poll narrows but never removes the window.
**Documented:** Threats (deployment-limits paragraph).

---

## Gap D — DEFLECT diverts to the honeypot; silent-drop contrast  [TESTED]

**Gap/claim.** DEFLECT was shown installing a redirect but honeypot *engagement* was never evaluated; and silent drops (vs a TCP reset) can hang endpoints.

**Fresh proof:**
```
silent-drop baseline:  atkns (.66) ping .2.10  ->  100% loss           # dropped, attacker hangs
force DEFLECT:         response=DEFLECT, action="DEFLECT conduit -> honeypot 192.168.3.99 (deception, self-healing)"
redirect flows:        p105 nw_src=.66 nw_dst=.10 -> set eth_dst=honeypot, ip_dst=192.168.3.99, goto t2  (n_packets=3)
                       p105 nw_src=192.168.3.99 nw_dst=.66 -> set ip_src=.2.10 (reverse rewrite)
honeypot capture:      IP 192.168.2.66 > 192.168.3.99: ICMP echo request     # attacker DIVERTED to the decoy
                       ARP, who-has 192.168.2.66 tell 192.168.3.99           # decoy engaging (trying to reply)
```

**Verdict:** DEFLECT diverts the attacker off the real asset onto the engaged decoy (wire-proven); the real PLC saw nothing. The full interactive round-trip (attacker receiving spoofed replies) did not complete — the minimal decoy could not resolve the attacker's MAC across the deception boundary. Note: a passive decoy needs its L2 entry seeded before delivery works.
**Documented:** §4.5 cross-layer (DEFLECT paragraph after `tab:crosslayer`); Future Work (interactive decoy; RST-on-quarantine).
**Artefacts:** `hpot_cap.txt`, `hpot_cap2.txt`.

---

## Framed limitations (verified real, not fixed by design / unsafe to test on the live process)

| Gap | Verified fact | Why framed, not fixed | Documented |
|-----|---------------|-----------------------|------------|
| G1 plaintext OpenFlow | `tcp:10.10.10.1:6653` on every switch, no TLS | Control channel is on an isolated wired management plane (`10.10.10.0/24`, hAP VLAN 1) unreachable by the modelled attackers; TLS conversion + overhead is a deployment step, not a data-plane claim | Threats (deployment-limits); Future Work |
| G3 state exhaustion | `STATEFUL=True`, `ct()` tracks every new connection | A real spoofed-source conntrack flood could crash the live fabric/process (violates the do-not-break constraint); GUARD gives partial cover (spoofed protected IDs dropped pre-conntrack) | Threats; Future Work |
| G4 file-based IDS bridge | `snort_bridge.py` uses `tail -F -s 0.05` + `COOLDOWN=3s` dedup | Adequate at measured single-source load; heavy multi-source load unmeasured; re-architecting to in-memory IPC is out of scope this late | Threats; Future Work |

---

## Reproducibility

Each fresh test is a short, reversible sequence run from Dell #1; the exact commands are in `GAPS_G1-G5_PLAN.md` (G2/G5) and `GAP_MITIGATION_PLAN.md` (Gap A/B), with the attack tools embedded (`frag_s7_write.py`, `hmi_cmd.py`, `spoof_high.py`, `cars_process_guardian.py`). Config backups (pre-hardening `cars.conf`/`cars.rules`, remediation agent) are in `~/cars_backup_2026-08-07_1715/` on Dell #1. Green-light after each run: `armstate` ARMED, `cars-{snort,bridge,flowaudit,remediation,hpot}` active, `flow-audit ok:1`, `0xca`=0.
