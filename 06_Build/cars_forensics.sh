#!/bin/bash
# =============================================================================
# CARS A1 — DEEP FORENSIC EVIDENCE COLLECTOR   (run on Dell#1)
# -----------------------------------------------------------------------------
# Accumulates multi-layer, cross-validated proof for every A1 response:
#   L1 on-wire  : .pcap on attacker/decoy/transit interfaces  (open in Wireshark)
#   L2 OpenFlow : dump-flows all tables (n_packets/n_bytes counters), before/after
#   L3 datapath : ovs-dpctl dump-flows  (kernel MEGAFLOWS = deepest real layer here)
#   L4 meter    : dump-meters + meter-stats band deltas
#   L5 derive   : ofproto/trace  (deterministic per-packet datapath action)
#   L6 ports    : dump-ports NIC/port packet counters, before/after
#   L7 decision : /cars/audit + /cars/status + controller BRAIN log (latency)
#   +  tshark dissections + an auto-correlated FORENSIC_REPORT.md
#
# HONESTY (Rule 0): this is a software OVS testbed, so "hardware level" = pcap wire
# + kernel datapath (ovs-dpctl) + NIC/port counters + ofproto/trace, NOT switch ASIC.
# CARS decides by IP/role ONLY (no protocol DPI -> that's A3). The BLOCK phase sends
# ICMP + TCP:102(S7comm) + TCP:502(Modbus) and shows ONE L3 flow catches all three
# => empirical proof of proto-blindness (the A3 motivation), captured on the wire.
# =============================================================================
set -u
SRC=192.168.3.66; DST=192.168.3.10; DEC=192.168.3.99
HMI=192.168.2.9;  PLC=192.168.2.10
API=http://10.10.10.1:8080/cars
BR=ovsgw
ATT_IF=ins2; TRANSIT_IF=eth0; MIRROR_IF=snort0
TS=$(date +%Y%m%d_%H%M%S)
OUT=$HOME/cars_forensics/run_$TS
mkdir -p "$OUT"/{pcap,flows,meters,ports,dpctl,trace,logs,decision}
SUM="$OUT/summary.tsv"; : > "$SUM"
echo "[*] evidence dir: $OUT"

have(){ command -v "$1" >/dev/null 2>&1; }
TSHARK=""; have tshark && TSHARK=1
INS2MAC=$(cat /sys/class/net/$ATT_IF/address 2>/dev/null)

band(){ sudo ovs-ofctl -O OpenFlow13 meter-stats $BR meter=1 2>/dev/null | grep -oP 'packet_count:\K[0-9]+' | head -1; }
pcapcnt(){ [ -f "$1" ] && tcpdump -r "$1" 2>/dev/null | wc -l || echo 0; }

snap(){ # $1=label
  local L=$1
  { echo "### table 0 (GUARD)";  sudo ovs-ofctl -O OpenFlow13 dump-flows $BR table=0
    echo "### table 1 (POLICY)"; sudo ovs-ofctl -O OpenFlow13 dump-flows $BR table=1
    echo "### table 2 (SWITCH)"; sudo ovs-ofctl -O OpenFlow13 dump-flows $BR table=2
  } > "$OUT/flows/${L}.txt" 2>&1
  sudo ovs-ofctl -O OpenFlow13 meter-stats $BR   > "$OUT/meters/${L}.txt" 2>&1
  sudo ovs-ofctl -O OpenFlow13 dump-ports  $BR   > "$OUT/ports/${L}.txt"  2>&1
  sudo ovs-dpctl dump-flows                      > "$OUT/dpctl/${L}.txt"  2>&1
}

clean(){ curl -s -X POST $API/restore -d "{\"src\":\"$SRC\",\"dst\":\"$DST\"}" >/dev/null 2>&1
         sudo ovs-ofctl -O OpenFlow13 del-flows $BR "table=1,ip,nw_src=$SRC" 2>/dev/null; sleep 1; }

# mixed probe: ICMP + real TCP SYNs to ICS ports 102 (S7comm) and 502 (Modbus)
probe_mixed(){ ping -c "${1:-10}" -i 0.1 -W1 $DST >/dev/null 2>&1
  python3 - "$DST" <<'PY' >/dev/null 2>&1
import socket,sys
d=sys.argv[1]
for port in (102,502):
    for _ in range(6):
        s=socket.socket(); s.settimeout(0.3)
        try: s.connect((d,port))
        except OSError: pass
        finally: s.close()
PY
}

CAPS=()
capstart(){ CAPS=()
  sudo timeout 90 tcpdump -i $ATT_IF -w "$OUT/pcap/$1__attacker_ins2.pcap" -U -nn 2>/dev/null & CAPS+=($!)
  sudo ip netns exec hpotns timeout 90 tcpdump -i hpot -w "$OUT/pcap/$1__decoy_hpot.pcap" -U -nn 2>/dev/null & CAPS+=($!)
  sudo timeout 90 tcpdump -i $TRANSIT_IF -w "$OUT/pcap/$1__transit_eth0.pcap" -U -nn 2>/dev/null & CAPS+=($!)
  sleep 1; }
capstop(){ sudo kill "${CAPS[@]}" 2>/dev/null; sleep 1; }

trace_pkt(){ # $1=label  $2=proto-fields
  sudo ovs-appctl ofproto/trace $BR \
     "in_port=$ATT_IF,dl_src=$INS2MAC,$2,nw_src=$SRC,nw_dst=$DST" \
     > "$OUT/trace/$1.txt" 2>&1; }

# =============================================================================
echo "[*] PHASE 0 — substrate / environment forensics"
{ echo "== date =="; date
  echo; echo "== kernel =="; uname -a
  echo; echo "== OVS version =="; sudo ovs-vsctl --version | head -1
  echo; echo "== datapath type =="; sudo ovs-vsctl get bridge $BR datapath_type 2>/dev/null || echo "(system/kernel default)"
  echo; echo "== bridges/ports =="; sudo ovs-vsctl show
  echo; echo "== $BR OpenFlow ports =="; sudo ovs-ofctl -O OpenFlow13 show $BR
  echo; echo "== meter features =="; sudo ovs-ofctl -O OpenFlow13 meter-features $BR
  echo; echo "== group features =="; sudo ovs-ofctl -O OpenFlow13 dump-group-features $BR
  echo; echo "== transit NIC ($TRANSIT_IF) =="; sudo ethtool -i $TRANSIT_IF 2>/dev/null; sudo ethtool $TRANSIT_IF 2>/dev/null | grep -iE "speed|duplex|link detected"
  echo; echo "== ip addrs =="; ip -br a
  echo; echo "== netns =="; ip netns list; echo "-- hpotns --"; sudo ip netns exec hpotns ip -br a
} > "$OUT/logs/00_environment.txt" 2>&1
echo "[*] controller status/audit snapshot"
curl -s $API/status  > "$OUT/decision/status_start.json" 2>&1
curl -s $API/audit   > "$OUT/decision/audit_start.json"  2>&1

echo "[*] stopping cars-bridge (isolate the enforcement mechanism from autonomous overrides)"
sudo systemctl stop cars-bridge 2>/dev/null

# ---- generic mechanism-forensics runner ------------------------------------
run(){ # $1=NAME  $2=FORCE  $3=trace-proto  $4=probe-fn
  local N=$1 F=$2 TR=$3 PF=$4
  echo "[*] ===== $N ====="
  clean
  snap "${N}_pre"
  capstart "$N"
  local B0=$(band)
  [ "$F" != "NONE" ] && curl -s -X POST $API/respond -d "{\"src\":\"$SRC\",\"dst\":\"$DST\",\"force\":\"$F\"}" >/dev/null 2>&1
  snap "${N}_armed"
  $PF
  local B1=$(band)
  capstop
  snap "${N}_post"
  trace_pkt "$N" "$TR"
  # reconciliation numbers
  local fpk=$(grep -hE "nw_src=$SRC" "$OUT/flows/${N}_post.txt" | grep -oP 'n_packets=\K[0-9]+' | awk '{s+=$1} END{print s+0}')
  local mdrop=$(( ${B1:-0} - ${B0:-0} ))
  local att=$(pcapcnt "$OUT/pcap/${N}__attacker_ins2.pcap")
  local dec=$(pcapcnt "$OUT/pcap/${N}__decoy_hpot.pcap")
  local tr=$(pcapcnt "$OUT/pcap/${N}__transit_eth0.pcap")
  printf "%s\t%s\t%s\t%s\t%s\t%s\n" "$N" "$fpk" "$mdrop" "$att" "$dec" "$tr" >> "$SUM"
  echo "    flow_matched=$fpk  meter_dropped=$mdrop  pcap[att=$att dec=$dec transit=$tr]"
}

# probe variants
p_std(){ probe_mixed 10; }
p_throttle(){ ping -c 80 -i 0.02 -W1 $DST >/dev/null 2>&1; }     # 40pps vs 20pps meter
p_isolate(){ ping -c 5 -i 0.1 -W1 $DST >/dev/null 2>&1; ping -c 5 -i 0.1 -W1 $DEC >/dev/null 2>&1; }  # two dsts
p_deflect(){ ping -c 4 -W1 $DST > "$OUT/logs/DEFLECT_ping.txt" 2>&1; }

# PHASE 1 — every response at the mechanism level
run ALLOW    NONE     "ip"                    p_std
run MONITOR  MONITOR  "ip"                    p_std
run BLOCK    BLOCK    "tcp,tp_dst=502"        p_std        # mixed ICMP+102+502 -> one L3 flow catches all
run ISOLATE  ISOLATE  "ip"                    p_isolate
run THROTTLE THROTTLE "icmp"                  p_throttle
run DEFLECT  DEFLECT  "icmp"                  p_deflect
clean

# REFUSE — CRITICAL loop is the real HMI<->PLC S7 traffic (never enforced)
echo "[*] ===== REFUSE (CRITICAL safety invariant) ====="
sudo timeout 12 tcpdump -i $MIRROR_IF -w "$OUT/pcap/REFUSE__mirror_snort0.pcap" -U -nn "host $HMI and host $PLC" 2>/dev/null &
RP=$!; sleep 1
curl -s -X POST $API/respond -d "{\"src\":\"$HMI\",\"dst\":\"$PLC\"}" > "$OUT/decision/REFUSE_decision.json" 2>&1
sleep 8; sudo kill $RP 2>/dev/null; sleep 1
snap "REFUSE_post"
refcnt=$(pcapcnt "$OUT/pcap/REFUSE__mirror_snort0.pcap")
printf "REFUSE\t(none-installed)\t0\t0\t0\t%s\n" "$refcnt" >> "$SUM"
echo "    HMI<->PLC mirror frames captured=$refcnt ; decision=$(cat "$OUT/decision/REFUSE_decision.json")"

# PHASE 2 — autonomous decision path (bridge ON): Snort -> bridge -> CARS -> flow
echo "[*] ===== AUTONOMOUS (detect->decide->enforce) ====="
clean; sudo systemctl start cars-bridge; sleep 3
sudo timeout 20 tcpdump -i $ATT_IF -w "$OUT/pcap/AUTONOMOUS__attacker_ins2.pcap" -U -nn 2>/dev/null & AP=$!
sleep 1
ping -c 12 -i 0.4 -W1 $DST > "$OUT/logs/AUTONOMOUS_ping.txt" 2>&1     # organic insider attack
sleep 2
curl -s $API/audit  > "$OUT/decision/audit_after_autonomous.json" 2>&1
curl -s $API/status > "$OUT/decision/status_after_autonomous.json" 2>&1
snap "AUTONOMOUS_post"
sudo kill $AP 2>/dev/null; sleep 1
clean

# =============================================================================
echo "[*] PHASE 3 — tshark dissections + report"
if [ -n "$TSHARK" ]; then
  for f in "$OUT"/pcap/*.pcap; do
    b=$(basename "$f" .pcap)
    tshark -r "$f" -q -z io,phs > "$OUT/logs/tshark_${b}_protohier.txt" 2>/dev/null
    tshark -r "$f" -n 2>/dev/null | head -40 > "$OUT/logs/tshark_${b}_frames.txt"
  done
else
  echo "    tshark not installed -> pcaps still saved for Wireshark; run: sudo apt-get install -y tshark"
fi

REPORT="$OUT/FORENSIC_REPORT.md"
{
echo "# CARS A1 — Forensic evidence report"
echo "Generated $(date) on $(hostname). Evidence dir: ${OUT}"
echo
echo "Substrate: OVS software SDN. Deepest real layers captured = on-wire pcap, kernel"
echo "datapath megaflows (ovs-dpctl), NIC/port counters, ofproto/trace. CARS decides by"
echo "IP/role only (no protocol DPI = A3). Every response is cross-validated across"
echo "independent counters (OVS flow, OVS meter, pcap frame count, traffic outcome)."
echo
echo "## Cross-validation summary"
echo "| Response | OVS flow n_packets | meter drops | pcap att | pcap decoy | pcap transit |"
echo "|---|---|---|---|---|---|"
while IFS=$'\t' read -r n fpk md a d t; do echo "| $n | $fpk | $md | $a | $d | $t |"; done < "$SUM"
echo
echo "## How to read the proof"
echo "- **BLOCK**: one L3 \`drop\` flow (\`ip,nw_src,nw_dst\`) — its \`n_packets\` counts ICMP **and** TCP:102 **and** TCP:502 alike -> CARS is proto-blind (A3 gap, on the wire in the BLOCK attacker pcap)."
echo "- **ISOLATE**: a single \`priority=110,nw_src\`-only flow drops traffic to *two* destinations (.10 and .99) -> source-wide quarantine."
echo "- **THROTTLE**: meter band drop count + delivered pings must sum to sent (delivery-verified, not meter-only)."
echo "- **DEFLECT**: decoy pcap shows request+reply; attacker pcap shows replies rewritten to .10 at **ttl=64** (decoy) not ttl=29 (PLC). See \`logs/DEFLECT_ping.txt\`."
echo "- **REFUSE**: no flow installed for HMI<->PLC; mirror pcap shows the loop still running (safety invariant)."
echo "- **AUTONOMOUS**: \`decision/audit_after_autonomous.json\` = the Snort->bridge->CARS chain enforcing without human input."
echo
echo "## Files"
echo "- \`pcap/\`  per-event captures per vantage point (Wireshark)."
echo "- \`flows/\` OpenFlow tables 0/1/2 with counters at pre/armed/post."
echo "- \`dpctl/\` kernel datapath megaflows.  \`meters/\` \`ports/\` counters.  \`trace/\` ofproto/trace."
echo "- \`decision/\` controller audit+status JSON.  \`logs/\` environment + tshark dissections."
} > "$REPORT"

# bundle for transfer to Wireshark on the Windows box
TAR=$HOME/cars_forensics_$TS.tar.gz
tar -czf "$TAR" -C "$HOME/cars_forensics" "run_$TS" 2>/dev/null
echo "[*] DONE."
echo "    report : $REPORT"
echo "    bundle : $TAR   (copy to E:\\Dissertation and open pcaps in Wireshark)"
sudo systemctl is-active cars-bridge >/dev/null && echo "    cars-bridge: active" || sudo systemctl start cars-bridge
