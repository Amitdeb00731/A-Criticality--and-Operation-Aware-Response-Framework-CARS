#!/usr/bin/env python3
# Point 11 - vast accuracy test. Drives a large LABELLED corpus through the deployed decision path
# (/cars/respond, decision-only with enforcement DISARMED so no rules are installed), scores
# TP/TN/FP/FN against security intent, and reports accuracy + false-positive rate with a 95% Wilson CI.
# Run on Dell 1:  python3 vast_accuracy.py
import urllib.request, json, time, math, csv, os

API = "http://10.10.10.1:8080"
TOK = open("/home/msclab/cars/api_token").read().strip()
OUT = os.path.expanduser("~/overnight_%s/vast" % time.strftime("%Y%m%d")); os.makedirs(OUT, exist_ok=True)

def post(path, body, auth=False):
    h = {"Content-Type": "application/json"}
    if auth: h["X-CARS-Token"] = TOK
    r = urllib.request.urlopen(urllib.request.Request(API + path, data=json.dumps(body).encode(), headers=h), timeout=8)
    return json.loads(r.read())
def respond(s, d, o, rate):
    try: return post("/cars/respond", {"src": s, "dst": d, "op": o, "proto": "S7", "dpid": 3, "rate": rate})
    except Exception as e: return {"response": "ERR", "err": str(e)}

PERMIT = {"ALLOW", "MONITOR", "REFUSE"}          # REFUSE = safety loop, mirrored not cut = permitted on the wire
RESTRICT = {"THROTTLE", "DEFLECT", "ISOLATE", "BLOCK"}

# ---- build the labelled corpus (label = security intent, independent of what CARS decides) ----
cases = []
# LEGIT: registered supervisory reads at normal (sub-flood) rates -> expect PERMIT
LEGIT = [("192.168.2.9","192.168.2.10","READ"), ("192.168.2.30","192.168.2.10","READ"),
         ("192.168.2.31","192.168.2.10","READ"), ("192.168.2.45","192.168.2.10","READ"),
         ("192.168.3.66","192.168.3.10","READ"), ("192.168.2.30","192.168.2.20","READ")]
for (s,d,o) in LEGIT:
    for rate in (0,1,2,3,4): cases.append((s,d,o,rate,"legit"))
# EXEMPT: the flood-exempt HIL / EWS high-rate I/O -> expect PERMIT even at high rate
for rate in (0,10,30,50):
    cases.append(("192.168.2.55","192.168.2.10","READ",rate,"exempt"))
    cases.append(("192.168.2.55","192.168.2.10","WRITE",rate,"exempt"))
# ATTACK: many unregistered sources x assets x ops x rates -> expect RESTRICT
ATK = ["192.168.2.%d" % i for i in range(120,171)]     # 51 unregistered sources
DST = ["192.168.2.10","192.168.3.10","192.168.2.30","192.168.2.20","192.168.2.9"]
OPS = ["READ","WRITE","CONTROL","DIAG"]
for s in ATK:
    for d in DST:
        for o in OPS:
            for rate in (0,12): cases.append((s,d,o,rate,"attack"))

print("corpus: %d cases (legit+exempt %d, attack %d)"
      % (len(cases), sum(1 for c in cases if c[4] in ("legit","exempt")), sum(1 for c in cases if c[4]=="attack")))

# ---- run decision-only ----
post("/cars/defense", {"on": False}, auth=True); time.sleep(0.5)
tal = {"TP":0,"TN":0,"FP":0,"FN":0}; rows = []; t0 = time.time()
for (s,d,o,rate,label) in cases:
    r = respond(s,d,o,rate); resp = r.get("response")
    permit = resp in PERMIT
    if label in ("legit","exempt"):
        v = "TN" if permit else "FP"
    else:
        v = "FN" if permit else "TP"
    tal[v] += 1; rows.append((s,d,o,rate,label,r.get("tier"),resp,v))
post("/cars/defense", {"on": True}, auth=True)       # re-arm
dt = time.time() - t0

# ---- report ----
n = sum(tal.values()); acc = (tal["TP"]+tal["TN"])/n
legit_n = tal["TN"]+tal["FP"]; attack_n = tal["TP"]+tal["FN"]
fp_rate = tal["FP"]/legit_n if legit_n else 0.0
fn_rate = tal["FN"]/attack_n if attack_n else 0.0
def wilson(k, nn):
    if nn == 0: return (0.0, 0.0)
    z = 1.96; p = k/nn; d = 1+z*z/nn
    c = (p + z*z/(2*nn))/d; h = z*math.sqrt(p*(1-p)/nn + z*z/(4*nn*nn))/d
    return (max(0,c-h), min(1,c+h))
lo, hi = wilson(tal["TP"]+tal["TN"], n)
with open(os.path.join(OUT,"vast.csv"),"w",newline="") as f:
    w = csv.writer(f); w.writerow(["src","dst","op","rate","label","tier","response","verdict"]); w.writerows(rows)

print("\n=== VAST ACCURACY (decision-only, deployed engine) ===")
print("cases=%d in %.1fs   TP=%d TN=%d FP=%d FN=%d" % (n, dt, tal["TP"],tal["TN"],tal["FP"],tal["FN"]))
print("accuracy = %.4f   95%% Wilson CI [%.4f, %.4f]" % (acc, lo, hi))
print("false-positive rate = %.4f  (legit/exempt n=%d)" % (fp_rate, legit_n))
print("false-negative rate = %.4f  (attack n=%d)" % (fn_rate, attack_n))
if tal["FP"] or tal["FN"]:
    print("\n-- misclassifications (investigate) --")
    for row in rows:
        if row[7] in ("FP","FN"): print("  ", row)
print("\nsaved -> %s/vast.csv" % OUT)
