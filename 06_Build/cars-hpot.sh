#!/bin/bash
# CARS A1/P3 DEFLECT decoy — isolated honeypot in its own network namespace on ovsgw.
# WHY a namespace: attacker vantage (ins2 .3.66) and the decoy (.3.99) both live on Dell#1;
# in one root stack + same /24 the kernel sees .3.66 as LOCAL and refuses to answer (martian),
# so the decoy could receive but never reply. hpotns isolates the stack -> attacker looks remote
# -> the decoy answers -> DEFLECT's interactive deception works. (DECISION_LOG CC-35.)
# Idempotent: safe on every boot and on manual re-run.
set -e
BR=ovsgw
PORT=hpot
NS=hpotns
MAC=02:00:00:00:03:99
IP=192.168.3.99/24

# 1) ensure the OVS internal decoy port exists on the bridge (pin ofport for stability)
ovs-vsctl --may-exist add-port "$BR" "$PORT" -- set interface "$PORT" type=internal ofport_request=6

# 2) ensure the namespace exists
ip netns list | grep -qw "$NS" || ip netns add "$NS"

# 3) move the port into the namespace only if it is still in the root netns
if ip link show "$PORT" >/dev/null 2>&1; then
    ip link set "$PORT" netns "$NS"
fi

# 4) configure the decoy stack inside the namespace (all idempotent)
ip netns exec "$NS" ip link set "$PORT" address "$MAC"
ip netns exec "$NS" ip addr replace "$IP" dev "$PORT"
ip netns exec "$NS" ip link set "$PORT" up
ip netns exec "$NS" ip link set lo up

# 5) return path for interactive deception (CC-45). The attacker's probes arrive source-addressed from the OT cell
#    (.2.0/24) which the decoy has no route to; strict/loose rp_filter would drop them and the decoy stays silent.
#    Disable rp_filter and add a link route back toward the cell so the decoy can actually answer. The controller's
#    reverse DEFLECT flow then rewrites the reply (src->real target, eth_dst->attacker) and outputs it to the attacker.
ip netns exec "$NS" sysctl -w net.ipv4.conf.all.rp_filter=0 >/dev/null
ip netns exec "$NS" sysctl -w net.ipv4.conf."$PORT".rp_filter=0 >/dev/null
ip netns exec "$NS" ip route replace 192.168.2.0/24 dev "$PORT"
echo "cars-hpot: decoy $IP ($MAC) live in netns $NS on $BR (return-path armed: rp_filter=0 + route .2.0/24)"
