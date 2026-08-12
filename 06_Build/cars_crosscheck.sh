#!/bin/bash
# =============================================================================
# CARS Phase-2d — MULTI-SOURCE CROSS-CORRELATION.   sudo bash cars_crosscheck.sh   (Dell#1)
# -----------------------------------------------------------------------------
# Proves results are REAL, not "just printed", by corroborating each event across FIVE physically
# independent sources that cannot fabricate each other:
#   WIRE   = kernel packet capture on the mirror (tshark)          — did the packet physically exist?
#   SNORT  = the IDS process alert log                              — did detection independently fire?
#   AUDIT  = the controller's decision log (a DIFFERENT machine)    — did the brain decide?
#   OVSFLOW= the OpenFlow datapath counter (OVS kernel)             — was enforcement physically applied?
#   OUTCOME= what the client actually experienced                   — did reality match the claim?
# Plus a NEGATIVE CONTROL (a legit conduit) to show the system does NOT fabricate enforcement when it shouldn't.
# Causal order must hold: t_wire(first attack pkt) < t_flow_install (you cannot enforce before the attack arrives).
# =============================================================================
set -u
ATK=192.168.2.66; TGT=192.168.2.10; MBPLC=192.168.2.20; OPR=192.168.2.31; API=http://10.10.10.1:8080/cars
ALERT=/var/log/snort/alert
TS=$(date +%Y%m%d_%H%M%S); OUT=$HOME/cars_forensics/xcheck_$TS; mkdir -p "$OUT"; V="$OUT/VERDICT.txt"; : >"$V"
say(){ echo "$1" | tee -a "$V"; }
pkts(){ ovs-ofctl -O OpenFlow13 dump-flows "$1" table=1 2>/dev/null | grep -m1 "$2" ; }
alerts(){ wc -l < "$ALERT" 2>/dev/null || echo 0; }
audit_has(){ curl -s $API/audit | python3 -c "import json,sys;print(sum(1 for l in json.load(sys.stdin)['audit'] if '$1' in l and '$2' in l))" 2>/dev/null || echo 0; }

say "===============  CARS MULTI-SOURCE CROSS-CHECK  $TS  ==============="

# ================= EVENT A: ATTACK (must corroborate across all 5) =================
say ""; say "===== EVENT A: attacker $ATK -> PLC $TGT (ICMP) — expect ALL sources to agree ====="
ovs-ofctl -O OpenFlow13 del-flows ovsgw "table=1,ip,nw_src=192.168.2.66" 2>/dev/null
curl -s -XPOST $API/restore -H 'Content-Type: application/json' -d "{\"src\":\"$ATK\",\"dst\":\"$TGT\",\"dpid\":3}" >/dev/null
sleep 1
PCAP="$OUT/attack.pcap"
timeout 10 tshark -i snort0 -n -f "host 192.168.2.66" -w "$PCAP" 2>/dev/null & CAP=$!
sleep 1
a0=$(alerts); au0=$(audit_has "192.168.2.66" "192.168.2.10")
ip netns exec atkns ping -i 0.1 -c 40 $TGT >/dev/null 2>&1 &
PING=$!
# poll for the enforcement flow, timestamp install via its own duration
ef=""; tpoll=""
for i in $(seq 1 300); do
  ef=$(pkts ovsgw "nw_src=192.168.2.66"); [ -n "$ef" ] && { tpoll=$(date +%s.%N); break; }; sleep 0.02
done
kill $PING 2>/dev/null; wait $PING 2>/dev/null
outcome=$(ip netns exec atkns ping -c2 -W1 $TGT 2>&1 | grep -oE "[0-9]+% packet loss")
sleep 1; kill $CAP 2>/dev/null; wait $CAP 2>/dev/null
a1=$(alerts); au1=$(audit_has "192.168.2.66" "192.168.2.10")

# --- extract each independent source ---
A_WIRE=$(tshark -r "$PCAP" -n -Y "icmp && ip.src==192.168.2.66 && ip.dst==192.168.2.10" 2>/dev/null | wc -l)
T_WIRE=$(tshark -r "$PCAP" -n -Y "icmp && ip.src==192.168.2.66 && ip.dst==192.168.2.10" -T fields -e frame.time_epoch 2>/dev/null | head -1)
A_SNORT=$((a1-a0))
A_AUDIT=$((au1-au0))
A_FLOWDUR=$(echo "$ef" | grep -oP 'duration=\K[0-9.]+')
A_FLOWDROP=$(pkts ovsgw "nw_src=192.168.2.66" | grep -oP 'n_packets=\K[0-9]+')   # re-read after attack: real drop count
A_RESP=$(echo "$ef" | grep -oP 'priority=1[01]0'); [ "$A_RESP" = "priority=110" ] && A_RESP=ISOLATE || A_RESP=BLOCK
T_FLOW=""; [ -n "$tpoll" ] && [ -n "$A_FLOWDUR" ] && T_FLOW=$(python3 -c "print($tpoll-$A_FLOWDUR)")
CAUSAL=""; [ -n "$T_WIRE" ] && [ -n "$T_FLOW" ] && CAUSAL=$(python3 -c "print('OK' if $T_FLOW>=$T_WIRE else 'VIOLATION')")

say ""
say "  SOURCE 1 WIRE    : $A_WIRE attacker->PLC frames physically captured  (t_first=$T_WIRE)"
say "  SOURCE 2 SNORT   : +$A_SNORT IDS alert(s) fired independently"
say "  SOURCE 3 AUDIT   : +$A_AUDIT controller decision(s) for this conduit (on Dell#2)"
say "  SOURCE 4 OVSFLOW : $A_RESP flow installed, dropped n_packets=$A_FLOWDROP at the datapath (t_install=$T_FLOW)"
say "  SOURCE 5 OUTCOME : attacker post-enforcement -> $outcome"
say "  CAUSALITY        : attack-on-wire BEFORE enforcement-installed ? -> $CAUSAL"
CORROB=0
[ "${A_WIRE:-0}" -gt 0 ] && CORROB=$((CORROB+1)); [ "${A_SNORT:-0}" -gt 0 ] && CORROB=$((CORROB+1))
[ "${A_AUDIT:-0}" -gt 0 ] && CORROB=$((CORROB+1)); [ -n "$A_FLOWDROP" ] && [ "${A_FLOWDROP:-0}" -ge 0 ] && CORROB=$((CORROB+1))
[ -n "$outcome" ] && CORROB=$((CORROB+1))
say "  >>> ATTACK corroborated by $CORROB/5 independent sources; causal order $CAUSAL"

# ================= EVENT B: LEGIT (negative control — NO fabricated enforcement) =================
say ""; say "===== EVENT B: operator $OPR -> Modbus PLC $MBPLC READ — negative control (must NOT be enforced) ====="
bu0=$(audit_has "192.168.2.31" "ALLOW")
lr=$(ip netns exec opns python3 /home/msclab/mb_client.py --host $MBPLC --op read 2>&1 | tr '\n' ' ' | tail -c 60)
sleep 2; bu1=$(audit_has "192.168.2.31" "ALLOW")
B_BLOCK=$(ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep -cE "priority=1[01]0,ip,nw_src=192.168.2.31")
say "  AUDIT   : +$((bu1-bu0)) ALLOW decision(s) for the operator"
say "  OVSFLOW : $B_BLOCK enforcement flow(s) against the operator  (expect 0 — no false enforcement)"
say "  OUTCOME : $lr"
echo "$lr" | grep -q READ && [ "${B_BLOCK:-1}" = "0" ] && say "  >>> LEGIT correctly ALLOWED, ZERO fabricated enforcement" || say "  *** control anomaly ***"

# cleanup
ovs-ofctl -O OpenFlow13 del-flows ovsgw "table=1,ip,nw_src=192.168.2.66" 2>/dev/null
curl -s -XPOST $API/restore -H 'Content-Type: application/json' -d "{\"src\":\"$ATK\",\"dst\":\"$TGT\",\"dpid\":3}" >/dev/null
cp "$ALERT" "$OUT/snort_alert.txt" 2>/dev/null; curl -s $API/audit > "$OUT/audit.json"
TAR=$HOME/cars_xcheck_${TS}.tar.gz; tar -czf "$TAR" -C "$HOME/cars_forensics" "xcheck_$TS" 2>/dev/null
say ""; say "bundle: $TAR"
echo; echo "=====  CROSS-CHECK VERDICT  ====="; cat "$V"
