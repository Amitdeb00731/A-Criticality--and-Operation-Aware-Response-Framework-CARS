#!/bin/bash
# CARS A3/P1 — stand up the Modbus endpoint topology in dedicated netns on ovsgw.
# WHY netns: attacker/operator/PLC on one host + same /24 would route locally (loopback) and never
# traverse ovsgw -> never mirrored -> Snort blind. Namespaces force traffic through the fabric. (A3_DESIGN)
# Idempotent.
set -u
BR=ovsgw
setup_ns(){ # $1 ns  $2 port  $3 ip  $4 mac
  local ns=$1 port=$2 ip=$3 mac=$4
  ip netns list | grep -qw "$ns" || ip netns add "$ns"
  ovs-vsctl --may-exist add-port "$BR" "$port" -- set interface "$port" type=internal
  if ip link show "$port" >/dev/null 2>&1; then ip link set "$port" netns "$ns"; fi
  ip netns exec "$ns" ip link set "$port" address "$mac"
  ip netns exec "$ns" ip addr replace "$ip/24" dev "$port"
  ip netns exec "$ns" ip link set "$port" up
  ip netns exec "$ns" ip link set lo up
  echo "  $ns: $ip on $BR:$port"
}
echo "[setup] Modbus endpoint namespaces on $BR:"
setup_ns mbns  mbplc 192.168.2.20 02:00:00:00:02:20   # Modbus PLC (server)
setup_ns opns  opr   192.168.2.31 02:00:00:00:02:31   # legit operator
setup_ns atkns atk   192.168.2.66 02:00:00:00:02:66   # attacker
echo "[setup] done. Start server:  sudo ip netns exec mbns python3 /home/msclab/mb_server.py 192.168.2.20"
