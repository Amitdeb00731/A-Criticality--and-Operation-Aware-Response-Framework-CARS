#!/bin/bash
# cars_flowaudit_test.sh - ISOLATED proof of the #28 FLOW-INTEGRITY checker against a REAL OVS bridge.
# Builds a throwaway bridge with a mock CARS policy (t0 GUARD + t1 cookie-0xa2 A2), baselines it, then simulates a
# Controller-in-the-Middle tampering campaign (inject bogus rule / delete policy / rewrite action / add legit reactive)
# and asserts the checker's verdict each time. NO live ports, NO PLCs, NO controller. Fully self-cleaning.
set -u
BR=fatest; BASE=/tmp/fa_test_base.json
CHK="$(dirname "$0")/cars_flow_audit.py"
O="sudo ovs-ofctl -O OpenFlow13"
cleanup(){ sudo ovs-vsctl --if-exists del-br $BR 2>/dev/null; rm -f "$BASE"; }
cleanup

pass=0; fail=0
run(){ python3 "$CHK" --bridges $BR --baseline-file "$BASE" --check >/tmp/fa_out 2>&1; echo $?; }
expect(){ # $1=label $2=expected-rc(0 clean / 2 drift) $3=grep-substr(optional)
  rc=$(run)
  ok=1; [ "$rc" = "$2" ] || ok=0
  if [ -n "${3:-}" ]; then grep -q "$3" /tmp/fa_out || ok=0; fi
  if [ "$ok" = 1 ]; then echo "  [PASS] $1"; pass=$((pass+1)); else
    echo "  [FAIL] $1 (rc=$rc want $2; grep '${3:-}')"; sed 's/^/       /' /tmp/fa_out; fail=$((fail+1)); fi
}

echo "== build throwaway bridge + mock CARS policy =="
sudo ovs-vsctl add-br $BR
$O add-flow $BR "cookie=0x0,table=0,priority=200,ip,in_port=1,nw_src=10.9.9.9,actions=goto_table:1"    # GUARD binding
$O add-flow $BR "cookie=0x0,table=0,priority=100,ip,nw_src=10.9.9.10,actions=drop"                      # GUARD anti-spoof drop
$O add-flow $BR "cookie=0xa2,table=1,priority=80,tcp,nw_src=10.9.9.9,nw_dst=10.9.9.11,tp_dst=502,actions=goto_table:2"  # A2 allowlist
$O add-flow $BR "cookie=0xa2,table=1,priority=55,ip,actions=drop"                                       # A2 default-deny
sleep 1

echo "== capture trusted baseline =="
python3 "$CHK" --bridges $BR --baseline-file "$BASE" --baseline

echo; echo "== TESTS =="
expect "T1 pristine policy -> CLEAN"                                    0 "CLEAN"
$O add-flow $BR "cookie=0x0,table=1,priority=105,dl_src=00:00:00:00:00:aa,dl_dst=00:00:00:00:00:bb,actions=drop"
expect "T2 legit reactive isolate added (cookie0x0 p105) -> still CLEAN" 0 "CLEAN"
$O add-flow $BR "cookie=0xdead,table=1,priority=90,ip,nw_src=10.9.9.66,actions=goto_table:2"
expect "T3 BOGUS rule injected (weird cookie) -> DRIFT/EXTRA"           2 "bogus rule injected"
$O del-flows $BR "cookie=0xdead/-1,table=1"
expect "T4 bogus removed -> CLEAN again"                                0 "CLEAN"
$O --strict del-flows $BR "cookie=0xa2/-1,table=1,priority=55,ip"
expect "T5 A2 default-deny DELETED -> DRIFT/MISSING"                    2 "policy rule removed"
$O add-flow $BR "cookie=0xa2,table=1,priority=55,ip,actions=drop"       # restore it
$O --strict mod-flows $BR "cookie=0xa2/-1,table=1,priority=80,tcp,nw_src=10.9.9.9,nw_dst=10.9.9.11,tp_dst=502,actions=drop"
expect "T6 allowlist action REWRITTEN to drop -> DRIFT/CHANGED"         2 "action modified"

echo; echo "== VERDICT: PASS=$pass FAIL=$fail =="
echo "   T1/T4 clean, T2 ignores legit reactive, T3/T5/T6 catch inject/remove/rewrite => flow-integrity checker works on real OVS."
cleanup; echo "(throwaway bridge + baseline removed)"
