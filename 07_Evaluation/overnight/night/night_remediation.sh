#!/usr/bin/env bash
# night_remediation.sh — exercise the last-good restore path. Fire a bounded FDI
# from the allowlisted SCADA host and record whether the remediation agent was
# invoked (restores counter climbs, level restored) OR the reactive cut pre-empted
# any drift (no restore needed) — both are honest outcomes. Aborts on excursion.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; source "$HERE/night_lib.sh"
CSV="$NIGHT_ROOT/logs/remediation.csv"; [ -f "$CSV" ] || echo "ts,restores_before,restores_after,level_before,level_min,level_max,excursion,outcome" > "$CSV"
rd(){ cat /tmp/cars_remediation_status.json 2>/dev/null|python3 -c "import sys,json;print(json.load(sys.stdin).get('$1'))" 2>/dev/null; }
rb=$(rd restores); lb=$(rd level)
log "remediation test: bounded FDI from .31, watching restore + level (abort on excursion)"
# bounded low-rate spoof so a couple of writes may land before the cut (tests restore, not devastation)
sudo ip netns exec "$NS_OP" timeout 6 python3 "$S7" --host "$PLC1" --dbspoof --db 7 --offset 0 --spoofval 25 --secs 5 --hz 6 >/dev/null 2>&1 &
lmin=100; lmax=0; exc=0
for i in $(seq 1 30); do
  l=$(rd level); [ -z "$l" ] && { sleep 1; continue; }
  li=$(printf '%.0f' "$l" 2>/dev/null||echo 50)
  [ "$li" -lt "$lmin" ] && lmin=$li; [ "$li" -gt "$lmax" ] && lmax=$li
  { [ "$li" -gt 78 ] || [ "$li" -lt 20 ]; } && { exc=1; log "  EXCURSION at level=$li — aborting probe"; sudo pkill -f "netns exec $NS_OP"; break; }
  sleep 1
done
sudo pkill -f "netns exec $NS_OP" 2>/dev/null; clean_src "$IP_OP"; sleep 3
ra=$(rd restores); la=$(rd level)
if [ "${ra:-0}" -gt "${rb:-0}" ] 2>/dev/null; then outcome="remediation_invoked_restored"
elif [ "$exc" = 1 ]; then outcome="EXCURSION_investigate"
else outcome="cut_preempted_drift_no_restore_needed"; fi
echo "$(TS),${rb},${ra},${lb},${lmin},${lmax},${exc},${outcome}" >> "$CSV"
log "  remediation: restores ${rb}->${ra} level[min=$lmin max=$lmax] -> $outcome"
selfheal; greencheck || arm
log "remediation test done"
