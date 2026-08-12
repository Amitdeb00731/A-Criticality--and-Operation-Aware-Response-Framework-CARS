#!/bin/bash
# cars_packet_proof.sh - WIRE-LEVEL proof of CARS operation-awareness + real datapath enforcement.
# Two synchronised capture points, S7 dissected on the wire (no logs, no inference):
#   MIRROR  (snort0)            = what the DPI actually sees  (S7 function codes on the wire)
#   PLC1PORT(enx9c69d331d874)   = what actually REACHES PLC1  (proves drop vs pass)
# Attacker = .2.31 (opns netns). READ(allow) + WRITE(control) ARMED, then WRITE DISARMED.
# Open the pcaps in Wireshark for deep inspection; the tshark summary below is a grounded pre-view.
set -u
API=http://10.10.10.1:8080/cars; TOKEN="$(cat ~/cars/api_token 2>/dev/null)"
S7=/home/msclab/s7_write.py; PLC1=192.168.2.10; MIRROR=snort0; PLCPORT=enx9c69d331d874
D=/tmp/cars_pcap; mkdir -p "$D"; rm -f "$D"/*.pcap
arm(){  curl -s -XPOST $API/defense -H "X-CARS-Token: $TOKEN" -H 'Content-Type: application/json' -d "{\"on\":$1}" >/dev/null; }
heal(){ curl -s -XPOST $API/restore -H "X-CARS-Token: $TOKEN" -H 'Content-Type: application/json' -d '{"src":"192.168.2.31","dst":"192.168.2.10","dpid":3}' >/dev/null
        for sw in ovsgw ovs1; do sudo ovs-ofctl -O OpenFlow13 --strict del-flows "$sw" "table=1,priority=110,ip,nw_src=192.168.2.31" 2>/dev/null; done; }
capture(){ # tag seconds   (tcpdump, not dumpcap: dumpcap's privilege-drop fails when backgrounded under sudo)
  sudo timeout "$2" tcpdump -i $MIRROR  -nn -U "host $PLC1 and tcp port 102" -w "$D/$1_mirror.pcap" 2>/dev/null &
  sudo timeout "$2" tcpdump -i $PLCPORT -nn -U "host $PLC1 and tcp port 102" -w "$D/$1_plc1.pcap"   2>/dev/null &
  sleep 2; }

echo "################  CARS WIRE-LEVEL PROOF  (mirror = DPI view | $PLCPORT = PLC1 wire)  ################"

echo; echo "===== PHASE A - ARMED : READ (allow) then WRITE (control -> isolate) ====="
arm true; heal
capture armed 22
echo "  READ  @ $(date +%H:%M:%S)"; sudo ip netns exec opns python3 $S7 --host $PLC1 --read 2>&1 | tail -1
sleep 3; heal; sleep 1
echo "  WRITE @ $(date +%H:%M:%S)"; sudo ip netns exec opns python3 $S7 --host $PLC1 --val 0 --count 6 2>&1 | tail -1
echo "  -- OpenFlow isolate flow installed on ovsgw (datapath enforcement) --"
sudo ovs-ofctl -O OpenFlow13 dump-flows ovsgw | grep -m1 "priority=110,ip,nw_src=192.168.2.31" | sed 's/^/     /'
wait; heal

echo; echo "===== PHASE B - DISARMED : WRITE (allow, full session) ====="
arm false
capture disarmed 15
echo "  WRITE @ $(date +%H:%M:%S)"; sudo ip netns exec opns python3 $S7 --host $PLC1 --val 0 --count 6 2>&1 | tail -1
wait; arm true; heal

echo; echo "################  S7comm ON THE WIRE - what REACHED PLC1 ($PLCPORT)  ################"
for t in armed disarmed; do
  echo "----- $t : PLC1 physical wire -----"
  sudo tshark -r "$D/${t}_plc1.pcap" -Y s7comm -T fields -e frame.number -e frame.time_relative -e ip.src -e ip.dst -e _ws.col.Info 2>/dev/null
done
echo; echo "----- ARMED : mirror (DPI view - S7 function codes seen on the wire) -----"
sudo tshark -r "$D/armed_mirror.pcap" -Y s7comm 2>/dev/null | head -25

echo; echo "################  PACKET COUNTS (grounded)  ################"
for f in "$D"/*.pcap; do printf "  %-34s S7comm=%s  total=%s\n" "$(basename "$f")" \
   "$(sudo tshark -r "$f" -Y s7comm 2>/dev/null | wc -l)" "$(sudo tshark -r "$f" 2>/dev/null | wc -l)"; done
echo; echo "pcaps in $D/ - open armed_plc1.pcap & disarmed_plc1.pcap in Wireshark (filter: s7comm)."
