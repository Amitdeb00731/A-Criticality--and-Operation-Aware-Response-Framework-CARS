#!/usr/bin/env python3
"""Emulated S7-1200 PLC for the CARS emulation.

A python-snap7 *server* that speaks real S7comm on TCP/102, exposing the process
image the testbed used: the outputs area (PA) whose byte 0 bit 3 is the pump
relay (Q0.3, mask 0x08), plus a small data block (DB1) for level/setpoint. The
tank co-simulation (``tank.py``) and the attack clients read and write it exactly
as they would a physical CPU, so the S7 frames Snort inspects are genuine.

This substitutes for the physical Siemens CPU only; the wire protocol, the
controller, Snort and OVS remain real. See ../README.md and ../../LIMITATIONS.md.

Usage:
    python3 s7_server.py [bind_ip] [tcpport]     # default 0.0.0.0:102 (102 needs root)
"""
import ctypes
import sys
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


def main() -> int:
    srv = Server()
    pa = (ctypes.c_uint8 * PA_SIZE)()
    db1 = (ctypes.c_uint8 * DB_SIZE)()
    srv.register_area(PA, 0, pa)
    srv.register_area(DB, DB_NUM, db1)
    srv.start(tcp_port=PORT)
    print(f"[s7_server] emulated S7 PLC up on {BIND}:{PORT} "
          f"(PA {PA_SIZE}B, DB{DB_NUM} {DB_SIZE}B); relay = PA0.3 mask 0x08", flush=True)
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
        srv.stop()
        srv.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
