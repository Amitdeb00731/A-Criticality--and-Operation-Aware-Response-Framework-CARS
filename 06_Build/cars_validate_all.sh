#!/bin/bash
# ============================================================================================
# CARS PLC2-4  —  CONSOLIDATED BOTH-CELLS END-TO-END VALIDATION.   sudo bash cars_validate_all.sh  (Dell#1)
# General (A2 default-deny, DEFLECT, GUARD, self-heal) + ICS (Modbus 5 classes, S7 both real PLCs)
# + agendas (A1/A2/A3/A4) + additions (hot-reload, maintenance, arm/disarm).  One PASS/FAIL verdict.
#
# Rule-0 correctness of the HARNESS itself (v2):
#  - PASS is matched against the DIFF of NEW audit lines (lines added since the attack), never a stale line,
#    and patterns are PROTOCOL-tagged (S7 / MODBUS) so one op can't match another cell's leftover decision.
#  - Each ICS check first clears the source's reactive ISOLATE (priority-110 nw_src drop) so every op can reach
#    the wire independently — otherwise the first CONTROL escalates the source to a full quarantine and later
#    ops never get a TCP connection (no packet -> no Snort alert -> no decision). Escalation itself is shown in SEC4.
#  - NOTE: defense is ARMED and S7 writes are --val 0, so NO relay motion is expected here; audible proof = the
#    arm/disarm showcases (PLC1 + PLC2-3). This run proves detection + discrimination + enforcement + additions.
# ============================================================================================
set -u
API=http://10.10.10.1:8080/cars; S7=/home/msclab/s7_write.py
PLC1=192.168.2.10; PLC2=192.168.3.10; MB=192.168.2.20; OPR=192.168.2.31; ATK=192.168.2.66
pass=0; fail=0
line(){ echo "--------------------------------------------------------------------------------"; }
step(){ echo; read -rp "        [ Enter to continue ] " _ || true; echo; }
audit_all(){ curl -s $API/audit | python3 -c "import json,sys;print(chr(10).join(json.load(sys.stdin)['audit']))" 2>/dev/null; }
restore(){ curl -s -XPOST $API/restore  -H 'Content-Type: application/json' -d "{\"src\":\"$1\",\"dst\":\"$2\",\"dpid\":3}" >/dev/null; }
defense(){ curl -s -XPOST $API/defense  -H 'Content-Type: application/json' -d "{\"on\":$1}" >/dev/null; }
maint(){   curl -s -XPOST $API/maintenance -H 'Content-Type: application/json' -d "{\"minutes\":$1}" >/dev/null; }
healsrc(){ for sw in ovs1 ovsgw; do ovs-ofctl -O OpenFlow13 --strict del-flows "$sw" "table=1,priority=110,ip,nw_src=$1" 2>/dev/null; done; }
ckv(){ if [ "$2" = ok ]; then echo "  [PASS]  $1"; pass=$((pass+1)); else echo "  [FAIL]  $1"; fail=$((fail+1)); fi; [ -n "${3:-}" ] && echo "          $3"; }
# expect LABEL WANT-RE SRC DST  <attack cmd...>  : heal src, fire, diff new audit lines, match protocol-tagged pattern.
# 3-attempt retry: a single snap7/modbus connect can be dropped after heavy isolate churn -> refire so a lost first
# packet doesn't fail a check (the CAPABILITY is what we test; a dropped connect is transport flakiness, not a decision).
expect(){ local label="$1" want="$2" src="$3" dst="$4"; shift 4
  local before after new i a hit=""
  for a in 1 2 3; do
    restore "$src" "$dst"; healsrc "$src"; sleep 1
    before=$(audit_all); "$@" >/dev/null 2>&1
    for i in $(seq 1 14); do sleep 0.4; after=$(audit_all)
      new=$(grep -vxFf <(echo "$before") <(echo "$after") 2>/dev/null)
      echo "$new" | grep -qE "$want" && break; done
    hit=$(echo "$new" | grep -E "$want" | tail -1); [ -n "$hit" ] && break
  done
  if [ -n "$hit" ]; then echo "  [PASS]  $label"; echo "          $hit"; pass=$((pass+1))
  else echo "  [FAIL]  $label  (wanted /$want/)"; echo "          last-new: $(echo "$new" | tail -1)"; fail=$((fail+1)); fi; }

clear
echo "################  CARS  —  CONSOLIDATED BOTH-CELLS VALIDATION (PLC2-4)  ################"
echo "[setup] Modbus sim up, defense ARMED, relays reset, sources restored ..."
pgrep -f mb_server.py >/dev/null || { ip netns exec mbns python3 /home/msclab/mb_server.py $MB >/dev/null 2>&1 & sleep 2; }
defense true; maint 0
for s in $OPR $ATK 192.168.3.66; do healsrc "$s"; done
restore $OPR $PLC1; restore $OPR $MB; restore 192.168.3.66 $PLC2
ip netns exec opns python3 $S7 --host $PLC1 --val 0 --count 1 >/dev/null 2>&1
python3 $S7 --host $PLC2 --val 0 --count 1 >/dev/null 2>&1
echo "        ready. both relays OFF, guard ARMED. (no relay motion expected — see setup note.)"
step

# === SEC 1 — ICS OPERATION-AWARENESS (A3), BOTH REAL PLCs + MODBUS ===========================
line; echo " SEC 1  ICS OPERATION-AWARENESS (A3)  —  same station/PLC/port, opposite outcomes"; line
echo " PLC1 / TB1 (real, .2.10):"
expect "PLC1 S7 READ  -> ALLOW"          "S7 *READ =>.*ALLOW"              $OPR $PLC1  ip netns exec opns python3 $S7 --host $PLC1 --read
expect "PLC1 S7 WRITE -> CONTROL/FORBID" "S7 *CONTROL => *(BLOCK|ISOLATE)" $OPR $PLC1  ip netns exec opns python3 $S7 --host $PLC1 --val 0 --count 1
expect "PLC1 S7 STOP  -> DIAG/FORBID"    "S7 *DIAG => *(BLOCK|ISOLATE)"    $OPR $PLC1  ip netns exec opns python3 $S7 --host $PLC1 --stop
echo " PLC2 / TB2 (real, .3.10, cross-NAT from Cell-1 .3.66):"
expect "PLC2 S7 READ  -> ALLOW"          "S7 *READ =>.*ALLOW"              192.168.3.66 $PLC2  python3 $S7 --host $PLC2 --read
expect "PLC2 S7 WRITE -> CONTROL/FORBID" "S7 *CONTROL => *(BLOCK|ISOLATE)" 192.168.3.66 $PLC2  python3 $S7 --host $PLC2 --val 0 --count 1
echo " Modbus sim (.2.20) — full FC taxonomy:"
expect "Modbus READ    -> ALLOW"         "MODBUS READ =>.*ALLOW"             $OPR $MB  ip netns exec opns python3 /home/msclab/mb_client.py --host $MB --op read
expect "Modbus coil    -> CONTROL"       "MODBUS CONTROL => *(BLOCK|ISOLATE)" $OPR $MB  ip netns exec opns python3 /home/msclab/mb_attack.py --host $MB --attack coil
expect "Modbus diag    -> DIAG"          "MODBUS DIAG => *(BLOCK|ISOLATE)"    $OPR $MB  ip netns exec opns python3 /home/msclab/mb_attack.py --host $MB --attack diag
expect "Modbus program -> PROGRAM"       "MODBUS PROGRAM => *(BLOCK|ISOLATE)" $OPR $MB  ip netns exec opns python3 /home/msclab/mb_attack.py --host $MB --attack program
expect "Modbus illegal -> ILLEGAL"       "MODBUS ILLEGAL => *(BLOCK|ISOLATE)" $OPR $MB  ip netns exec opns python3 /home/msclab/mb_attack.py --host $MB --attack illegal
step

# === SEC 2 — A2 PROACTIVE DEFAULT-DENY (unlisted conduit dropped) ============================
line; echo " SEC 2  A2 PROACTIVE DEFAULT-DENY  —  listed operator allowed, unlisted attacker denied"; line
healsrc $OPR; restore $OPR $MB; sleep 1     # clear the ISOLATE SEC1 left on the operator source
OPR_OUT=$(ip netns exec opns  python3 /home/msclab/mb_client.py --host $MB --op read 2>&1 | tr '\n' ' ' | tail -c 70)
ATK_OUT=$(timeout 7 ip netns exec atkns python3 /home/msclab/mb_client.py --host $MB --op read 2>&1 | tr '\n' ' ' | tail -c 70)
echo "   operator .2.31 -> mbplc read : $OPR_OUT"
echo "   attacker .2.66 -> mbplc read : $ATK_OUT"
DENY_RE="time?out|refused|error|unreach|no route|fail|none|block"
opok=1;    echo "$OPR_OUT" | grep -qiE "$DENY_RE" && opok=0
atkdenied=0; { [ -z "$ATK_OUT" ] || echo "$ATK_OUT" | grep -qiE "$DENY_RE"; } && atkdenied=1
if [ "$atkdenied" = 1 ] && [ "$opok" = 1 ]; then ckv "A2 default-deny: listed operator OK, unlisted .2.66 denied" ok
else ckv "A2 default-deny (listed allowed / unlisted denied)" bad "opr=[$OPR_OUT] atk=[$ATK_OUT]"; fi
step

# === SEC 3 — A1 REACTIVE: DEFLECT round-trip + ISOLATE flow present ==========================
line; echo " SEC 3  A1 REACTIVE  —  DEFLECT deception round-trip + ISOLATE quarantine flow"; line
ip netns exec atkns ping -c1 -W1 $PLC1 >/dev/null 2>&1     # warm-up so the controller learns .2.66's port/mac (reverse path)
sleep 1; healsrc $ATK                                      # ensure DEFLECT(105) isn't shadowed by any ISOLATE(110)
curl -s -XPOST $API/respond -H 'Content-Type: application/json' -d "{\"src\":\"$ATK\",\"dst\":\"$PLC1\",\"proto\":\"TCP\",\"dpid\":3,\"force\":\"DEFLECT\"}" >/dev/null; sleep 1
DFL=$(ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep -m1 "priority=105.*set_field" | tr -s ' ' | tail -c 110)
PING=$(ip netns exec atkns ping -c2 -W2 $PLC1 2>&1 | grep -E "ttl=|packet loss" | tr '\n' ' ')
echo "   deflect flow : $DFL"
echo "   attacker ping PLC1 (informational; full ttl=64 round-trip proven in CC-45/e2e): $PING"
if echo "$DFL" | grep -q "192.168.3.99->ip_dst"; then
  ckv "DEFLECT: attacker's PLC-bound traffic actively redirected to decoy .3.99 (deception engaged)" ok
  echo "$PING" | grep -q "ttl=64" && echo "          + live round-trip also observed this run (ttl=64)"
else ckv "DEFLECT: redirect flow installed" bad "flow=[$DFL]"; fi
for sw in ovsgw ovs1; do ovs-ofctl -O OpenFlow13 del-flows "$sw" "table=1,ip,nw_src=$ATK" 2>/dev/null; done
restore $OPR $PLC1; healsrc $OPR; sleep 1
ip netns exec opns python3 $S7 --host $PLC1 --val 0 --count 2 >/dev/null 2>&1; sleep 2   # drive .2.31 to block/isolate
ISO=$(ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep -m1 "actions=drop" | tr -s ' ' | tail -c 90)
echo "   quarantine flow on ovsgw: $ISO"
if echo "$ISO" | grep -q "actions=drop"; then ckv "ISOLATE/BLOCK: src-drop flow installed on the switch" ok; else ckv "ISOLATE/BLOCK flow installed" bad; fi
step

# === SEC 4 — GUARD anti-spoof (T0) + SELF-HEAL auto-expiry ===================================
line; echo " SEC 4  GUARD anti-spoof bindings (T0) + SELF-HEAL (block auto-expires when attack stops)"; line
G=$(ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=0 | grep -cE "arp|dl_src|nw_src")
echo "   T0 GUARD entries present: $G  (anti-spoof src/MAC bindings — measured; live-spoof injection not fired here)"
if [ "$G" -gt 0 ]; then ckv "GUARD: anti-spoof binding table active in T0" ok; else ckv "GUARD table active" bad; fi
healsrc $OPR; restore $OPR $PLC1; sleep 1
B0=0                                   # establish a real block first (retry attack until the drop flow appears)
for a in 1 2 3 4; do
  ip netns exec opns python3 $S7 --host $PLC1 --val 0 --count 2 >/dev/null 2>&1
  for i in $(seq 1 8); do B0=$(ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep -c "nw_src=192.168.2.31.*actions=drop"); [ "$B0" -ge 1 ] && break; sleep 0.5; done
  [ "$B0" -ge 1 ] && break
done
# the isolated connection's malicious S7 PDU keeps TCP-retransmitting and re-triggering detection (renewing the
# hard_timeout) until the attacker truly goes silent -> kill it, then poll past the retransmit tail + 30s heal.
pkill -f "s7_write.py --host $PLC1" 2>/dev/null; sleep 1
echo "   block on .2.31 now: $B0 flow(s). Attacker stopped; polling up to ~90s for auto-heal ..."
B1=$B0; ht=0
for i in $(seq 1 18); do sleep 5; ht=$((i*5)); B1=$(ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep -c "nw_src=192.168.2.31.*actions=drop"); [ "$B1" -eq 0 ] && break; done
echo "   block on .2.31 after ~${ht}s: $B1 flow(s)."
if [ "$B0" -ge 1 ] && [ "$B1" -eq 0 ]; then ckv "SELF-HEAL: block auto-expired ${ht}s after attack stopped" ok; else ckv "SELF-HEAL auto-expiry (still blocked after ${ht}s)" bad "before=$B0 after=$B1"; fi
step

# === SEC 5 — ADDITIONS: hot-reload, maintenance window, arm/disarm ===========================
line; echo " SEC 5  ADDITIONS  —  A2 hot-reload (no restart) + maintenance window + defense toggle"; line
RL=$(curl -s -XPOST $API/reload-a2 -H 'Content-Type: application/json' -d '{}')
echo "   POST /reload-a2 : $RL"
if echo "$RL" | grep -qiE "reload|allow"; then ckv "FEAT-1: A2 proactive policy hot-reloaded WITHOUT controller restart" ok; else ckv "FEAT-1 hot-reload" bad "$RL"; fi
maint 2
expect "FEAT-3: CONTROL waived inside maintenance window"   "MAINTENANCE-AUTHORISED"          $OPR $PLC1  ip netns exec opns python3 $S7 --host $PLC1 --val 0 --count 1
maint 0
expect "FEAT-3: CONTROL FORBIDDEN again once window closed" "S7 *CONTROL => *(BLOCK|ISOLATE)" $OPR $PLC1  ip netns exec opns python3 $S7 --host $PLC1 --val 0 --count 1
defense false
expect "PD-1: defense DISARMED -> monitor-only"            "DEFENSE DISARMED"                $OPR $PLC1  ip netns exec opns python3 $S7 --host $PLC1 --val 0 --count 1
defense true
expect "PD-1: defense ARMED -> enforced again"             "S7 *CONTROL => *(BLOCK|ISOLATE)" $OPR $PLC1  ip netns exec opns python3 $S7 --host $PLC1 --val 0 --count 1
step

# === EPILOGUE — safe state + verdict ========================================================
line; echo " EPILOGUE  —  safe state + verdict"; line
defense false
for s in $OPR $ATK 192.168.3.66; do healsrc "$s"; done
restore $OPR $PLC1; restore $OPR $MB; restore 192.168.3.66 $PLC2
ip netns exec opns python3 $S7 --host $PLC1 --val 0 --count 1 >/dev/null 2>&1
python3 $S7 --host $PLC2 --val 0 --count 1 >/dev/null 2>&1
defense true
echo "   both relays OFF | sources restored | guard ARMED"
echo
echo "================================================================================"
echo "   CARS CONSOLIDATED VERDICT :   PASS=$pass   FAIL=$fail   (total $((pass+fail)))"
if [ "$fail" -eq 0 ]; then
  echo "   ==> ALL CHECKS PASSED — both cells, general + ICS + agendas + additions validated."
else
  echo "   ==> $fail check(s) did NOT match — see [FAIL] lines above (real finding, not hidden)."
fi
echo "================================================================================"
