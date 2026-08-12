# AS-BUILT Topology — CARS testbed (2026-07-08, dedicated controller + GNS3 periphery)

Current physical + logical topology. Diagram: `asbuilt_topology.png`.
(Serial numbers NOT recorded — see bottom for how to capture.)

## Summary
Two **identical Siemens S7-1200 + SIMATIC HMI** teaching boxes, each wired to its own
**Open vSwitch** on a separate laptop (Dell #1, Dell #3 = **pure switches**). A **dedicated
CARS controller** (os-ken + `cars_engine.py`) runs on **Dell #2**. All three laptops link
via a **MikroTik hAP ac lite used as a dumb wired L2 management switch**. Teaching boxes'
own MikroTiks are bypassed. Textbook SDN: switches + one out-of-band controller.

## Three planes
- **OT data — 192.168.2.0/24:** PLC↔HMI (S7comm :102), on the OVS switches (USB-Eth ports). Box1 & Box2 are **two separate L2 segments** reusing the same clone IPs — not interconnected.
- **SDN control — 10.10.10.0/24 (WIRED via hAP):** OVS↔controller OpenFlow. Dell#2=.1 (controller), Dell#1=.2, Dell#3=.3. Static IPs (nmcli, DHCP-proof). Sub-ms latency.
- **Internet/lab — 192.168.88.0/24 (WiFi):** package installs only; never in the OT or control path.

## Hosts / roles
| Host | Role | Mgmt IP (wired) | Details |
|------|------|-----------------|---------|
| **Dell #2** | **CARS controller** (os-ken `~/cars/cars_engine.py`) | **10.10.10.1** | OpenFlow :6653, Event API :8080. Manages dpid 1 & 2. → hAP LAN4 |
| **Dell #1** | **OVS switch (Box 1)** + **OT supervisory host** + **GNS3 host** | 10.10.10.2 | OVS br0 **dpid=1**; controller=`tcp:10.10.10.1:6653`. → hAP LAN2. Runs SCADA+Historian via internal port `ot0`; hosts the GNS3 periphery via internal seam `it0` (see below). 30 GB RAM, KVM |
| **Dell #3** | **Pure OVS switch** (Box 2) | 10.10.10.3 | OVS br0 **dpid=2**; controller=`tcp:10.10.10.1:6653`. → hAP LAN3 |
| **Asus** | TIA Portal / engineering | — | — |
| MacBook | excluded | — | — |

## Devices, addresses, IDs (data plane)
| Item | IP | MAC | Wired via | Switch |
|------|----|-----|-----------|--------|
| Box1 PLC (S7-1200) | 192.168.2.10 | e0:dc:a0:63:98:09 | USB-Eth `enx9c69d331d874` → Dell#1 | dpid=1 |
| Box1 HMI | 192.168.2.9 | e0:dc:a0:62:b7:4c | USB-Eth `enx9c69d331aef0` → Dell#1 | dpid=1 |
| Box2 PLC (S7-1200) | 192.168.2.10 *(clone)* | e0:dc:a0:46:ff:ce | USB-Eth `enx9c69d3413f16` → Dell#3 | dpid=2 |
| Box2 HMI | 192.168.2.9 *(clone)* | e0:dc:a0:5c:60:44 | USB-Eth `enx9c69d3283cf9` → Dell#3 | dpid=2 |

## Control / CARS
- Controller: **os-ken + `cars_engine.py`** (v0.3.1, multi-switch, **eventlet-WSGI** Event API) on **Dell #2**.
- Event API (`http://10.10.10.1:8080`): `GET /cars/status`; `POST /cars/block|unblock {dpid,src,dst}`.
- Verified: event-driven per-box block+restore, targeted (block dpid=1 doesn't affect dpid=2). **Re-verified 2026-07-07** after moving off stdlib `http.server` (hung under eventlet) to eventlet-native WSGI + fixing the `unblock`→`block` endswith dispatch bug.
- **Resilience note:** single controller (Dell#2) = single point of failure → hook for the dissertation's resilient-control-plane discussion.

## OT supervisory zone (added 2026-07-07 — CC-14)
L2/L3 supervisory assets, on the OT plane **through OVS** so CARS sees/can block them. Hosted on **Dell#1** (the Box1 switch) via an OVS internal port — **not** on the CARS controller (Dell#2 stays a pure enforcer).
| Service | Role | Endpoint | Notes |
|---------|------|----------|-------|
| OVS internal port `ot0` | Dell#1 OT-plane foot | 192.168.2.30/24 | `ovs-vsctl add-port br0 ot0 type=internal`; reaches PLC .10 through OVS. Reversible: `del-port br0 ot0` |
| InfluxDB 2.7 | Historian store (L3) | `:8086` | org `cars`, bucket `plc`, token `cars-token-change-me` |
| Grafana 11.1 | Historian dashboards (L3) | `:3000` | admin/cars-admin-2026 |
| FUXA | SCADA/HMI (L2) | `:1881` | open-source web SCADA; built-in Siemens S7 + Modbus TCP drivers |
| Asus / TIA Portal | Engineering workstation (EWS) | — | OT-plane link still to wire |

Stack under `~/ot-stack/docker-compose.yml` (Influx+Grafana) + standalone `fuxa` container (Docker 29.4.0). All additive/reversible.
**Gated:** live PLC tags need **PUT/GET** enabled on the Box1 PLC (TIA Portal) or an `MB_SERVER` block — a brief reversible PLC stop/download. Until then the stack stands but reads no values.

## GNS3 virtual periphery (added 2026-07-08 — CC-16)
Appliance-grade IT→OT kill-chain, virtual, on Dell#1 — **guardrail: periphery only; the CARS core stays bare metal**.
| Item | Detail |
|------|--------|
| GNS3 | 2.2.59 (gui+server), native on Dell#1 (Ubuntu, 30 GB RAM, KVM). Local server. |
| Seam `it0` | OVS **internal port on br0**, no host IP. GNS3 **Cloud node binds to `it0`** → virtual traffic enters br0 and is CARS-mediated. |
| VPCS (test host) | 192.168.2.50. **Verified G2:** pinged real PLC .10 (~4 ms) **and** CARS block/unblock of VPCS→PLC works → CARS controls GNS3 traffic. |
| Kill chain BUILT (G3a/b) | VyOS **OT-FW** + **Ent-FW** routed chain: IT `10.0.40.0/24` → DMZ `172.16.35.0/24` → OT-FW (SNAT) → `it0` → br0 → real PLC. Verified end-to-end (TTL 30→29→28). Full addressing/IPs/MACs diagram: `it_ot_network_topology.png`. |
| Next (G3c/G4) | DMZ host + deny-by-default FW rules; then real attacker (Kali) + IDS (Suricata on br0) → Event API + MTTM measurement. |

Measurement-safe: br0/OVS stays native (bare metal); GNS3 nodes are upstream endpoints. Both seams (`ot0`, `it0`) auto-restore on boot via **`ot0-ip.service`**.

## Restart recipe (current)
Full cold-start SOP + verification checklist: **`06_Build/COLD_START.md`**. Quick version:
1. **Power order:** hAP → teaching boxes → the three Dells.
2. **Auto-restores:** OVS bridges/ports, `ot0` IP + `it0` up (systemd `ot0-ip.service`), Docker containers (`unless-stopped`), nmcli mgmt static IPs.
3. **Manual:** start controller on Dell#2 (`cd ~/cars && source venv/bin/activate && osken-manager ~/cars/cars_engine.py` → dpid 1,2); launch GNS3 on Dell#1 (`gns3`).
4. If a switch lost its controller line: `sudo ovs-vsctl set-controller br0 tcp:10.10.10.1:6653`.

## NOT in the topology yet (planned)
- **IDS (Suricata/Zeek) + attacker (Kali)** → will live in **GNS3** (G3/G4), off `it0`, kept OFF the controller node.
- **Purdue zones / dual firewalls / DMZ** → the G3 GNS3 build.
- **Live PLC tags** in Historian/SCADA → gated on PUT/GET (or `MB_SERVER`) on the Box1 PLC.
- **EWS (Dell #4)** OT-plane connection → deferred (needs a spare Dell #1 port / USB-C dongle).
- **Factory I/O** → dropped (CC-7). **Box 2** currently idle spare (evaluation-phase multi-box option).

## Serial numbers — how to capture (not yet recorded)
- **Laptops (Dell service tag):** `sudo dmidecode -s system-serial-number` on each Dell.
- **S7-1200 PLC:** device label / TIA Portal → Device view → Properties.
- **SIMATIC HMI:** back-panel label.
- **USB-Eth / MikroTik:** casing labels (MikroTik also in WinBox → System → RouterBOARD).
