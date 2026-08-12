# Project CARS — Hard Gap / Fluff Check + Novelty (Phase 3)

_Written 2026-07-18 under Rule 0 (question everything, no fluff, name every gap). Purpose: state honestly what CARS
has proven, where it is weak, which claims are thin, and what — if anything — is genuinely novel. This is the document
an examiner should not be able to out-skeptic._

---

## 1. Evidence base — what is actually proven (on hardware, cross-corroborated)

Not asserted — measured, and in Phase 2d corroborated across physically independent sources (kernel capture, Snort,
the controller on a separate machine, OVS datapath counters, client outcome):

- **Full response spectrum at packet/datapath level** (Phase 2a): ALLOW, MONITOR, THROTTLE (meter), DEFLECT (now full
  round-trip deception), ISOLATE (per-source), BLOCK, REFUSE (CRITICAL loop). Each with 4-layer proof.
- **Autonomous MTTM** (Phase 2b): mean 12.6 ms / steady-state ~11 ms, **0 timeouts over 15 trials**; CARS's own
  decide+enforce ~0.5 ms (≈4% of MTTM). Reversibility measured: bounded `hard_timeout=30s`, auto-heals, source forgiven.
- **Stress/adversarial** (Phase 2c): 8/8 invariant checks, the HMI→PLC control loop **never disrupted** (4032→4324)
  under flood, scanner, malformed frames, multi-cell, live spoofing; legit traffic survived under fire (zero collateral);
  IDS-offline defense-in-depth proven (A2 alone protects both PLCs, real PLC caught on its home switch).
- **Anti-hallucination** (Phase 2d): attack event 5/5 corroborated with correct causality (enforcement 22 ms AFTER the
  packet hit the wire, never before); legit event ALLOWED with zero fabricated enforcement.

This is a solid, honest empirical base. The gaps below do not undermine it — they bound what it means.

---

## 2. Hard gap analysis (ranked by how hard an examiner would press)

**G1 — A compromised *trusted* host is a blind spot, and the safety invariant is itself the attack surface. [most serious]**
CARS's central safety rule is CRITICAL (HMI↔PLC) → REFUSE: never cut the control loop. But that means an attacker who
*compromises a legitimately-bound endpoint* (takes over the HMI) and attacks the PLC over the trusted conduit is, by
design, **not enforced against** — CARS refuses to touch that conduit. Trust is bound by IP/MAC/port (GUARD), so
identity-spoofing is stopped, but endpoint *compromise* is not. The very invariant that makes automated response safe
(don't break the process) is the hole. Honest position: CARS defends the *network boundary and conduit semantics*, not
the integrity of trusted endpoints — that needs host-based defenses (out of scope) or an operation-level policy even on
trusted conduits (A3 partially does this: a trusted WRITE escalates — but CRITICAL is still capped at REFUSE).

**G2 — Enforcement is conduit-granular; the "operation-aware" response still cuts the whole conduit.**
A3 *detects* the operation (Modbus FC / S7 session) but OpenFlow enforces at L3/L4, so a THROTTLE/BLOCK on a bad WRITE
throttles/cuts *all* of that source's traffic to the target, not just writes. So "operation-aware response" is
operation-aware in the DECISION, conduit-level in the ENFORCEMENT. Not dishonest, but must be stated precisely.

**G3 — Detection dependency + brittle DPI (now quantified).** CARS is a *response* system; it is only as good as the IDS.
The Modbus/S7 DPI is Snort content rules on specific bytes (FC at offset 7; S7 proto-id 0x72), and getting them to fire
required `checksum_mode:none` and stateless rules (stream flush issues). Fragmentation, encryption, or a novel attack
that Snort misses → CARS never triggers. **Measured weakness (CC-52):** a *single one-shot* Modbus request is not
reliably flushed by Snort's PAF — in the ICS attack battery the FC43 PROGRAM op was MISSED on the single attempt and only
detected when repeated (`--count 4`). So a lone dangerous packet can evade the reactive layer some fraction of the time;
mitigations = Snort stream/rule tuning or the modbus preprocessor. A2 proactive still bounds unauthorized *sources*
regardless of detection — but cannot cover malicious *operations* from authorized sources that evade DPI.
**Upside (CC-52):** the operation-aware layer is now broad — READ/WRITE plus CONTROL(coil-force)/DIAG(restart)/
PROGRAM(FC43)/ILLEGAL(FC>43), with dangerous ops FORBIDDEN even from a trusted source, and repeated dangerous ops
escalating to source ISOLATE. This materially strengthens the "operation-aware, not 5-tuple" novelty claim.

**G4 — The Modbus operation-awareness was validated against a SIMULATOR, not a real Modbus PLC.** S7 session detection
and the control loop use the real Siemens hardware; the Modbus function-code intelligence (.20) is a pymodbus sim. So
"operation-aware DPI on real ICS hardware" is true for S7, simulated for Modbus function-code detail. State this.

**G5 — Proactive default-deny is fragile in complex topologies (CC-43).** It cannot see through NAT (MASQUERADE hides
the real source) and shared IPs across cells require per-segment scoping. Found and fixed here, but it shows the
approach needs careful per-topology policy engineering; a naive global allowlist breaks legitimate NAT'd paths.

**G6 — Single controller / single IDS; HA and scale untested.** One controller (SPOF — though data-plane flows persist
on failure until timeout), one Snort. Tested at 3 switches / ~handful of hosts / 2 cells. Plant-scale (hundreds of
devices), high concurrent multi-attacker load, and controller failover are **not** evaluated.

**G7 — DEFLECT is low-interaction deception.** The decoy answers ICMP via the kernel; it does not emulate a Modbus/S7
PLC stack, so an attacker who speaks Modbus/S7 to it finds a hollow shell. And `eth_src` is still the honeypot MAC (not
spoofed to the PLC's), so a MAC-aware attacker can distinguish the decoy. Good for diversion + basic intel/delay; not a
convincing high-interaction honeypot.

**G8 — Cross-host decision latency not independently measured.** MTTM is single-clock (Dell#1) to avoid Dell#1↔Dell#2
skew; the controller's contribution is its own `perf_counter` (~0.5 ms), not an externally-clocked cross-host figure.

---

## 3. Fluff audit — claims to downgrade or qualify

- **"Provably safe" → "empirically/demonstrably safe with bounded, reversible responses."** There is NO formal proof or
  model-checking. The safety is shown by many trials with zero process disruption + bounded/reversible enforcement — that
  is strong *empirical* evidence, not a *proof*. Using "provably" without a formal artifact is the biggest fluff risk in
  the whole project. Downgrade the word everywhere unless a formal model is added.
- **"Trust brain" is a rule-based first-match classifier**, not learning/AI. Keep the name if useful, but never imply
  machine intelligence.
- **"Sub-15 ms mitigation"** is real but for a *promptly detectable* (ICMP/single-packet) attack; stream-reassembled
  attacks carry higher detection latency. Always attach the caveat.
- **"Operation-aware"** — real for S7, simulator for Modbus function-code detail; decision-level not enforcement-level
  (see G2/G4).

None of these are fatal; all are fixable by precise wording. Left unqualified, each is an examiner entry point.

---

## 4. Novelty — honest separation of new vs synthesis vs engineering

**Not individually novel:** SDN/OpenFlow ACLs; IDS→SDN automated response; honeypot redirection; Modbus/S7 Snort DPI;
default-deny allowlisting. All exist in the literature and in products.

**The genuine contribution is the *synthesis under a safety discipline for OT*:** a single framework that couples
**reactive** (detection-driven) and **proactive** (pre-installed default-deny) SDN response, where responses are
**criticality-graded and safety-capped** — an explicit spectrum (ALLOW·MONITOR·THROTTLE·DEFLECT·ISOLATE·BLOCK·REFUSE)
whose selection is decoupled from the trust decision, hard-capped so the safety-critical control loop is **never**
enforced (REFUSE), and every response is **bounded, reversible (self-healing), and evidence-generating**. The thesis
value proposition — "automated network response for OT you can *actually turn on*, because it provably-in-practice will
not break the physical process" — is the novel framing, and it is backed by hardware evidence that the process loop
survives every response and every stress scenario.

**What an examiner will rightly probe:** "Which single element is new?" Honest answer: no single mechanism; the
contribution is the *integrated, safety-capped, criticality-aware reactive+proactive response model, demonstrated
end-to-end on real ICS hardware with measured bounded/reversible enforcement and cross-source verification.* If prior
SDN-ICS response work already grades responses by asset criticality AND caps them with a never-cut-the-loop safety
invariant AND unifies proactive+reactive AND proves reversibility on hardware, the delta shrinks — a focused related-work
comparison against the closest 3–5 papers is REQUIRED to defend the novelty and is the current biggest write-up gap.

---

## 5. Threat model — what CARS assumes and cannot defend

- **Assumes:** a trustworthy IDS feed; correct static host/role bindings; an uncompromised controller and OVS; the
  attacker is on the network but has NOT compromised a trusted endpoint; policy authored correctly per segment.
- **Defends:** unauthorized sources reaching PLCs (proactive, even IDS-down); detectable malicious operations from
  untrusted sources (reactive, ~11 ms); identity spoofing (GUARD); scanning (per-source ISOLATE); and does so without
  disrupting the process or legit traffic, reversibly.
- **Does NOT defend:** compromised trusted endpoints attacking over CRITICAL conduits (G1); DPI-evading operations from
  authorized sources (G3); host/firmware-level attacks; supply-chain; physical access; anything the IDS cannot see.

---

## 6. The examiner's five hardest questions (and the honest answers)

1. *"Is it actually novel or just integration?"* → Integration under a safety discipline is the contribution; needs the
   related-work comparison (§4) to quantify the delta. **[open write-up task]**
2. *"You say provably safe — where's the proof?"* → It's empirical, not formal. Reword, or add a model. (§3)
3. *"A compromised HMI walks right through."* → Correct; by design (safety cap). Out-of-scope boundary, stated. (G1)
4. *"Your Modbus intelligence is a simulator."* → True for function-code detail; S7 is real hardware. (G4)
5. *"Does it scale / survive controller loss?"* → Untested beyond the 3-switch testbed. Named as future work. (G6)

---

## 7. Verdict

The system is **real, honest, and does what it claims within a clearly bounded threat model**, with an unusually strong
empirical evidence base (hardware, cross-source, adversarial, reversibility-checked). The engineering is sound and the
gaps found were fixed or documented, not hidden. The remaining risks to the *dissertation* are not in the system but in
the *framing*: (a) the word "provably" (downgrade to empirical), (b) an explicit related-work novelty comparison, and
(c) precise language on operation-aware *decision* vs conduit-level *enforcement* and simulator-vs-real scope. Close
those three and the contribution stands on defensible ground. The one architectural gap worth stating up front rather
than defending under fire is G1 (compromised trusted endpoint) — owning it is stronger than hoping it isn't asked.
