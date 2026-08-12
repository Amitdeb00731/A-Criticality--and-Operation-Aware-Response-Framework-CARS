# Citation Verification Report (CC-5)

Verification pass over every web-sourced (🌐) citation in `MASTER_READING_LIST.md`,
per the no-hallucination / no-gap integrity rule. Method: re-search each item, confirm
it exists, check author/venue/year/ID against the publisher/arXiv record.

_Run: 2026-07-05_

## Headline result
**0 fabricated references. All 28 distinct web-sourced items are real and locatable.**
Local-folder papers were already verified (titles extracted from the PDFs). Corrections
below are metadata-level (year / authors / added DOI), not existence.

## Corrections applied (metadata only)
- **AI-driven 5G-SDN framework:** year **2026** (Frontiers in AI), not 2025. Authors: R. Shameli & S. Rajkumar. DOI 10.3389/frai.2026.1701944 (PMC12929375).
- **Digital Twin-Enhanced Incident Response:** authors **Allison, Smith, McLaughlin** (ARES 2023, DOI 10.1145/3600160.3600195).
- **Digital Twin-Driven IDS for SCADA:** author **A. Sayghe**, Sensors 25(16):4963, DOI 10.3390/s25164963.
- **D3O-IIoT:** add DOI **10.1038/s41598-025-33426-4** (Nature Sci Rep 2025; Wushishi et al.).
- **ITC (Intrusion Tolerant Controller):** add DOI **10.1016/j.cose.2023.103351** (Computers & Security vol 132, 2023).
- **TwinSec-IDS:** authors Krishnaveni, Sivamohan, Jothi, Chen, Sathiyanarayanan (Wiley CCPE 2025, DOI 10.1002/cpe.8334).
- **ML/DL SDN systematic review:** authors Doğan, Koçak, Alkan (IJIS 2025, DOI 10.1007/s10207-025-01114-z).
- **Zero Trust Architecture SLR:** authors Gambo & Almulhem; arXiv:2503.11659 (also JNSM 34(1):25, 2026).
- **Transformers/LLMs IDS survey:** author H. Kheddar (arXiv:2408.07583).
- **Reactive cyber deception:** journal version ScienceDirect S138912862600215X; earlier preprint **arXiv:2402.09191** ("Cyber Deception Reactive: TCP Stealth Redirection to On-Demand Honeypots", 2024).
- **Non-local attention IIoT-SCADA:** model "DeepNonLocalNN", Nature Sci Rep, Feb 2026 (s41598-026-37146-1).

## Two residual items to confirm at cite-time (honest flag)
- **CHAOS (Shi et al., 2017)** — well-established (Security and Communication Networks); exact article ID (Hindawi 3659167) not re-fetched this pass. Confirm before formal citation.
- **NIST SP 800-82** — cited as Rev. 2 (2015); **Rev. 3 was published in 2023**. Recommend citing **Rev. 3** as the current edition.

## Per-item status (web-sourced)
| # | Item (short) | Status | ID / DOI |
|---|--------------|--------|----------|
| 1 | Hammar, Optimal Security Response | ✅ verified | arXiv:2502.02541 |
| 2 | Enabling Dynamic Net Access Control (IDS+SDN) | ✅ verified | 10.1145/3309194.3309199 |
| 3 | Securing ICS: Automated Traffic Control + MTD | ✅ verified | S0140366425002099 |
| 4 | Deep RL IDS for SDN | ✅ verified | s41598-025-24869-w |
| 5 | Non-local attention IIoT-SCADA | ✅ verified | s41598-026-37146-1 |
| 6 | Transformers/LLMs IDS survey (Kheddar) | ✅ verified | arXiv:2408.07583 |
| 7 | AI-driven 5G-SDN federated RL | ✅ verified (yr fixed) | 10.3389/frai.2026.1701944 |
| 8 | P4Control (IEEE S&P 2024) | ✅ verified | arXiv:2405.14970 |
| 9 | Data Plane Programmability, industrial | ✅ verified | S1389128624002299 |
| 10 | Protocol-Aware P4 / MQTT | ✅ verified | arXiv:2601.07536 |
| 11 | Software-Defined TSN, cross-domain | ✅ verified | mdpi 2079-9292/13/7/1246 |
| 12 | P4-PSFP (TSN policing) | ✅ verified | arXiv:2311.07385 |
| 13 | TSN for Industrial Automation (survey) | ✅ verified | 10.1145/3695248 |
| 14 | TwinSec-IDS | ✅ verified | 10.1002/cpe.8334 |
| 15 | Digital Twin-Enhanced Incident Response | ✅ verified | 10.1145/3600160.3600195 |
| 16 | Digital Twin-Driven IDS for SCADA | ✅ verified | 10.3390/s25164963 |
| 17 | Reactive cyber deception | ✅ verified | S138912862600215X / arXiv:2402.09191 |
| 18 | D3O-IIoT (DRL deception) | ✅ verified | 10.1038/s41598-025-33426-4 |
| 19 | Survey of MTD in Power Grids | ✅ verified | arXiv:2409.18317 |
| 20 | CHAOS (SDN MTD) | ⚠ confirm ID | Hindawi 3659167 (2017) |
| 21 | Network Reconfiguration vs FDI | ✅ verified | 10.1007/978-3-032-01904-2_19 |
| 22 | CISA ZT Microsegmentation (Part One) | ✅ verified | CISA, 29 Jul 2025 |
| 23 | Zero Trust Architecture SLR | ✅ verified | arXiv:2503.11659 |
| 24 | Hammar & Stadler, Intrusion Tolerance | ✅ verified | arXiv:2404.01741 |
| 25 | ITC (intrusion-tolerant controller) | ✅ verified | 10.1016/j.cose.2023.103351 |
| 26 | ML/DL SDN systematic review | ✅ verified | 10.1007/s10207-025-01114-z |
| 27 | ML in ICS security (landscape) | ✅ verified | 10.1007/s10844-022-00753-1 |
| 28 | SWaT / WADI / HAI datasets (iTrust) | ✅ verified | iTrust SUTD |
| — | NIST SP 800-82 | ⚠ use Rev. 3 (2023) | NIST SP 800-82r3 |
| — | MiniCPS (also local) | ✅ verified | 10.1145/2808705.2808715 |

## Phase 8 additions (gap-closing, verified 2026-07-05)
All appeared in live search results (existence confirmed); metadata as below.
| Item | Status | ID / locator |
|------|--------|--------------|
| MITRE ATT&CK — Triton (TRITON/TRISIS) | ✅ verified | attack.mitre.org/software/S1009 |
| Process-aware security monitoring in ICS (review) | ✅ verified | IJCIP 2024, S187454822400060X |
| Safety & Security Co-Engineering of CPS (survey) | ✅ verified (authors TBC) | Future Internet 12(4):65, 10.3390/fi12040065 |
| ISA/IEC 62443 (3-2, 3-3) | ✅ standard (series) | IEC 62443-3-2 / -3-3 |
| Security Aspects of Zones & Conduits in IEC 62443 | ✅ verified | MDPI JCP 6(2):52 |
| IR Orchestration for AMI | ✅ verified | arXiv:2403.06907 |
| ICS reactive-response **metrics** paper | ❌ none found | GAP → define our own metrics |

**Honest note:** the evaluation-metrics gap is a genuine literature gap, not an omission —
no canonical source located. Treated as a contribution opportunity, not padded with a weak cite.

## Outcome
CC-5 resolved. The research contains **no hallucinated citations**. Residuals to finalise at
cite-time: CHAOS article ID; NIST → Rev. 3; Co-Engineering survey authors. Reading list now
covers the safety-centric thesis (Phase 8 added).
