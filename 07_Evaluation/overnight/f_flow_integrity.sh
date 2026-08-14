#!/usr/bin/env bash
# Point 12 - strict flow-integrity evaluation. Injects a bogus EXTRA rule many times (persistent and
# sub-poll transient) and measures the flow-integrity checker's detection rate and latency, quantifying
# the poll-window blind spot. SAFE: the bogus rule matches TEST-NET 198.51.100.99 (no real traffic).
#
# Usage:  ./f_flow_integrity.sh <trials> <persistent|transient>
#   ./f_flow_integrity.sh 30 persistent
#   ./f_flow_integrity.sh 30 transient
set -u
BR=ovsgw; FEED=/tmp/cars_flowaudit.jsonl; TESTIP=198.51.100.99
N="${1:-30}"; MODE="${2:-persistent}"
D=~/overnight_$(date +%Y%m%d)/flowint; mkdir -p "$D"; CSV="$D/${MODE}.csv"; echo "trial,detected,latency_s" > "$CSV"
inject(){ sudo ovs-ofctl -O OpenFlow13 add-flow "$BR" "table=1,priority=177,ip,nw_src=$TESTIP,actions=drop" 2>/dev/null; }
remove(){ sudo ovs-ofctl -O OpenFlow13 del-flows "$BR" "table=1,ip,nw_src=$TESTIP" 2>/dev/null; }

echo "[FLOWINT] $MODE x$N  (flow-audit poll = 10 s)"
for t in $(seq 1 "$N"); do
  remove; sleep 0.5
  base=$(wc -l < "$FEED" 2>/dev/null || echo 0)
  t0=$(date +%s.%N)
  inject
  [ "$MODE" = "transient" ] && { sleep 2; remove; }
  det=0; lat=""
  for i in $(seq 1 250); do        # watch up to 25 s
    if tail -n +$((base+1)) "$FEED" 2>/dev/null | grep -qiE "$TESTIP|EXTRA"; then
      det=1; lat=$(python3 -c "print(f'{$(date +%s.%N)-$t0:.1f}')"); break
    fi
    sleep 0.1
  done
  remove
  echo "$t,$det,${lat:-}" >> "$CSV"
  echo "  trial $t: detected=$det latency=${lat:-none}s"
  sleep 1
done
remove
python3 - "$CSV" <<'PY'
import csv,sys,statistics
r=list(csv.DictReader(open(sys.argv[1])))
det=[x for x in r if x['detected']=='1']; lat=[float(x['latency_s']) for x in det if x['latency_s']]
print("detection rate: %d/%d = %.0f%%"%(len(det),len(r),100*len(det)/max(1,len(r))))
if lat: print("detection latency (s): median %.1f mean %.1f min %.1f max %.1f"%(statistics.median(lat),statistics.mean(lat),min(lat),max(lat)))
PY
echo "[FLOWINT] done -> $CSV"
