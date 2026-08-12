# Pre-Build Readiness Checklist — Tier 3 Testbed (Project CARS)

Complete these before starting Phase A. Grouped by area; tick as done.
Reference: `Reactive_SDN_ICS_Tier3_Architecture.docx`.

---

## 1. Hardware to gather / acquire
- [ ] Dell #1 (Ubuntu) — SDN core + virtualization host (16GB+, full admin) ✓ have
- [ ] Dell #2 (Windows) — Factory I/O + real PLC process (16GB+, full admin) ✓ have
- [ ] Asus Vivobook (Win 11) — HMI + EWS ✓ have
- [ ] Siemens S7-1200/1500 PLC + 24V PSU ✓ have
- [ ] **2–3× USB-to-Ethernet adapters** (for Dell #1 OVS ports) — TO BUY
- [ ] Ethernet cables (5–6× Cat5e/6, short)
- [ ] Small unmanaged switch OR extra dongles (fallback if not enough ports)
- [ ] Safe demo I/O for the PLC: a few LEDs / a 24V relay / lamp (NO motors/heaters)
- [ ] (Optional) a cheap managed switch if you want real VLAN trunking instead of OVS-internal VLANs

## 2. Per-machine OS prep
- [ ] Dell #1: Ubuntu 22.04 LTS updated; confirm boots to Ubuntu; note total RAM (`free -h`)
- [ ] Dell #1: confirm sudo/admin; virtualization enabled in BIOS (VT-x/AMD-V) for KVM
- [ ] Dell #2: Windows updated; confirm GPU drivers OK for Factory I/O 3D
- [ ] Asus: Windows 11 updated; admin rights confirmed
- [ ] Record every machine's fixed lab IP plan (see §6)

## 3. Software to download / install
**Dell #1 (Ubuntu):**
- [ ] Open vSwitch (`apt install openvswitch-switch`)
- [ ] Ryu SDN framework — install in a Python venv (⚠ Ryu needs Python ≤3.9/3.10; consider the `os-ken` fork if you hit eventlet errors on newer Python)
- [ ] Docker + docker-compose
- [ ] KVM/QEMU + virt-manager (for pfSense VMs)
- [ ] Suricata + Zeek + ICSNPP plugins (IDS)
- [ ] InfluxDB + Grafana (historian) — via Docker
- [ ] Mosquitto (MQTT broker) + an OPC UA server (open62541 or python-opcua/FreeOpcUa)
- [ ] OpenPLC (soft-PLC #2) — Docker or native
- [ ] Wireshark, tcpdump, nmap, pymodbus, python-snap7
- [ ] pfSense ISO (×1, used for both firewall VMs)
- [ ] Kali Linux ISO/VM (attacker)

**Dell #2 (Windows):**
- [ ] Factory I/O (already licensed — confirm it launches and license is active)
- [ ] (Optional) VirtualBox if offloading the Kali attacker here

**Asus (Windows):**
- [ ] TIA Portal (version matching your S7-1200/1500 firmware) — EWS
- [ ] Ignition Maker Edition (free account/activation) — HMI/SCADA
- [ ] (Optional) Node-RED + node-red-dashboard + node-red-contrib-modbus/s7

## 4. Accounts / licenses to sort
- [ ] Ignition Maker Edition — free license activation (Inductive Automation account)
- [ ] Factory I/O — confirm university license covers the Dells you'll use
- [ ] TIA Portal — license/dongle available and version-compatible with the PLC
- [ ] GitHub access for ICSSIM / ICS-SimLab / GRFICS / ICSNPP repos

## 5. Siemens S7-1200/1500 PLC prep (in TIA Portal)
- [ ] Read exact model + firmware off the device label / TIA Portal
- [ ] Assign a static IP on the control subnet
- [ ] **Enable PUT/GET** communication (needed by the Factory I/O S7 driver)
- [ ] Check **"Optimized block access"** setting — set to non-optimized for the data blocks the S7 driver / Modbus map read
- [ ] Configure a **Modbus TCP server** block (for the primary CARS traffic on 502)
- [ ] Write a minimal control program (reads Factory I/O sensors → drives actuators + a safe LED)
- [ ] Add a simple **safety interlock (SIS)** rung (e.g., high-level cutoff)
- [ ] Confirm you can go online / download to the PLC from TIA Portal

## 6. Network / addressing plan (write it down before cabling)
- [ ] Decide subnet(s) and VLAN IDs — Control=VLAN10, Supervisory=20, Ops=30, DMZ=35, Enterprise=40
- [ ] Assign static IPs: PLC, HMI/Asus, Factory I/O host, historian, IDS mirror, firewalls
- [ ] Confirm the whole bench is **isolated** — no bridge to home/uni/corporate/internet
- [ ] Plan which physical port (dongle) on Dell #1 maps to which device/OVS port

## 7. Safety pre-flight (non-negotiable)
- [ ] Air-gapped lab LAN confirmed (no internet reachability from PLC)
- [ ] Only harmless I/O wired (LEDs/relay/simulated process) — nothing hazardous
- [ ] Fail-safe default agreed: controller defaults to mirror/allow, never block, on uncertainty
- [ ] Emergency stop / power-off procedure known

## 8. Pre-build verification (smoke tests before Phase A logic)
- [ ] Factory I/O launches and its 3D scene runs on Dell #2
- [ ] TIA Portal connects to and downloads to the real PLC
- [ ] `ovs-vsctl show` works on Dell #1; can create br0 and add a port
- [ ] `ryu-manager` starts without errors (in the venv)
- [ ] Docker runs a hello-world container; virt-manager can boot a test VM
- [ ] Ignition Maker opens its web designer on the Asus
- [ ] Two machines can ping each other through an OVS bridge

---

## Quick "to-buy / to-download" summary
**Buy:** 2–3 USB-to-Ethernet adapters · Ethernet cables · LEDs/relay for safe I/O · (optional) small switch.
**Download (free):** Ubuntu, Open vSwitch, Ryu (or os-ken), Docker, KVM, Suricata, Zeek+ICSNPP, InfluxDB, Grafana, Mosquitto, OpenPLC, pfSense, Kali, Ignition Maker, Node-RED.
**Already have / licensed:** Factory I/O, TIA Portal, the PLC, all three laptops.

_When every box above is ticked, we start Phase A: Factory I/O + real PLC + Ignition HMI through OVS on a flat network._
