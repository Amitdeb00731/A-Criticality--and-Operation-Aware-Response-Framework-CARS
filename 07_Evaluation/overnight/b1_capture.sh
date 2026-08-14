#!/usr/bin/env bash
# B1 - baseline normal-traffic characterisation (READ-ONLY capture).
# Run on Dell 1 with the rig ARMED and GREEN and NO attack running.
# It only sniffs the mirror and reads switch counters; it installs/changes nothing.
#
# Usage:  ./b1_capture.sh [seconds] [mirror_if] [bridge]
#   first validation run:  ./b1_capture.sh 60
#   real baseline window:  ./b1_capture.sh 900          (15 min of steady state)
set -u
DUR="${1:-300}"
MIRROR="${2:-snort0}"        # Snort mirror interface: sees all gateway OT data-plane traffic
BR="${3:-ovsgw}"
D=~/overnight_$(date +%Y%m%d)/b1; mkdir -p "$D"

echo "[B1] $(date) capturing ${DUR}s on ${MIRROR}, bridge ${BR} -> ${D}"
# 1) switch port counters (totals) at start
sudo ovs-ofctl -O OpenFlow13 dump-ports "$BR" > "$D/ports_start.txt" 2>&1
# 2) bounded packet capture of all OT data-plane traffic (headers only, -s 128)
sudo timeout "$DUR" tcpdump -i "$MIRROR" -nn -tt -s 128 -w "$D/baseline.pcap" 2>"$D/tcpdump.log"
# 3) counters at end + the bridge's own ops/s REPORT lines over the window
sudo ovs-ofctl -O OpenFlow13 dump-ports "$BR" > "$D/ports_end.txt" 2>&1
sudo journalctl -u cars-bridge --since "-${DUR}sec" --no-pager > "$D/bridge_ops.log" 2>&1

echo "[B1] done. pcap: $(du -h "$D/baseline.pcap" 2>/dev/null | cut -f1)"
echo "[B1] copy the folder ${D} into the repo at 07_Evaluation/overnight/results/b1/ so it can be analysed."
