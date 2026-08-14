#!/usr/bin/env bash
# Battery E - process-risk capture: does ARMED CARS perturb the legitimate process?
# Logs per-second tank level (process stability) and the legit-throughput counters for ONE phase.
# Run it ONCE disarmed and ONCE armed, same duration, with NO attack running, so the only
# difference between the two runs is whether reactive enforcement is on.
#
# Usage:  ./e_capture.sh <phase> <seconds> [bridge]
#   validation:   ./e_capture.sh disarmed 120   ;  (toggle)  ;  ./e_capture.sh armed 120
#   full run:     ./e_capture.sh disarmed 3600  ;  (toggle)  ;  ./e_capture.sh armed 3600
#
# Toggle enforcement between phases with your usual control, e.g.:
#   curl -s -X POST http://10.10.10.1:8080/cars/defense -H "X-CARS-Token: $(cat ~/cars/api_token)" -d '{"on":false}'   # disarm
#   curl -s -X POST http://10.10.10.1:8080/cars/defense -H "X-CARS-Token: $(cat ~/cars/api_token)" -d '{"on":true}'    # arm
set -u
PHASE="${1:?phase name: disarmed|armed}"; DUR="${2:-1800}"; BR="${3:-ovsgw}"
D=~/overnight_$(date +%Y%m%d)/e; mkdir -p "$D"
CSV="$D/${PHASE}.csv"; echo "ts,level,online,restores" > "$CSV"

echo "[E:$PHASE] logging tank level for ${DUR}s -> $CSV  (no attack should be running)"
sudo ovs-ofctl -O OpenFlow13 dump-flows "$BR" > "$D/${PHASE}_flows_start.txt" 2>&1
sudo ovs-ofctl -O OpenFlow13 dump-ports  "$BR" > "$D/${PHASE}_ports_start.txt" 2>&1

end=$((SECONDS+DUR))
while [ $SECONDS -lt $end ]; do
  vals=$(python3 - <<'PY' 2>/dev/null
import json
try:
    d=json.load(open("/tmp/cars_remediation_status.json"))
    print("%s %s %s"%(d.get("level"),d.get("online"),d.get("restores")))
except Exception:
    print("NA NA NA")
PY
)
  echo "$(date +%s.%N | cut -c1-14),${vals// /,}" >> "$CSV"
  sleep 1
done

sudo ovs-ofctl -O OpenFlow13 dump-flows "$BR" > "$D/${PHASE}_flows_end.txt" 2>&1
sudo ovs-ofctl -O OpenFlow13 dump-ports  "$BR" > "$D/${PHASE}_ports_end.txt" 2>&1
echo "[E:$PHASE] done. rows: $(( $(wc -l < "$CSV") - 1 ))"
echo "[E:$PHASE] copy ~/overnight_$(date +%Y%m%d)/e into the repo results/ when both phases are captured."
