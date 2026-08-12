#!/usr/bin/env python3
# cars_process_guardian.py - INDEPENDENT process-invariant monitor (defence-in-depth, READ-ONLY, ALARM-ONLY).
# Adds the checks the low-side remediation agent lacks: HIGH-side envelope, symmetric rate, and liveness.
# It NEVER writes the PLC and NEVER touches CARS enforcement or the remediation agent. Safe by construction.
# Level source: the remediation agent's published status file (no extra S7 load). Prod: a redundant sensor.
import json, time, os
STATUS="/tmp/cars_remediation_status.json"; FEED="/tmp/cars_guardian.jsonl"
CEIL=78.0; FLOORV=22.0      # safe envelope (control band is 28-72; alarm only outside a wider guard band)
MAXDELTA=25.0               # a per-poll jump this large is physically impossible = spoof/rate anomaly
STALL_S=12.0               # level frozen this long while it should be cycling = stopped/held (denial)
POLL=1.0
def alarm(kind, **kw):
    kw.update(event="PROCESS-ANOMALY", kind=kind, ts=time.time(), plc="PLC1")
    print("[GUARDIAN] ALARM %-10s %s" % (kind, {k:v for k,v in kw.items() if k not in ('event','ts','plc')}), flush=True)
    try:
        with open(FEED,"a") as f: f.write(json.dumps(kw)+"\n")
        os.chmod(FEED,0o644)
    except Exception: pass
def read_status():
    for _ in range(4):
        try:
            with open(STATUS) as f: d=json.load(f)
            return float(d["level"]), int(d.get("online",1)), float(d.get("ts",0))
        except Exception:
            time.sleep(0.05)
    raise RuntimeError("status unreadable after retries")
def main():
    print("[GUARDIAN] online (READ-ONLY, alarm-only): high-side envelope + rate + liveness on Tank.Level", flush=True)
    prev=None; last_val=None; last_change=time.time()
    while True:
        try: lvl, online, ts = read_status()
        except Exception as e:
            print("[GUARDIAN] status unreadable: %s"%e, flush=True); time.sleep(POLL); continue
        now=time.time()
        if lvl > CEIL:    alarm("HIGH_LEVEL", level=round(lvl,1), ceiling=CEIL)    # <-- what remediation MISSES
        if lvl < FLOORV:  alarm("LOW_LEVEL",  level=round(lvl,1), floor=FLOORV)
        if prev is not None and abs(lvl-prev) > MAXDELTA:
            alarm("RATE", level=round(lvl,1), prev=round(prev,1), delta=round(lvl-prev,1))
        if last_val is None or abs(lvl-last_val) > 0.6:
            last_val=lvl; last_change=now
        elif now-last_change > STALL_S:
            alarm("STALL", level=round(lvl,1), frozen_s=round(now-last_change,1)); last_change=now
        prev=lvl
        time.sleep(POLL)
main()
