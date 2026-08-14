#!/usr/bin/env bash
# CARS green-light check - run on Dell 1. READ-ONLY. Confirms the testbed is ready for overnight validation.
set -u
API="http://10.10.10.1:8080"
echo "===== CARS GREEN-LIGHT CHECK  $(date) ====="

echo "-- 1. CARS services (Dell 1) --"
for s in cars-snort cars-bridge cars-flowaudit cars-remediation cars-hpot cars-modbus; do
  printf "   %-18s %s\n" "$s" "$(systemctl is-active "$s" 2>/dev/null)"
done

echo "-- 2. Controller <-> switches (os-ken on Dell 2) --"
curl -s --max-time 5 "$API/cars/status" 2>/dev/null | python3 -c 'import sys,json;d=json.load(sys.stdin);print("   armed:",d.get("armed"),"| switches:",d.get("switches"),"| guards:",d.get("guards", d.get("guard")))' 2>/dev/null \
  || echo "   [WARN] controller API not answering on $API"

echo "-- 3. OVS controller connection --"
echo "   is_connected: $(sudo ovs-vsctl --no-headings --columns=is_connected list controller 2>/dev/null | tr '\n' ' ')"

echo "-- 4. Reactive-rule residue (0xca must be 0 on every bridge) --"
for br in ovs1 ovsgw ovs2; do
  n=$(sudo ovs-ofctl -O OpenFlow13 dump-flows "$br" 2>/dev/null | grep -ci 0xca)
  printf "   %-7s 0xca=%s\n" "$br" "${n:-NA}"
done

echo "-- 5. Proactive baseline present (0xa2 allowlist > 0) --"
for br in ovs1 ovsgw; do
  n=$(sudo ovs-ofctl -O OpenFlow13 dump-flows "$br" 2>/dev/null | grep -ci 0xa2)
  printf "   %-7s 0xa2=%s\n" "$br" "${n:-NA}"
done

echo "-- 6. Flow-integrity (expect CLEAN / ok:1) --"
sudo python3 /home/msclab/cars/cars_flow_audit.py --check --bridges ovs1,ovsgw 2>/dev/null | tail -2 \
  || { echo -n "   last audit feed: "; tail -1 /tmp/cars_flowaudit.jsonl 2>/dev/null; }

echo "-- 7. Process / remediation (expect online:1, level in 28-72 band) --"
echo -n "   "; cat /tmp/cars_remediation_status.json 2>/dev/null; echo

echo "-- 8. B1 dependency: mirror interface + Snort --"
ip -br link show snort0 2>/dev/null | sed 's/^/   /' || echo "   [WARN] snort0 mirror not found (set correct mirror for B1)"
pgrep -a snort 2>/dev/null | head -1 | sed 's/^/   snort: /' || echo "   [WARN] snort process not found"

echo "-- 9. Attacker reachability (Kali, optional) --"
ping -c1 -W1 192.168.2.77 >/dev/null 2>&1 && echo "   .2.77 (insider) reachable" || echo "   .2.77 not pinging (may be normal if firewalled)"

echo
echo "GREEN if: services active, is_connected=true, 0xca=0 on all bridges, 0xa2>0, flow-audit CLEAN,"
echo "remediation online:1 with level in 28-72, snort0 present and snort running."
