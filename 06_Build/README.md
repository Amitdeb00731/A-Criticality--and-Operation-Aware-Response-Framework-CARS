# 06_Build — the CARS system as built on the testbed

This is the system exactly as it ran on the hardware testbed: the os-ken controller, the
Snort detection bridge, the self-check and remediation agents, the process model, the
attack clients, and the evaluation harnesses. It runs as a set of `cars-*` systemd
services. For a **no-hardware** run, use `../framework/emulation/` instead; for the
config-driven controller, set `CARS_SITE` (see `../framework/`).

Dependencies: `requirements.txt` (os-ken, python-snap7, pymodbus, eventlet). Snort and
Open vSwitch are system packages. Start here: **`COLD_START.md`** (bring-up) and
**`AS_BUILT_TOPOLOGY.md`** (the wiring); build history is in `BUILD_LOG.md`.

## The decision core

| File | Role |
|---|---|
| `cars_engine.py` | os-ken OpenFlow 1.3 controller: `classify()`, criticality elevation, `select_response()`, GUARD binding, the three-table install, the authenticated control API. Reads a `site.yaml` when `CARS_SITE` is set. |
| `snort_bridge.py` | Snort alert file → operation + rate → `POST /cars/respond`. |
| `cars_flow_audit.py` | Flow-integrity check of the live tables against the trusted baseline (cookie `0x00a2`). |
| `cars_remediation.py` | Last-good process-state restore agent. |
| `l2_switch.py` | Reference L2 learning switch (Table 2 behaviour). |

## Process / hardware-in-the-loop

| File | Role |
|---|---|
| `cars_process.py` | Water-tank bang-bang control loop (the process model / control law). |
| `cars_dashboard.py` | Live operator dashboard (discovery-driven); `cars_nodered_*.json` are the Node-RED flows. |

## Detection rules

| File | Role |
|---|---|
| `cars.rules` | S7comm and Modbus operation-class Snort rules. |
| `cars_ics_dpi_rules.txt` | Working DPI rule notes. |

## Attack clients (research / authorised testing only — see ../ETHICS.md)

| File | Role |
|---|---|
| `s7_write.py`, `s7_probe.py` | S7 write / session-probe against a PLC. |
| `mb_attack.py`, `mb_client.py`, `mb_server.py` | Modbus attack, client, and a software Modbus server. |
| `cars_fdi_overflow.py` | False-data-injection overflow driver. |
| `kali_evil.sh` | Attacker-VM helper. |

## Evaluation harnesses

Reproduce the Chapter 4 results (see `../REPRODUCE.md` for the claim → harness map):

- `cars_eval.py` — decision-accuracy matrix through `/cars/respond`.
- `cars_criticality_proof.sh` — the criticality-scaled response sweep.
- `cars_wire_campaign.sh` / `cars_wire_campaign_disarmed.sh` / `cars_campaign_lib.sh` — the armed-vs-unprotected wire campaign.
- `cars_mttm.sh` — reaction-window (mean-time-to-mitigate) timing.
- `cars_e2e.sh`, `cars_packet_proof.sh`, `cars_ics_battery.sh`, `cars_stress.sh` — end-to-end, packet-level, battery and stress runs.
- `cars_flowaudit_test.sh`, `cars_stateful_test.sh`, `cars_deploy_verify.sh`, `cars_validate_all.sh` — component and deployment checks.

## Services and setup

`cars-*.service` are the systemd units (controller, snort bridge, flow-audit, remediation,
modbus, honeypot, cell-2). `cars-*.sh` and `cars-modbus-setup.sh` are the namespace/seam
setup helpers. `patch_*.py` are one-off retrofit patches applied during the build (kept for
the record; not needed for a fresh deploy).
