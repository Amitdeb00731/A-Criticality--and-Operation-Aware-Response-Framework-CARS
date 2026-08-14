#!/usr/bin/env python3
# B1 analyzer - run in the analysis environment (not the rig) on the captured pcap.
# Produces the normal-traffic baseline: per-conduit packets/s (mean/median/p95) and the traffic mix.
#
# Usage:  python3 b1_analyze.py results/b1/baseline.pcap [results/b1/bridge_ops.log]
import sys, collections, statistics, re
try:
    from scapy.all import PcapReader, IP, TCP, UDP
except Exception as e:
    sys.exit("scapy required: pip install scapy --break-system-packages  (%s)" % e)

PCAP = sys.argv[1]
BRIDGE = sys.argv[2] if len(sys.argv) > 2 else None
PORTMAP = {102: "S7", 502: "Modbus", 2404: "IEC104", 44818: "EtherNetIP"}

per_sec = collections.defaultdict(collections.Counter)   # sec -> conduit -> pkts
t0 = None
def conduit(p):
    if IP not in p: return None
    ip = p[IP]
    dport = p[TCP].dport if TCP in p else (p[UDP].dport if UDP in p else 0)
    proto = PORTMAP.get(dport, "other")
    return "%s->%s/%s" % (ip.src, ip.dst, proto)

n = 0
for p in PcapReader(PCAP):
    if IP not in p: continue
    t = int(float(p.time))
    if t0 is None: t0 = t
    c = conduit(p)
    if c: per_sec[t - t0][c] += 1; n += 1

dur = (max(per_sec) + 1) if per_sec else 1
totals = collections.Counter()
series = collections.defaultdict(list)
for sec in range(dur):
    cc = per_sec.get(sec, {})
    seen = set()
    for c, k in cc.items():
        totals[c] += k; series[c].append(k); seen.add(c)
    for c in series:                       # pad conduits idle this second with 0
        if c not in seen and len(series[c]) < sec + 1:
            series[c].append(0)

def p95(s):
    s = sorted(s); return s[max(0, int(0.95 * len(s)) - 1)] if s else 0

print("B1 baseline: %d packets over %d s, %d conduits\n" % (n, dur, len(totals)))
print("%-42s %8s %9s %8s %8s" % ("conduit (src->dst/proto)", "packets", "pps_mean", "pps_med", "pps_p95"))
for c, tot in totals.most_common():
    s = series[c] + [0] * (dur - len(series[c]))
    print("%-42s %8d %9.1f %8.1f %8d" % (c, tot, tot / dur, statistics.median(s), p95(s)))

# traffic mix by protocol
mix = collections.Counter()
for c, tot in totals.items(): mix[c.split("/")[-1]] += tot
print("\ntraffic mix by protocol:")
for pr, k in mix.most_common():
    print("  %-12s %8d  (%.1f%%)" % (pr, k, 100.0 * k / max(1, n)))

# ops/s from the bridge REPORT lines, if provided
if BRIDGE:
    rates = collections.defaultdict(list)
    rx = re.compile(r"REPORT (\S+) -> (\S+).*?(\d+)/s")
    for line in open(BRIDGE, errors="ignore"):
        m = rx.search(line)
        if m: rates["%s->%s" % (m.group(1), m.group(2))].append(int(m.group(3)))
    if rates:
        print("\nops/s per conduit (from cars-bridge REPORT lines):")
        print("%-34s %7s %7s %7s" % ("conduit", "mean", "med", "max"))
        for c, v in sorted(rates.items(), key=lambda kv: -statistics.mean(kv[1])):
            print("%-34s %7.1f %7.1f %7d" % (c, statistics.mean(v), statistics.median(v), max(v)))
