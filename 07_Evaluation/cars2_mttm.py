#!/usr/bin/env python3
# Cell-2 MTTM harness — IDENTICAL timing method to mttm.py (AG2), only the target changes,
# so Cell-1 (insider) vs Cell-2 (NAT path) numbers are directly comparable.
import time, subprocess, urllib.request, json, statistics
API="http://10.10.10.1:8080"; SRC="192.168.3.66"; DST="192.168.3.10"; IFACE="ins2"
CONDUIT=SRC+"->"+DST
def status():
    try: return json.loads(urllib.request.urlopen(API+"/cars/status",timeout=2).read())
    except Exception: return {}
def blocked(): return any(CONDUIT in b for b in status().get("conduit_blocks",[]))
def restore():
    try:
        r=urllib.request.Request(API+"/cars/restore",data=json.dumps({"src":SRC,"dst":DST}).encode(),
                                 headers={"Content-Type":"application/json"})
        urllib.request.urlopen(r,timeout=2).read()
    except Exception: pass
N=20; res=[]
print("MTTM - Cell-2 %s -> %s  (%d trials)"%(SRC,DST,N))
for i in range(N):
    restore(); time.sleep(0.4)
    if blocked(): restore(); time.sleep(0.6)
    t0=time.time()
    p=subprocess.Popen(["ping","-i","0.1","-I",IFACE,DST],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    while not blocked() and time.time()-t0<15: time.sleep(0.02)
    mttm=time.time()-t0; p.terminate(); res.append(mttm)
    print("  trial %2d: MTTM = %.3f s"%(i+1,mttm)); time.sleep(4)
restore(); res.sort()
print("\n=== MTTM (Cell-2 NAT path) n=%d ==="%len(res))
print("mean=%.3f  median=%.3f  std=%.3f  min=%.3f  max=%.3f  (seconds)"%(
    statistics.mean(res),statistics.median(res),statistics.pstdev(res),res[0],res[-1]))
open("/home/msclab/cars2_mttm_results.csv","w").write("trial,mttm_s\n"+"\n".join("%d,%.3f"%(i+1,v) for i,v in enumerate(res)))
print("saved -> ~/cars2_mttm_results.csv")
