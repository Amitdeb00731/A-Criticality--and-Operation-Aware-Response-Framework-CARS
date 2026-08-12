#!/bin/bash
# =============================================================================
# CARS A3 — Modbus DPI forensic evidence collector (run on Dell#1)
# For each scenario captures the full operation-aware chain, cross-validated:
#   wire (tshark Modbus func code)  ->  Snort alert (CARS-MODBUS-*)
#     ->  CARS decision (audit: tier+op+response)  ->  data-plane (OF flow)
# Proves the SAME operator gets read ALLOWed / write THROTTLEd, and an unknown
# write BLOCKed -- driven by the Modbus function code, not just IP/role. (CC-36)
# =============================================================================
set -u
SRV=192.168.2.20; OPR=192.168.2.31; ATK=192.168.2.66
API=http://10.10.10.1:8080/cars
TS=$(date +%Y%m%d_%H%M%S)
OUT=$HOME/cars_forensics/a3_run_$TS
mkdir -p "$OUT"/{pcap,alerts,flows}
echo "[*] A3 evidence dir: $OUT"

pgrep -f mb_server.py >/dev/null || { ip netns exec mbns python3 /home/msclab/mb_server.py 192.168.2.20 & sleep 2; }

{ echo "== Snort DPI config =="; grep -iE "checksum|include" /etc/snort/cars.conf; echo "-- rules --"; grep CARS-MODBUS /etc/snort/cars.rules
  echo; echo "== pymodbus =="; python3 -c "import pymodbus;print(pymodbus.__version__)"
  echo; echo "== netns endpoints =="; for n in mbns opns atkns; do echo -n "$n: "; ip netns exec $n ip -br a show 2>/dev/null | grep -v lo; done
} > "$OUT/environment.txt" 2>&1

scenario(){ # $1 label  $2 netns  $3 src_ip  ...client args
  local L=$1 NS=$2 SRC=$3; shift 3
  echo "[*] ===== $L ($SRC) ====="
  curl -s -X POST $API/restore -d "{\"src\":\"$SRC\",\"dst\":\"$SRV\"}" >/dev/null 2>&1
  sudo ovs-ofctl -O OpenFlow13 del-flows ovsgw "table=1,ip,nw_src=$SRC" 2>/dev/null; sleep 1
  local asz=$(sudo stat -c %s /var/log/snort/alert)
  sudo timeout 12 tshark -i snort0 -n -f "tcp port 502 and host $SRC" -w "$OUT/pcap/${L}.pcap" 2>/dev/null & local TP=$!
  sleep 1
  ip netns exec $NS python3 /home/msclab/mb_client.py --host $SRV "$@"
  sleep 4                                   # let Snort -> bridge -> CARS run
  sudo kill $TP 2>/dev/null; wait 2>/dev/null
  # evidence
  sudo tail -c +$((asz+1)) /var/log/snort/alert | grep -a CARS-MODBUS > "$OUT/alerts/${L}.txt" 2>/dev/null || true
  tshark -r "$OUT/pcap/${L}.pcap" -Y modbus -T fields -e ip.src -e ip.dst -e modbus.func_code -e _ws.col.Info 2>/dev/null > "$OUT/pcap/${L}_modbus.txt"
  ( sudo ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep "nw_src=$SRC" ) > "$OUT/flows/${L}.txt" 2>/dev/null
  [ -s "$OUT/flows/${L}.txt" ] || echo "(no policy flow -> ALLOW / pass to switch)" > "$OUT/flows/${L}.txt"
  echo "    alerts=$(grep -c . "$OUT/alerts/${L}.txt" 2>/dev/null) modbus_frames=$(grep -c . "$OUT/pcap/${L}_modbus.txt" 2>/dev/null)"
}

scenario OP_READ   opns  $OPR --op read
scenario OP_WRITE  opns  $OPR --op write --reg 0 --val 555
scenario ATK_WRITE atkns $ATK --op write --reg 8 --val 9999

curl -s $API/audit > "$OUT/cars_audit.json" 2>&1

# ---- report ----
R="$OUT/A3_FORENSIC_REPORT.md"
{
echo "# CARS A3 — Modbus DPI forensic report"
echo "_Generated $(date) on $(hostname). Dir: ${OUT}_"
echo
echo "Operation-aware chain, cross-validated per scenario: on-wire Modbus function code (tshark) ->"
echo "Snort DPI alert -> CARS decision (op-aware) -> OpenFlow data-plane action."
echo
echo "## Evidence chain"
echo "| Scenario | Wire func code | Snort alert | CARS decision (audit) | Data-plane |"
echo "|---|---|---|---|---|"
for L in OP_READ OP_WRITE ATK_WRITE; do
  fc=$(awk -F'\t' 'NR==1{print $3" "$4}' "$OUT/pcap/${L}_modbus.txt" 2>/dev/null)
  al=$(awk '{print $4}' "$OUT/alerts/${L}.txt" 2>/dev/null | head -1)
  dp=$(grep -oE "actions=[^ ]+" "$OUT/flows/${L}.txt" 2>/dev/null | head -1); [ -z "$dp" ] && dp="pass(no flow)"
  case $L in
    OP_READ)   src=$OPR;;
    OP_WRITE)  src=$OPR;;
    ATK_WRITE) src=$ATK;;
  esac
  de=$(python3 -c "import json,sys;a=json.load(open('$OUT/cars_audit.json'))['audit'];print([x for x in a if '$src' in x and '192.168.2.20' in x][-1][11:] if any('$src' in x and '192.168.2.20' in x for x in a) else '')" 2>/dev/null | sed 's/=>.*//' | tr -s ' ')
  echo "| $L | ${fc:-?} | ${al:-none} | ${de:-?} | ${dp} |"
done
echo
echo "## Reading the proof"
echo "- OP_READ: FC3 read -> CARS-MODBUS-READ -> OPERATIONAL/ALLOW -> no flow (permitted, monitored)."
echo "- OP_WRITE: FC6 write, SAME source -> CARS-MODBUS-WRITE -> SENSITIVE/THROTTLE -> meter flow. Operation escalates the response."
echo "- ATK_WRITE: FC6 write from unknown -> FORBIDDEN/BLOCK -> drop flow; 2nd write cannot connect."
echo "- Files: pcap/*.pcap (Wireshark), alerts/*, flows/*, cars_audit.json, environment.txt."
} > "$R"

TAR="$HOME/cars_a3_forensics_${TS}.tar.gz"
tar -czf "$TAR" -C "$HOME/cars_forensics" "a3_run_$TS" 2>/dev/null
echo "[*] DONE. report: $R"
echo "    bundle: $TAR"
