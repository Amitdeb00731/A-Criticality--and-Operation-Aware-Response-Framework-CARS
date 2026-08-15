#!/usr/bin/env bash
# night_monitor.sh — continuous traffic capture + periodic dissection. (Script 1.)
# Runs for the whole campaign in the background: rotating pcaps + a per-minute
# health/behaviour snapshot to CSV, so stability over 12-14 h is evidenced.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; source "$HERE/night_lib.sh"
DUR="${MON_DUR:-50400}"   # default 14 h
INT="${MON_INT:-60}"      # snapshot interval (s)
CSV="$NIGHT_ROOT/logs/monitor.csv"; [ -f "$CSV" ] || echo "ts,online,level,restores,ca_ovs1,ca_ovsgw,a2_ovs1,a2_ovsgw,flowaudit,cars_ms_avg,cars_ms_n" > "$CSV"
log "monitor: capturing (headers-only, rotating 1h, capped) + snapshot every ${INT}s for ${DUR}s"
# rotating hourly captures, headers only (-s 96) and at most 15 files each, so 14 h cannot fill the disk
sudo timeout "$DUR" tcpdump -i snort0 -nn -U -s 96 -G 3600 -W 15 -w "$NIGHT_ROOT/pcap/mirror_%H.pcap" 2>/dev/null &
sudo timeout "$DUR" tcpdump -i enx9c69d331d874 -nn -U -s 96 -G 3600 -W 15 -w "$NIGHT_ROOT/pcap/plc1_%H.pcap" 2>/dev/null &
end=$((SECONDS+DUR)); pcaps_killed=0
while [ $SECONDS -lt $end ]; do
  # disk guard: if free space drops below 1 GB, stop the pcaps (keep the CSV going) so nothing wedges
  freem=$(df -Pm "$NIGHT_ROOT" 2>/dev/null | awk 'NR==2{print $4}')
  if [ "${freem:-99999}" -lt 1024 ] && [ "$pcaps_killed" = 0 ]; then
    log "DISK GUARD: <1GB free, stopping pcaps; CSV snapshots continue"; sudo pkill -f "tcpdump.*$NIGHT_ROOT/pcap"; pcaps_killed=1
  fi
  st=$(cat /tmp/cars_remediation_status.json 2>/dev/null)
  online=$(echo "$st"|python3 -c 'import sys,json;print(json.load(sys.stdin).get("online"))' 2>/dev/null)
  level=$(echo "$st"|python3 -c 'import sys,json;print(json.load(sys.stdin).get("level"))' 2>/dev/null)
  restores=$(echo "$st"|python3 -c 'import sys,json;print(json.load(sys.stdin).get("restores"))' 2>/dev/null)
  c1=$(sudo ovs-ofctl -O OpenFlow13 dump-flows ovs1 2>/dev/null|grep -c 0xca)
  cg=$(sudo ovs-ofctl -O OpenFlow13 dump-flows ovsgw 2>/dev/null|grep -c 0xca)
  a1=$(sudo ovs-ofctl -O OpenFlow13 dump-flows ovs1 2>/dev/null|grep -c 0xa2)
  ag=$(sudo ovs-ofctl -O OpenFlow13 dump-flows ovsgw 2>/dev/null|grep -c 0xa2)
  fa=$(sudo python3 /home/msclab/cars_flow_audit.py --check --bridges ovs1,ovsgw 2>/dev/null|grep -oE 'CLEAN|DRIFT'|head -1)
  stj=$(curl -s -m4 "$API/cars/status")
  cavg=$(echo "$stj"|python3 -c 'import sys,json;print(json.load(sys.stdin).get("cars_ms_avg"))' 2>/dev/null)
  cn=$(echo "$stj"|python3 -c 'import sys,json;print(json.load(sys.stdin).get("cars_ms_n"))' 2>/dev/null)
  echo "$(TS),${online},${level},${restores},${c1},${cg},${a1},${ag},${fa:-NA},${cavg:-NA},${cn:-NA}" >> "$CSV"
  sleep "$INT"
done
log "monitor done"
