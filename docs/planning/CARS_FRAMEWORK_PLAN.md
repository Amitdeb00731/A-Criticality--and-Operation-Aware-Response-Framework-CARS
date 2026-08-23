# CARS as an installable framework — design and migration roadmap

Target chosen: **emulation for anyone**. Someone with no Siemens hardware should be able to `pip install` CARS, run one command, and watch a defended attack end to end; someone *with* a testbed should be able to point CARS at their own network by writing a config, not editing code.

This is the code analogue of the Chapter 3 generalisation: separate the **portable core** from the **site-specific instantiation**, put **adapters** around the swappable parts, and add an **emulation layer** so the hardware is optional.

---

## 1. Design principles

1. **Portable core vs. site config.** The engine (`classify`, criticality elevation, `select_response`, GUARD binding, the three-table install) stays general. Everything site-specific — addresses, MACs, ofports, roles, conduits, rulebook, criticality tiers, timeouts — moves out of the code into one documented config file. Adopting CARS then means writing `site.yaml` for your network.
2. **Adapters at the boundaries** so components are swappable and CARS becomes a *framework*, not a script:
   - **Detection adapter**: Snort today (could be Suricata/Zeek/P4) → normalises to an operation event posted to `/cars/respond`.
   - **Southbound adapter**: OVS + OpenFlow 1.3 via os-ken → enforcement actions (drop, meter, redirect) behind an interface.
   - **Asset registry / rulebook / criticality**: data, not code.
3. **Emulation is first-class.** The demo path must need no hardware, yet run real S7/Modbus, real Snort, real OpenFlow.
4. **Honesty carried over.** The documented gaps (unauthenticated `/cars/respond`, plaintext control channel, TCP-reset-on-quarantine, per-cell sensing) live in a `LIMITATIONS` / `SECURITY.md`, and offensive attack clients ship under a clear research-use notice.

---

## 2. The emulation layer (the key deliverable)

The important design decision: **reuse the real components; swap only the physical PLC.**

| Real testbed | Emulation-for-anyone |
|---|---|
| Siemens S7-1200 PLC | **snap7 server** (python-snap7 server mode) answering S7comm, driven by `cars_process.py` (the tank model) |
| Modbus unit | **pymodbus server** with the same register map |
| OVS fabric (OF 1.3) | **Mininet** OVS bridges (native OVS, OF 1.3) — same fabric |
| Snort on a SPAN mirror | **Snort** on a Mininet OVS mirror port — same sensor, same `cars.rules` |
| os-ken CARS controller | **unchanged** — the real `cars_engine.py` |
| Kali attack clients | the same `s7_write.py` / `mb_attack.py` / `cars_fdi_overflow.py`, gated as research-use |

Because the controller, Snort, OVS and the S7/Modbus wire traffic are all genuine, the emulated demo reproduces the paper's core result honestly — a forbidden S7 write is recovered by DPI and isolated with a `0x00ca` flow-mod — with the only substitution being a software PLC in place of the Siemens CPU. State that substitution plainly in the docs.

**`cars demo` flow:** bring up the two-cell Mininet topology + snap7/pymodbus PLC servers + Snort + controller; launch a forbidden operation from an unregistered host; show the isolate installed, the write blocked at the fabric, and the decision log — all in one terminal, no hardware.

Option: use **Containernet** (Mininet + Docker) if we want each host/PLC/sensor in its own container for cleaner isolation and a `docker-compose` story.

---

## 3. Target repository structure

```
cars/
├── cars/                      # installable Python package
│   ├── engine/                # classify, criticality elevation, select_response, GUARD, pipeline install
│   ├── adapters/
│   │   ├── detection/         # snort bridge: alert -> normalised operation event
│   │   └── southbound/        # os-ken OpenFlow 1.3 enforcement (drop/meter/redirect)
│   ├── api/                   # REST: /cars/respond (feed) + authenticated control endpoints
│   ├── config/                # schema + loader
│   └── cli.py                 # cars run | demo | verify
├── emulation/                 # the adoption layer (no hardware needed)
│   ├── topo.py                # Mininet/Containernet two-cell topology
│   ├── plc/                   # snap7 S7 server, pymodbus server, cars_process tank
│   ├── attacks/               # research-use attack clients (gated)
│   └── demo.sh                # one-command defended-attack demo
├── detection/                 # snort.conf + cars.rules
├── deploy/                    # docker-compose, systemd units (real deployment)
├── examples/                  # site.yaml, rulebook.yaml, criticality.yaml
├── docs/                      # quickstart, architecture (reuse Ch3 figures), config-reference, porting, LIMITATIONS
├── tests/                     # unit (engine) + integration (the demo as a test)
├── pyproject.toml
├── README.md   LICENSE   CONTRIBUTING.md   SECURITY.md
```

---

## 4. Config schema (`site.yaml`) — sketch

```yaml
controller: { of_version: "1.3", listen: "0.0.0.0:6653", api: "10.10.10.1:8080" }
criticality: { tiers: {CRITICAL: 3, HIGH: 2, MEDIUM: 1, LOW: 0}, timeout_base: 30, timeout_step: 15 }
assets:
  - { name: PLC1, ip: 10.0.0.10, mac: "..", role: plc, tier: CRITICAL, switch: ovs1, ofport: 3 }
  - { name: HMI1, ip: 10.0.0.9,  mac: "..", role: hmi, tier: HIGH,     switch: ovs1, ofport: 4 }
conduits:                      # proactive allowlist
  - { src: HMI1, dst: PLC1, dport: 102 }
rulebook:                      # first-match (src_role, dst_role, operation) -> tier
  - { src: hmi, dst: plc, op: any,     tier: CRITICAL }   # safety loop, never enforced
  - { src: any, dst: plc, op: control, tier: FORBIDDEN }
detection: { sensor: snort, alert: "/var/log/snort/alert", cooldown_s: 3 }
```

Everything the engine currently hardcodes is expressed here; the loader validates it against a schema and the engine consumes it.

---

## 5. Packaging, CLI, docs

- **Package:** `pyproject.toml`, pinned deps (os-ken, python-snap7, pymodbus, ryu/os-ken, requests). `pip install -e .` then `cars ...`.
- **CLI:** `cars run --config site.yaml` (real fabric), `cars demo` (emulation), `cars verify` (flow-integrity check).
- **Docs:** 5-minute emulation quickstart; architecture doc reusing the Chapter 3 diagrams (topology, pipeline, decision flow); config reference; "port it to your network" guide; `LIMITATIONS.md` mirroring the dissertation's Threats-to-Validity honestly.
- **CI:** lint + run `cars demo` headless as an integration test, so the demo can never silently rot.

---

## 6. Phased migration (each phase independently shippable)

- **Phase 0 — hygiene:** `LICENSE` (pick one), `README` skeleton, `SECURITY.md`, `.gitignore`, dependency pinning.
- **Phase 1 — extract config:** move hardcoded IPs/roles/conduits/rulebook into `site.yaml` + a loader; engine reads config. *(This is the exact code analogue of the Ch3 generalisation.)*
- **Phase 2 — package + CLI:** `cars run --config` works on the real testbed unchanged.
- **Phase 3 — emulation:** Mininet topology + snap7/pymodbus PLC servers + `cars_process`; `cars demo` runs the defended attack with no hardware.
- **Phase 4 — docs + CI:** quickstart, architecture, porting, LIMITATIONS; demo-as-test.
- **Phase 5 — polish + release:** `docker-compose`, tagged release, and a Zenodo DOI (which also gives the dissertation a citable software artefact).

---

## 7. Honest limitations to state in the repo

- Research prototype; **not production- or safety-certified**.
- Known security gaps carried openly (unauthenticated `/cars/respond`, plaintext OpenFlow control channel, no TLS, TCP-reset-on-quarantine and per-cell sensing as future work).
- Emulation uses **software PLC servers**; it is a functional demo, not a substitute for validating against real hardware and real process safety.
- Offensive attack clients are for **research and authorised testing only**.

---

## 8. Academic tie-in

- Strengthens the dissertation's reproducibility and future-work story (pairs with the MiniCPS and ICS-testbed reproducibility references already cited).
- Add a one-line **Availability** statement to the report pointing at the repo, and a future-work sentence: "CARS is packaged as an installable framework with an emulation mode, so the pipeline can be adopted and reproduced without the specific hardware."
- A Zenodo DOI makes the software formally citable.

---

## Next step

Authorise the GitHub connector, then I will: read the repo, confirm the actual module/file layout against this plan, and start **Phase 0 + Phase 1** (hygiene and config extraction) — the two lowest-risk, highest-leverage steps — before touching the emulation layer.
