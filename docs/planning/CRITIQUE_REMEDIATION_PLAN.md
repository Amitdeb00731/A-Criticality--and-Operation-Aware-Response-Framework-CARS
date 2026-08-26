# Peer-Review Critique Remediation Plan

Source: `All technical critiques.docx` (expert peer-reviewer dissection, section by section).
Method: every critique was read in full and checked against the actual report source before this plan was written. Nothing below is applied yet.

## Governing guardrail (REPORT_PLAN rules 1, 2, 9, 10)
The critique document supplies "Defensive Pivots" that sometimes assert mitigations we did **not** build (remediation-agent network-namespace isolation, HMAC-signed `/cars/respond`, netlink-conntrack RST synthesis, host integrity monitors). We do **not** import any of these as if implemented. Where a boundary is real, the report's existing posture stands: state the boundary honestly and carry the remedy as future work. Every added sentence must be true to what was actually built and, where it states a fact (versions, counts, capture numbers), must be confirmed on the device or from a source, never guessed.

## Verdict up front
The report already carries, as documented boundaries in `sec:threats`, `sec:evallongrun`, `sec:evaldpi`, `sec:controlplane` and the appendix, the large majority of the "loopholes": management-plane isolation (so the `/cars/respond` forgery and plaintext-OpenFlow critiques are bounded), the S7 six-slot socket-exhaustion finding with the TCP-reset remedy as future work, the conntrack correctly-sequenced-injection limit, encrypted-protocol blindness (S7CommPlus/OPC UA/CIP Security), the Cell-2 single-sensor blind spot, the NAT-collapse conduit-BLOCK downgrade, the 10 s poll gap closed by the event-driven monitor, flow-table saturation to 94k, the 20 s controller-reconnect stall, the trusted remediation-agent exposure, the slow-in-envelope FDI that evades guardian and agent, and the first-packet / atomic-STOP residual (with a dedicated figure). The class-imbalance point is already framed honestly and the Wilson interval it attacks was already removed. So this is not a rewrite. It is a set of surgical strengthenings plus a few genuine gaps.

---

## Tier A — Factual precision and internal consistency (must fix; some need Amit's confirmation)

A1. **"Two PLCs driving the physical process" (Supporting Technologies).** Only PLC1 drives the HIL tank; PLC2 is the second-cell controller used to validate the cross-cell / NAT-clone identity scheme. Reword to say exactly that. *Confirm PLC2's model (1211C/1212C) and that it drives no physical process.*

A2. **Software versions absent (Supporting Technologies) — reproducibility gap.** Add real versions:
   - Snort **2.9.x** — safely derivable now: the deployed `cars.conf` uses `stream5_global` / `stream5_tcp`, which is Snort 2.9 syntax (Snort 3 uses Lua `stream_tcp`). State "Snort 2.9" and, if Amit can read the exact build, the point release.
   - Open vSwitch **3.3.4** — already in the Fig 3.6 caption; surface it into the inventory too.
   - os-ken, TIA Portal, Factory IO versions — **need Amit** (`pip show os-ken` on the controller; TIA Portal and Factory IO "About" dialogs). Do not guess.

A3. **HMI count mismatch.** Supporting Technologies lists one KTP700 (singular); §3.7.1 says "an operator HMI on each cell" and the evaluation lists HMI1 and HMI2 as separate assets. **Need Amit:** is there one physical KTP700 panel or two? If one physical panel plus a soft/second-cell HMI endpoint, say so precisely. Fix the inventory to match reality either way (rule 2).

A4. **"Zero writes reached the PLC" vs "one frame (1374) reached the PLC port."** The packet proof (`sec:evalanatomy`, lines ~241, 257) honestly reports eight write attempts at the mirror and one frame at the PLC port; the process-devastation passage (line ~305) says "zero writes reached the PLC." Reconcile to the committed-vs-transport distinction and confirm which run each sentence describes. If they are the same run, change "zero writes reached the PLC" to "zero writes committed" (one transport frame leaked, absorbed by inertia); if different runs, name them so the reader is not left with an apparent contradiction. *Verify against the two captures before editing (rule 10).*

---

## Tier B — Terminology sharpening (high value, low risk)

B1. **"Hardware testbed rather than a simulation" (Abstract ¶2, Intro §1.1).** The HIL nuance is fully explained later in `sec:threats`, but the headline invites the "your process is 100% simulated" trap on first read. Qualify at first use: the controllers, operator panel and SDN fabric are physical hardware running real S7comm and Modbus/TCP; the tank fluid dynamics are a high-fidelity co-simulation in Factory IO (a hardware-in-the-loop testbed), chosen to avoid laboratory water hazards. Frame per Gardiner et al.'s testbed principles (already cited).

B2. **"Response ladder bounded in time and reversible."** Add half a sentence: the temporal bound and self-heal apply to the active network-enforcement rungs (the cookie-`0x00ca` flow-mods); REFUSE is a static, non-enforcement safety-invariant (alert-only on the operator loop), so it is deliberately outside the timeout, not an exception to it.

B3. **%ID/%QD "double-word".** Note that although `%ID100`/`%QD100` are 32-bit double-word addresses, they carry REAL (IEEE-754 single-precision) values on this process, not DINT/DWORD integers, so no SCALE/NORM_X normalisation is used. One clause in Background §2.1 or the Notation page.

---

## Tier C — Notation and Acronyms additions (easy, high value)

C1. Add the OT/protocol acronyms that already appear in the body and appendix but are undefined: **PDU, TPKT, COTP, MBAP, DPID** (and optionally REAL / IEEE-754). All are genuinely used; defining them aids the reviewer and demonstrates protocol fluency.

---

## Tier D — Threats-to-validity, genuine gaps to add (short, honest)

D1. **Layer-2 industrial protocols out of scope.** CARS scopes its operation-aware layer to IP-based ICS protocols (S7comm, Modbus/TCP). Non-IP real-time protocols carried directly over Ethernet (PROFINET RT, IEC 61850 GOOSE and Sampled Values) fall through the IP-scoped default-deny to L2 forwarding and are not operation-gated. State this as an explicit scope boundary (one or two sentences). The report currently mentions PROFINET only as controller processing jitter, not as a coverage boundary.

D2. **Sensor parser fragility (COTP length, Modbus offset).** Fold into the existing sensor-coverage limit: the S7 rules anchor on the `32 01` job header assuming the usual 3-byte COTP, and the Modbus rules read the function code at the standard MBAP offset; a non-standard COTP length or a Modbus-in-tunnel wrapper shifts the field and degrades recovery to the stateless five-tuple layer. This is the same class as the fragmentation/overlapping-segment residue already acknowledged; one honest sentence extends it to header-shift evasions.

D3. **(Optional) Same-source timing race / concurrent-role.** Brief note that a source-scoped isolate cuts a compromised source's legitimate and malicious operations alike (correct, since the source is compromised), and that shared-identity cases are handled by the conduit-BLOCK downgrade; a fine-grained same-millisecond read/write race on a single identity was not separately tested. Low priority; include only if it reads naturally.

---

## Tier E — Already covered; verify signposting only (little or no text change)
`/cars/respond` forgery, plaintext OpenFlow + management-plane isolation, socket exhaustion + TCP-reset future work, conntrack sequenced-injection, encrypted protocols, Cell-2 sensor blind spot, NAT-collapse BLOCK, poll-gap → event monitor, flow-table saturation, 20 s reconnect stall, trusted remediation agent, slow-in-envelope FDI, first-packet/STOP residual, class imbalance (+ transparency campaign), cookie-masking (bounded by the "knows the defence's own internal markings" clause). Action: read each cross-reference once during execution; add a pointer sentence only where a reviewer could plausibly miss the link. No new claims.

Optional academic strengthener: a short, declared "Scope and assumptions" pointer early in Ch3 that names the main boundaries and forward-references `sec:threats`, so the boundaries are seen as declared rather than found only at the end. Include only if it does not duplicate content.

---

## Needs Amit before those specific edits
1. PLC2 exact model and confirmation it drives no physical process (A1).
2. os-ken version (`pip show os-ken`), TIA Portal version, Factory IO version (A2).
3. HMI: one physical KTP700 or two panels; nature of HMI2 (A3).
4. Confirmation of which run the "zero writes" sentence describes, checked against the two pcaps (A4).

## Execution order (once approved and facts supplied)
1. Tier C and B3 (notation) — self-contained, no dependencies.
2. Tier B1/B2 (abstract + intro terminology).
3. Tier A1–A4 (inventory + versions + write-count reconciliation) once Amit's facts are in.
4. Tier D1–D2 (threats additions).
5. Tier E signpost pass.
6. Rebuild, verify: no undefined refs, no new AI-tells or em dashes (rule 2/3), page count and floats clean, and a final read of the changed sections against REPORT_PLAN rules 1, 2, 9, 10.

## Risk note
All Tier B/C/D edits are additive prose in the honest register the report already uses. The only edits that can change a factual claim are Tier A; those are gated on Amit's confirmation so nothing is asserted that was not measured or read from the device.
