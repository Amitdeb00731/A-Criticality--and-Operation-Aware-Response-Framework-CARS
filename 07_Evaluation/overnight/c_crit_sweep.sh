#!/usr/bin/env bash
# Point 6 - criticality under attack. Fires the SAME attacker op at one asset per criticality tier
# through the controller's real decision+enforcement path, and reads back the installed reactive rule
# so the criticality-scaled response and timeout are captured directly:
#   expect the isolate/block hard_timeout to follow 30 + 15*w -> CRITICAL 75, HIGH 60, MEDIUM 45, LOW 30.
# Uses the attacker identity .66 (unregistered) so every tier yields a reactive response comparable
# across tiers. No attack packets are sent to the process; rules self-expire and are cleared each step.
#
# Usage:  ./c_crit_sweep.sh
set -u
API=http://10.10.10.1:8080; TOK=$(cat ~/cars/api_token); BR=ovsgw; SRC=192.168.2.66
D=~/overnight_$(date +%Y%m%d)/crit; mkdir -p "$D"; CSV="$D/crit.csv"
echo "tier,dst,reported_tier,response,priority,hard_timeout,actions" > "$CSV"
clear_src(){ sudo ovs-ofctl -O OpenFlow13 del-flows "$BR" "table=1,ip,nw_src=$SRC" 2>/dev/null; }

# one representative asset per tier (from the deployed CRITICALITY map)
run(){
  local tier="$1" dst="$2"
  clear_src; sleep 1
  local r rep rule pr hto act
  r=$(curl -s -XPOST $API/cars/respond -H "Content-Type: application/json" -H "X-CARS-Token: $TOK" \
        -d "{\"src\":\"$SRC\",\"dst\":\"$dst\",\"op\":\"CONTROL\",\"proto\":\"S7\",\"dpid\":3,\"rate\":0}")
  rep=$(echo "$r" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('tier'),d.get('response'))" 2>/dev/null)
  sleep 0.6
  rule=$(sudo ovs-ofctl -O OpenFlow13 dump-flows "$BR" 2>/dev/null | grep -i "0xca" | grep "nw_src=$SRC" | head -1)
  pr=$(echo "$rule"  | grep -oE 'priority=[0-9]+'     | cut -d= -f2)
  hto=$(echo "$rule" | grep -oE 'hard_timeout=[0-9]+' | cut -d= -f2)
  act=$(echo "$rule" | grep -oE 'actions=[^ ]+'       | cut -d= -f2)
  printf "  %-9s %-14s decision=%-18s rule: prio=%s hard_timeout=%s actions=%s\n" "$tier" "$dst" "$rep" "${pr:-none}" "${hto:-none}" "${act:-none}"
  echo "$tier,$dst,$rep,$pr,$hto,$act" >> "$CSV"
  clear_src
}

echo "== criticality sweep: attacker $SRC, same CONTROL op, one asset per tier =="
run CRITICAL 192.168.2.10     # PLC1
run HIGH     192.168.3.10     # PLC2   (Cell-2)
run MEDIUM   192.168.2.30     # Historian/SCADA
run LOW      192.168.2.20     # Modbus sim
clear_src
echo "done -> $CSV  (expected hard_timeout: 75/60/45/30 for CRITICAL/HIGH/MEDIUM/LOW)"
