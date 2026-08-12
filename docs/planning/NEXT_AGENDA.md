# NEXT_AGENDA — Growing the CARS brain (post two-cell, reboot-proven build)
Date opened: 2026-07-15. Context: AG1-AG4 + evaluation complete; testbed reboot-persistent.

## Self-audit (the 8 questions) — honest gap analysis
| Question | Status |
|---|---|
| Fully used SDN/OpenFlow? | **Partial** — flow add/delete, 2-table pipeline, packet-in, stats, LLDP. UNUSED: meters (rate-limit), group tables (failover/redirect), output-to-port (reroute), set-field (rewrite), flow timeouts, OFPFC_MODIFY. We detect+drop, we don't *steer*. |
| Reactive AND proactive? | **Reactive only.** No allowlist / positive security / baseline / context policy. |
| Actions beyond block? | **No.** Only drop (block) + no-op (safety refuse). No reroute, throttle, honeypot, quarantine, DPI-redirect. |
| ICS protocols in decisions? | **No.** IP/role-based only. No Modbus/S7comm/DNP3 function-code awareness. |
| Strong rulebook (src/dst/action/timeout)? | **Partial.** Role-pair classify() + registry. No declarative table, no timeouts, no protocol/condition fields. |
| Real flow-mod (add/mod/delete)? | **Add+delete yes; modify+timeouts no.** Blocks permanent until manual restore. |
| Really dynamic for ICS? | **Semi.** Reacts dynamically, but the *response* is static + context-blind. |
| DPI (ICS + network)? | **No CARS DPI.** Snort = shallow signature match (ICMP/TCP to PLC IPs), not ICS payload/function-code inspection. |

## Core insight
CARS is currently criticality-aware **blocking** with a safety invariant. The name promises a **Response System**, but "response" is a binary drop. The novelty upside is to turn that single hammer into a **graduated, self-healing, criticality-graded response spectrum** using the OpenFlow capabilities we have not touched.

## CHOSEN: A1 — Graduated Response Repertoire
### Response spectrum (replaces binary block)
`ALLOW -> MONITOR -> THROTTLE -> DEFLECT -> ISOLATE -> BLOCK -> REFUSE`
- **ALLOW** — permit (baseline; today's OPERATIONAL).
- **MONITOR** — permit but heightened logging / targeted mirror.
- **THROTTLE** — rate-limit the conduit via an OpenFlow **meter** (graceful degradation; don't cut a possibly-legit ICS flow).
- **DEFLECT** — redirect the conduit to a honeypot/decoy (`output` + `set-field` dst rewrite) for deception/analysis.
- **ISOLATE** — quarantine the source (drop all its conduits, not just one).
- **BLOCK** — drop the conduit (today's FORBIDDEN).
- **REFUSE** — safety invariant: never enforce on a CRITICAL control loop (unchanged).

### Selection model: response = f(conduit criticality, threat persistence), safety-capped
- **Safety cap (invariant):** CRITICAL loop -> REFUSE, always, regardless of threat.
- **Criticality-graded escalation:** the ladder is steeper for higher-criticality targets. Persistence escalates the response in TIME:
  - 1st detection -> THROTTLE (or MONITOR for low criticality) — graceful, tolerant of false positives.
  - repeat within window -> BLOCK (with a hard timeout).
  - persistent -> ISOLATE the source.
- **DEFLECT** available for FORBIDDEN conduits (send the attacker to a decoy instead of the PLC).
- **Self-healing:** THROTTLE/BLOCK/ISOLATE carry OpenFlow **hard_timeouts** -> auto-expire and re-evaluate. Directly mitigates the ICS fear of a false-positive block severing legitimate operations (a mistaken response clears itself).

### OpenFlow mechanics this unlocks (answers Q1/Q3/Q6/Q7)
Meters (THROTTLE) · output+set-field (DEFLECT) · broader match/drop (ISOLATE) · hard/idle timeouts (self-healing) · OFPFC_MODIFY (in-place escalation). Turns "detect+drop" into "detect+steer".

### Implementation phases (do in order; TOMORROW = P0+P1)
- **P0 — Response-layer refactor.** Decouple *decision* (tier, unchanged) from *response* (new repertoire). Add a `respond_action(tier, conduit_state)` selector + per-conduit state (offense count, first/last seen). No behaviour change yet — pure structure so the rest slots in. Verify Cell-1/Cell-2 still block identically.
- **P1 — Self-healing timeouts.** Add `hard_timeout` to block flows -> auto-expiring blocks (no manual restore). Easy, always-supported, immediate "dynamic" win. Measure: block installs, expires after T, traffic resumes.
- **P2 — THROTTLE via meters.** VERIFY OVS/kernel meter support first (`ovs-ofctl -O OpenFlow13 dump-meter-features ovsgw`). If supported: create meter + apply-meter flow. If NOT: documented fallback = OVS per-port `ingress_policing_rate` (coarser) or note as future. Demo: flood -> throttled, not cut.
- **P3 — DEFLECT to honeypot.** Stand up a decoy endpoint (internal port / small VM). Redirect a FORBIDDEN conduit to it via output+`mod_nw_dst`. Demo: attacker reaches decoy, not PLC; real PLC untouched.
- **P4 — ISOLATE + persistence escalation.** Offense-count escalation THROTTLE->BLOCK->ISOLATE within a window.
- **P5 — Dashboard + audit + evaluation.** Show the *response type* per event (not just "blocked"); per-response color/label; export. Evaluate MTTM + effect per response; a criticality x response matrix.

### Rule-0 design questions to resolve before coding
1. Threat/persistence signal without DPI (A3 not yet): use Snort priority + repeat-count + proto. Is repeat-count-in-window a defensible "threat" proxy? (Proposed: yes, as *persistence*, distinct from *severity* which needs A3.)
2. Meter support on OVS 3.3.4 + this kernel — verify (P2 gate).
3. Honeypot endpoint: internal port with a logger vs a GNS3 VM — which fits the testbed cleanly?
4. Default response for a *first* FORBIDDEN detection: THROTTLE (graceful, false-positive-tolerant) vs immediate BLOCK (safer). Trade-off: ICS false-positive cost vs attacker dwell time. (Proposed: THROTTLE for SENSITIVE, fast-BLOCK-with-timeout for FORBIDDEN, tunable per policy.)
5. Do timeouts + escalation belong in the brain (controller state) or in flow timeouts (data plane)? (Proposed: both — data-plane timeout for self-healing, controller state for escalation memory.)

## Future roadmap (after A1)
- **A2 — Proactive allowlist** (default-deny conduits; pre-install allow for known-good ICS flows on protocol ports).
- **A3 — ICS-protocol DPI** (Modbus/S7comm function-code semantics; unauthorized WRITE = critical). Deepest novelty, hardest (S7comm weak DPI; may need a Modbus element).
- **A4 — Declarative policy rulebook** ((src,dst,proto,fcode,action,rate,timeout,condition) table; context: threat level, maintenance window, process state).
