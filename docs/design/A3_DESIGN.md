# A3 — ICS-protocol DPI (operation-aware criticality). Design + gate record.
Opened 2026-07-17. Standing mandate: question every mechanism; measured vs claimed; lock in files; no gap.

## The novelty A3 adds
CARS today decides by **who** is talking (src/dst IP→role). A3 adds **what operation** is being sent.
A *read* observes the process; a *write* actuates it. The write is the process-affecting act CARS's safety
thesis cares about, so the **response becomes a function of (source trust × operation risk)**. Headline:
"an unauthorized *write* to a running PLC is elevated/critical even from an otherwise-allowed source."
This is what pure IP/role classification cannot do, and it seeds the A4 declarative rulebook.

## Feasibility gate (RESOLVED 2026-07-17, Dell#1)
- **Snort 2.9.20 GRE** with the Modbus **dynamic preprocessor present**:
  `/usr/lib/snort/snort_dynamicpreprocessor/libsf_modbus_preproc.so`. Enable pattern from stock snort.conf:
  `dynamicpreprocessor directory /usr/lib/snort/snort_dynamicpreprocessor/` (L271) +
  `dynamicengine /usr/lib/snort/snort_dynamicengine/libsf_engine.so` (L274) +
  `preprocessor modbus: ports { 502 }` (L523). Enables `modbus_func` / `modbus_data` rule keywords.
- `cars.conf` = minimal (HOME_NET 192.168.2.0/24, EXTERNAL_NET any, include cars.rules). `cars.rules` SIDs
  1000001–1000008. Snort launched by `cars-snort.service`: `snort -q -A fast --daq afpacket -c cars.conf -i snort0`.
  Bridge = `snort_bridge.py` (reads /var/log/snort/alert).
- **pymodbus pinned to 3.6.9** (classic `ModbusSlaveContext` / `ModbusSequentialDataBlock(0,...)` API). 3.14
  refactored the datastore (`address-1` → rejects address 0; `ModbusSlaveContext`→`ModbusDeviceContext`);
  pinned for reproducibility + stable API. Install: `sudo pip3 install "pymodbus==3.6.9" --break-system-packages` (as root; netns exec runs as root).
- **Verdict:** Snort-native Modbus DPI is feasible → chosen. Fallback (unused): scapy DPI on the mirror.

## P1 result (DONE 2026-07-17)
Endpoints `mbns/.2.20`, `opns/.2.31`, `atkns/.2.66` live on ovsgw; pymodbus server + clients working. Mirror
(`tshark -i snort0 -Y modbus`) captured real function codes: FC3 read (operator), FC6 write single (operator +
attacker), FC16 write multiple (operator), with responses — proving the operation signal reaches the SPAN that
Snort inspects. Scripts: `06_Build/{mb_server.py, mb_client.py, cars-modbus-setup.sh}`.

## Architecture decisions (Rule-0 justified)
1. **DPI lives in the sensor (Snort), not the controller.** OVS/OpenFlow can't parse L7 at line rate and
   punting every packet to CARS is infeasible. Reuse the proven Snort→bridge→CARS loop. → Snort modbus
   preprocessor + function-code rules; bridge extracts the operation; CARS classify() becomes op-aware.
2. **Endpoints run in dedicated network namespaces** (mbns/opns/atkns on ovsgw). Required, not cosmetic:
   if client and server share one host/root-netns on the same /24, the kernel routes locally (loopback) and
   the traffic never traverses ovsgw → never mirrored → Snort never sees it (same martian trap as the A1
   decoy). Namespaces force the traffic through the fabric so the mirror carries it.
3. **Reactive limitation (honest).** DPI response is reactive: the *first* write may complete before the
   conduit is blocked (same as A1's first-packet-through). A3 proves operation-aware detection + reactive
   response; *preventing* the first write needs proactive default-deny on writes (A2/A4). Stated, not hidden.

## Endpoint topology (Modbus phase)
| netns | ovsgw port | IP | role (REGISTRY) | plays |
|---|---|---|---|---|
| mbns  | mbplc | 192.168.2.20 | plc (modbus) | simulated Modbus PLC (pymodbus server, deterministic regs) |
| opns  | opr   | 192.168.2.31 | supervisory  | legitimate operator (reads + sanctioned writes) |
| atkns | atk   | 192.168.2.66 | unknown      | attacker (unauthorized writes) |
Server register map: hr[0..9] preloaded; hr[8]=4242 designated "safety-critical setpoint" (register-level demo, stretch).

## Function-code → operation class
- READ  (non-process-affecting): 0x01 read coils, 0x02 read discrete, 0x03 read holding, 0x04 read input.
- WRITE (process-affecting): 0x05 write single coil, 0x06 write single register, 0x0F write multiple coils,
  0x10 write multiple registers.

## Decision matrix (source role × operation) — the A3 core
| Source role | READ | WRITE |
|---|---|---|
| supervisory / historian / scada (trusted control) | ALLOW (operational) | **elevate → SENSITIVE**: THROTTLE, then BLOCK on abuse (writes are privileged even for trusted sources) |
| ews (engineering, maintenance) | ALLOW / MONITOR | **SENSITIVE → THROTTLE** (permit-with-limit; EWS may write during maintenance) |
| unknown / it / dmz / gateway | already FORBIDDEN → BLOCK | **FORBIDDEN → BLOCK / DEFLECT** (unauthorized actuation = attack) |
| hmi ↔ plc (control loop) | CRITICAL → REFUSE | CRITICAL → REFUSE (safety invariant unchanged) |
Mechanism: operation risk lifts the effective tier one rung (READ = today's IP/role behaviour; WRITE escalates).
Implemented as a small FC→risk table so it extends to per-FC allowlists + register-level checks (A4).
Optional stretch: WRITE to hr[8] (safety-critical register) → hard REFUSE-equivalent.

## P2a result (DONE 2026-07-17) — DPI detection working, with two Snort gotchas recorded
Detection is driven by **content rules on the Modbus function-code byte** (payload offset 7; proto-id `00 00`
anchor at offset 2), SIDs 1000020–1000024 (write coil/reg/coils/regs + read holding). Verified: a WRITE from
`.2.66` fires `CARS-MODBUS-WRITE-reg`, a READ from `.2.31` fires `CARS-MODBUS-READ-holding` — operation + source IP.
- **Gotcha 1 (checksum offload) — THE blocker.** Internal netns↔netns traffic (opns→mbns via OVS, never crossing a
  physical NIC) carries uncomputed TCP checksums (`CHECKSUM_PARTIAL`). Snort silently drops the *payload inspection*
  of bad-checksum packets, so bare TCP rules matched (SYN) but content rules never did. Fix: **`config checksum_mode: none`**
  in cars.conf. (Existing ICMP rules worked only because `.3.66→.3.10` crosses the physical transit where checksums are real.)
- **Gotcha 2 (stream5 PAF).** The Snort 2.9 `modbus` preprocessor + `modbus_func` needs stream5 reassembly/PAF flush,
  which did not flush single-packet requests off the SPAN. Rather than tune PAF, detection uses stateless content rules
  (deterministic, exact FC match; Modbus PDUs are single-packet << MTU here). The modbus preprocessor remains available;
  content-rule DPI chosen for reliability on the mirror. Honest limit: a deliberately fragmented Modbus write could
  evade single-packet content matching — noted; proactive default-deny (A2) is the mitigation.

## Phases
- **P0** feasibility gate + this design lock. ✅ 2026-07-17.
- **P1** pymodbus PLC endpoint + legit/attacker clients in netns; confirm real Modbus traffic traverses ovsgw
  and is carried on the snort0 mirror. (build in progress)
- **P2** enable Snort modbus preprocessor in cars.conf + write/read function-code rules (SIDs 1000020+);
  extend snort_bridge.py to map the alert message → operation signal (READ/WRITE) for CARS.
- **P3** CARS op-aware classify(src,dst,op) + response; REGISTRY .2.20/.2.31/.2.66; /cars/respond accepts `op`.
- **P2** ✅ 2026-07-17. Content-rule FC DPI (SIDs 1000020-24) + `checksum_mode: none`; bridge v3 extracts op.
- **P3** ✅ 2026-07-17. `classify(src,dst,op)` — trusted WRITE escalates OPERATIONAL→SENSITIVE; op in audit.
  Verified at decision layer: `.2.31` READ→ALLOW, `.2.31` WRITE→THROTTLE, `.2.66` WRITE→BLOCK (same src+dst,
  different response purely by operation). Offense-count fix: benign permits (ALLOW/MONITOR) don't drive escalation.
- **P4** ✅ 2026-07-17. Autonomous Snort-DPI→bridge→CARS proven end-to-end: operator READ×2 → ALLOW (offense 0),
  operator WRITE → SENSITIVE/THROTTLE (offense 1), attacker WRITE → FORBIDDEN/BLOCK (2nd write fails to connect);
  sub-ms, self-healing. **A3-Modbus (novelty) COMPLETE.**
- **P5** ✅ 2026-07-17. (b) dashboard op chip (WRITE/READ/S7); (c) `cars_a3_forensics.sh` cross-validation bundle;
  (a) **S7CommPlus session detection** on the real S7-1200 — wire proto-id `72` confirmed (obfuscated payload, so NO
  clean func-code DPI); content rule (sid 1000040) TPKT+`72` to `.2.10:102`; mirror scopes it to unauthorized fabric
  sessions (legit loop intra-ovs1, unmirrored); attacker probe -> detect -> BLOCK->ISOLATE, safe (invalid COTP DT, PLC
  discards). **A3 COMPLETE** (CC-37). Honest boundary: operation-aware func-code DPI proven on Modbus; S7CommPlus =
  protocol/session-level only.
