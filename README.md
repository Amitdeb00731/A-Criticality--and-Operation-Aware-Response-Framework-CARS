# CARS — Criticality- and Operation-Aware SDN Intrusion Response for ICS

A reactive intrusion-response framework for industrial control networks that decides on two axes a uniform block ignores — the **criticality** of the asset under attack and the **industrial operation** recovered from the packet — and enforces a **bounded, reversible, evidence-generating** response as OpenFlow rules. Built and validated on a hardware testbed with real Siemens S7-1212C PLCs and a live tank process, and packaged here as an installable framework with a no-hardware emulation.

MSc Cyber Security dissertation, University of Bristol · Author: Amit Kiran Deb · Supervisor: Dr. Joseph Gardiner.

---

## Why

Automated intrusion response is rarely switched on in operational technology, and the reason is trust, not detection: a defence that blocks traffic can cut the very process it protects. CARS conditions its response on the asset's criticality and the operation in the packet — reading a value is treated differently from writing one, and a forbidden write on a CRITICAL PLC differently from one on a low-value unit — so an automatic response can be armed on a live process. Detection is delegated to a deep-packet-inspection sensor (Snort); the SDN layer makes the graded decision and enforces it.

## Try it

```bash
# validate a policy (any machine)
cd framework && pip install -e . && cars config validate examples/site.testbed.yaml

# run a full defended attack with NO hardware (Linux host with root, Mininet, Snort)
pip install -e '.[controller,emulation]'
CARS_SITE=examples/site.testbed.yaml osken-manager ../06_Build/cars_engine.py   # terminal A
sudo emulation/demo.sh                                                          # terminal B
```

See **[`framework/docs/QUICKSTART.md`](framework/docs/QUICKSTART.md)** and **[`framework/docs/ARCHITECTURE.md`](framework/docs/ARCHITECTURE.md)**.

> **No ICS hardware needed.** The emulation runs the full defended-attack demo on a single Linux machine — no PLCs, switches or cabling. Real hardware is only for reproducing the exact physical measurements. Full requirements and the three hardware tiers are in **[`HARDWARE.md`](HARDWARE.md)**.

## Headline results (from the live testbed)

- **100%** decision accuracy and **0%** false positives on the live process; the accuracy holds over a **2,078-case** labelled corpus (95% Wilson lower bound **0.9982**).
- Enforcement shown **on the wire**: an armed false-data injection was severed before its first write reached the PLC (**0 writes vs 973** unprotected).
- Reaction window: median **7.6 ms** (99th pct 67.9 ms) over 100 autonomous trials, every trial ending in an ISOLATE.
- Late-stage hardening, all validated live: an event-driven flow-integrity monitor (sub-poll injection caught **30/30** at median 0.27 s vs 5/30 for the 10 s poll), a conduit-level cut for NAT-collapsed identities, and a read-only process guardian for the trusted-insider envelope.

The evaluation carries its boundaries honestly (`framework/LIMITATIONS.md`, and the report's Threats to Validity), including the trusted-insider case a network layer must not act on.

## The pipeline

A three-table OpenFlow pipeline on Open vSwitch:

1. **Table 0 — GUARD.** Identity binding / anti-spoofing: a protected address from the wrong port is dropped.
2. **Table 1 — POLICY.** Stateful (connection tracking): established flow, then allowlisted conduit, then any reactive rule (cookie `0x00ca`, criticality-scaled self-healing timeout), then default-deny.
3. **Table 2 — SWITCH.** L2 learning and forwarding.

The response ladder is ALLOW, MONITOR, THROTTLE, DEFLECT, ISOLATE, BLOCK, REFUSE (REFUSE reserved for the safety loop — mirrored and alerted, never cut). A flow-integrity checker compares the live tables to a trusted baseline; an authenticated control interface prevents silent disarming.

## Repository layout

```
Reactive_SDN_ICS/
├── framework/        Installable framework: config-driven engine overlay, CLI,
│                     emulation (software PLCs + Mininet), tests, CI, docs, Docker
├── 06_Build/         The CARS system as built on the testbed: cars_engine.py
│                     (os-ken OpenFlow 1.3 controller), snort_bridge, flow-audit,
│                     remediation, dashboard, Snort rules, systemd units, harnesses
├── 07_Evaluation/    Evaluation harnesses + the curated results the report cites
│                     (raw output is reproduced by re-running; see REPRODUCE.md)
├── report/           The dissertation (LaTeX source, figures, bibliography)
├── docs/             Design notes, validation reports, and the report plan
├── REPRODUCE.md      How to reproduce the results (system, emulation, report)
├── BUILD.md          How to build the framework, the Docker image, and the report
├── CITATION.cff · CHANGELOG.md · LICENSE · ETHICS.md
```

## Reproduce and build

- **[`REPRODUCE.md`](REPRODUCE.md)** — reproduce the decision accuracy, the reaction window, and the defended-attack demo (hardware or emulation).
- **[`BUILD.md`](BUILD.md)** — install the framework, build the controller Docker image, and build the dissertation PDF.

## Testbed

A controller node, three OpenFlow switches (`ovs1` for Cell-1, `ovsgw` the gateway, `ovs2` for Cell-2) and two Siemens S7-1212C PLCs (6ES7 212-1BE40-0XB0, firmware 4.2.3) driving a Factory IO tank process, with a KTP700 operator panel and a Windows engineering workstation running TIA Portal. Deployment detail is in `06_Build/AS_BUILT_TOPOLOGY.md` and the report's Chapter 3.

## Ethics and responsible use

All offensive work was on an isolated, self-contained testbed with no production or external connectivity. The attack clients here exist to substantiate and reproduce the evaluation of a **defence**; they are for research and authorised testing only. See [ETHICS.md](ETHICS.md) and `framework/SECURITY.md`. Do not use any component against systems you do not own or have explicit permission to test.

## Citation and licence

Cite via [CITATION.cff](CITATION.cff). Source code is MIT ([LICENSE](LICENSE)); the written dissertation in `report/` is the author's academic work, © 2026 Amit Kiran Deb, shared for reference and not licensed for redistribution as another author's own.

With thanks to Dr. Joseph Gardiner and the University of Bristol Cyber Security group.
