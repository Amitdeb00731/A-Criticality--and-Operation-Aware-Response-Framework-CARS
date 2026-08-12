# Literature Extraction & Necessity Analysis — 7 Papers vs Project CARS

_Compiled 2026-07-29. Method: text extracted directly from the uploaded PDFs with `pdftotext`; every "What the paper says" line below is grounded in the extracted source text (abstracts, contribution sections, related-work sections). **Hard rule honoured: only what is actually written in the papers is reported here — no fabricated claims, figures, or results.** The "Necessity for CARS" column is my own analysis, clearly separated from what the paper states._

---

## Relevance ranking (my analysis, at a glance)

| Rank | Paper | Direct CARS aspect | Necessity |
|---|---|---|---|
| 1 | **Samanis PhD — MoTaR** (Bristol, your group) | Proactive concealment / P0-6 device-property leak | **HIGH — adopt principle** |
| 2 | **Controller-in-the-Middle** (Bristol, your group) | Control-plane trust / P0-4 | **HIGH — threat model + boundary** |
| 3 | **DPI PoC** (Mondragon, Sainz et al.) | A3 Snort-on-mirror + controller reflow | **HIGH — validates architecture** |
| 4 | **Policy Checker** (Bologna, Melis et al.) | Flow-rule integrity / consistency audit | **MEDIUM — a real gap we don't cover** |
| 5 | **DEFCLON Replica-MTD** (Mondragon/Padova, TDSC) | FDI defence / remediation novelty | **MEDIUM — cite; principle only** |
| 6 | **MTD in Power Grids survey** (arXiv) | MTD framing, metrics, trade-offs | **LOW–MED — framing/reference** |
| 7 | **Network-Reconfig MTD + DRL** (AFRICOMM) | SDN-MTD-vs-FDI evidence | **LOW–MED — cite; DRL out of scope** |

Two of the seven are from **your own group at Bristol (Rashid / Gardiner)** — MoTaR and Controller-in-the-Middle. These are the highest-leverage citations for the dissertation because they position CARS inside the exact research lineage of your supervisors' lab.

---

## 1. Samanis PhD — "MoTaR: Moving Target Against Reconnaissance" (University of Bristol; EPSRC + Airbus)

**What the paper says (extracted verbatim from abstract + §1.4.3):**
- Develops an MTD mechanism, **MoTaR (Moving Target Against Reconnaissance)**, "specifically designed for ICS networks." It "monitors live industrial network traffic, obfuscating critical ICS devices properties to disrupt reconnaissance attempts **while allowing normal operations to continue unaffected**."
- Three contributions, stated: (1) a "comprehensive evaluation of current asset scanning techniques in ICS environments... addresses issues related to legacy systems, proprietary protocols, and the operational disruption caused by static scanning approaches"; (2) MoTaR itself — "utilizing principles of **deception, dynamic network reconfiguration, and deep packet inspection**, while allowing legitimate asset scanning to operate"; (3) "stealthy reconnaissance detection" — behaviour-based anomaly detection systems miss stealthy recon, so MoTaR is "improved with an additional ICS traffic anomaly detection module."
- Supervisors: Prof. Awais Rashid, Dr. Joseph Gardiner.

**Necessity for CARS (my analysis):**
- This is the **single most directly relevant paper**. Our A2 default-deny already gives *concealment* (crown jewels invisible — findings P0-1/P0-5). MoTaR goes one step further to *deception*: obfuscating device **properties** (OS fingerprint, banners, protocol responses). That is exactly the unfixed gap in finding **P0-6** — HMI1 leaks a full OS fingerprint + enumerable ports because it must answer legitimate polls.
- Necessity: **HIGH as a principle to adopt for the devices we cannot simply hide** (the HMI, the collector). A future phase could present *false* device properties to unlisted sources while the stateful `+est` path keeps real replies flowing to legitimate clients — a natural extension of what CC-89 already built.
- It also gives us a **peer-reviewed, same-group precedent** for the "protect the process while defending" thesis: MoTaR explicitly preserves normal operation and *allows legitimate scanning*. That is the identical operational-awareness stance CARS champions ("save process at any cost").

---

## 2. Controller-in-the-Middle: Attacks on SDN in ICS (Gardiner, Eiffert, Garraghan, Race, Nagaraja, Rashid — Bristol / Lancaster / Strathclyde; CPSIoTSec '21)

**What the paper says (extracted verbatim from abstract):**
- "The centralisation of network control results in a **single point of failure** within the system, and thus potentially a major target of attack. An attacker who is capable of controlling the SDN controller gains **near full control of the network**."
- "We demonstrate a number of simple, yet highly effective, attacks from a **compromised SDN controller** within an ICS environment which can **break the real-time properties of industrial protocols**, and potentially interfere with the operation of physical processes."

**Necessity for CARS (my analysis):**
- Directly validates the **severity** of our finding **P0-4** (attacker POSTed `/cars/defense` → silent disarm). The paper's thesis is precisely: the controller/control-plane is the crown target. Our CC-85 fix (X-CARS-Token auth + audit on all control endpoints) is the **first-line mitigation** — it stops an attacker *reaching* the control API.
- However, the paper's threat is *broader*: the controller itself being compromised. Necessity: we should (a) **cite this to justify the P0-4 hardening**, (b) **document controller-compromise as an explicit honest boundary** (like G1/G6), and (c) note that "break the real-time properties" is exactly what **SDN Phase 2 (control-loop QoS)** defends — protecting loop latency even under control-plane stress.
- Same group as MoTaR and as your supervisors — high citation value.

---

## 3. Deep Packet Inspection for Intelligent IDS in SD Industrial Networks: A PoC (Sainz, Garitano, Iturbe, Zurutuza — Mondragon University)

**What the paper says (extracted verbatim from abstract + related work):**
- A **proof of concept** IDS using DPI in an SDN industrial network, detecting **ICMP Flood and packet-payload alteration based on signature comparison**, evaluated on a *scaled physical ICS testbed*.
- Motivation as written: SDN is "barely used with cyber security purposes in ICSs, which could be considered a good test candidate due to their **communication periodicity and predictability**."
- Related work, as cited in the paper: **Wan et al.** — a DPI module embedded in the switch via NFV, using a Hidden Markov Model; **Ha et al.** — an external IDS that samples mirrored traffic with a *dynamic sampling rate* and an algorithm to reduce false negatives; **Murillo et al.** — an external signature-based IDS connected to the SDN controller, where the controller **changes flow rules upon detection**.

**Necessity for CARS (my analysis):**
- **Murillo et al.'s pattern, as reported here, is CARS's exact architecture**: external signature IDS (our Snort on the mirror port `snort0`) + SDN controller (our os-ken engine) that reprograms flows on detection. This paper is strong evidence that our design is an established, valid SDN-IDS pattern — good to cite for the architecture chapter.
- Two adoptable ideas, grounded in the text: (1) the **periodicity/predictability** argument justifies baseline/anomaly detection for our fixed cyclic S7 polling — a hook for cross-flow analytics (Phase 4); (2) **Ha et al.'s dynamic sampling rate** matters *if* mirror volume grows with more devices — relevant to the topology-wide retrofit.
- Their detected classes (ICMP flood, payload alteration via signature) map onto our flood detection (A5) and our byte-exact S7 DPI at packet offset 17. Necessity: **HIGH for validation**, moderate for new capability.

---

## 4. A Policy Checker Approach for Secure Industrial SDN (Melis, Berardi, Contoli, Callegati, Esposito, Prandini — University of Bologna; CSNet 2018)

**What the paper says (extracted verbatim from abstract):**
- A toolkit letting a network administrator "implement and verify **in a formal way** security policies, in the context of an industrial network," built as "four application plug-ins of the ONOS controller."
- It "is able to detect compromised network boxes as a result of **bogus injected flow-rules, inner loops and black-holes** (notoriously difficult to detect via normal network scans), **flow-rule replacements or removal** and other SDN controller exploitations that may compromise the forwarding activities."

**Necessity for CARS (my analysis):**
- This targets a real gap CARS does **not** currently cover. We audit policy *intent* manually (CONSISTENCY_AUDIT.md) and enforce an allowlist/rulebook, but we do **not formally verify that the flow table actually installed on OVS matches the intended `a2_policy.json`** — i.e. we have no detector for tampered/bogus/removed flow-rules, loops, or black-holes.
- This is the **defensive complement to the Controller-in-the-Middle threat (paper #2)**: if an attacker reaches the control plane and injects/removes rules, a policy checker catches it. Necessity: **MEDIUM and concrete** — a lightweight "flow-integrity audit" (periodically diff live `ovs-ofctl dump-flows` against the intended policy; alarm on drift) would be a modest, high-credibility addition and directly strengthens the novelty-vs-firewall/IPS argument (stateless firewalls can't self-verify their own forwarding state).

---

## 5. Replica-Based Moving Target Defense Against Injection Attacks in SD-ICS — "DEFCLON" (Etxezarreta, Turrin, Garitano, Iturbe, Zurutuza, Conti — Mondragon / Padova / Örebro; IEEE TDSC, May/Jun 2026)

**What the paper says (extracted verbatim from abstract):**
- **False Data Injection (FDI)** attacks are "one of the main security threats to ICSs," with "high capacity of concealment and ability to evade intrusion detection systems that rely on accurate ICS models."
- **DEFCLON** is "a novel SDN-based Moving Target Defense (MTD) approach against FDI attacks." It "proactively **replicates network packets across multiple network paths** and adaptively selects a single path using a **signaling game model**" to reach the destination.
- Result claimed: it "mitigate[s] the effects of FDI attacks" and "introduce[s] different levels of uncertainty **without degrading network performance**."

**Necessity for CARS (my analysis):**
- FDI is exactly our **Phase 3 pen-test** (DB7 `Level` spoof → pump latch → overflow/dry). CARS's answer is *detect* (DPI on writes to the Q/output area) + *maintain* (remediation restores last-good) — the P1 novelty. DEFCLON is a complementary, *proactive* answer (make the injection target/path uncertain).
- Its multi-path packet replication needs a **multi-path topology**; our per-cell single control loop has limited path diversity, so the mechanism itself is heavier than our testbed supports. Necessity: **MEDIUM — cite as the strongest recent peer of our FDI defence**, and borrow the *principle* (uncertainty against injection) to frame Phase 3 micro-segmentation, but do not attempt to reimplement path-replication. The "without degrading network performance" constraint mirrors our "save process at any cost" rule and is worth quoting.

---

## 6. Survey of Moving Target Defense in Power Grids: Design Principles, Tradeoffs, and Future Directions (Lakshminarayana, Chen, Konstantinou, Mashima, Srivastava — arXiv 2409.18317, 2024)

**What the paper says (extracted verbatim from abstract):**
- "The key idea behind MTD is to introduce **periodic/event-triggered controlled changes** to the power grid's SCADA network/physical plant, thereby **invalidating the knowledge attackers use for crafting stealthy attacks**."
- Provides "a comprehensive overview," "classif[ies] the different ways in which MTD is implemented," and "introduce[s] the guiding principles behind the design of MTD, key performance metrics, and the associated trade-offs."

**Necessity for CARS (my analysis):**
- This is a **survey**, and its domain is power-grid state estimation, not S7 tank control — so it offers *framing*, not implementation. Necessity: **LOW–MEDIUM.** Use it for the literature-review chapter to (a) define MTD formally, (b) borrow its taxonomy to position CARS's proactive concealment as a light-touch MTD, and (c) adopt its "key performance metrics / trade-offs" vocabulary when we report our overhead numbers (e.g., our 0.25–0.76 ms enforcement latency as a performance metric). No implementation to lift.

---

## 7. Leveraging Network Reconfiguration to Mitigate Stealthy FDI in Smart Grid SCADA by Exploiting Attacker Uncertainty (Kpoze, Degila, Ahouandjinou — University of Abomey Calavi; AFRICOMM 2024, LNICST 652)

**What the paper says (extracted verbatim from abstract):**
- "An innovative SDN-based Moving Target Defense (MTD) approach to dynamically reconfiguring the network of a Smart Grid SCADA system to counter stealthy FDI attacks."
- "We also determine the **optimal network reconfiguration strategy and frequency** based on real-time network state using the **Proximal Policy Optimization (PPO) Deep Reinforcement Learning** algorithm."
- Result claimed: "prevent up to **92% of stealthy FDI attacks** while maintaining SCADA system performance."

**Necessity for CARS (my analysis):**
- Same MTD-vs-FDI family as #5 and #6, again in the smart-grid domain. The distinctive element is **PPO Deep-RL to time the reconfiguration** — considerably heavier machinery than CARS's deterministic rule-based response, and harder to defend/explain in a testbed dissertation. Necessity: **LOW–MEDIUM.** Cite it as evidence that SDN-driven reconfiguration mitigates stealthy FDI while preserving SCADA performance (reinforcing our operational-awareness thesis). Treat the DRL controller as **out of scope** — it adds explainability risk without a proportional benefit at our scale.

---

## Consolidated takeaways for CARS (my analysis)

1. **Two Bristol/your-group papers anchor the narrative.** MoTaR (proactive reconnaissance defence) and Controller-in-the-Middle (control-plane as crown target) let you position CARS as a direct, applied continuation of your lab's line of work. Cite both prominently.
2. **One concrete new capability worth building: a flow-integrity / policy checker** (from paper #4). It closes a genuine gap — we enforce policy but never verify our own installed flow state — and it is the defensive pair to the Controller-in-the-Middle threat. Low effort, high credibility, strengthens novelty-vs-firewall.
3. **One concrete gap the literature confirms is real: device-property leakage (P0-6),** for which MoTaR's *deception* (obfuscate properties, not just hide ports) is the peer-reviewed answer — a candidate future phase layered on top of the CC-89 stateful fabric.
4. **The MTD-vs-FDI cluster (#5, #6, #7)** collectively validates our FDI defence + remediation novelty and the "preserve process/performance" constraint, but their mechanisms (path replication, DRL-timed reconfiguration, multi-path grid topologies) are **heavier than our testbed warrants** — cite for framing and positioning, do not reimplement.
5. **The DPI PoC (#3)** confirms our external-Snort-plus-controller-reflow architecture is an established, valid SDN-IDS pattern (Murillo et al.), and offers two scaling hooks (periodicity-based baselining; dynamic mirror sampling) relevant to the topology-wide retrofit and Phase 4 analytics.

_No claim above about a paper's contents goes beyond the extracted source text. Necessity judgements are explicitly my own and are separated from the extracted facts._
