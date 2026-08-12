# A2 — Proactive allowlist / default-deny. Design + record.
Opened 2026-07-18. Complements A3 (reactive DPI): A3 detects-then-blocks (first packet lands, fragmentation can
evade); A2 **pre-installs the policy so unauthorized traffic never reaches a PLC** — prevention, not reaction.

## Decisions (Rule-0 justified)
1. **Scope: Modbus cell (`.2.20`) first.** Default-deny is the one mechanism that can *cause* the outage CARS prevents
   (an incomplete allowlist severs a legit flow). Prove it where that's harmless (simulated PLC), then extend to the
   real Cell-1 loop as a deliberate, tested step.
2. **Allowlist = declarative table.** Explicit, auditable `(src, dst, ip_proto, dport)` list > implicit role-derivation
   for a safety-critical deny; and it directly seeds the A4 rulebook.
3. **Deny action = proactive DROP.** Cleanest safe baseline — an unauthorized source never lands a packet. DEFLECT
   remains a per-conduit upgrade for later.

## Architecture (why it's L3/L4)
OpenFlow matches L3/L4, so A2's default-deny is at the **conduit/port** level (pre-deny unauthorized *sources*). It
cannot pre-deny by Modbus function code (L7) — that's precisely why A3's operation DPI is reactive. So:
- **A2 (proactive):** unknown source -> PLC = dropped before the first packet. Fixes A3's reactive-first-packet limit
  for unauthorized sources, and is immune to L7 fragmentation evasion (no detection needed).
- **A3 (reactive):** a bad *operation* (write) from an *allowed* source is still caught by the DPI path.
- Together = defense-in-depth.

## Pipeline (Table 1 priority order — reactive still wins)
`P110 ISOLATE > P105 DEFLECT > P100 BLOCK/THROTTLE` (reactive A1/A3)  **>**  `P60 allowlist ALLOW > P55 default-deny DROP`
(proactive A2)  **>**  `P0 pass`.
- Allowlist ALLOW (P60): `match(ip, src, dst, tcp_dst) -> goto switch`. Return traffic (dst != PLC) + non-PLC traffic pass at P0.
- Default-deny DROP (P55): `match(ip, dst=PLC) -> drop`.
- An allowed operator's WRITE still gets THROTTLEd because the reactive P100 flow overrides the P60 allow.
Installed proactively in `features_handler` at switch connect (like the guard), so the posture exists before any attack.

## Config (declarative)
```
ALLOWLIST = [ ("192.168.2.31","192.168.2.20",6,502) ]   # operator -> Modbus PLC TCP 502
DEFAULT_DENY_DSTS = ["192.168.2.20"]                     # PLCs under proactive default-deny (Modbus cell first)
```

## Phases
- **P1** (build) declarative allowlist + proactive default-deny for the Modbus cell; verify operator permitted,
  attacker pre-dropped from the first packet, A3 throttle still overrides for the operator's writes.
- **P2** ✅ 2026-07-18 (CC-41). Observed real `.2.10` traffic (only `.2.9->tcp/102`), allow-first + deny-with-60s-
  rollback live test (loop `n_packets 74->192`, deny 0), then permanent (`ALLOWLIST += (.2.9,.2.10,6,102)`,
  `DEFAULT_DENY_DSTS += .2.10`). Re-validated bridge-stopped: live loop intact (`177->243`), attacker pre-dropped
  (ovsgw deny `0->2`, no BRAIN line). Real PLC now proactively protected, process undisturbed.
- **P3** ✅ 2026-07-18. Forensic sweep (`cars_a2_forensics.sh`, bundle `cars_a2_forensics_*.tar.gz`): allow counters
  climb + traffic delivered for permitted conduits; deny counters climb + `connect FAILED` + **audit unchanged**
  (no CARS decision) for attackers = silent proactive prevention; real loop untouched. Resilience bonus: with the
  bridge (detection) STOPPED, A2 still dropped both attackers -> PLC protected even when the IDS is down.

## Honest note
A2 prevents unauthorized *sources*; it does not (and cannot at L3/L4) prevent a bad *operation* from an allow-listed
source — that stays A3's job. The safety risk is entirely in allowlist completeness, hence the phased scope.

## CC-43 finding: A2 x NAT x shared-IP (per-switch scoping required)
Deep testbed audit (2026-07-18) found that default-denying `.2.10` globally broke Cell-2: `.2.10` is a SHARED IP
(PLC1@ovs1 AND PLC2@ovs2), and Cell-2's PLC2 is reached via Dell#3 NAT which MASQUERADEs the source to `cell2gw .2.1`
(not allowlisted) -> the NAT path hit the deny. **Source-based proactive default-deny cannot see through NAT.** Fix:
`DEFAULT_DENY` is now `(dpid|None, ip)` per-switch — `.2.10` denies on ovs1 (Cell-1) only. Lesson: proactive policy must
be scoped per network segment, and behind NAT the gateway path must be allowlisted (or the controller needs the
de-NAT'd source). A2-P2's real-PLC protection stands on Cell-1; Cell-2 restored.
