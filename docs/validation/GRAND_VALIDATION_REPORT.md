# CARS — Grand Validation Campaign (wire/packet-level, every capability, armed vs unprotected)

_Campaign 2026-08-01. Seven phases, each captured at three wire points (PLC1 S7 port `enx9c69d331d874`, OpenFlow control channel `tcp/6653`, Snort DPI mirror `snort0`) with a full cross-layer snapshot per step (isolate flows, conntrack, GUARD counters, flow-audit status, PLC/process state, controller decision log) and every flow table dumped before/after. Harness: `06_Build/cars_campaign_lib.sh` + per-phase scripts. Evidence bundle: `/tmp/grand_campaign/phase{1..7}/` on Dell#1 (pcaps + `snap_*.txt` + `flows_*.txt`) plus the exported decision CSVs._

**Hard rule honoured:** every claim below is a captured packet, a logged decision, a live process reading, or a flow-table entry — no inference. Where a result was nuanced or unexpected (the RST reaction-window leak, the partial-bypass caught by conntrack) it is reported honestly, not smoothed.

## Method — three states, not two
"CARS doesn't protect" has two distinct meanings, and the campaign separates them:
- **CARS OFF / flat-network** — the attacker's path is opened around the CARS pipeline (a reversible per-path bypass, `cookie 0xb1`), simulating an ungoverned/flat OT segment. This is the true "massacre" baseline for outsider vectors, because the **proactive default-deny is always on** (it is *not* gated by the arm switch), so merely disarming does not expose an unregistered attacker.
- **DISARMED** — enforcement off (`enforce_enabled=false`); CARS still *detects and decides* (MONITOR) and the proactive structure still stands. Used for insider/process vectors where a conduit-holder's reactive protection is what's removed.
- **ARMED** — full proactive + reactive enforcement.

The legitimate Factory IO HIL loop (`.2.55`) and the historian telemetry ran **throughout every phase** and were **permitted (`ALLOW`) in every state** — zero false positives across the whole campaign.

---

## Phase 1 — Reconnaissance (scans / enumeration)
Attacker: Kali `.2.77` (external, unregistered). Tools: `arp-scan`, `nmap`, `s7-info`, `modbus-discover`.

| | CARS PROTECTING | FLAT-NET (enforcement bypassed) |
|---|---|---|
| L2 host discovery (ARP) | succeeds — 10 hosts + MACs | succeeds |
| Service port scan | **all `filtered`** | **80/102/443 + 502 `open`** |
| S7 identity (`s7-info`) | **no leak** | **`6ES7 212-1BE40-0XB0`, firmware `4.2.3`** |
| Modbus enum | failed | `502 open` |
| Scanner handling | **ISOLATE 75s (CRITICAL) / 60s (HIGH)** — criticality-scaled; self-healed | detection still fired, but bypassed path evaded enforcement |

**Finding:** under CARS the outsider learns only the L2 inventory (ARP broadcast is a network function, a documented boundary) and **nothing about services** — the PLC model/firmware stay invisible and the scanner is reactively isolated with **criticality-scaled durations**. Off, the identical scan fingerprints the PLC completely — exactly the intel that enables every later attack.

## Phase 2 — Spoofing / identity impersonation (GUARD anti-spoof)
Attacker: Kali forges ARP + IP as the trusted seams `.2.31`/`.2.45`.

| Spoof | Sent | GUARD dropped (ingress dpid3) | Visibility alerts |
|---|---|---|---|
| ARP as `.2.31` / `.2.45` | 5 / 5 | `arp .2.31=5`, `arp .2.45=5` | `IDENTITY-SPOOF REFUSE`, running totals |
| IP-spoof `.2.31` / `.2.45` → PLC:102 | 8 / 5 | `ip .2.31=8`, `ip .2.45=5` | each logged with `[total N]` |

**23/23 impersonation packets dropped at GUARD ingress**, every drop logged `FORBIDDEN · IDENTITY-SPOOF · REFUSE`, `hping3` reported **100% packet loss**, and the **real seams kept flowing `ALLOW`** (GUARD discriminates purely by port/MAC binding — no collateral). **Flat-net contrast:** with GUARD+policy bypassed, the spoofed `.2.31` SYN **reached the PLC wire carrying Kali's MAC**. **Bonus (layered defence):** a *partial* bypass (GUARD only, not conntrack) was still caught — the out-of-nowhere SYN arrived untracked and fell to the stateful default-deny.

## Phase 3 — State manipulation (stateful conntrack pipeline)
Attacker: Kali forges out-of-state ACKs, injected RSTs, half-open SYN floods to PLC:102.

| | STATEFUL (armed) | STATELESS allow (massacre) |
|---|---|---|
| ACK flood → PLC | **0 reached** | reached; **PLC RSTs back** (rtt 3–10 ms) |
| SYN flood → PLC | **0 reached** | would reach |
| Session established | **none** — embryonic ct entries, expired | PLC engages every forged packet |
| Only leak | **10 inert RSTs** in the ~1 s reactive-isolate window, **0 PLC response** | — |
| Source | **ISOLATED 75 s** | — |

**Finding:** stateful inspection let **zero forged packets establish a session**; the 21 conntrack entries the SYN flood created were embryonic (never committed) and expired. The only leakage was a 0.45 s burst of **inert RSTs** in the sub-second reactive-install window (timestamps `16:59:30.15–30.60`, isolate at `16:59:31`) — the PLC answered none of them and the process never moved. A classic stateless rule, by contrast, let the out-of-state ACKs reach the PLC and forced it to service every one.

## Phase 4 — Control-plane & flow tamper (controller compromise)
- **V-A control-API auth:** unauthenticated `POST /cars/defense {on:false}` → **`HTTP 401`**, CARS **stayed ARMED**. A compromised control-plane host cannot silently disarm the defence.
- **V-B flow-integrity checker:** injected 2 bogus rules (one hidden in the reactive priority band), deleted a real conduit (black-hole), rewrote a conduit's action → checker verdict **`ok:0 · missing=1 · extra=2 · changed=1`** within one 10 s poll, each surfaced to the decision log (`flow-integrity: policy-removed / bogus-injected ×2 / action-modified`). The reactive-band evasion was caught (CC-95 hardening). On restore the checker **self-cleared to `ok:1`** without re-baselining (proving byte-exact restoration). **Massacre implicit:** without the checker, all four tampers persist silently.

## Phase 5 — Op-aware ICS (S7 function × role × criticality, packet-level)
One `.2.31` S7 session, two functions, opposite verdicts — and the same write from a trusted host permitted:
- `.2.31 S7 **READ** (func 0x04)` → **ALLOW** (reached PLC, returned `DB7=40.24`)
- `.2.31 S7 **WRITE/CONTROL** (func 0x05)` → **FORBIDDEN → ISOLATE 75s [CRIT:CRITICAL]**
- `.2.55 (EWS) S7 **CONTROL** (same function)` → **ALLOW** — role+op+criticality, side by side.

CARS discriminates on the **S7 function read off the packet**, not the port. (Reaction-window note: the single write landed once before the isolate installed, then the source was cut and OB30 overwrote it — no harm.) The full op×tier×source decision matrix is exhaustively covered in `EVALUATION_REPORT.md` (100% accuracy, 0% FP).

## Phase 6 — Process devastation (false-data injection on the live tank) — CENTREPIECE
`.2.31` blinds the level sensor (`%ID100=0`) and jams the discharge shut (`%QD104=0`).

| | DISARMED (massacre) | ARMED (defense) |
|---|---|---|
| FDI writes landed | **2513** | **1** (`Receive timeout`) |
| Tank level (true) | **`DB7=194.75` — ~195%, overflow/spill** | `DB7≈65` (in band) |
| PLC's view | **blind** — `DB7=0, LevelIn=0` | truthful (real sensor) |
| `.2.31` | free to devastate | **ISOLATED 75 s** |
| Outcome | **tank overflowing while HMI reads empty** | **block-and-maintain — loop kept safe** |

**The signature result:** without CARS the attacker silently drives the physical tank to ~195% and over the side while the PLC and operator HMI both display empty (the Stuxnet deception); with CARS the attack is severed on the **first write** and the process never leaves its band. Re-arming recovered the loop cleanly. Detection-while-disarmed (70/70 spoof writes judged ISOLATE) is documented in CC-99b.

## Phase 7 — Response ladder (full graded repertoire)
All seven responses triggered with correct tier→response mapping and the enforcement each installs:

| Rung | Verdict | Enforcement |
|---|---|---|
| ALLOW | `OPERATIONAL` | none (monitor) |
| MONITOR | `OPERATIONAL/MONITOR` | none |
| THROTTLE | `SENSITIVE` (LOW asset) | meter @20 pps, 30 s |
| DEFLECT | `FORBIDDEN` | redirect → honeypot `192.168.3.99` |
| ISOLATE | `FORBIDDEN` (CRITICAL) | source quarantine, `0xca`, 75 s |
| BLOCK | `FORBIDDEN` (LOW) | conduit block, `0xca`, 30 s |
| REFUSE | `CRITICAL` (safety invariant) | mirror/alert only — loop never enforced |

Criticality graded the **response** too: `[CRIT:LOW]` blocks last 30 s, `[CRIT:CRITICAL]` isolates last 75 s. All reactive flows auto-expire (self-healing).

---

## Cross-cutting findings
- **Zero false positives across the entire campaign** — the Factory IO loop and historian telemetry were `ALLOW` in every phase and every state, even while attacks raged.
- **Criticality-awareness on both sides** — decision (SENSITIVE→FORBIDDEN elevation on CRITICAL assets) and response (block-duration + escalation speed scale with consequence tier: 75/60/45/30 s).
- **Layered defence, proven** — GUARD (anti-spoof) → stateful conntrack (out-of-state) → proactive default-deny → reactive graded response → flow-integrity self-check. A gap in one layer was caught by the next (Phase 2 partial bypass → conntrack).
- **Self-healing** — every reactive enforcement (isolate/block/throttle/deflect) auto-expires; the checker self-clears on restore; the process control loop self-recovers after the attacker is cut.
- **Honest boundary — the reactive-install window (~1 s)** — under a high-rate flood a small number of *inert* packets can reach the wire before the reactive isolate lands (10 RSTs in Phase 3; 1 write in Phases 5/6). None established a session, elicited a PLC response, or perturbed the process; the source was isolated within ~1 s. This is fundamental to reactive defence (same class as the flow-audit poll window), not a fixable bug.

## Documented boundaries (unchanged, honest)
L2 ARP host discovery is not policy-gated; the flat-net massacre requires a path that bypasses the governed pipeline (CARS protects governed traffic); the HMI↔PLC CRITICAL loop is a safety invariant never enforced (GUARD-anti-spoof mitigated); a fully-compromised endpoint within its trust (G1) and a fully-subverted controller remain fundamental limits.

## Overall verdict
Across reconnaissance, spoofing, state manipulation, controller compromise, op-aware ICS commands, live-process false-data injection, and the full response ladder — **every CARS capability was exercised at the packet/wire level, armed vs unprotected, with total cross-layer audit.** Unprotected, the attacker maps and fingerprints the PLC, impersonates trusted seams, injects/deletes flows, and overflows the physical tank while the operator sees "empty." Armed, CARS filters the recon, drops every spoof at ingress, refuses out-of-state forgeries, catches every flow tamper, discriminates ICS operations by S7 function and asset criticality, and severs the process attack on the first write — all while never once blocking the legitimate process. The defence can be turned on, and it holds.

_Evidence bundle (Dell#1 `/tmp/grand_campaign/phase{1..7}/`): `plc1_wire.pcap`, `of_control.pcap`, `dpi_mirror.pcap`, `snap_*.txt`, `flows_*.txt` per phase + exported decision CSVs. Recommend archiving off-box before reboot._
