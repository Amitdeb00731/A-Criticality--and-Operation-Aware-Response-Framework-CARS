#!/usr/bin/env python3
# Point 8 analyzer - jitter/loss on the legit HIL conduit around the Snort restart and the controller
# reconnect. Uses the HIL pcap (frame-accurate) plus the per-second timeline for event markers.
#
# Usage:  python3 p8_analyze.py results/jitter
import sys, os, csv, statistics
from scapy.all import PcapReader, IP

D = sys.argv[1] if len(sys.argv) > 1 else "results/jitter"
PCAP = os.path.join(D, "hil.pcap")
TL = os.path.join(D, "timeline.csv")

# event wall-clock times from the timeline
events = {}
rows = list(csv.DictReader(open(TL))) if os.path.exists(TL) else []
for r in rows:
    if r["event"]:
        events[r["event"]] = float(r["ts"])

# HIL frame timestamps
ts = [float(p.time) for p in PcapReader(PCAP) if IP in p]
ts.sort()
if not ts:
    sys.exit("no HIL frames in pcap")
t0, t1 = ts[0], ts[-1]
gaps = [b - a for a, b in zip(ts, ts[1:])]

def window(name, center, half=5):
    if name not in events: return None
    c = events[name]
    seg = [g for a, g in zip(ts, gaps) if center - half <= a <= center + half]
    return seg

def stats(seg):
    if not seg: return None
    return (1000*statistics.mean(seg), 1000*statistics.median(seg), 1000*max(seg))

# baseline = first 50 s (before any event)
base = [g for a, g in zip(ts, gaps) if a <= t0 + 50]
print("HIL conduit: %d frames over %.0f s\n" % (len(ts), t1 - t0))
print("%-16s %10s %10s %10s %10s" % ("window", "mean_ms", "med_ms", "maxgap_ms", "frames"))
def line(name, seg):
    s = stats(seg)
    if s: print("%-16s %10.2f %10.2f %10.1f %10d" % (name, s[0], s[1], s[2], len(seg)+1))
line("baseline", base)
for ev in ("SNORT_RESTART", "CTRL_DISCONNECT", "CTRL_RECONNECT"):
    if ev in events:
        c = events[ev]
        seg = [g for a, g in zip(ts, gaps) if c - 5 <= a <= c + 8]
        line(ev, seg)

# loss = any inter-frame gap far above baseline (HIL ~ every 7-8 ms at 129 pps)
bmean = statistics.mean(base) if base else 0.01
biggaps = [(a, g) for a, g in zip(ts, gaps) if g > max(0.2, 20*bmean)]
print("\nlarge gaps (>%.0f ms, candidate forwarding stalls/loss): %d" % (max(200, 20000*bmean), len(biggaps)))
for a, g in biggaps[:10]:
    near = min(events.items(), key=lambda kv: abs(kv[1]-a)) if events else ("-", 0)
    print("  gap %.0f ms at t+%.1fs  (near %s)" % (1000*g, a - t0, near[0]))
print("\nreading: if the reconnect/restart windows show mean/median inter-frame ~ baseline and no large")
print("gaps, the control-plane machinery does not disturb normal traffic; a cluster of large gaps at")
print("CTRL_DISCONNECT would indicate a brief forwarding stall during the outage.")
