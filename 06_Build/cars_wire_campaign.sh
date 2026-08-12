#!/bin/bash
# cars_wire_campaign.sh — WIRE/PACKET-LEVEL attack + cross-device evidence campaign against CARS.
# Attacks the control-plane, the flows, the conntrack state, and the process; captures pcaps at 3 wire points and
# timestamp-aligned state from EVERY layer (controller audit, switch flows, conntrack, guard, flow-audit, remediation/PLC).
# Reversible + process-safe: idle conduits, auto-expiring isolates, remediation restores. Run on Dell#1.
set -u
D=/tmp/campaign; rm -rf "$D"; mkdir -p "$D"; EV="$D/events.log"
API=http://10.10.10.1:8080
PLCIF=enx9c69d331d874          # PLC1 physical port
TS(){ date '+%H:%M:%S.%3N'; }
mark(){ echo "" | tee -a "$EV"; echo "=== [$(TS)] $* ===" | tee -a "$EV"; }
snap(){ { echo "--- snapshot [$(TS)]: $* ---"
  echo "conntrack_entries: $(sudo ovs-dpctl dump-conntrack 2>/dev/null | wc -l)"
  echo "remediation: $(cat /tmp/cars_remediation_status.json 2>/dev/null)"
  echo "flowaudit:   $(cat /tmp/cars_flowaudit_status.json 2>/dev/null)"
  echo "guard(.2.31/.2.45/.2.77): $(curl -s $API/cars/guard | python3 -c "import sys,json;d=json.load(sys.stdin)['drops'];print({k:v for k,v in d.items() if any(x in k for x in ('2.31','2.45','2.77'))})" 2>/dev/null)"
  echo "isolate_flows_ovs1: $(sudo ovs-ofctl -O OpenFlow13 dump-flows ovs1 table=1 | grep -c 'cookie=0xca')"
  echo "audit_tail:"; curl -s $API/cars/audit | python3 -c "import sys,json;[print('   '+l) for l in json.load(sys.stdin)['audit'][-5:]]" 2>/dev/null
  } >> "$EV"; }

mark "CAMPAIGN START — starting captures (PLC1 wire, OpenFlow control channel, DPI mirror)"
sudo timeout 240 tcpdump -i "$PLCIF" -nn -U -w "$D/plc1_wire.pcap"   'host 192.168.2.10 and tcp port 102' 2>/dev/null &
sudo timeout 240 tcpdump -i any     -nn -U -w "$D/of_control.pcap"   'tcp port 6653' 2>/dev/null &
sudo timeout 240 tcpdump -i snort0  -nn -U -w "$D/dpi_mirror.pcap"   2>/dev/null &
sleep 3
sudo ovs-ofctl -O OpenFlow13 dump-flows ovs1  > "$D/flows_ovs1_baseline.txt" 2>/dev/null
sudo ovs-ofctl -O OpenFlow13 dump-flows ovsgw > "$D/flows_ovsgw_baseline.txt" 2>/dev/null
snap "BASELINE"

# ── V1 CONTROL-PLANE: unauthenticated control attempt (P0-4 defence) ────────────────────────────────────────────────
mark "V1 CONTROL-PLANE attack: unauth POST /cars/defense {on:false} (expect 401 + DENIED audit)"
curl -s -o "$D/v1_resp.txt" -w "  HTTP=%{http_code}\n" -X POST $API/cars/defense -H 'Content-Type: application/json' -d '{"on":false}' | tee -a "$EV"
echo "  body: $(cat $D/v1_resp.txt)" >> "$EV"
sleep 2; snap "AFTER V1"

# ── V2 FLOW-INTEGRITY: attacker injects a bogus rule + DELETES a real A2 conduit (idle scada->modbus) ───────────────
mark "V2 FLOW tamper: inject bogus rule (ovsgw) + delete real A2 conduit .2.31->.2.20:502 (ovs1)"
sudo ovs-ofctl -O OpenFlow13 add-flow ovsgw "cookie=0x0,table=1,priority=6,ip,nw_src=198.51.100.66,actions=drop"
M='cookie=0xa2/-1,table=1,priority=80,ct_state=+new+trk,tcp,nw_src=192.168.2.31,nw_dst=192.168.2.20,tp_dst=502'
sudo ovs-ofctl -O OpenFlow13 --strict del-flows ovs1 "$M"
echo "  waiting 12s for the flow-audit watch-daemon to poll..." >> "$EV"
sleep 12
sudo python3 ~/cars_flow_audit.py --check --bridges ovs1,ovsgw >> "$EV" 2>&1
# restore
sudo ovs-ofctl -O OpenFlow13 --strict del-flows ovsgw "cookie=0x0/-1,table=1,priority=6,ip,nw_src=198.51.100.66"
sudo ovs-ofctl -O OpenFlow13 add-flow ovs1 "cookie=0xa2,table=1,priority=80,ct_state=+new+trk,tcp,nw_src=192.168.2.31,nw_dst=192.168.2.20,tp_dst=502,actions=ct(commit),goto_table:2"
sleep 2; snap "AFTER V2 (restored)"

# ── V3 STATE MANIPULATION: OT attacker forges out-of-state ACKs at PLC1:102 (try to bypass the ct pipeline) ─────────
mark "V3 STATE manip: attacker (.2.66) forges out-of-state ACKs to PLC1:102 (should NOT reach PLC1)"
sudo ip netns exec atkns python3 -c "from scapy.all import *; send(IP(src='192.168.2.66',dst='192.168.2.10')/TCP(sport=55555,dport=102,flags='A',seq=42),count=8,verbose=0); print('  8 forged out-of-state ACKs sent')" >> "$EV" 2>&1
sleep 2; snap "AFTER V3"

# ── V4 OP-AWARE ICS ATTACK: a COMPROMISED trusted seam (.2.31) writes a bogus level to PLC1 -> DPI ISOLATE + remediation ─
mark "V4 OP-AWARE ICS: compromised scada .2.31 S7-WRITE bogus level 5.0 to PLC1 DB7 (block AND maintain)"
echo "  remediation BEFORE: $(cat /tmp/cars_remediation_status.json)" >> "$EV"
sudo ip netns exec opns python3 -c "
import snap7,struct
c=snap7.client.Client()
try:
    c.connect('192.168.2.10',0,1); c.db_write(7,0,bytearray(struct.pack('>f',5.0))); print('  S7 WRITE sent: DB7.Level <- 5.0 (tamper)')
except Exception as e: print('  write outcome:',e)
" >> "$EV" 2>&1
sleep 5
echo "  remediation AFTER:  $(cat /tmp/cars_remediation_status.json)" >> "$EV"
snap "AFTER V4 (expect .2.31 ISOLATE + remediation restores++)"

mark "CAMPAIGN END — flushing + stopping captures"
sudo ovs-ofctl -O OpenFlow13 dump-flows ovs1  > "$D/flows_ovs1_end.txt" 2>/dev/null
sleep 3; sudo pkill -f "tcpdump.*campaign" 2>/dev/null; sleep 2
sudo chmod 644 "$D"/*.pcap 2>/dev/null
echo; echo "=== EVIDENCE BUNDLE in $D ==="; ls -la "$D"
echo; echo ">> UPLOAD these: events.log, plc1_wire.pcap, of_control.pcap, dpi_mirror.pcap  (+ flows_*.txt if small)"
