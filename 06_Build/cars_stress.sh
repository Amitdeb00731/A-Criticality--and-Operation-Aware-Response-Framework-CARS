#!/bin/bash
# =============================================================================
# CARS Phase-2c — STRESS / ADVERSARIAL TRIAL.   sudo bash cars_stress.sh   (Dell#1)
# -----------------------------------------------------------------------------
# Throws normal + edge + evil + strange traffic at CARS back-to-back and, after EVERY scenario,
# re-checks the SAFETY INVARIANT:  (1) real HMI->PLC control loop still advancing (process undisturbed),
# (2) controller responsive with all 3 switches, (3) no enforcement flow ever landed on a legit conduit.
# The pass criterion is not "CARS blocked things" but "CARS blocked the RIGHT things and never harmed the
# process or legit traffic, and recovered clean." Any invariant breach = CRITICAL finding (printed FAIL).
# =============================================================================
set -u
ATK=192.168.2.66; TGT=192.168.2.10; MBPLC=192.168.2.20; OPR=192.168.2.31; HMI=192.168.2.9
API=http://10.10.10.1:8080/cars
TS=$(date +%Y%m%d_%H%M%S); OUT=$HOME/cars_forensics/stress_$TS; mkdir -p "$OUT"; V="$OUT/VERDICT.txt"; : >"$V"
say(){ echo "$1" | tee -a "$V"; }
pkts(){ ovs-ofctl -O OpenFlow13 dump-flows "$1" table=1 2>/dev/null | grep -m1 "$2" | grep -oP 'n_packets=\K[0-9]+'; }
loopc(){ pkts ovs1 "nw_src=192.168.2.9,nw_dst=192.168.2.10"; }
clean_atk(){ ovs-ofctl -O OpenFlow13 del-flows ovsgw "table=1,ip,nw_src=192.168.2.66" 2>/dev/null
             curl -s -XPOST $API/restore -H 'Content-Type: application/json' -d "{\"src\":\"$ATK\",\"dst\":\"$TGT\",\"dpid\":3}" >/dev/null; }
PASS=0; FAIL=0
# SAFETY INVARIANT after each scenario -------------------------------------------------
LPREV=$(loopc)
inv(){  # $1 = scenario label
  local l1 sw legitblock ok=1 reason=""
  sleep 3; l1=$(loopc)
  [ "${l1:-0}" -gt "${LPREV:-0}" ] || { ok=0; reason="HMI->PLC loop STALLED ($LPREV->$l1)"; }
  sw=$(curl -s --max-time 4 $API/status | python3 -c "import json,sys;print(len(json.load(sys.stdin)['switches']))" 2>/dev/null)
  [ "${sw:-0}" = "3" ] || { ok=0; reason="$reason; controller not 3-switch (got ${sw:-none})"; }
  legitblock=$(ovs-ofctl -O OpenFlow13 dump-flows ovs1 table=1 2>/dev/null | grep -E "priority=1[01]0.*nw_src=192.168.2.9" | head -1)
  [ -z "$legitblock" ] || { ok=0; reason="$reason; LEGIT HMI conduit got blocked!"; }
  if [ $ok = 1 ]; then say "   INVARIANT OK  (loop $LPREV->$l1 climbing, ctrl=3sw, no legit block)"; PASS=$((PASS+1))
  else say "   *** INVARIANT FAIL: $reason ***"; FAIL=$((FAIL+1)); fi
  LPREV=$(loopc)
}

say "===============  CARS STRESS / ADVERSARIAL TRIAL  $TS  ==============="
say "baseline: loop=$(loopc)  ctrl=$(curl -s --max-time 4 $API/status | python3 -c "import json,sys;print(sorted(json.load(sys.stdin)['switches']))" 2>/dev/null)"

# 1. STORM — high-rate flood, must contain with ONE response, no crash --------------
say ""; say "[1] STORM: 300-pkt fast ICMP flood atk->PLC"
clean_atk; sleep 1
ip netns exec atkns ping -f -c 300 $TGT >/dev/null 2>&1 || true
say "   enforcement: $(ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep -m1 nw_src=192.168.2.66 | grep -oP 'priority=1[01]0[^ ]*' )"
inv "STORM"

# 2. SCANNER — one source, many targets -> per-source ISOLATE ----------------------
say ""; say "[2] SCANNER: atk sprays 5 targets (.10 .9 .20 .30 .1) — expect per-source ISOLATE"
clean_atk; sleep 1
for d in 10 9 20 30 1; do ip netns exec atkns ping -c2 -W1 192.168.2.$d >/dev/null 2>&1; done
iso=$(ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep -m1 "priority=110,ip,nw_src=192.168.2.66")
say "   ISOLATE flow: ${iso:-<none>}"
inv "SCANNER"

# 3. LEGIT-UNDER-FIRE — operator must succeed WHILE attacker floods (no collateral) --
say ""; say "[3] LEGIT-UNDER-FIRE: operator Modbus READ while atk floods PLC"
clean_atk; sleep 1
ip netns exec atkns ping -f -c 400 $TGT >/dev/null 2>&1 &
lr=$(ip netns exec opns python3 /home/msclab/mb_client.py --host $MBPLC --op read 2>&1 | tr '\n' ' ' | tail -c 70)
wait 2>/dev/null
say "   operator result under fire: $lr"
echo "$lr" | grep -q "READ" && say "   -> legit traffic SURVIVED under attack (no collateral)" || say "   *** legit READ FAILED under attack ***"
inv "LEGIT-UNDER-FIRE"

# 4. MALFORMED — oversized/fragmented frames must not crash the pipeline ------------
say ""; say "[4] MALFORMED: oversized (60000B, fragmented) ICMP atk->PLC"
clean_atk; sleep 1
ip netns exec atkns ping -s 60000 -c 3 -W1 $TGT >/dev/null 2>&1 || true
say "   controller still up: $(curl -s --max-time 4 $API/status >/dev/null && echo yes || echo NO)"
inv "MALFORMED"

# 5. MULTI-CELL — reactive (.10) + proactive (.20) simultaneously -------------------
say ""; say "[5] MULTI-CELL: simultaneous atk->PLC(.10 reactive) + atk->MBPLC(.20 A2-proactive)"
clean_atk; d0=$(pkts ovsgw "priority=55,ip,nw_dst=192.168.2.20"); sleep 1
ip netns exec atkns ping -f -c 200 $TGT >/dev/null 2>&1 &
ip netns exec atkns bash -c 'for i in $(seq 1 8); do timeout 1 bash -c "echo > /dev/tcp/192.168.2.20/502" 2>/dev/null; done' &
wait 2>/dev/null; d1=$(pkts ovsgw "priority=55,ip,nw_dst=192.168.2.20")
say "   reactive .10 enforce: $(ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep -m1 -oP 'priority=1[01]0,ip,nw_src=192.168.2.66[^ ]*')"
say "   proactive .20 deny n_packets ${d0:-0}->${d1:-0} (climb = A2 pre-drop working in parallel)"
inv "MULTI-CELL"

# 6. IDS-DOWN — kill detection; A2 proactive + ovs1 deny must still protect the PLC --
say ""; say "[6] IDS-DOWN: stop cars-bridge (no reactive) — defense-in-depth must hold"
systemctl stop cars-bridge; sleep 1
g0=$(pkts ovs1 "priority=55,ip,nw_dst=192.168.2.10"); e0=$(pkts ovsgw "priority=55,ip,nw_dst=192.168.2.20")
ip netns exec atkns ping -c3 -W1 $TGT >/dev/null 2>&1
ip netns exec atkns bash -c 'for i in 1 2 3; do timeout 1 bash -c "echo > /dev/tcp/192.168.2.20/502" 2>/dev/null; done'
g1=$(pkts ovs1 "priority=55,ip,nw_dst=192.168.2.10"); e1=$(pkts ovsgw "priority=55,ip,nw_dst=192.168.2.20")
say "   with IDS DOWN: real-PLC ovs1 .10 deny ${g0:-0}->${g1:-0} ; MBPLC .20 deny ${e0:-0}->${e1:-0}"
say "   (both climbing = A2 proactive still protects the assets when detection is offline)"
systemctl start cars-bridge; sleep 2
inv "IDS-DOWN"

# 7. SPOOF — forged source of a trusted host must be dropped by table-0 GUARD -------
say ""; say "[7] SPOOF: atk forges src=HMI .9 -> expect Table-0 anti-spoof drop"
clean_atk
if ip netns exec atkns python3 -c "import scapy.all" 2>/dev/null; then
  gd0=$(curl -s $API/guard | python3 -c "import json,sys;print(sum(json.load(sys.stdin)['drops'].values()))" 2>/dev/null || echo 0)
  ip netns exec atkns python3 -c "from scapy.all import *; send(IP(src='192.168.2.9',dst='192.168.2.10')/ICMP(),count=4,verbose=0)" 2>/dev/null
  sleep 1; gd1=$(curl -s $API/guard | python3 -c "import json,sys;print(sum(json.load(sys.stdin)['drops'].values()))" 2>/dev/null || echo 0)
  say "   guard drop count ${gd0}->${gd1} (climb = forged .9 dropped at Table-0)"
else
  say "   (scapy not present in atkns — spoof drop already proven in CC-22/CC-23; skipping live send)"
fi
inv "SPOOF"

# 8. RECOVERY — after the storm, system must return to a clean, healed baseline -----
say ""; say "[8] RECOVERY: wait for self-heal, verify clean baseline"
clean_atk; say "   waiting 33s for all enforcement to auto-heal..."; sleep 33
resid=$(ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep -cE "priority=1[01]0,ip,nw_src=192.168.2.66")
lr=$(ip netns exec opns python3 /home/msclab/mb_client.py --host $MBPLC --op read 2>&1 | tr '\n' ' ' | tail -c 50)
cms=$(curl -s $API/status | python3 -c "import json,sys;d=json.load(sys.stdin);print('avg=%sms n=%s'%(d['cars_ms_avg'],d['cars_ms_n']))" 2>/dev/null)
say "   residual attacker enforcement flows: $resid (expect 0 = fully healed)"
say "   legit operator read post-storm: $lr"
say "   controller latency stats: $cms"
[ "${resid:-1}" = "0" ] && echo "$lr" | grep -q READ && say "   -> RECOVERED CLEAN" || say "   *** recovery incomplete ***"
inv "RECOVERY"

say ""; say "===============  STRESS VERDICT: $PASS invariant-checks PASSED, $FAIL FAILED  ==============="
curl -s $API/status > "$OUT/status.json"; curl -s $API/audit > "$OUT/audit.json"
TAR=$HOME/cars_stress_${TS}.tar.gz; tar -czf "$TAR" -C "$HOME/cars_forensics" "stress_$TS" 2>/dev/null
say "bundle: $TAR"
echo; echo "=====  FULL VERDICT  ====="; cat "$V"
