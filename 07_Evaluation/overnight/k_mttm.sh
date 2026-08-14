#!/usr/bin/env bash
# Kali realism MTTM. The attack is a CONTINUOUS ICMP flood fired from the REAL Kali VM (.77) to PLC1,
# started separately on Kali. This Dell-1 harness measures each restore -> re-isolate cycle:
#   T0 = first .77 frame at the mirror after restore (pcap), T4 = isolate install (t_poll - flow.duration).
# Both timestamps are on Dell 1's clock (single clock, no skew); only the attacker PATH differs from the
# namespace run, so the delta is the real attacker-path overhead. ICMP to the PLC is a harmless L3 probe.
#
# START THE KALI FLOOD FIRST (on Kali):  sudo ping -I eth1 -i 0.02 192.168.2.10
# Then run this on Dell 1:               ./k_mttm.sh [N]     (default 100 ~ 11 min)
set -u
N="${1:-100}"; ATK=192.168.2.77; BR=ovsgw
D=~/overnight_$(date +%Y%m%d)/kali; mkdir -p "$D/pcap"
CSV="$D/mttm_decomp.csv"; echo "trial,t_enforce,flow_dur,hard_to" > "$CSV"
restore(){ sudo ovs-ofctl -O OpenFlow13 del-flows "$BR" "table=1,ip,nw_src=$ATK" 2>/dev/null; }

echo "[KALI-MTTM] $N trials, attacker=$ATK  (make sure the Kali ping flood is running)"
found=0
for t in $(seq 1 "$N"); do
  # start the capture BEFORE unblocking so the first post-restore frame is captured as T0
  sudo timeout 9 tcpdump -i snort0 -nn -tt -s96 -U "icmp and host $ATK" -w "$D/pcap/t${t}.pcap" 2>/dev/null & CAP=$!
  sleep 0.3
  restore          # unblock .77 -> the continuous flood's next frame passes -> T0 at the mirror
  te=""; dur=""; hto=""
  for i in $(seq 1 450); do
    line=$(sudo ovs-ofctl -O OpenFlow13 dump-flows "$BR" 2>/dev/null | grep -m1 -E "0xca.*nw_src=$ATK")
    if [ -n "$line" ]; then
      tp=$(date +%s.%N)
      dur=$(echo "$line" | grep -oE 'duration=[0-9.]+'   | cut -d= -f2)
      hto=$(echo "$line" | grep -oE 'hard_timeout=[0-9]+' | cut -d= -f2)
      te=$(python3 -c "print(f'{$tp - $dur:.6f}')"); found=$((found+1)); break
    fi
    sleep 0.02
  done
  sleep 0.4; kill "$CAP" 2>/dev/null; wait 2>/dev/null
  echo "$t,$te,$dur,$hto" >> "$CSV"
  echo "  trial $t: t_enforce=${te:-MISS} dur=$dur hto=$hto"
  sleep 4     # > COOLDOWN=3 so each trial's bridge dedup resets
done
restore
echo "[KALI-MTTM] done ($found/$N isolated) -> $D ; copy into repo results/ for analysis."
