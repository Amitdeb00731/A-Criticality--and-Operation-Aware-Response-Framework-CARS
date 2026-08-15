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
DDOS_EVERY="${DDOS_EVERY:-10}"    # run a DDoS phase every N cycles (transport-layer residual
GAP_EVERY="${GAP_EVERY:-16}"      # + gap-hunt run less often: they stress the PLC S7 stack and
                                  # the residual is already documented - keep them sparse + gentle)
COV_EVERY="${COV_EVERY:-4}"       # response-ladder + tier-sweep + GUARD + auth-API every N cycles
FP_EVERY="${FP_EVERY:-10}"        # adversarial-benign false-positive stress every N cycles
REM_EVERY="${REM_EVERY:-10}"      # bounded last-good-restore test every N cycles
mttm_header
log "=========== OVERNIGHT CAMPAIGN START (${HOURS} h) -> $NIGHT_ROOT ==========="

# ---- fail-fast preflight: catch anything that would need a human mid-run ----
preflight(){
  local fatal=0
  # 1) must run without a sudo password prompt (else it hangs at hour N unattended)
  if [ "$(id -u)" != "0" ] && ! sudo -n true 2>/dev/null; then
    log "FATAL: not root and sudo needs a password. An unattended run would hang on the first sudo."
    log "       relaunch as:  sudo -E HOURS=$HOURS bash $HERE/night_orchestrator.sh"
    fatal=1
  fi
  # 2) attack clients present
  for f in "$S7" "$MBATK"; do [ -f "$f" ] || { log "FATAL: missing attack client $f"; fatal=1; }; done
  # 3) capture interfaces present (non-fatal: capture degrades, run still completes)
  ip -br link show snort0 >/dev/null 2>&1 || log "WARN: mirror interface snort0 not found (edit night_lib.sh)"
  ip -br link show enx9c69d331d874 >/dev/null 2>&1 || log "WARN: PLC-port interface not found (edit night_lib.sh); leaked-frame counts will be 0"
  # 4) scapy for the DDoS + gap probes (non-fatal: those phases degrade)
  python3 -c 'import scapy' 2>/dev/null || log "WARN: scapy missing; DDoS + some gap probes will be skipped"
  # 5) disk headroom (non-fatal, but warn loudly)
  local freem; freem=$(df -Pm "$NIGHT_ROOT" 2>/dev/null|awk 'NR==2{print $4}')
  [ "${freem:-99999}" -lt 3072 ] && log "WARN: only ${freem}MB free at $NIGHT_ROOT; the disk guard will stop pcaps if it runs low"
  # 6) rig must be green to start (don't launch a doomed 14 h run)
  selfheal; arm
  bash "$HERE/../green_check.sh" > "$NIGHT_ROOT/logs/greencheck_start.txt" 2>&1 || true
  greencheck || { log "FATAL: rig not green at launch (controller/process). Fix, then relaunch."; fatal=1; }
  return $fatal
}
if ! preflight; then log "PREFLIGHT FAILED — aborting before the unattended run starts."; exit 1; fi
log "preflight passed: root/sudo ok, clients present, rig green. Safe to walk away."

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
  # Factory-IO liveness guard: a frozen tank (level not moving) with the process still
  # "online" means Factory IO's S7 link dropped - it does NOT auto-reconnect. Do not pile
  # attacks on a dead process; log the window, attempt recovery, and skip attacks this cycle.
  if tank_frozen; then
    log "watchdog: FACTORYIO_FREEZE (tank level not moving) - pausing attacks, attempting recovery"
    FZ="$NIGHT_ROOT/logs/freeze.csv"; [ -f "$FZ" ] || echo "ts,detail,cycle,level" > "$FZ"
    echo "$(TS),FACTORYIO_FREEZE,$cycle,$(tank_level)" >> "$FZ"
    recover_process; sleep 30; continue
  fi
  # attack battery every cycle (Dell-1 namespaces: high throughput)
  CYCLE=$cycle STOP_EVERY="${STOP_EVERY:-12}" ROUNDS=1 bash "$HERE/night_attack_battery.sh"
  # real-VM Kali vantage (realistic path), if configured, every KALI_EVERY cycles
  if [ "${USE_KALI:-0}" = "1" ] && [ $((cycle % ${KALI_EVERY:-3})) -eq 0 ]; then
    ROUNDS=1 bash "$HERE/night_kali.sh"
  fi
  # periodic coverage pass (response ladder + tier sweep + GUARD + auth-API)
  if [ $((cycle % COV_EVERY)) -eq 0 ]; then bash "$HERE/night_coverage.sh"; fi
  # periodic DDoS phase
  if [ $((cycle % DDOS_EVERY)) -eq 0 ]; then DDOS_DUR=90 bash "$HERE/night_ddos.sh"; fi
  # periodic gap-hunt pass
  if [ $((cycle % GAP_EVERY)) -eq 0 ]; then bash "$HERE/night_gaphunt.sh"; fi
  # periodic adversarial-benign false-positive stress
  if [ $((cycle % FP_EVERY)) -eq 0 ]; then FP_DUR=300 bash "$HERE/night_fpstress.sh"; fi
  # periodic bounded last-good-restore test
  if [ $((cycle % REM_EVERY)) -eq 0 ]; then bash "$HERE/night_remediation.sh"; fi
  # reset to a clean baseline between cycles; give the PLC S7 stack room to breathe
  # (constant back-to-back assault was what stressed Factory IO's link)
  clean_all_reactive; selfheal; sleep "${CYCLE_SLEEP:-45}"
done

log "campaign window elapsed; final snapshot"
clean_all_reactive; selfheal; arm
bash "$HERE/../green_check.sh" > "$NIGHT_ROOT/logs/greencheck_end.txt" 2>&1 || true
sudo pkill -f night_monitor 2>/dev/null; wait "$MONPID" 2>/dev/null
python3 "$HERE/night_analyze.py" "$NIGHT_ROOT" > "$NIGHT_ROOT/logs/SUMMARY.txt" 2>&1 || true
log "=========== CAMPAIGN DONE. Summary: $NIGHT_ROOT/logs/SUMMARY.txt ==========="
cat "$NIGHT_ROOT/logs/SUMMARY.txt" 2>/dev/null
