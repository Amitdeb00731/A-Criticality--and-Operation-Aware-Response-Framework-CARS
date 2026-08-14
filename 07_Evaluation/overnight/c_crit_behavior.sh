#!/usr/bin/env bash
# Point 6 (extended) - criticality JUDGEMENT & BEHAVIOUR under varied attacks.
# Exercises the controller's real decision+enforcement across: 2 sources (attacker .66, compromised
# SCADA .31), 4 tiers (CRITICAL/HIGH/MEDIUM/LOW), 4 ops (READ/WRITE/CONTROL/DIAG), 2 rates (normal/flood),
# in ALTERNATING (one at a time) and SIMULTANEOUS (all tiers at once) modes, over many cycles.
# Logs the judgement (decided tier, response, installed hard_timeout) each time.
# Process-safe: only attacker identities are isolated; the tank loop (.55/OB30) is untouched; rules
# are cleaned between combos and self-heal regardless.
#
# Usage:  ./c_crit_behavior.sh [cycles]     (default 20 ~ 12 min)
set -u
API=http://10.10.10.1:8080; TOK=$(cat ~/cars/api_token); BR=ovsgw
CYCLES="${1:-20}"
D=~/overnight_$(date +%Y%m%d)/critbeh; mkdir -p "$D"; CSV="$D/judgements.csv"
echo "ts,cycle,mode,src,dst,dst_tier,op,rate,decided_tier,response,hard_timeout" > "$CSV"

declare -A TIER=( [192.168.2.10]=CRITICAL [192.168.3.10]=HIGH [192.168.2.30]=MEDIUM [192.168.2.20]=LOW )
SRCS=(192.168.2.66 192.168.2.31)
DSTS=(192.168.2.10 192.168.3.10 192.168.2.30 192.168.2.20)
OPS=(READ WRITE CONTROL DIAG)
RATES=(0 12)

clean(){ for s in "${SRCS[@]}"; do sudo ovs-ofctl -O OpenFlow13 del-flows "$BR" "table=1,ip,nw_src=$s" 2>/dev/null; done; }

judge(){ # cycle src dst op rate mode
  local cyc=$1 src=$2 dst=$3 op=$4 rate=$5 mode=$6
  local r; r=$(curl -s -XPOST $API/cars/respond -H "Content-Type: application/json" -H "X-CARS-Token: $TOK" \
            -d "{\"src\":\"$src\",\"dst\":\"$dst\",\"op\":\"$op\",\"proto\":\"S7\",\"dpid\":3,\"rate\":$rate}")
  local dt rs; dt=$(echo "$r"|python3 -c "import sys,json;print(json.load(sys.stdin).get('tier'))" 2>/dev/null)
  rs=$(echo "$r"|python3 -c "import sys,json;print(json.load(sys.stdin).get('response'))" 2>/dev/null)
  sleep 0.4   # let the flow_mod land in the table before reading the installed timeout
  local hto; hto=$(sudo ovs-ofctl -O OpenFlow13 dump-flows "$BR" 2>/dev/null|grep -i 0xca|grep "nw_src=$src"|grep -oE 'hard_timeout=[0-9]+'|head -1|cut -d= -f2)
  echo "$(date +%s),$cyc,$mode,$src,$dst,${TIER[$dst]},$op,$rate,$dt,$rs,${hto:-}" >> "$CSV"
}

echo "[CRITBEH] $CYCLES cycles (alternating + simultaneous)"
for c in $(seq 1 "$CYCLES"); do
  # ALTERNATING: each source x each tier, with a random op and rate
  for src in "${SRCS[@]}"; do for dst in "${DSTS[@]}"; do
    op=${OPS[$RANDOM % ${#OPS[@]}]}; rate=${RATES[$RANDOM % ${#RATES[@]}]}
    judge "$c" "$src" "$dst" "$op" "$rate" alternating
    clean; sleep 0.25
  done; done
  # SIMULTANEOUS: attacker .66 hits all four tiers at once (concurrent)
  for dst in "${DSTS[@]}"; do judge "$c" 192.168.2.66 "$dst" CONTROL 12 simultaneous & done; wait
  sleep 0.5; clean
  echo "  cycle $c done ($(($(wc -l < "$CSV")-1)) judgements so far)"
  sleep 1
done
clean
echo "[CRITBEH] done -> $CSV ; rows: $(($(wc -l < "$CSV")-1))"
