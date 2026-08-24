# Reproducing CARS

Three levels of increasing hardware need. **Levels 1–2 need no ICS hardware** — one Linux machine is enough (see [`HARDWARE.md`](HARDWARE.md)). These steps were validated in a clean-room run on a fresh **Ubuntu 24.04** Dell, cloning this repo from scratch; the gotchas that run surfaced are baked in below.

> **Python version matters for the controller.** The self-test (Level 1) runs on any Python 3.9+. The **controller and emulation (Level 2) need Python 3.11** — os-ken (the OpenFlow framework) is not yet compatible with Python 3.12, and its 4.x wheels omit the runner. Use a Python 3.11 venv for Level 2.

---

## Level 1 — decision logic and process core (any machine, no root)

```bash
cd framework
python3 -m venv ~/carsenv && source ~/carsenv/bin/activate
pip install -e '.[dev,emulation]'          # pytest + ruff + python-snap7 + pymodbus
pytest tests/ -q                           # expect: 10 passed
cars config validate examples/site.testbed.yaml
```

- `test_config_parity.py` (7 tests) proves `site.testbed.yaml` reproduces the engine's built-in policy exactly.
- `test_emulation_core.py` (3 tests) starts the software S7 PLC and runs the tank co-simulation headless — a genuine self-test with no hardware.

Validated output: **`10 passed`**, and `cars config validate` prints `12 assets, 9 conduits, 32 rulebook rows, timeouts CRITICAL=75s … LOW=30s`.

---

## Level 2 — full defended attack in emulation (Linux host + root)

The physical Siemens CPU is replaced by a software S7 server; the controller, Snort, OVS and the S7/Modbus wire traffic are real.

### Install (Ubuntu 24.04, Python 3.11)

```bash
sudo apt update
sudo apt install -y git python3.11 python3.11-venv openvswitch-switch mininet snort
#   (on 22.04, python3.11 may need: sudo add-apt-repository ppa:deadsnakes/ppa)

git clone https://github.com/Amitdeb00731/A-Criticality--and-Operation-Aware-Response-Framework-CARS.git
cd A-Criticality--and-Operation-Aware-Response-Framework-CARS/framework

python3.11 -m venv ~/cars311 && source ~/cars311/bin/activate
pip install -e '.[controller,emulation]'   # os-ken (2.x, pinned), python-snap7, pymodbus, eventlet
pip install mininet                         # Mininet's Python API into the venv (apt's is system-python only)
```

### Run

```bash
# preserve the venv PATH under sudo; run via bash (fresh clones may lack the exec bit)
sudo -E env "PATH=$PATH" bash emulation/demo.sh
```

`demo.sh` starts the config-driven controller (defaulting to `examples/site.emulation.yaml`), brings up the two-cell Mininet fabric, and auto-starts the software PLCs and tank. When you reach the `mininet>` prompt, run these **one per line**:

```
hist cat /tmp/cars_tank.log
atk python3 ../../06_Build/s7_write.py --host 192.168.2.10
sh ovs-ofctl -O OpenFlow13 dump-flows ovs1 | grep 192.168.2.10
```

### What you should see (validated)

- **Controller log** (`/tmp/cars_controller.log`): `GUARD installed on dpid=1/3/2`, `A2 allowlist installed (STATEFUL/conntrack) … 9 allow, 4 deny`, `switch UP … total=3`.
- **Tank**: the bang-bang loop running — `level=… pump=… relay=… interference=0/…` — the process is live and undisturbed.
- **Attacker**: `TCP connection failed: timed out` — the unregistered `atk` (`192.168.2.77`) cannot reach PLC1; **zero landed**.
- **Flows**: the legitimate conduits at `priority=80, cookie=0xa2` (committed), and the default-deny
  `priority=55 … nw_dst=192.168.2.10 … actions=drop` with **`n_packets>0`** — the attacker's SYN retransmits caught at the handshake.

That is the Chapter 4 two-pivot proactive result, reproduced end to end on a blank machine.

### The operation-aware (DPI) half — reactive `0x00ca` isolate

The proactive demo above stops an *unregistered* attacker at the allowlist. The reactive path adds the operation-aware response for a **compromised, allowlisted** conduit: a host that is *allowed* to talk to a PLC but issues a **forbidden operation** (an S7 write to a CRITICAL CPU). Detection is Snort DPI; the graded decision and the criticality-scaled `0x00ca` isolate are the controller's.

One prerequisite makes this honest in emulation. On the hardware testbed the PLC ran its own ladder logic, so the *only* S7 write on the wire was an attack. In software, the tank is normally driven by an external client (`tank.py`) — those writes would themselves trip the S7-CONTROL rule. So run the PLC in **self-plant** mode, where the bang-bang loop runs *inside* the PLC (no legitimate control-write on the wire):

```bash
# terminal A — controller + fabric, PLC runs the plant itself
sudo -E env "PATH=$PATH" CARS_SELF_PLANT=1 bash emulation/demo.sh

# terminal B — Snort on the gateway SPAN + the Snort->controller bridge
sudo -E env "PATH=$PATH" bash emulation/dpi.sh
```

Then, at the `mininet>` prompt (terminal A), attack from an **allowlisted** host doing a **forbidden** op:

```
scada python3 ../../06_Build/s7_write.py --host 192.168.2.10 --count 5
sh ovs-ofctl -O OpenFlow13 dump-flows ovsgw | grep 0xca
```

What you should see:

- **Bridge** (`/tmp/cars_bridge.log`): `REPORT 192.168.2.31 -> 192.168.2.10 S7 op=CONTROL … | CARS: …` — Snort fired `CARS-S7-CONTROL-write` and the bridge reported the *operation*, not just "TCP".
- **Controller** (`/tmp/cars_controller.log`): the engine classifies CONTROL-on-CRITICAL-PLC as **FORBIDDEN** and installs an **ISOLATE** on `192.168.2.31`, cookie `0xca`, with the criticality-scaled timeout.
- **Flows**: a `cookie=0xca` rule on `ovsgw` matching `192.168.2.31`.
- **Process** (`/tmp/cars_s7.log`): the PLC's `interference` counter ticks up **once** (the first write leaked on the allowlisted conduit — the report's Gap 3) and then **stops** as the isolate cuts the source; the level keeps oscillating. The attacker is cut; the process is not.

> Contrast to prove the *operation* axis: `scada python3 ../../06_Build/s7_write.py --host 192.168.2.10 --read` performs an S7 **read**. It fires `CARS-S7-READ-var`, is classified OPERATIONAL, and is **not** isolated — same host, same conduit, different operation, different response.

The self-plant loop and its interference detection are self-tested (`python3 emulation/plc/s7_server.py` under `CARS_SELF_PLANT=1`); the Snort SPAN + bridge + isolate is the runbook above.

---

## Level 3 — hardware testbed (real PLCs)

Use `examples/site.testbed.yaml` (real GUARD bindings). The system runs as the `cars-*` systemd services in `06_Build/`; see `06_Build/COLD_START.md` and `06_Build/AS_BUILT_TOPOLOGY.md`. Minimum hardware is one Linux host + one S7-1200 (`HARDWARE.md`, Tier 1).

---

## Troubleshooting (seen in the clean-room run)

| Symptom | Cause / fix |
|---|---|
| `osken-manager` missing, `No module named 'os_ken.cmd'` | os-ken 4.x wheels omit the runner. Pin `os-ken>=2.7,<3` (the `[controller]` extra now does). |
| Controller won't run on Python 3.12 | os-ken isn't 3.12-ready — use a **Python 3.11** venv. The self-test (Level 1) is fine on 3.12. |
| `No module named 'mininet'` (under the venv) | apt installs Mininet into system Python only. `pip install mininet` into the venv. |
| `env: 'bash': No such file` / preflight `MISSING: osken-manager` under sudo | Run `sudo -E env "PATH=$PATH" bash emulation/demo.sh` to carry the venv PATH into root. |
| Legit hosts dropped as `SPOOFED`, tank `No route to host` | GUARD bindings are physical port/MAC. Use `examples/site.emulation.yaml` (demo.sh defaults to it). |
| `s7_write.py: error: required: --host` | Use `--host 192.168.2.10`. |
| `ovs-ofctl: 127.0.0.1 is not a bridge` | In the Mininet CLI, dump flows with `sh ovs-ofctl …` (OVS bridges live in the root namespace). |
| DPI: the tank host gets isolated / interference floods | You skipped self-plant. Start terminal A with `CARS_SELF_PLANT=1` so the PLC (not an external client) drives the actuator. |
| DPI: no `0xca` rule appears after the attack | Check `/tmp/cars_bridge.log` (did Snort alert?) and `/tmp/cars_snort.log`. Snort must be 2.9 for `cars.conf` (stream5); `apt install snort` on 24.04 gives 2.9. |
| DPI: bridge can't reach the controller | The bridge posts to `127.0.0.1:8080`. Run `dpi.sh` on the same host as the controller; the WSGI binds `0.0.0.0:8080` and `/cars/respond` needs no token. |

---

## Which harness reproduces which claim (hardware)

| Claim | Harness |
|---|---|
| 100% decision accuracy over 2,078 cases | `07_Evaluation/overnight/vast_accuracy.py` (data: `results/vast/vast.csv`) |
| Reaction window (median 7.6 ms) | `07_Evaluation/cars2_mttm.py`, `06_Build/cars_mttm.sh` |
| Criticality-scaled response ladder | `06_Build/cars_criticality_proof.sh` |
| Wire-level block-and-maintain (0 vs 973) | `06_Build/cars_wire_campaign.sh` / `_disarmed.sh` |
| Event-driven flow-integrity (30/30) | `07_Evaluation/overnight/gap4_flowmonitor/cars_flowmonitor.py` |
| Process transparency (armed ≈ disarmed) | `07_Evaluation/overnight/results/e2/interleaved.csv` |

## The dissertation

See `BUILD.md`.
