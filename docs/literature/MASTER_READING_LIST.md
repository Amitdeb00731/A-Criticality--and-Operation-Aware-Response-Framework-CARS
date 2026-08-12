# Master Reading List — Reactive SDN for ICS (Project CARS)

**Project:** Reactive SDN for Securing ICS Environments
**Working direction:** CARS (Criticality-Aware Response) — a working title / lead hypothesis, not the final contribution (decided as the testbed matures)
**Owner:** Amit Kiran Deb · Bristol Cyber Security Group · Supervisor: Joe Gardiner

Merged from the local paper collection and the deep web sweep. Ordered for reading.
Tags: **[E]** Essential · **[H]** High · **[R]** Reference · **[O]** Optional/skim.
Location: 📁 = PDF already in `papers/` or `papers/survey/` · 🌐 = fetch online (link).

> **Citations verified 2026-07-05** (CC-5): all 🌐 items confirmed real — 0 fabrications.
> Metadata corrections + 2 residuals (CHAOS article ID; cite **NIST SP 800-82 Rev. 3**, 2023)
> are in `VERIFICATION_REPORT.md`. Verify any *new* sources before citing.

Reading strategy: **Phases 1–2 are the parallel track** — read them while standing up the
testbed. Phases 3–7 inform the CARS response engine and can be read as each component is built.

---

## PHASE 0 — Orientation & positioning (fast, read first)
- [ ] **[E]** 📁 Etxezarreta, Garitano, Iturbe, Zurutuza (2023). *SDN approaches for intrusion response in ICS: A survey.* — the anchor taxonomy. `papers/Software-Defined Networking approaches for intrusion response in Industrial.pdf`
- [ ] **[O]** 📁 *Network Innovation using OpenFlow: A Survey.* — SDN/OpenFlow foundations; skim if new to SDN. `papers/`
- [ ] **[O]** 📁 *Security Control and Data Planes of SDN: Review of Traditional, AI, and MTD Approaches.* — one-stop map of SDN security options. `papers/`

## PHASE 1 — Closest prior work & the response model (core to CARS)
- [ ] **[E]** 📁 Piedrahita et al. (2018). *Leveraging SDN for Incident Response in ICS.* IEEE Software. — the reference architecture. `papers/survey/Leveraging_Software-Defined_Networking_for_Incident_Response...pdf`
- [ ] **[E]** 📁 Piedrahita et al. (2018). *Virtual incident response functions in control systems.* Computer Networks. — the extended version (cloud/NFV variant). `papers/survey/1-s2.0-S1389128618300434-main.pdf`
- [ ] **[E]** 🌐 Hammar (2025). *Optimal Security Response to Network Intrusions in IT Systems.* — decision-theoretic backbone for *safe* response. https://arxiv.org/pdf/2502.02541
- [ ] **[H]** 📁 *SoK: A Taxonomy for Contrasting ICS Asset Discovery Tools.* — underpins the "unseen device" / criticality classification in CARS. `papers/`

## PHASE 2 — Testbed foundations (read alongside the build)
- [ ] **[E]** 📁 Antonioli & Tippenhauer (2015). *MiniCPS: A Toolkit for Security Research on CPS Networks.* — emulation backbone. `papers/MiniCPS A Toolkit for Security Research on CPS Networks.pdf`
- [ ] **[E]** 📁 *Oops I Did It Again: Further Adventures in the Land of ICS Security Testbeds.* — testbed design choices & pitfalls; saves real time. `papers/`
- [ ] **[E]** 📁 Ndonda & Sadre (2018). *A Two-level IDS for ICS Networks using P4.* — line-rate Modbus allowlist + DPI feedback loop. `papers/survey/ewic_icscsr18_paper4.pdf`
- [ ] **[H]** 📁 Goldenberg & Wool (2013). *Accurate Modeling of Modbus/TCP for Intrusion Detection in SCADA.* — Modbus traffic model for the IDS side. `papers/1-s2.0-S1874548213000243-main.pdf`
- [ ] **[H]** 📁 Alsabbagh et al. *OpenPLC Aqua: Securing the OpenPLC and Related Systems.* — if using OpenPLC for the PLC layer. `papers/09_06_08_Alsabbagh.pdf`
- [ ] **[O]** 📁 *DSSnet: Smart-Grid Modeling + SDN Emulation Platform.* — only if going smart-grid. `papers/`

## PHASE 3 — Detection & filtering building blocks
- [ ] **[H]** 🌐 *Enabling Dynamic Network Access Control with Anomaly-based IDS and SDN.* — formalizes the IDS→controller→flow-rule loop. https://dl.acm.org/doi/10.1145/3309194.3309199
- [ ] **[H]** 📁 Tsuchiya et al. (2018). *SDN Firewall for Industry 4.0 Manufacturing Systems.* `papers/survey/v11-i02-p318_2534-10370-1-PB.pdf`
- [ ] **[H]** 📁 Brugman et al. *Cloud-Based IDPS for ICS Using SDN.* `papers/survey/Cloud_Based_Intrusion_Detection...pdf`
- [ ] **[H]** 📁 *Deep Packet Inspection for Intelligent Intrusion Detection in Software-Defined Industrial Networks.* `papers/survey/Deep packet inspection...pdf`
- [ ] **[H]** 📁 Radoglou-Grammatikis et al. *DIDEROT: An IDPS for DNP3-based SCADA Systems.* `papers/survey/3407023.3409314.pdf`
- [ ] **[H]** 📁 *A Policy Checker Approach for Secure Industrial SDN.* — policy verification (safety of response rules). `papers/survey/A_Policy_Checker_Approach...pdf`
- [ ] **[R]** 📁 Rivera et al. *ROS-Defender: SDN-Based Security Policy Enforcement for Robotic Applications.* — allow/drop/log/copy policy engine pattern. `papers/survey/ROS-Defender...pdf`

## PHASE 4 — Response strategies: MTD, deception, survivability
- [ ] **[E]** 📁 Samanis (2025). *Protecting Against Reconnaissance Attacks on ICS: A Moving Target Defense Approach.* Bristol PhD thesis — **same group**; template for method & write-up. `papers/Final_Copy_2025_11_25_Samanis_ES_PhD.pdf`
- [ ] **[H]** 📁 *Replica-Based MTD Against Injection Attacks in Software-Defined ICS.* `papers/Replica-Based_Moving_Target_Defense...pdf`
- [ ] **[H]** 🌐 *Securing ICS networks: SDN-based Automated Traffic Control and MTD against DDoS.* (2025) — multi-response orchestration to beat. https://www.sciencedirect.com/science/article/pii/S0140366425002099
- [ ] **[H]** 🌐 *Reactive cyber deception: adaptive redirection to on-demand honeypots with AI-driven data generation* (2026) — the redirect branch, elevated. https://www.sciencedirect.com/science/article/pii/S138912862600215X
- [ ] **[H]** 🌐 *D3O-IIoT: DRL-driven dynamic deception orchestration for IIoT* (2025). https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12816736/
- [ ] **[R]** 🌐 *Survey of Moving Target Defense in Power Grids: Design Principles, Tradeoffs, Future Directions* (2024). https://arxiv.org/pdf/2409.18317
- [ ] **[R]** 🌐 Shi et al. (2017). *CHAOS: An SDN-Based Moving Target Defense System.* https://www.hindawi.com/journals/scn/2017/3659167/
- [ ] **[R]** 🌐 *Leveraging Network Reconfiguration to Mitigate Stealthy FDI Attacks in Smart Grid SCADA Systems* (2025) — reactive reconfiguration survivability response. https://link.springer.com/chapter/10.1007/978-3-032-01904-2_19
- [ ] **[R]** 📁 *Toward a Cyber-Resilient and Secure Microgrid Using SDN.* `papers/Toward_a_Cyber_Resilient...pdf`

## PHASE 5 — Line-rate enforcement & determinism (CARS design decisions)
- [ ] **[H]** 🌐 *P4Control: Line-Rate Cross-Host Attack Prevention via In-Network Information Flow Control.* IEEE S&P 2024. https://arxiv.org/pdf/2405.14970
- [ ] **[H]** 📁 *Programmable Data Planes for Increased Digital Resilience in OT Networks.* `papers/Programmable_Data_Planes...pdf`
- [ ] **[H]** 🌐 *Leveraging Data Plane Programmability to enhance service orchestration at the edge: industrial security* (2024). https://www.sciencedirect.com/science/article/pii/S1389128624002299
- [ ] **[R]** 🌐 *A Protocol-Aware P4 Pipeline for MQTT Security and Anomaly Mitigation* (2026). https://arxiv.org/pdf/2601.07536
- [ ] **[H]** 🌐 *Software-Defined Time-Sensitive Networking for Cross-Domain Deterministic Transmission* (2024). https://www.mdpi.com/2079-9292/13/7/1246
- [ ] **[R]** 🌐 *P4-PSFP: P4-Based Per-Stream Filtering and Policing for TSN* (2023). https://arxiv.org/pdf/2311.07385
- [ ] **[R]** 🌐 *TSN for Industrial Automation: Current Advances and Future Directions.* ACM CSUR 2024. https://dl.acm.org/doi/10.1145/3695248

## PHASE 6 — AI-driven detection/response (CARS intelligence; depth optional)
- [ ] **[H]** 🌐 *Detection and mitigation of cyber-attacks in SDN using ML/DL: a systematic literature review* (2025). https://link.springer.com/article/10.1007/s10207-025-01114-z
- [ ] **[H]** 🌐 *Deep reinforcement learning-based intrusion detection scheme for SDN* (2025). https://www.nature.com/articles/s41598-025-24869-w
- [ ] **[H]** 🌐 *Non-local attention enhanced deep learning for cyberattack detection in IIoT-based SCADA* (2026). https://www.nature.com/articles/s41598-026-37146-1
- [ ] **[R]** 🌐 *Machine learning in ICS security: current landscape, opportunities and challenges* (2022). https://link.springer.com/article/10.1007/s10844-022-00753-1
- [ ] **[R]** 🌐 *Transformers and LLMs for Efficient IDS: A Comprehensive Survey* (2024). https://arxiv.org/pdf/2408.07583
- [ ] **[R]** 🌐 *AI-driven secure 5G-SDN framework with federated RL* (2025). https://pmc.ncbi.nlm.nih.gov/articles/PMC12929375/
- [ ] **[R]** 📁 *Ensemble Learning Framework for DDoS Detection in SDN-Based SCADA Systems.* `papers/`
- [ ] **[R]** 📁 Manso, Moura, Serrão (2019). *SDN-Based IDS for Early Detection and Mitigation of DDoS Attacks.* `papers/`
- [ ] **[R]** 📁 *Multi-Layer Adaptive IDS and Mitigation for SDN Adversarial Threats using BAT-MC Model.* `papers/`
- [ ] **[R]** 📁 *Towards Detection and Mitigation of Traffic Anomalies in SDN.* `papers/`

## PHASE 7 — Resilience, digital twin, zero trust (CARS robustness + framing)
- [ ] **[H]** 🌐 Hammar & Stadler (2024). *Intrusion Tolerance for Networked Systems through Two-Level Feedback Control.* https://arxiv.org/pdf/2404.01741
- [ ] **[R]** 🌐 *ITC: Intrusion Tolerant Controller for multicontroller SDN* (2023). https://www.sciencedirect.com/science/article/abs/pii/S0167404823002614
- [ ] **[H]** 📁 *Controller-in-the-Middle Attacks on SDN in Industrial Control Systems.* — control-plane threat model. `papers/Controller-in-the-Middle Attacks...pdf`
- [ ] **[R]** 📁 *AVANT-GUARD: Scalable and Vigilant Switch Flow Management in SDN.* CCS 2013. `papers/AvantGuard-CCS13.pdf`
- [ ] **[H]** 🌐 Krishnaveni et al. (2025). *TwinSec-IDS: Enhanced IDS in SDN-Digital-Twin-Based ICPS.* https://onlinelibrary.wiley.com/doi/10.1002/cpe.8334
- [ ] **[H]** 🌐 *Digital Twin-Enhanced Incident Response for Cyber-Physical Systems.* ACM ARES 2023. https://dl.acm.org/doi/10.1145/3600160.3600195
- [ ] **[R]** 🌐 *Digital Twin-Driven Intrusion Detection for Industrial SCADA* (2025). https://www.mdpi.com/1424-8220/25/16/4963
- [ ] **[H]** 🌐 CISA (2025). *The Journey to Zero Trust Microsegmentation.* https://www.cisa.gov/sites/default/files/2025-07/ZT-Microsegmentation-Guidance-Part-One_508c.pdf
- [ ] **[R]** 🌐 *Zero Trust Architecture: A Systematic Literature Review* (2025). https://arxiv.org/pdf/2503.11659

## PHASE 8 — Safety, standards & motivation (thesis-critical; added 2026-07-05, verified)
_Closes the safety-centric gaps: process-safety, IEC 62443 deployability framing, motivating attack, metrics._ (📘 = standard, not a fetchable paper.)
- [ ] **[E]** 🌐 MITRE ATT&CK — *Triton* (Software S1009): the **TRITON/TRISIS (2017)** attack that targeted a Triconex **Safety Instrumented System** at a Saudi petrochemical plant. https://attack.mitre.org/software/S1009/ — *the* motivating case; grounds "don't let the defence break safety."
- [ ] **[H]** 🌐 *Process-aware security monitoring in ICS: a systematic review and future directions.* Int. J. Critical Infrastructure Protection, 2024. https://www.sciencedirect.com/science/article/abs/pii/S187454822400060X — closest survey to CARS's process-aware premise.
- [ ] **[H]** 🌐 *Cybersecurity and Safety Co-Engineering of Cyberphysical Systems — A Comprehensive Survey.* MDPI Future Internet 12(4):65, 2020. DOI 10.3390/fi12040065 — safety/security interdependence: why a defence action can itself be a safety event. _(authors: confirm at cite.)_
- [ ] **[E]** 📘 **ISA/IEC 62443** series — esp. **62443-3-2** (security risk assessment; zones & conduits) and **62443-3-3** (system security requirements & security levels). The standard the zone-boundary / deployability framing rests on.
- [ ] **[R]** 🌐 *Security Aspects of Zones and Conduits in IEC 62443.* MDPI J. Cybersecurity & Privacy 6(2):52. https://www.mdpi.com/2624-800X/6/2/52 — academic treatment of the zones/conduits model.
- [ ] **[R]** 🌐 *Towards Incident Response Orchestration and Automation for the Advanced Metering Infrastructure.* arXiv:2403.06907 — CPS-context IR orchestration + evaluation framing.
- [ ] **[GAP — opportunity]** No canonical ICS *reactive-response* metrics paper exists (verified: not found). Derive metrics from SWaT/WADI/HAI conventions + standard IR metrics (MTTD / MTTM) + **define our own operator metrics** (zero defence-induced trips; false-block rate on critical flows; audit-trail completeness). Defining these is part of the contribution.

## ONGOING REFERENCE (datasets, standards, tools)
- [ ] **[E]** 🌐 iTrust. *SWaT / WADI / HAI ICS security datasets & testbeds.* https://itrust.sutd.edu.sg/itrust-labs_datasets/
- [ ] **[R]** 🌐 NIST SP 800-82 Rev. 2. *Guide to ICS Security.* https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-82r2.pdf
- [ ] **[R]** 🌐 Bernieri et al. (2019). *MimePot: a Model-based Honeypot for ICS.* (via anchor survey)

---

## Excluded (present locally but low value / not papers)
- `A Quantum-Safe Software-Defined Deterministic IoT...` (MDPI 2024) — niche tangent.
- `survey/978-3-030-55190-2.pdf` (IntelliSys 2020 proceedings) & `survey/978-981-15-3380-8.pdf` (ACIIDS 2020) — broad conference volumes; grep for a specific chapter only.
- `survey/Brochure.pdf` — unrelated (a dating-app pitch).
- `survey/projects_second_markers_2026.xlsx` — admin file.
- `Reactive SDN for Securing ICS Environments.pdf` & `survey/Poster-2711250*.pdf` — your own project docs (context, not reading).

---

_Progress convention: tick the box as you finish each paper. Essentials in Phases 0–2 are the
critical path for starting the testbed. Total: ~45 items (23 local, ~22 to fetch)._
