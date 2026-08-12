# CARS — Related Work & Novelty Positioning (write-up track F1)

_2026-07-23. The #1 write-up gap (per GAP_AND_NOVELTY.md): a sharp related-work comparison that makes the novelty defensible.
Rule 0: only systems we have actually read are characterised in detail; archetypes are labelled as such; specific extra
systems to add are TODO'd, not invented._

## 1. Field frame (from the Etxezarreta et al. survey — see PAPER_MAP_Etxezarreta_survey.md)
SDN-based intrusion response for ICS splits into **dynamic traffic filtering**, **network survivability**, and **cyber
deception (MTD + honeypot)**; along the strategy axis into **reactive** (IDS-driven, most common), **proactive** (pre-installed,
under-researched — mostly MTD), and **adaptive** (learning/game-theoretic, aspirational). The survey's recurring tension:
in ICS *"an outage is not acceptable"* and reactive response on a false positive can itself cause an outage — hence the call
for safe/preventive response. **CARS is positioned directly on that tension.**

## 2. Capability matrix (the axes that define CARS's contribution)
Legend: ● = yes/strong · ◑ = partial · ○ = no · — = n/a. Archetype columns are defensible generalisations the survey supports.

| Capability / property | **CARS (this work)** | Cárdenas group (Murillo Piedrahita et al. 2018, ×2) | Typical SDN-IR for ICS (survey archetype) | Traditional IDS-only (baseline) |
|---|---|---|---|---|
| Reactive response (detection→mitigation) | ● block/throttle/isolate/deflect/refuse | ● reroute/redirect | ● drop/block flows | ○ alert only |
| Proactive default-deny (works IDS-down) | ● A2 allowlist, pre-installed | ○ (IDS-driven) | ◑ some (mostly MTD) | ○ |
| **Safety cap — never cut the CRITICAL control loop** | **● REFUSE on hmi↔plc** | ○ (may take over/alter the loop) | ○ rarely explicit | — |
| Criticality-graded response (per-asset) | ● OPERATIONAL/SENSITIVE/FORBIDDEN/CRITICAL | ◑ | ◑ | ○ |
| Operation-aware DPI (protocol op, not 5-tuple) | ● Modbus FC + classic S7comm ops | ◑ (protocol-level) | ◑ | ◑ detection-only |
| Rate/behavioural (volumetric-DoS on legal ops) | ● A5 flood-graded THROTTLE→BLOCK | ○ | ○ | ◑ |
| Bounded + reversible (self-healing) response | ● hard_timeout, auto-heal, forgive | ◑ | ◑ | — |
| Anti-spoof / identity binding (GUARD) | ● IP+MAC+port bindings, ARP-guard | ○ | ◑ | ○ |
| **Process-level maintenance (state estimation / virtual sensor)** | ● **P1 DONE (last-good substitution, CC-72)** | **● (their core contribution)** | ○ | ○ |
| Deception (honeypot / MTD) | ◑ DEFLECT (low-interaction honeypot); no MTD | ● honeypot that emulates the process | ◑ | ○ |
| **Testbed = real ICS hardware** | **● 2× real Siemens S7-1200 + live process** | ○ **Mininet + physics co-sim** | mostly ○ (emulated) | varies |
| Evidence rigor (cross-source, hardware, adversarial, MITRE) | ● multi-source, hardware, MITRE ATT&CK ICS coverage | ◑ simulation | varies | varies |

## 3. The precise delta (what is NEW — the sentence an examiner can't out-skeptic)
No single mechanism is new (SDN ACLs, IDS→SDN response, honeypot redirection, S7/Modbus DPI, default-deny, state estimation
all exist). **The contribution is the *combination under a safety discipline, on real hardware*:**
1. **Reactive + proactive unified**, criticality-graded and **safety-capped** so the physical control loop is *never*
   enforced against — response is bounded and reversible. (The Cárdenas group and most SDN-IR work do not carry this
   never-cut-the-loop safety invariant; the survey flags it as needed but under-addressed.)
2. **Network-level attacker-bounding COMBINED WITH process-level state maintenance (P1).** The Cárdenas group *maintains the
   process* via estimation (in simulation); typical SDN-IR *bounds the attacker* at the network (in emulation). **CARS aims
   to do both, on real Siemens hardware** — this "block **and** maintain, safety-capped, on hardware" trio is claimed by
   none of the reference works individually.
3. **Demonstrated on real ICS hardware** with a live PLC-controlled process surviving attack, cross-source corroboration,
   and full MITRE ATT&CK for ICS coverage from real attacker VMs — an unusually strong empirical base for this field.

## 4. Closest work — honest positioning vs the Cárdenas group (the nearest neighbour)
Their contribution: **process-physics-aware virtual incident-response functions** — replace a compromised sensor with a
*model-estimated* value (virtual sensor / open-loop virtual PLC), redirect the attacker to a process-emulating honeypot.
Strong on *process-level maintenance*; **but simulated (Mininet), reactive-only, and without a safety cap** (their response
can take over/alter the loop). **CARS is complementary and, with P1, strictly broader on the axes that matter for OT safety:
safety-capped, reactive+proactive, on real hardware — and P1 borrows their best idea (estimation) as a mitigation rung.**
Frame CARS not as beating them but as *unifying* their process-level insight with network-level safety-capped response on hardware.

## 5. TODO — add 2–3 more closest systems for a full matrix (do when WebSearch resets / from Amit's paper set)
Chase, as named/characterised BY the Etxezarreta survey (do not invent specifics — read them):
- **Genge et al. [survey ref 63]** — the only surveyed work considering single *and* multi-controller intrusion response.
- **The data-plane detection/mitigation works [survey refs 56, 64]** — low-latency, response logic in the data plane (contrast
  CARS's controller-centric decision + data-plane-resident enforcement).
- **Data/control collaboration [survey ref 108]** — lightweight data-plane anomaly detection → controller deep-detection →
  mitigation (contrast CARS's Snort→bridge(rate)→controller→enforce split).
- Optionally one **SDN-MTD-for-ICS** proactive work to contrast CARS's default-deny vs MTD.
Fill their rows in the §2 matrix once read; each is one honest sentence of "how CARS differs."
