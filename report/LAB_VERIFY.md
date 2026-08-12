# Lab verification checklist for the Design and Implementation chapter

Purpose: capture the exact current upstanding system, device by device, so every fact and every diagram in Chapter 3 is confirmed live, not taken from a possibly stale file (REPORT_PLAN rule 9). Run these next lab session; paste outputs; we draw and write from the confirmed state only.

## Recalled, to confirm on the device
- Cell-2 on Dell#3: `ovs2` (dpid 2), PLC2 `.3.10` and HMI2 `.3.9` presented as `.2.10`/`.2.9` clones through DNAT, gateway `.2.1`. Confirm the NAT rules and which host holds `ovs2`.
- Kali VM runs on Dell#1, attached via `vmnet2` to `ovsgw`; during an attack only `eth1` (`.2.77`) is up, `eth0` and `eth2` disconnected; ofport floats (unpinned).
- Windows Dell (EWS `.2.55`, NIC `enx00e04c680018`) on `ovsgw` ofport 12, MAC `b4:e9:b8:a4:ce:46`.

## 1. Topology and port map (Fig: network topology, testbed architecture)
- Dell#1: `sudo ovs-vsctl show` ; for br in ovs1 ovsgw ovs2: `sudo ovs-ofctl -O OpenFlow13 show $br` (ofport to interface), and `sudo ovs-vsctl -- --columns=name,ofport list interface`.
- Map each ofport to its interface and host; note dpids; note the uplink/transit ports between bridges and to Dell#3.
- Dell#3: `sudo ovs-vsctl show` (confirm whether `ovs2` lives here); interfaces for PLC2/HMI2.

## 2. Enforcement pipeline (Fig: three-table pipeline)  <-- the section we build first tomorrow
- Dell#1, for br in ovs1 ovsgw ovs2: `sudo ovs-ofctl -O OpenFlow13 dump-flows $br table=0` (GUARD), `table=1` (POLICY), `table=2` (SWITCH).
- Confirm from the live tables: table 0 GUARD rules and the goto to table 1; table 1 cookies `0x00a2` (allowlist/default-deny priorities) and `0x00ca` (reactive), the `ct()` conntrack usage, exact priorities and goto to table 2; table 2 L2 learning.
- `sudo ovs-ofctl -O OpenFlow13 dump-meters ovsgw` (throttle meter).

## 3. Decision logic: registry, criticality, rulebook, bindings, constants
- Dell#2 (controller): locate the running engine (`systemctl status` or `ps aux | grep osken`); `diff` the deployed `cars_engine.py` against the repo master `06_Build/cars_engine.py`; confirm REGISTRY, CRITICALITY, CW, RULEBOOK, ALLOWLIST, DEFAULT_DENY, BINDINGS, and constants (GUARD_ENABLED, ARP_GUARD_ENABLED, FLOOD_RATE, FLOOD_EXEMPT, BLOCK_TIMEOUT, THROTTLE_RATE, ESCALATE, A2_COOKIE, REACTIVE_COOKIE, HONEYPOT_IP).
- Cross-check live via API: `curl -s $API/cars/criticality`, `curl -s $API/cars/status`, and the rulebook/A2 endpoints.

## 4. Deployment (Fig: deployment, control vs data plane)
- Dell#2: os-ken controller (`cars_engine.py`), API :8080, OpenFlow :6653.
- Dell#1: OVS bridges; Snort (`systemctl status cars-snort` or equivalent) and its mirror; remediation service; `cars-flowaudit` daemon; dashboard process/port; namespaces (`ip netns list` and per-ns `ip -4 addr`).
- Dell#3: `cars-cell2.sh` (`/usr/local/sbin/`), NAT.
- Windows Dell: Factory IO + TIA, `.2.55`, NIC.

## 5. Cell-2 NAT detail (Fig: topology, Cell-2 inset)
- Dell#3: `sudo iptables -t nat -L -n -v` (confirm DNAT `.3.10`->`.2.10` and MASQUERADE), `ip addr` for `cell2gw`/`.2.1`, transit interface to Dell#1.

## 6. Snort DPI and S7 operation classification (Fig: detection-to-response, S7 op classes)
- Dell#1: `cat /etc/snort/cars.rules` and `/etc/snort/cars.conf` (or the deployed paths); confirm which bridge is mirrored (expected `ovsgw`) and the S7 function-to-op mapping the rules encode.

## 7. Factory IO hardware-in-the-loop (Fig: HIL process flow)
- Windows Dell / TIA project: OB30 source, the Default tag table (`LevelIn %ID100`, `FillValve %QD100`, `DischargeValve %QD104`, `StartBtn %I10.0` etc., `Running %M0.0`, `HMI_Start/Stop %M0.1/0.2`), DB7 `Sim.Level`.
- Factory IO driver configuration (S7-1200 driver, I/O point offsets, the scene).
- Confirm the scaling (`LevelIn * 20`) and bang-bang thresholds (30/70) from the live OB30.

## 8. Live capture to lock exact values
- `curl -s $API/cars/guard` (bindings/counters), `curl -s $API/cars/audit` (decision format).
- Save `ovs-ofctl dump-flows` for all bridges/tables to files for the appendix (full flow tables).

Once these are confirmed, we build Figures 2 to 9 and write sections 3.2 to 3.7 from the confirmed state, in order, each traced to a captured artefact.

## Status (updated 3 Aug 2026)
- Sections 1 to 7: PASSED. Verified device by device on 3 Aug 2026 and captured into `verified_config.md`. Chapter 3 (sections 3.1 to 3.7, Figures 1 to 8) is written from that confirmed state.
- Section 8/9 (evidence capture): PASSED. Full captures taken live on 3 Aug 2026 (All_verifications.docx) and reconciled against verified_config.md with no drift. Placed: criticality and status screenshots inline (fig:criticality, fig:status); full flow tables, deployed RULEBOOK, a2_policy.json and Snort rules as text listings in Appendix A; GUARD counters and throttle meter as appendix figures. Only item 15 (a live reactive rule showing cookie 0x00ca) remains to capture. The deployed RULEBOOK confirms ews->plc = OPERATIONAL, retiring the stale July rulebook.json. Item 15 CLOSED (5 Aug): armed FDI triggered ISOLATE source 192.168.2.31, installed on ovs1+ovsgw as cookie=0xca, table=1, priority=110, nw_src=192.168.2.31, actions=drop, hard_timeout=75 (self-healing). ALL LAB_VERIFY ITEMS PASSED.
- July archive (`flows.zip`, `rulebook.json`, `meters.zip`, `ports.zip`): STALE, do not use. It predates the 3 Aug state and conflicts with it: reactive rules were cookie `0x0` there (now `0x00ca`); the POLICY table was empty (`priority=0 goto_table:2` only); and `rulebook.json` marks `ews->plc` as SENSITIVE where the deployed engine, and the live decision log, use OPERATIONAL. Recapture fresh (Section 9).

## 9. Evidence capture for Chapter 3 backing (fresh terminal screenshots)
Back each load-bearing diagram, table and claim with a genuine capture from the CURRENT system, captured the same way as `ovs-vsctl show` (run, screenshot, light arrow annotation only). Run in order. `[x]` done and placed, `[ ]` pending. `API=http://127.0.0.1:8080` on Dell 2 (confirm port).

Dell 1 (fabric + sensing):
- [x] 1. Topology: `sudo ovs-vsctl show`; `sudo ovs-ofctl -O OpenFlow13 show ovs1`; `... show ovsgw`  -> Fig 2, fig:ovsshow, Section 3.2
- [x] 2. Pipeline (HIGHEST): `for t in 0 1 2; do sudo ovs-ofctl -O OpenFlow13 dump-flows ovs1 table=$t; done`; same for `ovsgw`  -> Fig 5, Section 3.4
- [x] 3. Throttle meter: `sudo ovs-ofctl -O OpenFlow13 dump-meters ovsgw`  -> Section 3.6 (THROTTLE)
- [x] 4. Detection rules: `sudo grep -nE "s7comm|modbus|byte_test|offset" /etc/snort/cars.rules | head -60`  -> Fig 6, Fig 7, Section 3.6
- [x] 5. Services: `systemctl --no-pager status cars-snort cars-bridge cars-flowaudit cars-remediation`  -> Sections 3.6, 3.7
- [x] 6. Flow-integrity line: `journalctl -u cars-flowaudit -n 20 --no-pager`  -> Section 3.6
- [x] 7. Namespaces: `ip netns list`; per ns `sudo ip netns exec <ns> ip -4 addr`  -> Section 3.7

Dell 3 (Cell-2):
- [x] 8. Cell-2 switch: `sudo ovs-vsctl show`; `for t in 0 1 2; do sudo ovs-ofctl -O OpenFlow13 dump-flows ovs2 table=$t; done`  -> Fig 2, fig:ovsshow
- [x] 9. NAT clone: `sudo iptables -t nat -L -n -v`  -> Section 3.2

Dell 2 (controller / API):
- [x] 10. Controller live + decisions: `curl -s $API/cars/status`; decision log console  -> fig:decisionlog, Section 3.7
- [x] 11. Criticality: `curl -s $API/cars/criticality`  -> Table 3.1, Section 3.5
- [x] 12. Rulebook (must show `ews->plc = OPERATIONAL`): `grep -nE "RULEBOOK" -A40 /home/msclab/cars/cars_engine.py`  -> Table 3.2, Section 3.5
- [x] 13. Allowlist (9 conduits): `cat /home/msclab/cars/a2_policy.json`  -> Sections 3.4, 3.6
- [x] 14. GUARD bindings: `curl -s $API/cars/guard`  -> Section 3.4

Reactive rule, live:
- [x] 15. Drive one ISOLATE/BLOCK via the campaign, then on Dell 1: `sudo ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep -iE "0x0*ca"`  (cookie `0x00ca`, criticality-scaled `hard_timeout`)  -> Section 3.6

Appendix dumps (hard rule 8):
- [x] 16. `for b in ovs1 ovsgw; do for t in 0 1 2; do sudo ovs-ofctl -O OpenFlow13 dump-flows $b table=$t > ~/flows_${b}_t${t}_$(date +%F).txt; done; done`  -> Appendix full flow tables

Placement: 3 to 4 annotated screenshots inline (pipeline table, criticality, rulebook, one reactive rule); the rest and the full dumps to the Appendix, cross-referenced from the text.
