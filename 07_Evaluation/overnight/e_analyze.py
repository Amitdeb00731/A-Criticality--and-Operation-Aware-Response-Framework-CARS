#!/usr/bin/env python3
# Battery E analyzer - compares the disarmed vs armed process-risk phases.
# Answers: does arming CARS change the tank-level behaviour or reduce legitimate throughput?
#
# Usage:  python3 e_analyze.py results/e
import sys, os, csv, statistics, re, glob

D = sys.argv[1] if len(sys.argv) > 1 else "results/e"

def load_levels(phase):
    path = os.path.join(D, phase + ".csv")
    if not os.path.exists(path): return None
    lv = []
    for row in csv.DictReader(open(path)):
        try: lv.append(float(row["level"]))
        except: pass
    return lv

def port_pkts(fname):
    if not os.path.exists(fname): return None
    tot = 0
    for m in re.finditer(r"(?:rx|tx) pkts=(\d+)", open(fname, errors="ignore").read()):
        tot += int(m.group(1))
    return tot

def throughput(phase):
    s = port_pkts(os.path.join(D, phase + "_ports_start.txt"))
    e = port_pkts(os.path.join(D, phase + "_ports_end.txt"))
    return (e - s) if (s is not None and e is not None) else None

print("Battery E: process-risk, disarmed vs armed\n")
hdr = "%-10s %7s %7s %7s %7s %7s %8s %9s" % ("phase","n","mean","std","min","max","range","excursn")
print(hdr)
stats = {}
for phase in ("disarmed", "armed"):
    lv = load_levels(phase)
    if not lv:
        print("%-10s  (no data)" % phase); continue
    exc = sum(1 for x in lv if x < 20 or x > 80)      # samples outside the wider guard band
    stats[phase] = (statistics.mean(lv), statistics.pstdev(lv), min(lv), max(lv))
    print("%-10s %7d %7.1f %7.2f %7.1f %7.1f %8.1f %9d" %
          (phase, len(lv), statistics.mean(lv), statistics.pstdev(lv), min(lv), max(lv), max(lv)-min(lv), exc))

print("\nlegitimate throughput over the phase (all ports, rx+tx packets):")
for phase in ("disarmed", "armed"):
    tp = throughput(phase)
    print("  %-10s %s" % (phase, ("%d packets" % tp) if tp is not None else "(no counters)"))

if "disarmed" in stats and "armed" in stats:
    dmean, dstd = stats["disarmed"][0], stats["disarmed"][1]
    amean, astd = stats["armed"][0], stats["armed"][1]
    print("\nreading:")
    print("  level band:  disarmed mean %.1f (sd %.2f)  vs  armed mean %.1f (sd %.2f)" % (dmean, dstd, amean, astd))
    print("  -> armed disturbs the process only if the band/sd differ materially or excursions appear under armed but not disarmed.")
    print("  -> the tank naturally oscillates (bang-bang 30-70), so compare the band and spread, not a flat line.")
