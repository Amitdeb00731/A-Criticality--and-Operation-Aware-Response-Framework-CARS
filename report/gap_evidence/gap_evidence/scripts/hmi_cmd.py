#!/usr/bin/env python3
import snap7, sys
try: from snap7.type import Area; MK=Area.MK
except Exception: MK=0x83
HOST="192.168.2.10"
val=int(sys.argv[1],0) if len(sys.argv)>1 else 0x04     # 0x04=HMI_Stop, 0x02=HMI_Start
c=snap7.client.Client(); c.connect(HOST,0,1)
c.write_area(MK,0,0,bytearray([val & 0xFF]))            # one authorized Write-Var (0x05) to %M
print("[HMI-CMD] wrote %%MB0 = 0x%02X (%s)" % (val, "HMI_Stop" if val&0x04 else "HMI_Start" if val&0x02 else "?"))
c.disconnect()
