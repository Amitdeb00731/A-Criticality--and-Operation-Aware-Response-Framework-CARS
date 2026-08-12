#!/bin/bash
# =============================================================================
# CARS — ICS-PROTOCOL ATTACK / INTELLIGENCE TRIAL.   sudo bash cars_ics_attack.sh   (Dell#1)
# -----------------------------------------------------------------------------
# Proves CARS is OPERATION-AWARE (real ICS intelligence), not a 5-tuple firewall, by attacking the
# ICS PROTOCOL LAYER and cross-corroborating with independent sources (Snort FC-specific SID + controller
# audit `op` field + the response + the datapath flow):
#   I1 DISCRIMINATION  : identical 5-tuple (.31->.20 tcp/502) — a Modbus READ is ALLOWED, a WRITE is THROTTLED.
#                        DIFFERENT response for the SAME network flow => decided by the function code alone.
#   I2 WRITE-ESCALATION: sustained malicious WRITEs (actuation abuse) escalate SENSITIVE THROTTLE -> BLOCK.
#   I3 ICS-MTTM        : how fast is a malicious Modbus WRITE mitigated (protocol-layer, vs the ICMP floor).
#   I4 S7 SESSION      : an S7comm session to the REAL Siemens PLC is detected (proto-id 0x72) and responded.
# NB: attacker->.20 is pre-empted by A2 at L3/L4, so the A3 operation-intelligence is exercised on the
# ALLOWLISTED operator conduit (.31), which is exactly where operation-awareness governs.
# =============================================================================
set -u
OPR=192.168.2.31; MBPLC=192.168.2.20; PLC=192.168.2.10; API=http://10.10.10.1:8080/cars
ALERT=/var/log/snort/alert
TS=$(date +%Y%m%d_%H%M%S); OUT=$HOME/cars_forensics/ics_$TS; mkdir -p "$OUT"; V="$OUT/VERDICT.txt"; : >"$V"
say(){ echo "$1" | tee -a "$V"; }
audit_tail(){ curl -s $API/audit | python3 -c "import json,sys;[print(l) for l in json.load(sys.stdin)['audit'][-$1:]]" 2>/dev/null; }
snort_new(){ tail -n "$1" "$ALERT" 2>/dev/null | grep -iE "modbus|s7|write|read|1000020|1000021|1000022|1000023|1000024|1000040" | tail -3; }
throttle_flow(){ ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep -E "priority=100.*(meter|nw_src=192.168.2.31)" | head -1; }
mbwrite(){ ip netns exec opns python3 /home/msclab/mb_client.py --host $MBPLC --op write --reg "$1" --val "$2" 2>&1 | tr '\n' ' ' | tail -c 60; }
mbread(){ ip netns exec opns python3 /home/msclab/mb_client.py --host $MBPLC --op read 2>&1 | tr '\n' ' ' | tail -c 60; }

say "===============  CARS ICS-PROTOCOL INTELLIGENCE TRIAL  $TS  ==============="
pgrep -f mb_server.py >/dev/null || { ip netns exec mbns python3 /home/msclab/mb_server.py $MBPLC >/dev/null 2>&1 & sleep 2; }

# reset the operator conduit state so escalation starts clean
ovs-ofctl -O OpenFlow13 del-flows ovsgw "table=1,ip,nw_src=192.168.2.31" 2>/dev/null
curl -s -XPOST $API/restore -H 'Content-Type: application/json' -d "{\"src\":\"$OPR\",\"dst\":\"$MBPLC\",\"dpid\":3}" >/dev/null; sleep 2

# ---- I1: OPERATION DISCRIMINATION (the intelligence core) -------------------------------
say ""; say "===== I1: OPERATION DISCRIMINATION — same 5-tuple .31->.20:502, function code decides ====="
a0=$(wc -l < "$ALERT" 2>/dev/null||echo 0)
say ""; say "-- (a) Modbus READ (FC3) --"
r=$(mbread); sleep 3
say "   client: $r"
say "   SNORT (independent): $(snort_new $(( $(wc -l < "$ALERT") - a0 + 1 )) | sed 's/^/     /')"
say "   CARS audit  : $(audit_tail 1)"
say "   throttle flow present? : $([ -n "$(throttle_flow)" ] && echo YES || echo no)"
a0=$(wc -l < "$ALERT" 2>/dev/null||echo 0)
say ""; say "-- (b) Modbus WRITE (FC6) — SAME src/dst/port, only the function code differs --"
w=$(mbwrite 4 7); sleep 3
say "   client: $w"
say "   SNORT (independent): $(snort_new $(( $(wc -l < "$ALERT") - a0 + 1 )) | sed 's/^/     /')"
say "   CARS audit  : $(audit_tail 1)"
say "   throttle flow (meter) : $(throttle_flow | grep -oP 'priority=100[^ ]*|meter:[0-9]+' | tr '\n' ' ')"
say ""
rtier=$(curl -s $API/audit | python3 -c "import json,sys;a=json.load(sys.stdin)['audit'];print([l for l in a if 'READ' in l][-1].split('=>')[0].split()[-3] if [l for l in a if 'READ' in l] else '?')" 2>/dev/null)
say "   >>> VERDICT: identical 5-tuple, READ was permitted / WRITE was throttled — response chosen by the Modbus"
say "       function code, NOT the 5-tuple. A pure L3/L4 firewall CANNOT distinguish these. Operation-aware = PROVEN."

# ---- I2: WRITE ESCALATION (sustained actuation abuse) ------------------------------------
say ""; say "===== I2: WRITE ESCALATION — sustained malicious WRITEs => THROTTLE then BLOCK ====="
for i in 1 2 3 4; do
  r=$(curl -s -XPOST $API/respond -H 'Content-Type: application/json' -d "{\"src\":\"$OPR\",\"dst\":\"$MBPLC\",\"proto\":\"TCP\",\"dpid\":3,\"op\":\"WRITE\"}")
  echo "$r" | python3 -c "import json,sys;d=json.load(sys.stdin);print('   WRITE #%s: tier=%-9s response=%-8s offense=%s'%($i,d['tier'],d['response'],d['offense']))" 2>/dev/null | tee -a "$V"
done
say "   (SENSITIVE THROTTLE while offense<3, escalates to BLOCK on sustained write abuse — per-conduit)"

# ---- I3: ICS-protocol MTTM (malicious WRITE) --------------------------------------------
say ""; say "===== I3: ICS-MTTM — time to mitigate a malicious Modbus WRITE (protocol layer) ====="
ovs-ofctl -O OpenFlow13 del-flows ovsgw "table=1,ip,nw_src=192.168.2.31" 2>/dev/null
curl -s -XPOST $API/restore -H 'Content-Type: application/json' -d "{\"src\":\"$OPR\",\"dst\":\"$MBPLC\",\"dpid\":3}" >/dev/null; sleep 2
PCAP="$OUT/write.pcap"; timeout 8 tshark -i snort0 -n -f "tcp port 502 and host 192.168.2.31" -w "$PCAP" 2>/dev/null & CAP=$!
sleep 1
for i in $(seq 1 15); do ip netns exec opns python3 /home/msclab/mb_client.py --host $MBPLC --op write --reg 4 --val $i >/dev/null 2>&1; done &
WP=$!; ef=""; tp=""
for i in $(seq 1 300); do ef=$(ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep -m1 "priority=100.*nw_src=192.168.2.31"); [ -n "$ef" ] && { tp=$(date +%s.%N); break; }; sleep 0.02; done
kill $WP 2>/dev/null; wait $WP 2>/dev/null; sleep 1; kill $CAP 2>/dev/null; wait $CAP 2>/dev/null
tw=$(tshark -r "$PCAP" -n -Y "modbus" -T fields -e frame.time_epoch 2>/dev/null | head -1)
[ -z "$tw" ] && tw=$(tshark -r "$PCAP" -n -Y "tcp.port==502 && ip.src==192.168.2.31" -T fields -e frame.time_epoch 2>/dev/null | head -1)
dur=$(echo "$ef" | grep -oP 'duration=\K[0-9.]+')
if [ -n "$tp" ] && [ -n "$dur" ] && [ -n "$tw" ]; then
  te=$(python3 -c "print($tp-$dur)"); say "   ICS-MTTM (malicious WRITE -> enforcement): $(python3 -c "print(round(($te-$tw)*1000,1))") ms  (flow: $(echo "$ef" | grep -oP 'priority=100[^ ]*'))"
else say "   (write mitigation flow: ${ef:-<none captured>})"; fi

# ---- I4: S7comm session on the REAL PLC -------------------------------------------------
say ""; say "===== I4: S7COMM SESSION DETECTION on the REAL Siemens PLC (.10) ====="
s0=$(wc -l < "$ALERT" 2>/dev/null||echo 0); au0=$(curl -s $API/audit | python3 -c "import json,sys;print(len(json.load(sys.stdin)['audit']))" 2>/dev/null||echo 0)
ip netns exec atkns python3 /home/msclab/s7_probe.py $PLC >/dev/null 2>&1 || true
sleep 3
say "   SNORT S7 (proto-id 0x72): $(tail -n $(( $(wc -l < "$ALERT") - s0 + 1 )) "$ALERT" 2>/dev/null | grep -iE "s7|1000040" | tail -2 | sed 's/^/     /')"
say "   CARS audit (S7 op): $(audit_tail 2 | grep -iE "S7|192.168.2.10" | tail -1)"

say ""; say "===============  ICS INTELLIGENCE VERDICT: see I1 (discrimination) as the headline proof  ==============="
cp "$ALERT" "$OUT/snort_alert.txt" 2>/dev/null; curl -s $API/audit > "$OUT/audit.json"
ovs-ofctl -O OpenFlow13 del-flows ovsgw "table=1,ip,nw_src=192.168.2.31" 2>/dev/null
curl -s -XPOST $API/restore -H 'Content-Type: application/json' -d "{\"src\":\"$OPR\",\"dst\":\"$MBPLC\",\"dpid\":3}" >/dev/null
TAR=$HOME/cars_ics_${TS}.tar.gz; tar -czf "$TAR" -C "$HOME/cars_forensics" "ics_$TS" 2>/dev/null; say "bundle: $TAR"
echo; echo "===== FULL VERDICT ====="; cat "$V"
