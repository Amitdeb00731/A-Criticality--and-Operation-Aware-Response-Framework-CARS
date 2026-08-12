#!/bin/bash
# CARS GRAND VALIDATION CAMPAIGN — shared evidence-capture library.
# Source at the top of each phase script:  source /tmp/cars_campaign_lib.sh ; PHASE=phaseN
# Provides: arm/disarm, snap (cross-layer state), flowdump (audit every flow), capstart/capstop (3-point pcaps).
API=http://10.10.10.1:8080
TOKEN=$(cat /home/msclab/cars/api_token 2>/dev/null)
CAMP=/tmp/grand_campaign
PLCIF=${PLCIF:-enx9c69d331d874}     # PLC1 S7 physical port (override with: PLCIF=xxx before sourcing)
mkdir -p "$CAMP"
TS(){ date '+%H:%M:%S.%3N'; }
armstate(){ curl -s -m4 $API/cars/defense | python3 -c 'import sys,json;print("ARMED" if json.load(sys.stdin)["enforce_enabled"] else "DISARMED")' 2>/dev/null; }

arm(){    curl -s -X POST $API/cars/defense -H "X-CARS-Token: $TOKEN" -H "Content-Type: application/json" -d '{"on":true}'  >/dev/null; echo "[$(TS)] -> ARMED"; }
disarm(){ curl -s -X POST $API/cars/defense -H "X-CARS-Token: $TOKEN" -H "Content-Type: application/json" -d '{"on":false}' >/dev/null; echo "[$(TS)] -> DISARMED"; }

flowdump(){  # dump full flow tables (audit EVERY installed flow) tagged by label
  local tag="$1" d="$CAMP/$PHASE"; mkdir -p "$d"
  for br in ovs1 ovsgw; do sudo ovs-ofctl -O OpenFlow13 dump-flows $br > "$d/flows_${br}_${tag}.txt" 2>/dev/null; done
  echo "[$(TS)] flowdump($tag): ovs1=$(wc -l <"$d/flows_ovs1_${tag}.txt") ovsgw=$(wc -l <"$d/flows_ovsgw_${tag}.txt") rules"
}

snap(){  # full cross-layer snapshot -> file + stdout
  local label="$1" d="$CAMP/$PHASE"; mkdir -p "$d"; local f="$d/snap_${label}.txt"
  { echo "=== SNAP [$label] $(TS)  state=$(armstate) ==="
    echo "-- reactive/isolate flows (cookie 0xca) --"
    for br in ovs1 ovsgw; do echo "   $br t1 0xca: $(sudo ovs-ofctl -O OpenFlow13 dump-flows $br table=1|grep -c 0xca)"; done
    echo "-- conntrack entries: $(sudo ovs-dpctl dump-conntrack 2>/dev/null|wc -l)"
    echo "-- GUARD drops (nonzero only) --"
    curl -s -m4 $API/cars/guard | python3 -c "import sys,json;d=json.load(sys.stdin)['drops'];print('  ',{k:v for k,v in d.items() if v} or 'none')" 2>/dev/null
    echo "-- flow-audit: $(cat /tmp/cars_flowaudit_status.json 2>/dev/null)"
    echo "-- PLC1 process (remns/.2.45): $(sudo ip netns exec remns python3 /tmp/rd2.py 2>&1|tail -1)"
    echo "-- controller audit tail --"
    curl -s -m4 $API/cars/audit | python3 -c "import sys,json;[print('   '+l) for l in json.load(sys.stdin)['audit'][-10:]]" 2>/dev/null
  } | tee "$f"
}

capstart(){  # start 3-point wire capture; arg1=duration(s) arg2=extra plc filter (default: all .2.10 + arp)
  local dur="${1:-300}" filt="${2:-host 192.168.2.10 or arp}" d="$CAMP/$PHASE"; mkdir -p "$d"
  sudo timeout "$dur" tcpdump -i "$PLCIF" -nn -U -w "$d/plc1_wire.pcap" $filt 2>/dev/null &
  sudo timeout "$dur" tcpdump -i any     -nn -U -w "$d/of_control.pcap" 'tcp port 6653' 2>/dev/null &
  sudo timeout "$dur" tcpdump -i snort0  -nn -U -w "$d/dpi_mirror.pcap"  2>/dev/null &
  sleep 2; echo "[$(TS)] captures started -> $d (plc1_wire, of_control, dpi_mirror), ${dur}s"
}
capstop(){ sleep 2; sudo pkill -f "tcpdump.*grand_campaign" 2>/dev/null; sleep 1; sudo chmod 644 "$CAMP/$PHASE"/*.pcap 2>/dev/null; echo "[$(TS)] captures stopped; files:"; ls -la "$CAMP/$PHASE"/*.pcap 2>/dev/null; }
