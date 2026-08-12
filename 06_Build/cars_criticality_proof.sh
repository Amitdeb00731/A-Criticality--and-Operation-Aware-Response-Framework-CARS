#!/bin/bash
# cars_criticality_proof.sh - PROVE the Asset Criticality Framework (decision + response) live on CARS.
# Uses /cars/respond (the brain's decision interface) to fire controlled scenarios and tabulate
#   {tier, crit-tier, elevated, action(+timeout)} for each. Decision-side tests run DISARMED (pure
#   decision, no enforcement on real IPs); response-proportionality runs ARMED (real tier-scaled quarantine
#   from the harmless attacker IP .2.66, healed after each).
# Run on Dell#1 (has OVS for heal + the token at ~/cars/api_token + control-plane reach).
set -u
API=http://10.10.10.1:8080/cars
TOKEN="$(cat ~/cars/api_token 2>/dev/null || echo "${CARS_API_TOKEN:-}")"

arm(){   curl -s -XPOST $API/defense     -H "X-CARS-Token: $TOKEN" -H 'Content-Type: application/json' -d "{\"on\":$1}" >/dev/null; }
maint(){ curl -s -XPOST $API/maintenance -H "X-CARS-Token: $TOKEN" -H 'Content-Type: application/json' -d "{\"minutes\":$1}" >/dev/null; }
heal(){  for sw in ovsgw ovs1; do sudo ovs-ofctl -O OpenFlow13 --strict del-flows "$sw" "table=1,priority=110" 2>/dev/null; done; }
fire(){  # label src dst proto op
  curl -s -XPOST $API/respond -H 'Content-Type: application/json' \
    -d "{\"src\":\"$2\",\"dst\":\"$3\",\"proto\":\"$4\",\"op\":\"$5\",\"dpid\":3}" \
  | python3 -c "import json,sys
d=json.load(sys.stdin)
print('  %-32s tier=%-11s crit=%-9s elevated=%-5s | %s' % ('$1', d.get('tier'), d.get('crit'), str(d.get('elevated')), d.get('action')))"
}

echo "################  CARS ASSET-CRITICALITY FRAMEWORK - LIVE PROOF  ################"
echo "grounding: INL CCE (consequence) + CISA taxonomy + MITRE CJA (centrality). ACL: PLC1=CRIT, PLC2/HMI1=HIGH, HMI2/Hist=MED, Modbus=LOW."

echo; echo "===== PART 1 - DECISION SIDE: bounded elevation (disarmed = pure decision, nothing enforced) ====="
arm false
echo " [same trusted actor + op; only the TARGET's criticality changes the DECISION]"
fire "EWS->PLC1 READ  (dst CRITICAL)" 192.168.2.55 192.168.2.10 S7 READ
fire "EWS->PLC2 READ  (dst HIGH)"     192.168.2.55 192.168.3.10 S7 READ
echo " [now open an authorised maintenance window -> elevation must SUSPEND]"
maint 5
fire "EWS->PLC1 READ  (in MAINT win)" 192.168.2.55 192.168.2.10 S7 READ
maint 0
echo "  expect: PLC1 -> FORBIDDEN/elevated=True [CRIT:CRITICAL];  PLC2 -> SENSITIVE/elevated=False [CRIT:HIGH];  in-window -> permitted (elevation suspended)"

echo; echo "===== PART 2 - RESPONSE SIDE: proportionality (armed = real tier-scaled quarantine) ====="
arm true
echo " [identical dangerous op (CONTROL) from the same attacker; only the TARGET tier changes the RESPONSE/timeout]"
fire "any->PLC1 CONTROL (CRITICAL)"  192.168.2.66 192.168.2.10 S7 CONTROL; heal
fire "any->PLC2 CONTROL (HIGH)"      192.168.2.66 192.168.3.10 S7 CONTROL; heal
fire "any->Modbus CONTROL (LOW)"     192.168.2.66 192.168.2.20 MODBUS CONTROL; heal
echo "  expect: ISOLATE/BLOCK with hard_timeout 75s (CRIT) / 60s (HIGH) / 30s (LOW) = 30 + cw*15"

echo; echo "===== PART 3 - INVARIANTS (criticality never breaks the safety rules) ====="
echo " I1 - the control loop is NEVER enforced (safety cap), even on the CRITICAL asset:"
fire "I1  HMI->PLC1 CONTROL (loop)"   192.168.2.9  192.168.2.10 S7 CONTROL; heal
echo " I2 - trusted MONITORING is always allowed, even on the CRITICAL asset:"
fire "I2  SCADA->PLC1 READ"           192.168.2.31 192.168.2.10 S7 READ
heal
echo "  expect: I1 -> REFUSE (loop untouched);  I2 -> ALLOW (operational, monitor-only)"

echo; echo "===== DISARMED CONTRAST (same as PART 2, monitor-only) ====="
arm false
fire "any->PLC1 CONTROL (disarmed)"  192.168.2.66 192.168.2.10 S7 CONTROL
fire "any->PLC2 CONTROL (disarmed)"  192.168.2.66 192.168.3.10 S7 CONTROL
arm true; heal
echo "  expect: 'DEFENSE DISARMED - would ISOLATE (monitor only)' - decided, criticality-tagged, NOT enforced"

echo; echo "################  re-armed, flows healed. PROOF COMPLETE.  ################"
