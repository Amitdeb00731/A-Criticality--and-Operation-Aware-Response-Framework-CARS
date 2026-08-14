#!/usr/bin/env bash
# Points 9b / 7 / 10: monitor the LEGITIMATE process and the reactive-rule lifecycle while an
# attack is fired under ARMED CARS. Answers: does firing a defensive measure harm the legit
# process (9b)? does the system self-heal to normal (7)? and records every flow install/withdraw (10).
#
# Run this FIRST, then fire the attack ~20 s in from your attacker vantage (see command below).
# READ-ONLY except that it reads /tmp status and dumps flows; it installs nothing itself.
#
# Usage:  ./e_attack_monitor.sh <seconds> <attacker_ip> [bridge]
#   e.g.  ./e_attack_monitor.sh 180 192.168.2.31
set -u
DUR="${1:-180}"; ATK="${2:?attacker IP, e.g. 192.168.2.31}"; BR="${3:-ovsgw}"
D=~/overnight_$(date +%Y%m%d)/attack; mkdir -p "$D/flows"
CSV="$D/monitor.csv"; echo "ts,level,restores,legit_est,ca_count,atk_isolated,atk_hardto" > "$CSV"
echo "[ATK-MON] armed monitor for ${DUR}s, attacker=${ATK}. FIRE THE ATTACK ~20 s in."
prev_ca=0
end=$((SECONDS+DUR))
while [ $SECONDS -lt $end ]; do
  read lvl res < <(python3 -c 'import json;d=json.load(open("/tmp/cars_remediation_status.json"));print(d.get("level"),d.get("restores"))' 2>/dev/null || echo "NA NA")
  fl=$(sudo ovs-ofctl -O OpenFlow13 dump-flows "$BR" 2>/dev/null)
  est=$(echo "$fl" | grep -E "priority=85" | grep -oE "n_packets=[0-9]+" | head -1 | cut -d= -f2)
  ca=$(echo "$fl"  | grep -ci 0xca)
  iso=$(echo "$fl" | grep -i "0xca" | grep -c "nw_src=${ATK}")
  hto=$(echo "$fl" | grep -i "0xca" | grep "nw_src=${ATK}" | grep -oE "hard_timeout=[0-9]+" | head -1 | cut -d= -f2)
  echo "$(date +%s),${lvl},${res},${est},${ca},${iso:-0},${hto:-}" >> "$CSV"
  # snapshot the full table at each reactive-state change (install / withdraw) for the lifecycle ledger
  if [ "${ca:-0}" != "$prev_ca" ]; then echo "$fl" > "$D/flows/flows_$(date +%s)_ca${ca}.txt"; prev_ca=${ca:-0}; fi
  sleep 1
done
echo "[ATK-MON] done -> ${CSV} ; flow snapshots (install/withdraw) in ${D}/flows/"
echo "[ATK-MON] copy ~/overnight_$(date +%Y%m%d)/attack into the repo results/ for analysis."
