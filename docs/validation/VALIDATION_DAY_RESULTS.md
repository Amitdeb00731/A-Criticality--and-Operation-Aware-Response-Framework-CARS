# CARS — Rigorous Validation Day: Results Log

_2026-07-20. Real attackers: insider = Kali VM `.2.77` (VMware, OT L2 via vmnet2→ovsgw); IT = GNS3 kill chain (pending).
Process = Q0.3 relay + HMI↔PLC loop. Each row records: outcome vs the pre-defined expected decision + honest notes._

## Vantage status
- **Insider VM (.2.77):** WIRED + verified. Kali on OT L2; CARS classifies it `unknown`; L2 reachability to OT peers works
  (`.2.31` ping ok), PLC-bound traffic blocked. Tooling: nmap, hping3, scapy, `s7_write.py`/`mb_attack.py`/`mb_client.py`.
- **IT VM (GNS3 kill chain):** pending (replace VPCS with full-OS attacker in the 10.0.40.0/24 zone → DMZ → OT-FW SNAT → it0).

## Results

### R2 — Remote System Discovery (T0846) — unauthorized insider — **PASS**
- Attack: `nmap -sS -p102,502 .2.10 .2.20` + `--top-ports 50 .2.10` from `.2.77`.
- CARS: `FORBIDDEN .2.77(unknown) -> .2.10 TCP => BLOCK` then `ISOLATE source .2.77 (quarantine all conduits, self-healing)`.
- nmap outcome: **all ICS ports filtered**, no S7/Modbus service enumerable; scanner quarantined.
- Process harm: none.
- **Honest boundary:** nmap still saw the target **up + its Siemens MAC via L2 ARP** on the shared segment. CARS guards the
  L3/L4 conduit (blocks all service/data reachability) but does not suppress L2 MAC/ARP discovery — it is a conduit guard,
  not port-security/PVLAN. Attacker learns "a Siemens device is here," can touch nothing. (Future work: L2 port-security.)

### R3 — Unauthorized Command Message / Manipulation of Control (T0855/T0831) — authorized-but-malicious insider — **PASS**
- Setup: `.2.77` registered **supervisory** + allowlisted (`.2.10:102`, `.2.20:502`) = the malicious-insider model
  (legitimate OT workstation, misused). Controller restarted to load the role.
- READ → `OPERATIONAL .2.77(supervisory) -> .2.10 S7 READ => ALLOW` — insider monitors like a real operator.
- WRITE → `FORBIDDEN .2.77(supervisory) -> .2.10 S7 CONTROL => BLOCK conduit` — control command detected + cut.
- **CC-54 caveat:** client printed `wrote 0x00` — the first write PDU landed (relay unaffected, val 0) before the block;
  repeated writes blocked. "Insider can look, not touch beyond one reactive-window packet."
- Process harm: none. **T0855/T0831 covered from a real insider VM; read-allowed vs control-blocked discrimination shown.**

### R5 — Coil force FC5/15 (T0855/T0831) — insider — **PASS**
- `MODBUS CONTROL => BLOCK conduit`. Coil request got a Modbus response first (first-packet, CC-54) then cut. `.2.20` is the
  simulator (no physical relay) → no harm.

### R6 — Register/parameter write FC6/16 (T0836 Modify Parameter) — insider — **DETECTED + THROTTLED (nuanced)**
- read → `MODBUS READ => ALLOW`; write reg4=7 → `SENSITIVE MODBUS WRITE => THROTTLE conduit @20pps (meter)`. Write succeeded
  (`WRITE hr[4]=7 OK`) — THROTTLE is a meter, not a drop, so the single write lands.
- **Finding (graded sensitivity):** CARS classifies writes in 3 tiers — READ=OPERATIONAL/ALLOW, WRITE(parameter)=SENSITIVE/
  THROTTLE→BLOCK-on-abuse, CONTROL(actuation)=FORBIDDEN/BLOCK. A parameter-change *campaign* is rate-limited then cut.
- **Honest limitation (T0836):** CARS grades by operation TYPE, not the VALUE written (7 vs a dangerous setpoint), so a
  single legit-looking parameter write passes. Value/setpoint-aware inspection = future work. Maps T0836 = detected+throttled,
  not value-inspected.

### R7 — S7 PLC-Stop 0x29 (T0816 Device Restart/Shutdown) — insider — **PASS (double-layer)**
- CARS: `S7 DIAG => BLOCK conduit` (stop attempt detected + blocked at the network). AND the real S7-1200 **refused it
  natively** (`S7ProtocolError class=0x81 code=0x04` = PUT/GET access protection). Stop is stopped twice — network + CPU.

### R11 — Insider write storm / DoS on real PLC1 (T0814) — **PASS**
- Storm (10 Hz, 15 s) from `.2.77` on Q0.3. TB1 `.3` relay **clicked once** (CC-54 first-packet, audibly confirmed) then CARS
  `S7 CONTROL => ISOLATE source .2.77` repeatedly; storm connection cut (`S7TimeoutError`). Hundreds of attempted writes →
  one relay tick. Physical process protected. (Relay left on at cut; resets on the power-cycle / reset step.)

### R12 — HMI identity spoof / masquerade (T0856) — GUARD anti-spoof — **PASS**
- Insider forged HMI `.2.9` (5 spoofed-IP + 5 forged gratuitous-ARP from Kali's own MAC/port). GUARD table-0 drop counters
  `ip,nw_src=.2.9 => drop` and `arp,arp_spa=.2.9 => drop` both incremented `0 → 10` — every forged frame dropped at T0
  before reaching the loop or poisoning ARP. HMI identity un-wearable from the insider port.
- GUARD structure (measured): protected identities `.2.9` (HMI), `.2.10` (PLC), `.2.30` (historian) each have a priority-100
  drop for any frame claiming their IP/ARP, with legit bindings at priority 200 (e.g. `.2.30` from `sup0`+correct MAC).
- **Honest config-completeness note:** the operator `.2.31` is NOT in the anti-spoof set → a `.2.31` spoof would pass GUARD.
  Critical loop identities (HMI/PLC/historian) are covered; a complete deployment should bind ALL trusted hosts (`.2.31`
  addable as one drop rule). The mechanism works; the binding table is only as complete as configured.

## Insider vantage (Kali .2.77) — COMPLETE: R2, R3, R5, R6, R7, R11, R12 all PASS (with documented nuances).

### R1 — Remote System Discovery from IT/external (T0846) — GNS3 kill chain — **PASS**
- Kali placed in the IT zone `10.0.40.66` (replacing VPCS, off Ent-FW); attacks route IT→Ent-FW→DMZ→OT-FW(SNAT)→it0→ovsgw.
  Kali `ip route get 192.168.2.10` → `via 10.0.40.1 dev eth2` (genuinely through the Purdue chain; insider NIC eth1 down).
- Ping PLC1: 100% loss. Snort saw source **192.168.2.1** (OT-FW SNAT) on it0. CARS: `FORBIDDEN 192.168.2.1(gateway) ->
  192.168.2.10 ICMP => BLOCK conduit (all switches)`. **External attacker blocked at the OT boundary.**
- **KEY FINDING — SNAT collapses source identity (ties to G5):** the OT-FW SNATs ALL IT traffic to `.2.1`, so every
  external attack — regardless of technique — appears to CARS as the single `.2.1(gateway)` identity, which CARS treats as
  FORBIDDEN and blocks wholesale. Safe but COARSE: CARS cannot distinguish a legit EWS from an attacker behind the NAT.
  Consequence: operation-aware DPI (A3) is exercised from sources that CAN connect (allowlisted insider/operator), NOT from
  the fully-blocked external path. Strong proactive-boundary result + honest granularity boundary.

### IT crafted ICS attack (S7 write from IT) — boundary — **PASS**
- S7 write from Kali IT-mode → `S7ConnectionError: TCP connection failed: timed out`. CARS: `FORBIDDEN .2.1(gateway) ->
  .2.10 TCP => BLOCK`. Even a crafted ICS payload from IT is blocked at the boundary before the handshake. Covers
  "professionally-crafted ICS attack from the IT VM → blocked."

### R8 — Program Download FC43 (T0843 / T0889) — insider — **PASS**
- `mb_attack --attack program` (FC43 0x2B) from `.2.77` → `MODBUS PROGRAM => BLOCK conduit`. Logic/program download detected
  as PROGRAM and forbidden (first-packet got a Modbus response, CC-54, then cut). Matches T0843 detection guidance
  (alert on logic download from a non-EWS source).

## MITRE ATT&CK for ICS — COVERAGE (all 8 targeted techniques exercised from real VMs):
| Technique | Rows | Result |
|---|---|---|
| T0846 Remote System Discovery | R1 (IT), R2 (insider) | BLOCKED — no service enumerable (L2 MAC visible only) |
| T0855 Unauthorized Command Message | R3, R5 | BLOCKED (control ops cut) |
| T0831 Manipulation of Control | R3, R5, R11 | BLOCKED |
| T0836 Modify Parameter | R6 | DETECTED + THROTTLED (not value-inspected — honest) |
| T0816 Device Restart/Shutdown | R7 | BLOCKED (network) + PLC native refusal (double-layer) |
| T0843 Program Download | R8 | BLOCKED (PROGRAM classified) |
| T0814 Denial of Service | R11 | BLOCKED — process protected (1 relay tick then ISOLATE) |
| T0856 Spoof Reporting Message | R12 | BLOCKED at T0 (GUARD anti-spoof) |
Boundary/coarse: IT-originated attacks all SNAT→`.2.1(gateway)`→blocked wholesale (safe but no per-source granularity, G5).

## VD-6 — PROCESS INTEGRITY: live PLC process + no-harm under attack — **PASS (real hardware)**
- **Implemented a real closed-loop process on PLC1** (real Siemens S7-1200, CPU 1212C): bang-bang tank-level control in
  SCL (cyclic interrupt OB, 100 ms), pump actuator = `%Q0.3` relay, cycling on/off every ~4–5 s autonomously. Programmed
  via TIA Portal (point-to-point download), running independently on the OT network. Modelled on the Cárdenas-group water
  tank (LIT thresholds, pump ON<low / OFF>high) — but on **real hardware**, a step beyond their Mininet co-simulation.
- **No-harm test:** 20 s S7 control-injection storm (write flood @10 Hz on Q0.3) from a **compromised operator** (`.2.31`).
  CARS: `CONTROL => BLOCK conduit → ISOLATE source .2.31` (attacker severed, snap7 Receive-timeout). The PLC's internal
  100 ms loop reasserted Q0.3 *and* CARS quarantined the source within ms.
- **RESULT (observed on TB1):** the relay **kept its steady ~4–5 s rhythm throughout the storm — no visible disruption.**
  **Process integrity preserved under attack, on real hardware. The central thesis claim, demonstrated.**
- Note: the Kali insider VM had a post-`eth1`-flap VMware L2 fault (ARP reply not returning via `vmnet2`), so the storm ran
  from the operator conduit — equally valid (a compromised *trusted* operator). The `.2.77` insider storm→ISOLATE dynamic
  was already proven in R11 (with the relay clicking then silenced).

## VALIDATION DAY — VERDICT
Real-VM attackers (Kali insider + GNS3 IT kill chain) exercised the full **MITRE ATT&CK for ICS** target set (T0846, T0855,
T0831, T0836, T0816, T0843, T0814, T0856) — all detected + blocked, with honest nuances (T0836 throttled-not-value-inspected;
IT attacks SNAT-collapse to `.2.1`, safe-but-coarse, G5; L2 MAC visible in recon). GUARD dropped identity spoofing at T0.
A **real PLC-controlled process** was protected end-to-end: quarantine the attacker, process runs unharmed. 
**Still open (next session, optional):** multi-source concurrent DDoS + load/latency numbers; DPI-evasion (R13, tests G3);
R14 compromised-trusted-CRITICAL-loop live demo (documented boundary G1). Core attack-coverage + no-harm = DONE.
