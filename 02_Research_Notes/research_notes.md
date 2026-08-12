# Research Notes — Reactive SDN for ICS

Working notes behind the literature review. Anchor reference is the Etxezarreta et al.
(2023) survey; individual proposals below are as discussed there unless a direct link is given.

## Why SDN for ICS
- Centralized control plane + global network view + programmability -> coordinated,
  automated response to incidents (block/redirect/re-route) not possible with static config.
- ICS constraint: availability & integrity dominate; controls must not break real-time /
  deterministic comms or process safety (NIST SP 800-82).
- Double-edged: controller is a single point of failure and a DoS target; rule-install
  latency and controller throughput can bottleneck under load.

## Taxonomy of SDN-based intrusion response in ICS (Etxezarreta et al. 2023)
1. **Dynamic traffic filtering** — install/update flow rules to allow, drop, mirror, redirect;
   allowlists for ICS protocols. (Most relevant to this project.)
2. **Network survivability & reconfiguration** — re-route around compromised nodes to keep
   process running (e.g. defeating stealthy FDI attacks in smart-grid SCADA).
3. **Moving Target Defense (MTD)** — randomize IP addresses / flow paths (proactive or reactive)
   to shrink attacker reconnaissance window. e.g. CHAOS (Shi et al. 2017).
4. **Honeypot-based response** — redirect suspect traffic to a decoy ICS process for
   containment + deep inspection. e.g. MimePot (Bernieri et al.), Petroulakis et al. service chaining.

Note: most proposals act in the CONTROL plane; only a minority push enforcement to the
DATA plane (e.g. P4) — matters for real-time performance.

## Core mechanism: IDS -> controller -> action
Response vocabulary:
- **Allow** — permit known-good flow.
- **Block / quarantine** — deny outright (right action for an unseen device that alerts).
- **Mirror** — permit but copy to DPI/monitoring for deeper inspection.
- **Redirect** — steer to honeypot / forensic appliance without disrupting rest of network.

Rule installation trade-off:
- **Reactive** install (on first packet) = flexible/dynamic, but adds first-packet latency + controller load.
- **Proactive** install = fast forwarding, less adaptive.
- Practical ICS system blends: pre-install for known critical loops, react for anomalous/unseen.
- Inspection appliances lack bandwidth to see all traffic -> mirror/redirect selectively.

Safety-preserving response (key theme): can't default to "block everything suspicious" —
cutting a control loop can endanger the process. Piedrahita et al. substitute estimated
values for anomalous sensor readings so the process keeps running.

## Key primary works
- **Piedrahita et al. (2018), IEEE Software** — SDN + IDS on NFV; compromised water-level
  sensor; model-based deviation -> controller substitutes estimated values -> safe operation.
  Closest prior work to this project's objective. Evaluated by extending MiniCPS.
- **Ndonda & Sadre** — two-level IDPS; L1 = P4 Modbus allowlist on switches, L2 = DPI (Bro/Zeek);
  L2 detection updates L1 allowlist so attack later caught at line rate. Closes detect->block loop.
- **Tsuchiya et al.** — SDN ICS firewall: transparent + temporal + spatial (OPC UA) filtering.
- **Brugman et al.** — cloud IDPS via NFV; controller as IP/protocol firewall; drop flagged flows.
- **Rivera et al.** — policy-engine on controller; domain rules -> SDN actions (allow/drop/log/copy);
  tested in Mininet + Gazebo robot sim.
- **Melis et al.** — controller modules to ease policy definition + verification (NetPlumber).
- **Shi et al. (2017)** — CHAOS SDN MTD (host/port/path obfuscation).

## Tools / testbeds
- **Ryu** (Python) — defense logic as controller apps; common research choice.
- **Mininet + Open vSwitch** — network emulation. Reported IDS overhead ~0.016 ms latency, ~5% CPU.
- **MiniCPS** (Antonioli & Tippenhauer 2015) — de-facto standard for CPS security research.
- **Modbus/TCP** two-tank process (PLCs = slaves, HMI = master); DNP3 also appears.
- **P4** — data-plane allowlist filtering for latency-sensitive enforcement.

## Research gaps -> project positioning
1. Generic, source-agnostic event ingestion (accept standardized indicators from any IDS/service).
2. Device-aware differentiated responses (block unseen device vs redirect critical service).
3. Safety-constrained automation (guarantee action stays within a defined safety envelope).
4. Lightweight data-plane enforcement / localized mitigation at switch level (survey-noted gap).
5. Controller resilience under attack (reactive designs increase control-plane reliance).

## Sources (links)
- Etxezarreta et al. 2023, survey: https://www.sciencedirect.com/science/article/pii/S1874548223000288
  (open-access copy: Mondragon University repository)
- Piedrahita et al. 2018: https://www.scitepress.org/Papers/2019/73595/73595.pdf
- Ndonda & Sadre (P4/Modbus): https://www.scienceopen.com/hosted-document?doi=10.14236/ewic/ICS2018.4
- Shi et al. 2017 (CHAOS): https://www.hindawi.com/journals/scn/2017/3659167/
- SDN automated traffic control + MTD for ICS DDoS: https://www.sciencedirect.com/science/article/pii/S0140366425002099
- Anomaly IDS + SDN dynamic access control (ACM): https://dl.acm.org/doi/10.1145/3309194.3309199
- Ryu/Mininet ICS IDS testbed: https://www.researchsquare.com/article/rs-6092259/v1
- NIST SP 800-82 Rev.2: https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-82r2.pdf
