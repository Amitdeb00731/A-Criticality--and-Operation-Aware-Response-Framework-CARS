import subprocess, urllib.request, json, time, re
ALERT="/var/log/snort/alert"
API="http://10.10.10.1:8080/cars/respond"
COOLDOWN=3
RATEWIN=3.0        # A5: window (s) over which we count an op's burst to estimate its arrival rate (ops/s)
def post(url,data):
    req=urllib.request.Request(url,data=json.dumps(data).encode(),headers={"Content-Type":"application/json"})
    return urllib.request.urlopen(req,timeout=5).read().decode()
print("CARS-Snort bridge v4 (A3 op-aware + A5 rate) -> /cars/respond (brain decides)")
p=subprocess.Popen(["tail","-F","-s","0.05","-n0",ALERT],stdout=subprocess.PIPE,text=True)
seen={}; hits={}
for line in p.stdout:
    m=re.search(r'\{(ICMP|TCP|UDP)\}\s+([\d.]+)(?::\d+)?\s+->\s+([\d.]+)(?::\d+)?',line)
    if not m: continue
    proto,src,dst=m.group(1),m.group(2),m.group(3)
    # A3: pull the ICS protocol family + operation from the DPI alert message, if present.
    # CC-62 (PLC2-3): when a DPI operation rule fires, surface the ICS PROTOCOL (S7/MODBUS) in the
    # proto field in place of the bare transport (TCP) - so the decision log names S7 vs Modbus, not
    # just "TCP", while the op field keeps the operation semantics (CONTROL/READ/DIAG/...).
    op=None
    mo=re.search(r'CARS-(MODBUS|S7)-(WRITE|READ|CONTROL|DIAG|PROGRAM|ILLEGAL)',line)  # CC-51/PD: broadened ICS op taxonomy (Modbus + classic S7comm)
    if mo: proto=mo.group(1); op=mo.group(2)
    elif 'CARS-S7COMMPLUS' in line: proto='S7'; op='S7'   # A3/P5: S7CommPlus session marker (no func-code DPI on 0x72)
    key=(src,dst,op)                      # keep read vs write distinct (don't collapse under cooldown)
    # A5: count EVERY alert for this key over RATEWIN (even those suppressed by cooldown) so the brain sees the true
    # burst rate. The cooldown still limits how often we POST, but each POST carries the current ops/s.
    now=time.time()
    h=hits.setdefault(key,[]); h.append(now)
    while h and now-h[0]>RATEWIN: h.pop(0)
    rate=round(len(h)/RATEWIN,1)          # ops/s for THIS (src,dst,op) over the window
    if now-seen.get(key,0)<COOLDOWN: continue
    seen[key]=now
    payload={"src":src,"dst":dst,"proto":proto,"dpid":3,"rate":rate}
    if op: payload["op"]=op
    try:
        print(time.strftime("%H:%M:%S"),"REPORT",src,"->",dst,proto,("op="+op if op else ""),("%.0f/s"%rate),
              "| CARS:",post(API,payload))
    except Exception as e:
        print("bridge error:",e)
