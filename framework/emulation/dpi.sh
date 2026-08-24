#!/usr/bin/env bash
# CARS emulation — reactive DPI path (Snort -> controller bridge).
#
# Run this in a SECOND root terminal AFTER `demo.sh` is up (controller + Mininet
# running) and started in self-plant mode:
#
#     sudo -E env "PATH=$PATH" CARS_SELF_PLANT=1 bash emulation/demo.sh   # terminal A
#     sudo -E env "PATH=$PATH" bash emulation/dpi.sh                        # terminal B
#
# It puts a SPAN (mirror) on the gateway switch, runs Snort with the testbed CARS
# rules against it, and runs the Snort->controller bridge (retargeted from the
# testbed controller IP to this emulation's controller). Then an S7 write-var from
# an allowlisted host is detected as a FORBIDDEN operation and the controller
# installs a criticality-scaled 0x00ca ISOLATE — the operation-aware reactive path.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FW="$(cd "$HERE/.." && pwd)"
REPO="$(cd "$FW/.." && pwd)"
BUILD="$REPO/06_Build"
API="${CARS_API:-http://127.0.0.1:8080/cars/respond}"
BR="ovsgw"                       # gateway switch (dpid 3) — the testbed mirror point
SPAN="snort0"

[ "$(id -u)" -eq 0 ] || { echo "run with sudo (see the header)"; exit 1; }
command -v snort >/dev/null 2>&1 || { echo "MISSING: snort (sudo apt install -y snort)"; exit 1; }
ovs-vsctl br-exists "$BR" 2>/dev/null || { echo "MISSING: $BR — start emulation/demo.sh first"; exit 1; }

# cars.conf uses Snort 2.9 syntax (stream5). Warn if Snort 3 is installed.
if snort -V 2>&1 | grep -qiE 'Version 3'; then
  echo "WARN: Snort 3 detected — cars.conf is Snort 2.9 (stream5) syntax and may need porting to snort3.lua."
fi

echo "== install CARS Snort config + rules into /etc/snort =="
mkdir -p /etc/snort /var/log/snort
cp "$REPO/report/gap_evidence/gap_evidence/configs/cars.conf" /etc/snort/cars.conf
cp "$BUILD/cars.rules" /etc/snort/cars.rules
: > /var/log/snort/alert                     # fresh alert file (the bridge tails it)

echo "== SPAN: mirror all $BR traffic to $SPAN (root-namespace sensor port) =="
ovs-vsctl --may-exist add-port "$BR" "$SPAN" -- set interface "$SPAN" type=internal
ip link set "$SPAN" up
ovs-vsctl -- --id=@p get port "$SPAN" \
          -- --id=@m create mirror name=carsdpi select-all=true output-port=@p \
          -- set bridge "$BR" mirrors=@m >/dev/null

echo "== start Snort on $SPAN (fast alert -> /var/log/snort/alert) =="
pkill -f "snort .* -i $SPAN" 2>/dev/null || true
snort -q -A fast --daq afpacket -c /etc/snort/cars.conf -i "$SPAN" -l /var/log/snort \
      >/tmp/cars_snort.log 2>&1 &
SNORT_PID=$!
sleep 2
kill -0 "$SNORT_PID" 2>/dev/null || { echo "snort failed to start:"; tail -20 /tmp/cars_snort.log; exit 1; }
echo "snort up (pid $SNORT_PID, log /tmp/cars_snort.log)"

echo "== start the Snort->CARS bridge (-> $API) =="
# the testbed bridge hardcodes the testbed controller (10.10.10.1); retarget it to
# the emulation controller. Logic is otherwise unchanged (single source of truth).
sed "s#http://10\.10\.10\.1:8080/cars/respond#$API#" "$BUILD/snort_bridge.py" > /tmp/cars_bridge_emu.py
pkill -f cars_bridge_emu.py 2>/dev/null || true
python3 -u /tmp/cars_bridge_emu.py > /tmp/cars_bridge.log 2>&1 &
BR_PID=$!
trap 'kill $SNORT_PID $BR_PID 2>/dev/null || true; ovs-vsctl --if-exists clear bridge '"$BR"' mirrors; ovs-vsctl --if-exists del-port '"$BR"' '"$SPAN"' 2>/dev/null || true' EXIT
sleep 1

cat <<EOF

reactive DPI path is up. Now, in the Mininet CLI (terminal A), run an attack from
an ALLOWLISTED host performing a FORBIDDEN operation (an S7 write-var to a CRITICAL
PLC — the compromised-conduit / first-packet-leak scenario, report Gap 3):

    scada python3 $BUILD/s7_write.py --host 192.168.2.10 --count 5

Expected:
  * the FIRST write lands (scada->PLC1 is an allowlisted conduit),
  * Snort fires CARS-S7-CONTROL-write; this bridge REPORTs op=CONTROL
    (watch: tail -f /tmp/cars_bridge.log),
  * the controller classifies CONTROL-on-CRITICAL-PLC as FORBIDDEN and installs a
    0x00ca ISOLATE on 192.168.2.31 (watch: tail -f /tmp/cars_controller.log),
  * subsequent writes are cut, and the PLC's own process loop keeps running
    (watch: tail -f /tmp/cars_s7.log — interference stops climbing).

Confirm the reactive rule:
    (mininet)  sh ovs-ofctl -O OpenFlow13 dump-flows ovsgw | grep 0xca

Ctrl-C here to stop Snort + the bridge and remove the SPAN.
EOF
wait
