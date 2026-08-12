# RESUME — Cell-2 fabric integration (paused 2026-07-13)

## State at pause (all logged in DECISION_LOG CC-29 + DEMO_RESULTS.md)
Cell-2 (`192.168.2.10` PLC, project-locked S7-1200, could NOT be re-IP'd) is integrated onto
the fabric as **`192.168.3.10`** via a **Dell#3 Linux NAT gateway** over an **isolated
point-to-point transit** (Dell#1 eth0 —monitor dock— cable —monitor dock— Dell#3 eth0; no lab
switch, no VXLAN).

**Proven this session (then paused):**
- Physical transit up: raw `192.168.99.x` ping across eth0<->eth0 = 0% loss; `.3.10` ping from a
  fabric test port = **ttl=29** (real PLC via one NAT hop).
- Brain: `.3.66->.3.10` FORBIDDEN/blocked, `.2.30->.3.10` OPERATIONAL/allowed,
  `.3.9->.3.10` CRITICAL/refused (all sub-ms).
- Live enforcement: block -> ping 100% loss, restore -> ping returns ttl=29.
- Engine change deployed: REGISTRY `.3.10->plc`, `.3.9->hmi` (bindings/guard untouched; transit
  port deliberately NOT an uplink, so guard still drops any Cell-1 IP over the transit).
- Persistence: `cars-cell2.service` (Dell#3) installed + enabled (auto-runs at boot). Dell#1's
  `ovsgw` transit port + `ofport_request=9` persist in the OVS DB.

## OPEN ISSUE to fix first on resume
At end of session `arping 192.168.3.10` from Dell#1 `ins2` **timed out** even though BOTH eth0s
had carrier (`link detected: yes`), the `ovsgw` eth0 port was present (ofport 9), Dell#3 eth0
owned `.3.10`, and the DNAT rule was in place. Leading suspicion: **monitor-dock transit held
carrier but stalled frames** after the mid-session `ip addr flush dev eth0`. A fresh power-up +
reseat usually clears it. Confirm with the raw L2 test below before touching NAT/OVS.

## Bring-up runbook (wiring is intact — do NOT re-cable)
1. **Power on** all three Dells, both teaching boxes (PLC1/HMI1, PLC2/HMI2), GNS3 (cars-killchain).
2. **Base fabric** per COLD_START: OVS bridges ovs1/ovs2/ovsgw, controller on Dell#2
   (`cd ~/cars && source venv/bin/activate && osken-manager --observe-links ~/cars/cars_engine.py`),
   cars-seams (sup0/att0), snort + bridge. Confirm `curl -s http://10.10.10.1:8080/cars/status`
   shows switches [1,2,3], guard true.
3. **Sanity: Cell-1 demo still green** (sup .2.30->PLC1 allowed; VPCS/insider blocked).

## Cell-2 transit verify (fix the open issue)
4. **Interface names** — after reboot confirm the monitor-dock NICs still come up as `eth0` on
   BOTH Dell#1 and Dell#3 (`ip -br a`). If either renamed to `enx...`, re-point:
   Dell#1 `ovs-vsctl del-port ovsgw eth0; ovs-vsctl add-port ovsgw <name> -- set interface <name> ofport_request=9`
   and edit `/usr/local/sbin/cars-cell2.sh` eth0 -> new name.
5. **Carrier**: `ethtool eth0 | grep -i "link detected"` = yes on both. If no, reseat the
   monitor-to-monitor Ethernet cable.
6. **Raw L2 test FIRST** (isolate physical from OVS/NAT). On Dell#1 temporarily pull eth0 from the
   bridge: `sudo ovs-vsctl del-port ovsgw eth0`. Then:
   - Dell#1: `sudo ip addr add 192.168.99.1/24 dev eth0`
   - Dell#3: `sudo ip addr add 192.168.99.2/24 dev eth0` (service owns .3.x; add 99.2 alongside)
   - Dell#3: `ping -c3 192.168.99.1`
   - If replies -> physical link good; remove 99.x, `sudo ovs-vsctl add-port ovsgw eth0 -- set interface eth0 ofport_request=9`, redo step 7.
   - If timeout -> reseat cable / re-plug both monitor Type-C ends, retry.
7. **Cell-2 end-to-end**:
   ```
   # Dell#1
   sudo ovs-vsctl add-port ovsgw ins2 -- set interface ins2 type=internal
   sudo ip addr add 192.168.3.66/24 dev ins2 && sudo ip link set ins2 up
   sudo arping -c3 -I ins2 192.168.3.10     # expect replies from Dell#3 eth0 MAC
   ping -c3 192.168.3.10                     # expect ttl=29
   ```
   If arping still fails with carrier up: `sudo ovs-appctl fdb/show ovsgw`,
   `sudo ovs-ofctl dump-flows ovsgw table=1` (confirm the ff:ff:ff:ff:ff:ff FLOOD flow), and
   restart the controller (clean-slate re-learn). On Dell#3 confirm it answers ARP for .3.10 by
   watching `sudo tcpdump -ni eth0 arp` during the arping.

## Remaining TODO after transit is green
- **AG4**: Snort rules for `.3.10/.3.9` were appended to `/etc/snort/cars.rules` (sids 1000005-8)
  but autonomous detection was NOT yet verified (the ping failed). Restart Snort (cars.conf
  instance) + bridge, then `ping 192.168.3.10` from a .3.66 fabric port and confirm the bridge
  auto-prints `REPORT .3.66 -> .3.10 ... FORBIDDEN ... blocked` and the ping cuts off.
- **Dashboard**: add the `.3.10` PLC2 node + transit link to `cars_dashboard.py` ANCH (not started).
- Clean up test ports when done: `sudo ovs-vsctl del-port ovsgw ins2`; `curl .../cars/restore`.

## Boot flow (post-services, 2026-07-15) — after any reboot
AUTOMATIC (enabled systemd services — no action needed):
- Dell#3: `cars-cell2.service` -> Cell-2 NAT gateway (cell2gw .2.1, eth0 .3.1/.3.10, DNAT/MASQUERADE, ofport pins 1/2).
- Dell#1: `cars-snort.service` (Snort afpacket on snort0) + `cars-bridge.service` (snort_bridge.py). Distro `snort.service` disabled/conflicted.
- Dell#1: `cars-hpot.service` -> A1/P3 DEFLECT decoy `hpot` .3.99 in its own netns `hpotns` on ovsgw (isolated stack so the decoy can reply to the attacker; CC-35).
- OVS bridges + ports (incl. ovsgw transit `eth0` ofport 9, `cell2gw`) restored from OVS DB.

MANUAL (ONE step, by choice): Dell#2 controller ->
`cd ~/cars && source venv/bin/activate && osken-manager --observe-links ~/cars/cars_engine.py`

Note: the bridge starts before the controller; its POSTs harmlessly error (connection refused)
until the controller is up, then connect automatically (retries per-alert, never crashes). Start
the controller anytime. Sensor is always afpacket (do NOT hand-launch Snort with default pcap).
Checks: `systemctl is-active cars-cell2` (Dell#3) · `systemctl is-active cars-snort cars-bridge` (Dell#1) · `journalctl -fu cars-bridge`.
