# VD-1 — Real attacker VM setup (insider on OT via VMware→OVS; IT via GNS3)

_2026-07-20. Replaces VPCS with a full-OS attacker so ICS payloads (S7/Modbus) can be fired. Insider = VMware VM on OT L2
(.2.77) bridged into `ovsgw`. IT = same/clone VM in the GNS3 kill-chain IT zone (10.0.40.0/24 → DMZ → SNAT → it0)._

## Phase 1 — Build the attacker VM (VMware Workstation, Dell#1)
- OS: **Kali Linux** (full pentest/ICS toolkit; best for the "professionally-crafted" narrative) or **Ubuntu 22.04 minimal**
  (lighter/faster). Our scripts run on either.
- Specs: 2 vCPU, 4 GB RAM, 20 GB disk.
- **Two NICs** (set in VM settings before/after install):
  - NIC1 = **NAT (vmnet8)** → internet + apt + file transfer during setup only.
  - NIC2 = **Custom /dev/vmnet2** → the OT insider interface (added below). Attack traffic uses this.

## Phase 2 — Host wiring: vmnet2 → ovsgw (Dell#1, the part that makes CARS see it)
1. `sudo vmware-netcfg` → **Add Network → vmnet2** → Type **Host-only** → **UNCHECK "Use local DHCP service"** →
   keep "Connect a host virtual adapter" **checked** (we need the `vmnet2` interface) → **Apply**.
2. Turn `vmnet2` into a clean L2 uplink and add it to `ovsgw`:
   ```bash
   sudo ip addr flush dev vmnet2
   sudo ip link set vmnet2 up promisc on
   sudo ovs-vsctl add-port ovsgw vmnet2
   sudo ovs-vsctl show | grep -A1 vmnet2          # confirm it's a port on ovsgw
   sudo ovs-vsctl list mirror | grep -i select_all # confirm snort0 auto-mirrors new ports (true)
   ```
   (If `select_all` is not true, add vmnet2 to the mirror's select-src/dst-port explicitly.)

_Alternative (cleaner if you prefer all-in-GNS3): make a new OVS internal port `ins0` on `ovsgw`, bind a GNS3 **Cloud
node** to `ins0` (same pattern as `it0`), and attach the VM's OT NIC to that Cloud. Reuses the proven Cloud→OVS path._

## Phase 3 — VM network + tooling
Inside the VM:
```bash
# OT insider interface (NIC2 = the vmnet2 one; name may be eth1/ens37 - check `ip -br link`)
sudo ip addr add 192.168.2.77/24 dev eth1
sudo ip link set eth1 up
# (NIC1/NAT keeps internet for the next step)
sudo apt update && sudo apt install -y python3-pip nmap hping3 tcpdump
pip3 install --break-system-packages python-snap7 pymodbus scapy
```
Get our attack scripts onto the VM (via NAT NIC): `scp msclab@192.168.184.1:/home/msclab/{s7_write.py,mb_attack.py,mb_client.py} .`
(or VMware shared folder / paste). Confirm: `python3 s7_write.py --help`.

## Phase 4 — Verify the vantage (CARS sees .2.77)
```bash
# from the VM:
ping -c2 192.168.2.10
sudo python3 s7_write.py --host 192.168.2.10 --read
# on Dell#1:
sudo tail -8 /var/log/snort/alert | grep 2.77
curl -s http://10.10.10.1:8080/cars/audit | python3 -c "import json,sys;[print(l) for l in json.load(sys.stdin)['audit'] if '2.77' in l][-3:]"
```

### IMPORTANT interpretation (A2 vs A3)
`.2.77` is **NOT allowlisted**, so **A2 proactive default-deny will DROP its traffic to the PLC before it's even sent** —
the insider ping/read will fail and CARS shows the source blocked. **That is the correct, realistic result and is exactly
how we demonstrate A2** (an unlisted insider never reaches the PLC).
- Rows that test **A2 (proactive)**: run as-is from `.2.77` → expect blocked at L3/L4.
- Rows that test **A3 (operation-aware reactive)** need the payload to reach the wire, so temporarily **allowlist the
  insider conduit** first (simulating a *compromised trusted* host) so S7/Modbus PDUs get on the wire and DPI classifies
  them (CONTROL/DIAG/PROGRAM → BLOCK/ISOLATE). Add via hot-reload:
  `curl -s -XPOST http://10.10.10.1:8080/cars/reload-a2` after editing `a2_policy.json` to add `(.2.77,.2.10,6,102)`, or
  test A3 from the already-trusted operator vantage and keep `.2.77` as the pure-A2 insider.

## Phase 5 — IT vantage (after insider proven)
GNS3 is running (nodes green). Replace VPCS with the full-OS attacker in the IT zone (10.0.40.0/24): import the VMware VM
as a GNS3 VMware node (or a second clone), attach it where VPCS was, keep the kill chain (→ DMZ → OT-FW SNAT → it0 → PLC).
Then fire one ping from it to `192.168.2.10` and read the CARS audit — the **post-SNAT source IP** that appears is the
"IT VM" identity we track through R1/R4/R8/R13.
