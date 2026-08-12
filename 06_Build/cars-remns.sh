#!/bin/bash
# cars-remns.sh — (re)create the CARS remediation-agent netns + .2.45 seam on ovsgw. Idempotent; safe at boot & re-run.
set +e
ip netns add remns 2>/dev/null
ip link show rem0ovs >/dev/null 2>&1 || ip link add rem0 type veth peer name rem0ovs
# move the peer into the netns only if it's still in the root namespace
ip link show rem0 >/dev/null 2>&1 && ip link set rem0 netns remns
# CC-94: pin the ofport so the GUARD anti-spoof binding (in_port=14) survives every boot. Without this, OVS assigns
# whatever ofport is next (Kali/vmnet2 stole 14 on 2026-07-30 -> rem0ovs drifted to 13 -> remns ARPs dropped as spoof).
ovs-vsctl --may-exist add-port ovsgw rem0ovs -- set Interface rem0ovs ofport_request=14
ip netns exec remns ip addr add 192.168.2.45/24 dev rem0 2>/dev/null
ip netns exec remns ip link set rem0 up
ip netns exec remns ip link set lo up
ip link set rem0ovs up promisc on
exit 0
