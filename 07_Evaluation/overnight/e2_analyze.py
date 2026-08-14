#!/usr/bin/env python3
# Battery E v2 analyzer - load-controlled, outage-robust process-risk comparison.
# Segments the interleaved log into blocks (contiguous same-phase runs), measures each block's
# legitimate throughput, EXCLUDES blocks where the HIL/process clearly stalled (e.g. the Factory IO
# laptop hiccuped), then compares disarmed vs armed over the surviving, load-matched blocks.
#
# Usage:  python3 e2_analyze.py results/e2/interleaved.csv
import sys, csv, statistics

PATH = sys.argv[1] if len(sys.argv) > 1 else "results/e2/interleaved.csv"
rows = list(csv.DictReader(open(PATH)))

# --- segment into blocks on phase change ---
blocks = []           # each: {phase, levels[], est_samples[(ts,n)]}
cur = None
for r in rows:
    ph = r["phase"]
    if cur is None or ph != cur["phase"]:
        cur = {"phase": ph, "levels": [], "est": []}
        blocks.append(cur)
    try: cur["levels"].append(float(r["level"]))
    except: pass
    e = r.get("est_npkts", "")
    if e:
        try: cur["est"].append((float(r["ts"]), int(e)))
        except: pass

def block_pps(b):
    s = b["est"]
    if len(s) < 2: return None
    dn = s[-1][1] - s[0][1]; dt = s[-1][0] - s[0][0]
    return (dn / dt) if dt > 0 else None

# throughput per block; median defines "normal"; anything < 50% is a stalled/contaminated block
pps = [block_pps(b) for b in blocks]
good_pps = [p for p in pps if p is not None]
med = statistics.median(good_pps) if good_pps else 0
THRESH = 0.5 * med

kept = {"disarmed": [], "armed": []}
excluded = 0
for b, p in zip(blocks, pps):
    if p is None or (med and p < THRESH):
        excluded += 1; b["excluded"] = True
    else:
        kept[b["phase"]] += b["levels"]

print("Battery E v2 (load-controlled, outage-robust): disarmed vs armed\n")
print("blocks: %d total, %d excluded as stalled/degraded (throughput < %.0f pps = 50%% of median %.0f pps)\n"
      % (len(blocks), excluded, THRESH, med))
print("%-10s %8s %7s %7s %7s %7s %9s" % ("phase","samples","mean","std","min","max","excursn"))
for ph in ("disarmed", "armed"):
    lv = kept[ph]
    if not lv:
        print("%-10s  (no clean data)" % ph); continue
    exc = sum(1 for x in lv if x < 20 or x > 80)
    print("%-10s %8d %7.1f %7.2f %7.1f %7.1f %9d"
          % (ph, len(lv), statistics.mean(lv), statistics.pstdev(lv), min(lv), max(lv), exc))

if kept["disarmed"] and kept["armed"]:
    dm, ds = statistics.mean(kept["disarmed"]), statistics.pstdev(kept["disarmed"])
    am, as_ = statistics.mean(kept["armed"]), statistics.pstdev(kept["armed"])
    print("\nreading (clean blocks only):")
    print("  disarmed mean %.1f (sd %.2f)  vs  armed mean %.1f (sd %.2f)" % (dm, ds, am, as_))
    print("  -> if these match and excursions are 0 in both, arming does not perturb the process.")
