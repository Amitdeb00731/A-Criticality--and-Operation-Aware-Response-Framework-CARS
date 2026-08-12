#!/usr/bin/env python3
# CARS A3 — Modbus operator/attacker client. pymodbus 3.x.
# Run inside a netns (opns/atkns) so the source IP is that namespace's fabric IP.
import argparse
from pymodbus.client import ModbusTcpClient

p = argparse.ArgumentParser()
p.add_argument("--host", default="192.168.2.20")
p.add_argument("--op", required=True,
               choices=["read", "read_coils", "write", "write_multi", "write_coil"])
p.add_argument("--reg", type=int, default=0)
p.add_argument("--val", type=int, default=1)
p.add_argument("--count", type=int, default=4)
a = p.parse_args()

c = ModbusTcpClient(a.host, port=502, timeout=2)
if not c.connect():
    print("[client] TCP connect FAILED (conduit dropped/blocked?)")
    raise SystemExit(2)
try:
    if a.op == "read":
        r = c.read_holding_registers(address=a.reg, count=a.count)
        print("[client] READ  hr[%d..%d] -> %s" % (a.reg, a.reg + a.count - 1,
              getattr(r, "registers", r)))
    elif a.op == "read_coils":
        r = c.read_coils(address=a.reg, count=a.count)
        print("[client] READ_COILS co[%d..] -> %s" % (a.reg, getattr(r, "bits", r)))
    elif a.op == "write":                       # FC 0x06 write single register
        r = c.write_register(address=a.reg, value=a.val)
        print("[client] WRITE hr[%d]=%d -> %s" % (a.reg, a.val, "OK" if not r.isError() else r))
    elif a.op == "write_multi":                 # FC 0x10 write multiple registers
        r = c.write_registers(address=a.reg, values=[a.val] * a.count)
        print("[client] WRITE_MULTI hr[%d..]=%d -> %s" % (a.reg, a.val, "OK" if not r.isError() else r))
    elif a.op == "write_coil":                  # FC 0x05 write single coil
        r = c.write_coil(address=a.reg, value=bool(a.val))
        print("[client] WRITE_COIL co[%d]=%d -> %s" % (a.reg, a.val, "OK" if not r.isError() else r))
except Exception as e:
    print("[client] request error: %r" % e)
finally:
    c.close()
