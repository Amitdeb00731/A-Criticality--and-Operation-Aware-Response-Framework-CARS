# CARS: Reactive SDN for Securing ICS Environments

A criticality- and operation-aware SDN intrusion-response system for industrial control systems, built and validated on a hardware testbed with real Siemens S7-1212C PLCs and a live tank process.

MSc Cyber Security dissertation, University of Bristol.
Author: Amit Kiran Deb. Supervisor: Dr. Joseph Gardiner.

Repository: https://github.com/Amitdeb00731/A-Criticality--and-Operation-Aware-Response-Framework-CARS

---

## What this is

Automated intrusion response is rarely switched on in operational technology, and the reason is trust rather than detection: a defence that blocks traffic can cut the very process it is meant to protect. CARS addresses that barrier by conditioning its response on two properties that uniform blocking ignores: the **criticality** of the asset under attack, and the **industrial operation** recovered from the traffic itself, so that reading a value from a controller is treated differently from writing one. Responses are graded across a seven-rung ladder, bounded in time, reversible, and evidence-generating.

Detection is delegated to a deep-packet-inspection sensor (Snort); the software-defined network layer makes the graded decision and enforces it as OpenFlow rules.

### Headline results (from the live testbed)

- **100%** decision accuracy and **0%** false positives on the live process, across the tested space of source role, operation class and asset criticality; the accuracy result holds over a **2,078-case** labelled corpus (95% Wilson lower bound **0.9982**).
- Enforcement shown **on the wire**, not inferred from a log: an armed false-data injection was severed before its first write reached the PLC (0 writes versus 973 unprotected).
- Reaction window: median **7.6 ms** (95th percentile 38.4 ms, 99th 67.9 ms) over 100 autonomous trials, every trial ending in an ISOLATE.
- Late-stage hardening, all validated on the live testbed: an **event-driven flow-integrity monitor** that catches a sub-poll rule injection **30/30** at median 0.27 s (versus 5/30 for the 10 s poll); a **conduit-level cut** for NAT-collapsed identities so a shared gateway is no longer quarantined wholesale; and a read-only **process guardian** for the trusted-insider envelope.

The evaluation carries its boundaries honestly, including the trusted-insider case a network layer must not act on, and the late-stage defence-in-depth work that addresses part of it. A full independent audit of the report against its governing plan is in `report/AUDIT_REPORT.md`.

---

## Repository structure

```
Reactive_SDN_ICS/
├── report/                  The dissertation itself (LaTeX source)
│   ├── main.tex             Master file; build with pdflatex + bibtex
│   ├── 0X_*.tex             Chapters (intro, background, execution, evaluation, conclusion)
│   ├── abstract.tex ...     Front matter
│   ├── appendix.tex         Comprehensive appendix
│   ├── appendix_listings/   Code and config excerpts included by the appendix
│   ├── figures/             All figures (diagrams, charts, screenshots, photos)
│   ├── gap_evidence/        Raw before/after evidence for the late-stage gap fixes
│   └── references.bib       Bibliography (metadata read from the source PDFs)
├── 06_Build/                The CARS system: controller engine, sensors, services
│   ├── cars_engine.py       os-ken OpenFlow 1.3 controller (the decision core)
│   ├── snort_bridge.py      Snort alert -> controller response bridge
│   ├── cars_flow_audit.py   Flow-integrity self-check against a trusted baseline
│   ├── cars_remediation.py  Process-state last-good restore agent
│   ├── cars_process.py      Process model / control law reference
│   ├── cars_dashboard.py    Live operator dashboard (discovery-driven)
│   ├── cars-*.service        systemd units for the running services
│   ├── *.rules               Snort detection rules
│   └── *.md                  Build logs, as-built topology, cold-start notes
├── 07_Evaluation/           Evaluation harnesses and results (MTTM, response spectrum)
│   └── overnight/           Extended campaign: accuracy-at-scale, criticality behaviour,
│                            flow-integrity, reconnection jitter, and the Gap 1/2/4 fixes
│                            (harnesses under gap*/, raw data under results/)
├── 04_Testbed/              Testbed architecture, component list, Purdue mapping
├── 05_Execution/            Execution plan and tracker
├── 01_Literature_Review/    Literature review and reading list
├── 02_Research_Notes/       Working research notes
├── 03_Build_Scripts/        Document- and diagram-generation helpers
├── docs/                    Working records, organized by kind
│   ├── design/              Design notes, criticality framework, decision log, novelty
│   ├── validation/          Validation and verification reports, test matrices
│   ├── planning/            Report plan, roadmaps, session handoffs
│   ├── literature/          Reading list and paper maps
│   ├── offensive/           Attacker-VM setup and pen-test playbook (see ETHICS.md)
│   └── data/                Raw output dumps, allowlist, evaluation CSVs
└── _archive/                Superseded planning artefacts, kept for the record
```

---

## The CARS pipeline

CARS is realised as a three-table OpenFlow pipeline on Open vSwitch:

1. **Table 0 — GUARD.** Identity binding and anti-spoofing: each protected host is pinned to its ingress port, MAC and address; a packet claiming a protected address from any other port is dropped.
2. **Table 1 — POLICY.** A stateful stage using connection tracking, carrying the criticality- and operation-aware allowlist and a default-deny for protected assets. Reactive responses are installed here under cookie `0x00ca` with criticality-scaled, self-healing timeouts.
3. **Table 2 — SWITCH.** L2 learning and forwarding.

The response ladder runs ALLOW, MONITOR, THROTTLE, DEFLECT, ISOLATE, BLOCK, REFUSE, with the last reserved for the safety-critical loop (mirrored and alerted, never cut). A flow-integrity checker compares the live tables against a trusted baseline, and an authenticated control interface prevents silent disarming.

---

## Testbed

Three Dell nodes run the controller (Dell 2), the Open vSwitch fabric plus Snort and supporting services (Dell 1), and a second cell (Dell 3). Two Siemens S7-1212C PLCs (6ES7 212-1BE40-0XB0, firmware 4.2.3) drive a Factory IO tank-level process through the fabric, with a KTP700 operator panel and a Windows engineering workstation running TIA Portal. See `04_Testbed/` and `06_Build/AS_BUILT_TOPOLOGY.md`.

---

## Building the report

```bash
cd report
pdflatex main
bibtex main
pdflatex main
pdflatex main
```

Requires a full TeX Live (the class file `dissertation.cls` uses `algorithm2e`, `listings`, and the University of Bristol thesis template). The built `main.pdf` is not committed; it regenerates from source.

## Running the system

The controller is an os-ken application; the sensors and agents run as the `cars-*` systemd services in `06_Build/`. Python dependencies are listed in `06_Build/requirements.txt`. This is research code for an isolated testbed, not a turnkey deployment; see the ethics note below before running any offensive component.

---

## Ethics and responsible use

All offensive work in this project was conducted on an isolated, self-contained testbed with no connection to any production or external network. The attack tooling in this repository exists to substantiate and reproduce the evaluation of a **defence**; it is not a turnkey attack against any deployed system. See [ETHICS.md](ETHICS.md). Do not use any component of this repository against systems you do not own or have explicit permission to test.

---

## Citation

If you refer to this work, please cite it. See [CITATION.cff](CITATION.cff).

## License

Source code in this repository is released under the MIT License ([LICENSE](LICENSE)). The written dissertation (the contents of `report/`, and the planning and literature documents) is the author's academic work, © 2026 Amit Kiran Deb; it is shared for reference and is not licensed for redistribution as another author's own work.

## Acknowledgements

With thanks to Dr. Joseph Gardiner and the University of Bristol Cyber Security group.
