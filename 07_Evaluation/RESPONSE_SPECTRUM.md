# CARS Graduated Response Spectrum (A1) — evaluation summary
Testbed-verified on hardware, 2026-07-16 (DECISION_LOG CC-31..CC-33). CARS v0.8.

## The response repertoire
CARS replaces binary block/allow with a **criticality-graded, persistence-escalating, self-healing** response
ladder. The *decision* (conduit criticality tier, unchanged trust brain) is decoupled from the *response*
(the OpenFlow enforcement). Response = f(tier, offense count), safety-capped.

| Tier (decision) | Conduit example | 1st response | Escalation (persistence) | Data-plane mechanism | Effect (measured) | CARS decide+enforce |
|---|---|---|---|---|---|---|
| **CRITICAL** | hmi <-> plc (control loop) | **REFUSE** | never (safety invariant) | none (mirror/alert only) | loop never severed | ~0.005-0.015 ms |
| **OPERATIONAL** | supervisory -> plc | **ALLOW** | — | pass (goto switch table) | permit + monitor | ~0.01-0.02 ms |
| **SENSITIVE** | ews -> plc (elevated, known) | **THROTTLE** | -> BLOCK on sustained abuse | OpenFlow **meter** (20 pktps, drop band) + goto switch table | rate-capped, not cut — **delivery-verified**: 80 pkts @50pps -> **42 forwarded + 38 meter-dropped** (=80); meter `type=drop rate=20 burst=10` | ~0.3-0.6 ms |
| **FORBIDDEN** | unknown/gateway -> plc | **BLOCK** | -> **ISOLATE** source on persistence (offense >= 3) | drop flow (P100) -> src-wide drop (P110) | conduit dropped, then whole source quarantined | ~0.3-0.9 ms |
| **FORBIDDEN** (deception mode) | unknown -> plc | **DEFLECT** | self-heals @30 s | forward rewrite `set eth_dst/ipv4_dst`->decoy + reverse rewrite `.99->.10`, both P105 goto switch; decoy in isolated netns | attacker reaches decoy (**ttl=64**, interactive echo) not the real PLC (**ttl=29**); PLC never touched; attacker deceived | ~1.0-1.7 ms |

## Cross-cutting properties (all verified live)
- **Criticality-graded:** a PLC faces single-command attacks, so THROTTLE (which still passes ~20 pps) cannot
  protect it -> unknown->PLC is BLOCKED outright; THROTTLE is reserved for elevated-but-known conduits
  (permit-with-limit) and volumetric/recon. The response is chosen by the conduit's criticality, not uniform.
- **Self-healing:** every enforcing response carries a `hard_timeout` (30 s) + `SEND_FLOW_REM`; on expiry the
  controller clears state AND resets the offense count. A ceased attack (or a false positive) undoes itself with
  no operator action -- directly addressing the ICS risk of a mistaken block halting a live process.
- **Escalating:** sustained attack climbs the ladder (verified: insider ping -> BLOCK, BLOCK, ISOLATE across the
  autonomous Snort->CARS loop; on stop -> AUTO-HEALED + forgiven).
- **Sub-millisecond enforcement:** CARS decide+enforce stays <1 ms across all response types; end-to-end
  detect->enforce ~26 ms (Snort afpacket, sensor-bound).
- **OpenFlow coverage:** 3-table guard/policy/switch pipeline (T0 source-guard -> T1 policy -> T2 L2 switch), meters (QoS
  THROTTLE), **set-field rewrite + goto for traffic steering (DEFLECT)**, flow add/mod/delete, hard/idle timeouts,
  priority layering (P110 isolate > P105 deflect > P100 conduit > P0 pass), FlowRemoved events. (vs. the earlier
  detect-and-drop only — CARS now *steers*, not just drops.)

## Substrate note (honest)
OVS **kernel-datapath meters** enforce the THROTTLE rate correctly here, and — after the T2 switch-table fix (CC-35) —
**forward the passed packets** (meter + goto_table). This is validated by *delivery*, not just by meter counters:
80 pkts @50pps -> band dropped 38, **42 actually delivered to and answered by the PLC** (38+42=80). Earlier meter-only
figures (CC-32) proved the meter *released* packets but not that they were *forwarded*; a half-migrated pipeline was in
fact black-holing them at the handler-less table 2 until the fix. A userspace (`netdev`) datapath would be the
alternative if a deployment's kernel lacked meter support.

## Datapath-counter verification (2026-07-16) — proof at packet level, not controller claims
Single consolidated sweep, autonomous loop stopped (isolating the enforcement mechanism), reading OVS's own
per-flow `n_packets`/meter counters (kernel ground truth) + observed traffic outcome. Each response forced, cleaned
between runs, self-heal 30 s.

| Response | OVS datapath counter | Traffic outcome | Proven |
|---|---|---|---|
| ALLOW | no policy flow installed (pure fall-through to switch) | 5/5 delivered | ✓ |
| BLOCK | drop flow P100 `nw_src=.66,nw_dst=.10` **n_packets=10** | 0/10 received | ✓ |
| ISOLATE | **one** drop flow P110 `nw_src=.66` only **n_packets=10** | to `.10` 0/5 **and** to `.99` 0/5 (source-wide) | ✓ |
| THROTTLE | meter band drop **+38** | 42 delivered (38+42=80) | ✓ |
| DEFLECT | forward+reverse rewrite flows P105 | 4/4 at **ttl=64** (decoy), not ttl=29 (PLC) | ✓ |

Decide+enforce measured **0.6–0.9 ms** per response; all responses AUTO-HEALED on timeout. The one response that had
*not* been happening at packet level (THROTTLE, black-holed by the pre-fix pipeline) was caught and corrected the same
day (CC-35) — this table is the post-fix, datapath-verified record.

**Caveat (honest, decision-layer):** `select_response` autonomously chooses ALLOW/THROTTLE/BLOCK/ISOLATE/REFUSE.
**DEFLECT is enforcement-proven but force-invoked** — not yet wired into the automatic tier→response selection.

## DEFLECT substrate note (honest)
The decoy runs in its **own Linux network namespace** (`hpotns`) rather than the host root stack. This is required, not
cosmetic: with the attacker vantage and the decoy both on one host in the same /24, the kernel treats the attacker's
source IP as *local* and refuses to answer (martian), so the decoy can receive but never reply. Namespace isolation
(or a container/VM) makes the attacker look genuinely remote, enabling the interactive deception. A container image
(e.g. Conpot for fake S7comm/Modbus) is a drop-in richer decoy on the same redirect path.
