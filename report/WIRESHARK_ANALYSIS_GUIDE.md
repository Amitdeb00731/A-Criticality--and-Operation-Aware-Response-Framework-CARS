# Wireshark capture and packet-analysis guide (Chapter 4 wire-level backup)

Open the pcaps from `/tmp/cars_pcap/` (S7) and `e2e_full.pcap` (Modbus) in Wireshark. Take the screenshots below with the exact display filters given. Vital shots go in the body; the rest in Appendix A.7. Keep each shot tight (the packet list rows or one expanded frame), not the whole window.

Grounded facts already dissected from the pcaps (state these in the captions):
- Attacker S7 Write-Var frames `.31 -> .10`: armed_mirror = 8, armed_plc1 = 1, disarmed_plc1 = 7.
- The write targets the OUTPUT area (S7 area 0x82 = Q, an actuation) -> CARS classifies CONTROL.
- Reaction window: first write reaches at t+6.233 s; the isolate then cuts every write from t+6.544 s on.

## BODY (vital, rule 11) - 3 shots

### B1. The drop shown on the wire (the centrepiece) - two shots side by side
- **armed_mirror.pcap**, filter: `s7comm.param.func == 5 && ip.src == 192.168.2.31`
  -> shows 8 Write-Var frames (what the DPI/Snort sees).
- **armed_plc1.pcap**, same filter
  -> shows 1 Write-Var frame (what reaches the PLC).
Screenshot both packet lists. Caption: "Armed: the detector sees 8 attacker write frames (left); only 1 reaches the PLC (right). Seven are dropped in the fabric; one leaks in the reaction window." This is Table~\ref{tab:wiredrop} shown as packets.

### B2. The malicious operation on the wire (one frame, fully expanded)
- Any of the pcaps, filter: `s7comm.param.func == 5 && ip.src == 192.168.2.31`; select one Write-Var frame and expand the tree:
  `TPKT` -> `COTP` -> `S7COMM` -> `Header (ROSCTR: Job)` -> `Parameter (Function: Write Var)` -> `Item (Area: Outputs, Address ...)`.
Screenshot the expanded protocol tree. Caption: "A single S7 Write-Var frame: CARS recovers the operation (Write Var to the output area = a CONTROL actuation) from this parameter, and forbids it."

## APPENDIX A.7 (depth) - 4 shots

### A1. Disarmed contrast
- **disarmed_plc1.pcap**, filter: `s7comm.param.func == 5 && ip.src == 192.168.2.31`
  -> 7 Write-Var frames reaching the PLC. Caption: "Disarmed, the writes reach the PLC (contrast with the single armed write)."

### A2. The reaction window on the timeline
- **armed_mirror.pcap**, same filter; make sure the Time column shows seconds-since-first-packet. Screenshot the list with the 8 timestamps (6.233, 6.544, ... 19.8). Caption: "The first write lands at t+6.233 s; the isolate then drops every subsequent write - the reaction window on the wire."

### A3. The Modbus operation discriminator
- **e2e_full.pcap**, filter: `modbus`; find the two `.31 -> .20` frames, expand each to `Modbus` -> `Function Code`: one shows `Read Holding Registers (3)`, the other `Write Single Register (6)`. Screenshot both function-code fields. Caption: "Same conduit, two function codes: FC3 read (ALLOW) and FC6 write (THROTTLE). The verdict turns on this one field."

### A4. The S7 stream overview (optional)
- **armed_plc1.pcap**, filter: `s7comm`; screenshot the mix of legitimate `.55` HIL loop traffic (Read/Write Var) with the attacker's single write, to show the attack is a needle in the live process traffic.

## Precise short outputs to paste (text, for the appendix listings)
- The packet counts block from `cars_packet_proof.sh` (armed/disarmed mirror/plc1 S7comm totals) - already captured.
- `tshark -r armed_plc1.pcap -Y "s7comm.param.func==5 && ip.src==192.168.2.31" -T fields -e frame.number -e frame.time_relative -e s7comm.param.func` (one line per reaching write) if tshark is available; otherwise the scapy counts we already have.

## Placement summary
- Body: B1 (drop proof, 2 panels) + B2 (one frame dissected). These carry the wire-level claim.
- Appendix A.7: A1-A4 (disarmed contrast, reaction-window timeline, Modbus discriminator, stream overview) + the frame-byte breakdowns already written (Listing lst:modbusfc) + the packet-count block.
- Every screenshot caption states what it proves and its source pcap.
