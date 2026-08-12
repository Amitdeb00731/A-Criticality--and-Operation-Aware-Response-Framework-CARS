#!/bin/bash
# =============================================================================
# CARS A2 — proactive default-deny forensic sweep  (run: sudo bash, on Dell#1)
# Cross-validates the PROACTIVE layer per scenario:
#   OVS flow counters (allow P60 / deny P55, kernel ground truth) | traffic outcome | CARS audit delta.
# The A2 signature: a DENIED attacker is dropped at the data plane (deny n_packets climbs) AND produces
# NO new CARS audit entry -> silent proactive prevention, no detection (vs A3's reactive detect-then-block).
# Bridge stopped for the sweep so A3 can't fire on the attacker (isolates A2).
# =============================================================================
set -u
OPR=192.168.2.31; ATK=192.168.2.66; MBPLC=192.168.2.20; PLC=192.168.2.10; HMI=192.168.2.9
API=http://10.10.10.1:8080/cars
TS=$(date +%Y%m%d_%H%M%S); OUT=$HOME/cars_forensics/a2_run_$TS
mkdir -p "$OUT"/{pcap,art}; V="$OUT/VERDICT.txt"; : > "$V"
say(){ echo "$1" | tee -a "$V"; }
pkts(){ ovs-ofctl -O OpenFlow13 dump-flows "$1" table=1 | grep -m1 "$2" | grep -oP 'n_packets=\K[0-9]+'; }
auditn(){ curl -s $API/audit | python3 -c "import json,sys;print(len(json.load(sys.stdin)['audit']))" 2>/dev/null || echo 0; }

pgrep -f mb_server.py >/dev/null || { ip netns exec mbns python3 /home/msclab/mb_server.py 192.168.2.20 & sleep 2; }
say "[*] A2 forensic sweep -> $OUT (bridge stopped: A2 isolated from A3)"
systemctl stop cars-bridge
timeout 70 tshark -i snort0 -n -f "host 192.168.2.66 or host 192.168.2.31" -w "$OUT/pcap/a2_sweep.pcap" 2>/dev/null &

say ""; say "== A2 baseline: proactive allow (P60) + default-deny (P55) flows =="
{ echo "-- ovsgw --"; ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep -E "priority=60|priority=55"
  echo "-- ovs1 --";  ovs-ofctl -O OpenFlow13 dump-flows ovs1  table=1 | grep -E "priority=60|priority=55"; } \
  | tee "$OUT/art/a2_flows.txt" | sed 's/^/    /' | tee -a "$V" >/dev/null

scn(){ # $1 label  $2 netns  $3 flowsw  $4 flowmatch  $5 kind  ...client
  local L=$1 NS=$2 SW=$3 FM=$4 KIND=$5; shift 5
  local p0=$(pkts "$SW" "$FM"); local a0=$(auditn)
  local out; out=$(ip netns exec "$NS" "$@" 2>&1 | tr '\n' ' ' | tail -c 90)
  sleep 3
  local p1=$(pkts "$SW" "$FM"); local a1=$(auditn)
  say "[$L] $KIND  flow(${FM:9:30}) n_packets ${p0:-0}->${p1:-0}  audit ${a0}->${a1}  | $out"
}
say ""; say "== scenarios (DENIED attacker must show deny-counter climb AND audit unchanged) =="
scn OP_MBPLC_ALLOW  opns  ovsgw "priority=60,tcp,nw_src=192.168.2.31" ALLOW python3 /home/msclab/mb_client.py --host $MBPLC --op read
scn ATK_MBPLC_DENY  atkns ovsgw "priority=55,ip,nw_dst=192.168.2.20"  DENY  python3 /home/msclab/mb_client.py --host $MBPLC --op write --reg 8 --val 9
scn ATK_PLC_DENY    atkns ovsgw "priority=55,ip,nw_dst=192.168.2.10"  DENY  python3 /home/msclab/s7_probe.py $PLC

say ""; say "== real HMI->PLC loop survives permanent default-deny (ovs1 allow climbs, deny stays 0) =="
l0=$(pkts ovs1 "priority=60,tcp,nw_src=192.168.2.9"); d0=$(pkts ovs1 "priority=55,ip,nw_dst=192.168.2.10"); sleep 6
l1=$(pkts ovs1 "priority=60,tcp,nw_src=192.168.2.9"); d1=$(pkts ovs1 "priority=55,ip,nw_dst=192.168.2.10")
say "    HMI-loop allow n_packets ${l0:-0}->${l1:-0} (climbing=process alive) ; PLC deny ${d0:-0}->${d1:-0} (0=loop never denied)"

curl -s $API/audit > "$OUT/art/audit.json" 2>&1
systemctl start cars-bridge
TAR=$HOME/cars_a2_forensics_${TS}.tar.gz; tar -czf "$TAR" -C "$HOME/cars_forensics" "a2_run_$TS" 2>/dev/null
say ""; say "bundle: $TAR"
echo "===== VERDICT ====="; cat "$V"
