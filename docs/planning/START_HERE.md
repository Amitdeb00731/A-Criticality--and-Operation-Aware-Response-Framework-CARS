# START HERE — Session Primer (Project CARS)

**Purpose:** the project's memory. At the start of any session, read this + `DECISION_LOG.md`
to reload full context. Keep this file current as the single source of truth.

_Last updated: 2026-07-05_

## One-liner
Reactive SDN for securing ICS. Owner: **Amit Kiran Deb** · Bristol Cyber Security Group ·
supervisor **Joe Gardiner**. MSc dissertation, ~6 weeks. Working title **CARS**
(Criticality-Aware Response) — *a lead hypothesis, not the final contribution.*

## North star
A productizable, trustworthy **reactive-and-proactive SDN defence for ICS** that consumes
detection events and enforces **criticality-aware network responses** which are *provably safe*
(bounded, reversible, evidence-generating) — so an operator can enable automated response
**without risking the process**. Deployable as a zone-boundary overlay (brownfield-friendly).

## Locked decisions
- **Testbed = Tier 3** (full Purdue L0–L5: DMZ + corporate zone + dual firewalls; IT→OT kill chain). Build **incrementally**.
- **Hardware (ground truth, from photos 2026-07-05):** **2× Siemens S7-1200 PLCs**, each with a **real SIMATIC HMI panel** (KTP700 Basic? confirm), real I/O (relays / 24V in). **MikroTik hEX lite** switch. 3× UGREEN USB3→GbE, 3× cables. 2× Dell (dual-boot), 1× Asus (Win 11), MacBook.
- **Hosts:** Dell#1 Ubuntu = SDN core (Ryu + **Open vSwitch**) + historian. Dell#2 Ubuntu = IDS + attacker + GNS3/Docker VMs (DMZ, corporate, firewalls). Asus Win 11 = TIA Portal (EWS) for both PLCs + optional Ignition SCADA. 2× S7-1200 + 2× HMI = real L1/L2. **MikroTik = physical zone switch** (not the SDN fabric). MacBook excluded.
- **L0 process:** **real PLC I/O (LEDs/relays)** — Factory I/O dropped (CC-7). No OpenPLC soft-PLC (two real PLCs).
- **SDN switch:** **Open vSwitch on Dell #1** under Ryu (CC-6). MikroTik OpenFlow is experimental/v6 → not the critical path.
- **Protocols:** S7comm (PLC/HMI + realism) · **Modbus TCP** (primary CARS traffic, enable Modbus server on PLCs) · OPC UA / MQTT optional.
- **Orchestration:** GNS3 on Dell #2 for the virtual zones (firewalls/DMZ/corp); OVS on Dell #1 is the CARS-controlled fabric.
- **D4:** consume existing IDS (Suricata/Zeek), do NOT build a new detector. **D5:** "proactive" = posture escalation, not full MTD.
- **Contribution = TBD** among 6 candidates (safety-constrained response [CARS lead] / source-agnostic orchestration / hybrid data-plane / twin-validated / deception ladder / resilient control plane).

## Standing rules (non-negotiable)
0. **★ QUESTION EVERYTHING — the prime rule (highest priority).** Challenge every statement that defines the engine, every piece of logic we implement, every change to scope or goal, and every modification to the core logic — *before* it is accepted. Deep technical reasoning is mandatory and never skipped. Nothing enters the engine or the design unchallenged; if a claim, mechanism, or decision cannot survive rigorous scrutiny, it does not go in. This rule outranks momentum, convenience, and my own prior recommendations — I must challenge my *own* proposals as hard as the user's.
1. **No hallucination, no fluff, no gap.** Sources or `[UNVERIFIED]`/`[ASSUMPTION]` tags; measured vs expected labelled; name gaps; be concise. Verify every NEW citation before use.
2. **Mandate:** apply deep analysis, sharp questioning, strong reasoning; push back on our own decisions.
3. **De-scope fidelity, never the contribution.** If behind, use the ladder (see execution plan).
4. **File-locked context (hard rule).** Everything is locked in the files, never only in chat. Every decision/number/change is written to the relevant file the same session. The record stays **bulletproof, no gap** — no dangling refs, nothing living only in memory. Update `DECISION_LOG.md` + trackers as we go.

## Current status
- Done: literature review; verified master reading list (58 items, **0 hallucinated citations**, Phase 8 safety cluster added); Tier 3 architecture; decision log; **6-week execution plan**.
- **PHASE A DONE (2026-07-06):** Dell#1 Ubuntu 24.04 + OVS 3.3.4 (`br0`); controller = **os-ken 2.8.1** venv `~/cars/venv` running our own `~/cars/l2_switch.py`;
### ★ DAY STATE (2026-07-13) — testbed fully live + evaluated
Hardened testbed up (guard+arp-guard armed, fail-secure, cars-seams service persists seam IPs). Dashboard v5 live-sync (port bindings, link-health, guard telemetry, dated feed) on Dell#1 `python3 ~/cars_dashboard.py`. GNS3 `cars-killchain` up (external path live; OT-FW .1 discovered on it0). Detection loop up (Snort on snort0 + `~/snort_bridge.py`, cooldown=3). Engine v0.7 (dates, `/cars/links` ports, `/cars/guard`, `resp_ms`/`cars_ms`).
**★ MTTM RESULT: CARS decide+enforce = 0.613 ms (sub-ms); end-to-end MTTM = 1.132 s mean (min 139 ms) — ~99.95% Snort detection, not CARS.** See `07_Evaluation/MTTM_EVALUATION.md`, `~/mttm_results.csv`, `~/mttm.py`.
**NEXT (agenda order):** AG3 = P4 transit ovs2->ovsgw (harden the P150 uplink-guard FIRST per audit C-1/H-1) · AG4 = Cell-2 IDS detection · external-path MTTM (scripted VPCS) · optional Snort DAQ/pcap tuning · write-up (contribution + hardening + evaluation chapters assemble from DECISION_LOG CC-1..CC-28).
c:a0:62:b7:4c; box2 PLC e0:dc:a0:46:ff:ce / HMI e0:dc:a0:5c:60:44.
- **Restart recipe:** hAP on; laptops wired-static (nmcli `cars-mgmt`, 10.10.10.1/.2/.3). Dell#1/#3: `ovs-vsctl show` (if no controller line: `set-controller br0 tcp:10.10.10.1:6653`). Dell#2: `cd ~/cars && source venv/bin/activate && osken-manager ~/cars/cars_engine.py` → dpid 1,2. Event API: `curl -X POST http://10.10.10.1:8080/cars/block -d '{"dpid":1,"src":"<HMI>","dst":"<PLC>"}'`.
- **INFRASTRUCTURE COMPLETE.** (Gotcha: hAP DHCP 192.168.88.x hijacks manual IPs → use nmcli static.)
- **OT SUPERVISORY ZONE STANDING (2026-07-07, CC-14):** on **Dell#1** via OVS internal port **ot0=192.168.2.30** (CARS-visible path to PLC .10, ping-verified; **IP now auto-restored on boot via systemd `ot0-ip.service`** — no manual re-add needed). **Historian = InfluxDB 2.7 :8086 + Grafana 11.1 :3000**; **SCADA = FUXA :1881** (built-in S7/Modbus drivers). Docker 29.4.0, stack in `~/ot-stack/`. **Terminology locked:** "controller" = SDN/CARS enforcer (Dell#2) only; SCADA/Historian/EWS = supervisory *servers*, never on the controller. Two-tier OT→IT (IEC 62443 zones/conduits) is the plan; Dell#3/dpid=2 = future IT/DMZ switch. **Gated:** live tags need PUT/GET (or MB_SERVER) enabled on Box1 PLC (brief reversible TIA download). EWS (Asus) OT-plane link still to wire.
- **EWS CONNECTION DEFERRED (2026-07-07):** Dell#4 (Windows/TIA) chosen as dedicated EWS (correct per Purdue/IEC 62443 — L2/L3, high-value target, conduit to PLC policed by CARS). Blocker: **Dell#1 out of NICs** (RJ45=control, 2×USB=PLC/HMI; no free USB, no hub). Tried **hAP VLAN-trunk** (new VLAN20=OT; Dell#1 port=trunk; Dell#4→ether5 access) to add Dell#4 with no new hardware. VLAN table staged fine, but enabling `vlan-filtering=yes` **dropped the WinBox session** (switch-chip reprogram blip). Stopped + reverted; Dell#4 unplugged; **control plane verified healthy**. ⚠️ **hAP may still be vlan-filtering=yes with VLAN entries — VERIFY/clean next session:** WinBox via MAC **DC:2C:6E:A9:A7:10** → `/interface bridge set bridge vlan-filtering=no` + remove vlan-ids 1&20. Backup exists: `cars-hap-before-vlan.backup`. **Recommended next-session path: ~£8 USB-C→Ethernet dongle on Dell#1** (skips hAP entirely, zero control-plane risk) → add to br0 → Dell#4=192.168.2.40. Alt: retry VLAN in WinBox **MAC-mode** + an **on-hAP 2-min auto-revert scheduler** so a session blip can't trip it. (Also noted: Dell#4 on lab WiFi sees a 2nd `192.168.88.1` = lab router — expected clash, ignore.)
- **NEXT (contribution, pure software):** v0.4 = **conduit-criticality "trust brain"** (DESIGN CONFIRMED 2026-07-08 — see DECISION_LOG **CC-15**; code deferred, "write later"). **Criticality = property of the CONDUIT** `(src,dst,service)`, NOT the device (a device carries flows of opposite criticality → device tags insufficient; maps to IEC 62443 conduits + OpenFlow 5-tuple). Two layers: static `devices.yaml` roles → conduit-policy → per-flow criticality. Guard (confirmed): CRITICAL control conduit → hard-block **REFUSED**, mirror-only (safety invariant); OPERATIONAL → block ok; SENSITIVE (ews) → block-on-anomaly; FORBIDDEN (unknown) → block on sight; all decisions logged (audit trail). Then v0.5 IDS integration (Suricata/Zeek→Event API), then attack scenarios + evaluation. Note: os-ken lacks `os_ken.app.wsgi` → **Event API now uses eventlet-native WSGI** (stdlib `http.server` hung under the eventlet hub — abandoned). Regen Tier3 doc to real hardware someday.
- **Event-API fix log (2026-07-07):** (1) stdlib `http.server` bound :8080 but never accepted under eventlet hub → replaced with `eventlet.wsgi.server(eventlet.listen(('0.0.0.0',8080)), app)` in `hub.spawn`. (2) dispatch bug: `"unblock".endswith("block")` routed unblock→block → fixed to `endswith("unblock")` check first. Both verified.
- **SCALE-UP DIRECTION (2026-07-08, CC-16):** consolidate laptop-sprawl via virtualization. **GNS3 multi-appliance** chosen for the **IT→OT kill-chain periphery** (enterprise/DMZ/dual firewalls/attacker) — appliance realism for evaluation. **Guardrails (hard):** GNS3 = periphery ONLY; **CARS core (real PLCs/HMIs + OVS br0 + controller) stays BARE METAL**, never inside GNS3; single seam = GNS3 Cloud node ↔ br0; **measure MTTM on native br0** (decomposed detection/decision/enforcement), firewalls upstream of t0 (appliance realism = attack-path external validity, NOT part of the measured latency; nesting the loop in GNS3 contaminates timing). **Timebox** GNS3; fallback = one real MikroTik/pfSense firewall. **CC-16a RESOLVED (2026-07-08):** GNS3 on **Dell#1** (native Ubuntu, **internal `it0`↔br0 seam**, zero new hardware; 16GB+ → light appliances; core KEPT not rebuilt, GNS3 = periphery only; portable → migrate later if timing shows CPU contention).
- **GNS3 SEAM PROVEN (2026-07-08, G1–G2):** GNS3 2.2.59 native on Dell#1 (30GB RAM, KVM ok). OVS internal seam **`it0`** on br0 (no host IP). GNS3 Cloud node→it0 + VPCS host (192.168.2.50) **pinged REAL PLC 192.168.2.10 through br0 (~4ms)** → virtual↔real integration validated; **CARS block of GNS3 host→PLC verified** (VPCS ping timed out on block, recovered on unblock) = **G2 SEALED — CARS provably controls GNS3-originated traffic against real hardware.** `it0` persistent via `ot0-ip.service` (now up's both ot0+it0). Full detail: `06_Build/BUILD_LOG.md` Checkpoint G1–G2.
- **GNS3 KILL CHAIN BUILT (2026-07-08, G3a–G3b):** VyOS rolling (`vyos-2026.06.30`) installed to disk as **OT-FW**, then GNS3-**Duplicated** into **Ent-FW**, both native on Dell#1. Full routed path **VPCS (IT 10.0.40.66) → Ent-FW → DMZ 172.16.35.0/24 → OT-FW (NAT) → it0 → br0 → REAL PLC**, verified end-to-end (TTL **30→29→28** across the two firewalls; real PLC untouched via OT-FW SNAT). Addressing: **IT 10.0.40.0/24** (gw Ent-FW .1) · **DMZ 172.16.35.0/24** (Ent-FW .1 / OT-FW .2) · OT-FW eth1 **192.168.2.1** SNAT. Static routes both directions. **Clone gotcha (logged):** GNS3 Duplicate → new MACs → VyOS persistent-net renamed the clone's NICs **eth4–eth7** (not eth0/1); configure the actual names, delete phantom eth0/1. **Diagrams saved:** `06_Build/it_ot_network_topology.png` (subnets/IPs/MACs/connections), `asbuilt_topology.png` (regenerated), plus tiered + high-level views. Full detail: BUILD_LOG G3a/G3b.
- **★ CLEAN REBUILD DONE + VALIDATED (2026-07-10, P0–P5a):** Fabric rebuilt from scratch with clean names/dpids (kept os-ken + GNS3 + Docker). **ovs1 (dpid1, Box1: PLC1+HMI1) on Dell#1 · ovs2 (dpid2, Box2: PLC2+HMI2) on Dell#3 · ovsgw (dpid3, GATEWAY) on Dell#1**; ovs1↔ovsgw via OVS patch; controller (Dell#2) manages dpid 1/2/3. **CC-19: NO re-IP** — cells told apart by MAC+dpid (Box2 TIA project missing; identical IPs fine, boxes kept as-is). GNS3 seam `it0` moved to **ovsgw**; kill chain verified (VPCS→Ent-FW→OT-FW→ovsgw→ovs1→**real PLC1**, TTL 28). **Gateway enforcement VERIFIED:** CARS block on **dpid=3** (OT-FW MAC `0c:5d:b4:41:00:01`→PLC1) severs the attacker; unblock restores. Cell1 loop block/restore (dpid=1) also re-verified. **Current build = CLEAN_BUILD_SPEC interim (3-OVS).** Full detail: BUILD_LOG "CLEAN REBUILD". **P5b DONE** (sup0 192.168.2.30 on ovsgw, reaches PLC1). **★ P6 DONE — AUTONOMOUS reactive loop closed:** OVS mirror `m0` (ovsgw→`snort0`) → **Snort 2.9.20** (`/etc/snort/cars.conf`+`cars.rules`, sid 1000001) → **bridge `~/snort_bridge.py`** (Dell#1, tails alert → POST /cars/block dpid=3 OT-FW MAC `0c:5d:b4:41:00:01`→PLC1). Verified: Snort detect → CARS block at gateway, **no manual curl**. **TESTBED CORE COMPLETE.** NEXT: **v0.4 trust brain** (contribution) + evaluation (MTTM, safety invariant, Cell2 via DNAT). Restart P6: `sudo snort -A fast -i snort0 -c /etc/snort/cars.conf -l /var/log/snort` + `python3 ~/snort_bridge.py`.
- **★ v0.5.1 LIVE DISCOVERY + NOC CONSOLE (2026-07-11):** engine adds sensing (switch up/down, host discovery, port up/down, LLDP links) — brain UNCHANGED. New API: `/cars/hosts /ports /links /audit`. Launch controller with `osken-manager --observe-links ~/cars/cars_engine.py`. Backups on Dell#2: `cars_engine_v04_stable.bak`, `cars_engine_v05.bak`. Discovery-driven dashboard = `~/cars_dashboard.py` on Dell#1 → `python3 ~/cars_dashboard.py` → http://localhost:8090. Repo copies: `06_Build/cars_engine.py`, `06_Build/cars_dashboard.py`. Verified: link up/down tracks power-cycling live; LLDP shows ovs1↔ovsgw + ovs2 isolated. Fixed: dpid+MAC host keying (clones), port snapshot, ignore `0.0.0.0` boot ARP probes.
  **NEXT (morning):** 1) restart controller w/ the `0.0.0.0` patch + `ping -c2 -I sup0 192.168.2.10` → confirm `/cars/hosts` shows PLC1/PLC2 real IPs (no 0.0.0.0). 2) label/confirm the **two MACs @ 192.168.2.30** (sup0 vs SCADA/Historian container). 3) then: P4 transit · evaluation (MTTM) · write-up.

### ★ TOMORROW'S AGENDA (2026-07-12) — HARDENING PASS
Theme: harden everything end-to-end. Apply Rule 0 (question every policy/logic/change).
1. **Policy hardening** — audit `classify()` for every conduit: coverage gaps, over-broad FORBIDDEN, spoofing (trusted-IP impersonation → needs MAC↔IP binding), SENSITIVE/EWS path, both-direction conduits, Cell 2 policy. Verify the CRITICAL safety-invariant holds under all inputs.
2. **Conflict check** — overlapping/duplicate flow rules, priority collisions, block vs L2-learn interactions, the two-MACs-@-.30 ARP flap, clone-IP routing conflicts.
3. **Connectivity** — every conduit reachable as intended; legit loops untouched; ovs2/Cell2 path (P4); control-plane isolation; supervisory paths.
4. **Centralized intelligence** — is the brain the single source of truth? audit trail complete? decisions deterministic + logged? edge cases.
5. **Monitoring dashboard** — hardening: stale-node handling, discovery edge cases, block overlay correctness for clones, resilience if controller drops, polish.
Deliverable: a hardened, conflict-free, fully-covered CARS + a verification pass (subagent review recommended for high-stakes policy check).
- **★★ v0.4 TRUST BRAIN DONE + AUTONOMOUS (2026-07-10):** `cars_engine.py` v0.4 on Dell#2 = **device registry** (IP→role) + **conduit-criticality `classify()`** (CRITICAL/FORBIDDEN/SENSITIVE/OPERATIONAL) + **SAFETY GUARD** (critical loop → REFUSED, never hard-blocked) + `/cars/respond` (brain) + IP-conduit block + `/cars/restore` + audit log (`~/cars/cars_audit.log`). Snort bridge v2 (`~/snort_bridge.py`) reports flows to `/cars/respond`; **brain decides autonomously.** VERIFIED: insider(unknown)→PLC = **BLOCK** · supervisory(historian)→PLC = **ALLOW** · hmi→plc(loop) = **REFUSED** — same detector, opposite outcomes by role, hands-free. **THE CONTRIBUTION IS DEMONSTRATED.** Repo copy: `06_Build/cars_engine.py`. NEXT (research layer): **evaluation** (MTTM latency · formalize safety invariant · block-lifecycle auto-restore · Cell 2 via DNAT) + **write-up**.
- **Restart (current fabric):** Dell#1: `ovs1`(PLC1 enx…d874, HMI1 enx…aef0)+`ovsgw`(it0, patch); Dell#3: `ovs2`(PLC2 enx…3f16, HMI2 enx…3cf9). Controller Dell#2: `cd ~/cars && source venv/bin/activate && osken-manager ~/cars/cars_engine.py` → dpid 1/2/3. GNS3 project `cars-killchain` (start nodes). MACs: PLC1 e0:dc:a0:63:98:09 · HMI1 e0:dc:a0:62:b7:4c · PLC2 e0:dc:a0:46:ff:ce · HMI2 e0:dc:a0:5c:60:44 · OT-FW(OT side) 0c:5d:b4:41:00:01.

## Open items / gates
- **CC-1** scope: conduit-only vs intra-zone? (resolve Week 1)
- **CC-2** define exact action set + rollback guarantee (before Phase D)
- **CC-3** how safety is *proven* — envelope invariant and/or twin dry-run (resolve Week 1)
- **CC-4** measure CARS-added latency/jitter (Week 2)
- **CC-5** ✅ resolved — citations verified
- Cite-time residuals: CHAOS article ID; use **NIST SP 800-82 Rev. 3**; confirm Co-Engineering survey authors.

## File map
- `START_HERE.md` — this primer.
- `DECISION_LOG.md` — decisions, assumptions, integrity rules, critical-challenges thread.
- `README.md` — project index + status checklist.
- `MASTER_READING_LIST.md` — 58 sources, ordered, verified (📁 local / 🌐 fetch).
- `VERIFICATION_REPORT.md` — citation verification (CC-5).
- `01_Literature_Review/` — review + reading-list & gap-analysis docs.
- `02_Research_Notes/` — research notes (`research_notes.md`).
- `03_Build_Scripts/` — doc/diagram generators.
- `04_Testbed/` — components analysis, Tier 3 architecture, topology diagrams, **PRE_BUILD_CHECKLIST.md**.
- `05_Execution/` — 6-week plan + **EXECUTION_TRACKER.md** (tick weekly).
- `_archive/` — superseded files, kept not deleted (see `_archive/README.md`). Not part of the active plan.
- `papers/` + `papers/survey/` (in the other connected folder) — the 23 local PDFs.

## How to resume next session
Say: **"Read START_HERE and DECISION_LOG, then continue."** That reloads everything.
Then either *"let's start Phase A"* or name the task.
