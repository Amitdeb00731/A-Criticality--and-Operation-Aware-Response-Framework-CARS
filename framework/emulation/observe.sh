#!/usr/bin/env bash
# CARS emulation — live observatory. One screen, every proof.
#
# Opens a tmux 2x2 grid of the live streams and launches the web topology view:
#
#   +-----------------------------+-----------------------------+
#   | CONTROLLER  (GUARD + BRAIN)  | FLOWS  (0xa2 allow / 0xca    |
#   |  decisions, ISOLATE, heal    |  isolate / p55 default-deny) |
#   +-----------------------------+-----------------------------+
#   | PROCESS  (tank loop,         | DPI  (Snort alerts +         |
#   |  level / pump / interference)|  bridge op-aware REPORTs)    |
#   +-----------------------------+-----------------------------+
#
#   Web topology (live SVG, discovered nodes/links/guard/decisions):
#       http://localhost:8090
#
# Run it AFTER demo.sh (and, for the DPI pane, dpi.sh) are up:
#       sudo -E env "PATH=$PATH" bash emulation/observe.sh
# Detach with Ctrl-b then d; re-attach with `tmux attach -t cars`. Ctrl-b then x
# closes a pane. Quit everything: `tmux kill-session -t cars`.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
DASH="$REPO/06_Build/cars_dashboard.py"
SESSION="cars"
CTRL_LOG=/tmp/cars_controller.log
PROC_LOG=/tmp/cars_s7.log
BRIDGE_LOG=/tmp/cars_bridge.log
SNORT_ALERT=/var/log/snort/alert

[ "$(id -u)" -eq 0 ] || { echo "run with sudo (ovs-ofctl + the root-owned logs need it)"; exit 1; }
command -v tmux >/dev/null 2>&1 || { echo "MISSING: tmux (sudo apt install -y tmux)"; exit 1; }
touch "$CTRL_LOG" "$PROC_LOG" "$BRIDGE_LOG" 2>/dev/null || true

# --- launch the web topology dashboard (retargeted to the emulation controller) ---
DASH_PID=""
if [ -f "$DASH" ] && command -v python3 >/dev/null 2>&1; then
  pkill -f cars_dashboard.py 2>/dev/null || true
  CARS_URL="http://127.0.0.1:8080" python3 "$DASH" >/tmp/cars_dashboard.log 2>&1 &
  DASH_PID=$!
  sleep 1
  if kill -0 "$DASH_PID" 2>/dev/null; then
    echo "web topology: http://localhost:8090   (log /tmp/cars_dashboard.log)"
  else
    echo "note: web dashboard did not start (see /tmp/cars_dashboard.log); the terminal grid still works."
    DASH_PID=""
  fi
fi

FLOWS='for b in ovs1 ovsgw ovs2; do echo "== $b =="; ovs-ofctl -O OpenFlow13 dump-flows $b 2>/dev/null | grep -E "cookie=0x(ca|a2)|priority=55," || echo "  (none yet)"; done'

C1="clear; printf '\033[1;36m== CONTROLLER: GUARD installs + BRAIN decisions (ISOLATE / auto-heal) ==\033[0m\n'; tail -n 25 -f $CTRL_LOG"
C2="clear; printf '\033[1;33m== FLOWS: 0xa2 allow | 0xca reactive isolate | p55 default-deny ==\033[0m\n'; watch -t -c -n1 '$FLOWS'"
C3="clear; printf '\033[1;32m== PROCESS: tank loop — level / pump / interference ==\033[0m\n'; tail -n 25 -f $PROC_LOG"
C4="clear; printf '\033[1;35m== DPI: Snort alerts + operation-aware bridge REPORTs ==\033[0m\n'; tail -n 25 -f $BRIDGE_LOG $SNORT_ALERT 2>/dev/null"

tmux kill-session -t "$SESSION" 2>/dev/null || true
tmux new-session -d -s "$SESSION" -x "$(tput cols 2>/dev/null || echo 220)" -y "$(tput lines 2>/dev/null || echo 50)"
tmux set-option -t "$SESSION" -g mouse on 2>/dev/null || true
tmux send-keys -t "$SESSION:0.0" "$C1" C-m
tmux split-window -t "$SESSION:0" ;  tmux send-keys -t "$SESSION:0.1" "$C2" C-m
tmux split-window -t "$SESSION:0" ;  tmux send-keys -t "$SESSION:0.2" "$C3" C-m
tmux split-window -t "$SESSION:0" ;  tmux send-keys -t "$SESSION:0.3" "$C4" C-m
tmux select-layout -t "$SESSION:0" tiled

# clean up the web dashboard when the tmux session ends
( while tmux has-session -t "$SESSION" 2>/dev/null; do sleep 2; done
  [ -n "$DASH_PID" ] && kill "$DASH_PID" 2>/dev/null || true ) &

tmux attach -t "$SESSION"
