# CARS — Live Demo Validation (Supervisor Walkthrough)
**Date:** 2026-07-13  ·  **Testbed:** 3× hardware Dell + GNS3 kill-chain  ·  **Controller:** cars_engine.py v0.7  ·  **Console:** cars_dashboard.py v5 (post dedupe+overlay patch)

All six scenarios executed against the live testbed and confirmed on the real-time console. Numbers below are measured, not modelled.

## Pre-demo dashboard fixes (validated in Test 1)
- **Dedupe:** modelled "OT FW (NAT)" anchor goes *solid* when `.1` is discovered; discovered duplicate is filtered → **single OT-FW node**.
- **Block-line reachability scoping:** block overlays only target switches present in `/cars/links` (fabric-reachable) → **one line to the reachable PLC1**, not the isolated PLC2 clone.

## Results

| # | Scenario | Trigger | Decision | Latency (cars_ms) | Console proof |
|---|----------|---------|----------|-------------------|---------------|
| 1 | External kill-chain | VPCS `ping 192.168.2.10` (via GNS3 → OT-FW SNAT) | **FORBIDDEN → blocked** | ~0.6 ms | single OT-FW → PLC1 red line; clears on restore |
| 2 | Insider | `ping -I att0 192.168.2.10` (.66) | **FORBIDDEN → blocked** | 0.804 / 0.589 ms | 1/5 replies (80% loss); red line from `.66` node → PLC1 |
| 3 | Supervisor (intelligence) | `ping -I sup0 192.168.2.10` (.30) | **OPERATIONAL → allowed** | 0.011 ms | 3/3 replies; green feed row; no topology change |
| 4 | Safety invariant | `POST /cars/respond {.9→.10}` | **CRITICAL → refused** | 0.008 / 0.005 ms | amber feed row; no block installed |
| 5 | Anti-spoofing | scapy forge src=.30 from att0 | **dropped at ingress (guard)** | n/a (data-plane) | guard panel `3 × dpid3 ip 192.168.2.30` |
| 6 | Live link health | `ovs-ofctl mod-port ovs1 <HMI1> down/up` | link state tracked | ~1 s | HMI1 link red on down, heals on up |

## Headline findings
- **Same PLC, opposite decisions** (Tests 2 vs 3): identical Snort alert to the PLC — insider blocked, supervisor allowed — purely on conduit criticality. The intelligence, made visible.
- **Allow/refuse are ~microseconds** (11 µs / 5–8 µs): pure classification, no enforcement. Enforcement (block) is ~0.6 ms including drop-rule install across all switches. The brain is effectively free; cost is only paid when acting.
- **Safety by construction** (Test 4): CARS structurally refuses to sever the HMI↔PLC control loop even when asked — the property that makes automated response safe to switch on in a live plant.
- **Defense-in-depth proven** (Test 5): the brain, reasoning on the *claimed* IP, would ALLOW a forged supervisor identity — and the feed shows exactly that OPERATIONAL log. The **data-plane source-guard dropped the packet anyway**, on `(switch,port,MAC,IP)` binding mismatch, before it could be forwarded. Identity is validated in the fabric, not trusted from the header. This is why two layers exist, not one.
- **Console = controller's live view** (Test 6): the dashboard is state-driven from the controller, not a static diagram — link changes surface in ~1 s.

## Three-colour decision feed (the at-a-glance artifact)
Green OPERATIONAL (supervisor) · Red FORBIDDEN (insider/external) · Amber CRITICAL (loop, refused) — the entire policy, live, in one panel.

---
## Cell-2 fabric integration — LIVE (2026-07-13, AG3)
Cell-2 (clone-IP `192.168.2.10` PLC, project-locked S7-1200) brought onto the fabric as `192.168.3.10` via a Dell#3 Linux NAT gateway (DNAT/MASQUERADE) over an **isolated point-to-point transit** (Dell#1 ↔ monitor-dock Ethernet ↔ cable ↔ monitor-dock ↔ Dell#3 — no lab switch, no VXLAN). Engine change: REGISTRY `.3.10→plc`, `.3.9→hmi` only (bindings/guard untouched; transit port deliberately NOT trusted as uplink, so the guard still drops any Cell-1 IP arriving over the transit).

| Test | Trigger | Decision | cars_ms | Result |
|---|---|---|---|---|
| Cell-1 unaffected | sup `.2.30 → .2.10` | OPERATIONAL/allowed | 0.012 | Cell-1 intact after redeploy |
| Cell-2 insider | `.3.66 → .3.10` | FORBIDDEN/blocked | 0.501 | live ping blocked → restore → `ttl=29` returns |
| Cell-2 supervisor | `.2.30 → .3.10` | OPERATIONAL/allowed | 0.011 | trusted conduit allowed |
| Cell-2 safety invariant | `.3.9 → .3.10` | CRITICAL/refused | 0.004 | loop refuse holds for Cell-2 |
| Live enforcement | block/restore `.3.66→.3.10` | — | 0.685 | ping: blocked=100% loss, restored=2/2 `ttl=29` |

**Result:** same criticality-aware intelligence on a second, physically distinct cell whose PLC could not be re-IP'd — the SDN fabric transparently integrated a clone cell. `ttl=29` (PLC native 30 minus one NAT hop) confirms the real device answered across the transit. Remaining: AG4 (Cell-2 Snort rules/mirror for autonomous detection) + dashboard `.3.10` anchor.
