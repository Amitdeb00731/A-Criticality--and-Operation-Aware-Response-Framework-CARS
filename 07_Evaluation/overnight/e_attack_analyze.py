#!/usr/bin/env python3
# Analyzer for the attack-during-armed monitor (points 9b / 7 / 10).
# Reports: was the attacker isolated? did the legit tank stay in band while it was? did legit
# throughput keep flowing? and how long until the reactive rule self-expired (return to normal)?
#
# Usage:  python3 e_attack_analyze.py results/attack/monitor.csv
import sys, csv
PATH = sys.argv[1] if len(sys.argv) > 1 else "results/attack/monitor.csv"
rows = list(csv.DictReader(open(PATH)))

def f(x):
    try: return float(x)
    except: return None

iso_rows = [r for r in rows if (r.get("atk_isolated") or "0").strip() not in ("0","")]
levels_all = [f(r["level"]) for r in rows if f(r["level"]) is not None]
levels_iso = [f(r["level"]) for r in iso_rows if f(r["level"]) is not None]

# legit throughput continuity: does the established counter keep climbing across the whole run?
est = [int(r["legit_est"]) for r in rows if (r.get("legit_est") or "").isdigit()]
legit_climbed = (len(est) >= 2 and est[-1] > est[0])

# quarantine window + observed hard_timeout
first_iso = next((i for i,r in enumerate(rows) if (r.get("atk_isolated") or "0").strip() not in ("0","")), None)
last_iso  = next((len(rows)-1-i for i,r in enumerate(reversed(rows)) if (r.get("atk_isolated") or "0").strip() not in ("0","")), None)
hto = next((r["atk_hardto"] for r in iso_rows if r.get("atk_hardto")), None)
iso_secs = (last_iso - first_iso + 1) if (first_iso is not None and last_iso is not None) else 0

print("Attack-during-armed: process safety, isolation and self-heal\n")
print("  samples: %d   isolated samples: %d" % (len(rows), len(iso_rows)))
print("  attacker isolated:            %s" % ("YES" if iso_rows else "NO (attack may not have triggered / wrong attacker IP)"))
if levels_all:
    print("  tank level over whole run:    min %.1f  max %.1f  (band excursion if <20 or >80)" % (min(levels_all), max(levels_all)))
if levels_iso:
    exc = sum(1 for x in levels_iso if x < 20 or x > 80)
    print("  tank level WHILE isolated:    min %.1f  max %.1f  excursions=%d" % (min(levels_iso), max(levels_iso), exc))
print("  legit throughput kept flowing: %s" % ("YES" if legit_climbed else "NO"))
print("  observed hard_timeout on rule: %s s" % (hto or "n/a"))
print("  attacker isolated for ~:       %d s (self-heal when this ends)" % iso_secs)
print("\nreading:")
print("  point 9b PASS if: attacker isolated, 0 excursions while isolated, legit throughput kept flowing.")
print("  point 7  PASS if: the reactive rule self-expired near its hard_timeout and level returned to normal cycling.")
print("  point 10: the install/withdraw flow snapshots are in results/attack/flows/.")
