#!/usr/bin/env python3
"""Emulated Modbus PLC for the CARS emulation (pymodbus 3.x async).

Adapted from 06_Build/mb_server.py: a deterministic holding-register map with
hr[8]=4242 as the designated safety-critical setpoint, so the Modbus attack and
detection paths behave exactly as on the testbed. Binds <ip>:502 by default.

    python3 modbus_server.py [ip] [port]
"""
import asyncio
import sys

from pymodbus.datastore import (ModbusSequentialDataBlock,
                                 ModbusServerContext)
from pymodbus.server import StartAsyncTcpServer

try:                                              # pymodbus <3.9
    from pymodbus.datastore import ModbusSlaveContext as DevCtx
except ImportError:                               # pymodbus >=3.9 (slave -> device)
    from pymodbus.datastore import ModbusDeviceContext as DevCtx

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.2.20"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 502

hr = ModbusSequentialDataBlock(0, [100, 101, 102, 103, 104, 105, 106, 107, 4242, 0])
co = ModbusSequentialDataBlock(0, [0] * 16)
di = ModbusSequentialDataBlock(0, [0] * 16)
ir = ModbusSequentialDataBlock(0, [200, 201, 202, 203, 0, 0, 0, 0, 0, 0])
store = DevCtx(di=di, co=co, hr=hr, ir=ir)
try:                                              # slaves= (old) vs devices= (new)
    ctx = ModbusServerContext(slaves=store, single=True)
except TypeError:
    ctx = ModbusServerContext(devices=store, single=True)


async def main() -> None:
    print(f"[modbus_server] emulated Modbus PLC up on {HOST}:{PORT} "
          f"(hr[8]=4242 safety-critical)", flush=True)
    await StartAsyncTcpServer(context=ctx, address=(HOST, PORT))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
