#!/usr/bin/env bash
# Point 8 - discovery/reconnection jitter on NORMAL traffic.
# While the legit HIL conduit (.55<->PLC1) runs, it (1) restarts Snort (passive DPI re-attach) and
# (2) briefly bounces the ovsgw controller connection (switch<->controller reconnect + rediscovery),
# capturing the HIL packets so we can measure jitter/loss on legit traffic and whether the data plane
# keeps forwarding during the controller outage.
#
# NOTE: step 2 disconnects the controller from ovsgw for ~20 s. The data plane should keep forwarding
# (installed flows persist / fail-open), but proactive rule *updates* pause during the gap. It is brief
# and recovers on reconnect; re-baseline flow-audit and green-check afterwards.
#
# Usage:  ./p8_jitter.sh [seconds]     (default 240)
set -u
BR=ovsgw; DUR="${1:-240}"; MIRROR=snort0; HIL=192.168.2.55
D=~/overnight_$(date +%Y%m%d)/jitter; mkdir -p "$D"; CSV="$D/timeline.csv"
echo "ts,rel,level,legit_pps,ca,event" > "$CSV"
CTRL=$(sudo ovs-vsctl get-controller "$BR" 2>/dev/null | head -1); echo "[P8] controller target: ${CTRL:-unknown}"
[ -z "$CTRL" ] && { echo "[P8] could not read controller target; aborting"; exit 1; }

sudo timeout $((DUR+5)) tcpdump -i "$MIRROR" -nn -tt -s64 -U "host $HIL" -w "$D/hil.pcap" 2>/dev/null & CAP=$!
sleep 1
est(){ sudo ovs-ofctl -O OpenFlow13 dump-flows "$BR" 2>/dev/null | grep -E "priority=85" | grep -oE "n_packets=[0-9]+" | head -1 | cut -d= -f2; }
prev=$(est); start=$SECONDS
echo "[P8] monitoring ${DUR}s; events at t=60 (Snort), t=150 (disconnect), t=170 (reconnect)"
while [ $((SECONDS-start)) -lt "$DUR" ]; do
  t=$((SECONDS-start)); event=""
  case $t in
    60)  echo "[P8] t=60  restart Snort";          sudo systemctl restart cars-snort;        event="SNORT_RESTART";;
    150) echo "[P8] t=150 disconnect controller";  sudo ovs-vsctl del-controller "$BR";       event="CTRL_DISCONNECT";;
    170) echo "[P8] t=170 reconnect controller";   sudo ovs-vsctl set-controller "$BR" "$CTRL"; event="CTRL_RECONNECT";;
  esac
  now=$(est); pps=$(( ${now:-0} - ${prev:-0} )); prev=${now:-$prev}
  lvl=$(python3 -c 'import json;print(json.load(open("/tmp/cars_remediation_status.json")).get("level"))' 2>/dev/null)
  ca=$(sudo ovs-ofctl -O OpenFlow13 dump-flows "$BR" 2>/dev/null | grep -ci 0xca)
  echo "$(date +%s),$t,${lvl},${pps},${ca},${event}" >> "$CSV"
  sleep 1
done
kill "$CAP" 2>/dev/null; wait 2>/dev/null
echo "[P8] done -> $D"
echo "[P8] now: sudo python3 ~/cars/cars_flow_audit.py --baseline --bridges ovs1,ovsgw   (re-baseline), then ./green_check.sh"
