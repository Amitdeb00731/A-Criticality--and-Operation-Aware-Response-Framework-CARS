#!/bin/bash
# CARS Cell-2 NAT gateway (Dell#3) — presents real .2.10 PLC as .3.10 on the fabric.
# Idempotent; invoked by cars-cell2.service at boot. Survives reboot.
LOG(){ logger -t cars-cell2 "$*"; }

# Wait for the transit NIC (eth0, the monitor dock) and ovs2 to exist (~30s max).
for i in $(seq 1 30); do
  ip link show eth0 >/dev/null 2>&1 && ovs-vsctl br-exists ovs2 && break
  sleep 1
done

# Pin Cell-2 access-port ofports so a USB replug can't break the source-guard bindings.
ovs-vsctl set interface enx9c69d3413f16 ofport_request=1 2>/dev/null || true   # PLC2
ovs-vsctl set interface enx9c69d3283cf9 ofport_request=2 2>/dev/null || true   # HMI2

# cell2gw = Cell-2's gateway on ovs2 (the boxes' configured .2.1), local to Dell#3.
ovs-vsctl --may-exist add-port ovs2 cell2gw -- set interface cell2gw type=internal
nmcli dev set cell2gw managed no 2>/dev/null || true
ip addr replace 192.168.2.1/24 dev cell2gw
ip link set cell2gw up

# eth0 = fabric-facing transit (.3.1) that also owns .3.10 so it answers ARP for it.
nmcli dev set eth0 managed no 2>/dev/null || true
ip addr flush dev eth0
ip addr add 192.168.3.1/24  dev eth0
ip addr add 192.168.3.10/32 dev eth0
ip link set eth0 up

# Forwarding + 1:1 NAT (DNAT inbound, MASQUERADE toward the PLC). Idempotent.
sysctl -w net.ipv4.ip_forward=1 >/dev/null
iptables -t nat -C PREROUTING  -i eth0 -d 192.168.3.10 -j DNAT --to-destination 192.168.2.10 2>/dev/null \
  || iptables -t nat -A PREROUTING  -i eth0 -d 192.168.3.10 -j DNAT --to-destination 192.168.2.10
iptables -t nat -C POSTROUTING -o cell2gw -j MASQUERADE 2>/dev/null \
  || iptables -t nat -A POSTROUTING -o cell2gw -j MASQUERADE
iptables -C FORWARD -i eth0 -o cell2gw -j ACCEPT 2>/dev/null \
  || iptables -A FORWARD -i eth0 -o cell2gw -j ACCEPT
iptables -C FORWARD -i cell2gw -o eth0 -j ACCEPT 2>/dev/null \
  || iptables -A FORWARD -i cell2gw -o eth0 -j ACCEPT

LOG "Cell-2 NAT gateway up: eth0=.3.1/.3.10  cell2gw=.2.1  DNAT .3.10->.2.10"
