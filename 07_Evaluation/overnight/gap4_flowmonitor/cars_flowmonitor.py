#!/usr/bin/env python3
# CARS event-driven flow-integrity monitor (Gap 4 remedy) -- v2.
#
# Closes the 10-second poll blind spot in cars_flow_audit.py without changing its
# trusted verdict logic. It subscribes to OVS's Nicira flow-monitor
# (`ovs-ofctl monitor <br> watch:`), which emits an event the instant any flow is
# ADDED / MODIFIED / DELETED. On any change to the IMMUTABLE POLICY space that the
# auditor protects -- table 0 (GUARD) or table 1, and NOT a cookie-0xca reactive
# rule (an allowed live addition) -- it immediately invokes the deployed
# `cars_flow_audit.py --check`, the SAME trusted diff that the 10 s poller runs, so
# a sub-poll transient injection is confirmed and logged in milliseconds instead of
# being missed. The table-2 L2-learning churn is ignored, exactly as the auditor
# ignores it.
#
# Design: the monitor is only the TRIGGER; the authoritative verdict stays in the
# already-validated auditor (no re-implementation, no format-matching risk).
#
# Usage:
#   sudo python3 cars_flowmonitor.py \
#        --bridges ovs1,ovsgw \
#        --auditor /home/msclab/cars/cars_flow_audit.py \
#        --log /tmp/cars_flowmon.csv
#
import argparse, re, subprocess, sys, threading, time

TABLE_RE  = re.compile(r'table=(\d+)')
COOKIE_RE = re.compile(r'cookie=(0x[0-9a-fA-F]+|\d+)')
EVENT_RE  = re.compile(r'event=(ADDED|MODIFIED|DELETED)')

def canon_cookie(line):
    m = COOKIE_RE.search(line)
    if not m: return "0x0"
    c = m.group(1).lower()
    return c if c.startswith("0x") else hex(int(c))

def run_check(auditor, bridges):
    """Invoke the deployed auditor's one-shot check. Returns (verdict, raw)."""
    r = subprocess.run(["sudo", "python3", auditor, "--check", "--bridges", bridges],
                       capture_output=True, text=True)
    raw = (r.stdout + r.stderr).strip()
    verdict = "DRIFT" if ("DRIFT" in raw or r.returncode == 2) else \
              ("CLEAN" if "CLEAN" in raw else "UNKNOWN")
    return verdict, raw

class Trigger:
    def __init__(self, auditor, bridges, logf, debounce=0.15):
        self.auditor = auditor; self.bridges = bridges; self.logf = logf
        self.debounce = debounce; self.lock = threading.Lock(); self.pending = None
    def fire(self, br, line):
        t_event = time.time()
        with self.lock:
            # debounce a burst of events into one authoritative check
            if self.pending and (t_event - self.pending) < self.debounce:
                return
            self.pending = t_event
        time.sleep(self.debounce)
        verdict, raw = run_check(self.auditor, self.bridges)
        latency_ms = (time.time() - t_event) * 1000.0
        stamp = time.strftime("%H:%M:%S")
        sys.stderr.write("[flowmon] %s trigger on %s (%s) -> %s in %.0f ms\n"
                         % (stamp, br, line[:70], verdict, latency_ms))
        with open(self.logf, "a") as f:
            f.write("%.6f,%s,%s,%.1f,%s\n" % (t_event, br, verdict, latency_ms, line[:120].replace(",", " ")))
        with self.lock:
            self.pending = None

def watch(br, trig, warmup):
    p = subprocess.Popen(["ovs-ofctl", "monitor", br, "watch:"],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    sys.stderr.write("[flowmon] watching %s (tables 0,1; ignoring 0xca reactive + table 2)\n" % br)
    t_start = time.time()
    for line in p.stdout:
        line = line.strip()
        if not EVENT_RE.search(line):
            continue
        # suppress the initial table snapshot that OVS dumps on attach (warmup window)
        if time.time() - t_start < warmup:
            continue
        tm = TABLE_RE.search(line)
        if not tm or tm.group(1) not in ("0", "1"):     # ignore table 2 (L2 learn), like the auditor
            continue
        if canon_cookie(line) == "0xca":                # CARS reactive rule: allowed live addition
            continue
        trig.fire(br, line)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bridges", default="ovs1,ovsgw")
    ap.add_argument("--auditor", default="/home/msclab/cars/cars_flow_audit.py")
    ap.add_argument("--log", default="/tmp/cars_flowmon.csv")
    ap.add_argument("--warmup", type=float, default=3.0, help="ignore events for N s after attach (initial snapshot)")
    a = ap.parse_args()
    open(a.log, "w").write("t_event,bridge,verdict,latency_ms,change\n")
    trig = Trigger(a.auditor, a.bridges, a.log)
    threads = [threading.Thread(target=watch, args=(br.strip(), trig, a.warmup), daemon=True)
               for br in a.bridges.split(",")]
    for t in threads: t.start()
    sys.stderr.write("[flowmon] event-driven flow-integrity monitor up. Ctrl-C to stop.\n")
    for t in threads: t.join()

if __name__ == "__main__":
    main()
