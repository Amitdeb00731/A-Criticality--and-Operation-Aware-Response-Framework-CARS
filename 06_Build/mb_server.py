#!/usr/bin/env python3
# CARS A3 — simulated Modbus PLC (deterministic register map). pymodbus 3.x async.
# Runs inside netns mbns, listens 192.168.2.20:502.
import asyncio, sys
from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext
try:                                             # pymodbus <3.9
    from pymodbus.datastore import ModbusSlaveContext as DevCtx
except ImportError:                              # pymodbus >=3.9 (slave -> device rename)
    from pymodbus.datastore import ModbusDeviceContext as DevCtx

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.2.20"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 502

# holding regs hr[0..9]; hr[8]=4242 = designated "safety-critical setpoint" (register-level demo)
hr = ModbusSequentialDataBlock(0, [100, 101, 102, 103, 104, 105, 106, 107, 4242, 0])
co = ModbusSequentialDataBlock(0, [0] * 16)
di = ModbusSequentialDataBlock(0, [0] * 16)
ir = ModbusSequentialDataBlock(0, [200, 201, 202, 203, 0, 0, 0, 0, 0, 0])
store = DevCtx(di=di, co=co, hr=hr, ir=ir)
try:                                             # slaves= (old) vs devices= (new)
    ctx = ModbusServerContext(slaves=store, single=True)
except TypeError:
    ctx = ModbusServerContext(devices=store, single=True)

async def main():
    print(f"[mb_server] Modbus PLC up on {HOST}:{PORT} (hr[8]=safety-critical)", flush=True)
    await StartAsyncTcpServer(context=ctx, address=(HOST, PORT))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
