# Quickstart

Two paths: validate a policy in seconds (any machine), or run a full defended attack in emulation (a Linux host with root).

## 1. Install

```bash
cd framework
pip install -e .            # core (pyyaml + the cars package)
# for the live controller and/or emulation, add extras:
pip install -e '.[controller,emulation]'
```

## 2. Validate a site policy (any machine)

```bash
cars config validate examples/site.testbed.yaml
```

Loads the config, checks roles/tiers/rulebook, and prints the criticality-scaled timeouts (75/60/45/30 s). Copy `examples/site.testbed.yaml` to describe your own network — that is how you adopt CARS, no code edits.

## 3. Run it in emulation (Linux + root)

Needs Mininet, Open vSwitch and Snort. See `emulation/README.md` for detail.

```bash
# terminal A — the config-driven controller
CARS_SITE=examples/site.testbed.yaml osken-manager ../06_Build/cars_engine.py

# terminal B — fabric + software PLCs (auto-started), then attack
sudo emulation/demo.sh
mininet> atk python3 ../06_Build/s7_write.py 192.168.2.10
mininet> ovsgw ovs-ofctl -O OpenFlow13 dump-flows ovsgw | grep 0xca
```

Expected: the attacker's forbidden S7 write is recovered by Snort, classified FORBIDDEN on the CRITICAL PLC, and a `0x00ca` isolate is installed; the tank loop keeps running.

## 4. Run the tests

```bash
cd framework
PYTHONPATH=. pytest tests/ -q      # config parity + headless emulation core
```

The emulation-core suite starts the software S7 PLC and the tank co-sim with no hardware, so it is a genuine self-test of your install.

## Next

- `docs/ARCHITECTURE.md` — how the pieces fit.
- `../docs/planning/CARS_FRAMEWORK_PLAN.md` — the phase roadmap.
- `SECURITY.md` / `LIMITATIONS.md` — what this is and is not.
