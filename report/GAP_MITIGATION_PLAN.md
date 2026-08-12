# Gap-mitigation lab plan (defence-in-depth): DPI reassembly + process guardian

Governing rules: verify on device (R9), implement then test **fresh** and capture before writing (R10), capture the vital proof and signpost the rest (R11), keep every claim traceable (R1), and reverse every attack to a safe state.

Framing that both results serve (already agreed): the **proactive layer** (identity binding, allowlist, default-deny, conntrack) needs no sensor and drops every unregistered or spoofed source with a zero-millisecond reaction window (proven by the two pivots). So both weaknesses reduce to the **same** residual — a *trusted, already-allowlisted insider doing something dangerous* — and the correct architecture is defence-in-depth: the network layer must not cut the CRITICAL safety loop, so a **process layer** takes responsibility for application-level insider harm.

Pre-flight (both workstreams):
- Recall the stable baseline (LAB_VERIFY.md / verified_config.md); green-light the fabric; CARS armed.
- Dashboard up; the 4-pane cascade (Snort alert / bridge / brain audit / flow watch) open.
- `source ~/cars_campaign_lib.sh`; set `CAMP`, `PLCIF`.
- **Back up before editing:** copy `cars.rules` + `snort.conf`, and `cars_remediation.py`, so both changes are revertible.

---

## Workstream A — Gap 2: DPI stream-reassembly hardening (do first; lower risk)

Objective: recover the ICS operation even when the S7/Modbus PDU is fragmented across TCP segments, so a fragmented dangerous op on an allowlisted conduit is still classified and forbidden.

1. **Prove the gap fresh (baseline).** From the allowlisted conduit (`.2.31 -> .2.10`, armed), send a dangerous S7 write / Modbus FC with the PDU **fragmented across TCP segments** (scapy with small segments, or an MSS clamp, or `send` in pieces). Capture: Snort alert (expect **silent**), controller audit (expect **no FORBIDDEN**), `plc1_wire.pcap` (expect the write **reaches** the PLC). This is the fresh evidence of the weakness.
2. **Harden.** Enable Snort TCP **stream reassembly** (`stream` preprocessor, target-based, ports 102/502) with `flow:established`; re-anchor the ICS rules in `cars.rules` to the **TPKT/MBAP length field** using `byte_test`/`byte_jump` instead of absolute offsets, so the function code is found in the reassembled stream. Reload Snort. Fallback if S7 PAF is unreliable: add lightweight **reassembly in `snort_bridge.py`** (read the TPKT length at offset 2-3, buffer until the full PDU, then classify); stronger option: Suricata Modbus app-layer / Zeek+ICSNPP S7comm parser.
3. **Re-test fresh (after).** Same fragmented attack -> Snort now alerts on the reassembled PDU -> bridge recovers the op -> CARS FORBIDS -> write blocked. Capture the same four layers showing the catch.
4. **Evidence:** a small before/after table (fragmented attack: evaded vs caught) at Snort / bridge / controller / wire.
5. **Residual (state honestly):** reassembly defeats naive fragmentation; overlapping-segment and timing evasions remain an IDS arms race; single-frame stealth on a rare FC is still hard.
6. **Lands in:** §4.5.1 upgraded from "acknowledged gap" to "gap + implemented hardening, before/after"; Threats softened accordingly.

Post: re-baseline the flow-integrity checker if any static flow changed; re-arm; revert Snort config if the result is inconclusive.

---

## Workstream B — Gap 1: process safety-envelope guardian (defence-in-depth)

Objective: a process-layer monitor that catches a trusted/allowlisted insider driving the process **outside its physical safe envelope**, raises a FORBIDDEN-class alarm, and clamps to safe via the allowlisted remediation conduit, while the network layer (correctly) never cuts the CRITICAL loop.

1. **Prove the gap fresh (baseline).** From a trusted allowlisted role on the setpoint path (EWS `.2.55` or the HMI loop), issue an *authorised* S7 write that drives the tank out of its safe band. Armed. Capture: controller audit (expect **ALLOW / REFUSE monitor-only**, i.e., not cut), the tank level crossing the safety band, the HMI. Fresh evidence of the blind spot.
2. **Build the guardian** (extend `cars_remediation.py`, which already flags "a level the bang-bang law cannot produce", or a new `cars_process_guardian.py`):
   - read level **and** commanded setpoint/output over S7 (read-mostly);
   - hold a safety envelope `[safe_lo, safe_hi]` from the process spec plus the existing rate-of-change / last-good check;
   - on breach: emit a FORBIDDEN-class **process-anomaly event** into the controller decision log (so it appears on the dashboard) and **clamp/restore** to a safe value via the allowlisted remediation conduit;
   - keep it **narrow**: read-mostly, clamp authority limited to safe-band restoration, so compromising the guardian is not an arbitrary-write single point of trust (addresses the trusted-agent worry).
3. **Re-test fresh (after).** Same malicious insider setpoint -> guardian detects the envelope breach -> alarms + clamps -> process held in band although the network layer left the loop untouched. Capture the alarm (audit/dashboard) + the held process (level trace / HMI).
4. **Evidence:** before (insider drives out of band, network layer monitor-only) vs after (guardian alarms + holds), with the level trace.
5. **Residual (honest and fundamental):** a stealthy insider who stays **inside** the physical envelope is not caught by physical-invariant checking; the guardian is a first line, not a full application-layer IDS. This is the true boundary, and the network/process hand-off is the architectural answer.
6. **Lands in:** a new short subsection (Ch4 or Ch5) "Process-layer guardian (defence-in-depth)"; Threats reframed so the trusted-insider blind spot is **narrowed** to stealthy in-envelope manipulation, with the layered-defence argument made explicitly.

Safety: driving the tank out of band and clamping is on simulated Factory IO water; reverse to the safe state after each run.

---

## Order and outputs
1. Pre-flight + backups.
2. Workstream A: baseline capture -> harden -> after capture -> before/after table.
3. Workstream B: baseline capture -> build guardian -> after capture -> before/after + level trace.
4. Reconcile numbers (R9), re-arm, green-light.
5. Then write: upgrade §4.5.1 and the trusted-insider paragraph of Threats from acknowledged weaknesses to demonstrated mitigations with their residuals, and add the guardian subsection.
