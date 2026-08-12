#!/bin/bash
# A5 — RATE / BEHAVIORAL INTELLIGENCE demo (flood-aware, graded, safety-capped).   sudo bash cars_rate_demo.sh  (Dell#1)
#   ACT1 normal read      -> ALLOW           (flood detection does NOT false-trigger on normal rate)
#   ACT2 READ-FLOOD (20/s)-> THROTTLE->BLOCK (a LEGAL op abused for volumetric DoS — NEW in A5)
#   ACT3 WRITE-FLOOD(15/s)-> [FLOOD] ISOLATE (a burst of FORBIDDEN ops = active attack, quarantine now)
set -u
API=http://10.10.10.1:8080/cars; S7=/home/msclab/s7_write.py; PLC1=192.168.2.10; OPR=192.168.2.31
defense(){ curl -s -XPOST $API/defense -H 'Content-Type: application/json' -d "{\"on\":$1}" >/dev/null; }
restore(){ curl -s -XPOST $API/restore -H 'Content-Type: application/json' -d "{\"src\":\"$OPR\",\"dst\":\"$PLC1\",\"dpid\":3}" >/dev/null; }
healsrc(){ for sw in ovs1 ovsgw; do ovs-ofctl -O OpenFlow13 --strict del-flows "$sw" "table=1,priority=110,ip,nw_src=$OPR" 2>/dev/null; done; }
tailg(){ curl -s $API/audit | python3 -c "import json,sys;L=[l for l in json.load(sys.stdin)['audit'] if '$1' in l][-7:];[print('   '+l) for l in L]" 2>/dev/null; }
step(){ echo; read -rp "        [ Enter to continue ] " _ || true; echo; }
line(){ echo "--------------------------------------------------------------------------------"; }
clear
echo "###########  CARS A5 — RATE / BEHAVIORAL INTELLIGENCE (flood-aware, graded)  ###########"
echo "[setup] reset relay while DISARMED (so the reset write can't leave a block), heal, then ARM ..."
defense false; healsrc; restore; ip netns exec opns python3 $S7 --host $PLC1 --val 0 --count 1 >/dev/null 2>&1
healsrc; restore; defense true; sleep 1
step
line; echo " ACT 1 — NORMAL-rate read (baseline): one legit read is ALLOWED, no false flood"; line
healsrc; restore; sleep 1
ip netns exec opns python3 $S7 --host $PLC1 --read
sleep 3; echo "   CARS:"; tailg "READ =>"
step
line; echo " ACT 2 — READ-FLOOD: the SAME legal op at ~20/s = volumetric DoS -> graded THROTTLE then BLOCK"; line
healsrc; restore; sleep 1
echo "   firing ~20 reads/s for 16s (every single read is individually legal) ..."
timeout 18 ip netns exec opns python3 $S7 --host $PLC1 --readstorm --hz 20 --secs 16
sleep 2; echo "   CARS decisions (note [FLOOD] on a permitted op, THROTTLE -> BLOCK as it persists):"; tailg "FLOOD"
step
line; echo " ACT 3 — RECOVERY: flood stopped -> the SAME read returns to ALLOW (graded response self-heals)"; line
sleep 6                               # let the read-flood BLOCK auto-expire once the storm has ceased
healsrc; restore; sleep 1
ip netns exec opns python3 $S7 --host $PLC1 --read
sleep 3; echo "   CARS (back to ALLOW - reversible, no lasting penalty once the flood stops):"; tailg "READ =>"
step
line; echo " EPILOGUE"; line
healsrc; restore; ip netns exec opns python3 $S7 --host $PLC1 --val 0 --count 1 >/dev/null 2>&1
echo "   => CARS now decides on command RATE, not just command TYPE:"
echo "      - a flood of even LEGAL reads -> graded THROTTLE -> BLOCK, then ALLOW again when it stops (ACT 1-3);"
echo "      - a burst of FORBIDDEN writes is already cut on the FIRST packet by the reactive layer (ISOLATE, see the"
echo "        DoS demo CC-65) -> rate is redundant there; A5's added value is volumetric abuse of PERMITTED ops;"
echo "      - the CRITICAL HMI<->PLC loop is never throttled (safety cap holds even under flood)."
echo "###############################  END A5 RATE DEMO  ###############################"
