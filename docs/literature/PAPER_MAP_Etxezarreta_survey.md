# Paper Map & Self-Assessment — Etxezarreta et al., *SDN approaches for intrusion response in ICS: A survey* vs Project CARS

_Written 2026-07-20 under Rule 0 (map honestly, name every non-coverage). Source: Amit's Phase-0 notes on Etxezarreta,
Garitano, Iturbe, Zurutuza. This is a **survey** — the field map — so "passing" it = CARS is correctly situated on every
axis of its taxonomy, covers multiple response classes with hardware evidence, and **advances the open problems the survey
explicitly flags as under-researched.** It is NOT a head-to-head system comparison._

---

## 0. Verdict up front
**PASSED — and more usefully, CARS plants a flag on one of the survey's explicitly under-researched squares.** CARS maps
onto every axis of the taxonomy; covers 2 of 3 response categories strongly (dynamic filtering + honeypot deception) plus
process-survivability; implements **both** reactive and proactive response (a unification the survey notes is rare); sits
at the strong **physical-hardware** end of the testbed spectrum; hardens data-plane device identity (GUARD); and directly
answers the survey's headline tension — *reactive response risks outages in high-availability OT* — with a criticality-
graded, safety-capped, reversible response model proven on real Siemens PLCs. Non-coverage is real and named, and every
item of it corresponds to a **future direction the survey itself lists**, so absence is a scope boundary, not a failure.

---

## 1. Response-type taxonomy (the survey's three categories)

| Survey category | CARS mechanism | Evidence | Verdict |
|---|---|---|---|
| **1. Dynamic traffic filtering** (DPI / signature / anomaly / ML → drop/block flows) | A1 responses (BLOCK/THROTTLE/ISOLATE/REFUSE) via OpenFlow; A3 signature DPI (Snort: Modbus FC taxonomy, S7comm 0x32); A5 rate/anomaly | Phase-2a full response spectrum; ICS op-battery; A5 CC-66 | **COVERED — strong.** Multi-technique: signature + operation-aware + rate-anomaly, not just 5-tuple ACLs |
| **2. Network survivability** (maintain operation when a component fails; OpenFlow fast-failover) | Self-healing responses (bounded `hard_timeout`, auto-expire + forgive); A2 flows are data-plane-resident so persist if the controller drops | Phase-2b reversibility; Phase-2c "control loop never disrupted" | **PARTIAL.** *Process*-survivability (never cut the loop, responses reverse) = YES. *Network-failure* survivability (backup paths, fast-failover groups) = **NO** — distinct concept, not implemented |
| **3a. Cyber deception — Moving Target Defense** (randomise IP/paths) | — | — | **NOT COVERED.** CARS uses default-deny instead of MTD |
| **3b. Cyber deception — Honeypot-based** | A1 DEFLECT → honeypot .3.99 (set-field redirect, full round-trip) | CC-45; Phase-2a DEFLECT; PLC2-4 SEC3 | **COVERED** — low-interaction (survey-consistent limitation, our G7) |

---

## 2. Response strategy: reactive / proactive / adaptive (the survey's core axes + open problems)

| Survey axis | Survey's stance | CARS position | Verdict |
|---|---|---|---|
| **Reactive** | "currently the most common"; risk = false-positive → **outage** in high-availability OT | A1 detection-driven response, ~11 ms MTTM, bounded/reversible | Covered; and CARS's reversibility+safety-cap is a *direct mitigation* of the survey's stated false-positive-outage risk |
| **Proactive** | "a promising research field… requires extensive research"; most proactive work = MTD | A2 pre-installed **default-deny allowlist** (protects even IDS-down), hot-reloadable | **ADVANCES a named open problem** — a non-MTD proactive technique, and it **unifies reactive+proactive** in one framework (survey notes unification is rare) |
| **Adaptive** | vision = adapt to attacker behaviour via learning / game theory | Persistence-escalation (BLOCK→ISOLATE on offense count) + A5 rate-grading = **rule-based, behaviour-adaptive** | **PARTIAL.** Adapts to attacker persistence/rate, but is **not** learning/ML/game-theoretic — honest boundary |

---

## 3. Architecture mapping

- **Controller:** os-ken (Ryu fork). Survey: Ryu/POX are *research* controllers, "not intended for industrial use"; ODL/ONOS are better for industrial HA/scale. → **Stated limitation** — CARS uses a research-grade controller (fine for a research prototype; flag it).
- **Single vs multi-controller:** CARS is **single-controller (SPOF)**. Survey flags SPOF and multi-controller as a direction (only Genge et al. considered both). → **Not covered — future work (= our G6).** Note the data plane keeps enforcing installed flows if the controller drops (partial mitigation).
- **Where the logic lives:** Survey — most solutions are app-plane/controller-heavy; only [56,64] push detection/mitigation into the data plane for low latency. CARS: **detection** app-plane (Snort), **decision** controller (~0.5 ms), **enforcement** data-plane-resident (persistent, self-healing flows; A2 pre-installed). → Controller-centric decision, but data-plane-resident *enforcement*; **not** stateful-data-plane *detection*.
- **Stateful data plane / P4:** not used (OpenFlow, limited match fields). → future direction.
- **Data/control-plane collaboration:** Snort → bridge (**lightweight rate aggregation, A5**) → controller → data plane. Matches the survey's described split; the bridge's per-op rate windowing is a small sensor-side offload in the spirit of [108]. → **Aligned.**

---

## 4. Does CARS harden the SDN *itself*? (survey's SDN-vulnerability taxonomy)

| SDN vuln class (survey) | CARS |
|---|---|
| Data-plane: lack of device authn/authz, malicious traffic injection | **Addressed** — GUARD (IP/MAC/port bindings + ARP-guard) = device-identity binding; A2/A1 stop injected/unauthorised traffic |
| Control-plane: SPOF, controller overload | **Not hardened** — single controller (SPOF); A5 offloads rate-counting to the sensor to limit controller load under flood |
| Northbound/Southbound: unencrypted/weak protocols | Not addressed (OpenFlow not TLS-hardened in the testbed) |
| Application-plane: malicious/buggy apps, missing app authn | Snort/bridge *are* the app-plane; not specifically hardened |

→ CARS defends **the ICS via SDN**; it does **not** fully harden the SDN control plane itself. Honest.

---

## 5. Testbed positioning

Survey classes: **emulated** (Mininet/MiniCPS) · **virtualized** (VMs) · **physical** (real ICS — "a step forward… more
representative," but rare and low-replicability). CARS = **physical** (2× real Siemens S7-1200, audible relay actuation) +
emulated netns + a Modbus simulator = a **hybrid at the strong (physical) end.** The survey's standing caveat — nearly all
solutions are *small-scale, single-controller* — applies to CARS too (honest; = our G6). Tomorrow's real-VM attacker day
(insider/IT VMs, DDoS) adds the **virtualized-attacker** dimension on top of the physical target, strengthening this axis.

---

## 6. The single strongest alignment (the write-up money point)

The survey returns repeatedly to one tension: in ICS *"an outage is not acceptable,"* *"high availability is required,"* and
*"deploying response actions on false-positive alerts… could lead to outages,"* which is precisely why it calls for
proactive/preventive approaches. **CARS's central design is a direct answer to that stated problem:** responses are
criticality-graded and **safety-capped** (the CRITICAL HMI↔PLC loop is never enforced → REFUSE), **bounded and reversible**
(self-healing), and backed by **proactive default-deny** that holds even with the IDS offline — all demonstrated on
hardware with the physical control loop surviving every response and every stress/flood scenario. In the survey's own
language, CARS is *"automated network intrusion response for OT you can actually turn on, because it will not break the
physical process."* That is the square the survey marks under-researched, and it is where CARS contributes.

---

## 7. Non-coverage ledger (all = survey's own future directions ⇒ defensible scope, not failure)

1. **MTD** (moving-target defense) — CARS uses default-deny instead.
2. **Learning / game-theoretic adaptive** response — CARS is rule-based adaptive.
3. **Stateful-P4 data-plane detection** — CARS keeps detection in Snort/controller.
4. **Multi-controller / distributed control** — CARS is single-controller (SPOF). *(G6)*
5. **Industrial-grade controller** (ODL/ONOS) — CARS runs os-ken/Ryu (research).
6. **Network-failure survivability** (fast-failover groups, backup paths) — CARS does process-survivability, not link recovery.

Each is a clean sentence of "future work" in the dissertation, and each is one the survey itself flags as open.

---

## 8. Bottom line for the write-up
CARS is **fully situated** on the Etxezarreta taxonomy and is **net-positive**: it covers dynamic filtering + honeypot
deception + process-survivability, uniquely **unifies reactive and proactive** response, hardens data-plane identity, runs
on **rare physical ICS hardware**, and **directly advances the survey's headline open problem** (safe response for high-
availability OT). Its gaps are real but every one maps to a future direction the survey already names. **Verdict: passed —
grounded in the field map and advancing it on the safety-discipline axis, with an honest, survey-aligned boundary list.**
This survey is best used in the dissertation as the **framing reference** for the field and the source of the six future-
work items above.
