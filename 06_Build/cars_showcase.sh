#!/bin/bash
# CARS - OPERATION-AWARE ICS GUARD : LIVE SHOWCASE v3 (real Siemens S7-1200 PLC1).  sudo bash ~/cars_showcase.sh
# ACT1 operation-awareness (read allowed / write forbidden) | ACT2 physical attack unprotected (relay clicks) |
# ACT3 arm the guard (click then silence) | ACT4 attacker locked out of everything (incl. kill-switch) | epilogue safe.
set -u
API=http://10.10.10.1:8080/cars; PLC=192.168.2.10; S7=/home/msclab/s7_write.py
defense(){ curl -s -XPOST $API/defense -H 'Content-Type: application/json' -d "{\"on\":$1}" >/dev/null; }
agrep(){ curl -s $API/audit | python3 -c "import json,sys;a=[l for l in json.load(sys.stdin)['audit'] if '$1' in l];print('        '+(a[-1] if a else '(no $1 decision seen)'))" 2>/dev/null; }
restore(){ curl -s -XPOST $API/restore -H 'Content-Type: application/json' -d '{"src":"192.168.2.31","dst":"192.168.2.10","dpid":3}' >/dev/null; }
attk(){ ip netns exec opns python3 $S7 --host $PLC "$@" 2>&1 | tail -1; }
healwait(){ for i in $(seq 1 40); do ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep -q "nw_src=192.168.2.31.*actions=drop" || return; sleep 1; done; }
loop(){ ovs-ofctl -O OpenFlow13 dump-flows ovs1 table=1 | grep 'nw_src=192.168.2.9,nw_dst=192.168.2.10' | grep -oP 'n_packets=\K[0-9]+'; }
step(){ echo; read -rp "        [ Enter to continue ] " _ || true; echo; }
line(){ echo "================================================================================"; }
clear
echo "###############################################################################"
echo "#  CARS - OPERATION-AWARE ICS GUARD  |  LIVE SHOWCASE  |  real Siemens S7-1200 #"
echo "###############################################################################"
echo "[setup] disarm, clear state, relay OFF ..."
defense false; restore; healwait; ip netns exec opns python3 $S7 --host $PLC --val 0 --count 1 >/dev/null 2>&1
L0=$(loop); echo "        control loop (HMI<->PLC S7): $L0 climbing = plant healthy"
step
line; echo " ACT 1 - CARS READS THE OPERATION, NOT THE ADDRESS   (guard ARMED)"
echo "         Same station .31, same PLC .10, same port 102 - two operations:"; line
defense true
echo "   (a) legit S7 READ:                 $(attk --read)"; sleep 3; agrep "READ =>"
echo "   (b) S7 WRITE to a physical output:  $(attk --val 0 --count 1)"; sleep 3; agrep "CONTROL =>"
echo ""; echo "   => READ ALLOWED, WRITE FORBIDDEN. A firewall sees one identical conduit;"
echo "      CARS distinguishes the ICS OPERATION."
restore; healwait; step
line; echo " ACT 2 - PHYSICAL ATTACK, UNPROTECTED   (guard DISARMED)"; line
defense false
echo "   Attacker flaps the relay.   >>> LISTEN: the relay CLICKS <<<"
timeout 6 ip netns exec opns python3 $S7 --host $PLC --flap
ip netns exec opns python3 $S7 --host $PLC --val 0 --count 1 >/dev/null 2>&1
echo "   CARS SAW it, guard OFF:"; agrep "CONTROL =>"
step
line; echo " ACT 3 - DEPLOY THE GUARD   (ARMING)"; line
defense true
echo "   Identical attack.   >>> LISTEN: one tick, then SILENCE <<<"
timeout 8 ip netns exec opns python3 $S7 --host $PLC --flap 2>/dev/null
echo "   CARS decision:"; agrep "CONTROL =>"
step
line; echo " ACT 4 - THE ATTACKER IS LOCKED OUT OF EVERYTHING"; line
echo "   Still quarantined from Act 3, the attacker escalates to the KILL-SWITCH (CPU stop):"
echo "      $(attk --stop)"
echo "   => Quarantined. The CPU-halt never even connects. Once CARS catches one dangerous"
echo "      operation the source is cut from ALL conduits (S7-STOP is itself DIAG => FORBIDDEN)."
step
line; echo " EPILOGUE - safe state"; line
echo "   [quarantine self-heals, relay reset OFF, guard re-armed...]"
defense false; restore; healwait; ip netns exec opns python3 $S7 --host $PLC --val 0 --count 1 >/dev/null 2>&1
defense true
L1=$(loop); echo "   relay OFF | guard ARMED | loop $L0 -> $L1 (plant never stopped)"
echo ""; echo "   Same attacker, same PLC. The OPERATION decided allow vs block."
echo "###############################  END SHOWCASE  ################################"
