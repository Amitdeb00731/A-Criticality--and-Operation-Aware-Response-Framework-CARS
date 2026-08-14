#!/usr/bin/env bash
# B3 - MTTM vs background detection load (point 4).
# Adds benign Modbus reads to the LOW asset .20 (allowlisted .31->.20, throttled not blocked) as W
# background workers, MEASURES the actual alert rate achieved, then runs N MTTM trials. Run at a few
# W levels to build an MTTM-vs-(measured)-load curve. Safe: LOW test asset, reads only, no process impact.
#
# Usage:  ./b3_load_sweep.sh <workers> <trials>
#   ./b3_load_sweep.sh 0 40     (baseline: HIL only)
#   ./b3_load_sweep.sh 4 40     (+4 read workers)
#   ./b3_load_sweep.sh 10 40    (+10 read workers)
set -u
W="${1:-0}"; N="${2:-40}"; ATK=192.168.2.66; TGT=192.168.2.10; NS=atkns; BR=ovsgw; ALERT=/var/log/snort/alert
TOK=$(cat ~/cars/api_token 2>/dev/null)
D=~/overnight_$(date +%Y%m%d)/b3; mkdir -p "$D/pcap_w$W"
CSV="$D/mttm_w$W.csv"; echo "trial,t_enforce,flow_dur" > "$CSV"
restore(){ sudo ovs-ofctl -O OpenFlow13 del-flows "$BR" "table=1,ip,nw_src=$ATK" 2>/dev/null; }
# NOTE: restore is del-flows ONLY (like the validated B2 harness). The authenticated /cars/restore
# path (unblock_conduit) grants a brief post-restore recovery grace that inflates back-to-back MTTM
# trials to ~0.7 s - correct product behaviour, wrong for this measurement.

PIDS=()
for i in $(seq 1 "$W"); do
  ( while true; do sudo ip netns exec opns python3 /home/msclab/mb_client.py --host 192.168.2.20 --op read --reg 0 >/dev/null 2>&1; done ) & PIDS+=($!)
done
sleep 5
# measure the ACTUAL background alert rate over 10 s (the true x-axis for this level)
a0=$(sudo bash -c "wc -l < '$ALERT'" 2>/dev/null || echo 0); sleep 10; a1=$(sudo bash -c "wc -l < '$ALERT'" 2>/dev/null || echo 0)
RATE=$(python3 -c "print(f'{($a1-$a0)/10.0:.1f}')"); echo "$RATE" > "$D/rate_w$W.txt"
echo "[B3 w=$W] measured background alert rate = ${RATE}/s"

for t in $(seq 1 "$N"); do
  restore; sleep 1.2
  sudo timeout 9 tcpdump -i snort0 -nn -tt -s96 -U "icmp and host $ATK" -w "$D/pcap_w$W/t${t}.pcap" 2>/dev/null & CAP=$!
  sleep 0.3
  sudo ip netns exec "$NS" ping -i 0.05 -c 120 "$TGT" >/dev/null 2>&1 & PING=$!
  te=""; dur=""
  for i in $(seq 1 450); do
    line=$(sudo ovs-ofctl -O OpenFlow13 dump-flows "$BR" 2>/dev/null | grep -m1 -E "0xca.*nw_src=$ATK")
    if [ -n "$line" ]; then tp=$(date +%s.%N); dur=$(echo "$line"|grep -oE 'duration=[0-9.]+'|cut -d= -f2)
      te=$(python3 -c "print(f'{$tp-$dur:.6f}')"); break; fi
    sleep 0.02
  done
  sleep 0.4; kill "$PING" 2>/dev/null; sleep 0.3; kill "$CAP" 2>/dev/null; wait 2>/dev/null
  echo "$t,$te,$dur" >> "$CSV"
  sleep 4    # MUST exceed COOLDOWN=3s so each trial's bridge dedup resets (else MTTM is inflated to ~0.7s)
done

for p in "${PIDS[@]}"; do kill "$p" 2>/dev/null; done; sudo pkill -f mb_client.py 2>/dev/null
restore
echo "[B3 w=$W] done: rate=${RATE}/s, $N trials -> $CSV ; leave system green."
