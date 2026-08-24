#!/usr/bin/env python3
"""Framework flow-table saturation test (supervisor review, point 8).

Stresses the DESIGN, not the testbed hardware. It drives the CARS enforcement layer
directly: each POST to /cars/respond carries a distinct unregistered source, which the
engine classifies FORBIDDEN and enforces as a source-scoped ISOLATE, installing one
reactive 0x00ca flow per switch. Distinct sources accumulate reactive flows in the
OpenFlow table, so we can measure how the framework behaves as that table fills:

  * table growth vs sources injected (does every isolate install?),
  * per-install latency as the table grows (classifier insertion cost),
  * the controller's own decide time under the load,
  * and the self-healing DRAIN once the flood stops (hard_timeout expiry), which is the
    property that BOUNDS flow-table growth under a sustained flood at rate*timeout.

Safety: the source pool is 100.64.0.0/10 (CGN space), colliding with no real host; the
isolates are source-scoped (they never match a legitimate conduit, cf. the connection-
pool analysis) and self-heal via hard_timeout, so the live process is not cut by
construction. The switches run fail_mode=secure, so a full table never stops existing
flows. Run on Dell#1 (needs ovs-ofctl):  sudo python3 flowtable_stress.py [max_sources]
"""
import csv
import json
import os
import subprocess
import sys
import time
import urllib.request

API = "http://10.10.10.1:8080"
DST = "192.168.2.10"            # CRITICAL PLC1 -> ISOLATE with the longest (75s) timeout = max accumulation
BR = "ovsgw"
MAX = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
CHECKPOINTS = [250, 500, 1000, 2000, 4000, 6000, 8000, 12000, 16000, 20000, 30000, 40000]
OUT = os.path.expanduser("~/flowtable_stress_%s.csv" % time.strftime("%Y%m%d_%H%M%S"))


def post(src):
    body = json.dumps({"src": src, "dst": DST, "op": "CONTROL", "proto": "S7", "dpid": 3}).encode()
    r = urllib.request.urlopen(
        urllib.request.Request(API + "/cars/respond", data=body,
                               headers={"Content-Type": "application/json"}), timeout=5)
    return json.loads(r.read())


def reactive_count():
    try:
        out = subprocess.check_output(["ovs-ofctl", "-O", "OpenFlow13", "dump-flows", BR, "table=1"],
                                      text=True, stderr=subprocess.DEVNULL)
        return sum(1 for line in out.splitlines() if "0xca" in line)
    except Exception:
        return -1


def decide_ms():
    try:
        s = json.loads(urllib.request.urlopen(API + "/cars/status", timeout=3).read())
        return s.get("cars_ms_avg")
    except Exception:
        return None


def srcgen():
    a, b, c = 64, 0, 0
    while True:
        yield "100.%d.%d.%d" % (a, b, c)
        c += 1
        if c > 255:
            c = 0; b += 1
        if b > 255:
            b = 0; a += 1
        if a > 127:
            a = 64


def med(xs):
    return sorted(xs)[len(xs) // 2] if xs else 0.0


def main():
    rows = []
    g = srcgen()
    sent = 0
    t0 = time.time()
    base = decide_ms()
    print("== flow-table saturation: up to %d sources -> %s (75s isolates), OVS %s ==" % (MAX, DST, BR))
    print("baseline: decide_ms=%s  reactive_flows=%d" % (base, reactive_count()))
    ceiling = None
    lat = []
    for cp in [c for c in CHECKPOINTS if c <= MAX]:
        while sent < cp:
            s = next(g)
            tp = time.perf_counter()
            try:
                post(s)
            except Exception as e:
                ceiling = ("post_error", sent, str(e)[:60])
                break
            lat.append((time.perf_counter() - tp) * 1000)
            sent += 1
        if ceiling:
            break
        fc = reactive_count()
        dm = decide_ms()
        window = lat[-500:]                                   # recent install latency
        pl = med(window)
        el = round(time.time() - t0, 1)
        print("  sources=%d  reactive_flows=%d  install_med_ms=%.2f  decide_ms=%s  t=%ss"
              % (sent, fc, pl, dm, el))
        rows.append(("ramp", el, sent, fc, dm, round(pl, 2)))
        if dm and base and dm > max(2.0, base * 50):
            ceiling = ("decide_latency_spike", sent, dm); break
        if 0 <= fc < sent * 0.5 and sent > 4000:
            ceiling = ("install_not_tracking", sent, fc); break
    print("ramp done; ceiling=%s; peak reactive_flows=%d" % (ceiling, reactive_count()))

    print("== drain (stop flood; watch hard_timeout self-heal the table) ==")
    for _ in range(24):
        time.sleep(5)
        fc = reactive_count()
        el = round(time.time() - t0, 1)
        print("  drain t=%ss  reactive_flows=%d  decide_ms=%s" % (el, fc, decide_ms()))
        rows.append(("drain", el, sent, fc, decide_ms(), ""))
        if fc == 0:
            break

    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["phase", "t_s", "sources_sent", "reactive_flows", "decide_ms", "install_med_ms"])
        w.writerows(rows)
    print("\nsaved -> %s" % OUT)
    print("peak install latency (last window) and the drain curve are the framework-limit evidence.")


if __name__ == "__main__":
    main()
