# Fresh terminal captures to back Chapter 3 (Design and Implementation)

Purpose: back each load-bearing diagram, table and claim with a genuine capture from the CURRENT running system (the 3 Aug 2026 verified state), per hard rules 1, 2, 6 and 9. Capture the same way as `ovs-vsctl show` and the decision log: run the command, screenshot it (or save the text), add light arrow annotations only. Do NOT reuse the July archive (flows.zip / rulebook.json / meters.zip): verified stale — it predates the reactive-cookie hardening, shows an empty POLICY table, and marks `ews->plc` as SENSITIVE where the deployed engine now uses OPERATIONAL.

API base on Dell 2, e.g. `API=http://127.0.0.1:8080` (confirm the port).

## Already captured and placed (08-03)
- Topology: `ovs-vsctl show` for ovs1 and ovs2  ->  Figure (fig:ovsshow), backs Section 3.2 and Figure 2.
- Controller live: decision log console  ->  Figure (fig:decisionlog), backs Section 3.7 (engine runs and logs).

## To capture next session, mapped to what it backs

1. Enforcement pipeline (Section 3.4, Figure 5)  -- highest priority
   - `sudo ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=0`  (GUARD: p200 bind, p150 patch, p100 anti-spoof drop, p50/p0 goto)
   - `... dump-flows ovsgw table=1`  (POLICY: p90 ct, p85 +est, p80 allowlist 9 conduits, p55 default-deny, p10, p0; cookie 0x00a2)
   - `... dump-flows ovsgw table=2`  (SWITCH: p2 FLOOD, p1 learned, p0 CONTROLLER)
   - One annotated screenshot per table, or one tall shot. Full dumps for all bridges -> Appendix.

2. Criticality tiers and weights (Section 3.5, Table 3.1)
   - `curl -s $API/cars/criticality`  (.2.10 CRITICAL/3, .2.9 & .3.10 HIGH/2, .3.9 & .2.30 MEDIUM/1, .2.20 LOW/0; block = 30 + 15*weight = 75/60/45/30)

3. Rulebook (Section 3.5, Table 3.2)  -- capture the DEPLOYED one, not the old json
   - `curl -s $API/cars/rulebook`  (or print RULEBOOK from the running cars_engine.py). Must show `ews->plc any = OPERATIONAL` to match the table and the decision log.

4. Allowlist / A2 conduits (Sections 3.4, 3.6)
   - the 9 live conduits: `curl -s $API/cars/a2` or `cat` the deployed a2_policy.json on Dell 2 (to PLC1: .2.9/.2.31/.2.55/.2.45/.2.30; to Modbus: .2.31/.2.30; Cell-2: .3.66->.3.10; EWS->HMI1: .2.55->.2.9)

5. Detection and operation classes (Section 3.6, Figures 6 and 7)
   - `sed -n` excerpt of `/etc/snort/cars.rules` showing the S7 function bytes (0x04 READ, 0x05 WRITE/CONTROL, 0x28/0x29 DIAG) and the Modbus function codes (0x03 READ, 0x05/0x0F/0x06/0x10 write, 0x08 DIAG, 0x2B PROGRAM, >0x2B ILLEGAL)

6. Services and self-check (Sections 3.6, 3.7)
   - `systemctl --no-pager status cars-snort cars-bridge cars-flowaudit cars-remediation` (active/running)
   - one `cars-flowaudit` log line reporting a clean baseline or a drift, backing the flow-integrity claim

7. Throttle meter (Section 3.6, response ladder)
   - `sudo ovs-ofctl -O OpenFlow13 dump-meters ovsgw`  (the rate-limiting meter behind THROTTLE)

8. One reactive rule installed live (Section 3.6)
   - trigger an ISOLATE or BLOCK once, then `dump-flows ovsgw table=1 | grep 0x0*ca` to show the reactive rule at p110/p100 with cookie 0x00ca and the criticality-scaled hard_timeout

## Placement
- 3 to 4 annotated screenshots inline in the main text (pipeline table, criticality API, rulebook, one reactive rule). Everything else, and the full flow dumps for all bridges, go to Appendix (hard rule 8), cross-referenced from the text.
