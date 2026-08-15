#!/usr/bin/env bash
# night_kali.sh — add the REAL Kali VM as an attacker vantage (realistic path),
# alongside the Dell-1 namespaces. Measures the on-segment pivot (.2.77 / eth1)
# at scale on the same single clock (Dell-1 mirror), and offers a real-VM DDoS.
#
# Kali has no attack namespaces of its own; it is the attacker (triple-homed:
# eth1=.2.77 OT, eth2=10.0.40.66 IT->NAT .1, eth0=mgmt). The eth2/.1 NAT pivot is
# already captured in the two-pivot section, so overnight we automate the common
# on-segment .77 case; drive the NAT pivot manually if you want it re-captured.
#
# PREREQ: passwordless SSH from Dell 1 to Kali (mgmt/eth0 up). Set KALI_SSH.
#   USE_KALI=1 KALI_SSH=msclab@<kali-mgmt-ip> ROUNDS=n bash night_kali.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; source "$HERE/night_lib.sh"
mttm_header
KALI_SSH="${KALI_SSH:-}"; ROUNDS="${ROUNDS:-1}"; GAP="${GAP:-4}"; IP_KALI="192.168.2.77"; KS7="${KS7:-/home/msclab/s7_write.py}"
[ -z "$KALI_SSH" ] && { log "night_kali: KALI_SSH not set, skipping Kali phase"; exit 0; }
ssh -o BatchMode=yes -o ConnectTimeout=5 "$KALI_SSH" true 2>/dev/null || { log "night_kali: cannot SSH to $KALI_SSH (mgmt up? key installed?), skipping"; exit 0; }

# measure a Kali-sourced single injection at the Dell-1 mirror (single clock)
measure_kali(){
  local label="$1"; shift; local d="$NIGHT_ROOT/pcap"; local tag="$(date +%s)_$label"
  sudo timeout 12 tcpdump -i snort0 -nn -tt -U "host $IP_KALI" -w "$d/kmir_$tag.pcap" 2>/dev/null &
  sudo timeout 12 tcpdump -i enx9c69d331d874 -nn -tt -U "host $IP_KALI and host $PLC1" -w "$d/kplc_$tag.pcap" 2>/dev/null &
  sleep 0.3
  ssh -o BatchMode=yes "$KALI_SSH" "$@" >/dev/null 2>&1 &
  local te="" dur="" line=""
  for i in $(seq 1 400); do
    line=$(sudo ovs-ofctl -O OpenFlow13 dump-flows ovsgw 2>/dev/null | grep -m1 -E "0xca.*nw_src=$IP_KALI")
    if [ -n "$line" ]; then local tp; tp=$(date +%s.%N); dur=$(echo "$line"|grep -oE 'duration=[0-9.]+'|cut -d= -f2)
      te=$(python3 -c "print(f'{$tp-$dur:.6f}')" 2>/dev/null); break; fi; sleep 0.02
  done
  ssh -o BatchMode=yes "$KALI_SSH" "sudo pkill -f s7_write; sudo pkill -f ping" 2>/dev/null
  sleep 1; sudo pkill -f "kmir_$tag"; sudo pkill -f "kplc_$tag"; wait 2>/dev/null
  local t0; t0=$(sudo tcpdump -nn -tt -r "$d/kmir_$tag.pcap" "src $IP_KALI" 2>/dev/null|head -1|awk '{print $1}')
  local leaked; leaked=$(sudo tcpdump -nn -r "$d/kplc_$tag.pcap" "src $IP_KALI" 2>/dev/null|wc -l)
  local mttm=""; [ -n "$te" ] && [ -n "$t0" ] && mttm=$(python3 -c "print(f'{($te-$t0)*1000:.2f}')" 2>/dev/null)
  echo "$(TS),$label,$IP_KALI,${t0:-NA},${te:-NA},${mttm:-NA},$([ -n "$line" ] && echo ISOLATE_or_BLOCK || echo NONE),$(echo "$line"|grep -oE 'hard_timeout=[0-9]+'|cut -d= -f2),${leaked:-NA}" >> "$NIGHT_ROOT/logs/mttm_all.csv"
  log "  KALI $label mttm=${mttm:-NA}ms leaked=${leaked:-NA}"
  clean_src "$IP_KALI"; rm -f "$d/kmir_$tag.pcap" "$d/kplc_$tag.pcap"
}

log "Kali vantage: $ROUNDS round(s) from the real VM (.2.77, eth1)"
for r in $(seq 1 "$ROUNDS"); do
  measure_kali kali_connect  sudo python3 "$KS7" --host "$PLC1" --read --count 1; sleep "$GAP"
  measure_kali kali_control  sudo python3 "$KS7" --host "$PLC1" --storm --secs 2 --hz 10; sleep "$GAP"
  measure_kali kali_stop     sudo python3 "$KS7" --host "$PLC1" --stop; sleep "$GAP"
  greencheck || { selfheal; arm; }
done

# optional real-VM sustained flood (honest: a continuous flood is cut in ~1 s, not 7.6 ms)
if [ "${KALI_DDOS:-0}" = "1" ]; then
  log "Kali real-VM sustained flood (${KALI_DDOS_DUR:-120}s) — leak window, not single-injection MTTM"
  ssh -o BatchMode=yes "$KALI_SSH" "sudo timeout ${KALI_DDOS_DUR:-120} ping -I eth1 -i 0.02 $PLC1" >/dev/null 2>&1 &
  sleep $(( ${KALI_DDOS_DUR:-120} + 5 )); clean_src "$IP_KALI"; greencheck || arm
fi
log "Kali vantage done"
