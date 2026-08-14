#!/usr/bin/env bash
# B2 - MTTM stage-decomposition harness (points 3/4/5).
# Reproduces the reactive loop behind Figure 4.9 (attacker .66 ICMP -> PLC1) and captures the
# per-stage timestamps so the reaction window can be split into DETECTION (wire->Snort alert)
# and RESPONSE PLUMBING (alert->bridge->controller->flow install), explaining the distribution shape.
# Fires only a bounded ICMP probe from the attacker namespace; installs nothing itself.
#
# Usage:  ./b2_mttm_decomp.sh [N]     (validation: ./b2_mttm_decomp.sh 5 ; full: ./b2_mttm_decomp.sh 100)
set -u
N="${1:-30}"; ATK=192.168.2.66; TGT=192.168.2.10; NS=atkns; BR=ovsgw; ALERT=/var/log/snort/alert
API=http://10.10.10.1:8080/cars
D=~/overnight_$(date +%Y%m%d)/b2; mkdir -p "$D/pcap" "$D/alert"
CSV="$D/mttm_decomp.csv"; echo "trial,t_enforce,flow_dur,hard_to" > "$CSV"

TOK=$(cat ~/cars/api_token 2>/dev/null)
restore(){ sudo ovs-ofctl -O OpenFlow13 del-flows "$BR" "table=1,ip,nw_src=$ATK" 2>/dev/null
           curl -s -XPOST $API/restore -H "Content-Type: application/json" -H "X-CARS-Token: $TOK" -d "{\"src\":\"$ATK\",\"dst\":\"$TGT\",\"dpid\":3}" >/dev/null 2>&1; }

echo "[B2] $N trials, $ATK -> $TGT (ICMP), decomposing the reaction window"
for t in $(seq 1 "$N"); do
  restore; sleep 1.5
  off=$(sudo bash -c "wc -l < '$ALERT'" 2>/dev/null || echo 0)
  sudo timeout 9 tcpdump -i snort0 -nn -tt -s96 -U "icmp and host $ATK" -w "$D/pcap/t${t}.pcap" 2>/dev/null & CAP=$!
  sleep 0.3
  sudo ip netns exec "$NS" ping -i 0.05 -c 120 "$TGT" >/dev/null 2>&1 & PING=$!
  te=""; dur=""; hto=""
  for i in $(seq 1 450); do
    line=$(sudo ovs-ofctl -O OpenFlow13 dump-flows "$BR" 2>/dev/null | grep -m1 -E "0xca.*nw_src=$ATK")
    if [ -n "$line" ]; then
      tp=$(date +%s.%N)
      dur=$(echo "$line" | grep -oE "duration=[0-9.]+"   | cut -d= -f2)
      hto=$(echo "$line" | grep -oE "hard_timeout=[0-9]+" | cut -d= -f2)
      te=$(python3 -c "print(f'{$tp - $dur:.6f}')" 2>/dev/null)
      break
    fi
    sleep 0.02
  done
  sleep 0.4; kill "$PING" 2>/dev/null; sleep 0.4; kill "$CAP" 2>/dev/null; wait 2>/dev/null
  sudo bash -c "tail -n +$((off+1)) '$ALERT'" 2>/dev/null > "$D/alert/t${t}.txt"
  echo "$t,$te,$dur,$hto" >> "$CSV"
  echo "  trial $t: t_enforce=$te dur=$dur hto=$hto"
  sleep 3.5    # allow self-heal + bridge cooldown to reset between trials
done
restore
echo "[B2] done -> $D ; copy into repo results/ for analysis."
