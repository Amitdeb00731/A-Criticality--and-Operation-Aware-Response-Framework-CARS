#!/usr/bin/env python3
"""Framework flow-table saturation test (supervisor review, point 8).

Stresses the DESIGN, not the testbed hardware, by driving the CARS enforcement layer
directly: each POST to /cars/respond carries a distinct unregistered source, which the
engine classifies FORBIDDEN and enforces as a source-scoped ISOLATE, installing one
reactive 0x00ca flow per switch. Distinct sources accumulate reactive flows so we can
see how the framework behaves as the OpenFlow table fills.

Three modes:
  ramp    [max_sources]                 post to a target and sample table growth + install
                                        latency + decide time, then watch the self-heal drain.
  sustain [secs] [threads]              post concurrently for `secs` (> 2*timeout) so the table
                                        reaches STEADY STATE: install rate balances hard_timeout
                                        expiry and the table PLATEAUS at ~rate*timeout, proving a
                                        sustained flood cannot grow it without bound.
  ceiling [secs] [threads] [cap]        crank concurrency to find the highest sustainable INJECTION
                                        RATE and the largest table it yields, watching for the first
                                        sign of degradation (install latency bend, decide spike, or
                                        the switch failing to track installs). `cap` is a safety
                                        limit on peak reactive flows so the live rig is not driven
                                        to memory exhaustion.

Safety: sources are 100.64.0.0/10 (CGN, no real host); isolates are source-scoped (they never
match a legitimate conduit) and self-heal via hard_timeout, and the switches run
fail_mode=secure, so the live process is not cut by construction. Run on Dell#1:
    sudo python3 flowtable_stress.py sustain 160 24
    sudo python3 flowtable_stress.py ceiling 120 64 120000
"""
import csv
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request

API = "http://10.10.10.1:8080"
DST = "192.168.2.10"            # CRITICAL PLC1 -> ISOLATE with the longest (75s) timeout
BR = "ovsgw"
TIMEOUT_S = 75

_lock = threading.Lock()
_counter = {"a": 64, "b": 0, "c": 0}
_sent = 0
_errors = 0
_lat = []


def next_src():
    with _lock:
        s = "100.%d.%d.%d" % (_counter["a"], _counter["b"], _counter["c"])
        _counter["c"] += 1
        if _counter["c"] > 255:
            _counter["c"] = 0; _counter["b"] += 1
        if _counter["b"] > 255:
            _counter["b"] = 0; _counter["a"] += 1
        if _counter["a"] > 127:
            _counter["a"] = 64
        return s


def post(src):
    body = json.dumps({"src": src, "dst": DST, "op": "CONTROL", "proto": "S7", "dpid": 3}).encode()
    urllib.request.urlopen(
        urllib.request.Request(API + "/cars/respond", data=body,
                               headers={"Content-Type": "application/json"}), timeout=5).read()


def reactive_count():
    try:
        out = subprocess.check_output(["ovs-ofctl", "-O", "OpenFlow13", "dump-flows", BR, "table=1"],
                                      text=True, stderr=subprocess.DEVNULL)
        return sum(1 for line in out.splitlines() if "0xca" in line)
    except Exception:
        return -1


def decide_ms():
    try:
        return json.loads(urllib.request.urlopen(API + "/cars/status", timeout=3).read()).get("cars_ms_avg")
    except Exception:
        return None


def vswitchd_rss_mb():
    try:
        pid = subprocess.check_output(["pgrep", "-x", "ovs-vswitchd"], text=True).split()[0]
        kb = int(open("/proc/%s/status" % pid).read().split("VmRSS:")[1].split()[0])
        return round(kb / 1024, 1)
    except Exception:
        return None


def med(xs):
    return round(sorted(xs)[len(xs) // 2], 2) if xs else 0.0


def worker(stop_evt, cap):
    global _sent, _errors
    while not stop_evt.is_set():
        if cap and reactive_peek() >= cap:
            time.sleep(0.2); continue
        s = next_src()
        tp = time.perf_counter()
        try:
            post(s)
            with _lock:
                _sent += 1
                _lat.append((time.perf_counter() - tp) * 1000)
                if len(_lat) > 2000:
                    del _lat[:1000]
        except Exception:
            with _lock:
                _errors += 1


_peek = {"v": 0, "t": 0.0}
def reactive_peek():
    # cheap cached flow count so every worker isn't dumping flows
    if time.time() - _peek["t"] > 1.0:
        _peek["v"] = reactive_count(); _peek["t"] = time.time()
    return _peek["v"]


def run_concurrent(secs, threads, cap, out_csv):
    global _sent
    stop_evt = threading.Event()
    ws = [threading.Thread(target=worker, args=(stop_evt, cap), daemon=True) for _ in range(threads)]
    t0 = time.time()
    for w in ws:
        w.start()
    rows = []
    base = decide_ms()
    print("baseline decide_ms=%s  reactive_flows=%d  vswitchd=%sMB" % (base, reactive_count(), vswitchd_rss_mb()))
    last_sent = 0
    last_t = t0
    ceiling = None
    while time.time() - t0 < secs:
        time.sleep(5)
        now = time.time()
        el = round(now - t0, 1)
        fc = reactive_count()
        dm = decide_ms()
        with _lock:
            sent = _sent; errs = _errors; il = med(_lat[-1000:])
        rate = round((sent - last_sent) / (now - last_t), 0)
        last_sent, last_t = sent, now
        rss = vswitchd_rss_mb()
        print("  t=%5ss  flows=%7d  rate=%6s/s  install_med_ms=%5.2f  decide_ms=%s  errs=%d  vswitchd=%sMB"
              % (el, fc, int(rate), il, dm, errs, rss))
        rows.append((el, fc, int(rate), il, dm, errs, rss))
        if dm and base and dm > max(3.0, base * 100):
            ceiling = ("decide_spike", fc, dm); break
        if il > 25.0:
            ceiling = ("install_latency_bend", fc, il); break
        if errs > 50:
            ceiling = ("install_errors", fc, errs); break
        if cap and fc >= cap:
            ceiling = ("safety_cap_reached", fc, cap); break
    stop_evt.set()
    for w in ws:
        w.join(timeout=1)
    print("posting stopped. ceiling=%s  peak_flows=%d" % (ceiling, reactive_count()))

    print("== drain (self-heal) ==")
    dt0 = time.time()
    while time.time() - dt0 < TIMEOUT_S + 60:
        time.sleep(5)
        fc = reactive_count()
        el = round(time.time() - t0, 1)
        print("  drain t=%5ss  flows=%7d" % (el, fc))
        rows.append((el, fc, 0, 0, decide_ms(), _errors, vswitchd_rss_mb()))
        if fc == 0:
            break
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "reactive_flows", "inject_rate_s", "install_med_ms", "decide_ms", "errors", "vswitchd_mb"])
        w.writerows(rows)
    print("saved -> %s" % out_csv)
    return ceiling


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "ramp"
    ts = time.strftime("%Y%m%d_%H%M%S")
    if mode == "sustain":
        secs = int(sys.argv[2]) if len(sys.argv) > 2 else 160
        threads = int(sys.argv[3]) if len(sys.argv) > 3 else 24
        out = os.path.expanduser("~/flowtable_sustain_%s.csv" % ts)
        print("== SUSTAIN: %d threads for %ss -> plateau at ~rate*%ds ==" % (threads, secs, TIMEOUT_S))
        run_concurrent(secs, threads, None, out)
    elif mode == "ceiling":
        secs = int(sys.argv[2]) if len(sys.argv) > 2 else 120
        threads = int(sys.argv[3]) if len(sys.argv) > 3 else 64
        cap = int(sys.argv[4]) if len(sys.argv) > 4 else 120000
        out = os.path.expanduser("~/flowtable_ceiling_%s.csv" % ts)
        print("== CEILING: %d threads for %ss, safety cap %d flows ==" % (threads, secs, cap))
        run_concurrent(secs, threads, cap, out)
    else:
        # original single-threaded ramp to a target (kept for reference)
        os.system("echo use: sustain|ceiling ; running default ramp 20000")
        run_concurrent(60, 8, 20000, os.path.expanduser("~/flowtable_ramp_%s.csv" % ts))


if __name__ == "__main__":
    main()
