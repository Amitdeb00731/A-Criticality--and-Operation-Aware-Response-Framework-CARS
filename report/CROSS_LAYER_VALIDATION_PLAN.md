# Cross-layer validation plan (proving CARS at every level)

Purpose: prove CARS not by its own decision log alone but by independent agreement across every layer, for the same attack, armed and disarmed. This is the triangulation argument: the wire, the DPI, the controller, the datapath, the process and the operator view all tell the same story, so no single log is the sole source of truth. Grounded in hard rules 1, 9, 10, 11.

## The six levels to prove (for one representative attack, armed AND disarmed)
1. WIRE / packet journey: the packet captured at three points, the Snort mirror (\texttt{snort0}, what the DPI sees), the PLC1 S7 port (what actually reaches the PLC), and the OpenFlow channel. Shows whether the packet reaches the PLC and its journey through the fabric.
2. DPI / detection: the Snort alert (SID + message + the S7/Modbus function byte on the wire). Shows the operation recovered from the packet.
3. CONTROLLER / internal action: the audit/decision line, source and destination roles, operation, tier, criticality, response, mode. Shows CARS's decision.
4. FLOW / enforcement: the installed flow-mod in OVS (\texttt{dump-flows}, \texttt{cookie 0x00ca}, priority, match, action, timeout). Shows the datapath action.
5. PROCESS / outcome: the PLC and tank state (DB7 / HMI). Shows what happens to the physical process.
6. DASHBOARD / operator view: the decision log entry as the operator sees it.

Detection-to-action cycle (the timeline): attack frame t0 -> Snort alert t1 -> bridge POST t2 -> controller decide t3 -> flow install t4. MTTM = t4 - t0 (already measured: median 13.3 ms). The per-layer timestamps make the cycle visible.

## Deep packet inspection showcase (operation-awareness at the wire)
Run each operation and show the wire byte -> Snort SID -> CARS tier/response, armed vs disarmed. This proves the decision is on the industrial operation, not the 5-tuple.
- S7 (to PLC1 .2.10 / PLC2 .3.10, port 102, function byte at offset 17 after `32 01`): READ 0x04, WRITE/CONTROL 0x05, DIAG 0x28/0x29, PROGRAM, ILLEGAL.
- Modbus (to .2.20, port 502, function code at offset 7): READ 0x03, WRITE 0x06/0x10, CONTROL-coil 0x05/0x0F, DIAG 0x08, PROGRAM-MEI 0x2B, ILLEGAL >0x2B.
- The discriminator case: identical 5-tuple `.2.31 -> .2.20:502`, READ allowed vs WRITE throttled vs READ-flood throttled (already in Table 4.1; here shown at the wire with the Snort SID).

## Captures needed next session (fresh, rule 10)
1. `sudo bash cars_e2e.sh` (Dell 1) -> the five-layer proof per scenario (WIRE tshark count, SNORT alert delta, CARS audit, OVS n_packets, OUTCOME). The backbone cross-layer table.
2. `sudo bash cars_packet_proof.sh` (Dell 1) -> two synchronised pcaps (mirror vs PLC1 port) with the S7 write dissected: READ (allow, reaches) + WRITE (armed, cut) + WRITE (disarmed, reaches). Open in Wireshark; screenshot the S7 write frame hex (function `05` visible).
3. `sudo bash cars_ics_battery.sh` (Dell 1) -> the full ICS operation spectrum from `.2.31` at the Modbus unit: READ->ALLOW, WRITE->throttle, CONTROL/DIAG/PROGRAM/ILLEGAL->BLOCK, with the Snort SID per op.
4. Snort alert extract: `sudo tail -40 /var/log/snort/alert` during the runs (the SIDs for each operation).
5. One reactive rule live (already have; reuse the `0x00ca` dump).
6. Optional: a per-layer timestamped snapshot for one attack (`cars_campaign_lib.sh` `snap`) to build the detection-to-action timeline figure.

## Wireshark captures and packet analysis (dedicated, capture AND analyse)
Capture the pcaps, open them in Wireshark, and do the packet analysis — do not just store the raw pcaps. For each, take an annotated screenshot and write the reading.
- Sources: the pcaps from `cars_packet_proof.sh` and `cars_wire_campaign.sh` at the three points (PLC1 S7 port `plc1_wire.pcap`, Snort mirror `dpi_mirror.pcap`, OpenFlow channel `of_control.pcap`), armed and disarmed.
- Frames to isolate and annotate (S7comm / Modbus dissected on the wire):
  - S7 READ (function `0x04`) — allowed, reaches the PLC port.
  - S7 WRITE/CONTROL (function `0x05`) — the FDI/actuation; ARMED it appears at the mirror but NOT at the PLC port (dropped in the fabric); DISARMED it appears at both (reaches the PLC).
  - S7 DIAG/PROGRAM/ILLEGAL and a Modbus frame (function code at offset 7) for the DPI spectrum.
  - The OpenFlow `flow_mod` on `of_control.pcap` that installs the reactive drop (control-plane view of the enforcement).
- The analysis to write per frame: the protocol dissection (S7 header `32 01`, function byte, DB/area/offset), what operation it is, and armed-vs-disarmed — present at the mirror, absent at the PLC port when armed = the drop proven on the wire (not just in a log).
- Placement: body — one representative annotated frame (the S7 WRITE, armed dropped vs disarmed reaching) in the cross-layer / DPI section. Appendix — the full set of annotated frames, the follow-stream / hex breakdowns, the `flow_mod` capture, and the tshark summaries, each with its reading. This is appendix item 3 (packet/wire-level).

## What we already hold (do not re-capture)
- Controller decision log with timestamps (levels 3, 6) and the accuracy matrix (op discrimination).
- Installed `0x00ca` flows (level 4).
- MTTM 15-trial reaction window (the cycle timing).
- The armed-vs-disarmed traffic-flow diagram (fig:flow), overflow and armed-flow figures, criticality and MTTM charts.

## Placement in the dissertation (rule 11)
- Body, a new subsection in Chapter 4, "Cross-layer validation": one representative attack (an S7 WRITE/CONTROL to PLC1) shown as a compact cross-layer table (the six levels, armed vs disarmed, each a captured artefact), plus the detection-to-action timeline. The vital part only.
- Body, a DPI operation-awareness table: operation -> wire function byte -> Snort SID -> CARS tier -> response, armed vs disarmed.
- Appendix: the full pcap dissections (tshark output + a Wireshark hex screenshot of the S7 write frame), the Snort alert extracts, the `cars_e2e.sh` and `cars_ics_battery.sh` full output, and the per-layer snapshots.

## Order
Capture 1-4 next session -> build the cross-layer table + the DPI table + the timeline -> place vital parts in the body, full dumps in the appendix -> compliance check. No prose ahead of its captured artefact.
