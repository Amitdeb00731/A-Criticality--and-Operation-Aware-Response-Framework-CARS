#!/usr/bin/env bash
# CARS emulation launcher — preflight checks, start the controller, bring up the
# software fabric + PLCs. Requires a Linux host with root, Mininet, Open vSwitch,
# Snort and os-ken. Run from the framework/ directory:  sudo emulation/demo.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FW="$(cd "$HERE/.." && pwd)"
REPO="$(cd "$FW/.." && pwd)"
# default to the emulation config: GUARD anti-spoof bindings are physical-port/MAC
# specific and would false-drop Mininet hosts; POLICY (allowlist + default-deny) still enforces.
SITE="${CARS_SITE:-$FW/examples/site.emulation.yaml}"
ENGINE="$REPO/06_Build/cars_engine.py"

need() { command -v "$1" >/dev/null 2>&1 || { echo "MISSING: $1"; MISS=1; }; }
MISS=0
echo "== preflight =="
[ "$(id -u)" -eq 0 ] || { echo "MISSING: root (run with sudo)"; MISS=1; }
need mn; need ovs-vsctl; need osken-manager || need ryu-manager; need python3
python3 -c "import snap7" 2>/dev/null || { echo "MISSING: python-snap7 (pip install -e '.[emulation]')"; MISS=1; }
[ -f "$ENGINE" ] || { echo "MISSING: engine at $ENGINE"; MISS=1; }
[ -f "$SITE" ]   || { echo "MISSING: site config at $SITE"; MISS=1; }
command -v snort >/dev/null 2>&1 || echo "WARN: snort not found — DPI/reactive path will be inactive"
[ "$MISS" -eq 0 ] || { echo "preflight failed; install the items above."; exit 1; }
echo "preflight OK"

echo "== clean any prior mininet state =="
mn -c >/dev/null 2>&1 || true

echo "== starting CARS controller (config: $SITE) =="
# the engine still writes its audit log and seeds rulebook.json/a2_policy.json under
# this fixed path; create it so a fresh host (any username) does not trip on it.
mkdir -p /home/msclab/cars 2>/dev/null || true
MANAGER="$(command -v osken-manager || command -v ryu-manager)"
CARS_SITE="$SITE" "$MANAGER" "$ENGINE" > /tmp/cars_controller.log 2>&1 &
CTRL_PID=$!
trap 'kill $CTRL_PID 2>/dev/null || true' EXIT
sleep 3
kill -0 "$CTRL_PID" 2>/dev/null || { echo "controller failed to start; see /tmp/cars_controller.log"; tail -20 /tmp/cars_controller.log; exit 1; }
echo "controller up (pid $CTRL_PID, log /tmp/cars_controller.log)"

echo "== bringing up the fabric + software PLCs (Mininet CLI) =="
echo "   in the CLI:  atk python3 $REPO/06_Build/s7_write.py --host 192.168.2.10"
echo "   then:        sh ovs-ofctl -O OpenFlow13 dump-flows ovs1 | grep 192.168.2.10   (priority=55 drop = attacker denied)"
cd "$FW"
python3 "$HERE/topo.py"
