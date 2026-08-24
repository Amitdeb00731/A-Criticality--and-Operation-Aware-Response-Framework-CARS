#!/usr/bin/env python3
"""Emulated S7-1200 PLC for the CARS emulation.

A python-snap7 *server* that speaks real S7comm on TCP/102, exposing the process
image the testbed used: the outputs area (PA) whose byte 0 bit 3 is the pump
relay (Q0.3, mask 0x08), plus a small data block (DB1) for level/setpoint. The
tank co-simulation (``tank.py``) and the attack clients read and write it exactly
as they would a physical CPU, so the S7 frames Snort inspects are genuine.

This substitutes for the physical Siemens CPU only; the wire protocol, the
controller, Snort and OVS remain real. See ../README.md and ../../LIMITATIONS.md.

Two process models:
  * default          — the plant is driven externally by ``tank.py`` (an S7
                       client). Fine for the proactive demo (no DPI sensor).
  * CARS_SELF_PLANT  — the bang-bang control loop runs *inside* this server,
                       directly on the process image, the way a real CPU runs
                       its ladder logic. No legitimate S7 control-write then
                       exists on the wire, so once Snort/DPI is live the only
                       S7 write-var Snort sees is an attack. The loop also
                       reports *interference*: if an external write flips the
                       relay between our cycles, that write momentarily reached
                       the actuator (the first-packet leak on a compromised,
                       allowlisted conduit — the report's Gap 3).

Usage:
    python3 s7_server.py [bind_ip] [tcpport]     # default 0.0.0.0:102 (102 needs root)
    CARS_SELF_PLANT=1 python3 s7_server.py ...   # PLC runs the plant itself
"""
import os
import struct
import sys
import threading
import time

import snap7
from snap7.server import Server

try:
    from snap7.type import SrvArea
    PA, DB = SrvArea.PA, SrvArea.DB
except Exception:                       # older bindings
    PA, DB = 0x82, 0x84

BIND = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 102

PA_SIZE = 16      # process outputs; byte 0 bit 3 (0x08) = pump relay Q0.3
DB_NUM = 1
DB_SIZE = 32      # DB1: bytes 0..3 level (REAL), 4..7 setpoint (REAL)
RELAY_MASK = 0x08

# self-plant tunables (match tank.py so both process models behave identically)
SELF_PLANT = os.environ.get("CARS_SELF_PLANT", "") not in ("", "0", "false", "no")
LOW = float(os.environ.get("CARS_LOW", 30.0))
HIGH = float(os.environ.get("CARS_HIGH", 70.0))
FILL = float(os.environ.get("CARS_FILL", 6.0))
DRAIN = float(os.environ.get("CARS_DRAIN", 5.0))
DT = float(os.environ.get("CARS_DT", 0.5))
SETPOINT = float(os.environ.get("CARS_SETPOINT", 50.0))


def _plant(pa, db1, stop):
    """Run the bang-bang tank loop on the process image, in-process (no S7 wire
    traffic). Detects an external actuator write as interference."""
    level, pump, last, cyc, n, bad = SETPOINT, False, False, 0, 0, 0
    struct.pack_into(">f", db1, 4, SETPOINT)                 # DB1.4 setpoint (REAL)
    pa[0] = 0x00
    intent = False
    print("[plc] self-plant ON — CPU runs the bang-bang loop; the actuator is "
          "driven internally, so any external S7 write-var is an attack.", flush=True)
    while not stop.is_set():
        # 1) did an external write move the relay since we last asserted it?
        got = bool(pa[0] & RELAY_MASK)
        if got != intent:
            bad += 1                                          # interference: a foreign write reached the actuator
        # 2) control law + plant dynamics
        if level <= LOW:
            pump = True
        elif level >= HIGH:
            pump = False
        level = max(0.0, min(100.0, level + (FILL if pump else -DRAIN)))
        # 3) actuate (re-assert intent) + publish level for read-only monitors
        pa[0] = RELAY_MASK if pump else 0x00
        intent = pump
        struct.pack_into(">f", db1, 0, level)                # DB1.0 level (REAL)
        n += 1
        if pump != last:
            cyc += 1
            last = pump
        print("[plc] level=%5.1f  pump=%-3s  cycles=%d  relay=%-3s  interference=%d/%d"
              % (level, "ON" if pump else "off", cyc, "ON" if pa[0] & RELAY_MASK else "off", bad, n),
              flush=True)
        stop.wait(DT)


def main() -> int:
    srv = Server()
    # NB: register_area keeps the SAME reference for a bytearray (but copies a
    # ctypes array), so the self-plant thread must mutate these bytearrays in
    # place for clients — and the loop's own read-back — to see fresh values.
    pa = bytearray(PA_SIZE)
    db1 = bytearray(DB_SIZE)
    srv.register_area(PA, 0, pa)
    srv.register_area(DB, DB_NUM, db1)
    srv.start(tcp_port=PORT)
    print(f"[s7_server] emulated S7 PLC up on {BIND}:{PORT} "
          f"(PA {PA_SIZE}B, DB{DB_NUM} {DB_SIZE}B); relay = PA0.3 mask 0x08", flush=True)

    stop = threading.Event()
    plant = None
    if SELF_PLANT:
        plant = threading.Thread(target=_plant, args=(pa, db1, stop), daemon=True)
        plant.start()

    try:
        while True:
            # surface the server event log so a viewer can see the S7 sessions/reads/writes
            evt = srv.pick_event()
            if evt:
                print("[s7_server]", srv.event_text(evt), flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        if plant:
            plant.join(timeout=1.0)
        srv.stop()
        srv.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
