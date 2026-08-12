#!/bin/bash
# cars_verifyC.sh — Appendix C verification pass. RUN ON DELL#1:  sudo bash ~/cars_verifyC.sh
# Promotes the documented/inferred Appendix C claims to directly-verified. Read-only EXCEPT C.7 (stops+restarts Snort, self-heals).
API=http://10.10.10.1:8080/cars; PLC1=192.168.2.10; MB=192.168.2.20; S7=/home/msclab/s7_write.py; MBC=/home/msclab/mb_client.py
line(){ echo; echo "===================== $1 ====================="; }

line "C.2  control channel + two bridges  (EXPECT: both -> tcp:10.10.10.1:6653 ; ovs2 NOT here)"
for b in ovs1 ovsgw; do echo -n "  $b controller: "; ovs-vsctl get-controller $b 2>/dev/null; done
echo -n "  ovs2 present on Dell#1? "; ovs-vsctl br-exists ovs2 2>/dev/null && echo "YES (unexpected)" || echo "no (correct -> it lives on Dell#3)"
echo -n "  live OpenFlow sockets to :6653 = "; ss -tn 2>/dev/null | grep -c ':6653'

line "C.1  sensor tap: OVS mirror + Snort config  (EXPECT: a mirror object; HOME_NET + cars.rules; snort on an iface)"
ovs-vsctl list mirror 2>/dev/null | grep -Ei "name|select|output" | head || echo "  (no mirror object — inspect the SPAN/port config)"
grep -hE "HOME_NET|cars\.rules|include.*cars" /etc/snort/snort.conf 2>/dev/null | head || echo "  (snort.conf not at /etc/snort — locate: sudo find /etc -name snort.conf)"
echo -n "  snort sniff iface: "; ps -eo args 2>/dev/null | grep "[s]nort" | grep -o '\-i [^ ]*' | head -1 || echo "n/a"

line "C.3  Cell-2 NAT  (EXPECT: DNAT .3.10->.2.10 and/or MASQUERADE — run on the NAT host)"
iptables -t nat -S 2>/dev/null | grep -E '3\.10|MASQUERADE|2\.10' | head || echo "  (no NAT rules here — also try on Dell#3:  sudo iptables -t nat -S | grep -E '2\.10|MASQ')"

line "C.6  historian/SCADA stack  (EXPECT: HTTP code if up; 000/down if idle — gated on PUT/GET)"
for hp in "InfluxDB 8086" "Grafana 3000" "FUXA 1881"; do set -- $hp
  echo -n "  $1 :$2 -> "; curl -s -o /dev/null -m 3 -w "%{http_code}\n" http://127.0.0.1:$2/ 2>/dev/null || echo "down"; done

line "C.8  control-plane isolation  (EXPECT: OT seam CANNOT reach the API; control-plane CAN)"
echo -n "  from OT seam (opns/.2.31) -> API : "
if ip netns exec opns curl -s -m 3 -o /dev/null $API/status 2>/dev/null; then echo "REACHABLE  !! (unexpected — isolation gap)"; else echo "UNREACHABLE (correct — API is off-limits to the OT plane)"; fi
echo -n "  from control plane (Dell#1 base) -> API : "; curl -s -m 3 $API/defense; echo

line "C.7  degradation: SNORT DOWN  (EXPECT: proactive A2 still drops unlisted; reactive op-block goes blind; restores on start)"
echo "  -> stopping cars-snort ..."; systemctl stop cars-snort; sleep 2
echo -n "  [a] unlisted .2.66 -> Modbus .2.20   (want: STILL BLOCKED by A2 default-deny): "; timeout 7 ip netns exec atkns python3 $MBC --host $MB --op read 2>&1 | tail -1
echo -n "  [b] listed  .2.31 -> PLC1 S7 write   (want: NOT blocked — Snort is blind): "; ip netns exec opns python3 $S7 --host $PLC1 --val 0 --count 1 2>&1 | tail -1
echo "  -> restarting cars-snort ..."; systemctl start cars-snort; sleep 3
echo -n "  [c] listed  .2.31 -> PLC1 S7 write   (want: reactive back — triggers block): "; ip netns exec opns python3 $S7 --host $PLC1 --val 0 --count 1 2>&1 | tail -1
sleep 1
echo -n "  [d] listed  .2.31 -> PLC1 S7 write   (want: S7TimeoutError — block now active): "; ip netns exec opns python3 $S7 --host $PLC1 --val 0 --count 1 2>&1 | tail -1
echo "  audit (expect: NO decision for [b] while Snort down; a CONTROL=>BLOCK/ISOLATE once back):"
curl -s $API/audit | python3 -c "import sys,json;[print('     ',x) for x in json.load(sys.stdin).get('audit',[])[-4:]]"

line "DONE"
echo "  C.4 (IT->OT kill chain) is a separate guided shot — needs GNS3 up; see the note in chat."
echo -n "  final defense state: "; curl -s $API/defense; echo
echo "  (source-heal .2.31/.2.66 if you want a clean board:  curl -s -X POST $API/restore -d '{\"dpid\":3,\"src\":\"192.168.2.31\",\"dst\":\"192.168.2.10\"}')"
