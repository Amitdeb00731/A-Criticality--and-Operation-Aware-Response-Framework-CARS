# Build Log — Project CARS testbed

Running log of the build. Each checkpoint: command → result → status. File-locked (no gap).
Hardware: 2× S7-1200 + 2× SIMATIC HMI (real I/O) · MikroTik hEX lite (zone switch) ·
Dell#1 Ubuntu (Ryu+OVS) · Dell#2 Ubuntu (IDS/attacker/VMs) · Asus Win11 (TIA Portal).
SDN switch = OVS on Dell#1 (CC-6). L0 = real PLC I/O (CC-7).

_Started: 2026-07-06_

---

## PHASE A — minimal real loop (PLC ↔ HMI through OVS, Ryu managing OVS)

### Checkpoint A1 — Dell#1 Ubuntu base + Open vSwitch + NIC discovery
Status: **DONE (2026-07-06)**
- OVS **3.3.4** installed & running (empty bridge OK). Docker already present.
- Dell#1 RAM = **30 GiB** (better than the 16GB assumed). Swap 8G.
- **Constraint:** Dell#1 has **2 USB ports + 1 built-in Ethernet** = max 3 Ethernet ports. → full multi-device topology will use the MikroTik as aggregation; minimal loop uses the 2 USB ports.
- **Interfaces (Dell#1):**
  - `enp0s31f6` — built-in Ethernet (spare / future uplink to Dell#2 or MikroTik)
  - `wlp0s20f3` — WiFi (management/internet; NEVER added to br0)
  - `enx9c69d331d874` — USB-Eth #1 → **PLC port**
  - `enx9c69d331aef0` — USB-Eth #2 → **HMI port**

### Checkpoint A2 — create OVS bridge br0 + add 2 ports
Status: **DONE (2026-07-06)**
- `br0` created, fail_mode=standalone, ports = enx9c69d331d874 (PLC) + enx9c69d331aef0 (HMI) + internal br0. Confirmed via `ovs-vsctl show`.

### Checkpoint A3 — SDN controller install
Status: **IN PROGRESS**
- **Issue flagged:** Ryu is EOL (last release 2022), breaks on Python 3.12 (Ubuntu 24.04). → controller will be **os-ken (maintained Ryu fork, same API)** or **Ryu-in-Docker**; deciding after `python3 --version` / `/etc/os-release` check. CARS code stays ~identical either way.
- Confirmed: **Ubuntu 24.04.4 LTS, Python 3.12.3** → stock Ryu ruled out.
- **Controller chosen: os-ken** (maintained Ryu fork) in a venv at `~/cars/venv`. Project dir `~/cars/` created for CARS code. Fallback = Ryu-in-Docker if pip fails.
- Command: `osken-manager os_ken.app.simple_switch_13`; attach via `ovs-vsctl set-controller br0 tcp:127.0.0.1:6653`.
- **DONE:** os-ken **2.8.1** installed in `~/cars/venv`, works on Python 3.12. CC-8 resolved → controller = os-ken.

### Checkpoint A3b — verify OVS↔controller OpenFlow channel (no PLC needed)
Status: **IN PROGRESS**
- T1: `osken-manager os_ken.app.simple_switch_13` (foreground controller).
- T2: `ovs-vsctl set-controller br0 tcp:127.0.0.1:6653` (DONE).
- **Snag:** os-ken (Ubuntu pkg) has no bundled `os_ken.app.simple_switch_13` example. eventlet "RLock not greened" = harmless warning.
- **Fix:** wrote our own minimal L2 learning-switch app → `~/cars/l2_switch.py` (copy saved at `06_Build/l2_switch.py`). This is the **CARS seed file**. Run: `osken-manager ~/cars/l2_switch.py`.
Result: **DONE ✓** — controller logged `>>> switch connected: dpid=171978328747760`; OVS shows Controller tcp:127.0.0.1:6653. **SDN control plane live end-to-end via our own os-ken app.**

MILESTONE: OVS ✓ · os-ken controller ✓ · OpenFlow channel ✓ · custom app (l2_switch.py) driving it ✓.

### Checkpoint A4/A5 — wire PLC+HMI through OVS + verify real traffic
Status: **IN PROGRESS (physical)**
- Target: PLC → enx9c69d331d874 (PLC port); HMI → enx9c69d331aef0 (HMI port); no direct PLC↔HMI path except via OVS.
- **Rig topology (from photo):** PLC (S7-1200) + HMI both plug into the **MikroTik hEX lite** (rig's switch). → for minimal loop, **bypass MikroTik**: move PLC→enx…d874, HMI→enx…aef0 (Dell OVS). MikroTik becomes zone switch later.
- PLCs currently **powered off**; IPs unknown → will read via `tcpdump -i br0 -n -e` (ARP) + confirm via TIA "Accessible devices".
- **RESULT ✓ (2026-07-06): real ICS traffic crossing OVS.** HMI↔PLC S7comm (port 102) seen on both USB ports = OVS forwarding between them.

**Discovered network facts (LOCKED):**
| Device | IP | MAC | Port (OVS) | Notes |
|--------|----|-----|-----------|-------|
| PLC (S7-1200) | 192.168.2.10 | e0:dc:a0:63:98:09 | enx9c69d331d874 | S7comm server :102; LLDP from …98:0a |
| HMI | 192.168.2.9 | e0:dc:a0:62:b7:4c | enx9c69d331aef0 | polls PLC :102 |
| Subnet | 192.168.2.0/24 | — | — | rig subnet (was behind MikroTik) |

Port labels CONFIRMED (LLDP on d874 = PLC). Pending: dump-flows (controller-installed flows) + HMI-screen visual.

**PHASE A essentially COMPLETE:** OVS ✓ · os-ken controller ✓ · custom app ✓ · real HMI↔PLC loop through the SDN switch ✓.

**PHASE A COMPLETE ✓ (2026-07-06)** — dump-flows confirms controller-installed learning flows carrying real S7comm (834/854 pkts). Our os-ken app is actively forwarding live HMI↔PLC traffic through OVS.

### Checkpoint A6 — first reactive action (block/restore HMI↔PLC)
Status: IN PROGRESS
- Manual OVS flow: `priority=100 ... dl_src=HMI dl_dst=PLC actions=drop` → HMI supervisory link cut (process unaffected = SAFE; the CARS criticality lesson). Restore via `del-flows`.
- **Result ✓:** drop flow added → HMI "Connection lost" + **"The value could not be written to the PLC"** (write blocked; drop n_packets climbing). del-flows → "Connection established" (auto re-learn). **Reactive block + safe restore proven on real ICS.**
- Key insight: blocking HMI→PLC prevents a WRITE to the PLC = the CARS security primitive. Next: make it selective/reactive (event-triggered, criticality-gated) instead of blunt/manual. (OVS port map: enx…aef0=port2, enx…d874=port1.)

### Next (Phase B): baseline latency/jitter (CC-4); program PLC in TIA (Modbus server + safe LED/relay I/O); then grow l2_switch.py → CARS reactive engine (event API + criticality + safety guard).

### SESSION 1 END (2026-07-06). Plan for next session:
- **Add PLC-B directly to OVS** via Dell#1's free **built-in Ethernet (enp0s31f6)** → `ovs-vsctl add-port br0 enp0s31f6`; cable to PLC-B. Gives 2 PLCs + HMI-A on OVS with existing 3 ports. (HMI-B optional via USB hub.)
- **GOTCHA (do NOT):** plug PLC+HMI into the MikroTik as a plain switch → intra-pair traffic switches locally, never reaches OVS (CARS blind). MikroTik only works here if configured as a **VLAN trunk** (each device own VLAN → OVS). Defer that to the zone-building phase; not needed for basic 2-PLC attach.
- Then: differentiated per-PLC CARS demo (PLC-A critical→redirect, PLC-B→block); baseline latency; TIA program.
- Resume with: "continue CARS".

### Safe shutdown (session 1) + restart recipe
Shutdown: Ctrl+C the osken-manager; power off PLC/HMI (keep their settings); unplug patch cables; unplug + label USB-Eth adapters (PLC=d874, HMI=aef0); power off Dell (OVS config persists on disk). Optional: return cables to MikroTik if rig is shared.
**Nothing volatile lost** — OVS br0/ports/controller persist; controller = 1 command; PLC/HMI/adapters keep own state.
**Restart:** (1) replug adapters+cables, power PLC/HMI; (2) `sudo ovs-vsctl show` (confirm br0 + 2 ports); (3) `cd ~/cars && source venv/bin/activate && osken-manager ~/cars/l2_switch.py` → wait `>>> switch connected`. Then continue Phase B (add PLC-B on enp0s31f6).
_Note: USB-Eth OVS ports may show "no such device" until adapters plugged in — harmless; they activate on plug-in._

## SESSION 2 (2026-07-07)
- Loop restored clean (br0 + controller + `>>> switch connected`).
- New device logged: MikroTik hAP-series (model TBC) → future OT VLAN-trunk aggregator (DECISION_LOG CC + inventory).

### Checkpoint B1 — CARS v0.1 engine (Event API → reactive action)
Status: IN PROGRESS. File: `~/cars/cars_engine.py` (copy in `06_Build/cars_engine.py`).
- Learning switch + os-ken WSGI REST on :8080: `GET /cars/status`, `POST /cars/block`, `POST /cars/unblock` {src,dst MAC}. Controller installs priority-100 drop / DELETE_STRICT.
- **This realises the project's core objective: external event → controller → routing change.**
- Test: curl block HMI(e0:dc:a0:62:b7:4c)→PLC(e0:dc:a0:63:98:09), watch HMI drop, curl unblock.
- Result: _pending — DEFERRED. User chose to build full 2-box topology BEFORE reactiveness. cars_engine.py ready (06_Build) for when we resume reactive.
- NOTE: cars_engine.py uses single `self.dp` → fix to per-dpid dict before multi-switch reactive.

### Checkpoint B0 — 2-OVS / 1-SDN testbed (native bridges, not GNS3)
Status: IN PROGRESS. Decision: **two native OVS bridges** (br0=box1, br1=box2), both → one os-ken controller = "2 OVS → 1 SDN". Simpler/lower-latency than GNS3-OVS; GNS3 reserved for virtual zones. Controller already multi-datapath (keyed by dpid) → no code change. Keep l2_switch.py running for topology work.
- **Design guard:** teaching boxes likely identical clones (same IPs PLC .10 / HMI .9) → keep br0 & br1 as SEPARATE L2 domains (do NOT link) to avoid IP conflict.
- **Port reality:** full box2 PLC+HMI visibility = 4 device ports; have 3. Today: box2 on built-in (enp0s31f6)→br1 (both PLCs up); full box2 HMI needs 4th port (USB hub or hAP VLAN-trunk).
- Steps: add-br br1; set-controller br1; add-port enp0s31f6; cable box2 → built-in; tcpdump discover.
- Result: _pending user output._
- Open Qs: USB hub? boxes identical (IPs)? hAP model?

### Checkpoint B2 — Multi-vendor distributed fabric (CC-12): Dell#3 OVS + Allen-Bradley box
Status: IN PROGRESS. **Pivot from cloned-Siemens box2 → Allen-Bradley box on Dell#3** (multi-vendor, EtherNet/IP; kills IP-clash; distributed 2-OVS/1-controller fabric = the reliable multi-switch design).
- Dell#3: Ubuntu + OVS 3.3.4 installed ✓. Will run its own br0 = AB box (AB-PLC on built-in, AB-HMI on spare 3rd USB-Eth), controller = **tcp:192.168.88.165:6653** (Dell#1 WiFi, out-of-band; OT data = 192.168.2.x, mgmt = 192.168.88.x).
- Controller (os-ken) binds 0.0.0.0:6653 → remote OVS can connect. l2_switch.py already multi-datapath (learning); cars_engine.py needs per-dpid fix before multi-switch reactive.
- Dell#3 reachability ✓ (ping 192.168.88.165 OK; WiFi ~72ms/high jitter — affects first-packet flow-setup only, steady-state forwarding local).
- Dell#3 interfaces: built-in `enp0s31f6` + 2× USB-Eth `enx9c69d3413f16` (→AB-PLC), `enx9c69d3283cf9` (→AB-HMI). (Ignore leftover docker br-cd8d…/docker0.)
- Dell#3 br0 → controller tcp:192.168.88.165:6653; DPID differs from Dell#1 (separate machine) → no collision.
- **CHANGE: box2 = 2nd Siemens S7-1200** (NOT Allen-Bradley — user chose simpler). → testbed is 2× identical Siemens; **multi-vendor (CC-12) deferred/optional** (can swap AB in later for evaluation). Lose multi-vendor strength, keep distributed 2-switch fabric.
- **Box2 up ✓ (Dell#3 OVS):** PLC-B=192.168.2.10 (MAC e0:dc:a0:46:ff:ce, port enx…3f16), HMI-B=192.168.2.9 (MAC e0:dc:a0:5c:60:44, port enx…3cf9). S7comm loop crossing Dell#3 OVS. is_connected:true. Same IPs as box1 but different MACs + separate switch/segment → OK (never bridge box1↔box2 without re-IP).
- **Dell#3 dpid=226526544729166** joined controller ✓.
- **ISSUE:** controller shows 4 datapaths (+1 flapping), expected 2. Extra dpids 171978329767702 / 171978328128761 (Dell#1 MAC range) = likely **stray OVS bridges on Dell#1** from earlier br1/experiment. FIX: `ovs-vsctl show` on Dell#1 → `del-br` anything != br0. Then 2 clean switches → swap to multi-switch cars_engine.py.
- **RESOLVED:** Dell#1 has ONLY br0; Dell#3 has ONLY br0 → exactly 2 switches. Extra "switch connected" dpids were **historical** (OVS changes dpid when ports added → br0 reconnected under new ids during setup) + Dell#3 WiFi blips. No stray bridges.
- **Stable dpids set:** Dell#1 br0 `other-config:datapath-id=…0001` (box1); Dell#3 br0 `…0002` (box2). CARS addresses switches by dpid 1/2.
- **Box MACs:** box1 PLC e0:dc:a0:63:98:09 / HMI e0:dc:a0:62:b7:4c (dpid1). box2 PLC e0:dc:a0:46:ff:ce / HMI e0:dc:a0:5c:60:44 (dpid2). Both S7comm, subnet 192.168.2.0/24 (separate segments).

### Checkpoint B3 — CARS v0.2 multi-switch engine
Status: IN PROGRESS. cars_engine.py upgraded: per-dpid datapaths, REST `POST /cars/block|unblock {dpid,src,dst}`, `GET /cars/status`→switches [1,2]. Copy in 06_Build.
- Run `osken-manager ~/cars/cars_engine.py` → expect 2 lines: dpid=1, dpid=2.
- Demo: curl block dpid=1 (box1 HMI→PLC) → box1 HMI drops; dpid=2 (box2) independently. **Event-driven reactive control across a 2-switch fabric.**
- **SNAG:** this os-ken build has **no `os_ken.app.wsgi`** (missing in both Ubuntu pkg and pip). Also `sudo` bypasses the venv → system os-ken. **FIX (v0.3):** REST via Python **stdlib `http.server`** in an `os_ken.lib.hub` green thread — core os-ken only, no WSGI dep. Run with plain `osken-manager ~/cars/cars_engine.py` (NO sudo). Copy in 06_Build/cars_engine.py.
- **RESULT ✓✓ MILESTONE (2026-07-07):** CARS engine live — `CARS Event API listening on :8080`, both switches connected (dpid=1 box1/Dell#1, dpid=2 box2/Dell#3). Event-driven reactive block demonstrated **independently per box**: BLOCK dpid=1 → box1 HMI "connection lost"; UNBLOCK → "established"; BLOCK dpid=2 → box2 HMI lost; UNBLOCK → established. Box1 block did NOT affect box2 (targeted).
- **= project core objective working:** external event (HTTP, IDS stand-in) → controller → criticality-targeted per-switch routing change → safe restore, on a distributed 2-PLC / 2-switch fabric, real Siemens hardware. (Screenshot controller log for results chapter.)

### Checkpoint B4 — dedicated controller + wired mgmt (CC-13) — DONE ✓ (2026-07-07)
- hAP ac lite = dumb wired **L2 mgmt switch**; 3 laptops static-IP (nmcli `cars-mgmt`, never-default) on **10.10.10.0/24** (Dell#2=.1, Dell#1=.2, Dell#3=.3) → all ping ✓.
- **Controller relocated to Dell#2 (10.10.10.1)**: os-ken + cars_engine.py; both switches repointed `set-controller tcp:10.10.10.1:6653` → dpid=1 & dpid=2 connected. Old Dell#1 controller retired. Dell#1/#3 now **pure OVS switches**.
- **3-plane clean SDN:** OT data 192.168.2.x · control 10.10.10.x (wired) · internet 192.168.88.x (WiFi). As-built diagram + doc updated (`06_Build/asbuilt_topology.png`, `AS_BUILT_TOPOLOGY.md`).
- **Gotcha logged:** hAP default DHCP (192.168.88.1) hands 192.168.88.x leases that hijack manual `ip addr add` IPs → fix = nmcli static (method manual, never-default).
- **INFRASTRUCTURE COMPLETE.**

### NEXT (CARS contribution proper — pure software):
- **v0.4 "trust brain":** device registry (critical loop vs untrusted/unseen) + safety guard → block untrusted, mirror/redirect critical (never hard-block a critical loop); the safety-constrained criticality-aware response = the thesis.
- **v0.5 IDS integration:** Suricata/Zeek alert → auto-call Event API (real attack → auto-response).
- **Then:** attack scenarios + evaluation (MTTM, zero defence-induced trips, false-block rate).

### Checkpoint A4/A5 — wire PLC+HMI, verify loop (NEXT)
Blocked on: PLC IP + HMI IP + rig status (pre-built HMI↔PLC?).

Parallel (Asus/TIA): obtain PLC IP + HMI IP; confirm if pre-built rig (HMI↔PLC already talk).

---
(A3 Ryu control, A4 PLC program + Modbus + safe I/O, A5 wire + verify loop, baseline latency to follow.)

---

## Checkpoint B5 — Event API hardened (eventlet-WSGI) + dispatch bug fixed (2026-07-07)

**Context:** After relocating the controller to Dell#2, the Event API stopped responding — `ss -tlnp` showed `LISTEN 0.0.0.0:8080` but every curl (even `127.0.0.1`) timed out. Root cause: Python stdlib `http.server.HTTPServer.serve_forever()` running in an os-ken `hub.spawn` green thread binds/listens but never gets scheduled to `accept()` under the eventlet loop (partial monkey-patch, "RLock(s) were not greened"). It had worked by luck on Dell#1.

**Fix 1 — server:** replaced stdlib `http.server` with the **eventlet-native WSGI server**:
`wsgi.server(eventlet.listen(('0.0.0.0', 8080)), self._app, log_output=False)` inside `_serve_api`, spawned via `hub.spawn`. Uses eventlet's own green listen socket, so it cooperates with the hub and does not block. `GET /cars/status` immediately returned `{"switches":[1,2],...}`.

**Fix 2 — dispatch bug:** unblock silently ran block. Cause: `"/cars/unblock".endswith("block")` is `True`. Original line `fn = self.block if path.endswith('block') else self.unblock` therefore routed every unblock to block. Fixed to `fn = self.unblock if path.endswith('unblock') else self.block` (check the longer suffix first).

**Verified:** `POST /cars/block` drops Box1 HMI↔PLC (HMI shows connection lost); `POST /cars/unblock` restores it (HMI reconnects); `GET /cars/status` reflects `blocks` set accurately. Engine is now **cars_engine.py v0.3.1**. Repo copy updated at `06_Build/cars_engine.py`.

**Restart note:** on Dell#2 run without sudo in the venv: `cd ~/cars && source venv/bin/activate && osken-manager ~/cars/cars_engine.py`.

---

## Checkpoint G1–G2 — GNS3 installed + virtual↔real seam PROVEN (2026-07-08)

Scale-up per **CC-16** (GNS3 periphery around the bare-metal core). Host decision **CC-16a → GNS3 on Dell#1** (native Ubuntu; 30 GB RAM, KVM acceleration OK; zero new hardware).

- **GNS3 2.2.59** (gui + server) installed native on Dell#1 (PPA `gns3/ppa`), local server, user added to ubridge/kvm/libvirt/docker/wireshark groups (reboot applied).
- **Seam `it0`:** new OVS **internal port on br0** (`ovs-vsctl add-port br0 it0 type=internal`, up, **no host IP** — pure L2 doorway for GNS3). Sibling of `ot0`.
- **Integration proven:** GNS3 **Cloud node bound to `it0`** + a **VPCS** test host (`192.168.2.50/24`). **VPCS pinged the REAL PLC `192.168.2.10` through `br0` — replies ~3.5–4.6 ms.** A virtual GNS3 node reached real ICS hardware across the CARS-controlled fabric. → the whole "GNS3 periphery on bare-metal core" architecture is validated.
- **Persistence:** `it0` folded into `ot0-ip.service` (now brings up both `ot0` IP and `it0` on boot).
- **CARS control of GNS3 traffic:** [block/unblock of VPCS→PLC via Event API — result to append].

**Guardrails held:** br0/OVS native (bare metal); GNS3 nodes are upstream endpoints off `it0`; timing path unaffected. **Next:** G3 = build light multi-zone topology (enterprise → dual firewalls → DMZ → attacker); G4 = IDS + attack scenario + MTTM measured on native br0.

### Cold-start verification (2026-07-08)
Full power-cycle (hAP → boxes → Dells) verified end-to-end against `COLD_START.md`: mgmt pings sub-ms; both OVS switches auto-restored + reconnected to controller; `ot0-ip.service` active (ot0 IP + it0 up); 3 containers auto-up; controller sees dpid 1 & 2; Event API `{"switches":[1,2]}`; GNS3 VPCS→real PLC ping ~3–4 ms. Deterministic cold boot confirmed — only manual steps by design = start controller (Dell#2) + launch GNS3 (Dell#1). VPCS IP persistence: use `save` in VPCS console (writes startup.vpc).

### G2 SEALED — CARS controls GNS3 traffic (2026-07-08)
Event-API block of VPCS `00:50:79:66:68:00` → PLC `e0:dc:a0:63:98:09` (dpid=1): VPCS `ping 192.168.2.10` → 4× timeout. Unblock → ping recovered (~3–10 ms). Controller logged BLOCK then UNBLOCK. **Proven: a virtual GNS3 host's traffic to real ICS hardware is fully CARS-mediated (blockable/restorable) at the OT boundary** — the capability the kill-chain attack scenarios depend on. Note: VPCS IP persistence via `save` (startup.vpc). NEXT: G3 zones.

### G3a — routed kill-chain first hop (VyOS OT-FW) verified (2026-07-08)
GNS3: VyOS rolling `vyos-2026.06.30` installed to disk as **OT-FW**. Topology: VPCS (IT `10.0.40.66`) → eth0[OT-FW]eth1(`192.168.2.1`) → Cloud(`it0`) → br0 → **real PLC**. OT-FW: eth0=`10.0.40.1/24`, eth1=`192.168.2.1/24`, source-NAT masquerade (attacker→OT) so the real PLC is untouched. VPCS `ping 192.168.2.10` **through the firewall**: replies ~4–5 ms, **TTL=29** (was 30 direct → confirms the routed L3 hop). Proven: an IT-subnet host reaches real ICS through a routed firewall. Reinforces the L3/conduit point: on br0 all GNS3 traffic now bears the **OT-FW MAC** → per-attacker response needs v0.4 IP matching. Next G3b: DMZ + Enterprise-FW.

### G3b — full two-firewall IT→DMZ→OT kill chain verified (2026-07-08)
Added **Enterprise-FW** (GNS3 Duplicate of the OT-FW VyOS node). Chain:
`VPCS (IT 10.0.40.66, gw .1) → Ent-FW → DMZ 172.16.35.0/24 → OT-FW → Cloud(it0) → br0 → real PLC`.
- **Ent-FW:** eth0(=eth4) `10.0.40.1/24` (IT), eth1(=eth5) `172.16.35.1/24` (DMZ); static route `192.168.2.0/24 → 172.16.35.2`; no NAT.
- **OT-FW:** eth0 `172.16.35.2/24` (DMZ), eth1 `192.168.2.1/24` (OT) + source-NAT masquerade; static route `10.0.40.0/24 → 172.16.35.1`.
- **Result:** VPCS `ping 192.168.2.10` replies, **TTL=28** (30 direct → 29 one FW → 28 two FWs) → both firewalls traversed to real hardware. Real PLC untouched (OT-FW masquerade).
- **Clone gotcha (logged):** GNS3 **Duplicate** assigns new MACs → VyOS persistent-net reserved eth0–3 for the old MACs, so the clone's real NICs came up as **eth4–eth7**. Fixed by configuring the actual interfaces (eth4=IT, eth5=DMZ) and deleting the phantom eth0/eth1 config. For tidy names later, rebuild clones from a base image with persistent-net rules cleared.
- **Next:** G3c = DMZ host + deny-by-default firewall rules; G4 = real attacker + IDS (Suricata on br0) + MTTM.

### CLEAN REBUILD — 3-OVS gateway fabric + kill chain on the spine (2026-07-10)
Rebuilt the OT fabric from scratch (P0–P5a), clean bridge names + explicit dpids; kept the validated software (os-ken, GNS3 VyOS firewalls, Docker).
- Wiped old `br0` on Dell#1/#3. Rebuilt: **ovs1 (dpid1, Box1: PLC1+HMI1)** on Dell#1, **ovs2 (dpid2, Box2: PLC2+HMI2)** on Dell#3, **ovsgw (dpid3, gateway)** on Dell#1. `ovs1↔ovsgw` via OVS patch. Controller (Dell#2) manages dpid 1/2/3.
- **CC-19 applied:** no re-IP — cells distinguished by **MAC + dpid** (Box 2 TIA project unavailable; identical IPs are fine). Boxes kept as-is.
- **Kill chain re-attached to the gateway:** GNS3 seam `it0` moved to `ovsgw`; VPCS attacker (10.0.40.66) → Ent-FW → OT-FW → it0 → ovsgw → patch → ovs1 → **real PLC 1**, TTL=28 verified.
- **Gateway enforcement VERIFIED:** CARS block on **dpid=3** (OT-FW MAC `0c:5d:b4:41:00:01` → PLC1) severed the attacker's ping (seq 139–150 timeouts); unblock restored it (seq 198+). North-south containment at the OT boundary working. (Coarse NAT'd-MAC block; per-IP granularity = v0.4.)
- Cell 1 critical-loop block/restore (dpid=1, HMI1→PLC1) also re-verified on the new fabric.
- **NEXT:** P5b supervisory (SCADA/Historian → ovsgw, `192.168.10.x`) · P6 Snort → CARS · Cell 2 attacker path via DNAT later.

### P6 — AUTONOMOUS reactive IDS → SDN loop CLOSED (2026-07-10)
Full detect → decide → enforce loop, **no human in the loop**:
- **Mirror:** OVS `m0` (select_all) on `ovsgw` → `snort0` (verified: attacker ICMP copied via tcpdump).
- **Snort 2.9.20** on `snort0`, minimal config (`/etc/snort/cars.conf` + `cars.rules`), rule sid 1000001 "CARS-ATTACK ICMP to PLC1" (`icmp 192.168.2.1 -> 192.168.2.10`). Alerts fire on the attacker.
- **Bridge** `~/snort_bridge.py` (Dell#1, stdlib): tails `/var/log/snort/alert`; on "CARS-ATTACK" POSTs to the CARS Event API → block **dpid=3** (OT-FW MAC `0c:5d:b4:41:00:01` → PLC1). 30 s cooldown.
- **VERIFIED:** bridge printed `DETECT -> CARS BLOCK {"ok":true}`; controller logged `CARS: BLOCK dpid=3`; attacker severed at the gateway **without any manual curl**. Reactive IDS-driven SDN orchestration demonstrated end-to-end on real hardware.
- **Expected artifact:** the mirror copies ingress packets even when the block drops them → Snort keeps seeing the (now-dropped) attempts → bridge re-affirms the block each cooldown. Harmless; block-lifecycle (block once, auto-restore when attack subsides) = a v0.4/trust-brain refinement.

## ★ TESTBED CORE COMPLETE (clean rebuild, 2026-07-10)
3-OVS gateway fabric (ovs1/ovs2/ovsgw) + GNS3 IT→OT kill chain + supervisory foot + **autonomous Snort→CARS reactive loop**, all on a from-scratch clean build, reproducible. NEXT: **v0.4** conduit-criticality trust brain (the contribution) + evaluation (MTTM, safety invariant, both-loops).

### ★ v0.4 TRUST BRAIN — core demonstrated (2026-07-10)
`cars_engine.py` v0.4 deployed on Dell#2: **device registry** (IP→role) + **conduit-criticality `classify()`** + **SAFETY GUARD** + `/cars/respond` + **IP-conduit block** (`block_conduit`, OpenFlow 5-tuple) + **audit log** (`~/cars/cars_audit.log`). Controller manages dpid 1/2/3.
Brain decisions VERIFIED (`curl /cars/respond`, logged on the controller):
- `unknown` 192.168.2.66 → `plc` .10  →  **FORBIDDEN → BLOCK** ✓
- `historian` 192.168.2.30 → `plc` .10  →  **OPERATIONAL → ALLOW** ✓  (same dst PLC, opposite decision by *source role* = the intelligence)
- `hmi` 192.168.2.9 → `plc` .10 (the critical loop) → **CRITICAL → REFUSED (safety invariant)** ✓✓ — CARS is structurally incapable of hard-blocking the control loop = the "provably safe" claim, demonstrated.
NEXT: Stage 2 — rewire the Snort bridge to feed `/cars/respond` → autonomous, criticality-aware, provably-safe protection.

### ★★ v0.4 AUTONOMOUS — full contribution demonstrated (2026-07-10)
Snort bridge v2 (`~/snort_bridge.py`) now REPORTS flows to `/cars/respond`; the trust brain decides. Snort rule broadened (sid 1000001 rev3: `any -> 192.168.2.10`). End-to-end autonomous, criticality-aware, provably-safe protection VERIFIED:
- **Insider** att0 `192.168.2.66` → PLC1: Snort → bridge → brain **FORBIDDEN → BLOCK** → insider ping cut off, hands-free. ✓
- **Supervisory** sup0 `192.168.2.30` → PLC1: Snort → bridge → brain **OPERATIONAL → ALLOW** → ping uninterrupted. ✓
- Critical loop hmi→plc: **CRITICAL → REFUSED** (verified earlier).
Same IDS, same bridge — **opposite outcomes decided by the source's role, no human.** This is the contribution: generalized, intelligent, conduit-criticality-aware, provably-safe reactive SDN defence.
NEXT (research layer): evaluation — MTTM latency; formalize the safety invariant; block-lifecycle auto-restore; Cell 2 via DNAT; then the write-up.

### ★ v0.5 / v0.5.1 — live discovery + NOC console (2026-07-11)
Engine v0.5 (backup: `cars_engine_v04_stable.bak`, `cars_engine_v05.bak`) ADDS controller-side sensing, brain UNCHANGED:
- switch up/down (`EventOFPStateChange`/DEAD), host discovery (ARP/IPv4 snoop), port up/down (`OFPPortStatus` + `OFPPortDescStatsReply` snapshot), LLDP fabric links (`--observe-links`).
- New API: `/cars/hosts`, `/cars/ports`, `/cars/links`, `/cars/audit`.
v0.5.1 hardening (from real hardware testing):
- host table keyed by **dpid+MAC** (clone-safe) — both cells' identical-IP PLCs/HMIs now resolve distinctly.
- **port-desc snapshot on connect** (OFPPortStatus is change-only).
- **ignore `0.0.0.0`/broadcast** in IP-learning — PLC boot ARP probes (RFC 5227) were overwriting real IPs. Fixed.
VERIFIED live: LLDP found `ovs1<->ovsgw` and correctly showed **ovs2 isolated** (P4 deferred); power-cycling boxes flipped port/link state up/down on the map in real time.
Flagged by discovery: **two MACs answering for 192.168.2.30** (sup0 internal port + SCADA/Historian container) — confirm intended (possible ARP flap).
`cars_dashboard.py` v4 = discovery-driven force-directed NOC (Dell#1 `python3 ~/cars_dashboard.py`, http://localhost:8090): draggable nodes, hosts/links built from `/cars/hosts|links|ports`, live port up/down, decisions feed, active-enforcement, node inspector.
NEXT (morning): confirm `0.0.0.0` fix cleared PLC IPs; then P4 transit / evaluation (MTTM) / label the two-.30 interfaces.

### ★ HARDENING — HP1+HP2 done: data-plane source-guard (2026-07-12)
`cars_engine.py` v0.6 = brain + discovery + **two-table source-guard** (Table 0 guard / Table 1 switch). Fixed multi-homed ARP flux first (CC-21), verified bindings vs live ofports, armed the guard (CC-22). Spoof-tested on real hardware: forged `.30` (historian) and `.9` (HMI/CRITICAL-shield) from att0 **dropped at ingress**; legit sup0 + PLC↔HMI loops untouched; discovery clean under attack. Anti-spoofing = true prevention, not detection. NEXT: HP3 (Cell 2 enforcement) · HP4 (fail_mode) · HP5 (dashboard) · HP6 (verify + ARP-guard follow-up + refresh COLD_START).

### ★ HARDENING — ARP-guard done (2026-07-12)
Extended the two-table source-guard with dynamic ARP inspection (CC-23). Forged gratuitous ARP (att0 claiming .30) dropped at ingress; legit sup0 ARP + loops untouched. Anti-spoofing complete both layers. Backups: `cars_engine_v06.bak` (v0.6 IP-guard), `cars_engine_v051.bak`. NEXT in order: HP4 (fail_mode) -> HP3 (Cell 2) -> HP5 (dashboard) -> HP6 (verify + refresh COLD_START).

### ★ HARDENING — HP4 done: fail-secure (2026-07-12)
Found `standalone` fails OPEN (controller down → flows flushed → guard/blocks gone → spoof passes). Switched all bridges to `fail_mode: secure`. Re-tested with controller DEAD: 12 guard flows persisted, loop survived, forged `.30` still dropped. Enforcement holds under control-plane attack (CC-24). Persists in OVSDB. NEXT: HP3 (Cell 2 enforcement) -> HP5 (dashboard) -> HP6 (verify + refresh COLD_START).

### ★ HARDENING — HP3 done + HP4 completed (2026-07-12)
HP3: brain enforces block on EVERY switch (block-everywhere) — verified the drop lands on ovs2 (Cell 2), not just the gateway. HP4 finished: confirmed the ARP-during-outage break empirically, added a permanent broadcast-flood flow (behind the ARP-guard) — loop now survives a full controller outage + ARP flush (3/3). CC-25. Residual: Cell 2 detection still needs P4/2nd sensor. NEXT: HP5 (dashboard hardening) -> HP6 (verify + refresh COLD_START).

### ★ HARDENING — HP5 done: dashboard + discovery-after-restart (2026-07-12)
Root-caused blank discovery after restart to persistent-flow + no clean-slate; added OFPFC_DELETE-all on (re)connect → all active hosts re-discover in seconds (PLC1/HMI1/PLC2/HMI2 verified). Dashboard: infra filter, block dedupe, guard/arp-guard badges, controller-offline state, port-undefined fix (CC-26). NEXT: HP6 — verification pass + persistence (cars-seams service) + refresh COLD_START to the current hardened 3-OVS build.

### ★★★ HARDENING PASS COMPLETE — HP1–HP6 (2026-07-12)
Six items closed + independent audit run:
- **HP1/HP2** data-plane source-guard (IP+ARP, two-table) — spoofing dead at L3+L2; CRITICAL shield can't be stolen.
- **HP3** block-everywhere → Cell-2 enforcement reaches ovs2.
- **HP4** fail-secure + broadcast-flood → enforcement AND loops survive a controller outage of any length.
- **HP5** clean-slate-on-connect → discovery survives restart; dashboard infra-filter/dedupe/guard-badges/offline-state.
- **HP6** `cars-seams` service (seam-IP persistence), refreshed COLD_START, independent code audit (CC-27) — findings fixed (H-2/M-4/H-4/L-1/L-2) or scoped (C-1/H-1 = P4 prerequisite; M-2/H-3/M-1/M-3 = documented threats-to-validity).
**Acceptance run PASSED:** both guards armed, discovery clean, legit untouched, IP+ARP spoof dropped, Cell-2 block on ovs2, audit shows all-switches. Prime fixes CC-21..CC-27. Backups: `cars_engine_v04_stable/v051/v06.bak`.
**Remaining project work (not hardening):** P4 transit (harden P150 first) · Cell-2 IDS detection · evaluation (MTTM) · write-up.

### ★ DASHBOARD v5 (live-sync) + GNS3 back up (2026-07-13)
Engine v0.7 telemetry: audit lines now dated; `/cars/links` carries LLDP port bindings; `/cars/guard` exposes live table-0 source-guard drop counters (flow-stats poll).
Dashboard v5 (`cars_dashboard.py`): threaded server (no BrokenPipe), discovered PORT labels on every link, live link-health (port down -> red/broken, verified via `mod-port down`), link-hover tooltips showing the full binding, source-guard drops panel, dated feed, "last seen (ctrl)" relabel, controller-offline state, 1.2s sync.
GNS3 `cars-killchain` back up: VPCS attacker -> PLC1 traverses Ent-FW/DMZ/OT-FW(SNAT .1) -> it0 -> ovsgw; OT-FW `192.168.2.1` (0c:5d:b4:41:00:01) discovered on dpid3 port2. North re-lit.
NOTE: external attacker currently REACHES PLC1 but isn't blocked — Snort + bridge not running (needed for external reactive demo + MTTM).

### ★ AG1 + AG2 done — reactive loop live + MTTM evaluated (2026-07-13)
AG1: Snort + snort_bridge.py up; external kill-chain closed reactively (VPCS -> PLC1 blocked after 1 packet, .1 gateway->plc FORBIDDEN). AG2: MTTM measured on the insider path (20 trials, single-clock). **CARS decide+enforce = 0.613 ms (sub-ms); end-to-end MTTM = 1.132 s mean (min 139 ms) — ~99.95% Snort detection, NOT CARS.** Bridge poll tightened (tail -s 0.05); residual gate proven upstream in Snort. Full write-up: `07_Evaluation/MTTM_EVALUATION.md`. NEXT (agenda): AG3 P4 transit (P150 fix first) · AG4 Cell-2 detection · external-path MTTM · write-up.
