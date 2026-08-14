#!/usr/bin/env bash
# Gap 1 (rig) -- probe reaction-window vs benign background decision load. SAFE.
# Off-rig we measured the controller decision+log stage saturating ~16-18k/s
# single-core (RESULT.txt). This is the live counterpart on real hardware.
#
# Background load: a BOUNDED pool of workers each POSTing a benign allowlisted
# read (192.168.2.55 -> PLC READ) which classifies ALLOW and installs NO rule and
# grows NO state -- so it loads the controller decision path without polluting the
# fabric or fork-bombing. Probe: a single forbidden CONTROL from the attacker
# identity; /cars/respond is synchronous (it enforces before replying), so the
# probe curl's round-trip IS the decision+enforce reaction window. The probe rule
# is cleaned by cookie between levels.
#
# Run on Dell 1, CARS armed + green. Returns to green (0xca cleared) each level.
set -u
API="http://10.10.10.1:8080/cars/respond"
OUT="results/gap1_live"; mkdir -p "$OUT"
PROBE='{"src":"192.168.2.66","dst":"192.168.2.10","op":"CONTROL","rate":0,"dpid":3}'
BENIGN='{"src":"192.168.2.55","dst":"192.168.2.10","op":"READ","rate":0,"dpid":3}'
DUR="${DUR:-15}"
LEVELS=(0 4 8 16 32)      # background worker counts

bgworker(){ local end=$((SECONDS+DUR)) c=0
  while [ $SECONDS -lt "$end" ]; do
    curl -s -o /dev/null -X POST "$API" -H 'Content-Type: application/json' -d "$BENIGN"
    c=$((c+1))
  done; echo "$c" >> "$OUT/.wc"; }

echo "workers,bg_rate_per_s,probe_mttm_ms" > "$OUT/curve.csv"
for W in "${LEVELS[@]}"; do
  : > "$OUT/.wc"; pids=()
  for _ in $(seq 1 "$W"); do bgworker & pids+=($!); done
  sleep 2                                   # let the background ramp
  # fire probe; its synchronous round-trip = reaction window
  t0=$(date +%s.%N)
  curl -s -o /dev/null -X POST "$API" -H 'Content-Type: application/json' -d "$PROBE"
  t1=$(date +%s.%N)
  mttm=$(echo "($t1-$t0)*1000" | bc -l)
  for p in "${pids[@]}"; do wait "$p" 2>/dev/null; done
  posts=$(awk '{s+=$1} END{print s+0}' "$OUT/.wc")
  rate=$(echo "$posts / $DUR" | bc -l)
  printf "%d,%.0f,%.1f\n" "$W" "$rate" "$mttm" | tee -a "$OUT/curve.csv"
  for br in ovs1 ovsgw; do sudo ovs-ofctl -O OpenFlow13 del-flows "$br" "cookie=0xca/-1"; done
  sleep 4                                   # exceed COOLDOWN + settle
done
rm -f "$OUT/.wc"
echo "curve -> $OUT/curve.csv"
