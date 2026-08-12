# 6-Week Execution Tracker — Project CARS

Tick weekly. Full detail: `Reactive_SDN_ICS_6Week_Execution_Plan.docx`.
Indicative Wk1 = Mon 6 Jul 2026 → submit ~16 Aug 2026 (set to your real deadline).

**Rules:** writing runs from Week 1 · de-scope fidelity, never the contribution · honour the gates.

## Week 1 — Foundations & minimal loop
- [ ] Pre-build checklist complete (devices, installs, USB-Ethernet)
- [ ] Phase A: PLC drives Factory I/O, visible on Ignition HMI, traffic through OVS (flat)
- [ ] LOCK the single contribution
- [ ] Resolve CC-1 (conduit vs intra-zone scope) and CC-3 (safety-proof method)
- [ ] Read Ph 0–2 deep; write dissertation skeleton + Intro
- [ ] **Gate:** minimal loop up + contribution locked

## Week 2 — SDN baseline, detection, reactive skeleton
- [ ] Phase B: Ryu manages OVS; **measure baseline latency/jitter (CC-4)**
- [ ] Phase C-lite: IDS on mirror → Event API; manual trigger → one flow rule
- [ ] Historian (InfluxDB+Grafana) + OPC UA up
- [ ] Read safety cluster (Ph 8); write Methodology + Testbed chapter
- [ ] **CHECKPOINT:** reactive loop solid + latency acceptable? If NO → de-scope ladder

## Week 3 — CARS engine (the contribution)
- [ ] Criticality model (critical loop vs unknown host)
- [ ] Safety-constrained response (allow/block/mirror/redirect) + safety guard + audit log
- [ ] Unseen device blocked; critical-loop alert redirected; process uninterrupted
- [ ] Finish Lit Review; write Design chapter

## Week 4 — Zones, attack suite, first eval
- [ ] Zones in GNS3 (pfSense×2, DMZ, corp) as far as time allows
- [ ] Attack suite: recon, unauthorized Modbus/S7 write, FDI, DoS (IT→OT if ready)
- [ ] First metrics run
- [ ] **GATE:** writing underway — Intro + Background + Methodology drafted

## Week 5 — Full evaluation & results
- [ ] Full scenario suite run
- [ ] Operator metrics: zero defence-induced trips, false-block rate, MTTM, controller load, audit completeness
- [ ] Analysis; write Results + Analysis + Discussion
- [ ] Complete results table captured

## Week 6 — Writing, polish, submit
- [ ] Code freeze (bugfix only)
- [ ] Discussion (deployability/product argument + limitations), Conclusion, Abstract
- [ ] Final citation checks (CHAOS id; NIST SP 800-82 **Rev. 3**; co-engineering authors)
- [ ] Diagrams, proofread, format; supervisor-review buffer
- [ ] **SUBMIT**

---
### De-scope ladder (cut top-down if behind; never cut contribution/eval/writing)
1. Corporate/IT zone + dual firewalls → single boundary
2. Industrial DMZ (historian replica + jump host)
3. 2nd soft-PLC (OpenPLC)
4. OPC UA / MQTT → keep Modbus + S7comm
5. Full IT→OT kill chain → intra-OT attacks only

**Core that must survive:** real PLC + Factory I/O + OVS + Ryu + IDS + CARS engine + evaluation + writing.
