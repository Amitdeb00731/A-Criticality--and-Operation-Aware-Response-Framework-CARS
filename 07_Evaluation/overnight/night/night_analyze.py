#!/usr/bin/env python3
# night_analyze.py — summarise the overnight campaign into the numbers the report needs.
# Usage: python3 night_analyze.py $HOME/night_YYYYMMDD
import sys, csv, statistics as st, os
root = sys.argv[1] if len(sys.argv) > 1 else "."
L = os.path.join(root, "logs")
def rd(p):
    fp = os.path.join(L, p)
    return list(csv.DictReader(open(fp))) if os.path.exists(fp) else []

def pct(v, q):
    v = sorted(v);
    return v[min(len(v)-1, int(q/100*len(v)))] if v else float('nan')

print("==================== OVERNIGHT CAMPAIGN SUMMARY ====================\n")

m = rd("mttm_all.csv")
mt = [float(r["mttm_ms"]) for r in m if r.get("mttm_ms") not in (None,"","NA")]
lk = [int(r["leaked_frames"]) for r in m if r.get("leaked_frames") not in (None,"","NA")]
enforced = sum(1 for r in m if r.get("t_enforce") not in (None,"","NA"))
print("ATTACKS & MTTM (every attack, single clock)")
print(f"  total attacks measured : {len(m)}")
print(f"  ended in enforcement   : {enforced}/{len(m)}")
if mt:
    print(f"  MTTM ms: n={len(mt)} median={st.median(mt):.1f} mean={st.mean(mt):.1f} "
          f"p95={pct(mt,95):.1f} p99={pct(mt,99):.1f} min={min(mt):.1f} max={max(mt):.1f}")
if lk:
    print(f"  leaked frames at PLC port: median={st.median(lk):.0f} max={max(lk)} "
          f"| attacks with 0 leaked = {sum(1 for x in lk if x==0)}/{len(lk)}")
# per-vector breakdown
from collections import defaultdict
byv = defaultdict(list)
for r in m:
    if r.get("mttm_ms") not in (None,"","NA"): byv[r["label"]].append(float(r["mttm_ms"]))
print("  per-vector median MTTM:")
for k in sorted(byv): print(f"    {k:16} n={len(byv[k]):4} median={st.median(byv[k]):.1f} ms")

d = rd("ddos.csv")
if d:
    pm=[float(r["probe_mttm_ms"]) for r in d if r.get("probe_mttm_ms") not in (None,"","NA")]
    ar=[float(r["alert_rate_s"]) for r in d if r.get("alert_rate_s") not in (None,"","NA")]
    print("\nDDoS-UNDER-LOAD (real Snort->bridge->controller pipeline)")
    if ar: print(f"  sustained alert rate: median={st.median(ar):.0f}/s max={max(ar):.0f}/s")
    if pm: print(f"  probe MTTM under load: median={st.median(pm):.1f} ms max={max(pm):.1f} ms (baseline single-injection ~7.6 ms)")

g = rd("gaphunt.csv")
if g:
    print("\nGAP-HUNT OUTCOMES")
    for r in g: print(f"  [{r['gap']}] {r['attempt']} -> {r['outcome']}  ({r['detail']})")

lad = rd("ladder.csv")
if lad:
    print("\nRESPONSE-LADDER COVERAGE (decision + installed rule per response)")
    for r in lad: print(f"  {r['response_tested']:9} {r['src']}->{r['dst']:14} verdict={r['verdict']:16} rule={r['rule']}")

cp = rd("controlplane.csv")
if cp:
    print("\nCONTROL-PLANE / GUARD / AUTH PROBES")
    for r in cp: print(f"  [{r['probe']}] {r['detail']} -> {r['outcome']}")

fps = rd("fpstress.csv")
if fps:
    tot = fps[-1].get("fp_events","?")
    win = [int(r["legit_0xca"]) for r in fps if r.get("legit_0xca") not in (None,"","NA")]
    print("\nADVERSARIAL-BENIGN FALSE-POSITIVE STRESS (noisy-but-legit traffic)")
    print(f"  samples: {len(fps)} | wrongful cuts against a legit source (cumulative): {tot} (expect 0)")
    if win: print(f"  per-sample legit-0xca: max={max(win)} (any >0 = a false positive to investigate)")

rem = rd("remediation.csv")
if rem:
    print("\nLAST-GOOD RESTORE TEST (bounded FDI, abort-on-excursion)")
    for r in rem:
        print(f"  restores {r['restores_before']}->{r['restores_after']} "
              f"level[before={r['level_before']} min={r['level_min']} max={r['level_max']}] "
              f"excursion={r['excursion']} -> {r['outcome']}")

mo = rd("monitor.csv")
if mo:
    onl=[r for r in mo if r.get("online")=="1"]; drift=[r for r in mo if r.get("flowaudit")=="DRIFT"]
    lv=[float(r["level"]) for r in mo if r.get("level") not in (None,"","NA")]
    print("\nSTABILITY OVER THE NIGHT")
    print(f"  snapshots: {len(mo)} | process online: {len(onl)}/{len(mo)} ({100*len(onl)/max(1,len(mo)):.1f}%)")
    if lv: print(f"  tank level over run: mean={st.mean(lv):.1f} min={min(lv):.1f} max={max(lv):.1f} (band 20-78)")
    print(f"  flow-audit DRIFT snapshots (should be 0 in steady state): {len(drift)}")
print("\n(Reconcile any shifted headline number to these fresh figures per REPORT_PLAN R10.)")
