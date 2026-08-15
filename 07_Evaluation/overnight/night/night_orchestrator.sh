#!/usr/bin/env bash
# night_orchestrator.sh — the 12-14 h overnight CARS stress campaign.
# Ties together: continuous monitor (1), attack battery (2,3,4,5),
# bounded DDoS-under-load (6) and adversarial gap-hunt (7), with a watchdog
# that green-checks and self-heals each cycle and never freezes the process.
#
#   HOURS=14 bash night_orchestrator.sh
#
# Produces $HOME/night_YYYYMMDD/ : logs/*.csv, pcap/*, flows/*. Upload logs/ after.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; source "$HERE/night_lib.sh"
HOURS="${HOURS:-14}"; END=$(( $(date +%s) + HOURS*3600 ))
DDOS_EVERY="${DDOS_EVERY:-6}"     # run a DDoS phase every N cycles
GAP_EVERY="${GAP_EVERY:-8}"       # run a gap-hunt pass every N cycles
mttm_header
log "=========== OVERNIGHT CAMPAIGN START (${HOURS} h) -> $NIGHT_ROOT ==========="

# preflight
selfheal; arm
if ! greencheck; then log "PREFLIGHT not green — fix the rig, then relaunch"; fi
bash "$HERE/../green_check.sh" > "$NIGHT_ROOT/logs/greencheck_start.txt" 2>&1 || true

# continuous monitor in the background for the whole run
MON_DUR=$((HOURS*3600+300)) bash "$HERE/night_monitor.sh" &
MONPID=$!

cycle=0; fails=0
while [ "$(date +%s)" -lt "$END" ]; do
  cycle=$((cycle+1)); log "----- cycle $cycle -----"
  # watchdog: if unhealthy, self-heal and skip attacks this cycle (keep monitoring)
  if ! greencheck; then
    fails=$((fails+1)); log "watchdog: unhealthy (fail #$fails), self-healing + pausing attacks"
    selfheal; clean_all_reactive; arm; sleep 30; [ "$fails" -ge 5 ] && log "PERSISTENT UNHEALTH — investigate in the morning; monitor continues"
    continue
  fi
  fails=0
  # attack battery every cycle
  ROUNDS=1 bash "$HERE/night_attack_battery.sh"
  # periodic DDoS phase
  if [ $((cycle % DDOS_EVERY)) -eq 0 ]; then DDOS_DUR=240 bash "$HERE/night_ddos.sh"; fi
  # periodic gap-hunt pass
  if [ $((cycle % GAP_EVERY)) -eq 0 ]; then bash "$HERE/night_gaphunt.sh"; fi
  # reset to a clean baseline between cycles
  clean_all_reactive; selfheal; sleep 8
done

log "campaign window elapsed; final snapshot"
clean_all_reactive; selfheal; arm
bash "$HERE/../green_check.sh" > "$NIGHT_ROOT/logs/greencheck_end.txt" 2>&1 || true
sudo pkill -f night_monitor 2>/dev/null; wait "$MONPID" 2>/dev/null
python3 "$HERE/night_analyze.py" "$NIGHT_ROOT" > "$NIGHT_ROOT/logs/SUMMARY.txt" 2>&1 || true
log "=========== CAMPAIGN DONE. Summary: $NIGHT_ROOT/logs/SUMMARY.txt ==========="
cat "$NIGHT_ROOT/logs/SUMMARY.txt" 2>/dev/null
