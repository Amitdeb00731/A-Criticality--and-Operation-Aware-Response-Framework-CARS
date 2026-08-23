#!/usr/bin/env python3
"""Water-tank process co-simulation for the CARS emulation.

Adapted from 06_Build/cars_process.py. Runs the bang-bang control loop against
the emulated S7 PLC over real S7comm: reads the pump relay (PA0.3, mask 0x08),
updates the level with the fill/drain dynamics, re-asserts the relay every cycle,
and reads it back to report interference (readback != intent = an attacker write
that momentarily reached the actuator). On the testbed this ran on Factory IO + a
real CPU; here the same loop drives the software S7 server.

    python3 tank.py --host 127.0.0.1 --tcp-port 102
"""
import argparse
import sys
import time

import snap7

try:
    from snap7.type import Area
    PA = Area.PA
except Exception:
    PA = 0x82

RELAY_MASK = 0x08  # PA byte 0 bit 3 = pump relay Q0.3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="192.168.2.10")
    ap.add_argument("--rack", type=int, default=0)
    ap.add_argument("--slot", type=int, default=1)
    ap.add_argument("--tcp-port", type=int, default=102)
    ap.add_argument("--low", type=float, default=30.0)
    ap.add_argument("--high", type=float, default=70.0)
    ap.add_argument("--fill", type=float, default=6.0)
    ap.add_argument("--drain", type=float, default=5.0)
    ap.add_argument("--dt", type=float, default=0.5)
    a = ap.parse_args()

    c = snap7.client.Client()
    c.connect(a.host, a.rack, a.slot, tcp_port=a.tcp_port)
    if not c.get_connected():
        print("[tank] connect FAILED (PLC up? conduit allowed?)", file=sys.stderr)
        return 1
    print(f"[tank] process online against {a.host}:{a.tcp_port} — bang-bang tank, actuator PA0.3")
    level, pump, last, cyc, n, bad = 50.0, False, False, 0, 0, 0
    try:
        while True:
            if level <= a.low:
                pump = True
            elif level >= a.high:
                pump = False
            level = max(0.0, min(100.0, level + (a.fill if pump else -a.drain)))
            c.write_area(PA, 0, 0, bytearray([RELAY_MASK if pump else 0x00]))   # actuate + reassert
            got = c.read_area(PA, 0, 0, 1)[0] & RELAY_MASK                       # read the relay back
            n += 1
            if (got != 0) != pump:
                bad += 1
            if pump != last:
                cyc += 1
                last = pump
            print("[tank] level=%5.1f  pump=%-3s  cycles=%d  relay=%-3s  interference=%d/%d"
                  % (level, "ON" if pump else "off", cyc, "ON" if got else "off", bad, n))
            time.sleep(a.dt)
    except KeyboardInterrupt:
        c.write_area(PA, 0, 0, bytearray([0x00]))
        c.disconnect()
        print("\n[tank] stopped. actuations=%d interference-events=%d" % (n, bad))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
