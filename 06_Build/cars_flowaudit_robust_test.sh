#!/bin/bash
# cars_flowaudit_robust_test.sh — EXTENDED robustness proof of the #28 flow-integrity checker.
# Complements cars_flowaudit_test.sh (inject/remove/rewrite) with: BLACK-HOLE, LOOP-rule, and the EVASION/blind-spot.
# Isolated throwaway bridge — NO live ports, NO PLCs, NO process risk. Self-cleaning.
set -u
BR=farobust; BASE=/tmp/fa_robust_base.json
CHK="$(dirname "$0")/cars_flow_audit.py"
O="sudo ovs-ofctl -O OpenFlow13"
cleanup(){ sudo ovs-vsctl --if-exists del-br $BR 2>/dev/null; rm -f "$BASE"; }
cleanup

pass=0; fail=0
run(){ python3 "$CHK" --bridges $BR --baseline-file "$BASE" --check >/tmp/far_out 2>&1; echo $?; }
expect(){ # $1=label $2=expected-rc(0 clean / 2 drift) $3=grep-substr(optional)
  rc=$(run); ok=1; [ "$rc" = "$2" ] || ok=0
  if [ -n "${3:-}" ]; then grep -q "$3" /tmp/far_out || ok=0; fi
  if [ "$ok" = 1 ]; then echo "  [PASS] $1"; pass=$((pass+1)); else
    echo "  [FAIL] $1 (rc=$rc want $2; grep '${3:-}')"; sed 's/^/       /' /tmp/far_out; fail=$((fail+1)); fi
}

echo "== build throwaway bridge + mock CARS policy =="
sudo ovs-vsctl add-br $BR
$O add-flow $BR "cookie=0x0,table=0,priority=200,ip,in_port=1,nw_src=10.9.9.9,actions=goto_table:1"                  # GUARD
$O add-flow $BR "cookie=0xa2,table=1,priority=80,tcp,nw_src=10.9.9.9,nw_dst=10.9.9.11,tp_dst=502,actions=goto_table:2"   # A2 allowlist conduit
$O add-flow $BR "cookie=0xa2,table=1,priority=55,ip,actions=drop"                                                    # A2 default-deny
$O add-flow $BR "cookie=0xca,table=1,priority=105,dl_src=00:00:00:00:00:aa,dl_dst=00:00:00:00:00:bb,actions=drop"    # LEGIT reactive (cookie 0xca)
sleep 1
echo "== capture trusted baseline =="; python3 "$CHK" --bridges $BR --baseline-file "$BASE" --baseline

echo; echo "== TESTS =="
expect "R1 pristine -> CLEAN" 0 "CLEAN"

# --- BLACK-HOLE: rewrite a legit allowlist conduit's action to drop (traffic that SHOULD forward now silently dropped) ---
$O --strict mod-flows $BR "cookie=0xa2/-1,table=1,priority=80,tcp,nw_src=10.9.9.9,nw_dst=10.9.9.11,tp_dst=502,actions=drop"
expect "R2 BLACK-HOLE (allowlist conduit action -> drop) -> DRIFT/CHANGED" 2 "action modified"
$O --strict mod-flows $BR "cookie=0xa2/-1,table=1,priority=80,tcp,nw_src=10.9.9.9,nw_dst=10.9.9.11,tp_dst=502,actions=goto_table:2"  # restore
expect "R2b restored -> CLEAN" 0 "CLEAN"

# --- LOOP: inject a rule that would cause a forwarding loop (self-resubmit). Checker flags the RULE (not 'loop' semantically). ---
$O add-flow $BR "cookie=0xbad,table=1,priority=201,ip,actions=resubmit(,1)"
expect "R3 LOOP-rule injected (self-resubmit) -> DRIFT/EXTRA" 2 "bogus rule injected"
$O del-flows $BR "cookie=0xbad/-1,table=1"
expect "R3b loop-rule removed -> CLEAN" 0 "CLEAN"

# --- EVASION (post-hardening): a bogus rule at cookie0x0/prio108 no longer looks reactive (reactive = cookie 0xca) -> CAUGHT ---
$O add-flow $BR "cookie=0x0,table=1,priority=108,ip,nw_dst=10.9.9.11,actions=drop"
expect "R4 EVASION now CAUGHT (bogus cookie0x0 in old reactive band) -> DRIFT/EXTRA" 2 "bogus rule injected"
$O --strict del-flows $BR "cookie=0x0/-1,table=1,priority=108,ip,nw_dst=10.9.9.11"
expect "R4b evasion removed -> CLEAN" 0 "CLEAN"
# --- R5: a REAL reactive isolate (cookie 0xca) is still correctly ignored (no false positive on legit CARS response) ---
$O add-flow $BR "cookie=0xca,table=1,priority=106,dl_src=00:00:00:00:00:cc,dl_dst=00:00:00:00:00:dd,actions=drop"
expect "R5 real reactive (cookie 0xca) added -> still CLEAN (correctly ignored)" 0 "CLEAN"
$O --strict del-flows $BR "cookie=0xca/-1,table=1,priority=106,dl_src=00:00:00:00:00:cc,dl_dst=00:00:00:00:00:dd"

echo; echo "== VERDICT: PASS=$pass FAIL=$fail =="
echo "   R2 black-hole=CHANGED, R3 loop-rule=EXTRA caught; R4 evasion MISSED = the documented reactive-cookie blind spot."
echo "   -> Hardening decision: stamp CARS reactive rules with a DISTINCT cookie so R4-class rules can't hide."
cleanup; echo "(throwaway bridge + baseline removed)"
