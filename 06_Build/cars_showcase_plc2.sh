#!/bin/bash
# CARS LIVE S7 SHOWCASE — PLC2 / TB2 (Cell-2, reached cross-NAT at .3.10 from Cell-1 source .3.66).
#   sudo bash cars_showcase_plc2.sh   (Dell#1). Mirror of the PLC1 showcase on the second physical PLC.
set -u
API=http://10.10.10.1:8080/cars; PLC=192.168.3.10; S7=/home/msclab/s7_write.py
defense(){ curl -s -XPOST $API/defense -H 'Content-Type: application/json' -d "{\"on\":$1}" >/dev/null; }
agrep(){ curl -s $API/audit | python3 -c "import json,sys;a=[l for l in json.load(sys.stdin)['audit'] if '$1' in l];print('        '+(a[-1] if a else '(no $1 decision seen)'))" 2>/dev/null; }
restore(){ curl -s -XPOST $API/restore -H 'Content-Type: application/json' -d '{"src":"192.168.3.66","dst":"192.168.3.10","dpid":3}' >/dev/null; }
attk(){ python3 $S7 --host $PLC "$@" 2>&1 | tail -1; }
healwait(){ for i in $(seq 1 40); do ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep -q "nw_src=192.168.3.66.*actions=drop" || return; sleep 1; done; }
step(){ echo; read -rp "        [ Enter to continue ] " _ || true; echo; }
line(){ echo "================================================================================"; }
clear
echo "###########  CARS LIVE S7 SHOWCASE  |  PLC2 / TB2  (Cell-2, cross-NAT .3.10)  ###########"
echo "[setup] disarm, heal, relay OFF ..."
defense false; restore; healwait; python3 $S7 --host $PLC --val 0 --count 1 >/dev/null 2>&1
echo "        PLC2 relay reset OFF (Cell-1 -> .3.10 NAT -> PLC2 on ovs2/Dell#3)"
step
line; echo " ACT 1 - OPERATION-AWARE on PLC2 (guard ARMED): READ allowed vs WRITE forbidden"; line
defense true
echo "   (a) S7 READ  PLC2:   $(attk --read)"; sleep 3; agrep "READ =>"
echo "   (b) S7 WRITE PLC2:   $(attk --val 0 --count 1)"; sleep 3; agrep "CONTROL =>"
echo "   => same station/PLC/port; READ allowed, WRITE (CONTROL) forbidden - on the 2nd cell."
restore; healwait; step
line; echo " ACT 2 - PHYSICAL ATTACK on PLC2, UNPROTECTED (guard DISARMED)"; line
defense false
echo "   Attacker flaps PLC2's output.   >>> LISTEN: TB2 relay CLICKS <<<"
timeout 6 python3 $S7 --host $PLC --flap
python3 $S7 --host $PLC --val 0 --count 1 >/dev/null 2>&1
echo "   CARS saw it, guard OFF:"; agrep "CONTROL =>"
step
line; echo " ACT 3 - ARM THE GUARD: identical attack on PLC2"; line
defense true
echo "   >>> LISTEN: TB2 ticks once, then SILENCE - attacker locked out <<<"
timeout 8 python3 $S7 --host $PLC --flap 2>/dev/null
echo "   CARS decision:"; agrep "CONTROL =>"
step
line; echo " EPILOGUE - safe state"; line
defense false; restore; healwait; python3 $S7 --host $PLC --val 0 --count 1 >/dev/null 2>&1; defense true
echo "   PLC2 relay OFF | guard ARMED"
echo "   => CARS reaches, attacks, and PROTECTS the SECOND physical PLC (Cell-2, cross-NAT)"
echo "      operation-aware, exactly like PLC1."
echo "###############################  END PLC2 SHOWCASE  ###############################"
