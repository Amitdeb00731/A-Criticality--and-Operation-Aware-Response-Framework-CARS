# Hardware and requirements

**You do not need ICS hardware to run or reproduce CARS.** The emulation reproduces the full defended-attack pipeline in software on a single Linux machine. Real hardware is only needed to reproduce the exact physical timing and process-safety measurements. Three tiers:

## Tier 0 — Emulation (no hardware) — recommended, and what an external user runs

Reproduces the pipeline end to end with software PLCs: the same os-ken controller, Snort DPI, Open vSwitch and S7/Modbus wire traffic — only the physical Siemens CPU is replaced by a `python-snap7` server.

Minimum:
- **One x86-64 Linux host or VM** (tested on Ubuntu 22.04). ~2 vCPU, 4 GB RAM, ~10 GB disk, root/sudo.
- Packages: **Open vSwitch, Mininet, Snort**, and **Python 3.9+**.
- `pip install -e 'framework[controller,emulation]'` (os-ken, python-snap7, pymodbus, eventlet).
- **No PLCs, no switches, no cabling, no HMI.**

Run it: see `REPRODUCE.md` §2 and `framework/emulation/README.md`. The decision logic and the S7 process core also run headlessly on any OS via `pytest` (no root/Mininet needed).

## Tier 1 — Minimal real hardware (one PLC)

If you want genuine S7 traffic against a physical CPU, the testbed collapses to **two devices**:
- **One Linux host** running the controller **and** Open vSwitch **and** Snort **and** the supervisory/attacker endpoints (as Linux network namespaces) — all co-located, exactly as on the validated testbed's fabric-and-sensing node.
- **One Siemens S7-1200 PLC** (validated on a CPU 1212C, 6ES7 212-1BE40-0XB0, firmware 4.2.3).
- **One Ethernet link** (or a small unmanaged switch) between them.
- *Optional:* a Windows PC running **TIA Portal** (to program the PLC) and **Factory IO** (the tank process). Without it, drive the process with the software model (`06_Build/cars_process.py`).

This drops the second cell (`ovs2`/PLC2), the HMI panel and the separate management access point; the single Linux box carries the fabric, the sensor and the namespaced hosts.

## Tier 2 — Full testbed (as validated in the dissertation)

The complete setup behind the reported timing/process results (see `06_Build/AS_BUILT_TOPOLOGY.md`):
- **Four machines** — the OVS fabric + Snort + namespaced endpoints; the controller; the second cell (`ovs2`); and a Windows engineering workstation (TIA Portal + Factory IO). USB-C/USB and Ethernet adapters as needed.
- **Two Siemens S7-1200 PLCs** (1212C, firmware 4.2.3).
- **One Siemens KTP700 operator panel** (HMI).
- **One hAP access point** providing the isolated wired **management network** for the OpenFlow control plane, kept separate from the OT data plane.
- Ethernet cabling between the fabric, the PLCs, the HMI and the management plane.

None of this is required to run or reproduce the CARS *pipeline* — it is the high-fidelity environment that produced the specific reaction-window and process-safety numbers.

## Software

From `06_Build/requirements.txt` and system packages: **os-ken** (OpenFlow 1.3 controller), **python-snap7**, **pymodbus**, **eventlet**; **Open vSwitch**; **Snort 2.9.x**; **Python 3.9+**. Snort and Open vSwitch are system packages, not pip dependencies.

---

**In short:** clone the repo, install on one Linux box, and run the emulation — no PLCs, no cables, no ICS kit. Add a single S7-1200 for real-hardware fidelity; the full four-machine testbed is only for reproducing the exact measurements.
