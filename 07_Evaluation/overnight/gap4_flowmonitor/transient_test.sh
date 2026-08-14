#!/usr/bin/env bash
# Gap 4 -- event-driven transient-injection test (safe version).
# Re-runs the SAME 2 s inject-then-delete transient that the 10 s poller missed
# 25/30 times, but with the event-driven monitor running. Uses a DISTINCT cookie
# (0x0bad) so the delete is precise (cookie-scoped) and cannot touch any other
# rule. Scores detection from the monitor log (/tmp/cars_flowmon.csv).
#
# Prereq: cars_flowmonitor.py running in another terminal, writing /tmp/cars_flowmon.csv.
# Run from 07_Evaluation/overnight/. Harmless: the bogus rule targets a
# non-existent host (192.168.2.88), so no legitimate traffic ever matches it.
set -u
BR="${BR:-ovs1}"
LOG="${LOG:-/tmp/cars_flowmon.csv}"
COOKIE="0x0bad"
N="${1:-30}"
OUT="results/gap4_flowmonitor"; mkdir -p "$OUT"
CSV="$OUT/transient_eventdriven.csv"
echo "trial,injected_t,detected,detect_latency_ms" > "$CSV"
echo "== event-driven transient test: $N trials on $BR =="
for i in $(seq 1 "$N"); do
  t0=$(date +%s.%N)
  sudo ovs-ofctl -O OpenFlow13 add-flow "$BR" \
    "cookie=$COOKIE,table=1,priority=99,tcp,nw_src=192.168.2.88,nw_dst=192.168.2.10,tp_dst=502,actions=drop"
  sleep 2                                   # the 2 s transient window
  sudo ovs-ofctl -O OpenFlow13 del-flows "$BR" "cookie=$COOKIE/-1"   # precise: only our bogus rule
  # detection = a DRIFT row in the monitor log with t_event within [t0, t0+2.5]
  det=$(awk -F, -v t0="$t0" 'NR>1 && $3=="DRIFT" && $1>=t0 && $1<=t0+2.5 {print $4; exit}' "$LOG")
  if [ -n "$det" ]; then echo "$i,$t0,1,$det"; else echo "$i,$t0,0,"; fi | tee -a "$CSV"
  sleep 3                                   # settle between trials (> debounce + check time)
done
echo
echo "== summary =="
awk -F, 'NR>1{n++; if($3==1){d++; s+=$4}} END{printf "detected %d/%d", d, n; if(d)printf " | median-ish mean detect latency %.0f ms", s/d; print ""}' "$CSV"
echo "raw -> $CSV"
