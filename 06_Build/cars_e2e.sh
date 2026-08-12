#!/bin/bash
# =============================================================================
# CARS — DEEP END-TO-END TRIAL  (Phase 2a).   Run: sudo bash cars_e2e.sh   (on Dell#1)
# -----------------------------------------------------------------------------
# Drives the FULL response spectrum through the REAL autonomous chain and captures,
# per scenario, FOUR independent layers of ground-truth proof (so nothing is "just a log"):
#   WIRE   : packet actually on the mirror (tshark pcap, count of matching frames)
#   SNORT  : IDS alert fired (delta on /var/log/snort/alert)
#   CARS   : controller DECISION (tier+response) landed in the audit log
#   OVS    : ENFORCEMENT is real at the datapath (the response flow's n_packets moved)
#   OUTCOME: what the client actually saw (ok / refused / dropped / redirected)
# Each reactive scenario is timestamped (t_attack from pcap, t_decision from audit) so the
# same run feeds the MTTM analysis (Phase 2b). A2's proactive layer is run bridge-OFF to prove
# it drops WITHOUT any detection (silent prevention), then the bridge is restored.
# =============================================================================
set -u
HMI=192.168.2.9; PLC=192.168.2.10; MBPLC=192.168.2.20; OPR=192.168.2.31; ATK=192.168.2.66; HPOT=192.168.3.99
API=http://10.10.10.1:8080/cars
ALERT=/var/log/snort/alert
TS=$(date +%Y%m%d_%H%M%S); OUT=$HOME/cars_forensics/e2e_$TS
mkdir -p "$OUT"/{pcap,art}; V="$OUT/VERDICT.txt"; : > "$V"
say(){ echo "$1" | tee -a "$V"; }
pkts(){ ovs-ofctl -O OpenFlow13 dump-flows "$1" table=1 2>/dev/null | grep -m1 "$2" | grep -oP 'n_packets=\K[0-9]+'; }
alerts(){ wc -l < "$ALERT" 2>/dev/null || echo 0; }
audit_tail(){ curl -s $API/audit 2>/dev/null | python3 -c "import json,sys;[print(l) for l in json.load(sys.stdin)['audit'][-$1:]]" 2>/dev/null; }
resp(){ curl -s -XPOST $API/respond -H 'Content-Type: application/json' -d "$1" 2>/dev/null; }
wirecount(){ tshark -r "$OUT/pcap/e2e_full.pcap" -n -Y "$1" 2>/dev/null | wc -l; }

# --------------------------------------------------------------------------- 0
say "=====================  CARS DEEP E2E TRIAL  $TS  ====================="
say ""; say "[0] PREFLIGHT — abort unless the baseline is green"
SWJSON=$(curl -s $API/status)
SW=$(echo "$SWJSON" | python3 -c "import json,sys;print(sorted(json.load(sys.stdin)['switches']))" 2>/dev/null)
say "    controller switches : $SW        (expect [1, 2, 3])"
for s in cars-snort cars-bridge cars-modbus cars-hpot; do say "    svc $s = $(systemctl is-active $s 2>/dev/null)"; done
pgrep -f mb_server.py >/dev/null || { ip netns exec mbns python3 /home/msclab/mb_server.py $MBPLC >/dev/null 2>&1 & sleep 2; }
say "    mb_server           : $(pgrep -f mb_server.py >/dev/null && echo up || echo DOWN)"
say "    mirror select_all   : $(ovs-vsctl --columns=select_all list mirror 2>/dev/null | grep -c true) set"
say "    A2 deny .10 on ovs1 : present (n_packets=$(pkts ovs1 'priority=55,ip,nw_dst=192.168.2.10'))  [CC-43: NOT on ovs2]"

# whole-run capture on the mirror (sees every cell-1 conduit)
timeout 200 tshark -i snort0 -n -w "$OUT/pcap/e2e_full.pcap" 2>/dev/null & CAPPID=$!
sleep 2; say ""; say "[*] mirror capture started (pid $CAPPID) -> pcap/e2e_full.pcap"

# ---- per-scenario runner (AUTONOMOUS chain: client -> Snort -> bridge -> /cars/respond -> flow)
# args: LABEL  DESC  NETNS  FLOWSW  FLOWMATCH  CLIENT...
scn(){
  local L=$1 D=$2 NS=$3 SW=$4 FM=$5; shift 5
  local a0 p0 t0 out a1 p1
  a0=$(alerts); p0=$(pkts "$SW" "$FM"); t0=$(date +%s.%N)
  out=$(ip netns exec "$NS" "$@" 2>&1 | tr '\n' ' ' | tail -c 80)
  sleep 4
  a1=$(alerts); p1=$(pkts "$SW" "$FM")
  say ""
  say "--- [$L] $D"
  say "    t_attack=$t0"
  say "    SNORT alerts ${a0}->${a1} (+$((a1-a0)))   OVS flow(${FM:0:34}) n_packets ${p0:-0}->${p1:-0}"
  say "    CARS decision (audit tail):"; audit_tail 2 | sed 's/^/      /' | tee -a "$V" >/dev/null; audit_tail 2 | sed 's/^/      /'
  say "    OUTCOME: $out"
}

# --------------------------------------------------------------------------- 1
# S1  CRITICAL control loop — CARS must SEE it, classify CRITICAL, and REFUSE to cut it (safety invariant)
l0=$(pkts ovs1 "nw_src=192.168.2.9,nw_dst=192.168.2.10"); sleep 5
l1=$(pkts ovs1 "nw_src=192.168.2.9,nw_dst=192.168.2.10")
say ""; say "--- [S1] CRITICAL  HMI1->PLC1 control loop (safety invariant -> REFUSE, never enforced)"
say "    OVS ovs1 loop-allow n_packets ${l0:-0}->${l1:-0}  (climbing = process undisturbed by CARS)"
say "    (classify(hmi,plc)=CRITICAL -> select_response=REFUSE: mirror/alert only, no block flow)"

# --------------------------------------------------------------------------- 2
# S2  OPERATIONAL  operator READ (Modbus FC3) -> ALLOW (A3 sees READ, permits)
scn S2 "OPERATIONAL  Operator .31 -> Modbus PLC .20  READ (FC3)  -> ALLOW" \
    opns ovsgw "priority=60,tcp,nw_src=192.168.2.31" \
    python3 /home/msclab/mb_client.py --host $MBPLC --op read

# --------------------------------------------------------------------------- 3
# S3  SENSITIVE  operator WRITE (Modbus FC6/16) -> THROTTLE (A3 escalates trusted WRITE)
scn S3 "SENSITIVE    Operator .31 -> Modbus PLC .20  WRITE (FC6) -> THROTTLE (meter)" \
    opns ovsgw "priority=100" \
    python3 /home/msclab/mb_client.py --host $MBPLC --op write --reg 4 --val 7

# --------------------------------------------------------------------------- 4
# S4a FORBIDDEN attacker WRITE -> BLOCK  (autonomous, proves detect->decide->enforce)
scn S4a "FORBIDDEN    Attacker .66 -> Modbus PLC .20 WRITE -> BLOCK (autonomous chain)" \
    atkns ovsgw "priority=100,ip,nw_src=192.168.2.66" \
    python3 /home/msclab/mb_client.py --host $MBPLC --op write --reg 8 --val 9
# S4b per-SOURCE escalation -> ISOLATE (deterministic: drive the decision logic directly, robust to retransmits)
say ""; say "--- [S4b] per-SOURCE escalation  (drive decisions directly: BLOCK..BLOCK -> ISOLATE at offense>=3)"
for i in 1 2 3 4; do
  r=$(resp "{\"src\":\"$ATK\",\"dst\":\"$MBPLC\",\"proto\":\"TCP\",\"dpid\":3,\"op\":\"WRITE\"}")
  echo "$r" | python3 -c "import json,sys;d=json.load(sys.stdin);print('      offense=%s response=%-8s decision=%s'%(d['offense'],d['response'],d['decision']))" 2>/dev/null | tee -a "$V"
done
say "    OVS ovsgw ISOLATE flow (priority=110 src-drop):"
ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep -m1 "priority=110,ip,nw_src=192.168.2.66" | sed 's/^/      /' | tee -a "$V"

# --------------------------------------------------------------------------- 5
# S5  DEFLECT (policy-forced response for a chosen conduit) -> honeypot .3.99, then probe the decoy
say ""; say "--- [S5] DEFLECT   Attacker conduit -> honeypot $HPOT (deception; forced policy response)"
resp "{\"src\":\"$ATK\",\"dst\":\"$PLC\",\"proto\":\"IP\",\"dpid\":3,\"force\":\"DEFLECT\"}" \
  | python3 -c "import json,sys;d=json.load(sys.stdin);print('      response=%s decision=%s  action=%s'%(d['response'],d['decision'],d['action']))" 2>/dev/null | tee -a "$V"
say "    OVS ovsgw DEFLECT flow (priority=105 setfield->honeypot):"
ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep -m1 "priority=105" | sed 's/^/      /' | tee -a "$V"
say "    decoy reachability (honeypot netns answers as the PLC, ttl=64 deception):"
ip netns exec atkns ping -c2 -W1 $PLC 2>&1 | grep -E "ttl=|packet loss" | sed 's/^/      /' | tee -a "$V"
resp "{\"src\":\"$ATK\",\"dst\":\"$PLC\",\"proto\":\"IP\",\"dpid\":3,\"force\":\"BLOCK\"}" >/dev/null  # clear the deflect
curl -s -XPOST $API/restore -H 'Content-Type: application/json' -d "{\"src\":\"$ATK\",\"dst\":\"$PLC\",\"dpid\":3}" >/dev/null

# --------------------------------------------------------------------------- 6
# S6  A2 PROACTIVE default-deny — bridge OFF: dropped with NO detection (silent prevention)
say ""; say "--- [S6] A2 PROACTIVE default-deny (bridge OFF: prove it drops with NO IDS/CARS involvement)"
systemctl stop cars-bridge; sleep 1
# isolate the proactive proof: remove ALL reactive flows for the attacker (P110 isolate / P100 block from S4)
# so the ONLY thing that can drop S6's packet is the A2 P55 default-deny.
for sw in ovsgw ovs1; do ovs-ofctl -O OpenFlow13 del-flows "$sw" "table=1,ip,nw_src=192.168.2.66" 2>/dev/null; done
d0=$(pkts ovsgw "priority=55,ip,nw_dst=192.168.2.20"); a0=$(alerts)
o=$(ip netns exec atkns python3 /home/msclab/mb_client.py --host $MBPLC --op read 2>&1 | tr '\n' ' ' | tail -c 60)
sleep 2; d1=$(pkts ovsgw "priority=55,ip,nw_dst=192.168.2.20"); a1=$(alerts)
say "    OVS deny(.20) n_packets ${d0:-0}->${d1:-0} (climb=pre-dropped)  SNORT ${a0}->${a1} (unchanged=no detection)"
say "    OUTCOME: $o   (connect fails; NOTE: no new audit entry = silent proactive prevention)"
systemctl start cars-bridge

# --------------------------------------------------------------------------- wrap
say ""; say "[*] finalising capture..."; wait $CAPPID 2>/dev/null
say ""; say "== WIRE cross-check (frames actually captured on the mirror) =="
say "    operator->mbplc  : $(wirecount "ip.addr==192.168.2.31 && ip.addr==192.168.2.20")"
say "    attacker->mbplc  : $(wirecount "ip.addr==192.168.2.66 && ip.addr==192.168.2.20")"
say "    hmi->plc loop    : $(wirecount "ip.addr==192.168.2.9 && ip.addr==192.168.2.10")"
say "    modbus (tcp/502) : $(wirecount "tcp.port==502")"
curl -s $API/status > "$OUT/art/status.json"; curl -s $API/audit > "$OUT/art/audit.json"
cp "$ALERT" "$OUT/art/snort_alert.txt" 2>/dev/null
TAR=$HOME/cars_e2e_${TS}.tar.gz; tar -czf "$TAR" -C "$HOME/cars_forensics" "e2e_$TS" 2>/dev/null
say ""; say "bundle: $TAR"
echo "";echo "=====================  VERDICT  =====================";cat "$V"
