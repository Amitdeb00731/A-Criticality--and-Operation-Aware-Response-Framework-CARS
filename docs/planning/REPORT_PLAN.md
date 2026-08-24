# CARS Dissertation — Writing Plan and Governing Rules

Purpose: this file governs all report writing. It is read at the start of every writing session and is not optional. It encodes Amit's hard rules, the University of Bristol MSc template, the chapter map onto the actual lab work, and the citation discipline.

## 1. Hard rules (non-negotiable, from Amit)
1. No word is fluff, unclaimed, unverified, or invented. Every factual or empirical claim traces to a captured result, a logged decision, a source file, or a cited paper.
2. The report is the exact reflection of what was actually built and tested in the lab, formatted into a clean professional thesis. Nothing is described that was not done.
3. No sign of AI authorship. This includes avoiding stylistic tells (see section 2), not only content.
4. No AI signatures that automated detectors (for example Turnitin) flag. Write in a plain, human, technical register.
5. Referencing is genuine, clean, and complete. Citations carry real authors, titles, venues, years, and page numbers taken from the actual source. If context for a claim needs a paper we do not hold, stop and ask Amit to upload it. Never generate a citation, fact, figure, or quotation.
6. The report sounds like and shows the actual lab work.
7. The report meets the standard reached in the lab and demonstrates the entire body of work honestly, including boundaries and negative results.
8. Appendices carry all extras, but anything vital to understanding is signposted from the main text.
9. **Verify on the device, never assume.** Any confusion or uncertainty in any section or subsection triggers an immediate verification before a word or a diagram is committed: directly on the testbed devices (dump the live configuration, flow tables, source, and files from the terminals), and against the papers already in the references or planned for addition. Nothing is written or drawn from assumption, memory, or a possibly stale file when it can be confirmed on the running system or in a source. The Design and Implementation chapter in particular must reflect the exact current upstanding system, confirmed device by device, and that confirmed state is then followed consistently across every section.
10. **Rerun for the writeup, on the live system.** Every test, proof and piece of evidence is re-run on the current upstanding testbed, dedicated to the writeup, and captured fresh before the paragraph, table, figure or chart that uses it is written. This applies with full force to the Critical Evaluation chapter: the matrix, the criticality sweep, the wire campaign, the latency and the process-devastation evidence are all produced from a fresh dedicated run, not lifted from an earlier campaign. Stored results are used only to reconcile against the fresh run, never as a substitute for it. The system was tested and verified stable on 3 August 2026 and that baseline is recorded in `report/verified_config.md` and `report/LAB_VERIFY.md`; it is recalled for reconciliation, and any divergence is resolved on the device (rule 9) before a word is committed.
11. **Capture the vital proof; signpost the rest to the appendix.** As the system is tested and evaluated, the most vital proofs, logs, events and outputs are screenshotted or recorded. Where an artefact is too vast, comprehensive or detailed for the body, the single most vital part is shown in the body and the full artefact is placed in the appendix, with the body pointing to it explicitly by reference. Nothing vital is dropped; it is relocated and signposted. This holds for the Design and Implementation chapter as well as the Critical Evaluation. The appendix is deliberately comprehensive, per the blueprint in section 4.

## 2. Anti-AI-signature style discipline (concrete)
- Do not use em dashes or en dashes as sentence punctuation. Use commas, colons, semicolons, parentheses, or split the sentence.
- Avoid the words and tics that detectors and readers associate with generated text: delve, leverage, showcase, seamless, robust (as filler), realm, landscape, tapestry, testament, underscore, pivotal, crucial (overused), notably, moreover and furthermore stacked together, "it is worth noting", "in today's world", "plays a key role".
- Avoid the rhythmic tells: three-item parallel lists used decoratively, "not only X but also Y" as a habit, sentences that are all the same length, over-balanced antithesis.
- Avoid empty summarising phrases: "in conclusion", "overall", "as we can see".
- Prefer concrete numbers and named artefacts over adjectives. "The isolate flow installed in under one second" beats "the response was remarkably fast".
- Vary sentence length naturally. Let some sentences be short. Allow ordinary connectives.
- British spelling throughout (behaviour, minimise, defence), matching a Bristol thesis.
- Write from our own notes and results, not by paraphrasing source papers sentence by sentence (rule 5, and the plagiarism guidance).

## 3. Template and word budget
- Template: University of Bristol MSc thesis class `dissertation.cls`, sample `DataScience_UoB_MSc_thesis.tex`, logo `logo_uob_color.eps`, BibTeX. Format may be adapted to the material where sensible.
- Front matter: Abstract (<=1 page, compulsory), Supporting Technologies (<=1 page, compulsory, bullet list of hardware and software used), Notation and Acronyms (optional, useful here), Acknowledgements (optional). Skip "Summary of Changes" (that section is only for resubmissions).
- Body chapters and target proportions: Introduction (~10%), Background (~20%), Execution / Design and Implementation (~30%), Critical Evaluation (~30%), Conclusion (~10%).
- Suggested extra sections from the brief that suit this project: an Ethics statement and a Threats to Validity section. Both are appropriate for offensive-security lab work and we will include them.
- Word count: the brief allows 6,000 to 10,000 words for a laboratory-based dissertation, and 10,000 to 15,000 otherwise. CARS is heavily laboratory and implementation based, so we treat it as laboratory work and aim for the 6,000 to 10,000 band. CONFIRM WITH SUPERVISOR before final submission. The limit excludes title page, abstract, contents, references, and appendices.

## 4. Chapter map onto the actual work (evidence each section re-runs fresh)
Everything below already exists and is validated; the writing task is to author the narrative and, per section, produce clean captured evidence for that section (figures, tables, packet captures, decision logs).

- Abstract: the trust barrier for reactive OT defence; CARS as a criticality- and operation-aware SDN intrusion-response system that is bounded, reversible, and evidence-generating; the hypothesis that such a defence can be enabled without risking the process; the headline results (100% decision accuracy at 0% false positives on the live process, wire-level block-and-maintain, criticality-graded response).
- Supporting Technologies: 3 Dell nodes; 2 Siemens S7-1212C PLCs (6ES7 212-1BE40-0XB0, firmware 4.2.3); TIA Portal; Factory IO with the S7-1200 driver; Open vSwitch; os-ken (Ryu fork) OpenFlow 1.3 controller; Snort DPI; python-snap7; Kali Linux; Node-RED, Mosquitto, InfluxDB; scapy, hping3, nmap, arp-scan. Attribute each to where it is used.
- Notation and Acronyms: ICS, OT, PLC, HMI, EWS, SCADA, SDN, OVS, DPI, FDI, HIL, CARS, GUARD, and the S7 addressing.
- Ch1 Introduction: the OT security problem; why reactive SDN response for ICS is attractive but undeployed; the operator-trust bottleneck; the aims, objectives, and achievements as a closing bullet list.
- Ch2 Background: ICS and OT security fundamentals; SDN and OpenFlow; reactive SDN defence for ICS; stateful data-plane security (AvantGuard); flow-integrity and the controller-in-the-middle threat; asset criticality frameworks; ICS testbeds (MiniCPS, and the testbed SoK). Related work drawn from the real paper set. Self-contained, honest, in our own words.
- Ch3 Design and Implementation: CARS-first, testbed last (supervisor review, Aug 2026). Lead with CARS as an environment-independent architecture: the threat model, then CARS as an abstraction (detect/decide/enforce, criticality and operation axes, bounded/reversible/evidence-generating), the three-table pipeline (GUARD anti-spoof, stateful conntrack policy, L2 switch), the rulebook/operation classes/criticality model and decision matrix, the response ladder, the flow-integrity checker. Then a Portability and scalability section (a portable engine separated from a site configuration, verified by a config-parity test and shown in the hardware-free emulation; scale bounds from the flow-table stress test). Only then the concrete testbed instantiation (SDN fabric, two cells, Factory IO hardware-in-the-loop) and deployment. The design is the contribution; the testbed is one instantiation used to validate it. Key design decisions with their trade-offs (reactive cookie hardening, flood exemption for legitimate high-rate I/O, remediation scope) sit with their mechanisms.
- Ch4 Critical Evaluation: the accuracy and false-positive evaluation; the dedicated criticality sweep across CRITICAL, HIGH, MEDIUM, LOW; the wire-level campaign (recon, spoofing, state, controller compromise, op-aware, process devastation, response ladder) armed versus unprotected; analytical reading of each, including the reaction-window boundary and the layered-defence findings; comparison against the alternatives in the literature.
- Threats to Validity: single testbed, simulated versus physical process, reaction-window latency, the documented boundaries (L2 discovery, safety-invariant loop, compromised endpoint, full controller compromise).
- Ethics: isolated air-gapped testbed, no production infrastructure, responsible-disclosure posture, the intent of defensive research.
- Ch5 Conclusion: contributions and achievements against the aims; project status; future work (sensor-aware remediation on a live process per CC-101, SDN phase 2 and 3, MoTaR deception).
- Appendices (blueprint, per hard rule 11 — the comprehensive backing for both Chapter 3 and Chapter 4):
  1. System, response and evaluation detail that does not fit the body: full configurations, flow tables, the deployed decision logic, criticality and rulebook in full.
  2. All logs, events, proofs and outputs, elaborated: decision logs, flow-audit events, controller status and counters, the complete evaluation matrix.
  3. Packet-level and wire-level evaluation: capture the pcaps at the three wire points AND analyse them in Wireshark (do not just store raw captures). Put annotated Wireshark screenshots with the packet analysis: S7 and Modbus frame breakdowns (the `32 01` header, the function byte, DB/area/offset), the operation read off the wire, and the armed-versus-unprotected proof (a WRITE frame present at the Snort mirror but absent at the PLC port when armed = the drop shown on the wire, not only in a log), plus the OpenFlow `flow_mod` capture that installs the reactive rule. One representative annotated frame in the body, the full set with readings in the appendix. See CROSS_LAYER_VALIDATION_PLAN.md.
  4. Scenario testing in full: every attack surface, pivot point and attack strategy exercised, and the CARS response to each, where the body only summarises.
  5. Scripts and code, every program explained: for each script and module used in the build or the evaluation, state its role in the system, then reproduce and annotate its important working snippet(s) — not the whole file, the load-bearing lines — with a line-by-line explanation of what those lines do. At minimum cover:
     - Controller `cars_engine.py` (the lead example): the decision path `classify()` (role + operation, first-match RULEBOOK, to a tier), the criticality elevation (SENSITIVE -> FORBIDDEN on a CRITICAL asset), `select_response()` (the graded ALLOW..REFUSE ladder), the GUARD anti-spoof binding, the reactive-rule install (cookie `0x00CA`, the criticality-scaled `hard_timeout = 30 + 15w`), and the authenticated control API.
     - Detection and self-check: `snort_bridge.py` (Snort alert -> `/cars/respond`), `cars_flow_audit.py` (the 10 s poll against the trusted baseline and the drift verdict), `cars_remediation.py` (last-good restore).
     - Evaluation and proof harnesses: `cars_eval.py`, `cars_criticality_proof.sh`, `cars_wire_campaign.sh` and `_disarmed.sh`, `cars_campaign_lib.sh`, `cars_e2e.sh`, `cars_packet_proof.sh`, `cars_mttm.sh`, `cars_ics_battery.sh`.
     - Attack clients and process model: `s7_write.py`, `cars_fdi_overflow.py`, `mb_attack.py`, `cars_process.py`.
     Each entry gives: what it is, its role, and the annotated key excerpt. Use the `listings` package (as in Appendix A) with a short prose explanation per snippet.
  6. Extra work, the CARS intelligence dashboard: what it does, how it functions, and how it presents the live decisions and state.
  Body-to-appendix rule: for every test, evaluation, proof, log, event and output, if the body cannot hold the full content, the body shows the vital part and points to the appendix for the detailed showcase, analysis and elaboration.

Source material already written that feeds the chapters: DECISION_LOG.md (CC-1..CC-101), SYNC_STATE.md, EVALUATION_REPORT.md, GRAND_VALIDATION_REPORT.md, WIRE_VALIDATION_REPORT.md, CRITICALITY_FRAMEWORK.md, and the 06_Build source (cars_engine.py, cars_flow_audit.py, cars_eval.py, cars_campaign_lib.sh).

## 5. Citation base and discipline
- Real papers on disk (papers folder): Controller-in-the-Middle Attacks on SDN in ICS; AvantGuard (CCS 2013); MiniCPS; Reactive SDN for Securing ICS Environments; SDN approaches for intrusion response in Industrial (control systems); Replica-Based Moving Target Defense against Injection Attacks in SD-ICS; Oops I Did It Again (ICS testbeds); SoK taxonomy for ICS asset-discovery tools; Network Innovation using OpenFlow (survey); Programmable Data Planes for Digital Resilience in OT; Ensemble Learning for DDoS in SDN-based SCADA; SDN-based IDS (Manso et al. 2019); Towards Detection and Mitigation of Traffic Anomalies in SDN; DSSnet; Toward a Cyber-Resilient Microgrid using SDN; Multi-Layer Adaptive IDS (BAT-MC); Security/Control/Data planes review (traditional, AI, MTD); Alsabbagh; the IJCIP paper (S1874548213000243); the Samanis PhD thesis; plus the survey subfolder and "Notes from papers.docx".
- Discipline: build the .bib from metadata read out of each actual PDF (authors, exact title, venue, year, pages, publisher/DOI). Do not fill any field from memory. If a needed claim has no paper in this set, ask Amit to upload one before writing the sentence. Cross-check every in-text citation against the reference list before finalising.

## 6. Visual and presentation elements (full utilisation, all real)
We present the work visually as well as in prose. Every figure is either a diagram of the real system, a screenshot or photograph actually captured, or a chart plotting real measured data. No mock-ups, no illustrative-only numbers, no invented curves. Each figure carries a caption, a label, and a one-line statement of its source (which run, which capture, which file). Diagrams are drawn as clean vector graphics (TikZ or an equivalent) so they are crisp and editable; charts are generated from the captured data files.

Planned figures by chapter, with source and who captures:

- Background:
  - SDN and OpenFlow reference architecture (diagram, from cited literature).
  - Purdue / ICS zone reference model for asset criticality context (diagram, cited).
- Execution (Design and Implementation):
  - Physical testbed topology: 3 Dell nodes, 2 S7-1212C PLCs, HMI panel, wiring (architecture diagram) + hardware photographs (Amit photographs the rack, the two PLCs, the HMI, the switch/cabling).
  - Logical SDN fabric topology: bridges, dpids, ports, host roles and IPs (diagram, from the real ofport map).
  - Deployment diagram: what runs where (controller on Dell#2, OVS and Snort and remediation on Dell#1, Factory IO and TIA on the Windows node), with the control and data planes distinguished.
  - CARS engine pipeline: the three tables GUARD, POLICY (stateful), SWITCH, with match and action per table (block diagram).
  - Detection-to-response flow: packet, DPI classification, decision, flow-mod install, enforcement, self-heal (flow diagram).
  - Rulebook and criticality model as a matrix (role x operation x tier, and the asset criticality table with weights).
  - Response ladder as a graded diagram (ALLOW, MONITOR, THROTTLE, DEFLECT, ISOLATE, BLOCK, REFUSE) with the trigger and enforcement per rung.
  - Factory IO hardware-in-the-loop process flow: level sensor to PLC input image, OB30 control, valve outputs to the scene, closed loop (process flow diagram) + Factory IO scene screenshot + TIA OB30 and tag-table screenshots + HMI screen screenshot.
- Critical Evaluation:
  - Accuracy and false-positive matrix (structured table of the 27 cases) plus a TP/TN/FP/FN summary and a confusion-style summary.
  - Criticality sweep: a table and a bar chart of response and block duration across CRITICAL, HIGH, MEDIUM, LOW (from the dedicated sweep run).
  - Attack-chain diagram per campaign phase (the attacker path from recon to process impact).
  - Before-and-after process charts: tank level over time, armed versus unprotected, plotted from the captured DB7 time series (the disarmed overflow curve rising to ~195% against the armed curve held in band). This needs a clean per-second capture during the fresh runs.
  - Traffic-flow diagrams: armed (attacker cut at ingress, packet never reaches the PLC) versus unprotected (packet reaches the PLC), annotated with the wire evidence.
  - GUARD anti-spoof results: bar chart of spoofed packets sent versus dropped per identity.
  - Reaction-window illustration: timeline of the flood versus the isolate install.
  - Whole-campaign summary table: each capability, the unprotected outcome, the armed outcome, the evidence artefact.
  - Screenshots as evidence: Factory IO tank overflowing with the HMI reading empty (the deception), the dashboard decision log, and a packet view of the S7 write frame (Wireshark or tcpdump hex).
- Conclusion: an aims-versus-achievements table.

Capture responsibilities: Amit takes the hardware photographs and the on-screen Factory IO, TIA, and HMI screenshots during the fresh section runs. Claude produces the vector diagrams, generates the charts from the captured data files, and assembles the tables. For the before-and-after process charts we must log a per-second time series of the tank level during the fresh disarmed and armed runs, saved to file, so the curves are real.

## 7. Workflow
- Work section by section. For each section: agree the content, re-run the exact testbed slice or demo it needs, capture the evidence cleanly (figure or table or capture), then write the prose around that evidence. No prose ahead of its evidence.
- After drafting each section, self-check against section 1 (no unverified claim) and section 2 (no AI tells, no em dashes), and reconcile citations.
- Keep the running word count against the budget in section 3.
- The system is final and stable (implementation complete through CC-101). The task now is authored narrative plus clean captured proofs mapped to each chapter.
