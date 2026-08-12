#!/usr/bin/env python3
# CARS accuracy / false-positive evaluation — decision matrix via /cars/respond (grounded in REGISTRY+RULEBOOK).
# Runs the deployed engine's exact decision path (classify -> criticality elevation -> select_response) for a
# labelled case set, scores TP/TN/FP/FN, writes cars_eval_matrix.csv. Disarms for the decision-only pass, re-arms.
# Run on Dell#1:  python3 cars_eval.py
import json, urllib.request, time, csv
API="http://10.10.10.1:8080"; TOKEN=open("/home/msclab/cars/api_token").read().strip()
def post(path, body, auth=False):
    h={"Content-Type":"application/json"}
    if auth: h["X-CARS-Token"]=TOKEN
    r=urllib.request.urlopen(urllib.request.Request(API+path,data=json.dumps(body).encode(),headers=h),timeout=6)
    return json.loads(r.read())
def respond(src,dst,op,rate=0,dpid=1): return post("/cars/respond",{"src":src,"dst":dst,"op":op,"proto":"S7","dpid":dpid,"rate":rate})
PERMIT={"ALLOW","MONITOR","REFUSE"}
# (src,dst,op,rate,label,note)   label: legit|grey|attack|flood_exempt   — grey rows are shown, not scored
CASES=[
 # BAND 1 — LEGIT BENIGN (expect PERMIT) — false-positive test
 ("192.168.2.9","192.168.2.10","READ",0,"legit","HMI->PLC1 read (operator loop)"),
 ("192.168.2.9","192.168.2.10","WRITE",0,"legit","HMI->PLC1 setpoint (loop / safety-invariant)"),
 ("192.168.2.10","192.168.2.9","READ",0,"legit","PLC1->HMI reply (loop)"),
 ("192.168.2.55","192.168.2.10","READ",0,"legit","EWS/FactoryIO output read (HIL)"),
 ("192.168.2.55","192.168.2.10","CONTROL",0,"legit","EWS/FactoryIO input-image write (HIL)"),
 ("192.168.2.45","192.168.2.10","CONTROL",0,"legit","Remediation last-good restore"),
 ("192.168.2.30","192.168.2.10","READ",0,"legit","Historian telemetry poll PLC1"),
 ("192.168.2.30","192.168.2.20","READ",0,"legit","Historian telemetry poll Modbus"),
 ("192.168.2.31","192.168.2.20","READ",0,"legit","SCADA Modbus poll"),
 ("192.168.2.31","192.168.2.10","READ",0,"legit","SCADA read PLC1 (reads never elevated)"),
 # BAND 3 — GREY / criticality-graded (run before attacks so persistence doesn't pre-escalate)
 ("192.168.2.31","192.168.2.10","WRITE",0,"grey","SCADA WRITE CRITICAL PLC1 -> elevate SENSITIVE->FORBIDDEN"),
 ("192.168.2.31","192.168.2.20","WRITE",0,"grey","SCADA WRITE LOW Modbus -> SENSITIVE (graded)"),
 ("192.168.2.30","192.168.2.9","WRITE",0,"grey","Historian WRITE HIGH HMI1 -> SENSITIVE (graded)"),
 # BAND 2 — ATTACKS (expect BLOCK/ISOLATE) — true-positive / false-negative
 ("192.168.2.77","192.168.2.10","TCP",0,"attack","Kali outsider TCP->PLC1 (unregistered)"),
 ("192.168.2.77","192.168.2.10","READ",0,"attack","Kali outsider read PLC1"),
 ("192.168.2.66","192.168.2.20","WRITE",0,"attack","Unknown attacker write Modbus"),
 ("192.168.2.31","192.168.2.10","CONTROL",0,"attack","Compromised SCADA forces PLC1 actuator"),
 ("192.168.2.31","192.168.2.10","PROGRAM",0,"attack","SCADA unauthorized program download"),
 ("192.168.2.55","192.168.2.10","PROGRAM",0,"attack","EWS unauthorized program download (no window)"),
 ("192.168.2.55","192.168.2.10","DIAG",0,"attack","EWS unauthorized diagnostics"),
 ("192.168.2.55","192.168.2.10","ILLEGAL",0,"attack","Malformed/illegal S7 to PLC1"),
 ("192.168.2.1","192.168.2.10","READ",0,"attack","Gateway/DMZ reaches CRITICAL PLC (no conduit)"),
 ("192.168.2.30","192.168.2.10","CONTROL",0,"attack","Historian (read-only) issues CONTROL"),
 ("192.168.2.66","192.168.2.10","READ",0,"attack","Unknown attacker read CRITICAL PLC1"),
 # BAND 4 — FLOOD (volumetric overlay)
 ("192.168.2.30","192.168.2.10","READ",50,"attack","Historian READ flood (volumetric DoS, CRITICAL)"),
 ("192.168.2.55","192.168.2.10","CONTROL",50,"flood_exempt","EWS/FactoryIO high-rate CONTROL (FLOOD_EXEMPT)"),
 ("192.168.2.31","192.168.2.20","READ",50,"attack","SCADA READ flood on Modbus"),
]
def verdict(label,resp):
    permit=resp in PERMIT
    if label in ("legit","flood_exempt"): return "TN" if permit else "FP"
    if label=="attack": return "TP" if not permit else "FN"
    return "grey"
post("/cars/defense",{"on":False},auth=True); time.sleep(0.5)   # decision-only pass
print("%-11s %-13s %-9s %-9s %-4s %s"%("SRC->DST","OP(rate)","tier","resp","V","note"))
rows=[]; tal={"TP":0,"TN":0,"FP":0,"FN":0,"grey":0}
for src,dst,op,rate,label,note in CASES:
    try: o=respond(src,dst,op,rate); tier=o.get("tier"); resp=o.get("response")
    except Exception as e: tier="ERR"; resp=str(e)[:18]
    v=verdict(label,resp); tal[v]+=1
    print("%-11s %-13s %-9s %-9s %-4s %s"%("%s->%s"%(src.split('.')[-1],dst.split('.')[-1]),
          "%s(%d)"%(op,rate) if rate else op, tier, resp, v, note))
    rows.append((src,dst,op,rate,label,tier,resp,v,note))
post("/cars/defense",{"on":True},auth=True)   # re-arm
sc=tal["TP"]+tal["TN"]+tal["FP"]+tal["FN"]
print("\nTALLY  TP=%d TN=%d FP=%d FN=%d  grey=%d(shown)"%(tal["TP"],tal["TN"],tal["FP"],tal["FN"],tal["grey"]))
print("Accuracy=%.1f%%  FP-rate=%.1f%%  FN-rate=%.1f%%"%(100*(tal["TP"]+tal["TN"])/sc,
      100*tal["FP"]/max(1,tal["FP"]+tal["TN"]), 100*tal["FN"]/max(1,tal["FN"]+tal["TP"])))
with open("/tmp/cars_eval_matrix.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["src","dst","op","rate","label","tier","response","verdict","note"]); w.writerows(rows)
print("CSV -> /tmp/cars_eval_matrix.csv")
