#!/usr/bin/env python3
# Analyzer for the extended criticality judgement/behaviour run.
# Produces the judgement matrix and checks the grading patterns.
#
# Usage:  python3 c_crit_behavior_analyze.py results/critbeh/judgements.csv
import sys, csv, collections, statistics

PATH = sys.argv[1] if len(sys.argv) > 1 else "results/critbeh/judgements.csv"
rows = list(csv.DictReader(open(PATH)))
print("total judgements: %d\n" % len(rows))

# 1) timeout ladder by tier (isolate/block rules)
print("== timeout by target tier (should be 75/60/45/30) ==")
by_tier = collections.defaultdict(list)
for r in rows:
    if r["hard_timeout"]:
        by_tier[r["dst_tier"]].append(int(r["hard_timeout"]))
for tier in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
    v = by_tier.get(tier, [])
    if v:
        print("  %-9s hard_timeout: %s  (n=%d)" % (tier, sorted(set(v)), len(v)))

# 2) response by op (grading: reads vs writes/control/diag)
print("\n== response by op (across all tiers/sources) ==")
by_op = collections.defaultdict(collections.Counter)
for r in rows:
    by_op[r["op"]][r["response"]] += 1
for op in ("READ", "WRITE", "CONTROL", "DIAG"):
    if by_op[op]:
        print("  %-8s -> %s" % (op, dict(by_op[op])))

# 3) response by (tier, rate) - flood escalation
print("\n== response by tier and rate (normal=0 vs flood=12) ==")
cell = collections.defaultdict(collections.Counter)
for r in rows:
    cell[(r["dst_tier"], r["rate"])][r["response"]] += 1
for tier in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
    for rate in ("0", "12"):
        c = cell.get((tier, rate))
        if c: print("  %-9s rate=%-3s -> %s" % (tier, rate, dict(c)))

# 4) source comparison (attacker vs compromised SCADA)
print("\n== response by source ==")
by_src = collections.defaultdict(collections.Counter)
for r in rows:
    by_src[r["src"]][r["response"]] += 1
for s, c in by_src.items():
    print("  %-16s -> %s" % (s, dict(c)))

# 5) simultaneous mode - were all tiers judged concurrently with correct timeout?
print("\n== simultaneous bursts (attacker hits all tiers at once) ==")
sim = [r for r in rows if r["mode"] == "simultaneous"]
sim_tier = collections.defaultdict(list)
for r in sim:
    if r["hard_timeout"]: sim_tier[r["dst_tier"]].append(int(r["hard_timeout"]))
for tier in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
    v = sim_tier.get(tier, [])
    if v: print("  %-9s -> hard_timeout %s over %d concurrent hits" % (tier, sorted(set(v)), len(v)))
print("\nreading: the timeout must track the TARGET tier (75/60/45/30) regardless of op/source/mode;")
print("reads should be permitted where writes/control/diag are cut; flood should escalate; and")
print("simultaneous multi-tier attacks should each be judged independently and correctly.")
