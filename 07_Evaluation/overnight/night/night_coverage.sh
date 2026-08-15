#!/usr/bin/env bash
# night_coverage.sh — close the covered-but-thin / not-covered items:
#   (A) full response ladder  ALLOW/MONITOR/THROTTLE/DEFLECT/ISOLATE/BLOCK/REFUSE
#   (B) four-tier + Cell-2 sweep (CRITICAL PLC1, HIGH PLC2, MEDIUM historian, LOW Modbus)
#   (C) GUARD anti-spoof probe (spoofed identity -> drop counter)
#   (D) authenticated-API probe (unauth control -> 401, CARS stays armed)
# All bounded and unattended-safe; cookie-scoped cleanup; green-check at the end.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; source "$HERE/night_lib.sh"; mttm_header
LC="$NIGHT_ROOT/logs/ladder.csv";   [ -f "$LC" ] || echo "ts,response_tested,src,dst,verdict,rule" > "$LC"
CC="$NIGHT_ROOT/logs/controlplane.csv"; [ -f "$CC" ] || echo "ts,probe,detail,outcome" > "$CC"
respond(){ curl -s -m5 -X POST "$API/cars/respond" -H 'Content-Type: application/json' -d "$1"; }
verdict_of(){ echo "$1"|python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("response"),d.get("tier"))' 2>/dev/null; }

log "coverage: response ladder + tier sweep + GUARD + auth-API"

# ---- (A) response ladder ----------------------------------------------------
# ALLOW: trusted read of the critical PLC (decision-only, installs nothing)
v=$(verdict_of "$(respond '{"src":"192.168.2.31","dst":"192.168.2.10","op":"READ","proto":"S7","dpid":3}')"); echo "$(TS),ALLOW,192.168.2.31,192.168.2.10,$v,none" >> "$LC"
# REFUSE: the safety loop HMI->PLC control (mirrored, never cut)
v=$(verdict_of "$(respond '{"src":"192.168.2.9","dst":"192.168.2.10","op":"CONTROL","proto":"S7","dpid":3}')"); echo "$(TS),REFUSE,192.168.2.9,192.168.2.10,$v,none" >> "$LC"
# THROTTLE: trusted SENSITIVE write to a LOW asset, first offence (installs a meter)
v=$(verdict_of "$(respond '{"src":"192.168.2.31","dst":"192.168.2.20","op":"WRITE","proto":"MB","dpid":3}')")
mrule=$(sudo ovs-ofctl -O OpenFlow13 dump-flows ovsgw 2>/dev/null|grep -m1 '0xca.*meter'|grep -oE 'meter:[0-9]+'||echo none)
echo "$(TS),THROTTLE,192.168.2.31,192.168.2.20,$v,$mrule" >> "$LC"; clean_src 192.168.2.31
# DEFLECT: force the deception path (installs a redirect to the honeypot), then clean
v=$(verdict_of "$(respond '{"src":"192.168.2.66","dst":"192.168.2.10","op":"CONTROL","proto":"S7","dpid":3,"force":"DEFLECT"}')")
drule=$(sudo ovs-ofctl -O OpenFlow13 dump-flows ovsgw 2>/dev/null|grep -m1 '0xca.*set_field.*192.168.3.99'|grep -oE 'priority=[0-9]+'||echo redirect)
echo "$(TS),DEFLECT,192.168.2.66,192.168.2.10,$v,$drule" >> "$LC"; clean_src 192.168.2.66
# ISOLATE + BLOCK are exercised at scale by the attack battery; MONITOR is the ALLOW-with-record case.
log "  ladder: ALLOW/REFUSE/THROTTLE/DEFLECT recorded; ISOLATE/BLOCK from the battery"

# ---- (B) four-tier ladder via the enforcement API -------------------------
# The unregistered vantage is segmented off the LOW Modbus unit and Cell-2 (confirmed in
# the dry-run: .2.20 and .3.10 are unreachable, a positive result), and only PLC1 exposes
# S7 - so a physical storm cannot reach every tier. The criticality->hard_timeout ladder is
# a controller policy, so we drive the enforcement API per tier and read back the REAL
# installed rule's hard_timeout (respond installs the same rule the snort bridge would).
TL="$NIGHT_ROOT/logs/tierladder.csv"; [ -f "$TL" ] || echo "ts,dst,crit,response,hard_timeout_installed,cars_ms" > "$TL"
tier_probe(){ local dst="$1"
  local r; r=$(respond "{\"src\":\"$IP_ATK\",\"dst\":\"$dst\",\"op\":\"CONTROL\",\"proto\":\"S7\",\"dpid\":3}")
  local crit resp cms
  crit=$(echo "$r"|python3 -c 'import sys,json;print(json.load(sys.stdin).get("crit"))' 2>/dev/null)
  resp=$(echo "$r"|python3 -c 'import sys,json;print(json.load(sys.stdin).get("response"))' 2>/dev/null)
  cms=$(echo "$r"|python3 -c 'import sys,json;print(json.load(sys.stdin).get("cars_ms"))' 2>/dev/null)
  sleep 0.5
  local hto; hto=$(sudo ovs-ofctl -O OpenFlow13 dump-flows ovsgw 2>/dev/null|grep -m1 "0xca.*nw_src=$IP_ATK"|grep -oE 'hard_timeout=[0-9]+'|cut -d= -f2)
  echo "$(TS),$dst,${crit},${resp},${hto:-NA},${cms}" >> "$TL"
  log "  tier $dst crit=$crit resp=$resp hto_installed=${hto:-NA}s"
  clean_src "$IP_ATK"; sleep 1
}
tier_probe 192.168.2.10   # CRITICAL PLC1     -> expect 75
tier_probe 192.168.3.10   # HIGH PLC2         -> expect 60
tier_probe 192.168.2.30   # MEDIUM historian  -> expect 45
tier_probe 192.168.2.20   # LOW Modbus        -> expect 30
# segmentation positive control: the unregistered vantage must NOT reach the low tiers
for d in 192.168.2.20 192.168.3.10; do
  sudo ip netns exec "$NS_ATK" ping -c1 -W1 "$d" >/dev/null 2>&1 && seg=REACHABLE_investigate || seg=segmented_ok
  echo "$(TS),segmentation,atk_to_$d,$seg" >> "$CC"
done
log "  tier ladder done (crit->hard_timeout in tierladder.csv); segmentation recorded"

# ---- (C) GUARD anti-spoof probe --------------------------------------------
g0=$(curl -s -m4 "$API/cars/guard" 2>/dev/null | python3 -c 'import sys,json;print(sum(json.load(sys.stdin).get("drops",{}).values()))' 2>/dev/null || echo NA)
# spoof a protected identity (.55 EWS and .10 PLC) from the attacker port -> GUARD drop
sudo ip netns exec "$NS_ATK" python3 - <<'PY' 2>/dev/null
try:
  from scapy.all import Ether,ARP,IP,ICMP,sendp,send,conf; conf.verb=0
  for spoof in ("192.168.2.55","192.168.2.10","192.168.2.9"):
    sendp(Ether()/ARP(op=2,psrc=spoof,pdst="192.168.2.10"),count=5)
    send(IP(src=spoof,dst="192.168.2.10")/ICMP(),count=5)   # L3 send: GUARD ip-binding registers the drop
except Exception as e: print("guard-probe",e)
PY
sleep 3
g1=$(curl -s -m4 "$API/cars/guard" 2>/dev/null | python3 -c 'import sys,json;print(sum(json.load(sys.stdin).get("drops",{}).values()))' 2>/dev/null || echo NA)
echo "$(TS),guard_antispoof,drops_before=$g0 after=$g1,$([ "$g1" != "$g0" ] && echo SPOOF_DROPPED || echo check_counter)" >> "$CC"
log "  GUARD anti-spoof: drops $g0 -> $g1"

# ---- (D) authenticated-API probe (must be refused, CARS stays armed) --------
for ep in defense restore reload; do
  code=$(curl -s -o /dev/null -m5 -w '%{http_code}' -X POST "$API/cars/$ep" -H 'Content-Type: application/json' -d '{"on":false}' 2>/dev/null)
  echo "$(TS),authapi,unauth_POST_/cars/$ep,HTTP_$code$([ "$code" = 401 ] && echo _REFUSED)" >> "$CC"
done
echo "$(TS),authapi,armstate_after_unauth,$(armstate)" >> "$CC"
log "  auth-API: unauth control refused; armstate=$(armstate)"

clean_all_reactive; selfheal; greencheck || arm
log "coverage pass done"
