# Verified running configuration (captured live, 2026-08-03)

Source of truth for Chapter 3 figures and the appendix flow tables. Captured from the devices per REPORT_PLAN rule 9. OVS 3.3.4, controller `tcp:10.10.10.1:6653`, all bridges `fail_mode=secure`, connected. CARS ARMED, decision latency 0.024 ms mean (n=1258).

## Topology (ofport -> interface -> device)
Device MACs are the bound identities in GUARD (Table 0); interface MACs are the OVS port NICs.

### ovs1 = dpid 1 (Dell#1, Cell-1)
- p1 `enx9c69d331d874` -> PLC1, device MAC `e0:dc:a0:63:98:09`, `192.168.2.10` (CRITICAL)
- p2 `enx9c69d331aef0` -> HMI1, device MAC `e0:dc:a0:62:b7:4c`, `192.168.2.9` (HIGH)
- p3 `patch-ovs1-gw` -> patch to ovsgw

### ovsgw = dpid 3 (Dell#1, gateway and seams)
- p1 `patch-gw-ovs1` -> patch to ovs1
- p2 `it0` -> IT/enterprise vantage
- p3 `sup0` -> historian `192.168.2.30`, MAC `de:5a:28:ae:96:03` (MEDIUM)
- p4 `snort0` -> Snort DPI mirror sink
- p5 `att0` -> attacker vantage `192.168.2.67`
- p6 `hpot` -> honeypot `192.168.3.99`
- p7 `mbplc` -> Modbus PLC `192.168.2.20`, MAC `02:00:00:00:02:20` (LOW)
- p8 `ins2` -> Cell-2 seam (`.3.66` face / transit to Dell#3)
- p9 `eth0` -> uplink toward Dell#3 (`.3.x`), NIC MAC `b4:e9:b8:99:96:9e`
- p10 `opr` -> scada `192.168.2.31`, MAC `02:00:00:00:02:31`
- p11 `atk` -> attacker `192.168.2.66`
- p12 `enx00e04c680018` -> EWS / Factory IO host `192.168.2.55`, device MAC `b4:e9:b8:a4:ce:46`
- p13 `vmnet2` -> Kali `192.168.2.77` (UNREGISTERED, floating ofport: was 13 this boot)
- p14 `rem0ovs` -> remediation `192.168.2.45`, MAC `92:b7:80:63:54:56`

### ovs2 = dpid 2 (Dell#3, Cell-2)
- p1 `enx9c69d3413f16` -> PLC2, device MAC `e0:dc:a0:46:ff:ce`, internal `192.168.2.10` (external `192.168.3.10`, HIGH)
- p2 `enx9c69d3283cf9` -> HMI2, device MAC `e0:dc:a0:5c:60:44`, internal `192.168.2.9` (external `192.168.3.9`, MEDIUM)
- p5 `cell2gw` -> internal gateway `192.168.2.1`
- NAT on Dell#3: `PREROUTING -d 192.168.3.10 -i eth0 -j DNAT --to-destination 192.168.2.10`; `POSTROUTING -o cell2gw -j MASQUERADE`. Dell#3 eth0 holds `192.168.3.1` and `192.168.3.10/32`. Cell-2 runs the same internal `.2.10`/`.2.9`/gateway `.2.1` as Cell-1 (the clone), and is reached from the gateway fabric as `.3.10`/`.3.9`.

## Enforcement pipeline (both ovs1 and ovsgw; captured live)
Cookies: `0xa2` = proactive A2 policy; `0x0` on GUARD/SWITCH; reactive rules carry `0xca` (none active at capture, isolates expired).

### Table 0 - GUARD (identity binding / anti-spoof)
- p65535 LLDP (`dl_type=0x88cc`) -> CONTROLLER (os-ken topology discovery)
- p200 legit source (`in_port` + `dl_src` + `nw_src`/`arp_spa` all match the binding), IP and ARP -> `goto_table:1`
- p150 `in_port` = inter-bridge patch/uplink -> `goto_table:1` (already guarded at the far bridge)
- p100 any protected IP from a non-matching port, IP and ARP -> `drop` (the anti-spoof drop)
- p50 `ip` -> `goto_table:1`; p0 -> `goto_table:1`

### Table 1 - POLICY (stateful: conntrack + allowlist + default-deny)
- p90 `ct_state=-trk,ip` -> `ct(table=1)` (submit to conntrack, re-enter)
- p85 `ct_state=+est+trk,ip` -> `goto_table:2` (established connections pass; the stateful shield)
- p80 allowlist conduits `ct_state=+new+trk,tcp,<src>,<dst>,<dport>` -> `ct(commit),goto_table:2`:
  `.2.9->.2.10:102`, `.2.31->.2.10:102`, `.2.55->.2.10:102`, `.2.45->.2.10:102`, `.2.30->.2.10:102` (to PLC1);
  `.2.31->.2.20:502`, `.2.30->.2.20:502` (to Modbus); `.3.66->.3.10:102` (Cell-2 collector to PLC2); `.2.55->.2.9:102` (EWS to HMI1)
- p55 `ct_state=+new+trk,ip,nw_dst=<protected>` -> `drop` (default-deny; ovs1: `.2.10`,`.2.9`,`.2.20`; ovsgw: `.2.20`)
- p10 `ct_state=+new+trk,ip` -> `ct(commit),goto_table:2` (new to non-protected dst)
- p0 -> `goto_table:2`

### Table 2 - SWITCH (L2 learning)
- p2 broadcast -> FLOOD; p1 learned `(in_port,dl_src,dl_dst)` pairs -> `output`; p0 -> CONTROLLER (packet-in to learn)

### Reactive rules (installed at runtime, cookie 0xca; from cars_engine.py, none active at capture)
- ISOLATE: table 1, p110, `nw_src=<attacker>` -> drop (source quarantine)
- BLOCK: table 1, p100, conduit -> drop
- THROTTLE: table 1, p100, conduit -> meter + `goto_table:2`
- DEFLECT: table 1, p105, forward+reverse rewrite to honeypot `.3.99` + `goto_table:2`

## Decision logic (deployed engine, Dell#2 `/home/msclab/cars/cars_engine.py`, captured 2026-08-03)
Running as `osken-manager --observe-links` (pid 6700). Criticality also confirmed via `/cars/criticality`.

### Roles (REGISTRY)
plc: `.2.10` (PLC1, cell 1), `.3.10` (PLC2, cell 2), `.2.20` (Modbus sim); hmi: `.2.9` (HMI1), `.3.9` (HMI2);
historian: `.2.30`, `.3.66`; scada: `.2.31`; ews: `.2.55`; remediation: `.2.45`; gateway: `.2.1`; unknown: `.2.66`.
`.2.77` (Kali) is commented out -> unregistered -> role `unknown`. No host holds the `supervisory` role (those rulebook rows are dormant; `historian` rows are active).

### Criticality tiers and weights (source + API confirmed)
`.2.10` CRITICAL(3), `.3.10` HIGH(2), `.2.9` HIGH(2), `.3.9` MEDIUM(1), `.2.30` MEDIUM(1), `.2.20` LOW(0); unset -> LOW(0). Block/isolate duration = `BLOCK_TIMEOUT + weight*15` = 75/60/45/30 s.

### Constants
`GUARD_ENABLED=True`, `ARP_GUARD_ENABLED=True`, `BLOCK_TIMEOUT=30`, `THROTTLE_RATE=20`, `THROTTLE_BURST=10`, `ESCALATE=3`, `FLOOD_RATE=5.0`, `FLOOD_EXEMPT={192.168.2.55}`, `HONEYPOT_IP=192.168.3.99`, `A2_COOKIE=0x00A2`, `REACTIVE_COOKIE=0x00CA`.

### Rulebook (first-match-wins; source_role, dst_role, op, tier)
hmi->plc any = CRITICAL; plc->hmi any = CRITICAL (the loop; REFUSE, safety invariant).
remediation->plc CONTROL/any = OPERATIONAL. ews->plc READ/WRITE/CONTROL = OPERATIONAL.
any->plc/hmi CONTROL|DIAG|PROGRAM|ILLEGAL = FORBIDDEN (dangerous ops, any source).
ews->plc any = OPERATIONAL; ews->hmi any = SENSITIVE.
{supervisory,historian,scada}->{plc,hmi} WRITE = SENSITIVE; ...->{plc,hmi} any = OPERATIONAL.
any->plc/hmi any = FORBIDDEN; any->any any = FORBIDDEN.
Criticality elevation (in `respond`): a SENSITIVE op to a CRITICAL asset (weight>=3), outside a maintenance window, is elevated to FORBIDDEN.

### Allowlist (A2 conduits) - DRIFT NOTED
Deployed source seed = 6 conduits; running policy (a2_policy.json, installed as flows) = 9. The report uses the running 9 (authoritative, from the flow tables): to PLC1 `.2.9/.2.31/.2.55/.2.45/.2.30 -> .2.10:102`; to Modbus `.2.31/.2.30 -> .2.20:502`; Cell-2 `.3.66 -> .3.10:102`; EWS->HMI1 `.2.55 -> .2.9:102`. Source list is the cold-start seed.

### Default-deny
`(None,.2.20)` all switches; `(1,.2.10)`, `(1,.2.9)` on dpid1 (Cell-1); `(2,.2.9)` on dpid2 (Cell-2 clone).

## Detection and deployment (Dell#1, captured 2026-08-03)

### Detection-to-response chain
Snort (`cars-snort`, `snort -q -A fast --daq afpacket -c /etc/snort/cars.conf -i snort0`) reads the `ovsgw` SPAN mirror (`mirror m0`, `select_all=true` -> `snort0`); alerts are written to `/var/log/snort/alert`; `snort_bridge.py` (`cars-bridge`) tails that file and `POST`s each to `/cars/respond`; the controller classifies and installs the flow-mod. Snort HOME_NET `192.168.2.0/24`, `include /etc/snort/cars.rules`. Coverage is `ovsgw` (Cell-2 on `ovs2` is not mirrored).

### DPI operation classification (from `cars.rules`)
S7comm to `.2.10`/`.3.10` port 102 (function byte at offset 17 after `32 01`): `0x04` READ (sid 1000044/47), `0x05` WRITE/CONTROL (1000041/45), `0x28` DIAG-control (1000043/48), `0x29` DIAG-stop (1000042/46); `0x72` at offset 7 = S7CommPlus session (1000040).
Modbus to `.2.20` port 502 (function code at offset 7): `0x03` READ-holding (1000024), `0x05` control-coil / `0x0F` control-coils (1000020/22), `0x06` write-reg / `0x10` write-regs (1000021/23), `0x08` DIAG (1000025), `0x2B` PROGRAM-MEI (1000026), function `> 0x2B` = ILLEGAL (1000027, `byte_test:1,>,43,7`).
Plus recon triggers: ICMP/TCP-SYN to `.2.10`/`.2.9` (sids 1000001-4) and the Cell-2 equivalents (1000005-8).

### Services and processes
Dell#1: `cars-snort` (IDS), `cars-bridge` (Snort->/cars/respond), `cars-flowaudit` (`cars_flow_audit.py --watch 10 --bridges ovs1,ovsgw`, flow-integrity), `cars-remediation` (`cars_remediation.py`, `.2.45`), `cars-modbus` (Modbus scenario), `cars-seams`/`cars-ins2`/`cars-hpot` (seam IPs, Cell-2 vantage, honeypot decoy `.3.99`; oneshot/exited), and `cars_dashboard.py`.
Namespaces on Dell#1: `atkns` (`atk .2.66`), `remns` (`rem0 .2.45`), `opns` (`opr .2.31`), `mbns` (`mbplc .2.20`), `hpotns` (`hpot .3.99`).
Dell#2: `osken-manager --observe-links cars_engine.py` (controller, API :8080, OpenFlow :6653). Dell#3: `ovs2` + NAT (Cell-2). Windows Dell: TIA + Factory IO (EWS `.2.55`).

## Factory IO hardware-in-the-loop (Windows Dell, captured 2026-08-03)

### Factory IO S7-1200 driver
Model S7-1200, host `192.168.2.10`, adapter Intel I219-LM #2, auto-connect off, numerical type DWORD. I/O points: Bool inputs offset 10 count 4 (`%I10.0-10.3`), Bool outputs offset 0 count 3 (`%Q0.0-0.2`), DWORD inputs offset 100 count 3 (`%ID100/104/108`), DWORD outputs offset 100 count 4 (`%QD100/104/108/112`).

### Process tags used by OB30 (from the tag table)
`LevelIn` Real `%ID100` (level sensor, 0-5, written by Factory IO); `FillValve` Real `%QD100`, `DischargeValve` Real `%QD104` (actuators, read by Factory IO); `StartBtn %I10.0`, `ResetBtn %I10.1`, `StopBtn %I10.2` (scene buttons); `StartLight %Q0.0`, `ResetLight %Q0.1`, `StopLight %Q0.2` (lamps); `Running %M0.0` (latch); `HMI_Start %M0.1`, `HMI_Stop %M0.2`. `DB7` block `Sim.Level` Real (0-100). Legacy Int tags (`%IW100` etc.) exist but are unused by OB30.

### OB30 control logic (cyclic interrupt, verified current)
`Sim.Level := LevelIn * 20.0` (0-5 sensor -> 0-100). Latch: `Start OR HMI_Start -> Running:=TRUE`; `NOT StopBtn OR HMI_Stop -> Running:=FALSE` (Stop is normally-closed); `Reset -> Running:=FALSE`. While Running: `Sim.Level < 30 -> FillValve:=100`; `Sim.Level > 70 -> FillValve:=0`; `DischargeValve:=40`. Stopped: both valves 0 (tank holds). Lamps mirror Running / not-Running / Reset.

### Live cross-check (Dell#1, remns/.2.45)
`Start=0 Reset=0 Stop=1 | Running=1 | LevelIn=1.66 Fill=100.0 Disch=40.0 DB7=33.20`. `DB7 = LevelIn*20 = 33.2` confirms the scaling on the running PLC. (A second read timed out: `cars-remediation` was running and holding an S7 connection slot on the 1212C; stop it for the live loop.)
