#!/bin/bash
# =============================================================================
# CARS ICS ATTACK BATTERY (CC-51).   sudo bash cars_ics_battery.sh   (Dell#1)
# Fires the full ICS operation spectrum from the SAME trusted operator (.31) at the Modbus PLC (.20) and shows how the
# broadened brain classifies each by OPERATION SEMANTICS, not the 5-tuple:
#   READ -> OPERATIONAL/ALLOW | WRITE -> SENSITIVE/throttle | CONTROL,DIAG,PROGRAM,ILLEGAL -> FORBIDDEN/BLOCK.
# The point: a plain firewall sees one identical conduit; CARS gives it three different verdicts based on the ICS op.
# Conduit is restored between ops (dangerous ops BLOCK it); Snort single-packet flush is retried once (gap G3).
# =============================================================================
set -u
OPR=192.168.2.31; MB=192.168.2.20; API=http://10.10.10.1:8080/cars
TS=$(date +%Y%m%d_%H%M%S); OUT=$HOME/cars_forensics/battery_$TS; mkdir -p "$OUT"; V="$OUT/VERDICT.txt"; :>"$V"
say(){ echo "$1" | tee -a "$V"; }
alast(){ curl -s $API/audit | python3 -c "import json,sys;a=json.load(sys.stdin)['audit'];print(a[-1] if a else '')" 2>/dev/null; }
wait_dec(){ local b="$1" n; for i in $(seq 1 20); do n=$(alast); [ "$n" != "$b" ] && { echo "$n"; return; }; sleep 0.4; done; echo "NO-NEW-DECISION"; }
restore(){ curl -s -XPOST $API/restore -H 'Content-Type: application/json' -d "{\"src\":\"$OPR\",\"dst\":\"$MB\",\"dpid\":3}">/dev/null; }
probe(){ restore; sleep 2; local b d; b=$(alast); ip netns exec opns "$@" >/dev/null 2>&1; d=$(wait_dec "$b")
  [ "$d" = NO-NEW-DECISION ] && { b=$(alast); ip netns exec opns "$@" >/dev/null 2>&1; d=$(wait_dec "$b"); }; echo "$d"; }
row(){ local L=$1 EXP=$2; shift 2; local d op tier resp
  d=$(probe "$@")
  op=$(echo "$d"   | grep -oP 'TCP\s+\K[A-Z]+' | head -1)
  tier=$(echo "$d" | grep -oP '(OPERATIONAL|SENSITIVE|FORBIDDEN|CRITICAL)' | head -1)
  resp=$(echo "$d" | grep -oP '=>\s+\K[A-Z]+' | head -1)
  say "$(printf '  %-9s expect=%-8s detected=%-8s tier=%-11s response=%s' "$L" "$EXP" "${op:-none}" "${tier:-?}" "${resp:-?}")"; }
say "======== ICS ATTACK BATTERY — broadened operation intelligence (source = trusted operator .31 -> Modbus PLC .20) ========"
say "  operation  (crafted function code)              CARS verdict"
row "READ"    READ    python3 /home/msclab/mb_client.py --host $MB --op read
row "WRITE"   WRITE   python3 /home/msclab/mb_client.py --host $MB --op write --reg 4 --val 7
row "CONTROL" CONTROL python3 /home/msclab/mb_attack.py --host $MB --attack coil
row "DIAG"    DIAG    python3 /home/msclab/mb_attack.py --host $MB --attack diag
row "PROGRAM" PROGRAM python3 /home/msclab/mb_attack.py --host $MB --attack program
row "ILLEGAL" ILLEGAL python3 /home/msclab/mb_attack.py --host $MB --attack illegal
restore
say ""
say "  Expected: READ=OPERATIONAL/ALLOW | WRITE=SENSITIVE | CONTROL,DIAG,PROGRAM,ILLEGAL=FORBIDDEN/BLOCK"
say "  => the SAME trusted operator is ALLOWED to read, THROTTLED to write, and BLOCKED for dangerous ops."
say "     CARS reasons about the ICS OPERATION, not the 5-tuple. Broadened ICS intelligence demonstrated."
curl -s $API/audit > "$OUT/audit.json"
TAR=$HOME/cars_battery_${TS}.tar.gz; tar -czf "$TAR" -C "$HOME/cars_forensics" "battery_$TS" 2>/dev/null; say "bundle: $TAR"
echo; echo "===== VERDICT ====="; cat "$V"
