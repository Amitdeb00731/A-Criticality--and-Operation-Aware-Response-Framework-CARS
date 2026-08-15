#!/usr/bin/env bash
# ============================================================================
# night_lib.sh — shared helpers for the overnight CARS stress campaign.
# Source this from every night_*.sh. Runs on Dell 1. READ the runbook first.
# Safety: cookie-scoped deletes only; green-check + self-heal each cycle; the
# live process is never frozen (no del-controller). Single clock for all MTTM.
# ============================================================================
API="${API:-http://10.10.10.1:8080}"
TOKEN="$(cat /home/msclab/cars/api_token 2>/dev/null)"
ALERT="/var/log/snort/alert"
NIGHT_ROOT="${NIGHT_ROOT:-$HOME/night_$(date +%Y%m%d)}"
mkdir -p "$NIGHT_ROOT"/{logs,pcap,flows}
# attacker vantage points (namespaces on Dell 1) + real Kali
NS_ATK="atkns"; IP_ATK="192.168.2.66"        # unregistered on-segment
NS_OP="opns";   IP_OP="192.168.2.31"         # compromised-but-allowlisted SCADA
NS_MB="mbns";   IP_MB="192.168.2.20"         # Modbus unit vantage
PLC1="192.168.2.10"; PLC2="192.168.3.10"; HMI1="192.168.2.9"; MODBUS="192.168.2.20"
S7="/home/msclab/s7_write.py"; MBATK="/home/msclab/mb_attack.py"; FDI="/home/msclab/cars_fdi_overflow.py"

TS(){ date '+%Y-%m-%dT%H:%M:%S'; }
log(){ echo "[$(TS)] $*" | tee -a "$NIGHT_ROOT/logs/campaign.log"; }

armstate(){ curl -s -m4 "$API/cars/defense" | python3 -c 'import sys,json;print("ARMED" if json.load(sys.stdin).get("enforce_enabled") else "DISARMED")' 2>/dev/null; }
arm(){ curl -s -m4 -X POST "$API/cars/defense" -H "X-CARS-Token: $TOKEN" -H 'Content-Type: application/json' -d '{"on":true}' >/dev/null; }

# 0xca residue count across the fabric
ca_count(){ local n=0; for br in ovs1 ovsgw; do n=$((n+$(sudo ovs-ofctl -O OpenFlow13 dump-flows $br 2>/dev/null|grep -c 0xca))); done; echo $n; }
# cookie-scoped cleanup of a single source's reactive rule (NEVER by src/dst alone)
clean_src(){ local ip="$1"; for br in ovs1 ovsgw; do sudo ovs-ofctl -O OpenFlow13 del-flows $br "cookie=0xca/-1,ip,nw_src=$ip" 2>/dev/null; done; }
clean_all_reactive(){ for br in ovs1 ovsgw; do sudo ovs-ofctl -O OpenFlow13 del-flows $br "cookie=0xca/-1" 2>/dev/null; done; }

# lightweight green-check; returns 0 if healthy. Self-heals common faults.
greencheck(){
  local ok=1
  curl -s -m4 "$API/cars/status" >/dev/null 2>&1 || { log "WARN controller API not answering"; ok=0; }
  local online; online=$(python3 -c "import json;print(json.load(open('/tmp/cars_remediation_status.json')).get('online'))" 2>/dev/null)
  [ "$online" = "1" ] || { log "WARN process/remediation not online ($online)"; ok=0; }
  [ "$(armstate)" = "ARMED" ] || { log "re-arming (was $(armstate))"; arm; }
  return $((1-ok))
}
# self-heal: kill any runaway attack loops that survived a Ctrl-C / crash (lesson: mb_client respawn)
selfheal(){ for ns in "$NS_ATK" "$NS_OP" "$NS_MB"; do sudo pkill -f "netns exec $ns" 2>/dev/null; done
  sudo pkill -f 's7_write.py' 2>/dev/null; sudo pkill -f 'mb_attack' 2>/dev/null; sudo pkill -f 'mb_client' 2>/dev/null; sleep 1; }

# ---- the core measurement: single-clock MTTM + leaked frames + response ----
# measure_attack <label> <atk_ip> <atk_ns> <launch-cmd...>
# clocks first-attack-frame-on-mirror -> reactive-flow-install (t_enforce = now - flow.duration),
# counts frames that reached the PLC port after t0 (leaked/unacted), records the response + hard_timeout.
# Resets fast via cookie-scoped delete (self-heal lifecycle sampled separately, not per attack).
measure_attack(){
  local label="$1" atk="$2" ns="$3"; shift 3
  local d="$NIGHT_ROOT/pcap"; local tag="$(date +%s)_$label"
  # short captures at mirror (t0 source) and PLC port (leak counter)
  sudo timeout 12 tcpdump -i snort0 -nn -tt -U "host $atk" -w "$d/mir_$tag.pcap" 2>/dev/null & local CM=$!
  sudo timeout 12 tcpdump -i enx9c69d331d874 -nn -tt -U "host $atk and host $PLC1" -w "$d/plc_$tag.pcap" 2>/dev/null & local CP=$!
  sleep 0.3
  local t_launch; t_launch=$(date +%s.%N)
  ( "$@" ) >/dev/null 2>&1 &                    # launch the attack (caller supplies the client cmd)
  local te="" dur="" hto=""
  for i in $(seq 1 400); do                     # poll ~8s for the reactive install
    local line; line=$(sudo ovs-ofctl -O OpenFlow13 dump-flows ovsgw 2>/dev/null | grep -m1 -E "0xca.*nw_src=$atk")
    if [ -n "$line" ]; then
      local tp; tp=$(date +%s.%N)
      dur=$(echo "$line"|grep -oE 'duration=[0-9.]+'|cut -d= -f2)
      hto=$(echo "$line"|grep -oE 'hard_timeout=[0-9]+'|cut -d= -f2)
      te=$(python3 -c "print(f'{$tp-$dur:.6f}')" 2>/dev/null)
      break
    fi; sleep 0.02
  done
  sleep 0.5; sudo pkill -f "netns exec $ns" 2>/dev/null; sleep 1.5
  sudo pkill -f "mir_$tag"; sudo pkill -f "plc_$tag"; wait 2>/dev/null
  # first attack frame at the mirror = t0
  local t0; t0=$(sudo tcpdump -nn -tt -r "$d/mir_$tag.pcap" "src $atk" 2>/dev/null | head -1 | awk '{print $1}')
  # leaked frames = attacker frames seen at the PLC port at/after t0 (passed the fabric)
  local leaked; leaked=$(sudo tcpdump -nn -r "$d/plc_$tag.pcap" "src $atk" 2>/dev/null | wc -l)
  local mttm=""
  [ -n "$te" ] && [ -n "$t0" ] && mttm=$(python3 -c "print(f'{($te-$t0)*1000:.2f}')" 2>/dev/null)
  local resp="NONE"; [ -n "$line" ] && resp=$(echo "$line"|grep -oiE 'actions=drop' >/dev/null && echo ISOLATE_or_BLOCK || echo OTHER)
  echo "$(TS),$label,$atk,${t0:-NA},${te:-NA},${mttm:-NA},${resp},${hto:-NA},${leaked:-NA}" >> "$NIGHT_ROOT/logs/mttm_all.csv"
  log "  $label mttm=${mttm:-NA}ms leaked=${leaked:-NA} resp=$resp hto=${hto:-NA}"
  clean_src "$atk"                              # fast reset (cookie-scoped)
  rm -f "$d/mir_$tag.pcap" "$d/plc_$tag.pcap"   # keep logs lean; summary lives in the CSV
}

mttm_header(){ [ -f "$NIGHT_ROOT/logs/mttm_all.csv" ] || echo "ts,label,atk,t0,t_enforce,mttm_ms,response,hard_timeout,leaked_frames" > "$NIGHT_ROOT/logs/mttm_all.csv"; }
