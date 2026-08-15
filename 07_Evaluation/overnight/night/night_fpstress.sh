#!/usr/bin/env bash
# night_fpstress.sh — adversarial-benign false-positive stress. Hammer CARS with
# noisy-but-LEGITIMATE traffic and see whether anything legitimate is ever cut.
# (Closes reviewer point: 0% FP was only shown on clean traffic.)
# All traffic here is benign: legit reads from allowlisted sources at varied
# rates/offsets + broadcast/multicast storms. A false positive = any 0xca rule
# against a legitimate source, or any legit conduit removed, or the process cut.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; source "$HERE/night_lib.sh"
DUR="${FP_DUR:-300}"
CSV="$NIGHT_ROOT/logs/fpstress.csv"; [ -f "$CSV" ] || echo "ts,legit_0xca,a2_ovs1,a2_ovsgw,online,level,fp_events" > "$CSV"
LEGIT="192.168.2.31 192.168.2.45 192.168.2.55 192.168.2.30 192.168.2.9"
log "FP stress: ${DUR}s of noisy-but-legit traffic; watching for any wrongful cut"

# benign load: legit reads at varied rates + odd-but-valid offsets from allowlisted hosts
( end=$((SECONDS+DUR)); while [ $SECONDS -lt $end ]; do
    sudo ip netns exec "$NS_OP"  python3 "$S7" --host "$PLC1" --read --count 5 >/dev/null 2>&1
    sudo ip netns exec remns     python3 "$S7" --host "$PLC1" --read --count 5 >/dev/null 2>&1
    sudo ip netns exec "$NS_OP"  python3 "$MBATK" --host "$MODBUS" --fc 0x03 --count 5 >/dev/null 2>&1  # valid Modbus read
    sleep 1
  done ) &
BEN=$!
# broadcast / multicast storm from a legit-ish vantage (ARP + mDNS), bounded
sudo timeout "$DUR" ip netns exec "$NS_OP" python3 - <<'PY' 2>/dev/null &
try:
  from scapy.all import Ether,ARP,IP,UDP,sendp,conf; conf.verb=0; import time
  end=time.time()+9999
  while time.time()<end:
    sendp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(op=1,pdst="192.168.2.%d"%__import__('random').randint(1,254)),count=3)
    sendp(Ether(dst="01:00:5e:00:00:fb")/IP(dst="224.0.0.251")/UDP(dport=5353),count=2)
    time.sleep(0.2)
except Exception as e: print(e)
PY
NOISE=$!

fp_total=0; end=$((SECONDS+DUR))
while [ $SECONDS -lt $end ]; do
  sleep 20
  fp=0
  for s in $LEGIT; do n=0; for br in ovs1 ovsgw; do n=$((n+$(sudo ovs-ofctl -O OpenFlow13 dump-flows $br 2>/dev/null|grep -c "0xca.*nw_src=$s"))); done; fp=$((fp+n)); done
  a1=$(sudo ovs-ofctl -O OpenFlow13 dump-flows ovs1 2>/dev/null|grep -c 0xa2); ag=$(sudo ovs-ofctl -O OpenFlow13 dump-flows ovsgw 2>/dev/null|grep -c 0xa2)
  st=$(cat /tmp/cars_remediation_status.json 2>/dev/null)
  onl=$(echo "$st"|python3 -c 'import sys,json;print(json.load(sys.stdin).get("online"))' 2>/dev/null)
  lv=$(echo "$st"|python3 -c 'import sys,json;print(json.load(sys.stdin).get("level"))' 2>/dev/null)
  fp_total=$((fp_total+fp))
  echo "$(TS),$fp,$a1,$ag,${onl},${lv},$fp_total" >> "$CSV"
  [ "$fp" -gt 0 ] && log "  FP STRESS: $fp reactive rule(s) against a LEGIT source — investigate!"
done
sudo pkill -f "netns exec $NS_OP" 2>/dev/null; sudo pkill -f "netns exec remns" 2>/dev/null
kill "$BEN" "$NOISE" 2>/dev/null; wait 2>/dev/null; selfheal; greencheck || arm
log "FP stress done: total wrongful cuts over the window = $fp_total (expect 0)"
