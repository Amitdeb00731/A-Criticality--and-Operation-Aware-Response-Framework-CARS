#!/bin/bash
# =============================================================================
# CARS Phase-2b — MEAN-TIME-TO-MITIGATE (MTTM) harness.   sudo bash cars_mttm.sh [N]   (Dell#1)
# -----------------------------------------------------------------------------
# Measures the FULL autonomous reactive loop end-to-end:
#     attack-packet-on-the-wire  ->  Snort detect  ->  bridge  ->  controller decide  ->  flow installed
# MTTM = t_enforce - t_attack, both read on Dell#1's SINGLE clock (no cross-host skew):
#   t_attack  = epoch of the first attacker frame in the mirror pcap (tshark, us precision)
#   t_enforce = t_poll - flow.duration  (the enforcement flow's own age => install time, skew-free vs poll jitter)
# Target = real PLC .10 via ovsgw, which is NOT under A2 default-deny on ovsgw (that deny is ovs1-only, CC-43),
# so the REACTIVE loop is what mitigates here (not A2's proactive pre-drop). ICMP flood = harmless L3 probe;
# blocking .66->.10 never touches the HMI->PLC S7 loop (.9->.10). N trials -> mean/median/stdev/min/max.
# =============================================================================
set -u
N=${1:-15}
ATK=192.168.2.66; TGT=192.168.2.10; API=http://10.10.10.1:8080/cars
TS=$(date +%Y%m%d_%H%M%S); OUT=$HOME/cars_forensics/mttm_$TS; mkdir -p "$OUT"
CSV="$OUT/mttm.csv"; echo "trial,t_attack,t_enforce,mttm_ms,response,flow_dur_s" > "$CSV"

enforce_flow(){   # echo "<duration_s> <BLOCK|ISOLATE>" if an enforcement flow for the attacker exists, else nothing
  local line
  line=$(ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 2>/dev/null \
        | grep -m1 -E "priority=110,ip,nw_src=192.168.2.66|priority=100,ip,nw_src=192.168.2.66,nw_dst=192.168.2.10")
  [ -z "$line" ] && return
  local dur resp=BLOCK
  dur=$(echo "$line" | grep -oP 'duration=\K[0-9.]+')
  echo "$line" | grep -q "priority=110" && resp=ISOLATE
  echo "$dur $resp"
}

echo "== CARS MTTM: $N autonomous trials — attacker $ATK -> $TGT (ICMP), reactive detect->mitigate =="
systemctl is-active cars-bridge >/dev/null || { echo "cars-bridge not active — aborting"; exit 1; }

for t in $(seq 1 "$N"); do
  # clean slate for the attacker conduit
  ovs-ofctl -O OpenFlow13 del-flows ovsgw "table=1,ip,nw_src=192.168.2.66" 2>/dev/null
  curl -s -XPOST $API/restore -H 'Content-Type: application/json' -d "{\"src\":\"$ATK\",\"dst\":\"$TGT\",\"dpid\":3}" >/dev/null
  sleep 1
  PCAP="$OUT/t${t}.pcap"
  timeout 9 tshark -i snort0 -n -f "icmp and host 192.168.2.66" -w "$PCAP" 2>/dev/null & CAP=$!
  sleep 1
  ip netns exec atkns ping -i 0.05 -c 80 "$TGT" >/dev/null 2>&1 & PING=$!
  ef=""; t_poll=""
  for i in $(seq 1 400); do
    ef=$(enforce_flow)
    if [ -n "$ef" ]; then t_poll=$(date +%s.%N); break; fi
    sleep 0.02
  done
  kill $PING 2>/dev/null; wait $PING 2>/dev/null
  sleep 1; kill $CAP 2>/dev/null; wait $CAP 2>/dev/null
  if [ -z "$ef" ]; then echo "$t,NA,NA,TIMEOUT,," >> "$CSV"; echo "trial $t: TIMEOUT (no enforcement in 8s)"; continue; fi
  dur=$(echo "$ef" | awk '{print $1}'); resp=$(echo "$ef" | awk '{print $2}')
  t_attack=$(tshark -r "$PCAP" -n -Y "icmp && ip.src==192.168.2.66" -T fields -e frame.time_epoch 2>/dev/null | head -1)
  if [ -z "$t_attack" ]; then echo "$t,NA,NA,NOATTACK,$resp,$dur" >> "$CSV"; echo "trial $t: no attacker frame captured"; continue; fi
  t_enforce=$(python3 -c "print($t_poll - $dur)")
  mttm=$(python3 -c "print(round(($t_enforce - $t_attack)*1000,1))")
  echo "$t,$t_attack,$t_enforce,$mttm,$resp,$dur" >> "$CSV"
  printf "trial %2d: MTTM=%8s ms   response=%s\n" "$t" "$mttm" "$resp"
done

python3 - "$CSV" <<'PY'
import csv,sys,statistics as st
from collections import Counter
rows=[r for r in csv.DictReader(open(sys.argv[1])) if r['mttm_ms'] not in ('TIMEOUT','NOATTACK','')]
v=[float(r['mttm_ms']) for r in rows]
print("\n================  MTTM RESULTS  ================")
if v:
    print("valid trials : %d"%len(v))
    print("mean   : %.1f ms"%st.mean(v))
    print("median : %.1f ms"%st.median(v))
    print("stdev  : %.1f ms"%(st.pstdev(v) if len(v)>1 else 0))
    print("min/max: %.1f / %.1f ms"%(min(v),max(v)))
    print("response mix:",dict(Counter(r['response'] for r in rows)))
else:
    print("no valid trials")
PY
echo "csv: $CSV"
