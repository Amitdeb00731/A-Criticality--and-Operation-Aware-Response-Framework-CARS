#!/usr/bin/env python3
# cars_evidence_logger.py — RAW process/relay evidence logger for the disarmed-devastation baseline.
# Samples tank Level (DB7.0 Real) + relay Q0.3 (output byte 0, bit 3) + agent restores, timestamped, to CSV.
# Independent of the remediation agent (reads the PLC directly), so it works even in the agent-OFF pass.
# RUN on Dell#1 in a PLC-reachable netns with the snap7-capable python:
#   sudo ip netns exec opns /usr/bin/python3 /home/msclab/cars_evidence_logger.py <tag> <secs>
import snap7, struct, time, sys, json
HOST = "192.168.2.10"
tag  = sys.argv[1] if len(sys.argv) > 1 else "run"
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 200
OUT  = "/tmp/cars_evidence_%s.csv" % tag
c = snap7.client.Client(); c.connect(HOST, 0, 1)
f = open(OUT, "w"); f.write("ts,iso,level,relay_Q03,pump_expected,restores\n")
end = time.time() + secs; n = 0; toggles = 0; prev = None
lvl_min = 9e9; lvl_max = -9e9
print("[LOG] %s: logging %.0fs -> %s" % (tag, secs, OUT))
while time.time() < end:
    try:
        lvl = struct.unpack('>f', bytes(c.db_read(7, 0, 4)))[0]
        qb0 = c.ab_read(0, 1)[0]              # process-image output byte 0
        relay = (qb0 >> 3) & 1                # Q0.3 = pump relay
        rest = 0
        try: rest = json.load(open("/tmp/cars_remediation_status.json")).get("restores", 0)
        except Exception: pass
        if prev is not None and relay != prev: toggles += 1
        prev = relay
        lvl_min = min(lvl_min, lvl); lvl_max = max(lvl_max, lvl)
        pump_exp = 1 if lvl <= 30 else (0 if lvl >= 70 else -1)
        ts = time.time()
        f.write("%.3f,%s,%.1f,%d,%d,%d\n" % (ts, time.strftime("%H:%M:%S", time.localtime(ts)), lvl, relay, pump_exp, rest))
        f.flush(); n += 1
    except Exception:
        f.write("%.3f,ERR,,,,\n" % time.time()); f.flush()
        try: c.disconnect(); c.connect(HOST, 0, 1)
        except Exception: pass
    time.sleep(0.3)
f.close()
print("[LOG] %s done: %d samples | relay toggles=%d | level range %.1f..%.1f -> %s"
      % (tag, n, toggles, lvl_min, lvl_max, OUT))
