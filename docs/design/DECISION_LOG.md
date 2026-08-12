# Decision & Assumptions Log — Project CARS

Living document. Purpose: hold the project's reasoning honest to the finish —
every material decision, its justification, its risk, and what would falsify it.
Standing mandate (from Amit): apply deep analysis, sharp questioning, and strong
reasoning throughout; push back on our own decisions, including this list.

_Last updated: 2026-07-24 (CC-78 deep audit)_

---

## Research Integrity Rules (standing — non-negotiable, from Amit)
**★ QUESTION EVERYTHING — the prime rule (highest priority, from Amit 2026-07-08).**
- Challenge **every statement that defines the engine, every piece of logic implemented, every change to scope or goal, and every modification to the core logic** — *before* it is accepted. Deep technical reasoning is mandatory and never skipped.
- Nothing enters the engine or the design unchallenged; if a claim, mechanism, or decision cannot survive rigorous scrutiny, it does not go in.
- This outranks momentum, convenience, and prior recommendations — my *own* proposals get challenged as hard as anyone's. (Basis for this rule: the device-vs-conduit criticality challenge, CC-15 — exactly the kind of scrutiny that must be routine.)

**No hallucination, no fluff, no gap.**
- Every factual/empirical claim has a source, or is tagged `[UNVERIFIED]` / `[ASSUMPTION]`. No invented specifics (versions, figures, quotes, IDs) stated as fact.
- **Measured** results vs **expected/claimed** are always labelled distinctly. Testbed numbers = measured only.
- Gaps are named explicitly, never smoothed over. "I don't know / can't verify" is a valid, required answer.
- No padding or filler. Concision is a quality criterion.
- **Citation status:** local-folder papers = verified (titles extracted from the PDFs). Web-sweep citations = titles/venues from search snippets, **arXiv IDs / DOIs / years NOT individually verified** → must pass CC-5 before entering the dissertation.
- **File-locked context (hard rule, from Amit):** everything is **locked in the files**, never left only in chat. Every decision, number, assumption, or change is written to the relevant file **in the same session it is made**. `START_HERE.md` + this log are the single source of truth; the record must stay **bulletproof with no gap** — no dangling references, no detail that lives only in memory. File-set audited complete on 2026-07-05. Superseded files moved to `_archive/` (not deleted) same day; references updated so no dangling links.

---

## North Star (confirmed)
**Thesis:** A productizable, trustworthy **reactive-and-proactive SDN defense for ICS**
that consumes detection events and enforces **criticality-aware network responses**
which are *provably safe* — bounded, reversible, and evidence-generating — so that an
operator can enable automated response **without risking the physical process**.

**Value proposition (product pitch, one line):** "Automated network response for OT that
you can actually turn on — it reacts to threats at the zone boundary and guarantees it
will never trip your process, with an audit trail to prove it."

**Why it's impactful:** a decade of reactive-SDN-for-ICS research exists but is not
deployed, because operators fear the defense causing the outage. The bottleneck is
*trust*, not detection accuracy or a new response type. Removing that barrier is the
industry contribution.

---

## Confirmed decisions (with reasoning)
| # | Decision | Reasoning |
|---|----------|-----------|
| D1 | Tier 3 testbed, built **incrementally** from a minimal loop | Fidelity is a means; a working reactive contribution + evaluation is the goal. |
| D2 | De-scope **fidelity, never the contribution**, if behind | 6 weeks is real; the marks are in the mechanism + evaluation. |
| D3 | Position CARS at **IEC 62443 zone boundaries / conduits** (overlay, not greenfield) | Brownfield deployability = product realism; matches Tier 3 zone topology. |
| D4 | **Consume** existing detection (Suricata/Zeek; vendor IDS in field), don't reinvent it | Deployability + scope control; novelty goes to the reaction. *(confirm)* |
| D5 | "Proactive" scoped to **criticality-aware posture escalation**, not MTD randomization | MTD risks OT determinism and is scope-heavy in 6 weeks. *(confirm)* |
| D6 | Novelty budget → the **safety guarantee** (bounded, reversible, twin/envelope-validated) | This is the differentiator and the product's central claim. |
| D7 | Detection = pluggable interface; real detector wired for end-to-end demo | Product appeal + complete demonstration. |

## Hardware inventory — GROUND TRUTH (2026-07-05, from photos; supersedes earlier assumptions)
- **2× Siemens S7-1200 PLCs**, each with a **real SIMATIC HMI Basic panel** (looks like KTP700 Basic — confirm exact model). Real I/O: 24 V DC inputs, relay outputs, analog input.
- **MikroTik hEX lite (RB750r2)** router/switch. OpenFlow: `[VERIFIED 2026-07-05]` experimental only, **RouterOS v6 last supported it** (not v7); package availability for hEX lite (smips) unconfirmed. → **not** the critical-path SDN switch.
- 3× UGREEN USB 3.0 → Gigabit Ethernet adapters · several Ethernet cables (more added 2026-07-07).
- **NEW (2026-07-07): MikroTik hAP ac lite (RB952Ui-5ac2nD)** — 5× **10/100 Mbps** ports, 650MHz MIPSBE, 64MB RAM, PoE-out port5. [VERIFIED specs]. Capability = plain/VLAN switch only (no OVS, no containers, OpenFlow v6-EOL). 100M fine for PLC traffic → serviceable **OT-zone VLAN-trunk aggregator** later; not needed now.
- **Port/IP constraint (2026-07-07):** Dell#1 has only **1 free Ethernet port** (2 USB used by box1 PLC+HMI, no free USB slot). **Both teaching boxes are identical clones → same IPs (PLC .10 / HMI .9)** → cannot share one flat L2 without re-IP. Full dual-box OVS visibility (4 device ports) needs USB hub OR hAP VLAN-trunk OR re-IP box2.
- **DECISION (2026-07-07):** Single box suffices to build+prove CARS. Second box only adds criticality-differentiation (evaluation-phase). **Recommend: build CARS engine now; add box2 later via re-IP (PLC-B .20 / HMI-B .19) onto one OVS.** Optional cosmetic: box2 on br1 (built-in port, separate segment) for a 2-switch diagram, but no intra-box2 control without more ports. Guard against endless topology exploration — topology ≠ contribution.
- 2× Dell (Win/Ubuntu dual-boot, full admin, 16G
### CC-20 — Close all gaps: full-coverage detection + generalized policy (2026-07-10)
**Gap found:** insider `.66 → HMI1 (.9)` flowed freely — NOT a brain decision, a **detection gap** (Snort watched only PLC1 `.10`, ICMP only). **Lesson (dissertation): autonomous response is bounded by IDS coverage.**
**Fixes:**
1. **Detection** (`/etc/snort/cars.rules`): now **ICMP + TCP-SYN** to **both** critical assets — PLC1 `.10` and HMI1 `.9` (sids 1000001–1000004). Covers recon (ICMP) + connection attempts / S7comm / scans (TCP-SYN).
2. **Policy** (`classify()`): `if d == "plc"` → **`if d in ("plc","hmi")`** — both critical assets now get the full conduit treatment (unknown/gateway = FORBIDDEN·block, ews = SENSITIVE, supervisory = OPERATIONAL·allow); the PLC↔HMI loop stays **CRITICAL → REFUSED**.
**Coverage now complete for every scenario to date** (ICMP + TCP): external→PLC/HMI = BLOCK · insider→PLC/HMI = BLOCK · supervisory→PLC/HMI = ALLOW · loop = REFUSED.
**Residual limitations — documented as "threats to validity", NOT bugs:**
- **Cell 2** not in the mirror/detection path (deferred to DNAT re-integration, P4).
- **IP-identity** ⇒ an attacker spoofing a *trusted* IP would be mis-classified — needs MAC↔IP / port-security binding (future work).
- **External NAT** ⇒ attacker appears as `.1` (OT-FW), so its block is coarse for IT-origin traffic (per CC-19).
- **Signature detection** ⇒ only flagged patterns reach the brain; anomaly/ML detection is future work.

### CC-21 — Multi-homed OT host ARP flux (2026-07-12)
Discovery flagged `att0`'s MAC (`b6:27`) presenting IP `.30` (sup0's IP). **Root cause:** `sup0` (.30) and `att0` (.66) are both internal interfaces on Dell#1 on the **same 192.168.2.0/24 subnet** → default Linux answers/announces a local IP out *any* same-subnet interface (**ARP flux**). Also the root of the earlier "two MACs at .30". **Fix:** `net.ipv4.conf.all.arp_ignore=1` + `arp_announce=2`, persisted in `/etc/sysctl.d/99-cars-arp.conf`. Each interface now owns only its IP. Discovery clean: `.30↔sup0` only, `.66↔att0` only. *(Real deployment gotcha for multi-homed OT hosts — dissertation note. Cleaner long-term: put att0 in its own netns.)*

### CC-22 — Data-plane source-guard / anti-spoofing (two-table pipeline) (2026-07-12)
**Threat:** `classify()` trusts the source IP, so spoofing a trusted IP (historian → OPERATIONAL/allow) or the loop IP (HMI → CRITICAL/refuse = weaponized safety shield) bypasses CARS. **Fix (v0.6):** two-table pipeline — **Table 0 = source-guard** (IP↔MAC↔port bindings, verified from `ovs-ofctl`), **Table 1 = switch/brain (unchanged)**. A packet claiming a protected IP (`.9/.10/.30`) from the wrong port/MAC is **dropped at ingress**. **Staged safely:** (1) plumbing guard-off → forwarding proven identical; (2) bindings verified vs live discovery; (3) armed + spoof-tested. **VERIFIED:** legit `sup0`/loops untouched; forged `.30` and `.9` from att0 dropped in Table 0 (`n_packets` climbing); discovery uncorrupted under attack. Closes **HP1** (spoofing) + **HP2** (CRITICAL-shield abuse). **Residual:** IP-layer only — ARP-layer spoofing still open (ARP-guard = follow-up); `fail_mode: standalone` (HP4); bindings must be re-verified if ofports change. Control: `GUARD_ENABLED` flag in `cars_engine.py`; backups `cars_engine_v051.bak` (v0.5.1), `cars_engine_v04_stable.bak`.

### CC-23 — ARP-guard / dynamic ARP inspection (2026-07-12)
Completes the L2 residual of CC-22. Table 0 now also validates ARP **senders**: per binding, allow `(in_port, arp_spa=ip, arp_sha=mac) -> resubmit(,1)`; drop any protected `arp_spa` (`.9/.10/.30`) from the wrong sender = ARP cache poisoning. Staged via `ARP_GUARD_ENABLED` (off -> prove -> on). **VERIFIED:** legit `sup0` ARP passes the priority-200 allow (resubmit to table 1); a forged gratuitous ARP from att0 claiming `.30` dropped at ingress (`priority=100,arp,arp_spa=.30`, n_packets=3/3). **Anti-spoofing now COMPLETE at L3 (IP) + L2 (ARP).** Both flags armed: `GUARD_ENABLED=True`, `ARP_GUARD_ENABLED=True`. Residual: att0's own `.66` ARP still passes (correct — not impersonation); re-verify bindings if hardware re-plugged.

### CC-24 — Fail-secure control-plane resilience (2026-07-12)
Empirically characterized controller-death behavior. **Finding:** `fail_mode: standalone` **FAILS OPEN** — on controller loss OVS flushed table 0 (guard/blocks gone, `grep -c priority`=0) and reverted to fail-open forwarding; a forged `.30` was NOT dropped. Availability kept, **enforcement lost** → an adversary DoS-ing the control plane bypasses CARS. **Decision:** `fail_mode: secure` on all bridges (ovs1/ovsgw/ovs2). On controller loss OVS **keeps** installed flows; because CARS flows are permanent (no idle timeout) the established loops survive **and** the guard/blocks hold. **VERIFIED with controller DEAD:** table 0 kept 12 flows; `sup0`→PLC still pinged 2/2; forged `.30` still dropped (priority-100, n_packets=3). Enforcement no longer lifts under control-plane attack. `fail_mode` persists in OVSDB (survives reboot). **Documented residuals:** (a) switch reboot *during* a controller outage → empty table = blackout until CARS returns (mitigation: controller auto-restart/HA); (b) ARP re-resolution during a *long* outage still needs the controller (broadcast flood via packet_in) — mitigation: a permanent broadcast-flood flow (refinement) or brief restarts.

### CC-25 — Cell-2 (per-cell) enforcement + fail-secure ARP availability (2026-07-12)
**HP3:** `block_conduit`/`unblock_conduit` now enforce on **every connected switch**, so a block reaches the target's actual cell (isolated Cell 2 / clone IPs) instead of only the default gateway dpid. **VERIFIED:** `/cars/respond .77→.10` installed the drop on **ovs2 (dpid 2) table 1**, not just ovsgw. **Residual:** Cell 2 still has **no IDS detection** (Snort mirrors ovsgw only; ovs2 is isolated) — a Cell-2 attack is now *blockable* but not yet *detected*; full coverage needs the P4 transit or a 2nd sensor on Dell#3 (ties to P4).
**HP4 completion:** the fail-secure ARP-outage caveat (CC-24 residual b) was **empirically confirmed** — at a ~18-min outage the sup0↔PLC loop broke (100% loss) once ARP caches expired, while enforcement still held. **Fix:** a permanent **broadcast-flood flow** (table 1, priority 2, `eth_dst=ff:ff:ff:ff:ff:ff → FLOOD`), installed **behind** the Table-0 ARP-guard so spoofed ARP is still dropped first. **VERIFIED:** controller STOPPED + `ip neigh flush all` + `ping sup0→PLC` = 3/3. Fail-secure now preserves **both** enforcement *and* the control loops across an outage of any length.

### CC-26 — Discovery survives a controller restart (clean-slate on connect) + dashboard hardening (2026-07-12)
**Finding:** with fail-secure (persistent flows) + the HP4 broadcast-flood, after a controller restart ongoing traffic rides the persisted table-1 flows → no packet-in → the controller never re-learns hosts → `/cars/hosts` blank (PLC1 was UP with 7194 pkts through its guard allow, yet undiscovered). **Fix (HP5):** on switch (re)connect, `OFPFC_DELETE` all flows (`OFPTT_ALL`) then rebuild the baseline (table-miss, broadcast-flood, guard) — forces re-learning. Compatible with fail-secure (persistence matters while DOWN; this clears only on *reconnect*, controller present). **VERIFIED:** post-restart all active hosts (PLC1/HMI1/PLC2/HMI2) re-discovered within seconds. **Dashboard hardening:** filter IP-less infra ports, dedupe block-everywhere overlays, `src-guard`/`arp-guard` armed badges, controller-offline indicator, no "port undefined". *(Process note: the first clean-slate patch anchor was too specific and silently no-op'd — always `grep`-verify a patch landed.)*

### CC-27 — Independent security code audit of cars_engine.py v0.6 (HP6, 2026-07-12)
A subagent performed a skeptical review of the hardened engine vs CC-20..CC-26. Core design validated sound (two-table guard separation, IP/ARP path split, fail-secure ordering, block/unblock flow handling, DELETE_STRICT usage). Findings + resolutions:
**Fixed in code:**
- **H-2** repo/log mismatch: repo had `ARP_GUARD_ENABLED=False` while CC-23 says armed (deployed Dell#2 IS armed — poison test verified). Repo set to True.
- **M-4** eventlet race: `/cars/hosts` + `/cars/ports` iterated live dicts → possible "dict changed size" 500 under concurrent packet-in. Snapshot with `list(...)`.
- **H-4** misleading audit: block log said "@ dpid=3" but block-everywhere installs on all switches → now logs the actual dpid set.
- **L-1** phantom hosts: `_sw_dead` now purges `self.hosts` for the dead dpid.
- **L-2** silent audit-write failure → now warns once.
**Scoped / documented (threats-to-validity, not fixed now):**
- **C-1 / H-1 (P4 prerequisites):** the P150 uplink-trust + `UPLINKS[3]` are sound for the CURRENT topology (ovs1↔ovsgw is a virtual OVS patch, not attacker-reachable; ovs2 is isolated), BUT become exploitable when P4 adds the PHYSICAL VLAN-30 transit — a spoof on that segment would bypass the guard, and legit Cell-2 return traffic (`.10`/`.9` sourced) transiting the spine would be P100-dropped. **Anti-spoofing (CC-22) is hereby scoped to access-port attackers.** Harden P150 (rank P100 above uplink pass, or bind protected IPs on the transit in_port) BEFORE enabling P4.
- **M-2** SENSITIVE/EWS is dead code — no EWS in REGISTRY, so the SENSITIVE tier is never reached. Reclassified as **designed-but-not-deployed**; CC-20's "ews=SENSITIVE" is a design case, not a verified path.
- **H-3** brain trusts detector-reported IPs — CRITICAL-REFUSED is weaponizable / produces misleading audit entries whenever the guard doesn't cover the attack path (see C-1). Future: brain should cross-check src IP against BINDINGS/`self.hosts` before honoring REFUSED.
- **M-1** controller restart lifts all active blocks (clean-slate wipes them; sets re-init empty) — mitigated by the reactive loop re-detecting, but a restart momentarily un-blocks a live attack. Future: replay blocks on reconnect / persist them.
- **M-3** Event API is unauthenticated on `0.0.0.0` — mitigated by out-of-band mgmt plane (CC-17); future: bind mgmt-only + token.

### CC-28 — MTTM evaluation: CARS is sub-ms, sensor-bounded (2026-07-13)
Insider-path MTTM, 20 trials, single-clock. **CARS decide+enforce = 0.613 ms mean** (0.378–0.904 ms). **End-to-end MTTM = 1.132 s mean** (median 1.127, std 0.673, min 0.139, max 2.802). CARS = ~0.05% of MTTM; ~99.95% is Snort detection (libpcap/alert buffering — proven upstream of the bridge: tightening the bridge poll dropped the min to 48 ms but not the mean). Instrumentation: engine v0.7 `resp_ms` + `cars_ms` in `respond()`; `/cars/status.cars_ms_avg`. Thesis point: reactive SDN response is sub-ms and negligible; MTTM is bounded by (and improves with) the detector, independent of CARS. Detail: `07_Evaluation/MTTM_EVALUATION.md`.

## CC-29 (2026-07-13): Cell-2 fabric integration — DCP re-IP blocked, pivot to Linux NAT gateway
**Goal:** put Cell-2 (clone IPs .2.10/.2.9) on the fabric as a distinct subnet (192.168.3.0/24) so it can share a guarded transit without colliding with Cell-1.

- **Re-IP attempt (PROFINET DCP, pnio_dcp on Dell#3):** DCP *identified* PLC2 (e0:dc:a0:46:ff:ce, plcxb1d0ed, .2.10) but every `set_ip_address` (permanent AND temporary) was **acknowledged and ignored** — IP never left .2.10. **Finding: the S7-1200 IP is fixed in the downloaded TIA project; without that project the device cannot be re-IP'd, and factory-reset is off the table (wipes the program we can't reload).** Documented, not a dead end we caused.
- **Pivot (challenged options: OVS-native OpenFlow NAT vs VyOS/GNS3 NETMAP vs Linux NAT):** chose **Linux NAT gateway on Dell#3** — robust kernel NAT, no GNS3, minimal engine change. Rejected OVS-native after designing it against the code (it becomes an in-controller NAT-router: proxy-ARP + IP rewrite + next-hop routing — real but fragile over remote copy-paste).
- **Build:** `cell2gw` internal port on ovs2 = 192.168.2.1 (the boxes' configured gateway, so PLC/HMI talk to Dell#3 locally). NAT: `DNAT .3.10->.2.10` inbound + `MASQUERADE` toward the PLC so it only ever sees its gateway — kernel handles ARP + the reverse path via conntrack.
- **Robustness finding (build lesson):** the source-guard binds IP<->MAC<->**ofport**. Re-adding PLC2's USB port during the DCP work moved it ofport 1->4, so its .2.10 ARP fell into the P100 anti-spoof drop (**4,586 legit ARP replies silently dropped**) while HMI2 (untouched, ofport 2) worked. Fix: `ofport_request` pinned on both access ports so replug can't break the binding. **Action item: pin ofport_request permanently in the OVS boot config.**
- **VALIDATED (no extra hardware):** a namespace standing in for the fabric (.3.66) pinged **192.168.3.10 -> 3/3 replies, ttl=29** (PLC native ttl=30, minus the NAT hop) = a host knowing only the .3 identity reached the real PLC and was answered. Cell-2 = 192.168.3.0/24 proven.
- **Remaining (blocked on hardware):** live fabric transit ovs2<->ovsgw needs a 2nd Ethernet NIC (only one Type-C->Eth converter on hand). Options: (A) a 2nd USB/Type-C->Eth adapter -> clean dedicated cable [recommended]; (B) VXLAN over the mgmt link [today, but OT transit rides the control-plane wire — documented compromise of CC-14 separation]. Engine reg entries (.3.10->plc, .3.9->hmi), Snort/enforcement at ovsgw, and dashboard anchors follow once the transit is up.

## CC-30 (2026-07-15): Two-cell testbed — reboot-proven, fully green end-to-end
Full power-cycle recovery verified. After a cold boot, everything came back on its own except the
Snort daemon (started by hand by design):
- **Fabric:** controller + ovs1/ovs2/ovsgw up, src-guard + arp-guard armed, discovery clean.
- **Cell-2 transit persisted:** `cars-cell2.service` (Dell#3) re-applied cell2gw `.2.1`, eth0
  transit `.3.1/.3.10`, DNAT/MASQUERADE, and ofport pins at boot; Dell#1's `ovsgw` transit port +
  `ofport_request=9` restored from the OVS DB; monitor-dock NICs came back as `eth0` on both ends.
  Post-boot `ping .3.10` = **ttl=29** (real PLC via one NAT hop). The end-of-session ARP stall was
  a monitor-dock frame stall — cleared by the fresh power-up, exactly as predicted.
- **Cell-2 autonomous loop (AG4):** Snort (cars.conf, rules sid 1000005-8 for `.3.10/.3.9`) on the
  persisted `m0` mirror -> `snort_bridge.py` -> CARS. `ping .3.10` from `.3.66` self-blocked
  (1/15 through, then FORBIDDEN, sub-ms), **no manual API call**. Dashboard rendered the block-line
  to the `Cell-2 NAT · PLC2 .3.10` node live.
- **Discovery correctness (from live dashboard):** all 8 real endpoints resolved with correct
  dpid+port; **clone IPs handled** — PLC1/PLC2 both `.2.10`, HMI1/HMI2 both `.2.9`, separated by
  `dpid+port` (ovs1:p1 vs ovs2:p1). Only non-discovered IPs are the external attacker (behind NAT)
  and `.3.10` (NAT alias of `.2.10`, shown by the modeled node) — both correct.

**Dashboard additions this session:** `Cell-2 NAT · PLC2 .3.10` anchor + transit links
(ovsgw->nat2->ovs2); `.3.1` relabelled as **Cell-2 GW** (was rendering as red unknown); **Export
JSON** button (downloads every node's inspector data + links + live feeds as a local snapshot).

**Status: AG3 + AG4 COMPLETE. Two fully-protected cells, autonomous detection, reboot-persistent,
live on the console.** Remaining (future/optional): external-path MTTM (scripted VPCS), Snort
DAQ/pcap tuning, dissertation write-up (chapters assemble from DECISION_LOG CC-1..CC-30 +
DEMO_RESULTS.md).

## CC-31 (2026-07-16): A1 graduated-response build — P0 (decision/response decoupling) + P1 (self-healing)
- **P0 — decouple decision from response.** respond() split into DECISION (classify -> tier, unchanged),
  RESPONSE selection (select_response -> repertoire ALLOW/MONITOR/THROTTLE/DEFLECT/ISOLATE/BLOCK/REFUSE),
  and enforcement (enforce_response -> OpenFlow). Added per-conduit state (offense count, first/last seen)
  for escalation. New output fields `response` + `offense`. Behaviour IDENTICAL to v0.7 (verified:
  OPERATIONAL/allowed, FORBIDDEN/blocked, CRITICAL/refused unchanged). Pure scaffolding for P2-P4.
- **P1 — self-healing timeouts.** Blocks now carry `hard_timeout=BLOCK_TIMEOUT` (30s) + OFPFF_SEND_FLOW_REM;
  a FlowRemoved handler clears controller state and logs `block AUTO-HEALED (timeout)`. Verified: block on
  all 3 dpids -> after 30s with no traffic the flows expire, /cars/status empties itself, AUTO-HEALED logged
  per dpid. A continued attack renews the timer (Snort re-detects each cooldown). => dynamic/self-healing:
  a ceased attack or false-positive block dissolves on its own, no manual restore -- mitigates the ICS fear
  of a mistaken block severing legitimate operations.
- **Deploy lesson:** a heredoc string-replace anchor (the Table-0 comment) didn't match on Dell#2 so the
  handler was skipped (data-plane timeout worked regardless; only controller state-sync was missing);
  re-applied against a robust `def install_guard` anchor. Prefer unique code-line anchors over comment lines.
Next: P2 THROTTLE via OpenFlow meters (verify OVS/kernel meter support first).

## CC-32 (2026-07-16): A1 P2 — 2-table policy pipeline + THROTTLE (OpenFlow meters)
- **P2a pipeline refactor:** Table 1 = POLICY (block/throttle/deflect @P100), Table 2 = SWITCH (L2 learn,
  moved from table 1). Guard(t0)->policy(t1)->switch(t2). Verified forwarding + ALLOW/BLOCK/REFUSE identical
  (sup .2.30->.2.10 3/3; Cell-2 ttl=29). Clean architectural home for the response repertoire.
- **P2b THROTTLE:** enforce_response THROTTLE -> throttle_conduit installs a Table-1 flow
  `meter:1, goto_table:2` (rate-limit then forward, self-healing via hard_timeout). One shared drop-meter
  per switch (id 1, THROTTLE_RATE=20 pktps, burst 10). Added a `force` override to /cars/respond for
  invoking any response on demand (testing/demos).
- **Verified (controlled meter-stats delta):** 200-packet flood @200pps -> band dropped 149, passed 51
  (74.5% loss); 51/~2s ~= 25 pps == rate+burst. Under-rate 6/6 passes. THROTTLE != BLOCK (0%) != ALLOW (100%):
  a live, rate-capped flow. OVS kernel-datapath meters enforce correctly here (a single anomalous ping run
  earlier was a send-rate artifact, disproven by the counter deltas).
- **Debug lessons:** (1) an over-rate flow at the same priority-100 as a residual block can collide -> restore
  before re-testing; (2) trust meter-stats counters over ping% for meter validation.
Next: P4 escalation (THROTTLE->BLOCK->ISOLATE on persistence via conduit_state.offense). P3 DEFLECT (honeypot) after.

## CC-33 (2026-07-16): A1 P4 — criticality-graded escalation + ISOLATE (graduated response complete)
- **select_response (tier-split, criticality-graded):** CRITICAL->REFUSE (safety, unchanged); OPERATIONAL->ALLOW;
  SENSITIVE (ews->plc)-> THROTTLE then BLOCK on abuse; FORBIDDEN (unknown/gateway->plc)-> BLOCK now, ISOLATE the
  source on persistence. Rationale (design Q#4): a PLC faces single-command attacks, so THROTTLE (still passes
  ~20 pps) does NOT protect it -> unknown->PLC must be blocked outright; THROTTLE is for elevated-but-known
  (permit-with-limit) and volumetric/recon, not for guarding a critical asset. Escalation via conduit_state.offense
  (>= ESCALATE=3 climbs a rung).
- **ISOLATE:** `isolate_source` drops ALL of a source's IP traffic (any dst) at Table-1 priority 110 (above conduit
  rules), with hard_timeout self-heal.
- **Self-heal + forgiveness:** on auto-expiry the FlowRemoved handler clears state AND resets the offending
  conduit/source offense to 0 -> a ceased attack is forgiven; a returning attacker re-escalates from the bottom rung.
- **VERIFIED live (autonomous loop, sustained insider ping .3.66->.3.10):** offense 1->BLOCK, 2->BLOCK,
  3->ISOLATE source .3.66; /cars/status went conduit-block -> source-isolate; on stop, block + ISOLATE AUTO-HEALED
  and offense reset. Decide+enforce stayed 0.3-0.6 ms throughout.
- Minor cosmetic: earlier conduit-block flows (offense 1-2) coexist with the ISOLATE (offense 3) until each
  self-heals; ISOLATE (P110) dominates so enforcement is correct. Optional refinement: drop subsumed conduit
  blocks when escalating to ISOLATE.

**A1 status:** P0 (decouple), P1 (self-heal timeouts), P2 (2-table pipeline + THROTTLE meters), P4 (escalation +
ISOLATE) COMPLETE. Response repertoire live: ALLOW / THROTTLE / BLOCK / ISOLATE / REFUSE, criticality-graded,
escalating, self-healing, safety-capped, sub-ms. Remaining (optional): P3 DEFLECT (honeypot), P5 dashboard
response-type coloring + evaluation table.

## CC-34 (2026-07-16): A1 P5 — dashboard response-type coloring + evaluation artifact
- **Dashboard:** decision feed now renders a colored RESPONSE badge (rALLOW green / rTHROTTLE amber / rBLOCK red /
  rISOLATE magenta / rREFUSE blue) beside the tier, with a response-ladder legend. Verified live: the feed showed
  OPERATIONAL·ALLOW, CRITICAL·REFUSE, FORBIDDEN·THROTTLE, FORBIDDEN·ISOLATE in one view. The graduated response is
  now visible on the console, not just in logs. (cars_dashboard.pre-p5.bak on Dell#1.)
- **Evaluation artifact:** 07_Evaluation/RESPONSE_SPECTRUM.md — write-up-ready table (tier -> response -> escalation
  -> data-plane mechanism -> measured effect -> CARS latency) + cross-cutting properties + honest meter substrate note.

**A1 (graduated response) COMPLETE:** P0 decouple, P1 self-heal, P2 pipeline+THROTTLE, P4 escalation+ISOLATE,
P5 dashboard+eval. Repertoire ALLOW/THROTTLE/BLOCK/ISOLATE/REFUSE — criticality-graded, escalating, self-healing,
safety-capped, sub-ms, visible. Only optional remainder: P3 DEFLECT (honeypot redirect).

## CC-35 (2026-07-16): A1 P3 DEFLECT proven + pipeline-sync bug found + THROTTLE re-validated by *delivery*
Three linked findings from finishing P3, driven by Rule-0 scrutiny of "does the response actually work end-to-end".

- **Root bug — the deployed controller pipeline had silently diverged from the master.** Dell#2's `~/cars/cars_engine.py`
  was *half-migrated*: `features_handler` still built the SWITCH (broadcast FLOOD + controller-miss) in **table 1**, while
  `packet_in`/`throttle_conduit`/`deflect_conduit` had already moved to **table 2** (learn + `goto_table:2`). Net effect:
  **table 2 had no miss/flood handler, so any response that did `goto table 2` had its forwarded packets dropped by the
  implicit table-miss.** DEFLECT's redirect and THROTTLE's meter-passed packets were being **black-holed at table 2**.
  The E: master `features_handler` was already correct (T1 `P0→goto T2`; T2 = flood + controller-miss); only the on-box
  deploy was stale — the classic "patch the file, forget to restart / redeploy" trap.
  - **Diagnosed** by dumping all three tables (T1 held FLOOD+CONTROLLER, T2 held only orphaned learned flows) and
    `ovs-appctl ofproto/trace` (TRACE A: `OFPP_FLOOD` **does** include the internal decoy port — flood was never the
    problem; TRACE B: packet to the decoy hit `T1 P0 → CONTROLLER`, never reaching a switch). **Fixed** on Dell#2:
    `features_handler` now installs T1 `priority=0 → goto table 2` and moves FLOOD + controller-miss to `table_id=2`
    (patch validated with `ast.parse`), then controller restarted. Master + deploy now in sync.
- **DEFLECT (P3) proven — but only with an isolated decoy stack.** Forward flow (`set eth_dst=hpot, set ipv4_dst=.3.99,
  goto T2`) + reverse flow (`ipv4_src .3.99→.3.10, goto T2`), both P105, self-healing. After the pipeline fix the redirect
  reached the decoy, but it **would not reply**. Root cause: the honeypot (`.3.99`) and attacker vantage (`ins2 .3.66`) were
  both interfaces on **Dell#1's single root netns, same /24** — so the kernel saw the attacker's source IP as *local* and
  refused to answer (martian/asymmetric). **Fix (answers "why a VM honeypot?"):** move the decoy into its **own network
  namespace** (`hpotns`) so the attacker looks like a genuine remote host — a namespace gives the required stack isolation
  without a full VM (clean upgrade path to Conpot-in-a-container for fake S7/Modbus later).
  - **VERIFIED live:** attacker pings `.3.10`, gets 4/4 replies at **ttl=64** (the local decoy) — NOT the real PLC's
    **ttl=29** (through NAT); `hpotns` capture shows request **and** echo-reply + an ARP for the attacker; the reverse flow
    rewrites `.3.99→.3.10` so the attacker believes the PLC answered; **real PLC never touched**; decide+enforce **1.2 ms**;
    self-healed after 30 s on all 3 switches. Full interactive deception, not just diversion.
- **THROTTLE re-validated by DELIVERY (corrects CC-32).** CC-32's "51 passed" was measured by **meter-stats deltas**, which
  count what the *meter released*, not what was *delivered* — and under the broken pipeline those survivors were dropped at
  table 2. So the "rate-capped, not cut" claim was **unproven** (arguably a full block). Re-tested post-fix with a clean
  harness (stop `cars-bridge` so the autonomous loop can't BLOCK-override the forced THROTTLE at the same P100; direct
  `del-flows` to beat the 30 s self-heal race; meter confirmed `type=drop rate=20 burst=10 pktps` via `dump-meters`):
  **80 pings @ ~50 pps → meter band +38 dropped, ping 42 received; 38 + 42 = 80.** Genuine graceful rate-cap that *forwards*
  the allowance. THROTTLE now proven by delivery, not just by meter.
- **Test-harness gotchas recorded:** (1) `/cars/restore` does not reliably clear a same-priority (P100) THROTTLE flow, and
  OVS preserves a flow's `duration`/counters on an identical re-ADD (no `RESET_COUNTS`) — so re-forcing looks installed but
  the 30 s self-heal keeps expiring it mid-test; use a direct `del-flows` for a guaranteed-fresh flow. (2) The autonomous
  Snort→bridge loop will BLOCK a test flood and *replace* a forced THROTTLE at equal priority — stop `cars-bridge` for
  controlled response-type tests. (3) For meters, cross-check the **flow n_packets** (matched) + **meter band count**
  (dropped) + **ping received** (delivered); the three must sum.

**A1 (graduated response) FULLY COMPLETE + validated end-to-end:** ALLOW / MONITOR / THROTTLE / DEFLECT / ISOLATE / BLOCK /
REFUSE — criticality-graded, escalating, self-healing, safety-capped, sub-ms, **each response proven by effect+delivery**
(THROTTLE forwards 42/80, DEFLECT deceives at ttl=64, BLOCK/ISOLATE drop, REFUSE no-ops the safety loop). Persistence TODO:
`cars-hpot.service` to recreate the `hpotns` decoy at boot (done same day; see 06_Build/cars-hpot.service).

## CC-36 (2026-07-17): A3 — ICS-protocol DPI (operation-aware criticality), Modbus phase COMPLETE
The A3 novelty: CARS decides on **what operation** is sent (read vs write), not just **who** is talking. A *write*
actuates the process, so response = f(source trust × operation risk). Full design + gate in `A3_DESIGN.md`.
- **Gate (Snort 2.9.20):** Modbus dynamic preprocessor present, but two blockers surfaced: (1) stream5 PAF did not
  flush single-packet requests off the SPAN; (2) **checksum offload** — internal netns↔netns traffic carries
  uncomputed TCP checksums, so Snort silently dropped payload inspection. Fixes: detection via **stateless content
  rules on the Modbus function-code byte** (payload offset 7; proto-id anchor offset 2; SIDs 1000020-24) +
  **`config checksum_mode: none`**. (The ICMP rules had worked only because that traffic crosses a physical NIC.)
- **Endpoints (pymodbus 3.6.9, pinned):** three netns on ovsgw — `mbns/.2.20` (Modbus PLC server, deterministic
  registers), `opns/.2.31` (legit operator, role=supervisory), `atkns/.2.66` (attacker, role=unknown). Namespaces are
  required so traffic traverses the fabric and is mirrored (same martian trap as the A1 decoy).
- **Signal path:** Snort content rules emit `CARS-MODBUS-READ/WRITE-*` → `snort_bridge.py` v3 extracts the operation
  from the alert msg and passes `op` to CARS (cooldown keyed on `(src,dst,op)` so read≠write).
- **Brain:** `classify(src,dst,op)` — a trusted source's WRITE escalates OPERATIONAL→SENSITIVE (reads unchanged);
  unknown = FORBIDDEN regardless; `op` shown in the audit. Offense-count fix: only enforcing responses (not ALLOW/
  MONITOR) drive persistence escalation, so a polling operator's reads don't spuriously escalate its writes.
- **VERIFIED autonomous (Snort-DPI→bridge→CARS):** operator READ×2 → ALLOW (offense 0); operator WRITE →
  SENSITIVE/THROTTLE (offense 1); attacker WRITE → FORBIDDEN/BLOCK, 2nd write fails to connect. Decide+enforce
  0.01-0.9 ms; self-healing. Same src+dst, different response purely by operation — the A3 headline.
- **Honest limits (for the writeup):** (1) the *decision* is operation-aware but *enforcement* is conduit-level —
  OpenFlow matches L3/L4, not Modbus function codes, so a throttle/block covers the whole IP conduit (finer L7
  steering would need an L7 proxy). (2) Reactive: the *first* write lands before the conduit is blocked; preventing
  it needs proactive default-deny on writes (A2). (3) Single-packet content matching — a deliberately fragmented
  Modbus write could evade; A2/A4 mitigate. Detection lives in the sensor, correctly (controller stays L3).
- Files: `06_Build/{mb_server.py, mb_client.py, cars-modbus-setup.sh, snort_bridge.py}`; `cars_engine.py`
  REGISTRY+classify+respond edits (master + Dell#2, functionally in sync — comment/whitespace drift noted).
Next: **P5** — S7comm detection on the real S7-1200, dashboard operation column, A3 forensic sweep.

## CC-37 (2026-07-17): A3-P5 — dashboard op column + Modbus forensic sweep + S7CommPlus session detection. A3 COMPLETE.
- **(b) Dashboard op column:** feed renders a colored operation chip (amber WRITE / cyan READ / purple S7) beside tier
  and response. Verified live.
- **(c) A3 forensic sweep** (`06_Build/cars_a3_forensics.sh`): per-scenario cross-validation wire-func-code (tshark) ->
  Snort alert -> CARS decision -> OpenFlow action, Wireshark-openable bundle. Report table: OP_READ (FC3 / READ-holding /
  pass-no-flow), OP_WRITE (FC6 / WRITE-reg / meter+goto), ATK_WRITE (FC6 / WRITE-reg / drop). Same FC6 + same alert,
  different data-plane by source; same source, different action by operation — both axes proven.
- **(a) S7comm on the real S7-1200 — protocol-session detection (honest scope).** Wire evidence: the PLC speaks
  **S7CommPlus** (hex: TPKT `03 00` + COTP `02 f0 80` + proto-id **`72`** at payload offset 7; payload obfuscated/high-
  entropy). So clean read/write function-code DPI is **not** possible (unlike open Modbus) — a real, documented limit.
  What IS done: content rule (sid 1000040) on TPKT+`72` to `.2.10:102` detects an S7 session; and the mirror vantage
  scopes it perfectly — the legit HMI<->PLC loop is intra-`ovs1` (unmirrored), so the rule fires ONLY on S7 sessions that
  cross `ovsgw` from the fabric = an unauthorized source reaching the real PLC. Bridge tags `op=S7`; CARS classify
  (unknown->plc = FORBIDDEN) responds with no engine change.
  - **VERIFIED live (safe):** attacker `.2.66` S7 probe -> Snort detect -> CARS FORBIDDEN -> BLOCK, escalating to ISOLATE
    on repeat; 2nd probe fails to connect (conduit dropped); sub-ms. **Safety:** the probe is one connect + a single
    invalid COTP DT (no CR/CC handshake) that the PLC transport discards — no session, no read, no write; the running
    process is never touched. `06_Build/s7_probe.py`.
- **Honest A3 boundary (for the writeup):** operation-aware function-code DPI (read vs write) is proven on **Modbus**
  (open protocol); **S7CommPlus** permits only protocol/session-level detection on the real hardware, not read/write
  granularity. Detection lives in the sensor; enforcement stays conduit-level (OpenFlow = L3/L4).

**A3 (ICS-protocol DPI) COMPLETE:** CARS now decides on *what operation / protocol* is sent, not just *who* — Modbus
read/write operation-aware grading + S7CommPlus unauthorized-session detection on real hardware, all autonomous, sub-ms,
self-healing, visible on the dashboard, honestly bounded. Files: `06_Build/{mb_server.py, mb_client.py,
cars-modbus-setup.sh, snort_bridge.py, s7_probe.py, cars_a3_forensics.sh}`, `A3_DESIGN.md`. Remaining roadmap: A2
(proactive allowlist / default-deny writes — complements A3's reactive limit) and A4 (declarative rulebook).

## CC-38 (2026-07-17): A3 adversarial deep validation — PASS, with two honest findings
Ran `06_Build/cars_a3_validate.sh` (bundle `cars_a3_validation_*.tar.gz`): for every scenario cross-checked FOUR
independent layers that must corroborate — WIRE (tshark func code) | SNORT alert | CARS decision (audit) | DATA-PLANE
(OVS kernel flow `n_packets` + outcome). A claim only passes if all four agree; the flow counters are OVS's own kernel
numbers (not controller claims), so this is the anti-hallucination anchor.
- **Core matrix (all reconcile):** OP_READ wire=3/READ/OPERATIONAL-ALLOW/no-flow; OP_WRITE wire=6, OP_WMULTI wire=16,
  OP_WCOIL wire=5 -> all WRITE/SENSITIVE-THROTTLE/`meter:1,goto_table:2` (n_packets 5-6); ATK_WRITE wire=6 and
  **ATK_READ wire=3** -> both FORBIDDEN/BLOCK/`drop` (n_packets=5). Every function code classified correctly; an unknown
  source is FORBIDDEN regardless of op (op-awareness never downgrades an attacker).
- **Confuse-the-brain:** non-Modbus HTTP to :502 -> 0 false alerts; real HMI<->PLC loop -> 0 alerts (intra-ovs1,
  correctly invisible); fragmented Modbus write -> 0 WRITE alerts (single-packet DPI evasion, honestly shown).
- **Latency:** decide+enforce avg 0.492 ms over n=23 under the loop.
- **Finding 1 (known):** fragmented write evades single-packet content DPI -> stream reassembly / A2 default-deny mitigate.
- **Finding 2 (new, subtle-correct):** escalation to ISOLATE did NOT fire on a freshly-cleaned attacker (BLOCK x5, no
  ISOLATE). Correct because an effective BLOCK stops the attacker's traffic, so no new alerts -> offense counter doesn't
  climb; and offense is per-(src,dst) conduit, so a broad scanner hitting many targets once each never trips source-wide
  ISOLATE. Earlier ISOLATE runs fired only because offense had accumulated. **Refinement (A2/A4):** escalate on drop-flow
  hit counts, or track offense per-source, so a persistent/scanning attacker is quarantined even while blocked.

**A3 verdict:** operation-aware ICS DPI is real end-to-end at the packet/datapath level (four-layer corroboration),
adversarially sound (no downgrade, no false positives), sub-ms, with limits documented (frag evasion, conduit-level
enforcement, S7CommPlus opacity, escalation-needs-persistence). Cleared for the dissertation.

## CC-39 (2026-07-18): CC-38 Finding 2 RESOLVED — per-source offense escalation
Implemented + validated the per-source refinement flagged in CC-38. `select_response` now escalates FORBIDDEN
BLOCK->ISOLATE on a **per-SOURCE** offense counter (`self.source_state`), while SENSITIVE THROTTLE->BLOCK stays
per-conduit. Offense increments on enforcing responses only (benign permits don't count); the source counter resets on
ISOLATE auto-heal (forgiveness). Edits in `cars_engine.py` (master + Dell#2, ast-validated).
- **Why:** a broad scanner hitting many targets once each never trips a single conduit's ESCALATE=3, so the old
  per-conduit logic left it at BLOCK forever. Per-source catches the source's *aggregate* malice.
- **VALIDATED (clean run):** attacker `.2.66` hit THREE distinct conduits once each — `.2.20` (Modbus write), `.2.10`
  (ICMP), `.2.9` (ICMP) — each -> BLOCK with **conduit offense=1** (blocks even auto-healed between hits); the 4th hit
  (re-hit `.2.20`, conduit count still 1) -> **ISOLATE** source-wide. ISOLATE fired while the conduit's own count was 1,
  which per-conduit logic can never do -> definitive proof the escalation is source-driven. Sub-ms throughout.
- **Operational note found + fixed en route:** the controller had appeared "broken" (API hang, dashboard flapping) —
  root cause was the `osken-manager` process **suspended (state T)** after a Ctrl-Z to run commands in its terminal;
  not a code fault. Run the controller in tmux/dedicated terminal so it is never suspended.
- **Minor artifact noted:** a single `s7_probe` generates multiple Snort alerts via TCP retransmits (PLC discards the
  invalid COTP, never ACKs) -> inflates offense faster; benign (more attacker traffic = faster escalation), but use
  single-shot ICMP for clean per-conduit-vs-source demonstrations.

## CC-40 (2026-07-18): A2-P1 — proactive default-deny + declarative allowlist (Modbus cell). Prevention, not reaction.
A2 flips A3's reactive posture: pre-install the policy so unauthorized traffic never reaches a PLC. Design in
`A2_DESIGN.md`. Scope: Modbus cell (`.2.20`) first (safe — an incomplete allowlist can't sever the real process).
- **Mechanism (L3/L4, proactive at switch connect):** `install_allowlist()` installs, in Table 1: allowlisted conduits
  `P60 (ip,src,dst,tcp_dst)->goto switch`; default-deny `P55 (ip,dst=PLC)->drop`. Declarative
  `ALLOWLIST=[(.2.31,.2.20,6,502)]`, `DEFAULT_DENY_DSTS=[.2.20]`. Priority order keeps reactive on top:
  P110 ISOLATE > P105 DEFLECT > P100 BLOCK/THROTTLE (A1/A3) > P60 allow > P55 deny > P0 pass.
- **VALIDATED:** operator `.2.31` READ + WRITE -> `OK` (allowlisted, lands); operator WRITE then -> SENSITIVE/THROTTLE
  (A3 reactive P100 overrides the P60 allow -> layers compose). Attacker `.2.66` WRITE -> **TCP connect FAILED**: its
  SYN is dropped by P55 before any Modbus PDU exists, so it **never lands and generates NO BRAIN line** — the exact
  first-packet prevention A3 could not give (A3's first write landed then was blocked). A2 is also immune to the L7
  fragmentation evasion (no detection needed).
- **Honest characteristics:** (1) A2 pre-drop is **silent** — no CARS audit of the blocked attempt (the SYN is on the
  mirror but carries no Modbus payload to alert on); prevention trades away the audit trail. "Deny+log" is a future
  refinement; A3 still audits a bad *operation* from an *allowed* source. (2) A2 cannot pre-deny by function code (L7);
  an allowed source's bad write stays A3's job. **Defense-in-depth:** A2 pre-drops the protected conduit -> attacker
  pivots to non-A2 targets (`.2.10/.2.9`) -> A3 detects reactively -> per-source offense (CC-39) -> ISOLATE.
- Files: `A2_DESIGN.md`, `cars_engine.py` ALLOWLIST/DEFAULT_DENY_DSTS + `install_allowlist` (master + Dell#2).
- **Next A2-P2 (high care):** add the real Cell-1 allowlist (HMI<->PLC S7 loop, supervisory reads) and default-deny
  `.2.10` ONLY after proving the allowlist complete on the mirror (no process disruption). Then A2-P3 validate + A4.

## CC-41 (2026-07-18): A2-P2 — proactive default-deny extended to the REAL PLC (.2.10), loop-safe. PASS.
Extended A2 from the simulated Modbus PLC to the live S7-1200 (`.2.10`) via the evidence-first, reversible procedure.
- **Observe (A2-P2a):** captured all traffic to `.2.10` on the ovs1 box NICs — the ONLY source is `192.168.2.9 -> tcp/102`
  (HMI S7CommPlus loop), ~2-3 pkt/s; the "not .2.9" capture found nothing. Complete allowlist = one conduit.
- **Reversible live test (A2-P2b):** installed the allow (`.2.9->.2.10:102`, P60) FIRST, then the `.2.10` default-deny
  (P55) with a 60 s `hard_timeout` rollback. Loop-survival proven by counters: allow `n_packets 74->192` climbing
  (loop flowing through the allowlist), deny `n_packets=0` (loop never hit it). Process undisturbed.
- **Made permanent + re-validated (bridge stopped, A2 in isolation):** allow `n_packets 177->215->243` continuous
  (live loop intact permanently); attacker `.2.66->.2.10` s7_probe -> `connect FAILED`, `ovsgw` deny `n_packets 0->2`,
  and **NO BRAIN line** -> the real PLC is now protected by pure proactive default-deny, no detection needed.
- **Config:** `ALLOWLIST += (.2.9,.2.10,6,102)`; `DEFAULT_DENY_DSTS += .2.10` (master + Dell#2). Same allowlist entry
  also covers Cell-2's raw HMI2->PLC2 loop (identical IPs) on ovs2. Engine installs these at every switch connect
  (`install_allowlist`), so they persist across reboot with the controller.
- **Safety method (reusable):** observe -> allow-first -> deny-with-rollback -> verify-loop -> make-permanent. The one
  place we move slowly; a mistaken deny self-heals in <=60 s or on Ctrl-C (delete-all).

**A2 (proactive default-deny) COMPLETE for Cell-1 + Modbus cell.** Defense-in-depth now proven on real hardware: A2
pre-drops unauthorized sources at the PLC; A3 grades bad operations from allowed sources; A1 responds gradually;
per-source offense (CC-39) quarantines scanners. Remaining: A2-P3 forensic sweep (optional) and A4 declarative rulebook.

## CC-42 (2026-07-18): A4 — declarative, hot-reloadable rulebook. The decision policy is now configuration, not code.
Unified the scattered decision logic (role->tier + A3 write-escalation) into ONE ordered, first-match-wins table.
- **A4-P1 (refactor, behaviour-preserving):** `RULEBOOK = [(src, dst, op, tier), ...]`; `classify()` walks it top-down,
  first match wins (src/dst match by role OR exact IP OR "any"; op = "READ"/"WRITE"/"S7"/... or "any"). **Regression:
  400 role x role x op combinations, 0 mismatches vs the old hardcoded classify()** — pure refactor. Live-confirmed on
  the testbed (CRITICAL/OPERATIONAL/SENSITIVE/FORBIDDEN all identical).
- **A4-P2 (config-driven, hot-reload):** policy externalised to `~/cars/rulebook.json` (`load_rulebook()` seeds it from
  defaults on first run, loads it at startup, updates `RULEBOOK` in place). Endpoints: `GET /cars/rules` (inspect),
  `POST /cars/reload` (re-read the file live). **Demonstrated:** edit the JSON to permit `.2.66->.2.20`, `/cars/reload`
  -> decision flips FORBIDDEN->OPERATIONAL **with no code edit and no restart**; revert + reload -> back to FORBIDDEN.
  Controller logged both reloads (20 rules / 19 rules).
- **Scope (honest):** A4 makes the reactive DECISION policy config-driven. The A2 proactive allowlist is its own
  declarative table (`ALLOWLIST`/`DEFAULT_DENY_DSTS`), still applied at switch-connect (a change needs a restart to
  reinstall flows) — hot-reloading A2's data-plane flows is a possible future enhancement. `select_response`,
  per-source escalation, and enforcement are unchanged; A4 only replaces the tier decision.
- Files: `cars_engine.py` (RULEBOOK + `load_rulebook` + `/cars/rules` + `/cars/reload`), `~/cars/rulebook.json` (seeded),
  `A4_DESIGN.md`. Master + Dell#2 in sync.

**ROADMAP A1-A4 COMPLETE on real hardware.** A1 graduated response · A2 proactive default-deny (real PLC, loop-safe) ·
A3 ICS-protocol DPI (Modbus operation-aware + S7CommPlus session detection) · A4 declarative hot-reloadable rulebook;
plus per-source escalation (CC-38/39). Every layer proven at the packet/datapath level, adversarially validated, and
honestly bounded. Next natural work is write-up + evaluation consolidation from the CC log.

## CC-69 (2026-07-23): D3+D4-A — sensor false-data injection (Cárdenas signature attack) + "block-that-maintains", REAL hardware.
The process reads `Sim.Level` (DB7, non-optimized). Sensor spoof = external S7 `db_write` pinning `Level=20` (< LowL 30) →
pump should never stop. Tool: `s7_write.py --dbspoof --db 7 --offset 0 --spoofval 20`. Attacker = insider Kali `.2.77`.
- **DISARMED (baseline):** 181 spoof writes landed → `Level` pinned ~20, **pump stuck ON / relay lit = tank overflow**
  (operator read shows the false low level). = the paper's LIT101→overflow result, reproduced on real Siemens hardware.
- **ARMED (protected):** the `db_write` is S7 write-var `0x05` → CARS classifies `CONTROL` → `BLOCK → ISOLATE source .2.77`;
  spoof got **1 write (CC-54 first-packet) then S7TimeoutError** (conduit severed). **Level climbed back into the 30↔70
  oscillation, pump intervals normal = process MAINTAINED.** Confirmed by the live Level/pump monitor + audit + dashboard CSV.
- **NOVELTY framing (P1 Rung A = block-that-maintains):** CARS *maintains process correctness by cutting the malicious
  SOURCE at the network* — because it can identity-block the attacker, blocking suffices to keep the loop correct; the
  Cárdenas group must *estimate/substitute* because they redirect rather than block a compromised sensor. Disarmed=overflow
  vs armed=maintained is a clean CAUSAL claim that CARS's response preserves the physical process. Rung B (active last-good
  substitution via `cars_remediation.py`) = the explicit process-level state-maintenance, for the harder compromised-sensor
  case = optional next.
- Dashboard note: a `.2.77` attack on PLC1 shows containment on BOTH PLCs — correct: `ISOLATE source` is plant-wide
  quarantine (a caught insider is cut from every asset, not just the one it touched).

## HARD RULE (standing, from Amit 2026-07-27): WHOLE-TOPOLOGY / EVERY-DEVICE application — industry relevance, not a thesis demo.
Every differentiator/capability/novelty must be implemented and applied **as a whole, across every device, the entire topology and perimeter** — for maximum *practical* industry relevance and accuracy, NOT a single-cell/single-device proof-of-concept. Binding retroactively (close existing gaps) and on all future work.
- **Coverage audit (2026-07-27):** WHOLE = stateful policy (all switches), asset criticality (both cells/all assets), op-aware DPI (both cells' PLCs+Modbus), reactive response (network-wide), control-API auth. **GAPS (violations):** (1) **remediation is PLC1/Tank1-ONLY** → extend to every PLC (task #25); (2) **GUARD anti-spoof partial** — Modbus + trusted source seams (.2.31/.2.45/.2.55/.3.66) unbound (task #26); (3) Modbus telemetry deferred (task #14). Honest boundaries (NOT gaps): HMI DPI = S7CommPlus session-only (G3), single-controller Cell-2-internal not mirrored (G6).
- **Rule for next phases:** Phase 2 QoS must protect BOTH loops (PLC1↔HMI1 AND PLC2↔HMI2) on every switch; Phase 3 micro-seg every conduit; Phase 4 analytics is global by nature; Phase 5 P4 concept must generalize. No Cell-1-only demos accepted as "done".

## CC-101 (2026-08-01): SCOPE DECISION (Amit) — remediation "maintain" = clean-scope-and-document (NOT tested on live Factory IO).
Decision: the remediation agent's last-good-restore is presented as validated on the in-PLC SIMULATION only; on the live HIL process,
"maintain" is provided by the physical control loop's self-recovery after CARS isolates the attacker. Remediation is NOT run live and
NOT tested on the Factory IO loop — deliberate, defensible scope (chosen over adapting it to be process-band-aware).
- **Why (technical, honest):** on the sim, `DB7.Level` is a standalone authoritative variable an attacker tampers → last-good-restore
  applies cleanly (wire-validated CC-88, CC-96 V4: attacker DB7←5.0 detected `<floor`, `restores 1→2` captured). On the LIVE loop,
  `DB7.Level := LevelIn*20` is recomputed from the real sensor every scan and legitimately oscillates 30↔70 → the restore agent would
  misread natural dynamics as tamper and fight the process; and for the sensor-spoof (FDI) it reads the SAME spoofed sensor, so it's
  blinded exactly as the PLC is. The last-good-restore model does not map onto a closed-loop, sensor-driven process.
- **What we DID show live:** block-and-maintain via loop recovery — CARS isolates the attacker (block, proven), and the closed-loop
  control returns the tank to its safe band (maintain): Phase 6 armed (`.2.31` cut on 1st write, tank stays in band) + the disarmed→
  re-arm recoveries (overflowed tank drained back to ~58). Real ICS processes have their own regulatory control — this is the realistic picture.
- **Dissertation framing (ready to use):** "Remediation's last-good-restore is demonstrated and wire-validated on the in-PLC simulation,
  where the tampered variable is authoritative. On the live hardware-in-the-loop process the 'maintain' property is provided by the
  physical control loop's self-recovery once CARS severs the attacker; adapting the restore agent to a live sensor-driven process
  (distinguishing legitimate dynamics and spoofed sensors from tamper) is identified future work." → turns the boundary into a defended
  scope, novelty intact. Bring-up note stands: keep `cars-remediation` STOPPED for the live Factory IO loop.

## CC-100 (2026-08-01): GRAND VALIDATION CAMPAIGN — 7 phases, wire-level, armed vs unprotected, every capability. Report `GRAND_VALIDATION_REPORT.md`.
The comprehensive campaign requested by Amit ("every scenario, every attack, every angle, the massacre and the safety side").
Phased (validated each before next), Cell-1 + Factory IO focus, real Kali `.2.77` outsider. 3-state method (CARS OFF/flat-net vs
DISARMED vs ARMED) — key insight: the proactive default-deny is NOT gated by the arm switch, so an outsider stays blocked even
disarmed; the true "massacre" baseline needs a per-path bypass (`cookie 0xb1`, reversible) simulating a flat/ungoverned segment.
Capture rig: `06_Build/cars_campaign_lib.sh` (snap/flowdump/capstart 3-point pcaps/arm helpers); bundle in Dell#1
`/tmp/grand_campaign/phase{1..7}/`. **Results:**
- **P1 Recon:** protecting = service scan all `filtered`, no S7 identity leak, scanner ISOLATE 75s/60s (criticality-scaled), self-heal;
  flat-net = 80/102/443+502 open, PLC fingerprinted (`6ES7 212-1BE40-0XB0`, FW 4.2.3). L2 ARP discovery not gated (boundary).
- **P2 Spoofing:** 23/23 IP+ARP impersonations of `.2.31`/`.2.45` dropped at GUARD ingress + logged (running totals), real seams
  unaffected, hping3 100% loss; bypassed = spoofed SYN reached PLC (Kali MAC). Bonus: partial bypass caught by stateful default-deny.
- **P3 State:** stateful = ACK/SYN floods 0 reached, embryonic ct expired, only 10 INERT RSTs leaked in the ~1s reactive-install
  window (0 PLC response), source isolated; stateless allow = out-of-state ACKs reach + PLC RSTs back (rtt 3–10ms).
- **P4 Control-plane:** unauth disarm → 401 (stays ARMED); flow-integrity checker caught inject×2 (incl reactive-band evasion) +
  delete (black-hole) + rewrite (action-mod) → `ok:0 missing1 extra2 changed1`, surfaced to log, self-cleared on restore.
- **P5 Op-aware:** same `.2.31` session — READ(func04)=ALLOW vs WRITE(func05)=ISOLATE; same WRITE from `.2.55`=ALLOW (role+op+crit,
  packet-level, S7 function read off the wire).
- **P6 Process (centrepiece):** DISARMED FDI = 2513 writes, tank DB7=194.75 (~195%, OVERFLOW/spill) while PLC/HMI read empty;
  ARMED = 1 write (Receive timeout), `.2.31` isolated, tank in-band/truthful — block-AND-maintain on the live process.
- **P7 Response ladder:** all 7 fired — ALLOW/MONITOR/THROTTLE(meter@20pps30s LOW)/DEFLECT(→honeypot .3.99)/ISOLATE(75s CRIT)/
  BLOCK(30s LOW)/REFUSE(CRITICAL safety-invariant); criticality scales response duration.
- **Cross-cutting:** 0 false positives across all phases (legit loop ALLOW throughout); criticality on decision AND response;
  layered defence (a gap in one layer caught by the next); self-healing; honest reaction-window boundary (~1s, inert leaks only).
  Deliverable `GRAND_VALIDATION_REPORT.md`. Evidence bundle to be archived off Dell#1 before reboot.

## CC-99b (2026-08-01): FALSE-DATA-INJECTION (sensor-spoof) deception demo + decision-log analysis. Appendix in `EVALUATION_REPORT.md`.
Optional overflow visual, closed with evidence. Compromised SCADA `.2.31` writes `LevelIn(%ID100)=0` (+ jams `Discharge(%QD104)=0`)
at ~50 ops/s → PLC's bang-bang believes the tank empty, holds fill open, never trips the high-level interlock. DISARMED (for the
visual): reads held `LevelIn=0.00/DB7=0.00` while the real tank crested and **spilled over the side** (leaked true-sensor reads
`LevelIn=9.44/8.93` ≈ 180% of the 5.0 "full"); **PLC + operator HMI both showed EMPTY** — the deception. Decision-log analysis
(`cars_deception_decisionlog.csv`, 3000 decisions 13:38–14:26): arm-state windows map 1:1 to eval + 3 spoof runs; **70 `.2.31`
detections**, each `S7 CONTROL · FORBIDDEN · [CRIT:CRITICAL] · [FLOOD ~50 ops/s] · would ISOLATE` — **double-caught** (process-image
write = CONTROL→FORBIDDEN on CRITICAL, AND rate tripped FLOOD). Every one `DEFENSE DISARMED — would ISOLATE (monitor only)`: CARS
decided to cut `.2.31` on the first write of every burst; only our disarming let it land (armed run proved 0 writes). **Zero FP during
the attack** — concurrent Factory IO loop + historian polls stayed ALLOW. CSV `mode` column mislabels some rows ENFORCED; the action
string (`DEFENSE DISARMED`) is ground truth. Conclusion: detection 100% (70/70), enforcement is the switch — armed the spoof never lands.

## CC-99 (2026-08-01): ACCURACY / FALSE-POSITIVE EVALUATION — 100% accuracy, 0% FP across the topology. Report `EVALUATION_REPORT.md`.
The Monday deliverable. Harness `06_Build/cars_eval.py` drives the deployed engine's exact decision path via `/cars/respond`
(classify → criticality elevation → select_response) over a 27-case labelled matrix spanning roles × op-classes × criticality
tiers, disarmed (decision-only, no enforcement side-effects), then re-arms. Grounded in the deployed REGISTRY+RULEBOOK (read from
master==deployed `cars_engine.py`); expected column derived from that logic, measured column = live engine verdict.
- **RESULT: TP=13, TN=11, FP=0, FN=0 (grey=3 graded, shown). Accuracy=100.0%, FP-rate=0.0%, FN-rate=0.0%.** Matches the
  policy-derived prediction exactly.
- **0 FP on legit traffic** incl. the live Factory IO HIL loop under enforcement (`.2.55 CONTROL/READ→ALLOW`), HMI↔PLC loop
  (CRITICAL→REFUSE), remediation restore, historian telemetry, SCADA reads. **0 FN**: every dangerous op (CONTROL/PROGRAM/DIAG/
  ILLEGAL) FORBIDDEN regardless of source (incl. trusted `.2.55`/`.2.31`/`.2.30`), unregistered outsiders (`.2.77`/`.2.66`)
  isolated on any contact, gateway `.2.1` with no conduit blocked from the CRITICAL PLC.
- **Criticality grading proven on ONE policy (grey rows):** SCADA WRITE→CRITICAL PLC1 = elevated SENSITIVE→FORBIDDEN→ISOLATE, but
  same op→LOW Modbus = SENSITIVE→THROTTLE; historian WRITE→HIGH HMI1 = SENSITIVE→THROTTLE. **FLOOD_EXEMPT scoping proven:** EWS
  CONTROL@50→ALLOW (no FP on legit HIL) while historian READ@50→BLOCK (volumetric DoS cut) — identical rate, opposite response.
- **Packet-level corroboration:** the enforcing rows are backed by the live campaign (CC-96/98e) — `31→10 CONTROL→ISOLATE`
  (0 writes landed live), `77→10 TCP→ISOLATE` (6/6 connects blocked live), `55→10` legit rows (Factory IO loop clean, 0 isolates).
  So the matrix is not simulation-only.
- **Perf:** decide+enforce ~0.025 ms mean over 1000+ decisions (`/cars/status`). **Boundaries (honest, in report):** hmi↔plc
  safety-invariant loop is never enforced (dangerous op *from the HMI identity* not rulebook-blocked — intentional, GUARD-anti-spoof
  mitigated); G1 compromised-endpoint; full controller-compromise; flow-audit poll window. Artifacts: `EVALUATION_REPORT.md`,
  `cars_eval_matrix.csv`, `cars_decisions_1785588865862.csv`, `06_Build/cars_eval.py`.

## CC-98 (2026-07-31): FACTORY IO live HIL process integrated with ARMED CARS (Approach A). Task: Factory IO demo (#step4).
Factory IO (Level Control scene) on the Win Dell (EWS `.2.55`) now drives PLC1's real loop, running clean under ARMED CARS.
- **Loop:** Factory IO S7 driver (ComDrvS7) ↔ PLC1. Mapping: level `%ID100`(REAL, 0–5 sensor), fill valve `%QD100`, discharge
  `%QD104`. PLC OB30 rewritten: `"Sim".Level := "LevelIn" * 20.0` (0–5 → 0–100), bang-bang 30/70 on `DB7.Level`, discharge
  constant → oscillates 30↔70. PUT/GET enabled, DB7 non-optimized. `DB7.Level` stays the CARS-monitored variable. (Note: 3
  display scales — scene 0–255, DB7/HMI 0–100, sensor 0–5 — all proportional.)
- **CARS-vs-legit-write tension solved (Approach A):** Factory IO continuously WRITES the input image (classified `CONTROL`)
  at ~32 ops/s → armed CARS was isolating `.2.55` (control-to-CRITICAL + FLOOD). Fixes: (1) rulebook — `ews→plc READ/WRITE/
  CONTROL = OPERATIONAL` inserted BEFORE the dangerous-ops block (PROGRAM/DIAG/ILLEGAL stay FORBIDDEN, so engineering
  downloads still need authorisation); (2) `FLOOD_EXEMPT={.2.55}` (legit HIL polling isn't a DoS); (3) GUARD anti-spoof binding
  `(3,12,b4:e9:b8:a4:ce:46,.2.55)` so the trust can't be impersonated. **Proven:** `.2.55→.2.10 CONTROL/READ ⇒ ALLOW`
  (no FLOOD, no isolate), legit binding n_packets=7109, spoofed `.2.55` from atkns dropped (4). Re-baselined flow-audit to
  accept the new policy.
- **Nice validations along the way:** an ICMP ping from `.2.55` to the CRITICAL PLC → ISOLATE (unauthorised op caught); the TIA
  download (STOP/PROGRAM) needed disarm/authorisation (unauthorised program-change protection); the flow-audit daemon caught
  the intentional `.2.55` binding as drift (checker works).
- **Remediation:** stopped for Factory IO — it was built for the in-PLC sim (DB7.Level authoritative) and fights a live sensor
  (misreads normal movement as tamper). For the live process the CONTROL LOOP provides "maintain" (real feedback self-recovers
  after the attacker is cut); the last-good-restore novelty stays demonstrated on the sim (wire-validated CC-88/96).
- **CC-98b (reconnect fix):** Factory IO's TCP/COTP connection setup classifies as op `TCP` (not READ/CONTROL), which fell to
  the old `("ews","plc","any","SENSITIVE")` → elevated → ISOLATE on armed *reconnect*. Fixed: `ews→plc any = OPERATIONAL`
  (dangerous ops PROGRAM/DIAG/ILLEGAL still FORBIDDEN via earlier rules). Reloaded via `/cars/reload` (no restart), isolate
  cleared → Factory IO connects/cycles cleanly armed. Simulation verified: TCP/READ/WRITE/CONTROL=OPERATIONAL, PROGRAM/DIAG/ILLEGAL=FORBIDDEN.
- **NEXT:** attack demo on the live 3D tank — a compromised untrusted source (e.g. scada `.2.31`) forces the fill valve (`%Q`)
  → tank overflows → CARS op-aware DPI isolates it → control loop recovers; armed vs disarmed. Bring-up note: pin
  `enx00e04c680018` (port 12) ofport for the `.2.55` binding durability; re-baseline flow-audit after any policy change.
- **CC-98d (operator control — live scene Start/Stop/Reset working):** the Factory IO scene push-buttons now drive the process
  end-to-end (Start latches `Running %M0.0` → fill valve opens → tank fills; Stop halts; Reset flickers its lamp). Two non-obvious
  faults found and fixed, both proven by live `%IB` reads (no inference):
  (1) **Onboard `%I` clobber:** buttons were mapped to `%I0.0–0.3`, but those are the S7‑1212C's **onboard physical input
  terminals** — the CPU refreshes the input process image from the (unwired) terminals every scan, wiping Factory IO's PUT/GET
  writes to 0, so buttons never registered while `%ID100` (offset 100, no hardware) worked fine. Fix: remap Factory IO **Bool
  Inputs offset 0 → 10** (buttons now `%I10.0/10.1/10.2`, past the onboard bytes 0–1, so writes persist); PLC tags repointed to
  `%I10.x`. Proof: `%IB10` went from all-0 to reflecting live button presses.
  (2) **Normally-closed Stop:** the scene Stop button is **NC** (`%I10.2` rests at 1, → 0 when pressed). OB30's
  `IF "StopBtn" ... THEN "Running":=FALSE` therefore forced `Running` off every scan. Fix: `"StopBtn"` → `NOT "StopBtn"` (stop only
  on actual press; also fail-safe — if Factory IO disconnects the input reverts to 0 → process safely stops). Live proof:
  Start → `Run=1`, `Lvl` climbs; Stop pressed (`Stop=0`) → `Run=0`, tank holds. Diagnostic `/tmp/rd2.py` on Dell#1 extended to read
  `%IB10`. **HMI panel buttons remain deferred** (panel Transfer/Settings locked in Start Center); `HMI_Start/HMI_Stop`
  (`%M0.1/0.2`) are already wired in OB30, so they activate once the HMI project downloads. Recovery rule after any PLC download
  stands: **Start CPU → Factory IO Stop/Play → press scene Start.**
- **CC-98e (LIVE-PROCESS attack campaign — two vectors, armed vs disarmed, all measured):** ran the op-aware ICS attack against the
  live Factory IO HIL tank under ARMED CARS, reader = `remns/.2.45` (allowlisted, survives isolation of either attacker).
  **Vector 1 — compromised insider `.2.31` (scada, from `opns`)** forces the fill valve (`write %QD100=100 / %QD104=0`, PA area):
  ARMED ⇒ **0 writes landed** (first write `Receive timeout`), `.2.31` ISOLATED in <1s (`S7 CONTROL FORBIDDEN → ISOLATE 75s
  [CRIT:CRITICAL]`, ENFORCED), isolate `0xca`=1 on ovs1+ovsgw, tank steady (DB7 60→67, normal band). DISARMED (control) ⇒ **207
  writes landed @26/s**, attacker **seizes the actuators** (Fill→100, Disch→0), CARS still **DETECTS + decides ISOLATE but mode=
  MONITOR** (not acted) — *detection identical in both modes, arming is the only difference* (reproduces CC-96 on the live loop).
  Honest nuance: the level did **not** overflow — the PLC's own bang-bang **high-level interlock** re-closes fill at >70 every scan
  (defense-in-depth), so the measurable contrast is **control authority** (0 vs 207 writes; actuators untouched vs seized), not the
  level number (tank oscillates 30–70 regardless). A full visible overflow needs a **sensor-spoof** variant (`write %ID100=0` to
  blind the interlock) — deferred, best shown as a Factory IO screenshot since numeric reads would then show the spoofed value.
  **Vector 2 — external outsider Kali `.2.77` (VM on `vmnet2` → ovsgw ofport 12, unregistered)** attempts S7/TCP to PLC1: ARMED ⇒
  isolated at the **TCP connect layer** (`unknown → plc TCP → ISOLATE 75s [CRIT:CRITICAL]`, default-deny — *no* benign-TCP grace the
  insider got), isolate `0xca`=1 on both bridges, **Kali side: snap7 connect timed out + 6/6 raw TCP:102 connects BLOCKED, 0 landed**,
  tank untouched (DB7=38.8). `guard{.2.77}={}` is correct — unregistered ≠ GUARD-protected IP, so it's POLICY default-deny + reactive
  isolate, not anti-spoof. Repeated `.2.77` audit lines = the DPI re-observing the attacker's retry loop (each connect blocked on the
  wire per Kali timeouts), controller re-affirming quarantine — enforcement holds, not a leak. **Evidence:** live controller audit +
  3 decision CSVs (`cars_decisions_1785533492405/875168/534167717.csv`, ENFORCED vs MONITOR rows) + isolate-flow dumps + `remns`
  tank reads + Kali attacker stdout. Two threat classes (op-aware insider, unregistered outsider) both enforced topology-wide on the
  live physical process. **NEXT:** the Monday validation pass (accuracy / false-positive quantification across all scenarios).

## CC-97 (2026-07-31): flow-integrity checker — exclude os-ken infra flows (bring-up false-positive fix).
On the 2026-07-31 bring-up the `cars-flowaudit` daemon flooded the dashboard/controller every ~10s with a single MISSING:
`ovsgw t0 p65535 dl_dst=01:80:c2:00:00:0e dl_type=0x88cc => CONTROLLER` — that's **os-ken's own LLDP topology-discovery flow**
(`--observe-links`), not a CARS rule; it was in the prior baseline but not re-installed identically this boot. Root: the checker
baselined ALL table-0/1 rules incl. the SDN framework's internals. Fix: `is_infra(s)` excludes LLDP (`0x88cc`) + any
CONTROLLER-punt from collect() — the checker now watches ONLY CARS security policy (GUARD + A2). Re-baselined (70 flows) →
CLEAN → daemon restarted → flood stopped. Scoping note: a hypothetical attacker rule that punts to the controller is outside
this checker's remit (a different threat class from flow-policy tampering). Deployed Dell#1 + master in sync.

## CC-96 (2026-07-30): WIRE/PACKET-LEVEL attack campaign + cross-device evidence — full report `WIRE_VALIDATION_REPORT.md`.
Harness `06_Build/cars_wire_campaign.sh`: 4 real attack vectors, captured at 3 wire points (PLC1 port, OpenFlow 6653, Snort mirror)
+ timestamp-aligned state from every layer. Artifacts retained (pcaps + events.log + flows + v1_resp). **All proven, no inference:**
- **V1 control-plane:** unauth `/cars/defense` disarm → `HTTP 401` on wire + `CONTROL…DENIED` audit; never disarmed.
- **V2 flow tamper:** inject bogus + delete real A2 conduit → `cars-flowaudit` daemon caught it autonomously (`missing:1,extra:1`)
  + decision-log drift; self-cleared on restore. (Inline `--check` had a cosmetic `~`→`/root`-under-sudo path bug; daemon is the detector.)
- **V3 state manip:** 8 forged out-of-state ACKs from `.2.66` → **0 packets on the PLC1 wire** (never reached PLC; proven by absence).
- **V4 op-aware ICS (block AND maintain), captured at ALL 3 wire points:** compromised `.2.31` S7 **Write Var func 0x05, DB7,
  area 0x84, value 0x40A00000=5.0** (byte-exact on PLC wire + DPI mirror) → controller installs **ISOLATE flow-mod** (64 OF frames
  embed `.2.31` match on the 6653 channel) → PLC1 wire shows PLC **retransmitting with no `.2.31` reply = connection severed** →
  `isolate_flows(0xca) 0→1`, flow `priority=110 nw_src=.2.31 drop` in end-dump → remediation **restores 1→2**, level restored.
  One aligned chain: 44.464 connect → 44.529 write → ~44.5 isolate flow-mod → 45.176+ cut → restore by 49.
- **VERDICT:** control-API auth, flow-integrity checker, stateful pipeline, and op-aware DPI+criticality+remediation are ALL
  validated at the packet/wire level with matched cross-device evidence. Boundaries (full controller-compromise, poll-window, G1,
  G3) documented. This capability set is DONE and dissertation-grade.

## CC-95 (2026-07-30): ROBUSTNESS BATTERY — stateful pipeline + flow-integrity checker actually attack-tested, hardening added.
Answering the operator's rigor challenge ("did you test with ACTUAL attacks + controller-compromise?"). All proven at the wire,
no inference. New harnesses: `06_Build/cars_flowaudit_robust_test.sh` (isolated), `06_Build/cars_conntrack_robust_test.sh` (isolated).
- **HARDENING (engine + checker): distinct REACTIVE_COOKIE (0x00CA).** The isolated test R4 *demonstrated* a real blind spot: a
  malicious drop-rule disguised in the reactive envelope (cookie0x0, prio100-110, table1) was IGNORED by the checker. Fix: all 6
  reactive installs (block_conduit/throttle/isolate/deflect x2/block) now stamp `cookie=REACTIVE_COOKIE`; checker `is_reactive`
  keys on `0xca`. Deployed to Dell#2 (asserted patcher) + restarted; checker sed-patched on Dell#1 + re-baselined.
- **FLOW-INTEGRITY CHECKER — validated LIVE on the real A2 policy:** injection (`0xbad`)=EXTRA; **removal of a real allowlist rule
  (.2.31->.2.20:502)=MISSING**; **rewrite to drop (black-hole)=CHANGED**; each restored to CLEAN. Evasion now CAUGHT
  (cookie0x0/prio108 -> EXTRA); a REAL reactive isolate (cookie0xca) correctly IGNORED (no false positive). The watch-daemon
  caught the live removal/rewrite AUTONOMOUSLY and posted to the decision log. Isolated: black-hole=CHANGED, loop-rule(self-resubmit)=EXTRA.
- **CONTROLLER-COMPROMISE sim:** **C2 independence PASS** — the checker reads OVS directly + writes its own local feed
  (`/tmp/cars_flowaudit.jsonl`) on Dell#1, so detection/recording do NOT depend on the (possibly compromised) controller; the
  decision-log post is nice-to-have. **C3 residual limit (honest boundary):** a FULLY compromised controller knows `0xca` and can
  hide malicious rules inside it -> checker ignores them. Not a fixable bug (any data-plane checker sharing trust with the
  controller is evadable by a controller that owns the data plane); documented like G1. **C1 poll-window:** 10s daemon poll -> a
  rule living only between polls evades the daemon (point-in-time --check still catches). Mitigation available: faster poll /
  event-driven `ovs-ofctl monitor`.
- **STATEFUL PIPELINE robustness (isolated, mirrors live): 4/4** — legit `+est` works; unlisted `+new` dropped; **forged
  out-of-state ACKs cannot fake `+est`** (0 ESTABLISHED entries); **150-connect flood -> 0 committed attacker ct entries, legit
  client unbroken** (drops never commit -> no ct-exhaustion DoS).
- **VERDICT:** stateful pipeline + flow-integrity checker are now robustness-validated with real attacks, tight, with two
  honestly-documented boundaries (full controller-compromise, poll-window). Ready to build on.

## CC-94 (2026-07-30): OFPORT-DRIFT regression found + fixed at bring-up (GUARD anti-spoof brittleness). Green-light caught it.
On the 2026-07-30 bring-up, the GUARD seam anti-spoof for remediation `.2.45` broke: a flood of `FORBIDDEN/SPOOFED` alerts +
remediation stuck `online:0`. **Root cause:** the netns setup scripts re-add seam ports without a fixed `ofport_request`, so OVS
hands out whatever ofport is next — this boot **Kali/vmnet2 grabbed port 14**, pushing `rem0ovs` to 13. The binding hardcodes
`in_port=14`, so every remns ARP fell through to the priority-100 drop (never leaving the switch) → flood + no PLC reach.
MACs were fine (checked, not the cause). **Fix:** `ovs-vsctl set Interface rem0ovs ofport_request=14` (runtime) + baked
`ofport_request=14` into `cars-remns.sh` (durable). `opr`=10/`mbplc`=7 runtime-pinned too (didn't drift; script edits pending).
- **Second, independent issue same session:** remediation `No route to host` persisted after the port fix because **PLC1's
  teaching box was powered off** — operator powered it on → remediation `online:1`, restores tracking. Both fixes were needed;
  the port fix was necessary regardless (ARPs were dropped at the switch even with the PLC on).
- **Lesson for the writeup + a real robustness finding:** in_port-based anti-spoof is only as stable as the ofport assignment;
  pinning `ofport_request` is required for durable SDN source-binding across reboots. **Bring-up checklist now: green-light the
  seam ofports (rem0ovs=14, opr=10, mbplc=7) before trusting GUARD.** Optional further hardening: give remns a static MAC
  (`02:00:00:00:02:45`, matching the opns/mbns convention) + update the binding, so both MAC and port are deterministic.

## CC-93 (2026-07-29): #28 FLOW-INTEGRITY (policy) CHECKER built + isolated-proven + live-detection-proven. Task #28 (near-done).
New candidate A from `PAPER_EXTRACTION_NECESSITY.md` (Melis/Bologna policy-checker + defensive pair to Gardiner/Bristol
Controller-in-the-Middle). `06_Build/cars_flow_audit.py` + isolated harness `06_Build/cars_flowaudit_test.sh`.
- **What it does:** holds a TRUSTED BASELINE of the static security policy (all non-reactive table0/table1 rules — GUARD,
  A2 cookie-0xa2, and static structural defaults like the table-1 prio-0 miss) and flags MISSING (removed) / EXTRA
  (bogus injected, any cookie) / CHANGED (action rewritten). Ignores CARS reactive isolates (table1, cookie0x0, prio100-110)
  as legitimate live additions. Normalizes out volatile counters. Optional `/cars/flowaudit` POST surfaces drift into the
  decision log (schema-shaped -> tier FORBIDDEN, resp REFUSE, op DRIFT).
- **Isolated proof (real OVS throwaway bridge): 6/6** — pristine CLEAN, legit reactive ignored, inject/remove/rewrite all
  caught (`cars_flowaudit_test.sh`).
- **LIVE proof on ovs1+ovsgw:** baseline captured; injected a harmless bogus rule (`cookie=0xbad` drop on TEST-NET
  198.51.100.7) -> checker flagged EXTRA; removed -> back to prior state. **Control-plane flow-rule tampering is now
  detectable — the thing a stateless firewall/IPS cannot self-detect (the Controller-in-the-Middle defence).**
- **Design fix during bring-up:** first classifier only treated cookie-0xa2 as policy -> the engine's legit table-1 prio-0
  `goto_table:2` defaults showed as false-positive EXTRA. Refactored: baseline = ALL non-reactive rules; re-verified CLEAN on
  pristine + still catches injection. **Known blind spot (documented):** a rule crafted to look reactive (cookie0x0,
  prio100-110,table1) is ignored; tightening needs the engine to stamp reactive rules with a distinct cookie.
- **SEALED (2026-07-30):** `/cars/flowaudit` endpoint live on Dell#2 (selftest logged); fixed checker deployed to Dell#1
  (baseline=all-non-reactive → prio-0 false positive gone), re-baselined **72 static-policy flows → CLEAN**; live drift proof
  (`0xbad` inject → `DRIFT/EXTRA` → `flow-integrity:bogus-injected` in decision log → remove → CLEAN); **`cars-flowaudit.service`
  installed + enabled** (watch every 10s, `ok:1` status). Task #28 COMPLETE. Bring-up note: re-`--baseline` + `systemctl restart
  cars-flowaudit` after each boot (flows reinstall each start).

## CC-92 (2026-07-29): #26 GUARD anti-spoof extended to the TRUSTED SEAMS + PROVEN at the data plane. Task #26.
Extended `BINDINGS` from 3 identities (PLC1 .2.10, HMI1 .2.9, historian .2.30) to also anti-spoof the seams that carry
**elevated conduit privileges** — so an attacker can't steal allowlisted PLC-write access by impersonating them. Live discovery
gave exact (dpid, port, mac, ip): scada `.2.31`=ovsgw(dpid3) port10 `02:00:00:00:02:31`; remediation `.2.45`=port14
`92:b7:80:63:54:56`; Modbus `.2.20`=port7 `02:00:00:00:02:20`. `ews .2.55` not instantiated → skipped. Attacker seams
(att0/atk/vmnet2), honeypot, mirror, IT uplinks deliberately left UNBOUND (must stay untrusted/unknown).
- **Transit-safe by the same path .2.30 already uses:** cross-switch legit traffic arrives on ovs1 via the uplink (prio-150
  GOTO) above the prio-100 spoof-drop. Adding these IPs to PROTECTED_IPS could only break a seam if its in_port/MAC were wrong
  — they weren't (verified live).
- **Deploy:** idempotent compile-guarded patch to `~/cars/cars_engine.py` on Dell#2 (backup `.bak.preguard.*`), controller
  restarted (`osken-manager --observe-links ~/cars/cars_engine.py` in venv). fail_mode=secure kept the tanks running through it.
- **PROVEN LIVE (data-plane, no logs-only claims), ovsgw table 0:** prio-200 legit rules for all three (IP+ARP) + prio-100
  drops installed. **Positive control:** legit `.2.45→.2.10` prio-200 rule `n_packets=114`, remediation stayed online (level
  31.0) — legit path unbroken. **Spoof test:** 5 spoofed `.2.45` SYNs from atkns (port 11, wrong port) → prio-100 drop counter
  `0 → 5` (`270 B` = 54/SYN); controller guard API independently confirms `dpid3 ip 192.168.2.45: 5`. Identity theft of the
  remediation/scada/modbus seams is now blocked at ingress.
- **VISIBILITY REFINEMENT (operator-flagged) — RESOLVED (CC-92b, task #30).** Guard drops were silent (counter + `/cars/guard`
  only). Added `_guard_seen()` in the stats handler: keeps a per-key baseline (`guard_prev`) and, when a prio-100 drop counter
  climbs, emits a decision-log event via `_audit()`. **Key subtlety caught:** the dashboard's structured table/CSV is built by
  `parseAudit()`, whose regex REQUIRES a numeric dst + `\w+` roles + uppercase op — my first record (`dst="GUARD"`,
  `dst_role="anti-spoof"`) failed to parse and only showed in the raw feed. Reshaped to `tier=FORBIDDEN, src=<ip>,
  srole=SPOOFED, dst=0.0.0.0, drole=guard, proto=IP/ARP, op=SPOOF, resp=REFUSE` (verified against the regex before deploy).
  **PROVEN LIVE:** spoofed `.2.31` ×4 + `.2.45` ×5 from atkns → two `FORBIDDEN … SPOOFED … REFUSED (identity-spoof)` rows in
  `/cars/audit` AND in the dashboard decision table + CSV export, delta counts exact. Spoofs now enforced AND visible where the
  operator looks. `key` format for `/cars/guard` preserved (no regression).

## CC-91 (2026-07-29): #25 RESOLVED as PLC1-hardened + Tank2 boundary DOCUMENTED (Option B skipped, deliberately). Task #25.
Went deep on topology-wide remediation; landed on the honest engineering call rather than a hack. What we shipped and what we bounded:
- **WIN (kept): PLC1 remediation was a ZOMBIE and is now fixed.** Its status ts was ~1h45m stale — the service showed `active` but its S7 read had died (Node-RED starved its slot) and the old agent retried the same dead client forever. Added **auto-reconnect** (tear down + re-establish on failure, mark status offline while down) → restarted → revived, oscillating live. Real bug squashed. Agent is now config-driven (`plc1`/`plc2` profiles, argv/env), PLC1 default byte-identical.
- **Tank2 boundary (documented, not hacked):** PLC2's 1212C will **not** reliably service a second concurrent S7 client — proven THREE ways (persistent read: 1 read then `Receive timeout`; transient read: same; MQTT fallback: the collector isn't publishing per-tank level because Node-RED's own S7 reads are timing out + a 1001-listener socket leak). This is a **PLC connection-resource limit, not a CARS gap.**
- **Serendipitous positive finding — Cell-2 IS CARS-gated.** When the PLC2 agent ran from `.3.66`, the dashboard flagged **"historian attacking cell2-nat-plc2 .3.10"** → the `.3.66→.3.10` conduit egresses via `ins2` on the `ovsgw` CARS bridge, so CARS DOES observe/enforce it (refines the earlier over-pessimistic G6). **Consequence: Tank2 already receives the network-BLOCK half of "block AND maintain"** (an attacker spoofing `.3.10` is flagged like our own agent was). It also means remediation must NOT piggyback on `.3.66` (historian) — a proper Tank2 agent would need a dedicated Cell-2 `role=remediation` identity.
- **Decision (Amit + analysis): SKIP Option B.** Rationale: the "maintain" half on Tank2 is a repetition of the wire-proven Tank1 novelty (CC-87), gated behind repairing a broken Node-RED collector + new identity + slot workaround — a poor trade against the week's wrap-up and the "save process at any cost" rule. Tank2's primary defense (network-block) already holds. If full symmetry is wanted later: **Option A** (bump PLC2 S7 connection resources in TIA, brief download) is the clean path; the `plc2` profile is already coded and waiting.
- **Separate backlog item noted:** Node-RED collector is degraded (both PLC S7 reads timing out + EventEmitter leak) → needs a restart to clear; historian telemetry is supervisory, not core to CARS IDR. Tracked, not blocking.
- **Status #25:** PLC1 = done + hardened (topology-wide capability proven on the critical asset); PLC2 = bounded by hardware, documented. Marking substantially complete.

## CC-90 (2026-07-29): Literature-grounded new candidates folded in + 1-week feasibility decision. Tasks #28, #29. Plan: `WEEK_PLAN.md`.
Source: `PAPER_EXTRACTION_NECESSITY.md` (7 papers read from source text, no fabrication). Two new candidates promoted from the analysis; the rest of the reading validates existing posture (cite, don't reimplement).
- **New candidate A — flow-integrity / policy checker (#28), FEASIBLE THIS WEEK.** From Melis et al. (Bologna, formal policy verification) + defensive pair to Gardiner et al. Controller-in-the-Middle (Bristol, your group). Gap it closes: CARS enforces policy but never verifies its **own installed OVS flow table** hasn't been tampered (bogus/removed rules, loops, black-holes). Build: standalone `cars_flow_audit.py` (daemon, like remediation) that diffs live `ovs-ofctl dump-flows` vs intended `a2_policy.json`/`rulebook.json`, alarms + audit-logs on drift. Low effort, testable in isolation (throwaway bridge), strengthens novelty-vs-firewall (stateless firewalls can't self-verify forwarding state). **Verdict: fits the week (≈1 session).**
- **New candidate B — MoTaR-style property deception (#29), DESIGN + ISOLATED PROTO ONLY THIS WEEK.** From Samanis MoTaR PhD (Bristol, your group — supervisors Rashid/Gardiner). Closes finding **P0-6** (HMI `.2.9` still leaks OS fingerprint/banners because it must answer legit polls; CC-89 hid the port, not the properties). Mechanism: present *false* device properties to unlisted sources while `+est` keeps real replies to legit clients. **HIGH risk — touches the live HMI reply path.** Verdict: **NOT safe to rush to live in the same week as everything else.** This week = design doc + isolated prototype (no live HMI); full live rollout deferred to a dedicated session post-wrap-up.
- **1-WEEK FEASIBILITY DECISION (honest):** the week is spent making existing capabilities *whole* (hard rule: retrofits first) + shipping candidate A + the buildable SDN phases, NOT cramming every backlog item. **In-week (feasible):** stateful attack-path re-verify (the CC-89 seal gap), remediation→all PLCs (#25), GUARD anti-spoof→all devices (#26), flow-integrity checker (#28), SDN Phase 2 QoS/metering live + failover isolated proto (#21), SDN Phase 3 micro-segmentation (#22), /ui polish + token rotation (#17) + cosmetic tidy, final no-regression sweep + capstone. **Deferred beyond week (explicit, with reasons):** property-deception live rollout (#29, risk), SDN Phase 4 analytics (#23, scope — optional light version), SDN Phase 5 P4/BMv2 (#24, isolated Mininet, large — stretch/demo only), Modbus re-add (#14, blocked by Node18-vs-22 upgrade risk to the running Node-RED stack). Rationale: protects the stated goal ("wrap up the technical part") and the prime directive ("save process at any cost") over feature-count.

## CC-89 (2026-07-27): SDN PHASE 1 — STATEFUL (conntrack) reply-aware A2 policy, deployed + proven live. Task #20.
First of 5 SDN-utilization prototypes. **Novelty: stateful ICS conduit enforcement that shields CLIENTS (HMIs) from recon while preserving their function** — impossible with stateless L3/L4 default-deny (that's what blanked HMI1 in CC-86a). SDN capability = OVS `ct()` connection tracking.
- **Design + isolated proof:** `06_Build/cars_stateful_test.sh` (throwaway bridge + netns, private 10.9.9.0/24, NO PLCs) → PASS 3/3: allowlisted client works incl. its `+est` reply; attacker cannot scan the server OR the client (`+new` to protected dst dropped). Zero process risk.
- **Controller impl (`cars_engine.py`):** `STATEFUL` flag (fail-safe — install wrapped, any error → classic path, so a switch is never left flowless under fail_mode=secure). New POLICY (table 1): `-trk→ct(recirc)`, `+est→goto2`, `+new & allowlisted→ct(commit)+goto2`, `+new & protected-dst→drop`, `+new other→ct(commit)+goto2`. os_ken `NXActionCT` (API pre-validated in venv before deploy).
- **Deploy protocol (process-safe):** patched in-place (compile-guarded, backup `.bak.prestateful`) with STATEFUL=off first (no-op verify: `installed (CLASSIC)`), then re-added `.2.9` shield to runtime a2_policy + flipped STATEFUL=on + restart, with a **live loop-watch** (collector/remediation reads must keep flowing) and one-`sed` rollback.
- **PROVEN LIVE on ovs1 table 1:** ct dispatch `-trk` n_packets=15103; `+est` allow n_packets=15101 (loop + HMI replies); `.2.9→.2.10` HMI commit n_packets=1 (HMI initiating through the shield); `+new,nw_dst=.2.9→drop` armed. **Kali confined scan `.2.9:102 = filtered`** (was `open` in P0-6). **Control loop unbroken** (collector/remediation/Cell-2 all `=> ALLOW` throughout; remediation ts advancing). HMI panel stays live.
- **P0-6 now genuinely FIXED** (not just reverted): HMI recon-shielded AND functional. Master==deployed: `STATEFUL=True`, `.2.9` restored to DEFAULT_DENY seed (coupled — only safe with STATEFUL=True).
- **SEAL / no-regression under STATEFUL (2026-07-27, enforcement path verified live):** op-awareness `.2.31 READ⇒ALLOW` vs `WRITE⇒ISOLATE 75s [CRIT:CRITICAL]` (write cut, S7TimeoutError); A2 default-deny holds (`.2.66` TCP timed out = blocked, + reactive ISOLATE); criticality tags intact; remediation ts advancing (loop unbroken). **Conntrack preserves ALL enforcement (op-awareness + reactive isolate + criticality + default-deny) while adding stateful reply-awareness — zero regression. PHASE 1 BULLETPROOF & COMPLETE.**

## CC-88 (2026-07-27): WIRE-LEVEL proof — operation-awareness + real datapath enforcement, captured & dissected on the packets (no logs-only claims). Harness `06_Build/cars_packet_proof.sh`; pcaps `/tmp/cars_pcap/`.
Two synchronised capture points: `snort0` (DPI view) + `enx9c69d331d874` (PLC1 physical wire). Attacker `.2.31` (opns). Hard rule held: every claim = a frame + timestamp from the capture.
- **Operation-awareness dissected from bytes:** S7COMM `Function:[Read Var]` vs `Function:[Write Var]`. `.2.31` READ (Setup→Read Var→Ack, armed fr43-47) completed = ALLOW; `.2.31` WRITE (Setup→Write Var, armed fr119-126) = CONTROL.
- **ENFORCEMENT counted on PLC1's wire** (`tshark -Y 's7comm.param.func==5 && ip.src==192.168.2.31'`): **ARMED = 1 Write Var reached PLC1** (fr125 @ t6.311s, then isolate cut the session — the `S7TimeoutError`); **DISARMED = 7 Write Var all reached**. 1 vs 7 write frames on the wire = enforcement, nothing inferred.
- **Datapath drop-flow (grounded):** `nw_src=192.168.2.31 actions=drop, n_packets=14, hard_timeout=75`.
- **Three-view correlation:** wire frame ts ↔ BRAIN audit (`19:24:29 S7 READ⇒ALLOW`, `19:24:33 S7 CONTROL⇒ISOLATE 75s [CRIT:CRITICAL]`, `19:24:51 disarmed⇒would-ISOLATE monitor-only`) ↔ dashboard CSV — all consistent.
- **Tooling note:** `dumpcap` fails backgrounded-under-sudo (privilege-drop) → empty pcaps; `tcpdump -U` on the kernel-datapath OVS ports works.
- **Byte-level audit (raw pcap decoded):** READ frame = S7 Job, param func **`04` Read Var**, area **`82` (Q outputs)**, addr 0 → reads `QB0`. WRITE frame = S7 Job, param func **`05` Write Var**, area **`82`**, addr 0, data value **`00`** → writes `QB0=0` (actuator/output control — NOT `DB7=20`; that was the separate `--dbspoof` demo CC-87; the `cars_packet_proof.sh` write used `--val 0`). **Byte-exact DPI match:** on the wire `03 00`@0, `32 01`@7, and the **S7 function at offset 17** = `04`(read)/`05`(write) — exactly the Snort `cars.rules` offsets (`CARS-S7-READ-var "04";offset:17`, `CARS-S7-CONTROL-write "05";offset:17`). CARS discriminates ALLOW vs ISOLATE on ONE byte at one offset in an identical 5-tuple conduit — provably from the frame.
- **Final confirmations (raw pcap parsed byte-level):** (a) DISARMED = **7 Write Var all byte-identical** (`func 05 / area 82 Q / value 0x00`), 6 in a tight burst with no retransmit = same attack, only response differs. (b) MIRROR (DPI input) carries the `0x05` write frames — **8 write attempts** (1 forwarded + 7 TCP retransmits, exponential backoff 0.3→6.8s) vs **1** reaching PLC1's wire = the datapath dropped 7 (matches drop-flow n_packets=14). Mirror = brain's input; PLC1 wire = post-enforcement output; delta = exactly the dropped packets. WIRE-LEVEL PROOF COMPLETE — 4 corroborating views (wire, cars.rules offsets, BRAIN audit, dashboard).

## CC-87 (2026-07-27): P1 PROCESS-STATE MAINTENANCE ("block AND maintain") — PROVEN, protected vs unprotected.
Sensor-spoof (`db_write DB7.Level=20`) on both tanks; the differentiator no perimeter device can attempt (control-system state maintenance):
- **Tank 1 (PLC1 CRITICAL, CARS armed + remediation `.2.45`):** attacker `.2.31(scada)` S7 CONTROL → **FORBIDDEN → ISOLATE 75s**; S7 connection cut after **1 write** (`S7TimeoutError`); remediation detected the tamper + restored last-good (**restores 0→1**); level kept cycling truthfully. The *same* CONTROL op is FORBIDDEN from `.2.31` yet the remediation restore is ALLOWED (source+operation-aware, rulebook `remediation→plc=OPERATIONAL`).
- **Tank 2 (PLC2 HIGH, disarmed, NO remediation):** same spoof from `.3.66` → **135 writes landed, level PINNED ~20 for the full 15 s** (false reading held; HMI/historian misled), recovered only when the attack stopped.
- = "block AND maintain": CARS blocks the conduit AND maintains process state via last-good substitution. Cárdenas-style FDI, reproduced on real Siemens 1212C hardware.
- **CC-86a (regression found + fixed during this demo):** the P0-6 HMI default-deny (`.2.9`) **broke HMI1** — an HMI is a CLIENT that polls the PLC and needs the REPLY back (reply dst=`.2.9`), which a stateless L3/L4 default-deny drops. REVERTED (a2_policy + code seed + controller restart → HMI recovered). **P0-6 reclassified: proactive recon-shielding works for SERVERS (PLCs) only; HMI recon exposure stays reactive-only unless a stateful reply-aware allow is added.** Honest, citable limitation.

## CC-86 (2026-07-27): ASSET-CRITICALITY FRAMEWORK — PROVEN LIVE end-to-end (task #19). Harness: `06_Build/cars_criticality_proof.sh`.
All 8 scenarios matched design on the running controller. **Same 5-tuple → different verdict = the "a firewall/IPS cannot do this" result.**
- **Decision-side bounded elevation:** `EWS.2.55→PLC1 READ` = **FORBIDDEN, elevated=True [CRIT:CRITICAL]**; `EWS→PLC2 READ` = **SENSITIVE, elevated=False [CRIT:HIGH]** (same actor+op; target criticality alone flips the decision); `EWS→PLC1 READ` inside a maintenance window = **OPERATIONAL/ALLOW** (elevation SUSPENDED, process-state aware).
- **Response-side proportionality:** identical CONTROL op → **ISOLATE 75s (CRIT) / 60s (HIGH) / 30s (LOW)** = `30 + cw·15`. Same action, criticality scales the quarantine duration.
- **Invariants held:** **I1** `HMI→PLC1 CONTROL` (the loop) = **REFUSE — mirror/alert only, never cut** (safety cap; CARS refuses to block, the opposite of a naive IPS); **I2** `SCADA→PLC1 READ` = **ALLOW (operational)** (trusted monitoring always permitted, even on the CRITICAL asset).
- **Armed vs disarmed:** enforce vs `DEFENSE DISARMED - would ISOLATE (monitor only)` — decided + `[CRIT:tier]` tagged both ways.
- **Evidence table (src, op, target-tier, decision, elevated, response, timeout)** captured; grounding = INL CCE + CISA taxonomy + MITRE CJA (CRITICALITY_FRAMEWORK.md). Method: `/cars/respond` decision interface (decision-side disarmed = no enforcement; response-side armed from harmless `.2.66`, flows healed). This is both the **criticality proof (#19)** and the core **novelty/differentiator (CC-83)** demonstration.

## CC-85 (2026-07-27): CONTROL-API AUTH + audit (P0-4 fix) — the unauthenticated control API is closed.
Pen-test P0-4 found the CARS control API (`10.10.10.1:8080`) unauthenticated + control actions unlogged → any host with a control-plane path could **silently disarm** CARS. Fixed in `cars_engine.py`:
- `_load_api_token()` loads/generates a token at `~/cars/api_token` (0600); overridable by `CARS_API_TOKEN` env.
- `_app` gate: POST to `/cars/{defense,maintenance,reload,reload-a2,block,unblock,restore}` requires header `X-CARS-Token`; mismatch → **401** + audit `CONTROL … DENIED`. Success → audit `CONTROL … AUTHORISED`. Uses `_audit(dict)` so it shows in `/cars/audit` + BRAIN log (no more silent tamper).
- **Excluded** `/cars/respond` (Snort→brain feed) so `snort_bridge.py` is unchanged; read-only GETs stay open (monitoring). Dashboard/remediation call no control endpoint → unaffected.
- **PROVEN:** no-token `defense{on:false}` → `{"error":"unauthorized"}` (401) + `CONTROL…DENIED` logged; with-token → `{"enforce_enabled":...}` + `CONTROL…AUTHORISED`. Plant healthy, armed.
- Deploy: engine master + deployed Dell#2 patched (in-place, compile-guarded; token a1299…). **Operator tooling now needs `-H "X-CARS-Token: $TOKEN"` on control calls** (validation scripts to be patched). Master==deployed.
- Residual/notes: token is a shared secret (rotate as needed); could add per-caller tokens/mTLS later; `/cars/respond` injection is a separate lower-severity vector (bridge-token as future work).

## CC-84 (2026-07-27): FIXED role model + posture hardening (foundational brain tightening, operator request).
Removed role ambiguity ("2-3 supervisories") — every IP now has ONE fixed, distinct role; everything unregistered => `unknown` => strict default-deny + dangerous ops FORBIDDEN.
- **Role model (fixed):** plc=`.2.10/.3.10/.2.20`, hmi=`.2.9/.3.9`, **historian=`.2.30`+`.3.66`** (one logical Node-RED collector, honest role both cells), ews=`.2.55`, **scada=`.2.31`** (was supervisory — activates the previously-dead scada rulebook rows, fixes F3), remediation=`.2.45`, gateway=`.2.1`. `.2.66/.2.67/.2.77` + all else = unknown. No `supervisory`-role IPs remain.
- **Behaviour unchanged for legit traffic** (scada→plc any = OPERATIONAL == old supervisory; historian→plc any = OPERATIONAL) — collector + operator reads still ALLOW. Just clean, distinct labels + activated scada policy.
- **Posture hardening (P0-2 pentest gap fix):** added HMI1 to proactive `default_deny` — `(1,"192.168.2.9")`,`(2,"192.168.2.9")` — so HMIs are invisible to recon like PLCs, not merely reactively isolated. (Nothing legit connects TO an HMI at runtime; HMI-as-source `.2.9→.2.10` still allowlisted.)
- **Dashboard:** ROLE `.2.31`→scada, `.3.66`→historian; `hlabel` now returns distinct **Historian / SCADA / EWS** (was all "Supervisory"); `scada` glyph added.
- Deploy: engine→Dell#2 + a2_policy.json default_deny +2 HMI entries + **controller restart** (re-installs proactive flows + new REGISTRY); dashboard→Dell#1 restart+cache-bust. Masters: cars_engine.py + cars_dashboard.py.

## CC-83 (2026-07-26 planned): CARS-vs-firewall/IDS/IPS differentiators + novelty/efficiency test matrix (dissertation-critical).
**Key argument (from the P0 recon result where armed==disarmed for PLC1/Modbus):** the arm toggle controls only the REACTIVE brain (A1/A3/A5). The A2 **proactive default-deny is always-on and firewall-like by design** — so a *recon scan by an unknown/unlisted attacker* is stopped by the firewall floor before the brain engages → armed==disarmed. **That test exercised CARS's firewall-equivalent floor, NOT its novelty.** CARS's contribution is what happens to traffic that is *allowed through a legitimate conduit* (same 5-tuple a firewall passes):
- **Operation-aware** (DPI funccode): same `op→PLC:102` conduit, READ=ALLOW vs WRITE/STOP=FORBIDDEN→ISOLATE. A firewall/IPS can't split one 5-tuple on ICS semantics.
- **Criticality-scaled response:** same op → PLC1(CRIT)=ISOLATE 75s, PLC2(HIGH)=60s, Modbus(LOW)=30s.
- **Process-state-aware:** same write = permit-with-monitoring inside a maintenance window, FORBIDDEN outside.
- **SDN-wide quarantine + auto-heal:** isolates the SOURCE across all switches/conduits, self-heals on timeout — not one inline flow.
- **Process-state MAINTENANCE (P1 novelty):** remediation keeps the plant's DB7 level correct during/after a sensor-spoof — "block AND maintain." No perimeter device does control-system state maintenance.
- **Efficiency:** decide+enforce 0.25-0.76 ms (measured P0); end-to-end MTTM ~12 ms.
**TOMORROW's novelty/efficiency test matrix (full plant running, attack from LEGITIMATE identity `.2.31` operator, armed vs disarmed each):**
1. Operation-awareness: `.2.31→.2.10:102` S7 READ (ALLOW) vs WRITE (ISOLATE) vs STOP (ISOLATE). ← the "firewall can't do this" demo.
2. Criticality-scaling: same WRITE → PLC1 75s vs PLC2 60s vs Modbus 30s.
3. Process-state: WRITE inside maintenance window (permit-monitor) vs outside (FORBIDDEN).
4. Process-maintenance (P1): sensor-spoof DB7 → armed (block + remediation restores) vs disarmed (level pinned/pump latched/overflow). Tank1 (remediated) vs Tank2 (raw, no remediation).
5. SDN-wide quarantine: show ISOLATE flow on all dpids; auto-heal on timeout.
6. Response ladder/proportionality: MONITOR/THROTTLE/DEFLECT per escalation + flood.
7. Efficiency: run mttm.py (att0 `.2.67`) for MTTM distribution.
Capture armed-vs-disarmed contrast per test = the differentiator evidence table.

**TOMORROW — DEDICATED GOAL: TEST + PROVE THE ASSET-CRITICALITY FRAMEWORK end-to-end (CC-77 / CRITICALITY_FRAMEWORK.md).** Prove criticality drives BOTH decision and response, live, and tie each result to the grounding (INL CCE / CISA taxonomy / MITRE CJA):
- **Decision-side elevation (bounded):** SENSITIVE op → CRITICAL PLC1 elevates to FORBIDDEN (`elevated=True`); same op → PLC2 (HIGH) stays SENSITIVE (not elevated); inside a maintenance window elevation is suspended → OPERATIONAL/ALLOW. Sources: EWS `.2.55` (ews→plc SENSITIVE, Option A) and supervisory `.2.31`.
- **Response-side proportionality:** identical operation → tier-scaled quarantine `hard_timeout=30+cw*15` → **PLC1=75s (CRIT), PLC2=60s (HIGH), HMI2/Historian=45s (MED), Modbus=30s (LOW)**; `esc=max(1,ESCALATE-cw)`.
- **Criticality floors:** CRITICAL+flood→BLOCK; SENSITIVE+dcw≥3→BLOCK; FORBIDDEN+dcw≥3→ISOLATE.
- **Invariants:** I1 (hmi↔plc control loop = REFUSE, untouched by criticality); I2 (trusted READs / monitoring = ALLOW even on CRITICAL).
- **Strictness (operator ask):** demonstrate "very strict at any point" — every dangerous op to a CRITICAL asset is FORBIDDEN regardless of source/air-gap; show the `[CRIT:<tier>]` audit tag on every decision.
- Method: armed vs disarmed, one attack per tier, evidence table mapping {source, op, target, tier, decision, response, timeout} → framework justification.

## CC-82 (2026-07-25): PEN-TEST session 1 — black-box positional red-team started; Phase 0 (recon) done. Playbook: PEN_TEST_PLAYBOOK.md.
Adversary model: **black-box, zero-knowledge, positional** (IT → OT-insider → supervisory). InfluxDB de-scoped by operator.
- **Attacker posture set:** `.2.77` (Kali) stripped of trust — allowlist conduits pulled (runtime a2_policy `allow=10→8`, hot-reload) AND **unregistered** in the engine REGISTRY (was `supervisory`; line + 2 seed conduits commented) → genuine default-unknown. Dashboard ROLE `.2.77`→unknown. **Restore all 3 commented lines + re-add 2 a2_policy conduits to revert to the trusted-insider scenario.**
- **IT position:** no attacker node in GNS3 (only had VPCS). Deferred to a VPCS reachability test; GNS3 = dual pfSense (IT-FW/OT-FW) + DMZ + 2 cloud nodes, `it0` seam into ovsgw, IT→OT SNAT to `.2.1`.
- **Phase 0 recon (from `.2.77`, ARMED)** — crafted nmap `/24` + ICS NSE (`s7-info`,`modbus-discover`,`enip-info`) saved to Kali `~/pentest_recon_*.{nmap,gnmap,xml}`. **Result: A2 proactive default-deny HID PLC1 `.2.10` + Modbus `.2.20`** (absent from scan; attacker cannot enumerate the crown-jewel PLC). Findings (in playbook table):
  - **P0-1** crown jewels invisible (proactive concealment) — strong positive.
  - **P0-2 GAP:** HMI1 `.2.9:102` leaked a SYN-ACK (tcpwrapped) then reactive-blocked → dashboard "`.2.77`→HMI1". `.2.9` is NOT in A2 default_deny (only `.2.10`,`.2.20`). **Fix: add `(1,"192.168.2.9")` to default_deny for proactive parity.**
  - **P0-3 GAP:** supervisory stack (FUXA :1881, Grafana :3000, InfluxDB :8086) reachable from OT at `.2.30`+`.2.67` (Dell#1 0.0.0.0 binds), CARS ungated. MQTT :1883 localhost-only ✓; Node-RED :1880 paused.
- **Two contention findings (from D2/collector):** (1) Node-RED historian poll starves the remediation agent's PLC1 S7 connection slot (1212C limit); (2) remediation agent doesn't auto-reconnect after a drop. Mitigation used: pause Node-RED (`snap stop node-red`) + `systemctl restart cars-remediation` → remediation live on Tank 1.
- **RESUME TOMORROW at Phase 0b/1:** CARS was DISARMED for the raw-footprint baseline scan (`~/pentest_full_scan_*.txt`, `-p-` + default/discovery/vuln). Next: interpret the disarmed footprint (did PLC1/Modbus become visible, or does A2 proactive persist when disarmed?), then Phase 1 (ARP/MITM + segmentation), Phase 2 heavy ICS (S7 write/STOP, Modbus FCs, both cells), Phase 3 sensor-spoof (Tank1 protected+remediated vs Tank2 raw — remediation is Cell-1-only), Phase 4 DoS/A5, Phase 5 supervisory, Phase 6 combined devastation. Then remaining backlog: Modbus re-add (Node-18), /ui polish, token rotation.

## CC-81 (2026-07-25): D2 — second tank (PLC2 / Tank 2) commissioned + integrated. Two-tank plant live.
- **Key recall (corrected a wrong assumption):** PLC1's tank is a **PLC-internal SCL simulation**, not a physical sensor — `DB7 "Sim"` (non-optimized, `Level` Real @ DBD0, `Pump`), a **cyclic OB 100 ms** bang-bang, pump = **`%Q0.3`**, on an S7-1200 **1212C**. Sensor-spoof attacks work because `Level` is a writable sim value. (Source: `cars_process.py`, DECISION_LOG CC-69/CC-70.)
- **Therefore D2 was simple:** cloned PLC1's project → downloaded to PLC2 **as-is** (identical 1212C, same IP `.2.10`, in-PLC sim needs no sensor). Programmed over a **direct TB2-switch link** (Windows/TIA `.2.55` + PLC2 `.2.10` isolated) — deliberately bypassing the SDN so CARS wouldn't block the S7 program-download — then rewired PLC2 back to Dell#3 (`.3.10` via NAT).
- **Tank-2 tweak** (distinct from Tank-1's 30..70): band **20..55**, fill **+0.4** / drain **-0.6** per 100 ms. Verified live: level oscillating ~20-55, `Q0.3` toggling.
- **HMI2 skipped:** the cloned project's HMI carried only the university template screen (HMI1's real screen lives in a different project). Node-RED provides the Tank-2 view; HMI2 deferred.
- **Node-RED extended** (`06_Build/cars_nodered_cell2_add.json`): PLC2 S7 endpoint (`.3.10`, `DB7,REAL0`=level, `Q0.3`=pump) → `cars/cell2/plc2/*` → MQTT → InfluxDB (subscribe broadened to `cars/#`) + `/ui` TB2 tiles. **Also fixed Cell-1 pump bit `Q0.0`→`Q0.3`** (why cell1 pump always read 0).
- **CARS needed NO change:** Node-RED polls PLC2 as `.3.66` (route via `ins2`), already allowlisted `.3.66→.3.10:102`; reads = OPERATIONAL/ALLOW **[CRIT:HIGH]**. PROVEN live: both cells publishing, cell1 pump now real, audit repeating `.3.66→.3.10 S7 READ ALLOW [CRIT:HIGH]`.
- Pending: confirm `plc2_level` in InfluxDB; optional light two-tank interaction; refresh the Node-RED master flow file.

## CC-80 (2026-07-24): Node-RED historian-collector integrated — PLC1 S7 telemetry -> MQTT -> InfluxDB + /ui HMI, CARS-authorized & criticality-tagged.
Real Node-RED edge-gateway pattern (item 3 of the backlog). Design chosen for practical validity + D2 scalability + native sync with the existing stack.
- **Identity (elegant):** Node-RED runs on Dell#1 base ns; `ip route get .2.10/.2.20` -> `dev sup0 src 192.168.2.30` = the **Historian identity**. So the collector maps onto the existing Historian asset (role=historian, MEDIUM, GUARD-bound dpid3:3) — NO new registry entry, no new DPI, no rulebook change.
- **Only CARS change:** +2 A2 allowlist READ conduits (`.2.30->.2.10:102` S7, `.2.30->.2.20:502` Modbus) in runtime a2_policy.json (hot-reloaded, allow=10) + code ALLOWLIST seed (now 10, seed==runtime). Enforcement already correct: reads=OPERATIONAL->ALLOW; any write=CONTROL->FORBIDDEN + SENSITIVE-elevation on CRITICAL PLC1.
- **Infra stood up:** Mosquitto broker `127.0.0.1:1883` (apt+systemd). InfluxDB 2.7.12 (docker; org=`cars`, bucket=`plc`, token). Flow master: `06_Build/cars_nodered_flow.json` (S7 read DB7.REAL0=level, Q0.0=pump -> MQTT `cars/cell1/plc1/*` -> InfluxDB `cars_telemetry` -> /ui gauges/chart).
- **PROVEN LIVE:** MQTT publishing `cars/cell1/plc1/level` (moving 54/62/34) + `pump`; CARS audit repeating `.2.30(historian) -> .2.10(plc) S7 READ => ALLOW [CRIT:CRITICAL]` each ~4s poll. New conduit works end-to-end.
- **Node-RED reality:** TWO instances coexist — plain `node-red` snap (editor :1880, our working instance, Node v18) and `node-red-industrial` (Flask :1882, nodes baked in). Palette s7/influxdb/dashboard installed on :1880; **Modbus DEFERRED** — `node-red-contrib-modbus@5.60` needs Node>=22 (EBADENGINE on Node 18) -> install an older 5.3x/5.4x, or consolidate onto node-red-industrial.
- **Scales to D2:** add `cars/cell2/...` topics + a PLC2 S7 endpoint; collector conduit pattern already modeled.
- **InfluxDB landing CONFIRMED:** `from(bucket:"plc") ... cars_telemetry` returns live `plc1_level`/`plc1_pump` (cell1 tag). Full path PLC1->NodeRED->MQTT->InfluxDB proven.
- **Collector-write->blocked demo PROVEN (security figure):** same `.2.30` that is ALLOWed to READ, on attempting an S7 WRITE to PLC1, got `FORBIDDEN ... S7 CONTROL => ISOLATE source 192.168.2.30 75s (quarantine all conduits) [CRIT:CRITICAL]` + switch drop-flow `priority=110,nw_src=192.168.2.30 hard_timeout=75 actions=drop` (35 pkts dropped). READ allowed / WRITE isolated, criticality-scaled 75s. Restored after (telemetry resumes). READ classifications keep appearing in the audit during isolation because the mirror still feeds Snort->brain (classification decision) while the P110 flow drops forwarding — audit=decision log, enforcement=flow table.
- Pending: /ui dashboard eyeball; re-add Modbus (Node-18 version); rotate `cars-token-change-me` before write-up.

## CC-79 (2026-07-24): POST-AUDIT no-regression sweep (cars_validate_all.sh) — 19/20 PASS, the 1 FAIL is an expected CC-77 timeout-calibration artifact, NOT a regression.
Ran the full consolidated both-cells suite after deploying every CC-78 fix + the N3 renumber. Log: `~/validate_postaudit_<ts>.log` (Dell#1); decisions CSV `cars_decisions_1784927420003.csv`.
- **Criticality response proven live + proportional** (the headline result): identical PLC1 CONTROL/STOP → **ISOLATE 75s [CRIT:CRITICAL]**; PLC2 CONTROL → **ISOLATE 60s [CRIT:HIGH]**; Modbus ops → **ISOLATE 30s [CRIT:LOW]**. Timeouts `30+cw*15` = 75/60/30 exactly as designed. Decision-side elevation intact (SENSITIVE→FORBIDDEN on CRITICAL).
- **A3** op-awareness both cells (READ→ALLOW vs WRITE/STOP/coil/diag/program/illegal→blocked) ✅. **A2** default-deny (listed .2.31 OK, unlisted .2.66 denied — N3 renumber did NOT break atkns) ✅. **A1** DEFLECT→decoy .3.99 + ISOLATE src-drop ✅. **GUARD** 8 anti-spoof bindings ✅. **FEAT-1** A2 hot-reload, **FEAT-3** maintenance-window waive+reclose, **PD-1** defense disarm/rearm ✅.
- **The 1 FAIL — SEC 4 SELF-HEAL auto-expiry (before=1, after=1):** the self-heal test triggers a **PLC1** block (now CRITICAL → hard_timeout **75s** per CC-77) but waits only **~35s** — the wait was calibrated for the pre-criticality 30s timeout. So the block is (correctly) still present at 35s. **This is the criticality feature working (CRITICAL assets quarantine longer), not a self-heal fault** — the auto-expiry itself was verified in CC-76/C.7. **Test needs recalibration**, not the system. Fix: point the self-heal check at a LOW-criticality conduit (Modbus .2.20, 30s) OR extend its wait to ~80s.
- **Verdict: no regression from the audit (F1/F2/N2/N3).** Clean post-audit baseline established.

## CC-78 (2026-07-24): DEEP cross-device audit — every deployed artifact diffed vs master; all gaps resolved or logged.
Ingested every deployed config/script/service (Dell#1/2/3) + live `ip`/`ovs`/`iptables`/systemd state and diffed against E:\ masters. See CONSISTENCY_AUDIT.md §6.
- **Deployed == master (functionally) for all code:** `cars_engine.py` (maint fix present), `snort_bridge.py`, `cars_remediation.py`, `mb_server.py` — comment/whitespace drift only.
- **Dashboard mystery solved:** two dashboards were uploaded — plain `cars_dashboard.py` is a **stale backup** (no badge/steadiness); `cars_dashboard-31045dcf.py` is **byte-identical to master** → **criticality badge + steadiness fix ARE deployed** (running copy confirmed).
- **CC-76 fix confirmed deployed:** `cars-bridge` drop-in `After/PartOf=cars-snort` + `Restart=on-failure`; `cars-snort` drop-in `Wants=cars-bridge`.
- **Cell-2 setup location RESOLVED:** `/usr/local/sbin/cars-cell2.sh` (why `ls ~/*.sh` on Dell#3 was empty). NAT reconfirmed (DNAT .3.10→.2.10, MASQUERADE cell2gw=.2.1).
- **Fixes applied to masters:** **F1** dashboard `ROLE`/`TYPEOF`/`hlabel` synced to registry (+.2.20/.2.31/.2.77/.3.66, +`supervisory` glyph); **F2** engine seeds (+2 remediation RULEBOOK rows, +4 ALLOWLIST conduits) → **seed==runtime verified (29 rules, 8 conduits)**; **N2** Cell-2 S7 control-start `0x28` sid 1000048 added to a new `cars.rules` master. Engine `py_compile` OK.
- **New findings needing user:** **N1** active Snort config is `/etc/snort/cars.conf` (uploaded `snort.conf` is stock Debian default, NOT it) → upload cars.conf to close the audit. **N3** duplicate `.2.66` on `att0`(base) + `atkns` → decide dedup. **N4** `.2.1` shared by cell2gw + OT-FW (both gateway, info-only).
- **DEPLOYED + VERIFIED on hardware (2026-07-24, `cars_deploy_verify.sh`):** Dell#1 — dashboard F1 swapped + relaunched, running :8090 confirmed **serving the new ROLE map** (proves live reload, not just file); cars.rules N2 deployed to `/etc/snort/cars.rules`, `snort -T` clean, cars-snort+cars-bridge restarted together. Dell#2 — engine F2 deployed, **seed==runtime verified live (29 rules/8 conduits)**, controller healthy (PLC1=CRITICAL), not restarted (runtime unaffected). Backup-first + rollback-on-fail; one iteration needed (`sudo cp` for the root-owned `/etc/snort/cars.rules` write). **master==deployed on all three fixes.**
- **N1 CLOSED:** `cars.conf` = `HOME_NET 192.168.2.0/24` (OT subnet, tighter than stock `any`; harmless — rules use explicit dst IPs incl. .3.x), `EXTERNAL_NET any`, `include /etc/snort/cars.rules`.
- F3 (scada rows) + F4 (.2.77 test conduit) accepted as-is.
- **N3 CLOSED (2026-07-24, Option A):** the duplicate `.2.66` was NOT vestigial — `att0` (base-ns) is used by `mttm.py`, which must sit in the base ns because it queries the controller API `10.10.10.1:8080` that OT netns `atkns` can't reach (C.8 isolation); `atkns/.2.66` is the canonical attacker for ~10 scripts. Fix: renumbered the MTTM vantage `att0` → **`.2.67`** (persistent in `cars-seams.service` + applied live, `mttm.py SRC=.2.67`), `atkns` keeps `.2.66`. Eliminates the standing ARP ambiguity (att0 had 24k dropped RX). MTTM unaffected — SUSPECT rules are dst-keyed, so `.2.67`→PLC1 is detected/blocked identically. Dashboard `cars-dashboard.service` deferred (user hand-edits the py).

## CC-77 (2026-07-24): ASSET-CRITICALITY framework (two-place: decision + response) built, deployed (cars_engine v0.7), proven on hardware.
Supervisor feedback: assets differ in criticality; PLC1 (safety-critical primary tank) > PLC2 (buffer). Grounded in recognised methods
(NOT invented) - see CRITICALITY_FRAMEWORK.md: INL **CCE** consequence-prioritisation (primary), **CISA** OT criticality/function taxonomy
(Water/Wastewater), attack-path **centrality** modifier. ACL per protected asset: PLC1=CRITICAL, PLC2/HMI1=HIGH, HMI2/Historian=MEDIUM,
Modbus=LOW; unset->LOW (backward-compatible). `CW`={3,2,1,0}.
- **Decision side (elevation, bounded):** a SENSITIVE op to a CRITICAL asset -> **FORBIDDEN** (nothing but the loop + an authorised
  window may touch the safety-critical PLC). PROVEN: EWS->PLC1 = `FORBIDDEN,ISOLATE,elevated=True`; EWS->PLC2/Modbus = `SENSITIVE`.
  In a maintenance window the elevation is suspended -> EWS->PLC1 = `OPERATIONAL/ALLOW` (permitted-with-monitoring).
- **Response side (proportionality):** `esc=max(1,ESCALATE-cw)`, CRITICAL floors (FORBIDDEN->ISOLATE now, SENSITIVE->BLOCK, flood->cut),
  `hard_timeout=30+cw*15` (75/60/30 s). PROVEN: same CONTROL -> PLC1 **ISOLATE** vs PLC2/Modbus **BLOCK**.
- **Invariants preserved:** I1 hmi<->plc loop = REFUSE (untouched); I2 trusted READs/monitoring = ALLOW (supervisory read PLC1 = ALLOW).
- **Policy (Option A):** `ews->plc/hmi` reverted OPERATIONAL->SENSITIVE in rulebook.json (so EWS is elevated on critical assets; legit
  access via the maintenance window). Two code edits also needed the `maint` line to permit an in-window elevated op.
- New: `GET /cars/criticality`; audit line carries `[CRIT:<acl>]` (+`,elevated`); `respond` JSON has `crit`/`elevated`. Master==deployed (v0.7).
- Verified: 9-case + 7-case standalone logic tests + live `/cars/respond`. Pending: no-regression run of cars_validate_all.sh; dashboard crit badge.

## CC-76 (2026-07-24, Appendix C verification): sensing-path coupling finding + C.1/2/3/6/7/8 all confirmed on hardware.
Ran `cars_verifyC.sh` to promote the documented Appendix C claims to directly-verified. Results:
- **C.1** ✅ OVS mirror `m0` (`select_all:true`) → `snort0`; Snort sniffs `-i snort0`. Note: `HOME_NET=any` (works — cars.rules are dst-IP-specific; could be tightened).
- **C.2** ✅ `ovs1`+`ovsgw` → `tcp:10.10.10.1:6653`, `ovs2` not local, 2 live OF sockets.
- **C.3** ✅ (on Dell#3) `PREROUTING -d 192.168.3.10 -j DNAT --to 192.168.2.10` + `POSTROUTING -o cell2gw -j MASQUERADE` — exactly as documented.
- **C.6** ✅ historian/SCADA **LIVE**: InfluxDB :8086=200, Grafana :3000=302, FUXA :1881=200 (not idle — correct the cheat sheet).
- **C.8** ✅ control-plane isolation: OT seam (`opns`/.2.31) → `:8080` API **UNREACHABLE**; control plane → reachable. The unauthenticated API is safe by isolation, empirically.
- **C.7** ✅ proactive holds when the sensor path is down (unlisted `.2.66`→Modbus stayed BLOCKED by A2 default-deny throughout), and reactive **restores** once the bridge is back (2nd `.2.31` write → `S7ConnectionError timed out` = blocked).
- **FINDING (CC-76):** `cars-bridge` is **dependency-coupled to `cars-snort`** — `systemctl stop cars-snort` **cascaded** and stopped the bridge; `systemctl start cars-snort` did **NOT** revive it, so reactive detection was **silently blind for ~5 min** (Snort alerting, nothing forwarded to the brain; audit went quiet — mistaken at first for the remediation agent dying, but the agent was alive the whole time — Snort saw its `.2.45` reads). **Real single-point coupling in the sense→signal path.** Fix: always `systemctl restart cars-snort cars-bridge` together; harden `cars-bridge.service` to auto-revive with Snort (`PartOf=cars-snort.service` + `Restart=always`). **FIX APPLIED 2026-07-24**: systemd drop-ins — `cars-bridge.service.d/override.conf` (`After`+`PartOf=cars-snort.service`, `Restart=on-failure`) and `cars-snort.service.d/override.conf` (`Wants=cars-bridge.service`) → bridge now starts/stops/restarts with Snort. CC-76 CLOSED. Good resilience-chapter material.
- **C.4** ✅ (later same day): IT attacker `10.0.40.66` via GNS3 chain (Ent-FW→DMZ→OT-FW) **SNAT'd to `.2.1`**; default-deny dropped it at `ovs1` (couldn't ping the PLC; topology showed `.2.1→PLC1`); when allowlisted through, reactive cut it: `192.168.2.1(gateway) → .2.10 TCP => BLOCK (all switches)` (gateway→plc FORBIDDEN outright). G5 identity-collapse proven both proactively and reactively. **Entire Appendix C (C.1–C.8) now empirically verified on hardware.** (Kali quirk: fire `s7_write.py` WITHOUT sudo — snap7 is in the user env, not root's.)

## CC-75 (2026-07-24, disarmed worst-case "devastation" baseline): raw unprotected impact + 2 hardware findings.
Defense DISARMED, remediation agent STOPPED (Pass A), max-intensity battery from Kali `.2.77` on live PLC1 (evidence: cars_evidence_logger).
- **Physical impact (as intended):** sensor spoof pinned Level to 0/100 → pump/relay LATCHED to extremes; STAGE 2/3/6 output-flap at 20 Hz
  = violent relay chatter ("like a gun / uzi") — the raw actuator devastation with zero defense. This is the baseline of what CARS+agent prevent.
- **FINDING 1 — T0816 CPU stop/start is REJECTED by the S7-1200:** `plc_stop`/`plc_hot_start` → `S7ProtocolError class=0x81 code=0x04
  "service not implemented on the module"`. The 1212C firmware doesn't expose the classic stop service via S7comm, so that attack vector is
  **closed on this hardware** — the process never halted. Honest positive (device-level, not CARS).
- **FINDING 2 — PLC self-protects under concurrent S7 load:** the grand-finale (3 concurrent attack sessions) triggered `ConnectionReset by peer`
  from the PLC's S7 stack — the CPU dropped excess concurrent connections (mild self-defensive DoS behaviour). Worth citing re: G6/load limits.
- **Recovery:** program/firmware never touched (runtime-only by design); on re-arm + agent restart the tank OB resumes its own Level integration and
  normal 30-70 oscillation; relay resumes cycling. Note: Pass B (agent-on, disarmed) is already covered by the earlier disarmed sensor test
  (137 writes / 47 restores / reading maintained, actuator latched) — no need to re-run.

## CC-74 (2026-07-23, Validation Campaign 2): PHYSICAL signature of sensor FDI + armed/disarmed necessity of BOTH layers.
Live-tank sensor false-data injection (`--dbspoof` DB7=20) from `.2.31`, armed vs disarmed, on real PLC1:
- **ARMED:** attacker cut after **1 write** (BLOCK→ISOLATE); agent +1 restore; pump keeps cycling (never latches); tank in-band. No harm.
- **DISARMED:** attacker lands **137 writes**; agent fires **~47 restores** (kept the DB reading at last-good ~35, never stuck at 20);
  BUT the **physical pump latched ON and the relay went silent** — control law latches pump ON at Level<=30, and the attacker
  re-forces 20 faster than the loop recovers, so Q0.3 never sees >=70 to toggle off. In a real plant = pump-stuck-on / overflow.
- **Recovery:** on re-arm + attack stop, tank resumes 30-70 sweep, relay clicks again, restores freeze (no phantom heals). Full self-recovery.
**Finding (honest, nuanced):** the agent maintains the *sensor reading* in both states, but under *sustained disarmed* injection the
*actuator* can still latch — so **only the network block (armed, cut-after-1-packet) fully prevents the physical harm**. This is the
"block AND maintain" thesis demonstrated *physically*: neither layer alone suffices under all conditions; together they protect both
the reading and the actuator. (Also validates C2/no-hallucination from the 800-row run: 774 ALLOW vs 24 enforcement, all against attackers.)
Self-heal FAIL in cars_validate_all.sh = measurement artifact (35s window < TCP-retransmit re-isolation refresh); verified clean:
controller conduit_blocks/mac_blocks empty, only allowlist ALLOW flows remain. Core = effectively 20/20.

## CC-73 (2026-07-23): Unified remediation feed — "block AND maintain" now in ONE decision log + live dashboard card.
Integrated the remediation agent's activity into the dashboard: agent writes a live status + event feed to `/tmp`
(`cars_remediation_status.json`, `cars_remediation.jsonl`); the dashboard (same host, Dell#1) reads them locally via a new
`/api/remediation` route (no OT→control-plane break) and (a) shows a **Process-remediation card** and (b) interleaves
restores into the **Decision Log** as purple `RESTORE`/`MAINT` rows. **Proven** by the exported CSV (`cars_decisions_1784839189774.csv`):
one log contains, at 21:37:43, all three — `.2.77 CONTROL => BLOCK(all switches) => ISOLATE ENFORCED` (attacker cut),
`.2.45 S7 RESTORE OPERATIONAL MAINT "RESTORED last-good 56.0 (saw tampered 21.0)"` (process maintained), and continuous
`.2.45 READ => ALLOW` (authorized conduit). Kali: 1 write then S7TimeoutError. This is the single-artifact evidence figure
for the P1 novelty.
- Engineering lessons logged in SYNC_STATE.md: master≠deployed can happen (reconcile by ingesting the deployed file);
  after ANY dashboard edit you MUST restart `cars_dashboard.py` (HTML served from memory) AND cache-bust the browser
  (`:8090/?v=<tag>`); the `enx*` USB-NICs emit benign IPv6 link-local churn (carrier stays up) that makes Chrome abort
  fetches — silenced with `disable_ipv6=1`, and the card is now flap-proof via a cached last-good payload.
- Minor polish TODO: the agent-injected RESTORE row uses `HH:MM:SS` while controller rows use `MM-DDTHH:MM:SS` — align later.
- Consistency fixes (post-review): (1) RESTORE rows now use the controller's `MM-DDTHH:MM:SS` timestamp format (was
  browser `HH:MM:SS`); (2) restores get their own decision-log mode **`REMEDIATE`** (teal) instead of reusing `MAINT` —
  `MAINT` is reserved for the operator maintenance-window feature, so the two are no longer conflated. Mode column now:
  ENFORCED / MONITOR / MAINT (maintenance window) / REMEDIATE (autonomous agent restore). Distinction matters: MAINT
  *relaxes* policy for human ops; REMEDIATE is an always-on authorised corrective write by the .2.45 role.
- ROOT-CAUSE (fixed): the live card looked dead for ~an hour of debugging — cause was a missing `()` on the card-render
  IIFE (`(function(){...})` never invoked), while `_remLast` (line before) and the log-injection (block after) both ran,
  producing the paradox: data present, log correct, card frozen. Fix = `})` -> `})()`. Confirmed with a 2nd attack:
  card shows `restores 2` with both `RESTORED` rows (58.0/saw22.0 @22:20:40, 56.0/saw21.0 @21:37:43), CSV has both
  `.2.77 => ISOLATE` + `.2.45 RESTORE MAINT` pairs. Not cache, not the enx IPv6 flap — a one-char JS defect.

## CC-72 (2026-07-23): D4 Rung B — process-state MAINTENANCE via last-good substitution. P1 NOVELTY COMPLETE.
Stood up an authorised `remediation` identity (`.2.45`, netns on ovsgw; role `remediation`; allowlisted; rulebook
`["remediation","plc","CONTROL","OPERATIONAL"]` above the blanket forbidden row). Ran `cars_remediation.py` (process-anomaly
based: watches `Tank.Level` DB7, restores last-good on an impossible drop / below-floor value; audit-independent because the
OT netns can't reach the control-plane API — cleaner + mirrors a real virtual-sensor).
- **Result (armed sensor spoof from `.2.77`):** CARS `CONTROL => BLOCK → ISOLATE .2.77` (network block, attacker cut after 1
  write) **AND** the agent logged `TAMPER (Level=22, prev 32) -> RESTORED last-good 32` (process-level state maintenance).
  CSV corroborated: `.2.77 => BLOCK/ISOLATE ENFORCED`, `.2.45(remediation) => ALLOW`. The HMI/level returns to normal via the
  restore rather than the slow self-climb.
- **THE NOVELTY, now fully demonstrated on real hardware:** CARS does **block (network) AND maintain (process)** — it bounds
  the attacker with a safety-capped SDN response *and* actively restores correct process state (borrowing the Cárdenas-group
  estimation idea, integrated with the network block). No reference paper claims this trio: safety-capped network response +
  process-level maintenance + real ICS hardware. Rung A = block-that-maintains (source-cut suffices); Rung B = active
  substitution for the harder case. **P1 done.** `.2.45` added to the dashboard topology as a `CARS-Remediation` node.

## CC-71 (2026-07-23): D1 — controller-DoS resilience (fail-secure data plane) PROVEN.
Killed the CARS controller (os-ken on Dell#2) mid-operation and re-tested:
- Attacker `.2.66` (unlisted) → PLC1 read TIMED OUT **both with the controller running AND after it was killed** — the
  pre-installed **A2 default-deny drop flows persist in OVS** (`fail_mode=secure`); no controller needed to keep an
  unauthorized source out.
- Operator `.2.31` still read `QB0=0x08` and the process kept cycling → legit traffic + control loop untouched. 9 standing
  A2/pipeline flows held.
- **Result:** the single-controller SPOF (G6) is mitigated at the data plane — proactive protection + installed enforcement
  survive controller loss. **Honest limit:** new REACTIVE detections pause while the controller is down (no brain to decide),
  but the standing proactive layer and the process both hold. Answers "attack the SDN controller." Controller restarted after.

## CC-70 (2026-07-23): D1 — HMI1 visual (operator panel) + on-screen false-data deception vs CARS protection.
Configured **HMI1 (KTP700 Basic PN, `.2.9`)** in WinCC to display `Sim.Level` (I/O field + bar) and `Sim.Pump` (lamp),
downloaded from the EWS. Two screenshots captured (the strongest report figure):
- **Shot 1 DISARMED:** Kali `.2.77` sensor-spoof (274 writes) → panel shows **false low `Level` ~20 while the pump lamp
  stays green / relay stuck ON** = operator deceived, live on a real panel (the Cárdenas false-reporting effect, visible).
- **Shot 2 ARMED:** spoof gets 1 write then `S7TimeoutError` (CARS `CONTROL => ISOLATE .2.77`) → panel returns to the
  30↔70 oscillation = **CARS protecting operator-visible integrity.**
- **Extra finding (A2 EWS scoping):** the HMI download from the EWS `.2.55` was BLOCKED at first because `.2.55` is
  allowlisted to the PLC `.2.10` only, NOT the HMI `.2.9` (flash-LED worked = L2 DCP; the IP download conduit was denied).
  = the authorized EWS can reach only its authorised targets. Completed the download by disarming briefly (or would
  allowlist `.2.55->.2.9`). Also: KTP Basic needed **Transfer mode** enabled on the panel to accept the push (panel-side).

## CC-68 (2026-07-22): EWS added (Windows+TIA on ovsgw) + honest S7CommPlus DPI-coverage boundary.
Completed the deferred **Engineering Workstation**: Windows laptop w/ TIA Portal wired to Dell#1 via Type-C→Ethernet
(`enx00e04c680018` added to `ovsgw`), OT IP `192.168.2.55`. Demonstrates authorized-engineering-through-CARS.
- **Unauthorized EWS** (`.2.55` unregistered): `FORBIDDEN(unknown) -> .2.10 => BLOCK → ISOLATE`. A rogue engineering
  station cannot reach the PLC — identity/conduit protection (A2 + registry) holds.
- **Authorized EWS** (registered supervisory + allowlisted): TIA `Go online` + monitor + **program download all ALLOWED**.
  **Confirmed end-to-end:** downloaded a live edit (DrainRate -0.8 -> -2.0) through CARS and the relay's OFF phase visibly
  shortened (~5 s -> ~3 s), pump ON ~5 s / OFF ~3 s = correct bang-bang with fill slower than drain. Modification took effect.
- **HONEST FINDING (extends G3 — DPI coverage):** TIA speaks **S7CommPlus (0x72)**; CARS's operation-aware DPI parses only
  **classic S7comm (0x32)** (snap7 / Metasploit-style, blocked all day) + Modbus. So a TIA program-download is classified
  only as an `S7` *session* → `ALLOW`, **not** as `PROGRAM` → it is NOT operation-gated. CARS gates the EWS by IDENTITY,
  not by operation, for S7CommPlus. The maintenance-window PROGRAM gate therefore applies to classic-S7comm/Modbus program
  ops, not TIA-native downloads. Mitigations: identity gating (works), A5 rate-limit (works), future = S7CommPlus
  download-request DPI or "flag high-volume 0x72 from a non-HMI source."
- **A5 tuning data point:** TIA's bursty online polling tripped `[FLOOD 6–12 ops/s] THROTTLE` (rate-limited, not cut,
  auto-healed). Legit engineering traffic is bursty → consider raising `FLOOD_RATE` for trusted EWS or exempting the
  CRITICAL 0x72 loop. Logged in `VALIDATION_DAY_RESULTS.md`.
- **`.2.55` now a first-class `ews` role** (not borrowed `supervisory`): the pre-existing rulebook `ews` rows were changed
  from SENSITIVE→OPERATIONAL so the EWS can monitor continuously (SENSITIVE would escalate THROTTLE→BLOCK and cut TIA);
  dangerous ops (CONTROL/DIAG/PROGRAM classic-S7comm) remain FORBIDDEN + maintenance-gated. Audit now reads
  `192.168.2.55(ews) => ALLOW`. Added to the **dashboard topology** as an `EWS` node (ROLE/TYPEOF/hlabel in cars_dashboard.py).

## CC-67 (2026-07-22): RIGOROUS VALIDATION DAY — real-VM attackers, full MITRE ICS coverage, + a REAL PLC process protected.
Full record: `VALIDATION_DAY_RESULTS.md`; test matrix: `TEST_MATRIX_validation_day.md`; paper basis: `PROCESS_and_PAPER_LEARNINGS.md`.
- **Real attackers stood up:** Kali VM insider on the OT L2 (`.2.77`, VMware→vmnet2→ovsgw) running real snap7/pymodbus/scapy/nmap;
  IT attacker via the **GNS3 Purdue kill chain** (`10.0.40.66` → Ent-FW → DMZ → OT-FW SNAT → `it0`), CARS-mediated.
- **MITRE ATT&CK for ICS — all 8 targeted techniques exercised + blocked:** T0846 recon (filtered), T0855/T0831 command
  injection (blocked), T0836 modify-parameter (SENSITIVE→THROTTLE — honest: type-graded, not value-inspected), T0816 stop
  (network-blocked + PLC PUT/GET native refusal, double-layer), T0843 program download (PROGRAM→blocked), T0814 DoS
  (blocked, process protected), T0856 spoof (GUARD T0 drop). Insider = authorized-but-malicious (registered supervisory,
  reads allowed / control blocked); unauthorized insider blocked at boundary.
- **KEY FINDING (G5):** the OT-FW SNATs ALL IT traffic to `.2.1(gateway)` → CARS blocks it wholesale = safe but coarse
  (can't distinguish EWS from attacker behind NAT). Operation-aware DPI is exercised from sources that can connect.
- **REAL PLC PROCESS + NO-HARM (the capstone):** programmed a bang-bang tank-level control loop into the real S7-1200 1212C
  (SCL, cyclic OB 100 ms, pump=`%Q0.3`) via TIA Portal — cycles autonomously every ~4–5 s. Under a 20 s control-injection
  storm from a compromised operator, CARS `CONTROL => BLOCK → ISOLATE` and **the relay kept its steady rhythm throughout —
  process integrity preserved on REAL hardware** (a step beyond the Cárdenas-group Mininet simulation this is modelled on).
- **Honest boundaries carried:** reactive first-packet (CC-54); L2 MAC/ARP recon visible (conduit guard, not port-security);
  Kali VM had a post-flap VMware `vmnet2` L2 fault (ARP reply not returning) — storm re-run from the operator conduit.
- **Still open (next session, optional):** multi-source concurrent DDoS + load/latency numbers; DPI-evasion (R13/G3); R14
  compromised-trusted CRITICAL-loop live demo (G1, documented). Core attack-coverage + no-harm = DONE.

## CC-66 (2026-07-19): A5 — RATE / BEHAVIORAL INTELLIGENCE (flood-aware, graded, safety-capped). PROVEN.
Added a 4th decision axis to CARS: not just WHAT the op is (A3), WHO/WHERE (role/criticality), and PERSISTENCE (offense
count) — but the op's RATE. The sensor (snort_bridge v4) counts every alert per (src,dst,op) over RATE_WINDOW=3s and
sends ops/s in the /respond payload (the controller can't see true packet rate — the bridge dedups POSTs on a 3s
cooldown — so the burst size is carried in the report). The brain flags flood = rate >= FLOOD_RATE (5/s) and grades:
- **OPERATIONAL + flood -> THROTTLE (meter) then BLOCK** on persistence — a VOLUMETRIC DoS built from individually-LEGAL
  ops (read/poll flood). This is the genuinely NEW capability: pre-A5 every read was ALLOW, so a read-flood that
  saturates a PLC's comms was invisible.
- **SENSITIVE + flood -> BLOCK; FORBIDDEN + flood -> immediate ISOLATE; CRITICAL -> REFUSE always** (safety cap holds
  even under flood — the HMI loop is never throttled).
**PROVEN (cars_rate_demo.sh, dashboard CSV corroborated):** a single S7 READ from .2.31 at ~17/s produced, on the SAME
legal op: `READ => ALLOW` (normal) -> `[FLOOD 17 ops/s] THROTTLE conduit @20pps` x2 -> `[FLOOD 17 ops/s] BLOCK conduit`
-> `READ => ALLOW` again once the flood stopped (graded AND reversible/self-healing). Controller latencies 0.4-0.7 ms.
**HONEST findings (Rule 0):**
- The [FLOOD] label rarely appears on FORBIDDEN writes: a forbidden op is cut on the FIRST packet by the reactive layer,
  so its rate never accumulates at the sensor to trip the threshold. Rate is therefore REDUNDANT for forbidden ops
  (already ISOLATEd fast, CC-65); A5's real value is on PERMITTED-op floods. State this — don't claim "flood detection
  catches everything".
- Demo ACT1 first-run failed to CONNECT because the setup's relay-reset write (a CONTROL op) BLOCKed the conduit while
  armed -> fixed in cars_rate_demo.sh (reset relay DISARMED, heal, then arm; heal before the baseline read).
Files: cars_engine.py (RATE_WINDOW/FLOOD_RATE, select_response flood grading, respond() rate->flood, [FLOOD] audit
label, rate/flood in out dict); snort_bridge.py v4 (per-key sliding-window rate); s7_write.py (--readstorm); cars_rate_demo.sh.
Deploy note: the Dell#2 engine had drifted from master (comment/whitespace) — patched via a line-locating transformer
(/tmp/a5patch2.py), NOT block-match, and NOT base64 (Amit's preference). A5_DESIGN.md written.

## CC-65 (2026-07-19): DUAL-PLC DoS-style flicker storm — disarmed baseline vs armed protection, side by side.
`cars_dos_flicker.sh` launches simultaneous high-rate output storms on BOTH real PLCs (PLC1 .2.10 via opns .2.31;
PLC2 .3.10 cross-NAT via root .3.66) using `s7_write.py --storm --hz H --secs S` (single connection, hammers
QB0=0x08<->0x00). Ran both scenarios back-to-back:
- **DISARMED (enforce_enabled=false):** both storms completed (166 / 171 toggle cycles), TB1 + TB2 relays clattered
  the full 20s; CARS logged `S7 CONTROL => DEFENSE DISARMED - would ISOLATE/BLOCK` on BOTH cells at 0.01-0.03 ms.
  Saw + classified every write, deliberately no enforcement = the IDS-only/unprotected baseline.
- **ARMED (enforce_enabled=true):** snap7 clients died with `S7TimeoutError: Receive timeout` — CARS cut the conduits
  mid-storm. Controller fired `ISOLATE source .2.31` AND `ISOLATE source .3.66` together (0.23-0.70 ms enforcement),
  quarantined both attackers across all 3 switches, then `ISOLATE AUTO-HEALED` on every dpid once the storm ceased.
- **Dashboard CSV corroboration:** each timestamp = 2 rows (both PLCs), `mode` column cleanly separates `MONITOR`
  (disarmed) from `ENFORCED` (armed) — a clean, exportable A/B evidence artifact.
- **Honest boundary (CC-54 reactive first-packet):** on the armed run the relays aren't perfectly still — the guard
  can't un-send the first packet, so each source gets a tick or two before ISOLATE lands and the connection times out.
  Claim = "storm stopped within a few ms, attacker locked out", NOT "relay never moves".
- Artifacts saved: `cars_dos_flicker.sh`, `s7_write.py` (+`--storm --hz --secs`).

## CC-64 (2026-07-19): PLC2-4 PROVEN — consolidated both-cells end-to-end validation, effective 20/20.
`cars_validate_all.sh` (auto-with-pauses) exercises general + ICS + all agendas + all additions across BOTH cells,
matching each PASS against the fresh audit DIFF (no stale lines) with protocol-tagged patterns. Final result 19/20 in
one pass + the 20th confirmed by a focused re-test:
- **SEC1 ICS operation-awareness (A3) 10/10:** PLC1 & PLC2 (real) READ->ALLOW vs WRITE->CONTROL->BLOCK/ISOLATE vs
  STOP->DIAG; Modbus .2.20 full taxonomy READ/CONTROL(coil)/DIAG/PROGRAM/ILLEGAL. All correctly tagged `S7`/`MODBUS`.
- **SEC2 A2 default-deny:** listed operator .2.31 genuinely read `[101,102,103,104]`; unlisted attacker .2.66 TCP-denied.
- **SEC3 A1:** DEFLECT redirect flow installed (attacker's PLC-bound traffic rewritten to decoy .3.99) + ISOLATE drop flow.
- **SEC4 GUARD (T0 bindings) + SELF-HEAL:** confirmed — block auto-expired at ~30s once the attacker stopped (focused re-test).
- **SEC5 additions:** A2 hot-reload (no restart), maintenance window waive+reclose, defense arm/disarm — all pass.
- **REAL FINDING (defensible, not a bug):** an ISOLATEd source's malicious S7 PDU keeps TCP-RETRANSMITTING; each
  retransmit is re-mirrored to Snort and re-detected, RENEWING the hard_timeout. So the quarantine correctly persists
  *while the malicious command is still on the wire* and self-heals ~30s after the attacker truly goes silent. The first
  35s harness window was simply shorter than the retransmit tail; killing the client -> clean 30s heal.
- **HARNESS Rule-0 hardening (so PASS/FAIL is trustworthy):** (1) match the DIFF of NEW audit lines, not "last line
  changed" (a prior run's stale `S7 DIAG` had spuriously PASSed a Modbus-diag check); (2) clear a source's priority-110
  ISOLATE before each check (restore only deletes the priority-100 conduit, so after the first CONTROL the source was
  quarantined and later ops never reached the wire = no packet, no alert, no decision); (3) 3-attempt retry to survive a
  dropped first connect; (4) protocol-tagged patterns + anchored `=> *(BLOCK|ISOLATE)` so MAINTENANCE-AUTHORISED /
  DEFENSE-DISARMED lines (which also contain "BLOCK") can't false-pass an "enforced" check. `cars_validate_all.sh` saved.

## CC-63 (2026-07-19): PLC2-3 PROVEN — full arm/disarm showcase mirrored on the SECOND physical PLC (TB2).
Ran `cars_showcase_plc2.sh` (Cell-1 source .3.66 -> PLC2 at .3.10 cross-NAT). All acts passed with audible confirmation:
- **ACT1 operation discrimination:** `READ => ALLOW (operational)` vs `WRITE => CONTROL => BLOCK conduit (switches 1,2,3)` —
  same station/PLC/port, opposite outcomes, on the second cell.
- **ACT2 disarmed:** flap attack -> TB2 relay CLICKS, CARS logs `CONTROL => DEFENSE DISARMED - would ISOLATE (monitor only)`.
- **ACT3 armed:** identical attack -> `CONTROL => ISOLATE source .3.66 (self-healing)`, one tick then silence.
- **EPILOGUE:** relay OFF, guard ARMED. Controller latencies 0.013–0.594 ms; ISOLATE auto-healed on all 3 dpids at timeout.
CARS now reaches, attacks, AND protects BOTH physical PLCs operation-aware, cross-NAT. Reactive first-packet (CC-54) holds
on both. `cars_showcase_plc2.sh` saved to 06_Build.

## CC-62 (2026-07-19): Decision log now names the ICS PROTOCOL (S7/MODBUS), not just the transport (TCP).
From the dashboard CSV export Amit noticed S7 writes were tagged `proto=TCP, op=CONTROL` — the ICS protocol identity was
missing (an S7 write and a Modbus coil-force both showed `CONTROL`/`TCP`, indistinguishable). Root cause: `snort_bridge.py`
regexed the op out of the alert msg (`CARS-S7-CONTROL-write`) with a NON-capturing group `(?:MODBUS|S7)`, discarding the
family; proto stayed the L4 transport. **Fix (1 line, bridge):** capture the family — `CARS-(MODBUS|S7)-(<OP>)` — and set
`proto = S7|MODBUS` when a DPI op fires (S7CommPlus session -> `proto=S7`); non-ICS traffic keeps TCP/ICMP. Deployed to the
`cars-bridge` systemd unit (restarted via `systemctl restart cars-bridge`, NOT pkill — Amit correctly flagged that pkill+nohup
would race the service manager into a DOUBLE instance -> double-counted offenses). Verified: S7 write to PLC2 now logs
`... S7    CONTROL =>  BLOCK conduit`. op = operation semantics; proto = protocol family. Master `snort_bridge.py` updated.
- **Operability note:** systemd-managed CARS units must be restarted through `systemctl`, never pkill/nohup — a manual
  nohup copy runs alongside the respawned unit and duplicates every decision.

## CC-61 (2026-07-19): PLC2-2 PROVEN + a real Snort finding — broad session rules masked the operation DPI.
Deployed the Cell-2 registry/allowlist (.3.66 supervisory, .3.66->.3.10 allow) + .3.10 S7 rules. First test FAILED: an
S7 write to PLC2 came back OPERATIONAL/ALLOW (relay landed), not CONTROL. Capture (Rule 0) proved the write PDU is
byte-identical to PLC1 (0x32@7, 0x01@8, func 0x05@17) - so the rule matched but was NOT logged.
- **Root cause:** `sid 1000005/1000006` are broad `icmp/tcp any -> 192.168.3.10 any` SESSION rules (no content/flags), and
  cars.conf had NO `event_queue` config -> Snort's default surfaced ONE event per packet and the generic session rule
  WON, masking the operation-specific S7 rule (sid 1000045). PLC1 has no such broad rule, so it never surfaced there.
- **Fix (one line, global, helps both cells):** `config event_queue: max_queue 10 log 5 order_events content_length` ->
  Snort now logs both the session AND the operation event. Re-test: S7 write to PLC2 -> `OPERATIONAL ALLOW` (session) +
  `CONTROL => BLOCK/ISOLATE` (operation) -> conduit cut, snap7 Receive-timeout. **PLC2 now operation-aware exactly like PLC1.**
- **Technical-accuracy note for the write-up:** operation-aware ICS detection can be silently masked by coarse session/anomaly
  rules under a detector's default single-event-per-packet policy; multi-event logging (or precise session rules) is
  required for the operation layer to be reliable. Light-on = reactive first-packet (CC-54), consistent across both PLCs.

## CC-60 (2026-07-19): PLC2 (Cell-2) end-to-end — reach + audible actuation PROVEN; operation-aware DPI extended.
Goal: replicate the PLC1 attacks/defence on the SECOND physical PLC (TB2) and validate the whole system across both cells.
- **PLC2-1 PROVEN:** Cell-1 netns (opns) is IP-isolated to .2.0/24 (no route to .3.x), but Dell#1 root reaches PLC2 at
  `.3.10` (DNAT->.2.10 on ovs2) sourced as `.3.66`. snap7 `.3.10` write QB0=0xFF -> **TB2 relay clicked audibly**
  (`connected to PLC2: True`). `.2.10`=PLC1/TB1 vs `.3.10`=PLC2/TB2 are two distinct boxes. And CARS already
  source-blocks the cross-cell probe (`FORBIDDEN .3.66 -> .3.10 => BLOCK/ISOLATE`) at ovsgw.
- **Architecture note (honest, G6):** CARS's Snort mirror is on ovsgw (Dell#1). A Cell-1->PLC2 attack crosses that
  mirror -> detectable + blockable at the Cell-1 edge before Dell#3. A Cell-2-INTERNAL attack (host on ovs2) is not
  mirrored -> not inspected. So Cell-2 is protected against the external/cross-cell threat, not intra-cell (would need a
  Snort/mirror on Dell#3 = scale/future work).
- **PLC2-2 (built, deploying):** REGISTRY += `.3.66` (supervisory eng station), ALLOWLIST += `(.3.66,.3.10,6,102)`,
  Snort S7 rules for `.3.10` (write 0x05->CONTROL sid1000045, stop 0x29->DIAG 1000046, read 0x04->READ 1000047). So
  PLC2 gets the SAME operation-aware treatment as PLC1: READ allowed, WRITE=CONTROL forbidden, etc.

## CC-59 (2026-07-19): Dashboard cosmetic pass — Decision Log tab (structured, filterable, exportable).
Amit asked for tabbed live logs + filters/sort + export; I filtered the ask to what amplifies technical accuracy/novelty
(Rule 0, "don't blindly follow"): BUILT a Topology|Decision-Log tab split with a full-width structured decision table
(time / src(role) -> dst(role) / proto / op / tier / response / mode), filters on the NOVELTY axes (Tier, Response, Op,
Mode + free-text), a live response-counts strip, CSV+JSON export of the filtered rows, and CLIENT-SIDE ACCUMULATION
(keeps up to 3000 unique decisions/session vs the API's 60-line window). CUT as low-value/misleading: date-time range
pickers (audit is session-recent) and arbitrary multi-column sort (kept a newest/oldest toggle). Deployed to Dell#1 via
raw-heredoc-blocks + tiny python stitch with truncation asserts (the reliable incremental method after the escaped-patcher
paste kept truncating). Dashboard is now a real operator + evidence console. Master `cars_dashboard.py` updated.
`cars_dashboard.py` gained: DEFENSE arm/disarm + MAINT window toggle buttons, new op badges (CONTROL/DIAG/PROGRAM/
ILLEGAL), and a `do_POST` proxy so the browser can POST to the controller. Deployed to Dell#1 (base64/full-file, the
inline patcher paste kept truncating). Live 4-state proof — SAME S7 output-write from .31, four button states, four
distinct decisions (browser clicks -> controller `*** DEFENSE/MAINTENANCE ... ***` markers align exactly):
  1. DEFENSE ARMED,   MAINT off -> CONTROL => BLOCK
  2. DEFENSE DISARMED           -> CONTROL => DEFENSE DISARMED - would BLOCK (monitor only)
  3. DEFENSE ARMED,   MAINT off -> CONTROL => ISOLATE   (BLOCK vs ISOLATE = per-source escalation ladder, not a button diff)
  4. MAINT WINDOW OPEN          -> CONTROL => MAINTENANCE-AUTHORISED (window) - ALLOW
So the dashboard is a real operator console, not just a viewer. **All three FEAT items (FEAT-1/2/3) complete + verified.**
The implementation's within-architecture operability gaps are now closed; remaining limits (G1 compromised endpoint,
G2 L7-proactive, reactive first-packet) stay documented as boundaries.

## CC-57 (2026-07-19): FEAT-1 (A2 hot-reload) + FEAT-3 (maintenance window) BUILT + PROVEN. FEAT-2 (dashboard) next.
Completing the implementation's operability gaps (within-architecture; the G1/G2/reactive-first-packet limits remain).
- **FEAT-3 maintenance window (PROVEN):** `GET/POST /cars/maintenance {minutes}`. During an open window, DELIBERATE
  engineering ops (CONTROL/DIAG/PROGRAM) are downgraded FORBIDDEN->OPERATIONAL (permitted-with-monitoring); ILLEGAL is
  NEVER waived. Live proof: S7 write in-window -> `CONTROL => MAINTENANCE-AUTHORISED (window) - ALLOW`; window closed ->
  `CONTROL => BLOCK`. Answers "engineers do legitimately write outputs sometimes" without weakening the default stance.
- **FEAT-1 A2 hot-reload (PROVEN):** ALLOWLIST/DEFAULT_DENY now seed + load from `a2_policy.json` (on the controller);
  A2 flows are cookie-tagged `0x00A2`; `POST /cars/reload-a2` wipes ONLY the cookie-tagged proactive flows on every
  switch and re-derives from the new config (reactive P100+ untouched). Live proof: added a `.2.99` default-deny to the
  JSON + reload -> the drop flow appeared on ovsgw (`cookie=0xa2`) with NO restart, then vanished on revert. Also
  `GET /cars/allowlist`. Symmetric with A4 (CC-42). Master engine deployed to Dell#2 via a fail-closed idempotent patcher.
- Endpoints added: `/cars/maintenance` (GET/POST), `/cars/allowlist` (GET), `/cars/reload-a2` (POST). Decisions still
  sub-ms. FEAT-2 (dashboard: defense/maintenance toggles + new op badges + do_POST proxy) implemented in master, deploy
  pending on Dell#1.

## CC-56 (2026-07-19): Viva-ready live showcase (`cars_showcase.sh` v3) — the full story in one paced run.
Polished 4-act narrated demo on the real S7-1200, all reliable + honest (no stale data, ends in a safe state):
- **ACT 1 operation-awareness (armed):** same station/PLC/port, `S7 READ => ALLOW` vs `S7 WRITE(CONTROL) => BLOCK` — the
  firewall-can't-do-this beat. Added S7 read rule sid 1000044 (func 0x04 -> READ) for the clean contrast.
- **ACT 2 unprotected (disarmed):** attacker flaps Q0.3 -> relay CLICKS; CARS logs 'would block'.
- **ACT 3 armed:** identical attack -> one tick then SILENCE, `CONTROL => ISOLATE`.
- **ACT 4 total lockout:** the quarantined attacker can't even connect to attempt the kill-switch (honest reframe after
  the stop proved flaky/stale-data-prone live; S7-STOP=DIAG=>FORBIDDEN stands from CC-55).
- **Epilogue:** self-heal, relay reset OFF, guard re-armed; control loop climbed throughout (plant never stopped).
Decisions 0.01-0.7 ms. Two ~30s heal pauses double as narration windows. Full S7 attack client `s7_write.py`
(read/write/flap/stop/start). This is the flagship artifact for the write-up/viva.

## CC-55 (2026-07-19): PD-7 — broadened S7 coverage: CPU stop/control detection (kill-switch) added + proven.
Captured a real snap7 `plc_stop`/`plc_hot_start` PDU (defense off). Dissection: classic S7comm job (0x32/ROSCTR=1),
func at TCP-payload offset 17 — **STOP=0x29** (carries "P_PROGRAM"), **Control/start=0x28** (same slot as the write's 0x05).
Added Snort sids 1000042 (CARS-S7-DIAG-stop) + 1000043 (CARS-S7-DIAG-control) -> bridge op=DIAG -> FORBIDDEN (existing row).
**Proven:** `--stop` with defense ARMED -> audit `DIAG => ISOLATE source .31` — CARS catches the CPU-halt command on the
wire. S7 guard now covers write-to-output (CONTROL) AND stop/control (DIAG).
- **Defense-in-depth finding:** this S7-1200 REFUSES the classic S7comm stop (PUT/GET protection, S7ProtocolError
  class=0x81 code=0x04), so the kill-switch does not halt THIS CPU — the network guard blocks the ATTEMPT and the CPU
  refuses it (two independent layers). On a vulnerable CPU (S7-300/400 or protection-off) the stop would halt the plant
  and CARS is the protection. Physical drama stays with the WRITE demo (relay); STOP is detection+block of the attempt.
- Master `cars_ics_dpi_rules.txt` + `s7_write.py` (--stop/--start) updated. Attack coverage: Modbus READ/WRITE/CONTROL/
  DIAG/PROGRAM/ILLEGAL + S7 write + S7 stop/control — a broad real-world ICS attack surface, operation-classified.

## CC-54 (2026-07-19): PD-4 resolved — single-shot ICS detection is RELIABLE; reactive first-packet reality documented.
Measured single S7-write detection with defense DISARMED (no enforcement to confound), spaced past the 3s bridge dedup:
**10/10 detected**, and `snort0` RX `0 errors / 0 dropped / 0 missed`. So Snort 2.9 `-A fast --daq afpacket` with NO stream5
(pure per-packet inspection) reliably catches single ICS request packets. The earlier "misses" (e.g. CC-52 PROGRAM,
S7 first-write) were a too-short audit-poll WINDOW, not packet loss or PAF flush. **No DAQ/stream tuning needed.**
- **Honest capability statement (goes in the eval + supersedes any 'relay never moves' framing):** CARS's A3 is a
  *reactive* guard — it acts on OBSERVING the write, so the FIRST malicious write inherently reaches the PLC (the relay
  ticks once) and CARS then blocks the source within ~ms (MTTM ~11ms), locking the attacker out so a SUSTAINED attack
  (flapping/repeated writes) is stopped almost immediately. No reactive system can un-send the first packet; claiming
  'the output never moves' would be overclaiming. Preventing even the first write needs PROACTIVE L7 blocking, which
  OpenFlow cannot do (G2) — so for an allow-read/deny-write policy the reactive operation-aware layer is the mechanism,
  and it is inherently first-packet. Defense-in-depth: A2 proactively denies unauthorized SOURCES entirely (never reach
  the PLC); A3 reactively catches dangerous OPERATIONS from allowed sources after the first packet.
- **Demo narrative (honest):** disarmed -> attacker flaps -> relay clicks continuously; armed -> relay ticks ONCE then
  the attacker is quarantined and the clicking stops. That single residual tick is the reactive-defense reality, framed
  as a feature boundary, not hidden. PD-1..PD-6 complete.

## CC-53 (2026-07-19): LIVE S7 PHYSICAL-ATTACK DEFENCE on the real PLC1 — action-taking guard proven on hardware.
Built from Amit's real snap7 exploits (exploit_plc_conveyor/logic_flap): classic S7comm (0x32) Write-Var to the PLC
output area (0x82) toggles a physical relay on Q0.3 (audible). PD-1..PD-6:
- **PD-1** `/cars/defense` arm/disarm switch (enforce_enabled; disarmed = classify+log 'would block', no flow).
- **PD-2/3** captured a real snap7 write PDU on the mirror; grounded S7-write signature (TCP-payload offsets: 0x32@7,
  0x01@8 ROSCTR job, 0x05@17 Write-Var, 0x82@27 output). Snort rule sid 1000041 `CARS-S7-CONTROL-write`; bridge regex
  extended to `CARS-(?:MODBUS|S7)-...` -> op=CONTROL; reuses the existing CONTROL->FORBIDDEN rulebook row. The legit HMI
  loop is S7CommPlus (0x72) so the 0x32 rule never fires on it; S7 reads (func 0x04) not flagged.
- **PD-5** eng-station allowlist `.2.31->.2.10:102` (A2 permits it; the WRITE is what A3 catches). snap7 3.1.0 installed.
- **PD-6 demo (`cars_s7_demo.sh`):** DISARMED -> `CONTROL => would BLOCK` and the relay CLICKS (attack lands). ARMED ->
  `CONTROL => ISOLATE source .31` and the snap7 write times out (`S7ConnectionError`), attack dropped before the PLC.
  decide+enforce 0.3-0.7 ms.
- **Key proof:** same attacker/PLC/operation; the ONLY variable is the arm switch. CARS is a real action-taking,
  operation-aware ICS guard on physical hardware.
- **Open (PD-4, next):** single-packet flush (G3) lets the first write or two land before the block, so the relay can
  be left energized ('light left on'). Harden Snort stream/PAF on ports 102/502 so the FIRST S7 write is dropped -> the
  relay never moves when armed (clean 'protected = stays off' demo). Also relay-reset needs defense disarmed (an OFF-write
  is itself a CONTROL op the armed guard blocks).

## CC-52 (2026-07-19): Broadened ICS intelligence (brain v2) BUILT + PROVEN — ICS attack battery, 6/6 operation classes.
ICS-B1..B5 complete. New DPI ops (Snort rules + bridge regex + 8 rulebook FORBIDDEN rows + `mb_attack.py` raw-FC client
+ `cars_ics_battery.sh`). Battery result — SAME trusted operator `.31 -> Modbus PLC .20`, verdict driven by ICS operation:
  READ    -> OPERATIONAL -> ALLOW
  WRITE   -> SENSITIVE   -> THROTTLE
  CONTROL -> FORBIDDEN   -> BLOCK       (coil force FC5/15 = direct digital actuation)
  DIAG    -> FORBIDDEN   -> BLOCK/ISOLATE (restart FC8)
  PROGRAM -> FORBIDDEN   -> BLOCK       (FC43 MEI)
  ILLEGAL -> FORBIDDEN   -> BLOCK       (FC>43)
CARS decide+enforce 0.017-0.839 ms. **The brain now reasons over a full ICS operation taxonomy and forbids dangerous
operations by their NATURE even from a fully-trusted source ("save the process at any cost") — a plain L3/L4 firewall
sees one identical conduit and cannot make these six distinctions.**
- **Bonus finding:** per-source escalation fired live — sequential dangerous ops from `.31` accumulated offenses and the
  3rd (DIAG) escalated BLOCK->ISOLATE (source quarantine), then auto-healed. So "repeated dangerous ops / ICS recon from
  a trusted source -> isolate" is demonstrated, not just single-op block.
- **Honest caveat (G3):** PROGRAM was MISSED on the single-shot attempt and only detected on `--count 4` — Snort's PAF
  stream flush on one-shot Modbus requests is unreliable, so a single dangerous packet can evade detection some of the
  time. This is the one real operational weakness of the DPI feed (reactive layer); mitigations = Snort stream/rule
  tuning or the modbus preprocessor. A2 proactive still bounds unauthorized SOURCES regardless. Strengthen G3 note in
  GAP_AND_NOVELTY with this quantified flakiness.
- **Novelty impact:** the operation-aware contribution is materially stronger now — not just READ/WRITE but a
  criticality-graded response over CONTROL/DIAG/PROGRAM/ILLEGAL with a dangerous-op-forbidden-from-trusted safety rule.
  Bundle: `cars_battery_20260719_155423.tar.gz`.

## >>> SESSION PAUSE 2026-07-18 (resume here) <<<
Long session ended; testbed powered down safely. State is fully persisted (nothing lost on reboot):
- **DONE this session:** CC-43 (A2/NAT per-switch fix), CC-44 (Phase-2a e2e), CC-45 (DEFLECT round-trip FIXED), CC-46
  (MTTM ~11ms + reversibility), CC-47 (stress 8/8), CC-48 (5-source cross-check), CC-49 (gap/novelty -> GAP_AND_NOVELTY.md),
  CC-50 (ICS discrimination PROVEN), CC-51 (broadened-ICS design lock).
- **ICS-battery build IN PROGRESS:** ICS-B1 (Snort rules CONTROL/DIAG/PROGRAM/ILLEGAL) DONE + live on Dell#1;
  ICS-B2 (bridge op regex extended) DONE + live on Dell#1. Both services active, normal traffic unaffected.
- **RESUME AT ICS-B3:** add rulebook FORBIDDEN rows to `cars_engine.py` (master + Dell#2 ~/cars/) so
  `("any","plc",<CONTROL|DIAG|PROGRAM|ILLEGAL>,"FORBIDDEN")` (+ hmi) sit AFTER the CRITICAL loop rows and BEFORE the
  trusted rows; restart controller; regression-check existing decisions unchanged. Then ICS-B4 (`mb_attack.py` raw-FC
  client + `cars_ics_battery.sh`) and ICS-B5 (run + 5-source cross-corroborate).
- **NOTE:** until ICS-B3 lands, a CONTROL/DIAG op from the operator would currently classify OPERATIONAL->ALLOW (the
  `supervisory->plc->any` rulebook row catches it) — harmless (only the attack client sends those), but it's exactly
  why B3 must precede any battery run. Snort/bridge backups saved as `*.bak` on Dell#1.

## CC-51 (2026-07-18): DESIGN LOCK — broadened ICS operation intelligence (brain v2). Amit: build all classes, dangerous=FORBIDDEN.
Extend the brain from 3 operations (READ/WRITE/S7) to a full ICS operation taxonomy so it recognises dangerous operations
by their NATURE and forbids them even from a trusted source ("save the process at any cost"). Design (Rule-0 locked):
- **Operation taxonomy (Modbus FC -> op label):**
  - FC 1,2,3,4  -> `READ`    (observe; safe)
  - FC 6,16     -> `WRITE`   (set registers/setpoints; sensitive actuation)
  - FC 5,15     -> `CONTROL` (force coils = DIRECT digital-output actuation; DANGEROUS)
  - FC 8        -> `DIAG`    (diagnostics: can force listen-only / restart comms; DANGEROUS)
  - FC 43       -> `PROGRAM` (encapsulated MEI / device programming; DANGEROUS)
  - undefined FC-> `ILLEGAL` (malformed/probe; ANOMALY) [detected for the specific illegal FCs we rule for; not exhaustive]
  - S7 session  -> `S7` (existing)
- **Classification (rulebook, first-match, NEW rows inserted AFTER the CRITICAL loop rows, BEFORE the trusted rows):**
  `("any","plc",<CONTROL|DIAG|PROGRAM|ILLEGAL>,"FORBIDDEN")` (+ same for "hmi"). So the real HMI->PLC loop stays
  CRITICAL/REFUSE (trusted, never cut), but ANY dangerous op to a PLC/HMI -> FORBIDDEN -> BLOCK, INCLUDING from the
  trusted operator. A trusted WRITE stays SENSITIVE (throttle); a trusted CONTROL/DIAG/PROGRAM/ILLEGAL is FORBIDDEN.
- **Recon + volumetric covered by existing mechanics:** a source issuing many dangerous ops (FC-scan) accrues per-source
  offenses -> ISOLATE (scanner quarantine, CC-38); a sustained WRITE-storm -> SENSITIVE escalates THROTTLE->BLOCK. No new
  escalation logic needed — the new op DETECTION feeds the existing offense/escalation engine.
- **Build order:** (1) Snort rules for FC5/15,FC8,FC43,illegal (msg `CARS-MODBUS-<OP>` so the bridge maps them);
  (2) bridge regex `CARS-MODBUS-(WRITE|READ|CONTROL|DIAG|PROGRAM|ILLEGAL)`; (3) rulebook rows -> Dell#2; (4) `mb_attack.py`
  raw-Modbus-FC crafting client (opns) + `cars_ics_battery.sh`; (5) validate + 5-source cross-corroborate.
- **Honest scope:** Modbus is a simulator (G4); enforcement stays conduit-granular (G2) so a dangerous op blocks the whole
  operator conduit (acceptable per "save the process"); "illegal FC" detection covers specific ruled FCs, not arbitrary
  (Snort content can't cheaply match "not-in-set"). CRITICAL loop still REFUSE (G1 unchanged — a compromised loop endpoint
  is still trusted by the safety cap).

## CC-50 (2026-07-18): ICS-protocol intelligence trial — operation discrimination PROVEN (+ harness bugs caught).
Amit challenged (correctly) that the Phase-2 harnesses attacked mostly with generic ICMP/TCP, not ICS-protocol attacks,
so they didn't aggressively prove the operation-aware intelligence. Built `cars_ics_attack.sh`. Two harness bugs found
and fixed under Rule 0 (both are anti-hallucination lessons):
1. **v1 printed STALE evidence:** the discrimination test's connects timed out (my own cleanup `del-flows nw_src=.31`
   deleted the A2 P60 ALLOW rule for the operator, so its SYN hit the bare P55 deny), and the harness displayed 15-min-old
   Snort/audit lines and stamped "PROVEN" on a test that never ran. Fixed: never `del-flows` the allowlisted src; use
   `/cars/restore` (removes only P100 enforcement, preserves P60). Also: allowlist is only re-installed at switch-connect,
   so clobbering it needs a manual re-add or controller restart.
2. **v2/v3 false negative:** the `/cars/audit` endpoint returns only the last 60 lines, so a `len()>before` check can
   NEVER see a new decision once >60 exist. Fixed to detect a change in the LAST line.
- **RESULT — operation discrimination PROVEN:** same 5-tuple `.31->.20:502`, a Modbus READ (FC3) produced ALLOW + NO
  enforcement flow (client got register data), a WRITE (FC6) produced an audited `WRITE => BLOCK`/enforcement flow — the
  response decided by the function code alone. Two independent witnesses (controller audit line containing "WRITE" +
  the datapath P100 flow). A pure L3/L4 firewall cannot do this. (Also independently shown in e2e S2 READ->ALLOW /
  S3 WRITE->THROTTLE.)
- **Clean ladder run (final):** after forcing an auto-heal (only HARD_TIMEOUT resets the count; DELETE/restore does NOT),
  same 5-tuple `.31->.20:502` gave **READ(FC3)=>ALLOW, flow=none** and **WRITE(FC6)=>THROTTLE, flow=`meter:1,goto_table:2`**
  — discrimination proven live on the wire. BUT the ladder stayed at THROTTLE and did not reach BLOCK: writes #2 and #4
  gave NO-NEW-DECISION because **Snort did not alert on every single one-shot Modbus write** (PAF stream flush on small
  single requests is unreliable), so only 2 of 4 writes incremented the offense counter. This is a **detection-layer
  limitation (gap G3), NOT a CARS logic flaw** — the escalation logic is proven deterministically via the I2 API run
  (THROTTLE x3 -> BLOCK) and whenever the counter is saturated. It corroborates the DPI-brittleness already flagged in
  GAP_AND_NOVELTY G3. Reset mechanics: `_flow_removed` HARD_TIMEOUT resets conduit_state count; manual DELETE does not.
  Attacker S7->.10 is contained as FORBIDDEN/ISOLATE at TCP; deep S7 proto-id 0x72 detection is on the legit HMI loop
  (CRITICAL/REFUSE), not on the pre-empted attacker path.
- **Coverage gap acknowledged:** MTTM/stress/crosscheck lean generic (ICMP/TCP); the ICS-operation intelligence is proven
  by e2e + this trial, but a dedicated ICS-attack battery (malformed PDUs, illegal function codes, FC-scan, register
  write-storms, S7 job requests) would strengthen the "true ICS intelligence" evidence and is worth adding for the eval.

## CC-49 (2026-07-18): Phase-3 hard gap/fluff check + novelty -> GAP_AND_NOVELTY.md.
Rule-0 self-audit of the whole system. Full write-up in `GAP_AND_NOVELTY.md`. Headline conclusions:
- **System is real, honest, bounded** — strong hardware/cross-source/adversarial evidence base; gaps found were fixed or
  documented, not hidden.
- **8 gaps named (ranked).** Most serious = **G1: a compromised TRUSTED endpoint is a blind spot** — the safety cap
  (CRITICAL->REFUSE, never cut the loop) is also the attack surface; own it up front. Others: G2 conduit-granular
  enforcement vs operation-aware decision; G3 detection dependency + brittle DPI; G4 Modbus DPI validated on a SIMULATOR
  (S7 is real); G5 proactive default-deny fragile under NAT/shared-IP (CC-43); G6 single controller/IDS, scale+HA
  untested; G7 DEFLECT is low-interaction (decoy doesn't emulate Modbus/S7, eth_src not spoofed); G8 cross-host latency
  not independently clocked.
- **Fluff to fix (3, all wording):** (1) "provably safe" -> "empirically/demonstrably safe" (NO formal proof exists —
  biggest fluff risk); (2) sub-15ms MTTM is the ICMP/prompt-detect floor, not universal; (3) "operation-aware" =
  decision-level + S7-real/Modbus-sim, not enforcement-level.
- **Novelty (honest):** no single mechanism is new; the contribution is the SYNTHESIS under a safety discipline —
  unified reactive+proactive SDN response, criticality-graded + safety-capped (never cut the control loop) + bounded +
  reversible + evidence-generating, proven on real ICS hardware. **Biggest remaining write-up gap = an explicit
  related-work comparison vs the closest 3-5 SDN-ICS response papers** to quantify the delta.
- **Three actions to make the dissertation defensible:** (a) downgrade "provably"; (b) add the related-work novelty
  comparison; (c) precise language on decision-vs-enforcement granularity and simulator-vs-real scope.

## CC-48 (2026-07-18): Phase-2d multi-source cross-correlation — results are REAL, not printed (5/5 + neg control).
`cars_xcheck.sh` corroborated one attack event across five physically independent sources that cannot fabricate each
other, plus a legit negative control.
- **ATTACK (.66->.10 ICMP): 5/5 corroborated, causal order OK.** WIRE=3 frames (kernel capture); SNORT=+3 alerts (IDS
  process); AUDIT=+1 decision (controller on a DIFFERENT machine, Dell#2); OVSFLOW=BLOCK installed, datapath drops
  n_packets=2 (OVS kernel); OUTCOME=100% loss (client). Numbers self-consistent: 3 wire = 1 pre-block attack ping + 2
  post-block outcome pings; flow n_packets=2 = exactly those 2 dropped; enforcement installed 22 ms AFTER first packet
  on wire (t_install 511.489 > t_wire 511.467) — enforcement never precedes the attack.
- **LEGIT negative control (.31->.20 READ):** +1 ALLOW audit, 0 enforcement flows against the operator, client read
  [777,102,103,104] succeeded -> the system does NOT fabricate enforcement for benign traffic (no false positives).
- **Anti-hallucination significance:** a printed-but-unreal result would show a claim in one source with silence in the
  independent ones; instead all four subsystems (capture/IDS/controller/datapath) agree with correct causality. Every
  headline result in this project is now backed by cross-source physical evidence. Bundle: `cars_xcheck_20260718_230829`.

## CC-47 (2026-07-18): Phase-2c stress/adversarial trial — 8/8 invariant checks, safety loop never disrupted.
`cars_stress.sh`, 8 hostile scenarios back-to-back, SAFETY INVARIANT re-checked after each (HMI->PLC loop advancing +
controller 3-switch responsive + no legit conduit blocked). **Result: 8 passed / 0 failed.** The control loop climbed
uninterrupted 4032->4324 across the whole trial — the process was never disturbed under attack.
- **[1] STORM** 300-pkt flood -> single BLOCK, loop intact. **[2] SCANNER** 5-target spray -> per-source ISOLATE.
  **[3] LEGIT-UNDER-FIRE** operator Modbus READ returned [777,102,103,104] WHILE attacker flooded = ZERO collateral
  damage (the key safety result). **[4] MALFORMED** 60000B fragmented ICMP -> controller stayed up, loop intact.
  **[5] MULTI-CELL** reactive .10 ISOLATE + proactive .20 deny (25->26) in parallel. **[7] SPOOF** forged src=.9 dropped
  4/4 at Table-0 guard (dashboard: "4 spoofed packets dropped at ingress"). **[8] RECOVERY** 0 residual flows (all
  self-healed), legit read works -> RECOVERED CLEAN. CARS decide+enforce 0.013-0.819 ms throughout.
- **[6] IDS-DOWN inconclusive as first run (Rule 0):** counters `.10 deny 8->8`, `.20 deny 26->26` did NOT climb, so the
  "A2 still protects" label was wrong. Cause: residual ISOLATE (P110) from scenario 5 dropped the attacker's packets
  before they reached the A2 P55 deny flows — PLC stayed protected, but by a leftover REACTIVE flow, not A2. Re-tested
  cleanly (clear .66 reactive flows on all switches -> stop bridge -> attack): **PROVEN — ovs1 .10 deny 8->11 and ovsgw
  .20 deny 56->59, both +3 (the 3 pings / 3 TCP connects).** With detection fully offline and no leftover reactive flow,
  A2 proactive ALONE keeps the attacker off both PLCs; the real PLC .10 is caught by A2 on its HOME switch (ovs1) though
  the attack originated on ovsgw = cross-switch defense-in-depth. Scenario 6 closed.
- Bundle: `cars_stress_20260718_225754.tar.gz`. Harness fix: black-holed TCP connects to A2-denied .20 hung on the silent
  drop (no RST) -> wrapped in `timeout 1`. That silent-drop-hang is itself a write-up note (no info leak to the attacker).

## CC-46 (2026-07-18): Phase-2b MTTM — full autonomous mean-time-to-mitigate measured on hardware.
`cars_mttm.sh`, 15 autonomous trials, attacker `.66 -> .10` (ICMP), reactive detect->mitigate. All timing on Dell#1's
single clock (pcap `t_attack`; `t_enforce = t_poll - flow.duration`, skew-free), so no Dell#1/Dell#2 clock bias.
- **MTTM (attack-on-wire -> enforcement-flow-installed): mean 12.6 ms, median 11.9 ms, stdev 6.1 ms, min 8.3, max 34.9.**
  Trial 1 (34.9 ms) is a cold-start outlier (Snort/bridge/ARP warm-up); **steady-state (trials 2-15) mean ~11.0 ms,
  sigma ~1.5 ms** — tight. **0 timeouts / 15 -> 100% mitigation reliability.**
- **Key breakdown finding:** controller self-measured `decide+enforce` = **0.35-0.73 ms (~0.5 ms)** every trial, i.e. the
  CARS brain is only ~4% of MTTM. The remaining ~11 ms = Snort detect/flush + bridge poll + cross-host API RTT + flowmod
  install. **The SDN controller is NOT the bottleneck** — CARS adds sub-millisecond decision cost on top of the IDS.
  Defensible thesis framing: response latency is bounded by detection/signaling, not by the trust brain.
- **Honest caveat:** this is the ICMP (single-packet-detectable) floor. Stream-reassembled attacks (TCP/Modbus) carry
  higher Snort PAF flush latency; those to the PLCs are pre-empted by A2 anyway. So 11 ms = reactive floor for a promptly
  detectable threat, not a universal constant. Response type mix: 1 BLOCK then 14 ISOLATE (per-source offense accumulates
  across trials without reset; timing is the same mechanism). Bundle: `mttm_20260718_224129/` (per-trial pcaps + csv).
- **Reversibility (measured):** a triggered BLOCK carried `hard_timeout=30s` and auto-removed after ~27s (poll t0 was
  ~3s post-install) with no operator action — bounded + self-healing on all 3 switches. Response was BLOCK not ISOLATE,
  proving per-source offense was FORGIVEN after the earlier ISOLATEs healed. Confirms the "provably safe: bounded,
  reversible" thesis property end-to-end (detect -> decide -> enforce -> auto-heal -> forgive).
- Belongs in the Evaluation chapter (latency subsection) alongside the Phase-2a spectrum proof.

## CC-45 (2026-07-18): DEFLECT round-trip deception — FIXED and proven attacker-side (resolves CC-44 Finding 3).
The Phase-2a trace showed DEFLECT's return leg was broken (attacker never received the spoofed reply). Fixed properly
(Amit chose "fix it now") in three stacked corrections, each verified before the next:
1. **hpotns return path (post-reboot regression):** `rp_filter=2`->0 + `ip route add 192.168.2.0/24 dev hpot`, so the
   decoy stops dropping the `.2.0/24`-sourced probe and actually replies. Persisted into `cars-hpot.sh` step 5.
2. **table-2 punt:** the reverse P105 flow did `set_field:ip_src=.10 -> goto_table:2`; table 2 had no learned flow for
   the attacker MAC so it punted to the controller and died. Changed `deflect_conduit` to look up the attacker's host
   record (`_host_on`) and `output:<attacker_port>` DIRECTLY instead of goto_table:2. Reply then reached the `atk` NIC —
   but as `PACKET_OTHERHOST` (kernel-dropped before the socket).
3. **eth_dst mismatch:** the decoy's reply carried the wrong L2 dst. Added `set_field:eth_dst=<attacker_mac>` to the
   reverse flow (MAC from the same host lookup). 
**PROVEN:** attacker `ping .10` -> `64 bytes from 192.168.2.10 ttl=64 ... 3 received, 0% packet loss` while every packet
actually hit the decoy `.3.99`. Reverse flow: `set_field:192.168.2.10->ip_src,set_field:02:00:00:00:02:66->eth_dst,
output:11`. DEFLECT is now full interactive deception: divert + decoy engages + attacker believes the PLC answered,
real PLC untouched. Master + Dell#2 + cars-hpot.sh updated. (Cosmetic hardening left as future work: also spoof
`eth_src=<PLC_mac>` so a MAC-savvy attacker can't distinguish the decoy — not needed for the deception to function.)

## CC-44 (2026-07-18): Phase-2a deep end-to-end trial — full spectrum through the real chain + 2 attribution findings.
`cars_e2e.sh` drove the whole response spectrum on the clean baseline with 4-layer proof (wire pcap | Snort | audit |
OVS counter | client outcome) + per-decision latency. **Cleanly proven end-to-end:** S2 OPERATIONAL->ALLOW (Snort+1,
P60 0->6, client read [777,102,103,104]); S3 SENSITIVE->THROTTLE (P100 meter 0->6, write still delivered); S4b
per-source escalation (offense 1/2/3 BLOCK, 4 ISOLATE, real P110 src-drop flow); S6 A2 proactive deny (deny .20 2->4,
Snort unchanged, no audit = silent prevention); S1 loop CRITICAL->REFUSE while ovs1 loop-allow climbed 2405->2416.
CARS decide+enforce latency **0.012–1.333 ms** across all decisions.
- **Finding 1 (defense-in-depth, not a fault):** S4a (attacker->.20 WRITE) showed Snort+0 / block-flow 0->0 yet connect
  FAILED — because `.20` is under A2 proactive default-deny, so the SYNs were dropped at P55 *before* detection (that's
  S6's inherited deny count of 2). **Proactive pre-empts reactive** — as designed. Consequence: attacker->Modbus-PLC does
  not isolate the reactive autonomous BLOCK; that chain is proven separately (A3 forensics + explicit-call dashboard).
  To demo the reactive path in isolation, target a dst NOT under A2 default-deny.
- **Finding 2 (priority order working, test mis-ordered):** S5 DEFLECT installed the correct P105 setfield flow
  (eth_dst->02:00:00:00:03:99, ip_dst->192.168.3.99) but the decoy ping showed 100% loss — because S4b had ISOLATEd
  `.66` (P110), which outranks DEFLECT (P105 < P110). The quarantine ate the ping. Fix: deflect a NON-isolated source
  (bridge off + clear the isolate) exposed a DEEPER, real finding via ofproto/trace (see Finding 3). Lesson for Phase 2c
  ordering: DEFLECT and ISOLATE on the same source are mutually exclusive by priority; sequence tests accordingly.
- **Finding 3 (DEFLECT return-leg limitation — corrects the record):** DEFLECT's forward-diversion + decoy engagement
  are FULLY PROVEN (forward P105 n_packets=3, decoy netns receives the rewritten `.3.99` packets and REPLIES; reverse
  P105 n_packets=3, `ip_src` rewritten back to `.10`). BUT the spoofed reply NEVER reaches the attacker's NIC (0 inbound
  frames on `atk`). ofproto/trace root cause: after the reverse `set_field:ip_src=.10 -> goto_table:2`, table 2 has no
  learned flow for the attacker MAC, so it punts to CONTROLLER (priority-0 miss); the L2 packet-in/out path does not put
  the rewritten packet back on the attacker port. Also needed a post-reboot netns fix (hpotns `rp_filter=2`->0 + route to
  `.2.0/24`) just to make the decoy reply at all. **Record correction:** the earlier "ttl=64 deception worked" was the
  DECOY replying observed AT THE HONEYPOT, not confirmed at the attacker. Net: DEFLECT's defensive value (divert attacker
  off the real PLC + engage a decoy for intel/delay) is proven; the attacker-facing round-trip deception is NOT delivered
  and is a genuine pipeline limitation. Fix option = reverse flow `output:<attacker_port>` directly instead of
  `goto_table:2`; alt = document as known limitation / future work.
- **Wire cross-check:** operator->mbplc 24 frames, attacker->mbplc 4 (denied SYNs), modbus/502 28; hmi->plc loop 0 on the
  mirror because the loop rides ovs1 (physical ports) not the ovsgw snort0 mirror — loop proof is the ovs1 counter+audit.
- Bundle: `cars_e2e_20260718_213157.tar.gz`. Both findings are attribution/ordering, not capability gaps.

## CC-43 (2026-07-18): Testbed audit finding — A2 default-deny x NAT x shared-IP broke Cell-2. Per-switch scoping fix.
The Phase-1 deep testbed audit flagged Cell-2 (`.3.10`) unreachable. Two of my hypotheses were WRONG and I corrected them
with evidence (Rule 0): (1) "ICMP-silent PLC" — disproved when S7/TCP-102 also failed; (2) "faulted PLC" — disproved when
removing one OpenFlow rule made it instantly reachable. **Real root cause:** A2-P2's `.2.10` default-deny installs on
EVERY switch (`install_allowlist` runs per switch-connect), including **ovs2 (Cell-2)** — because `.2.10` is a SHARED IP
(PLC1@ovs1 AND PLC2@ovs2). Cell-2's PLC2 is reached via Dell#3 NAT, which `MASQUERADE`s the source to `cell2gw .2.1`;
that source isn't in the allowlist, so the NAT path hits the `.2.10` deny and is dropped. ARP still passed (not IP),
so the box looked alive at L2 but dead at S7 — misleading. Proof: `ovs2` deny counter climbing (16) + `.2.9->.2.10`
allow at 13562 pkts (Cell-2's own loop fine); deleting the deny -> `PLC2 S7 ALIVE`.
- **Insight (dissertation-grade):** source-based *proactive* default-deny **cannot see through NAT** — MASQUERADE hides
  the real source, so behind a NAT the gateway path must be allowlisted or the PLC becomes unreachable. Combined with a
  duplicate PLC IP across cells, a per-cell policy leaks onto the other cell. This is a real limitation of A2, not a bug
  in the idea; it argues for either de-NAT'd visibility (see the true source) or per-segment policy scoping.
- **Fix:** `DEFAULT_DENY_DSTS` (list) -> `DEFAULT_DENY` (list of `(dpid|None, ip)`); `install_allowlist` installs each deny
  only on its scoped switch. So `.2.20` denies on all switches; `.2.10` denies on **ovs1 (dpid 1) only** — A2-P2's real-PLC
  protection preserved on Cell-1, Cell-2 NAT path freed. Master + Dell#2.
- **Also:** the audit's transit check used ICMP against a PLC that ignores ping even when healthy — will switch the audit
  probe to TCP/102. And the flag was ALSO CARS correctly blocking `ins2 (.3.66) -> .3.10` (an unknown source) — expected.
- **Testbed otherwise proven sound:** Cell-1 (real PLC1/HMI1, live loop, bindings match physical MACs), Modbus cell,
  ovs2 on Dell#3, transit link (ttl=64 both ways), NAT config, mirror select_all, all services/netns, Snort, controller.

## CC-11 (archived note)
ess MikroTik bypassed/VLAN'd). **Costs:** more complexity + extra latency hops (worse CC-4). **Verdict:** the right tool for the **zone-building phase** (multi-switch + Purdue zones, already in Tier 3 plan), best for inter-zone/attacker traffic; keep real boxes' intra-box loops on directly-wired OVS. Parked as stretch. **Meta:** topology ≠ contribution; build CARS engine first, dress topology later.

**Network-topology options explored (summary):** (A) single native OVS on Dell#1, direct-wired devices — CURRENT, simplest, keeps intra-box control ✓ recommended for build. (B) MikroTik-as-OVS per box — INFEASIBLE (SMIPS: no OVS, no containers). (C) GNS3 2×OVS via MikroTik gateways — feasible, for zone phase, loses intra-box control. → **Use A now; C later for zones/realism.**

- **CC-10 (evaluated & parked 2026-07-06):** Idea — make each teaching box's MikroTik an OVS/OpenFlow switch, forming a multi-switch fabric to the laptop OVS. **Verdict: not feasible on the hEX lite.** OVS cannot be installed on RouterOS (closed OS, no package); RouterOS containers (only way to run OVS) require ARM/x86, but **hEX lite = SMIPS → no containers**. Native RouterOS OpenFlow is v6-only/experimental/SMIPS-unconfirmed and likely lacks mirror/redirect. **Concept is sound (distributed edge SDN enforcement; os-ken already supports multi-datapath)** — realise later, if wanted, via **Raspberry Pi 4 (ARM) running OVS per box**, the 2nd Dell as a 2nd OVS, or GNS3 emulated switches. Parked as stretch/future-work; single OVS fully suffices for the CARS contribution.
- **CC-9 (noted 2026-07-06):** Laptop-as-OVS port count (Dell#1 = 3 Eth ports) is an *emulation* limit, not an SDN/CARS limit — a 2-port OVS is a valid OpenFlow switch. Scaling: (a) **MikroTik as VLAN-trunk aggregation** (many OT devices → 1 trunk → 1 OVS port; MikroTik used as plain VLAN switch, OpenFlow irrelevant); (b) zone devices (DMZ/corp/IDS/attacker/firewalls) are VMs/containers on **internal** OVS ports (no physical ports). **Real caveat = data-path latency/jitter** from laptop kernel + USB-Eth: makes CC-4 numbers conservative/worst-case → measure and state explicitly (if timing holds here, holds on real hardware).
- **CC-8 (RESOLVED 2026-07-06):** Controller = **os-ken 2.8.1** (maintained Ryu fork) in venv `~/cars/venv`, verified on Ubuntu 24.04 / Python 3.12. Ryu dropped (EOL). CARS apps use `os_ken.*` API (near-identical to Ryu). All "Ryu" references now mean **os-ken**.
- **CC-6 (RESOLVED 2026-07-05):** SDN switch = **Open vSwitch on Dell #1** (full OpenFlow 1.3). MikroTik hEX lite = physical zone switch only (its OpenFlow is experimental/v6, not trusted for the critical path).
- **CC-7 (RESOLVED 2026-07-05):** L0 process = **real PLC I/O (LEDs/relays)**. **Factory I/O dropped** — no longer needed. Frees Dell #2 from Windows/GPU duty.
- **CC-5 (RESOLVED 2026-07-05):** Verified every web-sourced citation — **0 fabrications**; all 28 items real. Metadata corrections + 2 residuals (CHAOS ID, NIST → Rev. 3) recorded in `VERIFICATION_REPORT.md`. Local papers already verified. Re-check the 2 residuals + any *new* sources at cite-time.
