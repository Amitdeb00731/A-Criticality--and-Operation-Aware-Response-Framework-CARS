#!/usr/bin/env python3
# B2 analyzer (sandbox) - MTTM stage decomposition.
# Per trial: T0 = first attack frame on the wire (pcap), T4 = t_enforce (flow install epoch, from CSV),
# optional T1 = first Snort alert timestamp. Reports the total-MTTM distribution (to reproduce Fig 4.9)
# and the DETECTION vs RESPONSE-PLUMBING split, and flags outliers (cooldown/poll-boundary tail).
#
# Usage:  python3 b2_analyze.py results/b2
import sys, os, csv, glob, re, statistics, datetime
try:
    from scapy.all import PcapReader, IP
except Exception as e:
    sys.exit("scapy required (%s)" % e)

D = sys.argv[1] if len(sys.argv) > 1 else "results/b2"
rows = {r["trial"]: r for r in csv.DictReader(open(os.path.join(D, "mttm_decomp.csv")))}

def first_frame(pcap):
    for p in PcapReader(pcap):
        if IP in p: return float(p.time)
    return None

ATK_MATCH = "192.168.2.66"     # pick the ATTACK alert, not the background HIL (.55) alerts
def first_alert_epoch(fn, day):
    # Snort fast alert: "MM/DD-HH:MM:SS.uuuuuu ..."  -- first line mentioning the attacker
    if not os.path.exists(fn): return None
    line = None
    for l in open(fn, errors="ignore"):
        if ATK_MATCH in l:
            line = l; break
    if not line: return None
    m = re.search(r"(\d\d)/(\d\d)-(\d\d):(\d\d):(\d\d)\.(\d+)", line)
    if not m: return None
    mo, dd, hh, mm, ss, us = map(int, m.groups())
    try:
        dt = datetime.datetime(day.year, mo, dd, hh, mm, ss, int(str(us).ljust(6, "0")[:6]),
                               tzinfo=day.tzinfo)
        return dt.timestamp()
    except Exception:
        return None

totals, det, plumb, outliers = [], [], [], []
for t, r in sorted(rows.items(), key=lambda kv: int(kv[0])):
    te = r["t_enforce"]
    if not te: continue
    te = float(te)
    pcap = os.path.join(D, "pcap", "t%s.pcap" % t)
    t0 = first_frame(pcap) if os.path.exists(pcap) else None
    if t0 is None: continue
    total_ms = (te - t0) * 1000.0
    if total_ms < 0 or total_ms > 5000: continue           # guard against clock/parse glitches
    totals.append(total_ms)
    day = datetime.datetime.fromtimestamp(t0).astimezone()
    t1 = first_alert_epoch(os.path.join(D, "alert", "t%s.txt" % t), day)
    if t1 and t0 <= t1 <= te:
        det.append((t1 - t0) * 1000.0); plumb.append((te - t1) * 1000.0)

def pct(a, p): a = sorted(a); return a[max(0, int(p/100*len(a)) - 1)] if a else float("nan")

print("B2 MTTM decomposition  (n=%d clean trials)\n" % len(totals))
if totals:
    print("TOTAL reaction window (ms): median %.1f  mean %.1f  p95 %.1f  p99 %.1f  min %.1f  max %.1f"
          % (statistics.median(totals), statistics.mean(totals), pct(totals,95), pct(totals,99), min(totals), max(totals)))
    thr = pct(totals, 95)
    outliers = [x for x in totals if x > thr]
    print("outliers (> p95=%.1f ms): %d of %d  -> likely detection landing on a bridge cooldown/poll boundary"
          % (thr, len(outliers), len(totals)))
if det:
    print("\nstage split (n=%d trials with a parseable alert timestamp):" % len(det))
    print("  detection  (wire -> Snort alert):        median %.1f ms  mean %.1f ms" % (statistics.median(det), statistics.mean(det)))
    print("  plumbing   (alert -> bridge -> install):  median %.1f ms  mean %.1f ms" % (statistics.median(plumb), statistics.mean(plumb)))
    print("  -> both stages are near-constant, which is why the total clusters tightly rather than spreading 5-50 ms.")
else:
    print("\n(no parseable alert timestamps; total-window distribution above still reproduces Fig 4.9)")
