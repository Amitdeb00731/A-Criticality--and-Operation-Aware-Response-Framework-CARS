# Candidate references for CARS (13 core + optional)

All entries below are read from the actual PDFs already held in the papers folder (main folder or `survey/`), so every field traces to the source per REPORT_PLAN rule 5. Nothing is filled from memory. Two "optional" items carry a field that needs one confirmation before use, and are flagged.

Each entry: BibTeX (ready to paste into `references.bib`), what it is, why it supports CARS, and where to cite it.

---

## Core set (13) — directly or very closely supports CARS

### 1. Two-level IDS for ICS using P4 (closest architectural sibling)
Supports: **literature gap + implementation.** A whitelist/allowlist first level plus a DPI second level that updates the whitelist through an SDN controller — the same layered shape as CARS (proactive allowlist + reactive operation-aware DPI). The strongest single comparator for the CARS pipeline.
Cite in: Ch2 (related work), Ch3 (pipeline design rationale), Ch4 (comparison with related work).

```bibtex
@inproceedings{kabasele2018twolevel,
  author    = {Kabasele Ndonda, Gorby and Sadre, Ramin},
  title     = {A Two-level Intrusion Detection System for Industrial Control System Networks using {P4}},
  booktitle = {Proceedings of the 5th International Symposium for ICS \& SCADA Cyber Security Research (ICS-CSR)},
  year      = {2018},
  publisher = {BCS Learning \& Development (eWiC)},
  doi       = {10.14236/ewic/ICS2018.4}
}
```

### 2. Cloud-based IDS/IPS for ICS using SDN (motivation + related work)
Supports: **motivation + literature gap.** Argues passive, locally-placed ICS IDS lack network visibility and manual upkeep; proposes an SDN-based detect-and-prevent framework, motivated by the 2015 Ukraine grid attack. Good source for the "detection is not the barrier; reactive deployment is" motivation.
Cite in: Ch1 (motivation), Ch2 (related work).

```bibtex
@inproceedings{brugman2019cloud,
  author    = {Brugman, Jonathon and Khan, Mohammed and Kasera, Sneha and Parvania, Masood},
  title     = {Cloud Based Intrusion Detection and Prevention System for Industrial Control Systems Using Software Defined Networking},
  booktitle = {2019 Resilience Week (RWS)},
  year      = {2019},
  publisher = {IEEE},
  isbn      = {978-1-7281-2135-2}
}
```

### 3. DIDEROT: IDS/IPS for DNP3 SCADA (operation-aware IDPS)
Supports: **approach + related work.** A protocol-aware detection-and-prevention system for an industrial protocol (DNP3), pairing anomaly detection with active prevention — a direct analogue to CARS's operation-aware DPI-plus-response, in a different protocol.
Cite in: Ch2 (related work), Ch4 (comparison).

```bibtex
@inproceedings{radoglou2020diderot,
  author    = {Radoglou-Grammatikis, Panagiotis and Sarigiannidis, Panagiotis and Efstathopoulos, George and Karypidis, Paris-Alexandros and Sarigiannidis, Antonios},
  title     = {{DIDEROT}: An Intrusion Detection and Prevention System for {DNP3}-based {SCADA} Systems},
  booktitle = {Proceedings of the 15th International Conference on Availability, Reliability and Security (ARES '20)},
  year      = {2020},
  month     = aug,
  address   = {Virtual Event, Ireland},
  publisher = {ACM},
  doi       = {10.1145/3407023.3409314}
}
```

### 4. Virtual incident response functions in control systems (SDN/NFV response for ICS)
Supports: **approach.** SDN/NFV-based virtualised incident-response functions for control systems — the reactive-response direction CARS takes, from the same group as the IEEE Software paper already cited (this is the fuller Computer Networks journal treatment).
Cite in: Ch2 (related work), Ch3 (response design). Note: companion to the already-cited `murillo2018leveraging`; keep both or pick one.

```bibtex
@article{murillo2018virf,
  author    = {Murillo Piedrahita, Andr{\'e}s F. and Gaur, Vikram and Giraldo, Jairo and C{\'a}rdenas, Alvaro A. and Rueda, Sandra Julieta},
  title     = {Virtual incident response functions in control systems},
  journal   = {Computer Networks},
  volume    = {135},
  pages     = {147--159},
  year      = {2018},
  publisher = {Elsevier},
  doi       = {10.1016/j.comnet.2018.01.040}
}
```

### 5. Accurate modeling of Modbus/TCP for intrusion detection (Modbus DPI grounding)
Supports: **implementation.** The canonical DFA model of Modbus/TCP for IDS; grounds the Modbus operation-recovery and detection rules CARS uses at the sensor. High-quality, widely cited.
Cite in: Ch2 (background, protocol IDS), Ch3 (detection / DPI rules).

```bibtex
@article{goldenberg2013modbus,
  author    = {Goldenberg, Niv and Wool, Avishai},
  title     = {Accurate modeling of {Modbus/TCP} for intrusion detection in {SCADA} systems},
  journal   = {International Journal of Critical Infrastructure Protection},
  volume    = {6},
  number    = {2},
  pages     = {63--75},
  year      = {2013},
  publisher = {Elsevier},
  doi       = {10.1016/j.ijcip.2013.05.001}
}
```

### 6. SDN firewall for Industry 4.0 manufacturing systems (proactive allowlist layer)
Supports: **implementation + approach.** An SDN-based firewall/whitelisting for industrial manufacturing traffic; supports the CARS proactive layer (identity binding, conduit allowlist, default-deny).
Cite in: Ch2 (related work), Ch3 (proactive policy).

```bibtex
@article{tsuchiya2018firewall,
  author    = {Tsuchiya, Akihiro and Fraile, Francisco and Koshijima, Ichiro and {\'O}rtiz, Angel and Poler, Ra{\'u}l},
  title     = {Software defined networking firewall for industry 4.0 manufacturing systems},
  journal   = {Journal of Industrial Engineering and Management},
  volume    = {11},
  number    = {2},
  pages     = {318--333},
  year      = {2018},
  publisher = {OmniaScience},
  doi       = {10.3926/jiem.2534}
}
```

### 7. Programmable Data Planes for Increased Digital Resilience in OT Networks (recent, OT data-plane)
Supports: **approach + future work.** Recent (2025) treatment of data-plane programmability for OT security; supports the data-plane enforcement argument and the P4/stateful-fabric future work.
Cite in: Ch2 (background, programmable data planes), Ch5 (future work).

```bibtex
@article{holik2025pdp,
  author  = {Holik, Filip and Cook, Marco M. and Li, Xicheng and Shah, Awais Aziz and Pezaros, Dimitrios},
  title   = {Programmable Data Planes for Increased Digital Resilience in {OT} Networks},
  journal = {IEEE Communications Magazine},
  volume  = {63},
  number  = {7},
  year    = {2025},
  publisher = {IEEE},
  doi     = {10.1109/MCOM.001.2400446}
}
```

### 8. Toward a Cyber Resilient and Secure Microgrid Using SDN (SDN resilience + spec-based IDS)
Supports: **motivation + approach.** Uses SDN's global view for self-healing and specification-based intrusion detection in a critical-infrastructure setting; supports the SDN-for-OT-resilience motivation and the self-healing framing.
Cite in: Ch1/Ch2 (motivation, SDN for CI resilience).

```bibtex
@article{jin2017microgrid,
  author  = {Jin, Dong and Li, Zhiyi and Hannon, Christopher and Chen, Chen and Wang, Jianhui and Shahidehpour, Mohammad and Lee, Cheol Won},
  title   = {Toward a Cyber Resilient and Secure Microgrid Using Software-Defined Networking},
  journal = {IEEE Transactions on Smart Grid},
  volume  = {8},
  number  = {5},
  pages   = {2494--2504},
  year    = {2017},
  publisher = {IEEE},
  doi     = {10.1109/TSG.2017.2703911}
}
```

### 9. SDN-Based IDS for Early Detection and Mitigation of DDoS (reactive source-mitigation method)
Supports: **approach.** Reactively impairs attacks at their source by having an IDS notify the SDN controller to push forwarding decisions — the same mirror-detect-then-controller-reacts loop CARS uses (though DDoS/IoT rather than ICS).
Cite in: Ch2 (related work), Ch3 (detection-to-response path).

```bibtex
@article{manso2019ddos,
  author  = {Manso, Pedro and Moura, Jos{\'e} and Serr{\~a}o, Carlos},
  title   = {{SDN}-Based Intrusion Detection System for Early Detection and Mitigation of {DDoS} Attacks},
  journal = {Information},
  volume  = {10},
  number  = {3},
  pages   = {106},
  year    = {2019},
  publisher = {MDPI},
  doi     = {10.3390/info10030106}
}
```

### 10. Network Reconfiguration to Mitigate Stealthy FDI in SCADA (SDN-MTD vs FDI)
Supports: **approach + future work.** SDN-based moving-target defence against stealthy false-data-injection in SCADA; directly relevant to the CARS FDI scenario and the deception/MTD future-work comparison.
Cite in: Ch4 (FDI discussion), Ch5 (future work).

```bibtex
@inproceedings{kpoze2025reconfig,
  author    = {Kpoze, Aur{\'e}lie and Degila, Jules and Ahouandjinou, Arnaud},
  title     = {Leveraging Network Reconfiguration to Mitigate Stealthy {FDI} Attacks in Smart Grid {SCADA} Systems by Exploiting Attacker Uncertainty},
  booktitle = {Towards New e-Infrastructure and e-Services for Developing Countries (AFRICOMM 2024)},
  series    = {Lecture Notes of the Institute for Computer Sciences, Social Informatics and Telecommunications Engineering (LNICST)},
  volume    = {652},
  pages     = {293--314},
  year      = {2025},
  publisher = {Springer},
  doi       = {10.1007/978-3-032-01904-2_19}
}
```

### 11. Ensemble Learning for DDoS Detection in SDN-Based SCADA (SDN-SCADA reactive detection)
Supports: **approach.** Detection of DDoS in SDN-based SCADA; a data-driven point of contrast to the CARS rule-based, operation-aware decision (useful to show why CARS avoids the ML false-positive risk on a live process).
Cite in: Ch2 (related work), Ch4 (comparison / why not ML).

```bibtex
@article{oyucu2024ensemble,
  author  = {Oyucu, Saadin and Polat, Onur and T{\"u}rko{\u{g}}lu, Muammer and Polat, H{\"u}seyin and Aks{\"o}z, Ahmet and A{\u{g}}da{\c{s}}, Mehmet Tevfik},
  title   = {Ensemble Learning Framework for {DDoS} Detection in {SDN}-Based {SCADA} Systems},
  journal = {Sensors},
  volume  = {24},
  number  = {1},
  pages   = {155},
  year    = {2024},
  publisher = {MDPI},
  doi     = {10.3390/s24010155}
}
```

### 12. Survey of Moving Target Defense in Power Grids (MTD framing for future work)
Supports: **background + future work.** A comprehensive MTD survey; frames the MTD alternative to CARS block-and-maintain alongside the replica-MTD and Samanis references already cited.
Cite in: Ch2 (background, deception/MTD), Ch5 (future work).

```bibtex
@article{lakshminarayana2024mtd,
  author  = {Lakshminarayana, Subhash and Chen, Yexiang and Konstantinou, Charalambos and Mashima, Daisuke and Srivastava, Anurag K.},
  title   = {Survey of Moving Target Defense in Power Grids: Design Principles, Tradeoffs, and Future Directions},
  journal = {arXiv preprint arXiv:2409.18317},
  year    = {2024},
  eprint  = {2409.18317},
  archivePrefix = {arXiv},
  primaryClass  = {eess.SY}
}
```

### 13. ROS-Defender: SDN-Based Security Policy Enforcement (per-flow policy enforcement)
Supports: **approach.** SDN-based, dynamic per-flow security-policy enforcement (in robotics); a cross-domain precedent for the CARS model of enforcing graded policy on flows from a controller.
Cite in: Ch2 (related work, SDN policy enforcement).

```bibtex
@inproceedings{rivera2019rosdefender,
  author    = {Rivera, Sean and Lagraa, Sofiane and Nita-Rotaru, Cristina and Becker, Sheila and State, Radu},
  title     = {{ROS}-Defender: {SDN}-Based Security Policy Enforcement for Robotic Applications},
  booktitle = {2019 IEEE Security and Privacy Workshops (SPW)},
  year      = {2019},
  publisher = {IEEE},
  doi       = {10.1109/SPW.2019.00030}
}
```

---

## Flagged fields — resolved

### 14. Abdi et al. 2024 — SDN security review (WIRED IN)
Resolved: the on-disk PDF was an accepted preprint with a placeholder DOI and "VOLUME 11, 2023". The published record (IEEE Xplore) is **IEEE Access, vol. 12, pp. 69941–69980, 2024, DOI 10.1109/ACCESS.2024.3393548**. Passes honesty (real metadata confirmed + legitimate background survey). Added to `references.bib` as `abdi2024sdnreview`.

```bibtex
@article{abdi2024sdnreview,
  author    = {Abdi, Abdinasir Hirsi and Audah, Lukman and Salh, Adeb and Alhartomi, Mohammed A. and Rasheed, Haroon and Ahmed, Salman and Tahir, Ahmed},
  title     = {Security Control and Data Planes of {SDN}: A Comprehensive Review of Traditional, {AI}, and {MTD} Approaches to Security Solutions},
  journal   = {IEEE Access}, volume = {12}, pages = {69941--69980}, year = {2024},
  publisher = {IEEE}, doi = {10.1109/ACCESS.2024.3393548}
}
```

### Alsabbagh et al. 2023 — OpenPLC Aqua (HELD, not wired in)
Metadata now fully resolved from the GI digital library (which hosts the identical PDF): INFORMATIK 2023, 8th Industrial Automation and Control Systems Workshop (IACS 2023), Berlin, 26–29 Sept 2023; Gesellschaft für Informatik, Bonn; DOI 10.18420/inf2023_206; ISBN 978-3-88579-731-9; pp. 2085–2096.
**Decision: held out of `references.bib`.** The metadata passes, but the relevance does not clear the "directly or very closely supports" bar: the paper hardens the *OpenPLC soft-PLC* webserver (credential encryption, TLS, whitelisting) and is not about SDN network response or S7/Modbus operation-aware defence. Citing it in CARS would be padding, which Rule 1 forbids. The verified entry is kept here in case a specific PLC-insecurity claim later needs it:

```bibtex
@inproceedings{alsabbagh2023openplc,
  author    = {Alsabbagh, Wael and Kim, Chaerin and Langend{\"o}rfer, Peter},
  title     = {No Attacks Are Available: Securing the {OpenPLC} and Related Systems},
  booktitle = {INFORMATIK 2023 -- Designing Futures (8th Industrial Automation and Control Systems Workshop, IACS 2023)},
  series    = {Lecture Notes in Informatics (LNI)},
  pages     = {2085--2096}, year = {2023}, address = {Berlin, Germany},
  publisher = {Gesellschaft f{\"u}r Informatik e.V.}, doi = {10.18420/inf2023_206}, isbn = {978-3-88579-731-9}
}
```

## Other optional / lower priority (available in the papers folder)
- **Hannon et al., "DSSnet"** — SDN + power-distribution simulation testbed; only if another grid/SDN testbed cite is wanted (MiniCPS and "Oops I Did It Again" already cover testbeds).
- **Bose et al. 2024, "Multi-Layer Adaptive IDS ... BAT-MC Model"**, ICCES 2024, doi 10.1109/ICCES63552.2024.10859339 — generic ML SDN IDS; lower relevance.
- **Kausar et al. 2021, "Towards Detection and Mitigation of Traffic Anomalies in SDN"**, ICTC 2021, doi 10.1109/ICTC52510.2021.9621029 — generic SDN anomaly detection; lower relevance.

---

## Coverage against the five support areas
- Motivation: brugman2019cloud, jin2017microgrid, (Alsabbagh).
- Literature gap: kabasele2018twolevel, brugman2019cloud, (Abdi survey).
- Implementation: kabasele2018twolevel, goldenberg2013modbus, tsuchiya2018firewall, holik2025pdp.
- Approach: radoglou2020diderot, murillo2018virf, manso2019ddos, kpoze2025reconfig, oyucu2024ensemble, rivera2019rosdefender.
- Goal / future work: holik2025pdp, kpoze2025reconfig, lakshminarayana2024mtd.
