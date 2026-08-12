#!/bin/bash
# =============================================================================
# PD-6: CARS LIVE S7 PHYSICAL-ATTACK DEMO — real PLC1 relay on Q0.3.   sudo bash cars_s7_demo.sh   (Dell#1)
# Phase A: DISARM the guard -> attacker flaps the relay -> it CLICKS (sabotage lands).
# Phase B: ARM the guard   -> same attack -> CARS detects the S7 Write-Var (CONTROL) and drops it -> relay SILENT.
# Same attacker, same PLC, same operation: the only variable is whether CARS is armed. Audible proof of an
# operation-aware ICS guard protecting a physical process.
# =============================================================================
set -u
API=http://10.10.10.1:8080/cars; PLC=192.168.2.10
defense(){ curl -s -XPOST $API/defense -H 'Content-Type: application/json' -d "{\"on\":$1}" >/dev/null; }
armstate(){ curl -s $API/defense; }
audit(){ curl -s $API/audit | python3 -c "import json,sys;[print('      ',l) for l in json.load(sys.stdin)['audit'][-3:]]" 2>/dev/null; }
relayoff(){ ip netns exec opns python3 /home/msclab/s7_write.py --host $PLC --val 0 --count 1 >/dev/null 2>&1; }
healed(){ ! ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep -q "nw_src=192.168.2.31.*actions=drop"; }
echo "================  CARS LIVE S7 PHYSICAL ATTACK DEMO — PLC1 relay (Q0.3)  ================"
echo "[reset] disarm guard, wait for any source-isolate to self-heal, turn the relay OFF ..."
defense false
curl -s -XPOST $API/restore -H 'Content-Type: application/json' -d '{"src":"192.168.2.31","dst":"192.168.2.10","dpid":3}' >/dev/null
for i in $(seq 1 40); do healed && break; sleep 1; done
relayoff && echo "        relay OFF, guard disarmed  (defense=$(armstate))"
sleep 2
echo ""
echo ">>> PHASE A — GUARD DISARMED (as if CARS were not deployed). <<<"
echo ">>> The attacker (.31) writes the PLC output over S7. LISTEN: the relay CLICKS for ~6s. <<<"
timeout 6 ip netns exec opns python3 /home/msclab/s7_write.py --host $PLC --flap
echo "      CARS saw the operation but did NOT enforce (disarmed):"; audit
relayoff; sleep 2
echo ""
echo ">>> PHASE B — ARMING THE GUARD. Identical attack. <<<"
defense true; echo "      defense=$(armstate)"
echo ">>> LISTEN: the relay ticks ONCE (the reactive guard sees that first write), then the attacker is"
echo ">>>         quarantined and it falls SILENT — the sustained attack is stopped in milliseconds. <<<"
timeout 8 ip netns exec opns python3 /home/msclab/s7_write.py --host $PLC --flap 2>/dev/null
echo "      CARS decision (S7 Write-Var detected as CONTROL => FORBIDDEN => blocked):"; audit
echo ""
echo ">>> RESULT: same attacker, same S7 output-write. Disarmed -> the relay flaps under attacker control."
echo ">>>         Armed -> CARS detects the dangerous operation, locks the attacker out after one tick,"
echo ">>>         and the physical process is protected from sustained sabotage. <<<"
