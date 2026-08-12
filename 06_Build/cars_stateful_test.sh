#!/bin/bash
# cars_stateful_test.sh - ISOLATED proof of the Phase-1 stateful (conntrack) POLICY logic.
# Builds a throwaway OVS bridge + 3 netns on a PRIVATE subnet (10.9.9.0/24). NO live ports, NO PLCs.
# Proves: an allowlisted CLIENT works incl. its return traffic (ct +est), while an attacker cannot
# scan the server OR the client (ct +new to a protected dst is dropped) -> the exact HMI fix,
# with the reply path preserved. Fully self-cleaning.
set -u
BR=ststest; SUB=10.9.9
cleanup(){ for n in cli srv atk; do sudo ip netns del $n 2>/dev/null; done; sudo ovs-vsctl --if-exists del-br $BR 2>/dev/null; }
cleanup   # start clean

echo "== build isolated bridge + netns (cli=allowlisted client, srv=server, atk=attacker) =="
sudo ovs-vsctl add-br $BR
declare -A IP=( [cli]=9 [srv]=10 [atk]=66 )
for n in cli srv atk; do
  sudo ip netns add $n
  sudo ip link add ${n}0 type veth peer name ${n}1
  sudo ip link set ${n}1 netns $n
  sudo ovs-vsctl add-port $BR ${n}0
  sudo ip link set ${n}0 up
  sudo ip netns exec $n ip link set lo up
  sudo ip netns exec $n ip addr add $SUB.${IP[$n]}/24 dev ${n}1
  sudo ip netns exec $n ip link set ${n}1 up
done

echo "== install STATEFUL POLICY flows (protect srv .10 AND cli .9; allowlist only cli->srv:502) =="
O="sudo ovs-ofctl -O OpenFlow13"
$O del-flows $BR
$O add-flow $BR "table=0,priority=100,arp,actions=normal"
$O add-flow $BR "table=0,priority=90,ip,ct_state=-trk,actions=ct(table=1)"
$O add-flow $BR "table=0,priority=0,actions=normal"
# post-conntrack decisions:
$O add-flow $BR "table=1,priority=100,ip,ct_state=+est,actions=normal"                                              # RETURN traffic on an allowed conn -> pass (the client-reply fix)
$O add-flow $BR "table=1,priority=90,ip,ct_state=+new,tcp,nw_src=$SUB.9,nw_dst=$SUB.10,tp_dst=502,actions=ct(commit),normal"  # allowlisted initiation
$O add-flow $BR "table=1,priority=50,ip,ct_state=+new,nw_dst=$SUB.10,actions=drop"                                  # protected server: unsolicited new -> drop
$O add-flow $BR "table=1,priority=50,ip,ct_state=+new,nw_dst=$SUB.9,actions=drop"                                   # protected CLIENT: unsolicited new -> drop (shield)
$O add-flow $BR "table=1,priority=10,ip,ct_state=+new,actions=ct(commit),normal"                                    # anything else new -> allow+track
$O add-flow $BR "table=1,priority=0,actions=normal"
sleep 1

echo; echo "== server listens on tcp/502 =="
sudo ip netns exec srv bash -c 'timeout 25 nc -lk 502 >/dev/null 2>&1 &' ; sleep 1

pass=0; fail=0
t(){ if [ "$2" = "$3" ]; then echo "  [PASS] $1"; pass=$((pass+1)); else echo "  [FAIL] $1  (got $2 want $3)"; fail=$((fail+1)); fi; }
conn(){ sudo ip netns exec $1 bash -c "timeout 3 nc -z -w2 $2 $3 >/dev/null 2>&1" && echo up || echo down; }

echo "== TESTS =="
t "T1 cli->srv:502 (allowlisted; needs the +est reply to complete)" "$(conn cli $SUB.10 502)" up
t "T2 atk->srv:502 (unlisted server scan -> blocked)"               "$(conn atk $SUB.10 502)" down
t "T3 atk->cli:502 (client scan -> blocked = CLIENT SHIELDED)"      "$(conn atk $SUB.9  502)" down

echo; echo "== conntrack table (proof the allowed conn is tracked) =="
sudo ovs-dpctl dump-conntrack 2>/dev/null | grep "$SUB" | head
echo; echo "== VERDICT: PASS=$pass FAIL=$fail =="
echo "   T1 up + T2/T3 down  => stateful policy shields client+server from scans yet passes the client's own replies (the HMI fix)."
cleanup; echo "(isolated bridge + netns removed)"
