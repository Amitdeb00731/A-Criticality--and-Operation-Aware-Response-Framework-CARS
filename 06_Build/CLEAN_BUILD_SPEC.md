# CLEAN BUILD SPEC — CARS Testbed (definitive from-scratch design)
_2026-07-09 · 4-OVS hierarchy · clean role distribution · clean subnets · build fresh (reset as needed)._

## Inventory
- TB1: **PLC1 + HMI1 + hEx switch** · TB2: **PLC2 + HMI2 + hEx switch**
- 3× **Dell** (each 1 Eth + 2 USB) · 1× **Asus** (Windows, 2 USB) · 1× **hAP** (3 LAN)
- Many Ethernet cables + USB→Eth converters.

## KEEP (validated software — re-attaches; there is no Ryu to remove)
Controller = **os-ken** (the maintained Ryu fork; same API — cite as "Ryu-based / os-ken"). `cars_engine.py`, the GNS3 VyOS firewalls, and the Docker images are all portable. "From scratch" = clean OVS fabric + IP plan; the software mounts onto it.

## Role distribution (clean — one role per machine)
| Machine | Role | Runs |
|---------|------|------|
| **Dell #1** | **OT DATA-PLANE FABRIC + real boxes** | **All 4 OVS bridges** (OVS1 Cell1 · OVS2 Cell2 · OVS3 supervisory-agg · OVS4 OT-edge), joined by OVS **patch ports**. Real PLC1/HMI1/PLC2/HMI2 attach to OVS1/OVS2. |
| **Dell #2** | **SDN CONTROLLER — PURE** | os-ken; manages all 4 dpids via OpenFlow. Nothing else (isolated from the attacker). |
| **Dell #3** | **VIRTUAL PERIPHERY + services** | **GNS3** (IT · DMZ · IT-FW · OT-FW · attacker) + **Docker** (SCADA · Historian · Snort). Attaches to the fabric via the VLAN-30 transit. |
| **Asus** | **Engineering (EWS)** | TIA Portal — programs PLC1 & PLC2. |
| **hAP (3 LAN)** | **control plane** | dumb L2: untagged **VLAN1 = control** (Dell1/2/3) + tagged **VLAN30 = OT-transit** (Dell1↔Dell3). No RouterOS config. |
| **hEx ×2** | box access switches **or** spare | see "Dell #1 ports" |

Clean separation: **real OT → Dell #1 · control → Dell #2 · virtual/attacker → Dell #3 · engineering → Asus.**

## Clean subnets (per tier)
| Tier | Subnet | Hosts |
|------|--------|-------|
| IT / Enterprise (L4/5) | `10.0.40.0/24` | attacker .66 · corporate .20 |
| Industrial DMZ (L3.5) | `172.16.35.0/24` | jump/hist-replica .10 |
| OT supervisory (L2/L3) | `192.168.10.0/24` | SCADA .20 · Historian .30 · EWS .40 |
| OT **Cell 1** (Box 1) | `192.168.1.0/24` | PLC1 .10 · HMI1 .11 |
| OT **Cell 2** (Box 2) | `192.168.2.0/24` | PLC2 .10 · HMI2 .11 |
| SDN control (out-of-band) | `10.10.10.0/24` | controller(Dell#2) .1 · Dell#1 .2 · Dell#3 .3 |
| OT-transit | **VLAN 30** | L2 fabric extension Dell#1 ↔ Dell#3 |

## The 4-OVS hierarchy (all on Dell #1, patch-connected)
```
        OT-FW (GNS3, Dell#3) ── transit ──> OVS4 (edge, dpid=4)
                                              │  patch
   SCADA/Historian/EWS (Dell#3) ─ transit ─> OVS3 (supervisory-agg, dpid=3)
                                              │  patch
                                     ┌────────┴────────┐
                                 OVS1 (Cell1, dpid=1)  OVS2 (Cell2, dpid=2)
                                   │  │                  │  │
                                 PLC1 HMI1             PLC2 HMI2   (REAL)
```
- **North-south** (IT→OT attack) via the **OT-FW**; **intra-OT** (supervisory↔cells) routed **locally on Dell #1** (keeps real traffic off the virtual hairpin).
- One os-ken controller manages **dpid 1/2/3/4**. CARS enforces per-conduit (CC-15): FORBIDDEN attacker→PLC at the edge, OPERATIONAL supervisory→PLC, SENSITIVE EWS→PLC, and never hard-blocks the critical PLC↔HMI loops (mirror-only).

## Dell #1 ports (the one real decision)
Dell #1 must attach **4 real devices** (PLC1, HMI1, PLC2, HMI2) + 1 uplink (Eth → hAP, carrying control VLAN1 + transit VLAN30). Two clean ways:
- **(A) Powered USB hub** → 4 USB-Eth, one dedicated OVS port per device. Simplest, native CARS visibility, no VLAN gymnastics. Small purchase. **[recommended]**
- **(B) The 2 hEx switches** → each box's PLC+HMI on its hEx, one trunk per box to Dell #1 (2 USB), **VLAN-hairpin** so PLC↔HMI still crosses OVS. No purchase, uses your hardware, but more config.

## INTERIM MODE (no hub yet — 2026-07-10)
Until a powered USB-C hub arrives, run the **3-OVS** layout (no hub needed): each box keeps its **own** Dell (2 USB-Eth per box = native loop visibility).
- **Dell #1:** OVS1 (Box 1) + **OVS-GW (dpid=3, gateway/supervisory)** + GNS3 (IT/DMZ/FWs/attacker) + Docker (SCADA/Historian/Snort). Eth → hAP (VLAN1 control + VLAN30 transit).
- **Dell #3:** OVS2 (Box 2). Eth → hAP.
- **Dell #2:** os-ken controller (pure). **Asus:** EWS. **hAP:** control + transit.
- 3 OVS: OVS1 + OVS2 → OVS-GW → OT-FW. Supervisory binds to OVS-GW. This **extends the current build** (add OVS-GW bridge + re-IP Box2 + transit), no wipe.
- **Migration when hub arrives:** add OVS4 (edge) + move both boxes onto Dell #1 (4 ports via hub) → Dell #3 becomes the dedicated virtual-services host. Easy, additive.

## Build order (from scratch — reset freely)
- **P0 Reset:** clear old OVS bridges (`ovs-vsctl del-br`), old GNS3 project, stale IPs. Keep os-ken venv + `cars_engine.py` + Docker images.
- **P1 Base:** Ubuntu + OVS + Docker where needed; os-ken venv on Dell#2; hAP dumb; static control IPs (nmcli, 10.10.10.x).
- **P2 Real OT:** attach boxes to Dell#1 (hub or hEx); create **OVS1, OVS2**; **re-IP** PLC/HMI to the cell subnets; verify each PLC↔HMI loop through OVS.
- **P3 SDN fabric:** create **OVS3, OVS4**; patch OVS1/2→OVS3→OVS4; point all at controller `10.10.10.1`; verify dpid 1–4.
- **P4 Transit:** VLAN30 Dell#1↔Dell#3 (Linux VLAN over the dumb hAP).
- **P5 Virtual periphery:** GNS3 on Dell#3 (IT/DMZ/FWs/attacker) → OT-FW to OVS4 via transit; supervisory (SCADA/Historian) on Dell#3 → OVS3.
- **P6 IDS:** Snort on Dell#3, mirror from the fabric → alert to CARS Event API.
- **P7 EWS:** Asus/TIA programs both PLCs.
- **P8 Verify:** attacker → both cells; reactive block/restore on each; MTTM.
