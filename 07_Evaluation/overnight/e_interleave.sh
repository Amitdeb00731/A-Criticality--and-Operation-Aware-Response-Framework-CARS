#!/usr/bin/env bash
# Battery E v2 - LOAD-CONTROLLED process-risk test.
# Interleaves disarmed/armed in short blocks so any background-load drift affects BOTH phases
# equally, and logs the legitimate throughput inline so the two phases can be shown load-matched.
# No attack runs; this measures only whether arming perturbs normal operation.
#
# Usage:  ./e_interleave.sh <total_seconds> <block_seconds> [bridge]
#   validation:  ./e_interleave.sh 600 60      (5 disarmed + 5 armed 1-min blocks)
#   full run:    ./e_interleave.sh 7200 300     (12 disarmed + 12 armed 5-min blocks, 2 h)
set -u
TOTAL="${1:-3600}"; BLOCK="${2:-300}"; BR="${3:-ovsgw}"
TOK=$(cat ~/cars/api_token)
D=~/overnight_$(date +%Y%m%d)/e2; mkdir -p "$D"
CSV="$D/interleaved.csv"; echo "ts,phase,level,online,restores,est_npkts" > "$CSV"

arm(){ curl -s -X POST http://10.10.10.1:8080/cars/defense -H "X-CARS-Token: $TOK" -d "{\"on\":$1}" >/dev/null 2>&1; }
est(){ sudo ovs-ofctl -O OpenFlow13 dump-flows "$BR" 2>/dev/null \
        | grep -E "priority=85" | grep -oE "n_packets=[0-9]+" | head -1 | cut -d= -f2; }

echo "[E2] interleaving ${TOTAL}s in ${BLOCK}s blocks on ${BR} -> ${CSV}"
end=$((SECONDS+TOTAL)); phase="disarmed"; i=0
while [ $SECONDS -lt $end ]; do
  [ "$phase" = "disarmed" ] && arm false || arm true
  bend=$((SECONDS+BLOCK))
  while [ $SECONDS -lt $bend ] && [ $SECONDS -lt $end ]; do
    read lvl onl res < <(python3 -c 'import json;d=json.load(open("/tmp/cars_remediation_status.json"));print(d.get("level"),d.get("online"),d.get("restores"))' 2>/dev/null || echo "NA NA NA")
    ep=""; [ $((i % 15)) -eq 0 ] && ep=$(est)      # sample throughput every ~15 s (light on the switch)
    echo "$(date +%s),$phase,$lvl,$onl,$res,$ep" >> "$CSV"
    i=$((i+1)); sleep 1
  done
  [ "$phase" = "disarmed" ] && phase="armed" || phase="disarmed"
done
arm true       # leave the system ARMED
echo "[E2] done -> ${CSV} ; rows: $(( $(wc -l < "$CSV") - 1 )) ; system left ARMED"
echo "[E2] copy ~/overnight_$(date +%Y%m%d)/e2 into the repo results/ for analysis."
