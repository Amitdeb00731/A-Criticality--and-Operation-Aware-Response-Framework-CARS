# CARS emulation — try it with no hardware

This layer runs the CARS pipeline end to end in software: the same os-ken controller, Snort and Open vSwitch as the testbed, with the physical Siemens PLC replaced by a software S7 server and the Modbus unit by a pymodbus server. Only the CPU is substituted — the S7comm/Modbus on the wire, the DPI, the flow-mods and the criticality-graded response are all genuine.

## Requirements

A Linux host (or VM) with **root**, plus:

- Open vSwitch and **Mininet**
- **Snort** (with the CARS rules from `../../06_Build/cars.rules`)
- Python deps: `pip install -e '..[controller,emulation]'` (os-ken, requests, python-snap7, `pymodbus>=3.5,<3.9`)

It cannot run in a sandbox without kernel network namespaces.

## Components

| File | Role | Verified |
|---|---|---|
| `plc/s7_server.py` | Software S7-1200: python-snap7 server on `:102`, exposing the pump relay (PA0.3) and DB1 | ✅ real S7comm round-trip tested |
| `plc/tank.py` | Water-tank co-simulation (bang-bang control) driving the S7 server, from `cars_process.py` | ✅ full loop tested against `s7_server` |
| `plc/modbus_server.py` | Software Modbus unit (pymodbus), from the testbed `mb_server.py` | reuses testbed-proven code; pin `pymodbus<3.9` |
| `topo.py` | Mininet two-cell fabric (ovs1/ovsgw/ovs2, OF 1.3, remote controller, Snort mirror) | runs on a Linux+root host |

## Quickstart

```bash
# 1. controller (config-driven), in one terminal
CARS_SITE=../examples/site.testbed.yaml osken-manager ../../06_Build/cars_engine.py

# 2. fabric + hosts, in another (root)
sudo python3 topo.py
#    then in the Mininet CLI, start the software PLCs and the process:
mininet> plc1 python3 plc/s7_server.py 192.168.2.10 &
mininet> mbplc python3 plc/modbus_server.py 192.168.2.20 &
mininet> hist  python3 plc/tank.py --host 192.168.2.10 &

# 3. launch an attack and watch CARS isolate it
mininet> atk python3 ../../06_Build/s7_write.py 192.168.2.10     # forbidden S7 CONTROL -> ISOLATE
```

Expected: the attacker's S7 write is recovered by Snort, classified FORBIDDEN on the CRITICAL PLC, and a `0x00ca` drop is installed (Table 1, priority 110); the tank loop keeps running.

## Verification status (honest)

The **S7 process core is verified**: `s7_server.py` serves real S7comm and `tank.py` runs the full bang-bang loop against it (level oscillates, pump cycles, relay reads back) — this is the substitution the emulation depends on. The **SDN layer** (`topo.py`) is standard Mininet + OVS + OpenFlow 1.3, the same stack the testbed runs; it is provided as the topology scaffold and should be validated on your host. The **Modbus server** mirrors the testbed `mb_server.py`; register addressing follows your pinned pymodbus version (use the shipped `mb_client.py`).

This is a functional demonstration, not a substitute for validating against real hardware and real process safety. See `../LIMITATIONS.md`.
