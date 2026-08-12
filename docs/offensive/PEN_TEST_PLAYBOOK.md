# CARS — Open Red-Team Pen-Test Playbook (2026-07-25)
_Authorized adversarial assessment of the CARS SDN-IDR testbed for the MSc dissertation. Full kill-chain, both cells + supervisory stack, aggressive with disarmed baselines to capture raw process impact vs CARS-protected outcome. Mapped to **MITRE ATT&CK for ICS**._

## Scope & targets
| Asset | IP | Crit | Notes |
|---|---|---|---|
| PLC1 / Tank1 | .2.10 (Cell-1) | CRITICAL | S7-1200 1212C, DB7 "Sim" in-PLC bang-bang, pump Q0.3, band 30-70 |
| PLC2 / Tank2 | .3.10 (NAT→.2.10, Cell-2) | HIGH | same program, band 20-55 |
| HMI1 | .2.9 | HIGH | KTP700 |
| Modbus sim | .2.20 | LOW | pymodbus, hr[8]=safety reg |
| Historian collector (Node-RED) | .2.30 / .3.66 | MEDIUM | reads both PLCs → MQTT → InfluxDB |
| Supervisory stack (Dell#1) | localhost | – | MQTT :1883, Node-RED :1880, InfluxDB :8086 (token `cars-token-change-me`), Grafana :3000, FUXA :1881 |
| Attacker vantages | atkns `.2.66`, Kali insider `.2.77`, IT/GNS3 (`.2.1` SNAT) | – | |

## Adversary model — BLACK-BOX, POSITIONAL (zero knowledge)
The attacker knows **nothing** at the start — not the assets, protocols, IPs, or that CARS/SDN exists. Everything must be discovered. We run the kill-chain from **multiple positions in sequence**, documenting how far each gets and what stops it:
1. **Position IT** (enterprise zone, GNS3) — *start here*. Can an external IT attacker even discover/reach OT through the firewall chain + CARS?
2. **Position OT-insider** (Kali `.2.77` / `.2.66`, L2 on the OT segment).
3. **Position supervisory** (foothold on the collector/`.2.30` vantage).
Goal at each: discover → reach → manipulate the physical process → spoof reporting. _(InfluxDB de-scoped per operator.)_

## Method — each vector run twice
1. **DISARMED baseline** (`defense off`, remediation may be OFF for pure impact) → observe raw physical/data impact.
2. **ARMED CARS** (`defense on`, remediation ON) → observe detection + response + restore.
Contrast = the dissertation result. Between vectors, return to safe state (below).

## Safe-state / recovery (run between phases)
```
curl -s -XPOST http://10.10.10.1:8080/cars/defense -H 'Content-Type: application/json' -d '{"on":true}'   # re-arm
# clear any stuck isolate flows
for sw in ovs1 ovsgw; do sudo ovs-ofctl -O OpenFlow13 --strict del-flows "$sw" "table=1,priority=110" 2>/dev/null; done
# restore process values (remediation also does this): re-run PLC programs to RUN if STOPped (TIA), or power-cycle the actuator relay
sudo ip netns exec ctlns python3 /home/msclab/cars_process.py   # (optional) reassert bang-bang if used
```

---
## PHASE 0 — Recon (T0846 Remote System Discovery, T0842 Network Sniffing, T0840 I/O Image)
Goal: from the insider, map the OT + supervisory attack surface; see what CARS detects.
- Host/port sweep of OT subnet + PLCs + supervisory ports.
- Establish which recon CARS's SUSPECT rules catch (ICMP/TCP-SYN to PLC/HMI) and what it misses (supervisory ports, sniffing).
Commands issued per-phase during execution.

## PHASE 1 — Access & Network (T0830 MITM/ARP, T0886 Remote Services, T0812 Default Creds)
- ARP-spoof / MITM on the OT segment → GUARD anti-spoof (T0 bindings) expected to block.
- IT→OT pivot via GNS3 (SNAT `.2.1`) → default-deny + identity-collapse (G5).
- Cross-cell reach (`.2.66` → `.3.x`) → segmentation test.

## PHASE 2 — Heavy ICS protocol attacks (T0855 Unauth Command, T0831 Manipulate Control, T0836 Modify Parameter)
- S7 write / control / **STOP (0x29)** on PLC1 and PLC2 (halt = max impact).
- Modbus FC5/6/15/16/8/43/illegal on `.2.20`.
- Disarmed → PLC halts / relay flips (impact). Armed → BLOCK/ISOLATE, criticality-scaled (PLC1 75s vs PLC2 60s).

## PHASE 3 — Sensor spoofing / False Data Injection (T0832/T0856 Spoof Reporting, T0839 Module Firmware n/a)
- `db_write` DB7.Level on **both** tanks: pin low → pump latches ON → overflow; pin high → pump off → dry.
- Disarmed → false HMI/Historian + physical latch. Armed → CARS blocks the write **and** remediation restores last-good (the P1 novelty), both cells.

## PHASE 4 — Flooding / DoS (T0814 Denial of Service, T0815)
- S7/Modbus op-flood → A5 rate detection → THROTTLE/BLOCK.
- Connection-exhaustion on PLC :102.
- Control-plane stress (OpenFlow) → SDN resilience.

## PHASE 5 — Supervisory / data-layer attacks (T0859 Valid Accounts, T0872 Indicator Removal, poisoning)
- **MQTT publish-spoof**: inject fake `cars/cell*/plc*/level` → poison Historian + HMI (broker reachability test: localhost-only vs network).
- **InfluxDB weak token** (`cars-token-change-me`): read/write/delete Historian buckets.
- **Node-RED :1880**: unauth editor → inject/exfil flow.
- **Grafana :3000 / FUXA :1881**: default creds.
- Collector-conduit abuse: write from `.2.30`/`.3.66` → CARS FORBIDDEN/ISOLATE (already shown Cell-1).

## PHASE 6 — Combined impact + mitigation (capstone)
- Multi-vector disarmed devastation on both tanks (spoof + actuator flip + flood) → capture worst-case process state.
- Re-arm → CARS + remediation recover → capture the protected outcome.

## Findings log (filled during execution)
| # | Phase | Vector | MITRE | Disarmed impact | Armed CARS outcome | Gap/Note |
|---|---|---|---|---|---|---|
| P0-1 | 0 | Full-subnet nmap recon from unknown `.2.77` | T0846 | (baseline pending) | **PLC1 `.2.10` + Modbus `.2.20` INVISIBLE** — A2 default-deny drops probes pre-SYN; attacker cannot enumerate the critical PLC | Strong: proactive concealment of crown jewels |
| P0-2 | 0 | Same scan, HMI1 `.2.9:102` | T0846 | — | HMI1 leaks a SYN-ACK (port 102 "tcpwrapped") then CARS reactively blocks; dashboard shows "`.2.77`→HMI1" | **GAP: `.2.9` not in A2 default-deny** → reactive-only, initial probe leaks. Fix: add `(1,"192.168.2.9")` to default_deny |
| P0-3 | 0 | Same scan, supervisory ports | T0846/T0842 | — | **FUXA :1881, Grafana :3000, InfluxDB :8086 reachable** at `.2.30`+`.2.67` (Dell#1 0.0.0.0 binds); CARS doesn't gate them | **GAP: supervisory stack exposed to OT segment.** (MQTT :1883 localhost-only ✓; Node-RED :1880 paused) |
| **P0-4** | 0 | **Attacker VM POSTed `/cars/defense` to `10.10.10.1:8080`, toggled enforce on/off** | **T0878 Alarm Suppression / T0814** | **silent CARS disarm** (`{"enforce_enabled":false}`) | ~~NO auth; NO log~~ | **CLASSIFIED (test-VM artifact via eth0 NAT) + FIXED (CC-85, 2026-07-27):** control API now requires `X-CARS-Token` on defense/maintenance/reload/reload-a2/block/unblock/restore + audit-logs every attempt (`CONTROL … DENIED/AUTHORISED`). Token at `~/cars/api_token` (0600, control-plane only). **Proven: no-token disarm → 401 + logged; with-token → works.** `/cars/respond` (bridge feed) + read GETs unchanged. |
| note | — | **Kali is triple-homed** | — | — | — | eth1=`.2.77` (OT insider), **eth2=`10.0.40.66` (IT/enterprise position — we DO have an IT vantage)**, eth0=NAT/mgmt (do not attack from this). Use `nmap -e eth1` / `-e eth2` to source correctly. |
| **P0-5** | 0 | Confined-insider scan of PLC1 `.2.10` + Modbus `.2.20`, **armed AND disarmed** | T0846 | disarmed: **still ALL ports filtered** | armed: all filtered | **SUCCESS + strong finding: A2 proactive default-deny is ARM-INDEPENDENT** — crown jewels invisible even with defense OFF. Only L2 leak: host exists (ARP) + Siemens MAC OUI. |
| **P0-6** | 0 | Same scan, HMI1 `.2.9` | T0846 | disarmed: **102 open + all ports enumerated + full OS fingerprint** | armed: 102 open (tcpwrapped) + some resets, then ISOLATE 60s cut it | **LIMITATION (not fixable via default-deny) — CC-86a:** adding `.2.9` to `default_deny` DID shield recon (`.2.9:102`→`filtered`) but **broke HMI1's display** — an HMI is a CLIENT that polls the PLC and needs the REPLIES back (reply dst=`.2.9`), which a stateless L3/L4 default-deny drops. **REVERTED**, then **properly FIXED via SDN Phase 1 stateful conntrack (CC-89):** `.2.9` back in default-deny, but OVS `ct()` `+est` passes the HMI's own replies → **HMI recon-shielded (`.2.9:102 filtered`) AND functional (panel live)**, proven on the live fabric. The stateless-L3/L4 limitation is now closed by exploiting an SDN capability plain OpenFlow lacked. |
| **P0-7** | 1 | Confined OT insider (eth1) → Cell-2 `.3.10`/`.3.9` | T0846 | "failed to determine route" | same | **SUCCESS: OT-Cell-1 insider has NO route to Cell-2** — cross-cell segmentation holds. |
| perf | — | Reactive enforcement (armed) | — | — | FORBIDDEN→ISOLATE **0.25–0.76 ms**, criticality-scaled (`.2.10`=75s CRIT, `.2.9`=60s HIGH), **FLOOD 14-15 ops/s** flagged, auto-heal on timeout. Disarmed: "would ISOLATE (monitor only)" 0.01–0.07 ms. | Armed/disarmed semantics exact. |
