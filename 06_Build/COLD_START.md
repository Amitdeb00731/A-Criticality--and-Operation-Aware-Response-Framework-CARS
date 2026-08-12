# COLD START — CARS Testbed Bring-Up & Verification (hardened build)
_Current architecture: 3-OVS gateway fabric + conduit-criticality brain + data-plane source-guard + fail-secure. Last updated 2026-07-12 (supersedes the 2026-07-08 br0/2-dpid version)._

Resume phrase: **"continue CARS"** (reloads START_HERE + DECISION_LOG). This file = the physical bring-up + hardened-state verification.

---

## 0. Machine roles & identities
| Machine | Role | Key facts |
|---------|------|-----------|
| **Dell #1** | OT data plane + gateway + services | `ovs1` (dpid 1, Cell 1), `ovsgw` (dpid 3, gateway), seams `sup0/it0/snort0/att0`, GNS3, Docker, Snort. Control `10.10.10.2`. |
| **Dell #2** | SDN controller (pure) | `osken-manager` · CARS engine. Control `10.10.10.1` (OpenFlow :6653, Event API :8080). |
| **Dell #3** | OT Cell 2 | `ovs2` (dpid 2, Cell 2). Control `10.10.10.3`. |
| **hAP** | control plane (dumb L2) | VLAN 1 untagged = control. Boots to saved config. |

**Ports (ofport → device):** ovs1: 1=PLC1(`e0:dc:a0:63:98:09`), 2=HMI1(`e0:dc:a0:62:b7:4c`), 3=patch→gw. ovsgw: 1=patch→ovs1, 2=it0, 3=sup0(`de:5a:28:ae:96:03`,`.30`), 4=snort0, 5=att0(`b6:27:88:18:de:2c`,`.66`). ovs2: 1=PLC2(`e0:dc:a0:46:ff:ce`), 2=HMI2(`e0:dc:a0:5c:60:44`).
**Subnets:** OT data `192.168.2.0/24` (PLC `.10`, HMI `.9`, sup `.30`, insider `.66`, OT-FW `.1`) · SDN control `10.10.10.0/24`.

---

## 1. Power-UP — ORDER MATTERS
1. **hAP first** → wait ~45 s (control-plane switch must be up before the Dells).
2. **Teaching boxes** (Box1 PLC1/HMI1, Box2 PLC2/HMI2) → wait for PLCs to reach RUN.
3. **Dells** — #1, #2, #3.

## 2. What auto-restores vs manual on boot
- **Auto (persistent):** OVS bridges/ports + patches (OVSDB) · `fail_mode: secure` (OVSDB) · ARP-flux fix (`/etc/sysctl.d/99-cars-arp.conf`) · seam IPs (**`cars-seams.service`**, if installed) · Docker containers (`unless-stopped`) · control-plane static IPs (nmcli).
- **Manual:** the CARS controller (Dell #2, foreground) · the dashboard (Dell #1) · Snort + bridge (when running the detection loop) · GNS3 GUI.

---

## 3. Verification checklist (top-to-bottom)

### L1 — control plane (any Dell)
- [ ] `ping -c2 10.10.10.1 && ping -c2 10.10.10.2 && ping -c2 10.10.10.3`

### L2 — OVS fabric (Dell #1 + Dell #3)
- [ ] `sudo ovs-vsctl show` → `ovs1`+`ovsgw` (Dell#1) / `ovs2` (Dell#3), Controller `tcp:10.10.10.1:6653`.
- [ ] `sudo ovs-vsctl get-fail-mode ovs1 ovsgw` (and `ovs2` on Dell#3) → **secure** on all.
  - If a controller line is missing: `sudo ovs-vsctl set-controller <br> tcp:10.10.10.1:6653`.

### L2.5 — seams (Dell #1)
- [ ] `ip -br addr show sup0` → `192.168.2.30/24` · `ip -br addr show att0` → `192.168.2.66/24`.
  - If missing (and no `cars-seams.service`): `sudo systemctl start cars-seams` OR manually
    `sudo ip addr add 192.168.2.30/24 dev sup0; sudo ip link set sup0 up` (and `.66` on att0; `ip link set it0/snort0 up`).

### L3 — CARS controller (Dell #2)
- [ ] `cd ~/cars && source venv/bin/activate && osken-manager --observe-links ~/cars/cars_engine.py`
  - Logs: `GUARD installed on dpid=1/2/3 (ip=True arp=True)`, `>>> switch UP dpid=1/2/3`.
- [ ] `curl -s http://10.10.10.1:8080/cars/status` → `"switches":[1,2,3], "guard":true, "arp_guard":true`.
- [ ] `curl -s http://10.10.10.1:8080/cars/hosts` → PLC1/HMI1/PLC2/HMI2 (sup0 appears once it sends).

### L4 — real control loops
- [ ] Box1 + Box2 HMIs show **connected** to their PLCs (S7comm live). `ping -c2 -I sup0 192.168.2.10` replies.

### L5 — hardening proofs (optional but definitive)
- [ ] **Source-guard:** forge `.30`/`.9` from att0 (scapy) → dropped; `dump-flows ovsgw table=0 | grep priority=100` counters climb; legit `sup0` unaffected.
- [ ] **Fail-secure:** kill controller → `dump-flows ovsgw table=0 | grep -c priority` stays nonzero, `ping -I sup0 .10` still replies (broadcast-flood re-resolves ARP), forged `.30` still dropped. Relaunch → clean re-attach + discovery repopulates.

### L6 — periphery (when needed)
- [ ] Snort: `sudo snort -A fast -i snort0 -c /etc/snort/cars.conf -l /var/log/snort` + `python3 ~/snort_bridge.py` (reports to `/cars/respond`).
- [ ] Dashboard: `python3 ~/cars_dashboard.py` → `http://localhost:8090` (badges show `src-guard armed` / `arp-guard armed`).
- [ ] GNS3: open `cars-killchain`, start nodes (IT attacker path).

---

## 4. Hardened-state summary (what "good" looks like)
`fail_mode: secure` on all bridges · `GUARD_ENABLED=True` + `ARP_GUARD_ENABLED=True` · ARP-flux sysctl in place · seam IPs present · controller with `--observe-links` · discovery lists the real hosts · dashboard badges green.

## 5. Rollback points (Dell #2 `~/cars/`)
`cars_engine_v04_stable.bak` (v0.4 brain) · `cars_engine_v051.bak` (v0.5.1 discovery) · `cars_engine_v06.bak` (v0.6 IP-guard). Restore = `cp <bak> cars_engine.py` + relaunch.

## 6. Known residuals (documented, not bugs)
Cell 2 has no IDS detection yet (mirror is on ovsgw only; needs P4 transit or a 2nd sensor) · switch-reboot-during-controller-outage → blackout until CARS returns · guard bindings must be re-verified if hardware is re-plugged (ofports).
