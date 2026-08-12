# Project CARS — One-Week Wrap-Up Plan & Feasibility Decision

_Compiled 2026-07-29. Governs the final technical week. Folds in the two literature-grounded new candidates (from `PAPER_EXTRACTION_NECESSITY.md`) alongside the remaining gap-fixes and the agendas decided earlier (`SYNC_STATE.md` → NEXT AGENDAS). Hard rule honoured: retrofits first (make existing capabilities whole before adding new); prime directive: save process at any cost; every claim of "done" must be proven live or in isolation, not asserted._

---

## The feasibility question, answered

**Can the two new candidates be implemented, and can everything be sorted in a week alongside the remaining gaps and agendas?**

**Yes — with one honest split and one honest trim.**

- **Candidate A (flow-integrity / policy checker) — FEASIBLE this week.** Small, self-contained, testable in isolation, high dissertation value. It ships.
- **Candidate B (MoTaR-style property deception, P0-6) — DESIGN + ISOLATED PROTOTYPE only this week.** The mechanism rewrites what the HMI presents on the wire; getting it wrong regresses the live panel. It is not safe to rush to live in the same week we are wrapping everything else. Design + throwaway-bridge prototype now; dedicated live-rollout session later.
- **Trim to keep the week real:** SDN Phase 4 (analytics) is optional/light; SDN Phase 5 (P4/BMv2) is an isolated stretch demo; Modbus re-add is deferred (it needs a Node 18→22 upgrade that risks the running Node-RED stack). Cramming these would put the wrap-up — and the process — at risk for feature-count, which violates the prime directive.

Net: the week delivers a **whole, proven system** (retrofits complete, one new novelty shipped, the buildable SDN phases done, supervisory hygiene closed) rather than a wide-but-shaky one.

---

## Effort & feasibility table

| Item | Task | Effort | Live risk | In-week? |
|---|---|---|---|---|
| Stateful attack-path re-verify (CC-89 seal gap) | — | S | low | ✅ yes |
| Retrofit remediation → all PLCs (Tank2) | #25 | M | med (S7 slot limits) | ✅ yes |
| Retrofit GUARD anti-spoof → all devices/seams | #26 | M | low | ✅ yes |
| **New A: flow-integrity / policy checker** | #28 | S–M | low (read-only audit) | ✅ yes |
| SDN Phase 2: control-loop QoS/metering (live) + failover (isolated proto) | #21 | M | med | ✅ yes |
| SDN Phase 3: dynamic micro-segmentation | #22 | M | med | ✅ yes |
| /ui polish + rotate `cars-token-change-me` + cosmetic registry tidy | #17 | S | low | ✅ yes |
| Final no-regression sweep + capstone combined pen-test | #18 | M | med | ✅ yes |
| **New B: property deception (P0-6)** | #29 | L | **HIGH (live HMI)** | ⚠️ design + isolated proto only |
| SDN Phase 4: cross-flow analytics | #23 | M–L | low–med | ⚠️ light version optional |
| SDN Phase 5: P4/BMv2 line-rate (isolated Mininet) | #24 | L | none (isolated) | ⚠️ stretch/demo only |
| Modbus re-add (Node-18 compatible) | #14 | M | med (Node upgrade) | ❌ deferred |

_S ≈ ¼–½ session, M ≈ 1 session, L ≈ 2+ sessions._

---

## Day-by-day (7 sessions)

**Day 1 — Close the CC-89 seal gap + start the biggest retrofit.**
Re-run the full no-regression sweep with `STATEFUL=True` on the **attack path** (reactive ISOLATE/BLOCK, A3 op-awareness, criticality response, remediation all still fire under the ct pipeline). Then begin the remediation retrofit design (config-driven, multi-PLC).

**Day 2 — Retrofit remediation to ALL PLCs (#25).** Biggest whole-topology gap: Tank2 currently has no remediation. Make `cars_remediation.py` PLC-list-driven (PLC1 `.2.10` band 30–70, PLC2 via NAT `.3.10`→`.2.10` band 20–55), mind the 1212C S7 connection limit. Prove: Tank2 DB7 spoof → CARS block **and** last-good restore, both cells.

**Day 3 — GUARD anti-spoof → all devices (#26) + flow-integrity checker (#28).** Bind Modbus `.2.20` + trusted seams (`.2.31`/`.2.45`/`.2.55`/`.3.66`) into GUARD BINDINGS; verify a spoofed `.2.45`/`.2.31` is dropped. Then build `cars_flow_audit.py` + isolated test (throwaway bridge, like `cars_stateful_test.sh`): inject a bogus/removed flow → auditor raises drift alarm + audit-log.

**Day 4 — SDN Phase 2 (#21).** Control-loop QoS/metering: guarantee S7/Modbus loop latency under a DoS burst (OVS meters/queues on the control-loop conduits, both cells). Fast-failover as an **isolated** prototype only (topology is single-uplink → real failover needs a redundant link we don't have live).

**Day 5 — SDN Phase 3 (#22).** Dynamic micro-segmentation: time-bounded conduits as data-plane flows (extends the existing allowlist/maint-window infra to auto-expiring per-conduit flows across the whole topology).

**Day 6 — Deception design + supervisory hygiene.** Candidate B (#29): write the property-deception design + build the **isolated** prototype (present false OS/banner properties to unlisted sources on a throwaway bridge; verify `+est` still passes legit replies). NO live HMI. Then `/ui` polish, **rotate `cars-token-change-me`** and the InfluxDB token (#17), cosmetic registry tidy (.3.66 criticality, deployed name strings).

**Day 7 — Consolidate & seal.** Full no-regression sweep across the whole topology; capstone combined-vector pen-test (both tanks: spoof + actuator flip + flood, disarmed vs armed) to capture the protected-outcome result. Update `SYNC_STATE.md`, `DECISION_LOG.md`, `PEN_TEST_PLAYBOOK.md`; mark the technical part wrapped.

---

## Explicitly deferred (with reasons, so nothing is silently dropped)

- **Property-deception live rollout (#29)** — mechanism rewrites live HMI wire properties; a regression blanks the panel. Deserves its own session after the wrap-up, not a rushed slot. _This week: design + isolated proof only._
- **SDN Phase 4 analytics (#23)** — a lightweight scan/lateral-movement detector is optional if Day 4–5 run ahead; the full campaign-detection version is post-wrap-up.
- **SDN Phase 5 P4/BMv2 (#24)** — isolated Mininet only, never the live tanks; large. Stretch/demo if time remains, else a documented future-work item (still defensible: it's the line-rate ceiling of the op-enforcement idea).
- **Modbus re-add (#14)** — blocked by `contrib-modbus@5.60` needing Node ≥ 22 vs the installed Node 18; the upgrade risks the running Node-RED collector. Non-core to the novelty; deferred unless a Node-18-compatible Modbus node is found.

---

## Success criteria for "technical part wrapped"

1. Every core capability applies **across the whole topology** (both cells, all PLCs, all trusted seams) — the hard rule satisfied, not Cell-1-only.
2. The two retrofits (#25, #26) proven live; the flow-integrity checker (#28) proven in isolation + wired to CARS alarms.
3. SDN Phases 2–3 live; Phase 1 already sealed.
4. Control loop never broken during any change (loop-watch on every deploy); one-command rollback documented for each.
5. All decisions logged in `DECISION_LOG.md`; final no-regression sweep green.

_Feasibility verdict stands: a disciplined week wraps the technical part with both new candidates folded in — A shipped, B designed+prototyped — provided Phase 4/5 and Modbus stay deferred as above._
